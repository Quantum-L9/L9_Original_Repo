#!/usr/bin/env python3
"""
L9 CI Check — noqa Comment Placement Validator
==============================================

Prevents the "noqa-inside-string" bug where # noqa comments are accidentally
placed inside string literals instead of at the end of the line.

This bug was introduced by auto-fixers that incorrectly added noqa comments
inside f-strings, causing SQL injection vulnerabilities to be hidden AND
the noqa to not actually suppress the warning.

Example of the bug:
    WRONG:  query = f"SELECT * FROM {table}  # noqa: ADR-0087"
    RIGHT:  query = f"SELECT * FROM {table}"  # noqa: ADR-0087

Usage:
    python3 ci/check_noqa_placement.py              # Check all files
    python3 ci/check_noqa_placement.py path/to/file.py  # Check specific file
    python3 ci/check_noqa_placement.py --verbose    # Show all checked files

Exit codes:
    0 = All files pass
    1 = Violations found
"""

from __future__ import annotations

# ============================================================================
__dora_meta__ = {
    "component_name": "Check noqa Placement",
    "module_version": "1.0.0",
    "created_by": "L9 Agent",
    "created_at": "2026-02-13T00:00:00Z",
    "updated_at": "2026-02-13T00:00:00Z",
    "layer": "operations",
    "domain": "ci",
    "module_name": "check_noqa_placement",
    "type": "service",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": [],
        "memory_layers": [],
        "imported_by": ["ci.auto_fix_adr"],
    },
}
# ============================================================================

import argparse
import re
import sys
from pathlib import Path

# Directories to skip
SKIP_DIRS = {
    ".venv",
    "venv",
    ".git",
    "__pycache__",
    "node_modules",
    "_archived",
    ".backup",
    "current_work",
    ".cursor",
}


def should_skip(path: Path) -> bool:
    """Check if path should be skipped."""
    return any(skip in path.parts for skip in SKIP_DIRS)


def find_python_files(root: Path) -> list[Path]:
    """Find all Python files to check."""
    files = []
    for py_file in root.rglob("*.py"):
        if not should_skip(py_file):
            files.append(py_file)
    return sorted(files)


def check_noqa_in_string(file_path: Path) -> list[tuple[int, str, str]]:
    """
    Check if # noqa comments appear inside SQL f-strings IN A WAY THAT'S A BUG.

    We're looking for the specific bug pattern where an auto-fixer incorrectly
    placed a noqa comment inside an f-string SQL query.

    BUG pattern (what we catch):
        query = f"SELECT * FROM {table}  # noqa: ADR-0087"
        ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
        This is an f-string SQL with {interpolation} AND noqa inside the string.
        The noqa won't work and the SQL is corrupted.

    OK patterns (what we ignore):
        new_line = f"{line}  # noqa: ADR-0019"  # Building code (not SQL)
        test_file.write_text('x = 1  # noqa: ADR-0019')  # Test data
        if "# noqa" not in line:  # Checking for noqa presence

    Returns list of (line_number, line_content, issue_description).
    """
    try:
        content = file_path.read_text()
    except (UnicodeDecodeError, OSError):
        return []

    issues = []
    lines = content.split("\n")

    # Skip certain file types entirely (test files, documentation, CI tools)
    path_str = str(file_path)
    file_name = file_path.name

    # Skip test files (in tests/ directory or named test_*.py or *_test.py)
    if (
        "/tests/" in path_str
        or file_name.startswith("test_")
        or file_name.endswith("_test.py")
    ):
        return []

    # Skip documentation and examples
    if "/docs/" in path_str or "/examples/" in path_str:
        return []

    # Skip CI tools that legitimately construct noqa strings
    skip_files = [
        "ci/auto_fix_adr.py",
        "ci/check_noqa_placement.py",
        "ci/check_adr_compliance.py",
    ]
    if any(path_str.endswith(skip) for skip in skip_files):
        return []

    # Skip scripts/ci/ directory
    if "/scripts/ci/" in path_str:
        return []

    # SQL keywords that indicate this is a database query
    sql_keywords = ["SELECT", "INSERT", "UPDATE", "DELETE", "CREATE", "DROP", "ALTER"]

    for i, line in enumerate(lines, 1):
        # Skip lines without noqa
        if "# noqa" not in line:
            continue

        # Skip lines that are clearly checking for noqa presence
        if re.search(r'["\']#\s*noqa["\']', line):
            continue
        if re.search(r'\.find\(["\']#\s*noqa', line):
            continue
        if "in line" in line and "noqa" in line:
            continue

        # Skip docstrings
        stripped = line.strip()
        if stripped.startswith('"""') or stripped.startswith("'''"):
            continue

        # THE ACTUAL BUG PATTERN:
        # f-string SQL query with {interpolation} AND noqa inside the string
        # Pattern: f"SELECT...{var}...# noqa..." or f"INSERT...{var}...# noqa..."

        for sql_keyword in sql_keywords:
            # Check for f-string SQL with interpolation that has noqa inside
            # This pattern matches: f"SELECT...{table}...# noqa..."
            # Using raw string with explicit quote class to avoid escaping issues
            pattern = rf"""f["'][^"']*{sql_keyword}[^"']*\{{[^}}]+\}}[^"']*#\s*noqa[^"']*["']"""
            fstring_sql_bug = re.compile(pattern, re.IGNORECASE)

            if fstring_sql_bug.search(line):
                # Make sure there's no proper noqa AFTER the string
                match = fstring_sql_bug.search(line)
                if match:
                    after_match = line[match.end() :]
                    if "# noqa" not in after_match:
                        issues.append(
                            (
                                i,
                                line.strip(),
                                f"noqa inside f-string SQL ({sql_keyword}) — corrupts query, noqa won't work",
                            )
                        )
                        break  # Don't report same line multiple times

        # Also check triple-quoted f-string SQL
        for sql_keyword in sql_keywords:
            pattern = rf'f"""[^"]*{sql_keyword}[^"]*\{{[^}}]+\}}[^"]*#\s*noqa[^"]*"""'
            triple_sql_bug = re.compile(pattern, re.IGNORECASE)
            if triple_sql_bug.search(line):
                issues.append(
                    (
                        i,
                        line.strip(),
                        f"noqa inside triple-quoted f-string SQL ({sql_keyword})",
                    )
                )
                break

    return issues


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Check that # noqa comments are not inside string literals",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python3 ci/check_noqa_placement.py              # Check all files
    python3 ci/check_noqa_placement.py core/        # Check specific directory
    python3 ci/check_noqa_placement.py file.py      # Check specific file

This check prevents the "noqa-inside-string" bug where auto-fixers
accidentally place # noqa comments inside f-strings or other string literals.

Example of the bug:
    WRONG:  query = f"SELECT * FROM {table}  # noqa: ADR-0087"
    RIGHT:  query = f"SELECT * FROM {table}"  # noqa: ADR-0087
        """,
    )
    parser.add_argument(
        "paths",
        nargs="*",
        default=["."],
        help="Files or directories to check (default: current directory)",
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Show all checked files"
    )

    args = parser.parse_args()

    # Collect files to check
    files_to_check = []
    for path_str in args.paths:
        path = Path(path_str)
        if path.is_file() and path.suffix == ".py":
            files_to_check.append(path)
        elif path.is_dir():
            files_to_check.extend(find_python_files(path))

    if not files_to_check:
        print("No Python files found to check.")  # noqa: ADR-0019
        return 0

    if args.verbose:
        print(f"Checking {len(files_to_check)} Python files...")  # noqa: ADR-0019

    all_issues = []

    for file_path in files_to_check:
        issues = check_noqa_in_string(file_path)
        if issues:
            all_issues.extend([(file_path, *issue) for issue in issues])

    if not all_issues:
        print(f"✅ All {len(files_to_check)} files pass noqa placement check")  # noqa: ADR-0019
        return 0

    # Report issues
    print(f"❌ Found {len(all_issues)} noqa-inside-string violation(s):\n")  # noqa: ADR-0019

    for file_path, line_num, line_content, description in all_issues:
        print(f"{file_path}:{line_num}: {description}")  # noqa: ADR-0019
        print(f"    {line_content}")  # noqa: ADR-0019
        print()  # noqa: ADR-0019

    print("Fix: Move # noqa comment to END of line, OUTSIDE the string literal")  # noqa: ADR-0019
    print('  WRONG:  f"SELECT * FROM {table}  # noqa: ADR-0087"')  # noqa: ADR-0019
    print('  RIGHT:  f"SELECT * FROM {table}"  # noqa: ADR-0087')  # noqa: ADR-0019

    return 1


if __name__ == "__main__":
    sys.exit(main())
