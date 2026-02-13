#!/usr/bin/env python3
"""
Fix timezone imports across the L9 codebase.

Resolves: NameError: name 'timezone' is not defined

This script adds 'timezone' to datetime imports where it's missing
but the code uses datetime.now(timezone.utc) or similar.
"""

# ============================================================================
__dora_meta__ = {
    "component_name": "Fix Timezone Imports",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2026-01-31T08:57:02Z",
    "updated_at": "2026-01-31T22:21:56Z",
    "layer": "operations",
    "domain": "scripts",
    "module_name": "fix_timezone_imports",
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

import re
from pathlib import Path

import structlog

logger = structlog.get_logger(__name__)

L9_ROOT = Path(__file__).parent.parent

# Patterns to match and fix
PATTERNS = [
    # from datetime import datetime -> from datetime import datetime, timezone
    (r"^(\s*from datetime import datetime)(\s*)$", r"\1, timezone\2"),
    # from datetime import datetime, timedelta -> from datetime import datetime, timezone, timedelta
    (r"^(\s*from datetime import datetime), (timedelta\s*)$", r"\1, timezone, \2"),
    # from datetime import datetime, timedelta, X -> from datetime import datetime, timezone, timedelta, X
    (r"^(\s*from datetime import datetime), (timedelta,)", r"\1, timezone, \2"),
    # from datetime import timedelta, datetime -> from datetime import timedelta, datetime, timezone
    (r"^(\s*from datetime import timedelta, datetime)(\s*)$", r"\1, timezone\2"),
]

# Skip patterns - files that already have timezone
SKIP_PATTERNS = [
    r"from datetime import.*timezone",
    r"from datetime import datetime, timezone",
]

# Directories to skip
SKIP_DIRS = {
    ".git",
    ".venv",
    "venv",
    "__pycache__",
    "node_modules",
    ".pytest_cache",
    ".mypy_cache",
    "analysis_reports",
}


def should_skip_file(filepath: Path) -> bool:
    """Check if file should be skipped."""
    for part in filepath.parts:
        if part in SKIP_DIRS:
            return True
    return False


def file_already_has_timezone(content: str) -> bool:
    """Check if file already imports timezone."""
    for pattern in SKIP_PATTERNS:
        if re.search(pattern, content, re.MULTILINE):
            return True
    return False


def file_uses_timezone(content: str) -> bool:
    """Check if file uses timezone (e.g., timezone.utc)."""
    return "timezone.utc" in content or "timezone(" in content


def fix_file(filepath: Path, dry_run: bool = False) -> tuple[bool, str]:
    """
    Fix timezone import in a single file.

    Returns: (was_modified, reason)
    """
    try:
        content = filepath.read_text()
    except Exception as e:
        return False, f"Error reading: {e}"

    # Skip if already has timezone import
    if file_already_has_timezone(content):
        return False, "Already has timezone"

    # Check if file needs the fix (uses timezone but doesn't import it)
    needs_fix = file_uses_timezone(content)

    # Also check for datetime import without timezone
    has_datetime_import = bool(re.search(r"from datetime import datetime", content))

    if not has_datetime_import:
        return False, "No datetime import"

    # Apply fixes
    new_content = content
    modified = False

    for pattern, replacement in PATTERNS:
        new_content, count = re.subn(
            pattern, replacement, new_content, flags=re.MULTILINE
        )
        if count > 0:
            modified = True

    if not modified:
        return False, "No matching pattern"

    if dry_run:
        return True, "Would fix (dry run)"

    # Write back
    try:
        filepath.write_text(new_content)
        return True, "Fixed"
    except Exception as e:
        return False, f"Error writing: {e}"


def main():
    """
    Performs argument parsing and initiates the process to fix missing 'timezone' imports in the L9 codebase.



    Raises:
        argparse.ArgumentError: If argument parsing encounters an error.
    """
    import argparse

    parser = argparse.ArgumentParser(description="Fix timezone imports in L9 codebase")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be changed without making changes",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Show all files, not just modified ones",
    )
    args = parser.parse_args()

    print(
        f"{'[DRY RUN] ' if args.dry_run else ''}Scanning L9 codebase for timezone import fixes..."
    )
    logger.info("root: l9 root\n", L9_ROOT=L9_ROOT)

    fixed = []
    skipped = []
    errors = []

    for filepath in sorted(L9_ROOT.rglob("*.py")):
        if not filepath.is_file():
            continue  # Skip directories that happen to end in .py
        if should_skip_file(filepath):
            continue

        rel_path = filepath.relative_to(L9_ROOT)
        was_modified, reason = fix_file(filepath, dry_run=args.dry_run)

        if was_modified:
            fixed.append((rel_path, reason))
            logger.info("✅ rel path", rel_path=rel_path)
        elif "Error" in reason:
            errors.append((rel_path, reason))
            logger.info("❌ rel path: reason", rel_path=rel_path, reason=reason)
        elif args.verbose:
            skipped.append((rel_path, reason))
            logger.info("⏭️  rel path: reason", rel_path=rel_path, reason=reason)

    # Summary
    logger.info("\n{'=' * 60}")
    logger.info("summary {'(dry run)' if args.dry_run else ''}")
    logger.info("{'=' * 60}")
    logger.info("fixed:   {len(fixed)} files")
    logger.info("skipped: {len(skipped)} files")
    logger.error("errors:  {len(errors)} files")

    if fixed and not args.dry_run:
        logger.info("\n✅ {len(fixed)} files have been updated with timezone import.")
        logger.info("run tests to verify: pytest tests/ -x")
    elif fixed and args.dry_run:
        print(
            f"\n🔍 {len(fixed)} files would be updated. Run without --dry-run to apply."
        )


if __name__ == "__main__":
    main()
# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "SCR-OPER-005",
    "governance_level": "medium",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": ["caching", "cli", "filesystem", "operations", "scripts", "testing"],
    "keywords": ["already", "fix", "imports", "should", "skip", "timezone", "uses"],
    "business_value": "This script adds 'timezone' to datetime imports where it's missing but the code uses datetime.now(timezone.utc) or similar.",
    "last_modified": "2026-01-31T22:21:56Z",
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
