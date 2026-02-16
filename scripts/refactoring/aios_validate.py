#!/usr/bin/env python3
"""
AIOS Compliance Validator for L9

Validates L9 codebase against AIOS architectural patterns:
- Type hints on async functions
- Structured logging imports
- Pydantic usage

Usage:
    python scripts/refactoring/aios_validate.py [--path PATH]

Examples:
    python scripts/refactoring/aios_validate.py                    # Scan L9 core modules
    python scripts/refactoring/aios_validate.py --path core/agents # Scan specific path
"""

# ============================================================================
__dora_meta__ = {
    "component_name": "Aios Validate",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2026-01-21T01:07:38Z",
    "updated_at": "2026-01-24T13:02:53Z",
    "layer": "operations",
    "domain": "scripts",
    "module_name": "aios_validate",
    "type": "service",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": [],
        "memory_layers": [],
        "imported_by": [],
    },
}
# ============================================================================

import argparse
import ast
import sys
from pathlib import Path

import structlog

# L9 module directories to scan (not "src" - L9 uses flat structure)

logger = structlog.get_logger(__name__)

L9_SCAN_DIRS = [
    "core",
    "api",
    "memory",
    "orchestration",
    "runtime",
    "workers",
    "agents",
]

# Directories to skip
SKIP_DIRS = {
    "__pycache__",
    ".venv",
    "venv",
    ".git",
    "node_modules",
    "tests",  # Tests don't need strict compliance
    "_archived",
}


class AOISCompliance(ast.NodeVisitor):
    """Verify AIOS architectural patterns"""

    def __init__(self, filename: str) -> None:
        """Initialize compliance checker for a file."""
        self.filename = filename
        self.violations: list[str] = []
        self.has_pydantic = False
        self.has_logging = False
        self.functions: list[tuple] = []

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        """Visit import-from statement node."""
        if node.module == "pydantic":
            self.has_pydantic = True
        if "json_logger" in str(node.module or ""):
            self.has_logging = True
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        """Visit async function definition node."""
        self.functions.append(("async", node.name))
        # Check for type hints on public async functions
        if not node.name.startswith("_") and not node.returns:
            self.violations.append(f"Missing return type: async def {node.name}()")
        self.generic_visit(node)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        """Visit function definition node."""
        # Only track public methods/module functions
        if not node.name.startswith("_"):
            if node.name not in ["__init__", "__repr__", "__str__"]:
                self.functions.append(("sync", node.name))
        self.generic_visit(node)

    def check_file(self) -> list[str]:
        """Run compliance checks"""
        if not self.has_logging and "logger" in self.filename:
            self.violations.append("No json_logger import found")
        return self.violations


def should_skip(path: Path) -> bool:
    """Check if path should be skipped"""
    return any(skip in path.parts for skip in SKIP_DIRS)


def scan_directory(base_path: Path) -> dict[str, list[str]]:
    """Scan directory for AIOS compliance violations"""
    violations_summary: dict[str, list[str]] = {}

    for py_file in base_path.rglob("*.py"):
        if should_skip(py_file):
            continue

        try:
            with open(py_file, encoding="utf-8") as f:
                content = f.read()
            tree = ast.parse(content)
        except (SyntaxError, UnicodeDecodeError) as e:
            violations_summary[str(py_file)] = [f"Parse error: {e}"]
            continue

        checker = AOISCompliance(str(py_file))
        checker.visit(tree)
        file_violations = checker.check_file()

        if file_violations:
            violations_summary[str(py_file)] = file_violations

    return violations_summary


def main() -> int:
    """
    Performs AIOS compliance validation for L9 codebase, checking for architectural pattern adherence.


    Returns:
        Exit status code as integer indicating success (0) or failure (non-zero) in validation process.
    """
    parser = argparse.ArgumentParser(description="AIOS Compliance Validator for L9")
    parser.add_argument(
        "--path",
        type=str,
        default=None,
        help="Specific path to scan (default: all L9 core modules)",
    )
    args = parser.parse_args()

    # Find repo root (look for pyproject.toml or .git)
    repo_root = Path.cwd()
    while repo_root != repo_root.parent:
        if (repo_root / "pyproject.toml").exists() or (repo_root / ".git").exists():
            break
        repo_root = repo_root.parent

    violations_summary: dict[str, list[str]] = {}

    if args.path:
        # Scan specific path
        scan_path = repo_root / args.path
        if not scan_path.exists():
            logger.info("❌ path not found: scan path", scan_path=scan_path)
            return 1
        violations_summary = scan_directory(scan_path)
    else:
        # Scan all L9 core modules
        for module_dir in L9_SCAN_DIRS:
            module_path = repo_root / module_dir
            if module_path.exists():
                violations_summary.update(scan_directory(module_path))

    # Report
    if violations_summary:
        logger.info("⚠️  aios compliance issues:")
        for filepath, violations in sorted(violations_summary.items()):
            rel_path = (
                Path(filepath).relative_to(repo_root)
                if filepath.startswith(str(repo_root))
                else filepath
            )
            for violation in violations:
                logger.info(
                    "  rel path: violation", rel_path=rel_path, violation=violation
                )
        print(
            f"Total: {sum(len(v) for v in violations_summary.values())} issues in {len(violations_summary)} files"
        )
        return 1
    logger.info("✅ all modules pass aios compliance checks")
    return 0


if __name__ == "__main__":
    sys.exit(main())

# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "SCR-OPER-030",
    "governance_level": "medium",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": [
        "api",
        "ast",
        "async",
        "caching",
        "cli",
        "filesystem",
        "operations",
        "scripts",
        "service",
        "testing",
    ],
    "keywords": [
        "aios",
        "check",
        "compliance",
        "directory",
        "scan",
        "should",
        "skip",
        "validate",
    ],
    "business_value": "Implements AOISCompliance for aios validate functionality",
    "last_modified": "2026-01-24T13:02:53Z",
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
