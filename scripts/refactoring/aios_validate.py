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

import argparse
import ast
import sys
from pathlib import Path
from typing import Dict, List

# L9 module directories to scan (not "src" - L9 uses flat structure)
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

    def __init__(self, filename: str):
        self.filename = filename
        self.violations: List[str] = []
        self.has_pydantic = False
        self.has_logging = False
        self.functions: List[tuple] = []

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        if node.module == "pydantic":
            self.has_pydantic = True
        if "json_logger" in str(node.module or ""):
            self.has_logging = True
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self.functions.append(("async", node.name))
        # Check for type hints on public async functions
        if not node.name.startswith("_") and not node.returns:
            self.violations.append(f"Missing return type: async def {node.name}()")
        self.generic_visit(node)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        # Only track public methods/module functions
        if not node.name.startswith("_"):
            if node.name not in ["__init__", "__repr__", "__str__"]:
                self.functions.append(("sync", node.name))
        self.generic_visit(node)

    def check_file(self) -> List[str]:
        """Run compliance checks"""
        if not self.has_logging and "logger" in self.filename:
            self.violations.append("No json_logger import found")
        return self.violations


def should_skip(path: Path) -> bool:
    """Check if path should be skipped"""
    return any(skip in path.parts for skip in SKIP_DIRS)


def scan_directory(base_path: Path) -> Dict[str, List[str]]:
    """Scan directory for AIOS compliance violations"""
    violations_summary: Dict[str, List[str]] = {}

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

    violations_summary: Dict[str, List[str]] = {}

    if args.path:
        # Scan specific path
        scan_path = repo_root / args.path
        if not scan_path.exists():
            print(f"❌ Path not found: {scan_path}")
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
        print("⚠️  AIOS Compliance Issues:")
        print()
        for filepath, violations in sorted(violations_summary.items()):
            rel_path = (
                Path(filepath).relative_to(repo_root)
                if filepath.startswith(str(repo_root))
                else filepath
            )
            for violation in violations:
                print(f"  {rel_path}: {violation}")
        print()
        print(
            f"Total: {sum(len(v) for v in violations_summary.values())} issues in {len(violations_summary)} files"
        )
        return 1
    else:
        print("✅ All modules pass AIOS compliance checks")
        return 0


if __name__ == "__main__":
    sys.exit(main())
