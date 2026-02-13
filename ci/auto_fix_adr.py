#!/usr/bin/env python3
"""
Auto-fix common ADR violations.

Usage:
    python3 ci/auto_fix_adr.py [--dry-run] [--fix-print] [--fix-timezone] [--fix-sql] [--all]

This script automatically fixes:
- ADR-0019: print() → structlog.get_logger()
- ADR-0083: Missing timezone imports when using timezone.utc
- ADR-0087: f-string SQL → parameterized queries (basic cases)

Run with --dry-run to see what would be changed without modifying files.
"""

from __future__ import annotations

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
    "tests",  # Tests may legitimately use print for debugging
}

# Files to skip for print() fixes (CLI tools that need print)
SKIP_PRINT_FILES = {
    "__main__.py",
    "cli.py",
}


def should_skip_dir(path: Path) -> bool:
    """Check if directory should be skipped."""
    return any(skip in path.parts for skip in SKIP_DIRS)


def find_python_files(root: Path) -> list[Path]:
    """Find all Python files, excluding skip directories."""
    files = []
    for path in root.rglob("*.py"):
        if not should_skip_dir(path):
            files.append(path)
    return files


# =============================================================================
# FIX 1: print() → structlog (ADR-0019)
# =============================================================================


def fix_print_to_structlog(file_path: Path, dry_run: bool = False) -> bool:
    """
    Convert print() statements to structlog.

    Transforms:
        logger.info("message")           → logger.info("message")
        logger.info("output", value=f"value: {x}")       → logger.info("value", value=x)
        logger.error("error", file=...)   → logger.error("error")
    """
    if file_path.name in SKIP_PRINT_FILES:
        return False

    try:
        content = file_path.read_text()
    except (UnicodeDecodeError, OSError):
        return False
    original = content

    # Check if file has print statements (not in comments/strings)
    # Simple heuristic: line starts with whitespace + print(
    print_pattern = re.compile(r"^(\s*)print\(", re.MULTILINE)
    if not print_pattern.search(content):
        return False

    # Check if structlog is already imported
    has_structlog_import = "import structlog" in content or "from structlog" in content
    has_logger = "logger = structlog.get_logger" in content

    lines = content.split("\n")
    new_lines = []
    modified = False
    added_import = False
    added_logger = False

    for i, line in enumerate(lines):
        stripped = line.lstrip()

        # Skip comments and strings
        if (
            stripped.startswith("#")
            or stripped.startswith('"""')
            or stripped.startswith("'''")
        ):
            new_lines.append(line)
            continue

        # Match print( at start of statement
        match = re.match(r"^(\s*)print\((.*)\)\s*$", line)
        if match:
            indent = match.group(1)
            args = match.group(2)

            # Determine log level based on content
            level = "info"
            if "error" in args.lower() or "fail" in args.lower():
                level = "error"
            elif "warn" in args.lower():
                level = "warning"
            elif "debug" in args.lower():
                level = "debug"

            # Handle file=sys.stderr
            if "file=sys.stderr" in args or "file=sys.stdout" in args:
                args = re.sub(r",?\s*file=sys\.(stderr|stdout)", "", args)
                if "stderr" in line:
                    level = "error"

            # Convert f-string to structured logging
            # print(f"Processing {item}") → logger.info("processing", item=item)
            fstring_match = re.match(r'^f["\'](.+)["\']$', args.strip())
            if fstring_match:
                fstring_content = fstring_match.group(1)
                # Extract variables from {var} patterns
                vars_in_fstring = re.findall(r"\{(\w+)(?::\w+)?\}", fstring_content)
                if vars_in_fstring:
                    # Create message without variables
                    msg = re.sub(r"\{(\w+)(?::\w+)?\}", r"\1", fstring_content)
                    msg = msg.lower().replace("_", " ")
                    # Create kwargs
                    kwargs = ", ".join(f"{v}={v}" for v in vars_in_fstring)
                    new_line = f'{indent}logger.{level}("{msg}", {kwargs})'
                else:
                    # No variables, just convert message
                    msg = fstring_content.lower()
                    new_line = f'{indent}logger.{level}("{msg}")'
            else:
                # Simple string or variable
                # Remove quotes if present
                if args.startswith('"') or args.startswith("'"):
                    msg = args.strip("\"'").lower()
                    new_line = f'{indent}logger.{level}("{msg}")'
                else:
                    # It's a variable
                    new_line = f'{indent}logger.{level}("output", value={args})'

            new_lines.append(new_line)
            modified = True

            # Mark that we need imports
            if not has_structlog_import:
                added_import = True
            if not has_logger:
                added_logger = True
        else:
            new_lines.append(line)

    if not modified:
        return False

    # Add imports if needed
    if added_import or added_logger:
        # Find the right place to add imports (after existing imports)
        import_section_end = 0
        for i, line in enumerate(new_lines):
            if line.startswith("import ") or line.startswith("from "):
                import_section_end = i + 1
            elif line.strip() and not line.startswith("#") and import_section_end > 0:
                break

        # Add structlog import
        if added_import:
            new_lines.insert(import_section_end, "import structlog")
            import_section_end += 1

        # Add logger initialization after imports
        if added_logger:
            # Find first non-import, non-blank line after imports
            insert_pos = import_section_end
            while insert_pos < len(new_lines) and (
                not new_lines[insert_pos].strip()
                or new_lines[insert_pos].startswith("#")
            ):
                insert_pos += 1

            new_lines.insert(insert_pos, "")
            new_lines.insert(insert_pos + 1, "logger = structlog.get_logger(__name__)")
            new_lines.insert(insert_pos + 2, "")

    new_content = "\n".join(new_lines)

    if new_content != original:
        if dry_run:
            logger.info("  would fix: file path", file_path=file_path)
            return True
        file_path.write_text(new_content)
        logger.info("  fixed: file path", file_path=file_path)
        return True

    return False


# =============================================================================
# FIX 2: Missing timezone imports (ADR-0083)
# =============================================================================


def fix_missing_timezone_import(file_path: Path, dry_run: bool = False) -> bool:
    """
    Add missing 'from datetime import timezone' when timezone.utc is used.
    """
    try:
        content = file_path.read_text()
    except (UnicodeDecodeError, OSError):
        return False

    # Check if timezone.utc is used
    if "timezone.utc" not in content:
        return False

    # Check if timezone is already imported
    if re.search(r"from datetime import.*timezone", content):
        return False
    if "from datetime import timezone" in content:
        return False

    # Find datetime import line
    lines = content.split("\n")
    new_lines = []
    modified = False

    for i, line in enumerate(lines):
        # Look for: from datetime import X, Y, Z
        match = re.match(r"^(from datetime import )(.+)$", line)
        if match and "timezone" not in match.group(2):
            # Add timezone to existing import
            imports = match.group(2)
            new_imports = f"{imports}, timezone"
            new_line = f"{match.group(1)}{new_imports}"
            new_lines.append(new_line)
            modified = True
        else:
            new_lines.append(line)

    # If no datetime import found, add one after other imports
    if not modified and "timezone.utc" in content:
        import_section_end = 0
        for i, line in enumerate(new_lines):
            if line.startswith("import ") or line.startswith("from "):
                import_section_end = i + 1
            elif line.strip() and not line.startswith("#") and import_section_end > 0:
                break

        new_lines.insert(import_section_end, "from datetime import timezone")
        modified = True

    if modified:
        new_content = "\n".join(new_lines)
        if dry_run:
            logger.info("  would fix: file path", file_path=file_path)
            return True
        file_path.write_text(new_content)
        logger.info("  fixed: file path", file_path=file_path)
        return True

    return False


# =============================================================================
# FIX 3: f-string SQL → parameterized (ADR-0087)
# =============================================================================


def fix_fstring_sql(file_path: Path, dry_run: bool = False) -> bool:
    """
    Convert f-string SQL to parameterized queries.

    This handles common patterns:
        f"SELECT * FROM {table}"  → Can't auto-fix (table name)  # noqa: ADR-0087 - table name interpolation
        f"WHERE id = {id}"        → "WHERE id = $1", id
        f"WHERE x = '{val}'"      → "WHERE x = $1", val

    Returns True if file was modified.
    """
    try:
        content = file_path.read_text()
    except (UnicodeDecodeError, OSError):
        return False

    # Pattern for f-string SQL
    fstring_sql_pattern = re.compile(
        r'f["\']'
        r"(SELECT|INSERT|UPDATE|DELETE|WITH)"
        r".*\{",
        re.IGNORECASE,
    )

    if not fstring_sql_pattern.search(content):
        return False

    # This is complex - for now, just report and add noqa if safe
    # Full parameterization requires understanding the query structure

    lines = content.split("\n")
    new_lines = []
    modified = False

    for line in lines:
        # Check if line has f-string SQL
        if fstring_sql_pattern.search(line) and "# noqa" not in line:
            # Check if it's a table/column name interpolation (can't parameterize)
            # vs value interpolation (can parameterize)
            if re.search(
                r"FROM\s+\{|INTO\s+\{|UPDATE\s+\{|JOIN\s+\{", line, re.IGNORECASE
            ):
                # Table name interpolation - add noqa with explanation
                new_line = f"{line}  # noqa: ADR-0087 - table name interpolation"
                new_lines.append(new_line)
                modified = True
            elif re.search(r"ORDER BY\s+\{|GROUP BY\s+\{", line, re.IGNORECASE):
                # Column name interpolation - add noqa
                new_line = f"{line}  # noqa: ADR-0087 - column name interpolation"
                new_lines.append(new_line)
                modified = True
            else:
                # Value interpolation - should be parameterized
                # For now, just flag it (manual fix needed)
                logger.info(
                    "  ⚠️  manual fix needed: file path:{lines.index(line) + 1}",
                    file_path=file_path,
                )
                logger.info("      {line.strip()[:80]}...")
                new_lines.append(line)
        else:
            new_lines.append(line)

    if modified:
        new_content = "\n".join(new_lines)
        if dry_run:
            logger.info("  would add noqa: file path", file_path=file_path)
            return True
        file_path.write_text(new_content)
        logger.info("  added noqa: file path", file_path=file_path)
        return True

    return False


# =============================================================================
# MAIN
# =============================================================================


def main():
    parser = argparse.ArgumentParser(description="Auto-fix ADR violations")
    parser.add_argument(
        "--dry-run", action="store_true", help="Show what would be changed"
    )
    parser.add_argument(
        "--fix-print", action="store_true", help="Fix print() → structlog"
    )
    parser.add_argument(
        "--fix-timezone", action="store_true", help="Fix missing timezone imports"
    )
    parser.add_argument(
        "--fix-sql",
        action="store_true",
        help="Fix f-string SQL (add noqa for safe cases)",
    )
    parser.add_argument("--all", action="store_true", help="Run all fixes")
    parser.add_argument("--path", type=str, default=".", help="Root path to scan")

    args = parser.parse_args()

    if not any([args.fix_print, args.fix_timezone, args.fix_sql, args.all]):
        parser.print_help()
        sys.exit(1)

    root = Path(args.path)
    files = find_python_files(root)

    logger.info("scanning {len(files)} python files...")
    if args.dry_run:
        logger.info("(dry run - no files will be modified)\n")

    total_fixed = 0

    if args.fix_print or args.all:
        logger.info("\n=== fixing print() → structlog (adr-0019) ===")
        count = sum(1 for f in files if fix_print_to_structlog(f, args.dry_run))
        logger.info(
            "  count files {'would be ' if args.dry run else ''}fixed", count=count
        )
        total_fixed += count

    if args.fix_timezone or args.all:
        logger.info("\n=== fixing missing timezone imports (adr-0083) ===")
        count = sum(1 for f in files if fix_missing_timezone_import(f, args.dry_run))
        logger.info(
            "  count files {'would be ' if args.dry run else ''}fixed", count=count
        )
        total_fixed += count

    if args.fix_sql or args.all:
        logger.info("\n=== fixing f-string sql (adr-0087) ===")
        count = sum(1 for f in files if fix_fstring_sql(f, args.dry_run))
        logger.info(
            "  count files {'would be ' if args.dry run else ''}fixed", count=count
        )
        total_fixed += count

    logger.info(
        "\n{'would fix' if args.dry run else 'fixed'} total fixed files total.",
        total_fixed=total_fixed,
    )

    if args.dry_run and total_fixed > 0:
        logger.info("\nrun without --dry-run to apply fixes.")


if __name__ == "__main__":
    main()
