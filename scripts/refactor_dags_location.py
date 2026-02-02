#!/usr/bin/env python3
"""
Refactor Script: Move workflows/dags/ → workflows/dags/

This script:
1. Creates workflows/dags/ directory
2. Moves all DAG files
3. Updates all import paths
4. Updates all hardcoded string paths
5. Updates DORA metadata

Run with --dry-run first to preview changes.

Usage:
    python scripts/refactor_dags_location.py --dry-run
    python scripts/refactor_dags_location.py --execute
"""

import argparse
import shutil
from pathlib import Path

# Project root
PROJECT_ROOT = Path(__file__).parent.parent

# Source and destination
SRC_DIR = PROJECT_ROOT / "workflows" / "session" / "dags"
DST_DIR = PROJECT_ROOT / "workflows" / "dags"

# Patterns to replace
REPLACEMENTS = [
    # Python imports (dotted)
    ("workflows.dags", "workflows.dags"),
    # File paths (slashed)
    ("workflows/dags", "workflows/dags"),
]

# Files to update (beyond the moved files)
FILES_TO_UPDATE = [
    "workflows/session/interface.py",
    "workflows/session/registry.py",
    "readme/adr/0070-session-dag-workflow-orchestration.md",
    "workflows/Dags-Harvest/DAG-Harvest-2.md",
]


def find_files_with_pattern(
    root: Path, pattern: str, extensions: list[str]
) -> list[Path]:
    """Find all files containing pattern."""
    matches = []
    for ext in extensions:
        for filepath in root.rglob(f"*{ext}"):
            # Skip __pycache__ and .git
            if "__pycache__" in str(filepath) or ".git" in str(filepath):
                continue
            try:
                content = filepath.read_text()
                if pattern in content:
                    matches.append(filepath)
            except Exception:
                pass
    return matches


def update_file_content(filepath: Path, dry_run: bool = True) -> tuple[bool, list[str]]:
    """Update file content with replacements. Returns (changed, changes)."""
    try:
        content = filepath.read_text()
        original = content
        changes = []

        for old, new in REPLACEMENTS:
            if old in content:
                count = content.count(old)
                content = content.replace(old, new)
                changes.append(f"  '{old}' → '{new}' ({count} occurrences)")

        if content != original:
            if not dry_run:
                filepath.write_text(content)
            return True, changes
        return False, []
    except Exception as e:
        return False, [f"  ERROR: {e}"]


def main():
    parser = argparse.ArgumentParser(
        description="Move workflows/dags/ to workflows/dags/"
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Preview changes without executing"
    )
    parser.add_argument("--execute", action="store_true", help="Execute the refactor")
    args = parser.parse_args()

    if not args.dry_run and not args.execute:
        print("ERROR: Must specify --dry-run or --execute")
        print("Run with --dry-run first to preview changes")
        return 1

    dry_run = args.dry_run
    mode = "DRY RUN" if dry_run else "EXECUTING"

    print(f"\n{'=' * 60}")
    print(f"DAG Location Refactor - {mode}")
    print(f"{'=' * 60}")
    print(f"\nSource: {SRC_DIR}")
    print(f"Destination: {DST_DIR}")

    # Check source exists
    if not SRC_DIR.exists():
        print(f"\nERROR: Source directory does not exist: {SRC_DIR}")
        return 1

    # List files to move
    dag_files = list(SRC_DIR.glob("*.py"))
    print(f"\n📁 Files to move ({len(dag_files)}):")
    for f in dag_files:
        print(f"  - {f.name}")

    # Find all files needing updates
    print("\n🔍 Scanning for files with references...")
    all_files_to_update = set()

    for pattern, _ in REPLACEMENTS:
        matches = find_files_with_pattern(
            PROJECT_ROOT, pattern, [".py", ".md", ".yaml", ".yml"]
        )
        all_files_to_update.update(matches)

    # Remove source files from update list (they'll be moved)
    all_files_to_update = {
        f
        for f in all_files_to_update
        if SRC_DIR not in f.parents and f.parent != SRC_DIR
    }

    print(f"\n📝 Files to update ({len(all_files_to_update)}):")
    for f in sorted(all_files_to_update):
        print(f"  - {f.relative_to(PROJECT_ROOT)}")

    # Phase 1: Create destination directory
    print(f"\n{'=' * 60}")
    print("PHASE 1: Create destination directory")
    print(f"{'=' * 60}")

    if DST_DIR.exists():
        print(f"  ⚠️  Destination already exists: {DST_DIR}")
    else:
        print(f"  Creating: {DST_DIR}")
        if not dry_run:
            DST_DIR.mkdir(parents=True, exist_ok=True)

    # Phase 2: Move files
    print(f"\n{'=' * 60}")
    print("PHASE 2: Move DAG files")
    print(f"{'=' * 60}")

    for src_file in dag_files:
        dst_file = DST_DIR / src_file.name
        print(f"  {src_file.name} → {dst_file.relative_to(PROJECT_ROOT)}")
        if not dry_run:
            shutil.copy2(src_file, dst_file)

    # Phase 3: Update content in moved files
    print(f"\n{'=' * 60}")
    print("PHASE 3: Update imports in moved files")
    print(f"{'=' * 60}")

    for src_file in dag_files:
        dst_file = DST_DIR / src_file.name
        target = dst_file if not dry_run else src_file
        changed, changes = update_file_content(target, dry_run)
        if changed:
            print(f"\n  {src_file.name}:")
            for c in changes:
                print(c)

    # Phase 4: Update other files
    print(f"\n{'=' * 60}")
    print("PHASE 4: Update references in other files")
    print(f"{'=' * 60}")

    for filepath in sorted(all_files_to_update):
        changed, changes = update_file_content(filepath, dry_run)
        if changed:
            print(f"\n  {filepath.relative_to(PROJECT_ROOT)}:")
            for c in changes:
                print(c)

    # Phase 5: Remove old directory (only if execute)
    print(f"\n{'=' * 60}")
    print("PHASE 5: Cleanup old directory")
    print(f"{'=' * 60}")

    if dry_run:
        print(f"  Would remove: {SRC_DIR}")
    else:
        print(f"  Removing: {SRC_DIR}")
        # Don't actually remove yet - keep for safety
        print(
            "  ⚠️  Old directory preserved for safety. Remove manually after verification:"
        )
        print(f"     rm -rf {SRC_DIR}")

    # Summary
    print(f"\n{'=' * 60}")
    print("SUMMARY")
    print(f"{'=' * 60}")
    print(f"  Files moved: {len(dag_files)}")
    print(f"  Files updated: {len(all_files_to_update)}")

    if dry_run:
        print("\n✅ DRY RUN COMPLETE - No changes made")
        print("   Run with --execute to apply changes")
    else:
        print("\n✅ REFACTOR COMPLETE")
        print(
            '   Verify with: python -c "from workflows.dags import INSPECT_DAG; print(INSPECT_DAG.id)"'
        )
        print(f"   Then remove old: rm -rf {SRC_DIR}")

    return 0


if __name__ == "__main__":
    exit(main())
