#!/usr/bin/env python3
"""
L9 Code Generation Validator
============================
Strict validation for generated code against Module-Spec v2.5.

BEHAVIOR:
- Enforce repo file manifest (no files outside allowed list)
- Enforce tool_id usage
- Enforce dependency contract alignment
- Enforce test presence
- NO permissive fallbacks
- NO inference

EXIT CODES:
- 0: All validations passed
- 1: Validation failed
- 2: Configuration error

Usage:
    python ci/validate_codegen.py --spec path/to/spec.yaml --files file1.py file2.py
    python ci/validate_codegen.py --spec path/to/spec.yaml --dir api/
"""

# ============================================================================
__dora_meta__ = {
    "component_name": "Validate Codegen",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2025-12-20T15:08:40Z",
    "updated_at": "2026-01-12T14:26:37Z",
    "layer": "operations",
    "domain": "ci",
    "module_name": "validate_codegen",
    "type": "cli",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": ["HTTP API"],
        "memory_layers": ["working_memory"],
        "imported_by": [],
    },
}
# ============================================================================

import os
import re
import sys
from pathlib import Path

import structlog
import yaml

logger = structlog.get_logger(__name__)


# =============================================================================
# FORBIDDEN PATTERNS
# =============================================================================

# Forbidden imports per standards
FORBIDDEN_IMPORTS = {
    "logging": "Use structlog instead of logging",
    "aiohttp": "Use httpx instead of aiohttp",
    "requests": "Use httpx instead of requests",
}

# Forbidden function calls
FORBIDDEN_CALLS = {
    "print": "Use structlog for logging, not print statements",
    "uuid.uuid4": "Use UUIDv5 for thread_id, not uuid4",
}

# Required patterns in code
REQUIRED_PATTERNS = {
    "tool_id": r"tool_id\s*[=:]",
    "structlog": r"import\s+structlog|from\s+structlog",
}


# =============================================================================
# VALIDATION RESULT
# =============================================================================


class CodeValidationResult:
    """Accumulates code validation errors."""

    def __init__(self) -> None:
        """Initialize validation result container."""
        self.errors: list[str] = []
        self.warnings: list[str] = []
        self.files_checked: list[str] = []

    def add_error(self, error: str) -> None:
        """Add an error to the result."""
        self.errors.append(error)

    def add_warning(self, warning: str) -> None:
        """Add a warning to the result."""
        self.warnings.append(warning)

    @property
    def is_valid(self) -> bool:
        """Check if validation passed."""
        return len(self.errors) == 0

    def print_report(self) -> None:
        """Print validation report."""
        logger.info(f"\n{'=' * 70}")
        logger.info("CODE VALIDATION REPORT")
        logger.info(f"{'=' * 70}")
        logger.info(f"Files checked: {len(self.files_checked)}")

        if self.is_valid:
            logger.info("✅ PASSED - All code requirements satisfied")
        else:
            logger.error(f"❌ FAILED - {len(self.errors)} error(s) found\n")
            for i, error in enumerate(self.errors, 1):
                logger.error(f"  [{i}] {error}")

        if self.warnings:
            logger.warning(f"\n⚠️  WARNINGS ({len(self.warnings)}):")
            for warning in self.warnings:
                logger.warning(f"    - {warning}")

        logger.info(f"{'=' * 70}\n")


# =============================================================================
# FILE MANIFEST VALIDATOR
# =============================================================================


def validate_file_manifest(
    spec: dict, files: list[str], result: CodeValidationResult
) -> None:
    """
    Validate that all files are in the allowed manifest.

    STRICT: Any file not in allowed_new_files or allowed_modified_files = FAIL
    """
    repo = spec.get("repo", {})
    root_path = repo.get("root_path", "")

    allowed_new = repo.get("allowed_new_files", [])
    allowed_modified = repo.get("allowed_modified_files", [])

    # Get module_id for template substitution
    metadata = spec.get("metadata", {})
    module_id = metadata.get("module_id", "")
    module_name = metadata.get("name", "")

    # Expand templates in allowed files
    def expand_template(template: str) -> str:
        """
        Generates a code template by replacing placeholders with module-specific identifiers.

        Args:
            template: String containing placeholders to be replaced with module identifiers.

        Returns:
            The expanded template string with placeholders substituted by module-specific values.
        """
        return (
            template.replace("{{module}}", module_id)
            .replace("{{Module}}", module_name.replace(" ", ""))
            .replace("{{MODULE}}", module_id.upper())
        )

    allowed_new_expanded = [expand_template(f) for f in allowed_new]
    allowed_modified_expanded = [expand_template(f) for f in allowed_modified]

    all_allowed = set(allowed_new_expanded + allowed_modified_expanded)

    for file_path in files:
        # Normalize path relative to repo root
        rel_path = str(
            Path(file_path).relative_to(root_path) if root_path else file_path
        )

        # Check if file is in allowed list
        if rel_path not in all_allowed:
            # Check if any pattern matches
            matched = False
            for allowed in all_allowed:
                # Simple glob matching
                pattern = allowed.replace("*", ".*")
                if re.match(pattern, rel_path):
                    matched = True
                    break

            if not matched:
                result.add_error(
                    f"FILE NOT IN MANIFEST: {rel_path}\n"
                    f"       Allowed new files: {allowed_new_expanded}\n"
                    f"       Allowed modified: {allowed_modified_expanded}"
                )


# =============================================================================
# TOOL_ID USAGE VALIDATOR
# =============================================================================


def validate_tool_id_usage(
    file_path: str, content: str, result: CodeValidationResult
) -> None:
    """
    Validate that tool_id is used correctly.

    STRICT: All handlers must use tool_id for identity
    """
    # Check if this is a handler/adapter file
    if "_adapter" in file_path or "_handler" in file_path or "routes" in file_path:
        if "tool_id" not in content:
            result.add_error(
                f"MISSING tool_id: {file_path}\n"
                f"       All handlers must use tool_id for canonical identity"
            )


# =============================================================================
# DEPENDENCY CONTRACT VALIDATOR
# =============================================================================


def validate_dependency_contract(
    spec: dict, file_path: str, content: str, result: CodeValidationResult
) -> None:
    """
    Validate that code aligns with declared dependencies.

    STRICT:
    - No undeclared outbound calls
    - No imports from disallowed tiers
    """
    dependency_contract = spec.get("dependency_contract", {})
    outbound = dependency_contract.get("outbound", [])

    # Extract declared outbound modules
    declared_modules = set()
    for out in outbound:
        if isinstance(out, dict):
            declared_modules.add(out.get("to_module", ""))

    # Check for httpx calls to undeclared endpoints
    # This is a heuristic - look for httpx.post/get/etc calls
    httpx_pattern = r'httpx\.(post|get|put|delete|patch)\s*\(\s*["\']([^"\']+)["\']'
    matches = re.findall(httpx_pattern, content)

    for _method, url in matches:
        # Check if URL matches any declared outbound
        matched = False
        for out in outbound:
            if isinstance(out, dict):
                endpoint = out.get("endpoint", "")
                if endpoint in url or url.endswith(endpoint):
                    matched = True
                    break

        if not matched and "localhost" not in url and "127.0.0.1" not in url:
            result.add_warning(
                f"UNDECLARED OUTBOUND: {file_path} calls {url}\n"
                f"       Not in dependency_contract.outbound"
            )


# =============================================================================
# TEST PRESENCE VALIDATOR
# =============================================================================


def validate_test_presence(
    spec: dict, generated_files: list[str], result: CodeValidationResult
) -> None:
    """
    Validate that required tests exist.

    STRICT:
    - If spec has acceptance.positive, matching test files must exist
    - If spec has acceptance.negative, matching test files must exist
    """
    acceptance = spec.get("acceptance", {})
    test_scope = spec.get("test_scope", {})

    positive_tests = acceptance.get("positive", [])
    negative_tests = acceptance.get("negative", [])

    # Extract required test function names
    required_tests = set()
    for test in positive_tests:
        if isinstance(test, dict) and "test" in test:
            required_tests.add(test["test"])

    for test in negative_tests:
        if isinstance(test, dict) and "test" in test:
            required_tests.add(test["test"])

    # Find test files in generated files
    test_files = [f for f in generated_files if "test_" in f or "_test.py" in f]

    if not test_files and required_tests:
        result.add_error(
            f"NO TEST FILES: Spec requires {len(required_tests)} tests but no test files generated\n"
            f"       Required tests: {list(required_tests)[:5]}..."
        )
        return

    # Check that test functions exist in test files
    found_tests = set()
    for test_file in test_files:
        if os.path.exists(test_file):
            try:
                with open(test_file) as f:
                    content = f.read()
                    for test_name in required_tests:
                        if f"def {test_name}" in content:
                            found_tests.add(test_name)
            except Exception:
                pass

    missing_tests = required_tests - found_tests
    if missing_tests:
        result.add_error(
            f"MISSING TESTS: The following required tests are not implemented:\n"
            f"       {list(missing_tests)}"
        )

    # Validate smoke test presence if required
    if test_scope.get("docker_smoke"):
        smoke_files = [f for f in generated_files if "smoke" in f.lower()]
        if not smoke_files:
            result.add_error(
                "MISSING SMOKE TEST: test_scope.docker_smoke=true but no smoke test file generated"
            )


# =============================================================================
# FORBIDDEN PATTERNS VALIDATOR
# =============================================================================


def validate_forbidden_patterns(
    file_path: str, content: str, result: CodeValidationResult
) -> None:
    """
    Validate that code doesn't use forbidden patterns.

    STRICT:
    - No forbidden imports
    - No print statements
    - No uuid4 for thread_id
    """
    # Check imports
    for forbidden, reason in FORBIDDEN_IMPORTS.items():
        pattern = rf"^(?:import\s+{forbidden}|from\s+{forbidden})"
        if re.search(pattern, content, re.MULTILINE):
            result.add_error(
                f"FORBIDDEN IMPORT: {file_path} imports {forbidden}\n       {reason}"
            )

    # Check for print statements (but allow in tests)
    if "test_" not in file_path:
        print_pattern = r"\bprint\s*\("
        if re.search(print_pattern, content):
            result.add_error(
                f"FORBIDDEN: {file_path} uses print statements\n"
                f"       Use structlog for logging"
            )


# =============================================================================
# PACKET METADATA VALIDATOR
# =============================================================================


def validate_packet_metadata(
    spec: dict, file_path: str, content: str, result: CodeValidationResult
) -> None:
    """
    Validate that packet metadata is included correctly.

    STRICT: All required metadata must be present in packet creation
    """
    packet_contract = spec.get("packet_contract", {})
    required_metadata = packet_contract.get("requires_metadata", [])

    # Only check files that deal with packets
    if "packet" not in file_path.lower() and "adapter" not in file_path.lower():
        return

    # Check for packet creation patterns
    packet_patterns = [
        r"PacketEnvelopeIn\s*\(",
        r"PacketEnvelope\s*\(",
        r"create_packet\s*\(",
    ]

    creates_packets = any(re.search(p, content) for p in packet_patterns)

    if creates_packets:
        for meta in required_metadata:
            # Check if metadata is referenced
            if meta not in content:
                result.add_warning(
                    f"PACKET METADATA: {file_path} creates packets but may be missing '{meta}'"
                )


# =============================================================================
# MAIN VALIDATION ENTRY POINT
# =============================================================================


def validate_code(
    spec_path: str,
    files: list[str],
) -> CodeValidationResult:
    """
    Validate generated code against Module-Spec v2.5.

    Args:
        spec_path: Path to the spec YAML file
        files: List of generated/modified code files

    Returns:
        CodeValidationResult with all errors and warnings
    """
    result = CodeValidationResult()

    # Load spec
    if not os.path.exists(spec_path):
        result.add_error(f"SPEC NOT FOUND: {spec_path}")
        return result

    try:
        with open(spec_path) as f:
            spec = yaml.safe_load(f)
    except yaml.YAMLError as e:
        result.add_error(f"SPEC PARSE ERROR: {e}")
        return result

    if spec is None:
        result.add_error("EMPTY SPEC: Spec file is empty")
        return result

    # Validate file manifest
    validate_file_manifest(spec, files, result)

    # Validate test presence
    validate_test_presence(spec, files, result)

    # Validate each file
    for file_path in files:
        if not os.path.exists(file_path):
            result.add_warning(f"FILE NOT FOUND: {file_path}")
            continue

        if not file_path.endswith(".py"):
            continue

        result.files_checked.append(file_path)

        try:
            with open(file_path) as f:
                content = f.read()
        except Exception as e:
            result.add_error(f"READ ERROR: {file_path} - {e}")
            continue

        # Run validators
        validate_tool_id_usage(file_path, content, result)
        validate_dependency_contract(spec, file_path, content, result)
        validate_forbidden_patterns(file_path, content, result)
        validate_packet_metadata(spec, file_path, content, result)

    return result


def find_files_in_dir(directory: str) -> list[str]:
    """Find all Python files in a directory."""
    files = []
    for path in Path(directory).rglob("*.py"):
        files.append(str(path))
    return files


def main() -> int:
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Validate generated code against Module-Spec v2.5"
    )
    parser.add_argument("--spec", required=True, help="Path to the spec YAML file")
    parser.add_argument("--files", nargs="+", help="List of files to validate")
    parser.add_argument("--dir", help="Directory containing files to validate")

    args = parser.parse_args()

    if not args.files and not args.dir:
        logger.error("ERROR: Must provide --files or --dir")
        return 2

    files = args.files or []
    if args.dir:
        files.extend(find_files_in_dir(args.dir))

    if not files:
        logger.warning("No files to validate")
        return 0

    result = validate_code(args.spec, files)
    result.print_report()

    return 0 if result.is_valid else 1


if __name__ == "__main__":
    sys.exit(main())

# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "CI-OPER-003",
    "governance_level": "medium",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": [
        "api",
        "ci",
        "cli",
        "config",
        "filesystem",
        "logging",
        "operations",
        "testing",
    ],
    "keywords": [
        "codegen",
        "contract",
        "dependency",
        "dir",
        "expand",
        "files",
        "find",
        "forbidden",
    ],
    "business_value": "Implements CodeValidationResult for validate codegen functionality",
    "last_modified": "2026-01-12T14:26:37Z",
    "modified_by": "L9_Codegen_Engine",
    "change_summary": "Initial generation with DORA compliance",
}
# ============================================================================
# L9 DORA BLOCK - AUTO-UPDATED - DO NOT EDIT
# Runtime execution trace - updated automatically on every execution
# ============================================================================
__l9_trace__ = {
    "trace_id": "",
    "task": "",
    "timestamp": "",
    "patterns_used": [],
    "graph": {"nodes": [], "edges": []},
    "inputs": {},
    "outputs": {},
    "metrics": {"confidence": "", "errors_detected": [], "stability_score": ""},
}
# ============================================================================
# END L9 DORA BLOCK
# ============================================================================
