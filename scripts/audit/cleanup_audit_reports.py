#!/usr/bin/env python3
"""
L9 Audit Report Cleanup Script
==============================

Manages old audit reports in the reports/ directory.
Keeps 1 most recent of EACH report type, deletes the rest.

Actions:
- archive: Move old reports to reports/_archived/
- delete: Permanently delete old reports
- list: Show what would be cleaned up (dry-run)

Report Types (grouped separately):
- dead_code_audit_*     → Dead code audit outputs
- dead_code_baseline*   → Dead code baselines
- dead_code_risk*       → Risk matrices
- dead_code_gmp*        → GMP plans for dead code
- wiring_audit*         → Wiring integrity audits
- audit_run_*           → Generic audit runs
- graph_audit_*         → Graph audits

EXCLUDED (never touched):
- GMP_Report_*          → GMP execution reports
- dead_code_resolved*   → Important baselines

Usage:
    python cleanup_audit_reports.py --action list          # Show what would be deleted
    python cleanup_audit_reports.py --action delete        # Delete old, keep 1 per type
    python cleanup_audit_reports.py --action archive       # Archive old, keep 1 per type
    python cleanup_audit_reports.py --keep 2               # Keep 2 most recent per type
"""

# ============================================================================
__dora_meta__ = {
    "component_name": "Cleanup Audit Reports",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2026-01-14T12:08:12Z",
    "updated_at": "2026-01-14T12:10:12Z",
    "layer": "operations",
    "domain": "scripts",
    "module_name": "cleanup_audit_reports",
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
import shutil
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.parent
REPORTS_DIR = REPO_ROOT / "reports"
ARCHIVE_DIR = REPORTS_DIR / "_archived"

# Report type patterns (order matters - more specific first)
REPORT_TYPES = {
    "dead_code_audit": ["dead_code_audit_*.json", "dead_code_audit_*.md"],
    "dead_code_baseline": ["dead_code_baseline*.json", "dead_code_baseline*.md"],
    "dead_code_risk": ["dead_code_risk*.json", "dead_code_risk*.md"],
    "dead_code_gmp": ["dead_code_gmp*.json", "dead_code_gmp*.md"],
    "wiring_audit": ["wiring_audit*.json", "wiring_audit*.md"],
    "audit_run": ["audit_run_*.json", "audit_run_*.html"],
    "graph_audit": ["graph_audit_*.json", "graph_audit_*.md"],
}

# Files/patterns to NEVER delete
PROTECTED_PATTERNS = [
    "GMP_Report_*",  # GMP execution reports - NEVER delete
    "GMP_*",  # Any GMP file
    "Report_GMP-*",  # Old GMP report format
    "dead_code_resolved*",  # Important baseline
]

# Specific files to always keep
KEEP_FILES = {
    "dead_code_resolved.json",
}


def matches_protected(filename: str) -> bool:
    """Check if filename matches any protected pattern."""
    from fnmatch import fnmatch

    for pattern in PROTECTED_PATTERNS:
        if fnmatch(filename, pattern):
            return True
    return filename in KEEP_FILES


def get_report_type(filepath: Path) -> "str | None":
    """Determine the report type for a file."""
    from fnmatch import fnmatch

    filename = filepath.name

    for report_type, patterns in REPORT_TYPES.items():
        for pattern in patterns:
            if fnmatch(filename, pattern):
                return report_type
    return None


def get_audit_files_by_type() -> "dict[str, list[Path]]":
    """Get all audit report files grouped by type."""
    files_by_type: dict[str, list[Path]] = defaultdict(list)

    for report_type, patterns in REPORT_TYPES.items():
        for pattern in patterns:
            for filepath in REPORTS_DIR.glob(pattern):
                # Skip archived and protected files
                if "_archived" in str(filepath):
                    continue
                if matches_protected(filepath.name):
                    continue
                files_by_type[report_type].append(filepath)

    # Sort each type by modification time (newest first)
    for report_type in files_by_type:
        files_by_type[report_type] = sorted(
            files_by_type[report_type], key=lambda f: f.stat().st_mtime, reverse=True
        )

    return dict(files_by_type)


def get_audit_files() -> list[Path]:
    """Get all audit report files (flat list for backward compat)."""
    files_by_type = get_audit_files_by_type()
    all_files = []
    for files in files_by_type.values():
        all_files.extend(files)
    return sorted(all_files, key=lambda f: f.stat().st_mtime, reverse=True)


def get_file_age_days(filepath: Path) -> float:
    """Get file age in days."""
    mtime = datetime.fromtimestamp(filepath.stat().st_mtime)
    age = datetime.now() - mtime
    return age.total_seconds() / 86400


def format_file_info(filepath: Path) -> str:
    """Format file info for display."""
    size_kb = filepath.stat().st_size / 1024
    mtime = datetime.fromtimestamp(filepath.stat().st_mtime)
    age_days = get_file_age_days(filepath)
    return f"{filepath.name:50} {size_kb:8.1f} KB  {mtime:%Y-%m-%d %H:%M}  ({age_days:.1f}d old)"


def list_files(files: list[Path]) -> None:
    """Display files that would be affected."""
    if not files:
        print("No audit report files found to clean up.")
        return

    print(f"\n📋 Found {len(files)} audit report files:\n")
    print(f"{'Filename':50} {'Size':>10}  {'Modified':16}  {'Age'}")
    print("-" * 90)

    total_size = 0
    for f in files:
        print(format_file_info(f))
        total_size += f.stat().st_size

    print("-" * 90)
    print(f"Total: {len(files)} files, {total_size / 1024:.1f} KB")


def archive_files(files: list[Path], dry_run: bool = False) -> int:
    """Move files to _archived/ directory."""
    if not files:
        print("No files to archive.")
        return 0

    if not dry_run:
        ARCHIVE_DIR.mkdir(exist_ok=True)

    archived = 0
    for f in files:
        dest = ARCHIVE_DIR / f.name
        if dry_run:
            print(f"  Would archive: {f.name}")
        else:
            # Handle name collision
            if dest.exists():
                stem = dest.stem
                suffix = dest.suffix
                counter = 1
                while dest.exists():
                    dest = ARCHIVE_DIR / f"{stem}_{counter}{suffix}"
                    counter += 1

            shutil.move(str(f), str(dest))
            print(f"  ✅ Archived: {f.name} → _archived/")
            archived += 1

    return archived


def delete_files(files: list[Path], dry_run: bool = False) -> int:
    """Permanently delete files."""
    if not files:
        print("No files to delete.")
        return 0

    deleted = 0
    for f in files:
        if dry_run:
            print(f"  Would delete: {f.name}")
        else:
            f.unlink()
            print(f"  🗑️  Deleted: {f.name}")
            deleted += 1

    return deleted


def main():
    """
    Main function to clean up old L9 audit reports by archiving or deleting outdated files based on report type and age.
    Returns:
        None, performs file operations and user interactions.
    """
    parser = argparse.ArgumentParser(
        description="Clean up old L9 audit reports",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # List all audit reports (dry-run)
  python cleanup_audit_reports.py --action list

  # Archive all but the 3 most recent
  python cleanup_audit_reports.py --action archive --keep 3

  # Delete reports older than 14 days
  python cleanup_audit_reports.py --action delete --older-than 14

  # Archive everything except latest
  python cleanup_audit_reports.py --action archive --keep 1
""",
    )

    parser.add_argument(
        "--action",
        choices=["list", "archive", "delete"],
        default="list",
        help="Action to perform (default: list)",
    )
    parser.add_argument(
        "--keep",
        type=int,
        default=3,
        help="Number of most recent files to keep (default: 3)",
    )
    parser.add_argument(
        "--older-than",
        type=int,
        default=0,
        help="Only affect files older than N days (default: 0 = all)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would happen without making changes",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Skip confirmation prompt",
    )

    args = parser.parse_args()

    # Get all audit files
    all_files = get_audit_files()

    if args.action == "list":
        list_files(all_files)
        print(f"\nProtected files (never deleted): {KEEP_FILES}")
        return 0

    # Filter by age if specified
    if args.older_than > 0:
        all_files = [f for f in all_files if get_file_age_days(f) > args.older_than]

    # Keep the N most recent
    files_to_process = all_files[args.keep :] if args.keep > 0 else all_files

    if not files_to_process:
        print(f"No files to {args.action}. Keeping {args.keep} most recent.")
        return 0

    # Show what will be affected
    print(f"\n{'DRY RUN - ' if args.dry_run else ''}Files to {args.action}:")
    print("-" * 50)
    for f in files_to_process:
        print(f"  {f.name}")
    print("-" * 50)
    print(f"Total: {len(files_to_process)} files")
    print(f"Keeping: {min(args.keep, len(all_files))} most recent files")

    # Confirm unless --force or --dry-run
    if not args.force and not args.dry_run:
        confirm = input(
            f"\n⚠️  {args.action.upper()} these {len(files_to_process)} files? [y/N]: "
        )
        if confirm.lower() != "y":
            print("Cancelled.")
            return 1

    # Execute action
    if args.action == "archive":
        count = archive_files(files_to_process, args.dry_run)
        if not args.dry_run:
            print(f"\n✅ Archived {count} files to reports/_archived/")
    elif args.action == "delete":
        count = delete_files(files_to_process, args.dry_run)
        if not args.dry_run:
            print(f"\n✅ Deleted {count} files")

    return 0


if __name__ == "__main__":
    sys.exit(main())

# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "SCR-OPER-001",
    "governance_level": "medium",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": ["cli", "filesystem", "operations", "rest-api", "scripts", "testing"],
    "keywords": [
        "age",
        "archive",
        "audit",
        "cleanup",
        "days",
        "delete",
        "files",
        "format",
    ],
    "business_value": "Utility module for cleanup audit reports",
    "last_modified": "2026-01-14T12:10:12Z",
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
