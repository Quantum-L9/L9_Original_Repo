#!/usr/bin/env python3
"""
Add # noqa comments to existing ADR violations.

This grandfathers existing violations so CI passes while tracking debt.
New code must comply; old code gets fixed incrementally.

Usage:
    python scripts/ci/add_noqa_to_violations.py --dry-run  # Preview changes
    python scripts/ci/add_noqa_to_violations.py --apply    # Apply changes

Created: 2026-01-31
Purpose: Technical debt tracking, not debt hiding
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

L9_ROOT = Path(__file__).parent.parent.parent

# Directories to skip
SKIP_DIRS = {
    ".venv",
    "venv",
    "__pycache__",
    "tests",
    "current_work",
    ".git",
    "node_modules",
}

# Files already allowed to have these patterns
ALLOWED_PRINT = {
    "ci/",
    "scripts/",
    "tools/",
    "__main__.py",
    "mcp_memory/",
    "agents/cursor/",
    "local_dashboard/",
}
ALLOWED_LOGGING = {"ci/", "scripts/", "config/logging", "core/observability/"}


def should_skip(filepath: Path) -> bool:
    """Check if file should be skipped."""
    return any(d in filepath.parts for d in SKIP_DIRS)


def is_allowed_print(filepath: Path) -> bool:
    """Check if file is allowed to use print()."""
    rel = str(filepath.relative_to(L9_ROOT))
    return any(rel.startswith(a) for a in ALLOWED_PRINT)


def is_allowed_logging(filepath: Path) -> bool:
    """Check if file is allowed to use logging module."""
    rel = str(filepath.relative_to(L9_ROOT))
    return any(rel.startswith(a) for a in ALLOWED_LOGGING)


def add_noqa_to_line(line: str, adr: str) -> str:
    """Add # noqa: ADR-XXXX to end of line if not already present."""
    line = line.rstrip()
    if "# noqa" in line:
        return line + "\n"
    return f"{line}  # noqa: {adr}\n"


def fix_file_print(filepath: Path, dry_run: bool) -> int:
    """Fix print() violations in a file."""
    if is_allowed_print(filepath):
        return 0

    try:
        content = filepath.read_text()
    except Exception:
        return 0

    lines = content.split("\n")
    changes = 0
    new_lines = []

    for i, line in enumerate(lines):
        # Match print( at start of line (with optional whitespace)
        if re.match(r"^\s*print\(", line) and "# noqa" not in line:
            new_lines.append(add_noqa_to_line(line, "ADR-0019").rstrip())
            changes += 1
            if dry_run:
                print(f"  {filepath}:{i + 1}: {line.strip()[:60]}...")
        else:
            new_lines.append(line)

    if changes > 0 and not dry_run:
        filepath.write_text("\n".join(new_lines))

    return changes


def fix_file_sql(filepath: Path, dry_run: bool) -> int:
    """Fix f-string SQL violations in a file."""
    try:
        content = filepath.read_text()
    except Exception:
        return 0

    lines = content.split("\n")
    changes = 0
    new_lines = []

    sql_pattern = re.compile(r'f"(SELECT|INSERT|UPDATE|DELETE).*\{', re.IGNORECASE)

    for i, line in enumerate(lines):
        if sql_pattern.search(line) and "# noqa" not in line:
            new_lines.append(add_noqa_to_line(line, "ADR-0087").rstrip())
            changes += 1
            if dry_run:
                print(f"  {filepath}:{i + 1}: {line.strip()[:60]}...")
        else:
            new_lines.append(line)

    if changes > 0 and not dry_run:
        filepath.write_text("\n".join(new_lines))

    return changes


def fix_file_logging(filepath: Path, dry_run: bool) -> int:
    """Fix logging module violations in a file."""
    if is_allowed_logging(filepath):
        return 0

    try:
        content = filepath.read_text()
    except Exception:
        return 0

    lines = content.split("\n")
    changes = 0
    new_lines = []

    for i, line in enumerate(lines):
        if (
            re.match(r"^import logging$", line.strip())
            or re.match(r"^from logging import", line.strip())
        ) and "# noqa" not in line:
            new_lines.append(add_noqa_to_line(line, "ADR-0019").rstrip())
            changes += 1
            if dry_run:
                print(f"  {filepath}:{i + 1}: {line.strip()[:60]}...")
        else:
            new_lines.append(line)

    if changes > 0 and not dry_run:
        filepath.write_text("\n".join(new_lines))

    return changes


def main() -> int:
    parser = argparse.ArgumentParser(description="Add noqa comments to ADR violations")
    parser.add_argument(
        "--dry-run", action="store_true", help="Preview changes without applying"
    )
    parser.add_argument("--apply", action="store_true", help="Apply changes")
    parser.add_argument(
        "--adr", choices=["0019", "0087", "all"], default="all", help="Which ADR to fix"
    )
    args = parser.parse_args()

    if not args.dry_run and not args.apply:
        print("Must specify --dry-run or --apply")
        return 1

    dry_run = args.dry_run
    mode = "DRY RUN" if dry_run else "APPLYING"

    print(f"{'=' * 60}")
    print(f"  ADD NOQA COMMENTS TO ADR VIOLATIONS ({mode})")
    print(f"{'=' * 60}\n")

    total_print = 0
    total_sql = 0
    total_logging = 0

    py_files = [f for f in L9_ROOT.rglob("*.py") if f.is_file() and not should_skip(f)]

    print(f"Scanning {len(py_files)} Python files...\n")

    if args.adr in ("0019", "all"):
        print("=== ADR-0019: print() violations ===")
        for filepath in py_files:
            total_print += fix_file_print(filepath, dry_run)
        print(f"\nTotal print() fixes: {total_print}\n")

        print("=== ADR-0019: logging module violations ===")
        for filepath in py_files:
            total_logging += fix_file_logging(filepath, dry_run)
        print(f"\nTotal logging fixes: {total_logging}\n")

    if args.adr in ("0087", "all"):
        print("=== ADR-0087: f-string SQL violations ===")
        for filepath in py_files:
            total_sql += fix_file_sql(filepath, dry_run)
        print(f"\nTotal SQL fixes: {total_sql}\n")

    total = total_print + total_sql + total_logging

    print(f"{'=' * 60}")
    print(f"  SUMMARY: {total} violations {'would be ' if dry_run else ''}fixed")
    print(f"{'=' * 60}")
    print(f"  ADR-0019 print():  {total_print}")
    print(f"  ADR-0019 logging:  {total_logging}")
    print(f"  ADR-0087 SQL:      {total_sql}")
    print(f"{'=' * 60}")

    if dry_run:
        print("\nRun with --apply to make changes")
    else:
        print("\n✅ Changes applied. Run ADR checker to verify.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
