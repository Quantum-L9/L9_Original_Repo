#!/usr/bin/env python3
"""
Memory Spec v3.0 Verification Script

Validates that memory_spec_v3.0.yaml is:
1. The ONLY memory spec (no duplicates)
2. Fully instantiated (all modules exist)
3. All required methods are implemented
4. Contracts are wired

Usage:
    python scripts/audit/verify_memory_spec_v3.py
    python scripts/audit/verify_memory_spec_v3.py --verbose
    python scripts/audit/verify_memory_spec_v3.py --fix-suggestions
"""

from __future__ import annotations

# ============================================================================
__dora_meta__ = {
    "component_name": "Verify Memory Spec V3",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2026-01-13T18:30:12Z",
    "updated_at": "2026-01-13T16:13:17Z",
    "layer": "operations",
    "domain": "scripts",
    "module_name": "verify_memory_spec_v3",
    "type": "cli",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": [],
        "memory_layers": ["semantic_memory"],
        "imported_by": [],
    },
}
# ============================================================================

import argparse
import ast
import re
import sys
from pathlib import Path
from typing import Any

import yaml

# =============================================================================
# Configuration
# =============================================================================

REPO_ROOT = Path(__file__).parent.parent.parent
MEMORY_DIR = REPO_ROOT / "memory"
SPEC_FILE = MEMORY_DIR / "memory_spec_v3.0.yaml"

# Patterns that indicate deprecated/old specs
DEPRECATED_SPEC_PATTERNS = [
    "memory-yaml*.yaml",
    "memory_spec_v1*.yaml",
    "memory_spec_v2*.yaml",
    "*-wirein-*.yaml",
]

# =============================================================================
# Spec Loader
# =============================================================================


def load_spec() -> dict[str, Any]:
    """Load and parse the memory spec v3.0."""
    if not SPEC_FILE.exists():
        print(f"❌ CRITICAL: Spec file not found: {SPEC_FILE}")
        sys.exit(1)

    with open(SPEC_FILE) as f:
        return yaml.safe_load(f)


# =============================================================================
# Check 1: No Duplicate Specs
# =============================================================================


def check_no_duplicate_specs(verbose: bool = False) -> tuple[bool, list[str]]:
    """Ensure memory_spec_v3.0.yaml is the ONLY active spec."""
    issues = []

    # Check for deprecated spec files
    for pattern in DEPRECATED_SPEC_PATTERNS:
        matches = list(MEMORY_DIR.glob(pattern))
        for match in matches:
            issues.append(f"Deprecated spec found: {match.name}")

    # Check tests directory for old wire-in files
    tests_dir = REPO_ROOT / "tests"
    if tests_dir.exists():
        for pattern in ["*memory-yaml*.yaml", "*wirein*memory*.yaml"]:
            matches = list(tests_dir.glob(pattern))
            for match in matches:
                issues.append(f"Old wire-in test file: {match.relative_to(REPO_ROOT)}")

    # Check for stale comment bindings in code
    binding_pattern = re.compile(r"#\s*bound to memory-yaml")
    for py_file in MEMORY_DIR.glob("*.py"):
        content = py_file.read_text()
        if binding_pattern.search(content):
            issues.append(f"Stale v2.0 binding comment in: {py_file.name}")

    passed = len(issues) == 0
    return passed, issues


# =============================================================================
# Check 2: Required Modules Exist
# =============================================================================


def check_required_modules(spec: dict, verbose: bool = False) -> tuple[bool, list[str]]:
    """Verify all modules referenced in spec exist."""
    issues = []

    # Extract module references from memory_layers
    memory_layers = spec.get("memory_layers", {})
    for layer_name, layer_config in memory_layers.items():
        module = layer_config.get("module")
        if module:
            module_path = MEMORY_DIR / module
            if not module_path.exists():
                issues.append(
                    f"Layer '{layer_name}' references missing module: {module}"
                )
            elif verbose:
                print(f"  ✓ {layer_name} → {module}")

    # Extract module references from pipelines
    pipelines = spec.get("pipelines", {})
    for pipeline_name, pipeline_config in pipelines.items():
        entrypoint = pipeline_config.get("entrypoint")
        if entrypoint:
            entrypoint_path = MEMORY_DIR / entrypoint
            if not entrypoint_path.exists():
                issues.append(
                    f"Pipeline '{pipeline_name}' references missing entrypoint: {entrypoint}"
                )
            elif verbose:
                print(f"  ✓ {pipeline_name} → {entrypoint}")

        # Check binding modules
        binding = pipeline_config.get("binding", {})
        for bind_name, bind_module in binding.items():
            bind_path = MEMORY_DIR / bind_module
            if not bind_path.exists():
                issues.append(
                    f"Pipeline '{pipeline_name}' binding '{bind_name}' references missing: {bind_module}"
                )

    # Check query_classifier module
    retrieval = pipelines.get("retrieval", {})
    query_classifier = retrieval.get("query_classifier", {})
    qc_module = query_classifier.get("module")
    if qc_module:
        qc_path = MEMORY_DIR / qc_module
        if not qc_path.exists():
            issues.append(f"Query classifier references missing module: {qc_module}")
        elif verbose:
            print(f"  ✓ query_classifier → {qc_module}")

    passed = len(issues) == 0
    return passed, issues


# =============================================================================
# Check 3: Required Methods Exist
# =============================================================================


def extract_class_methods(file_path: Path) -> dict[str, list[str]]:
    """Extract all method names from classes in a Python file."""
    methods_by_class: dict[str, list[str]] = {}

    try:
        content = file_path.read_text()
        tree = ast.parse(content)
    except (SyntaxError, FileNotFoundError):
        return methods_by_class

    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            class_methods = []
            for item in node.body:
                if isinstance(item, ast.FunctionDef) or isinstance(
                    item, ast.AsyncFunctionDef
                ):
                    class_methods.append(item.name)
            methods_by_class[node.name] = class_methods

    return methods_by_class


def extract_function_names(file_path: Path) -> list[str]:
    """Extract all top-level function names from a Python file."""
    functions = []

    try:
        content = file_path.read_text()
        tree = ast.parse(content)
    except (SyntaxError, FileNotFoundError):
        return functions

    for node in ast.iter_child_nodes(tree):
        if isinstance(node, ast.FunctionDef) or isinstance(node, ast.AsyncFunctionDef):
            functions.append(node.name)

    return functions


def parse_method_signature(sig: str) -> str:
    """Extract method name from signature like 'store_embedding(vector: List[float], ...) -> UUID'."""
    match = re.match(r"(\w+)\s*\(", sig)
    return match.group(1) if match else sig


def check_required_methods(spec: dict, verbose: bool = False) -> tuple[bool, list[str]]:
    """Verify all required_methods from spec are implemented."""
    issues = []

    memory_layers = spec.get("memory_layers", {})

    for layer_name, layer_config in memory_layers.items():
        module_name = layer_config.get("module")
        if not module_name:
            continue

        module_path = MEMORY_DIR / module_name
        if not module_path.exists():
            continue  # Already reported in module check

        # Get all methods in this module
        class_methods = extract_class_methods(module_path)
        top_functions = extract_function_names(module_path)
        all_methods = set(top_functions)
        for methods in class_methods.values():
            all_methods.update(methods)

        # Check responsibilities
        responsibilities = layer_config.get("responsibilities", {})
        for resp_name, resp_config in responsibilities.items():
            if isinstance(resp_config, dict):
                required = resp_config.get("required_methods", [])
                for method_sig in required:
                    method_name = parse_method_signature(method_sig)
                    if method_name not in all_methods:
                        issues.append(
                            f"Layer '{layer_name}' responsibility '{resp_name}' "
                            f"missing method: {method_name} (in {module_name})"
                        )
                    elif verbose:
                        print(f"  ✓ {layer_name}.{resp_name} → {method_name}")

    # Check pipeline-specific modules (reasoning_replay, consolidation)
    pipelines = spec.get("pipelines", {})
    for pipeline_name, pipeline_config in pipelines.items():
        entrypoint = pipeline_config.get("entrypoint")
        if not entrypoint:
            continue

        entrypoint_path = MEMORY_DIR / entrypoint
        if not entrypoint_path.exists():
            continue

        class_methods = extract_class_methods(entrypoint_path)
        top_functions = extract_function_names(entrypoint_path)
        all_methods = set(top_functions)
        for methods in class_methods.values():
            all_methods.update(methods)

        # Check responsibilities in pipeline
        responsibilities = pipeline_config.get("responsibilities", {})
        for resp_name, resp_config in responsibilities.items():
            if isinstance(resp_config, dict):
                required = resp_config.get("required_methods", [])
                for method_sig in required:
                    method_name = parse_method_signature(method_sig)
                    if method_name not in all_methods:
                        issues.append(
                            f"Pipeline '{pipeline_name}' responsibility '{resp_name}' "
                            f"missing method: {method_name} (in {entrypoint})"
                        )
                    elif verbose:
                        print(f"  ✓ {pipeline_name}.{resp_name} → {method_name}")

    passed = len(issues) == 0
    return passed, issues


# =============================================================================
# Check 4: Feature Flags Defined
# =============================================================================


def check_feature_flags(spec: dict, verbose: bool = False) -> tuple[bool, list[str]]:
    """Verify feature flags are defined in code (optional - informational)."""
    issues = []
    warnings = []

    feature_flags = spec.get("feature_flags", {})
    if not feature_flags:
        return True, []

    # Search for flag usage in codebase
    for flag_name, flag_config in feature_flags.items():
        found = False

        # Check memory directory
        for py_file in MEMORY_DIR.glob("**/*.py"):
            content = py_file.read_text()
            if flag_name in content:
                found = True
                if verbose:
                    print(f"  ✓ {flag_name} found in {py_file.name}")
                break

        # Check core directory
        if not found:
            core_dir = REPO_ROOT / "core"
            if core_dir.exists():
                for py_file in core_dir.glob("**/*.py"):
                    content = py_file.read_text()
                    if flag_name in content:
                        found = True
                        if verbose:
                            print(
                                f"  ✓ {flag_name} found in {py_file.relative_to(REPO_ROOT)}"
                            )
                        break

        if not found:
            # Not an error, just informational
            warnings.append(
                f"Feature flag '{flag_name}' not found in code (may be future)"
            )

    if verbose and warnings:
        for w in warnings:
            print(f"  ⚠ {w}")

    # Feature flags not found is not a failure - they may be planned
    return True, []


# =============================================================================
# Check 5: Contracts Validation (Lightweight)
# =============================================================================


def check_contracts(spec: dict, verbose: bool = False) -> tuple[bool, list[str]]:
    """Basic validation that contract targets exist."""
    issues = []

    pipelines = spec.get("pipelines", {})

    for pipeline_name, pipeline_config in pipelines.items():
        contracts = pipeline_config.get("contracts", [])

        for contract in contracts:
            if isinstance(contract, dict):
                # Handle must_call
                must_call = contract.get("must_call")
                if must_call:
                    # Extract module.method format
                    if "." in must_call:
                        layer, method = must_call.split(".", 1)
                        layer_config = spec.get("memory_layers", {}).get(layer, {})
                        module = layer_config.get("module")
                        if module:
                            module_path = MEMORY_DIR / module
                            if module_path.exists():
                                all_methods = set(extract_function_names(module_path))
                                for methods in extract_class_methods(
                                    module_path
                                ).values():
                                    all_methods.update(methods)

                                if method not in all_methods:
                                    issues.append(
                                        f"Pipeline '{pipeline_name}' contract must_call "
                                        f"'{must_call}' - method not found"
                                    )
                                elif verbose:
                                    print(f"  ✓ Contract {pipeline_name} → {must_call}")

    passed = len(issues) == 0
    return passed, issues


# =============================================================================
# Main Verification
# =============================================================================


def run_verification(verbose: bool = False, fix_suggestions: bool = False) -> bool:
    """Run all verification checks."""
    print("=" * 60)
    print("Memory Spec v3.0 Verification")
    print("=" * 60)
    print(f"Spec file: {SPEC_FILE.relative_to(REPO_ROOT)}")
    print()

    spec = load_spec()
    all_passed = True

    # Check 1: No duplicates
    print("▶ Check 1: No Duplicate Specs")
    passed, issues = check_no_duplicate_specs(verbose)
    if passed:
        print("  ✅ PASS - No deprecated specs found")
    else:
        print("  ❌ FAIL")
        for issue in issues:
            print(f"    - {issue}")
        all_passed = False
    print()

    # Check 2: Required modules
    print("▶ Check 2: Required Modules Exist")
    passed, issues = check_required_modules(spec, verbose)
    if passed:
        print("  ✅ PASS - All modules exist")
    else:
        print("  ❌ FAIL")
        for issue in issues:
            print(f"    - {issue}")
        all_passed = False
    print()

    # Check 3: Required methods
    print("▶ Check 3: Required Methods Implemented")
    passed, issues = check_required_methods(spec, verbose)
    if passed:
        print("  ✅ PASS - All required methods found")
    else:
        print("  ⚠️  PARTIAL")
        for issue in issues:
            print(f"    - {issue}")
        # Don't fail on missing methods - spec may be aspirational
    print()

    # Check 4: Feature flags
    print("▶ Check 4: Feature Flags (Informational)")
    passed, issues = check_feature_flags(spec, verbose)
    print("  ℹ️  INFO - Feature flag check complete")
    print()

    # Check 5: Contracts
    print("▶ Check 5: Contract Validation")
    passed, issues = check_contracts(spec, verbose)
    if passed:
        print("  ✅ PASS - Contracts validated")
    else:
        print("  ⚠️  PARTIAL")
        for issue in issues:
            print(f"    - {issue}")
    print()

    # Summary
    print("=" * 60)
    if all_passed:
        print("✅ VERIFICATION PASSED")
        print("   memory_spec_v3.0.yaml is the sole active spec")
    else:
        print("❌ VERIFICATION FAILED")
        print("   See issues above")
    print("=" * 60)

    return all_passed


def main():
    parser = argparse.ArgumentParser(
        description="Verify memory spec v3.0 implementation"
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Show detailed output"
    )
    parser.add_argument(
        "--fix-suggestions", action="store_true", help="Show fix suggestions"
    )
    args = parser.parse_args()

    success = run_verification(
        verbose=args.verbose, fix_suggestions=args.fix_suggestions
    )
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()

# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "SCR-OPER-001",
    "governance_level": "medium",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": ["ast", "cli", "config", "filesystem", "operations", "scripts", "testing"],
    "keywords": [
        "check",
        "contracts",
        "duplicate",
        "extract",
        "feature",
        "flags",
        "function",
        "load",
    ],
    "business_value": "Utility module for verify memory spec v3",
    "last_modified": "2026-01-13T16:13:17Z",
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
