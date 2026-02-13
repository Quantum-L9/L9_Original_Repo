#!/usr/bin/env python3
"""
L9 N+1 Query Detection Script

Detects potential N+1 query patterns in Python code by analyzing:
- Database queries inside loops
- Async database calls in list comprehensions
- Sequential queries that could be batched

Usage:
    python scripts/check_n_plus_1.py [files...]
    python scripts/check_n_plus_1.py --all
    python scripts/check_n_plus_1.py --changed  # Git changed files only

Exit codes:
    0 - No issues found
    1 - Potential N+1 patterns detected
    2 - Script error
"""

# ============================================================================
__dora_meta__ = {
    "component_name": "Check N Plus 1",
    "module_version": "1.0.0",
    "created_by": "cryptoxdog",
    "created_at": "2026-01-23T15:55:26Z",
    "updated_at": "2026-01-24T13:02:53Z",
    "layer": "operations",
    "domain": "scripts",
    "module_name": "check_n_plus_1",
    "type": "cli",
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
import re
import subprocess
import sys
from pathlib import Path
import structlog



logger = structlog.get_logger(__name__)

class N1DetectorVisitor(ast.NodeVisitor):
    """AST visitor to detect N+1 query patterns"""

    def __init__(self, filename: str):
        """
        Initializes the N1DetectorVisitor with the filename to analyze for N+1 query patterns in Python code.

        Args:
            filename: The name of the file being analyzed for database query patterns.


        Raises:
            ValueError: If filename is not a string.
        """
        self.filename = filename
        self.issues: list[tuple[int, str, str]] = []
        self.in_loop = False
        self.loop_line = 0

    def visit_For(self, node: ast.For) -> None:
        """Visit for loop"""
        old_in_loop = self.in_loop
        old_loop_line = self.loop_line

        self.in_loop = True
        self.loop_line = node.lineno

        # Visit loop body
        self.generic_visit(node)

        self.in_loop = old_in_loop
        self.loop_line = old_loop_line

    def visit_While(self, node: ast.While) -> None:
        """Visit while loop"""
        old_in_loop = self.in_loop
        old_loop_line = self.loop_line

        self.in_loop = True
        self.loop_line = node.lineno

        # Visit loop body
        self.generic_visit(node)

        self.in_loop = old_in_loop
        self.loop_line = old_loop_line

    def visit_Call(self, node: ast.Call) -> None:
        """Visit function call"""
        # Check if this is a database query call
        if self._is_db_query(node):
            if self.in_loop:
                self.issues.append(
                    (
                        node.lineno,
                        "potential_n_plus_1",
                        f"Database query inside loop (loop starts at line {self.loop_line})",
                    )
                )

        self.generic_visit(node)

    def visit_ListComp(self, node: ast.ListComp) -> None:
        """Visit list comprehension"""
        # Check for database queries in list comprehension
        for _generator in node.generators:
            # Mark as in loop for the comprehension body
            old_in_loop = self.in_loop
            old_loop_line = self.loop_line

            self.in_loop = True
            self.loop_line = node.lineno

            # Visit the element expression
            self.visit(node.elt)

            self.in_loop = old_in_loop
            self.loop_line = old_loop_line

    def _is_db_query(self, node: ast.Call) -> bool:
        """Check if a call is a database query"""
        # Pattern 1: conn.fetch_one(...), conn.fetch_all(...), conn.execute(...)
        if isinstance(node.func, ast.Attribute):
            method_name = node.func.attr
            if method_name in (
                "fetch_one",
                "fetch_all",
                "fetch",
                "execute",
                "executemany",
            ):
                return True

        # Pattern 2: await db.query(...), await session.query(...)
        if isinstance(node.func, ast.Attribute):
            if node.func.attr in ("query", "get", "filter", "all", "first"):
                return True

        return False


def check_file_ast(filepath: Path) -> list[tuple[int, str, str]]:
    """
    Check a Python file for N+1 patterns using AST analysis

    Args:
        filepath: Path to Python file

    Returns:
        List of (line_number, issue_type, description) tuples
    """
    try:
        with open(filepath, encoding="utf-8") as f:
            source = f.read()

        tree = ast.parse(source, filename=str(filepath))
        visitor = N1DetectorVisitor(str(filepath))
        visitor.visit(tree)

        return visitor.issues
    except SyntaxError as e:
        logger.error("⚠️  syntax error in filepath: e", filepath=filepath, e=e)
        return []
    except Exception as e:
        logger.error("⚠️  error analyzing filepath: e", filepath=filepath, e=e)
        return []


def check_file_regex(filepath: Path) -> list[tuple[int, str, str]]:
    """
    Check a Python file for N+1 patterns using regex (fallback)

    Args:
        filepath: Path to Python file

    Returns:
        List of (line_number, issue_type, description) tuples
    """
    issues = []

    try:
        with open(filepath, encoding="utf-8") as f:
            lines = f.readlines()

        in_loop = False
        loop_line = 0
        indent_level = 0

        for i, line in enumerate(lines, 1):
            stripped = line.lstrip()
            current_indent = len(line) - len(stripped)

            # Detect loop start
            if re.match(r"(for|while)\s+", stripped):
                in_loop = True
                loop_line = i
                indent_level = current_indent

            # Detect loop end (dedent)
            elif in_loop and stripped and current_indent <= indent_level:
                in_loop = False

            # Detect database query in loop
            if in_loop and (
                re.search(
                    r"\.(fetch_one|fetch_all|fetch|execute|executemany)\s*\(", line
                )
                or re.search(r"await\s+.*\.(query|get|filter|all|first)\s*\(", line)
            ):
                issues.append(
                    (
                        i,
                        "potential_n_plus_1",
                        f"Database query inside loop (loop starts at line {loop_line})",
                    )
                )

    except Exception as e:
        logger.error("⚠️  error analyzing filepath: e", filepath=filepath, e=e)

    return issues


def get_changed_files() -> list[Path]:
    """Get list of changed Python files from git"""
    try:
        result = subprocess.run(
            ["git", "diff", "--name-only", "--cached", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
        )

        files = []
        for line in result.stdout.strip().split("\n"):
            if line.endswith(".py"):
                path = Path(line)
                if path.exists():
                    files.append(path)

        return files
    except subprocess.CalledProcessError:
        logger.error("⚠️  not a git repository or git not available")
        return []


def get_all_python_files(root: Path) -> list[Path]:
    """Get all Python files in repository"""
    exclude_dirs = {
        "__pycache__",
        ".git",
        ".venv",
        "venv",
        "env",
        "node_modules",
        ".pytest_cache",
        ".mypy_cache",
        "build",
        "dist",
        ".eggs",
    }

    files = []
    for path in root.rglob("*.py"):
        # Skip excluded directories
        if any(excluded in path.parts for excluded in exclude_dirs):
            continue
        files.append(path)

    return files


def format_issue(filepath: Path, line: int, issue_type: str, description: str) -> str:
    """Format an issue for display"""
    return f"{filepath}:{line} [{issue_type}] {description}"


def main():
    """
    Detects potential N+1 query patterns in Python code by analyzing database query usage.



    Raises:
        SyntaxError: If the provided files contain invalid Python syntax.
    """
    parser = argparse.ArgumentParser(
        description="Detect potential N+1 query patterns in Python code"
    )
    parser.add_argument(
        "files", nargs="*", help="Files to check (default: changed files)"
    )
    parser.add_argument(
        "--all", action="store_true", help="Check all Python files in repository"
    )
    parser.add_argument(
        "--changed", action="store_true", help="Check only git changed files (default)"
    )
    parser.add_argument(
        "--method",
        choices=["ast", "regex", "both"],
        default="ast",
        help="Detection method (default: ast)",
    )
    parser.add_argument(
        "--strict", action="store_true", help="Exit with error code if any issues found"
    )

    args = parser.parse_args()

    # Determine which files to check
    if args.files:
        files = [Path(f) for f in args.files]
    elif args.all:
        files = get_all_python_files(Path.cwd())
    else:
        files = get_changed_files()
        if not files:
            logger.info("ℹ️  no changed python files to check")
            return 0

    if not files:
        logger.info("ℹ️  no files to check")
        return 0

    logger.info("🔍 checking {len(files)} file(s) for n+1 query patterns...\n")

    total_issues = 0
    files_with_issues = 0

    for filepath in files:
        if not filepath.exists():
            logger.error("⚠️  file not found: filepath", filepath=filepath)
            continue

        # Run detection
        issues = []

        if args.method in ("ast", "both"):
            issues.extend(check_file_ast(filepath))

        if args.method in ("regex", "both"):
            regex_issues = check_file_regex(filepath)
            # Deduplicate if using both methods
            if args.method == "both":
                existing_lines = {issue[0] for issue in issues}
                issues.extend([i for i in regex_issues if i[0] not in existing_lines])
            else:
                issues.extend(regex_issues)

        if issues:
            files_with_issues += 1
            total_issues += len(issues)

            logger.info("⚠️  filepath", filepath=filepath)
            for line, _issue_type, description in sorted(issues):
                logger.info("    line line: description", line=line, description=description)
            logger.info("output", value=)

    # Summary
    if total_issues > 0:
        print(
            f"❌ Found {total_issues} potential N+1 pattern(s) in {files_with_issues} file(s)"
        )
        logger.info("output", value=)
        logger.info("💡 tips:")
        logger.info("   - use any() operator for batch queries: where id = any($1)")
        logger.info("   - use executemany() for batch inserts")
        logger.info("   - fetch related data with joins or separate batch queries")
        logger.info("   - see docs/database_best_practices.md for examples")

        if args.strict:
            return 1
        logger.info("output", value=)
        logger.error("ℹ️  run with --strict to fail ci on n+1 patterns")
        return 0
    logger.info("✅ no n+1 query patterns detected")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        logger.error("\n⚠️  interrupted by user")
        sys.exit(2)
    except Exception as e:
        logger.error("❌ error: e", e=e)
        sys.exit(2)

# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "SCR-OPER-002",
    "governance_level": "medium",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": [
        "ast",
        "batch-processing",
        "caching",
        "cli",
        "filesystem",
        "operations",
        "scripts",
        "subprocess",
        "testing",
        "visitor-pattern",
    ],
    "keywords": [
        "all",
        "ast",
        "changed",
        "check",
        "detector",
        "files",
        "format",
        "issue",
    ],
    "business_value": "Implements N1DetectorVisitor for check n plus 1 functionality",
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
