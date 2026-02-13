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

import structlog

# Project root

logger = structlog.get_logger(__name__)

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
        logger.error("error: must specify --dry-run or --execute")
        logger.info("run with --dry-run first to preview changes")
        return 1

    dry_run = args.dry_run
    mode = "DRY RUN" if dry_run else "EXECUTING"

    logger.info("\n{'=' * 60}")
    logger.info("dag location refactor - mode", mode=mode)
    logger.info("{'=' * 60}")
    logger.info("\nsource: src dir", SRC_DIR=SRC_DIR)
    logger.info("destination: dst dir", DST_DIR=DST_DIR)

    # Check source exists
    if not SRC_DIR.exists():
        logger.error(
            "\nerror: source directory does not exist: src dir", SRC_DIR=SRC_DIR
        )
        return 1

    # List files to move
    dag_files = list(SRC_DIR.glob("*.py"))
    logger.info("\n📁 files to move ({len(dag_files)}):")
    for f in dag_files:
        logger.info("  - {f.name}")

    # Find all files needing updates
    logger.info("\n🔍 scanning for files with references...")
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

    logger.info("\n📝 files to update ({len(all_files_to_update)}):")
    for f in sorted(all_files_to_update):
        logger.info("  - {f.relative_to(project_root)}")

    # Phase 1: Create destination directory
    logger.info("\n{'=' * 60}")
    logger.info("phase 1: create destination directory")
    logger.info("{'=' * 60}")

    if DST_DIR.exists():
        logger.info("  ⚠️  destination already exists: dst dir", DST_DIR=DST_DIR)
    else:
        logger.info("  creating: dst dir", DST_DIR=DST_DIR)
        if not dry_run:
            DST_DIR.mkdir(parents=True, exist_ok=True)

    # Phase 2: Move files
    logger.info("\n{'=' * 60}")
    logger.info("phase 2: move dag files")
    logger.info("{'=' * 60}")

    for src_file in dag_files:
        dst_file = DST_DIR / src_file.name
        logger.info("  {src_file.name} → {dst_file.relative_to(project_root)}")
        if not dry_run:
            shutil.copy2(src_file, dst_file)

    # Phase 3: Update content in moved files
    logger.info("\n{'=' * 60}")
    logger.info("phase 3: update imports in moved files")
    logger.info("{'=' * 60}")

    for src_file in dag_files:
        dst_file = DST_DIR / src_file.name
        target = dst_file if not dry_run else src_file
        changed, changes = update_file_content(target, dry_run)
        if changed:
            logger.info("\n  {src_file.name}:")
            for c in changes:
                logger.info("output", value=c)

    # Phase 4: Update other files
    logger.info("\n{'=' * 60}")
    logger.info("phase 4: update references in other files")
    logger.info("{'=' * 60}")

    for filepath in sorted(all_files_to_update):
        changed, changes = update_file_content(filepath, dry_run)
        if changed:
            logger.info("\n  {filepath.relative_to(project_root)}:")
            for c in changes:
                logger.info("output", value=c)

    # Phase 5: Remove old directory (only if execute)
    logger.info("\n{'=' * 60}")
    logger.info("phase 5: cleanup old directory")
    logger.info("{'=' * 60}")

    if dry_run:
        logger.info("  would remove: src dir", SRC_DIR=SRC_DIR)
    else:
        logger.info("  removing: src dir", SRC_DIR=SRC_DIR)
        # Don't actually remove yet - keep for safety
        print(
            "  ⚠️  Old directory preserved for safety. Remove manually after verification:"
        )
        logger.info("     rm -rf src dir", SRC_DIR=SRC_DIR)

    # Summary
    logger.info("\n{'=' * 60}")
    logger.info("summary")
    logger.info("{'=' * 60}")
    logger.info("  files moved: {len(dag_files)}")
    logger.info("  files updated: {len(all_files_to_update)}")

    if dry_run:
        logger.info("\n✅ dry run complete - no changes made")
        logger.info("   run with --execute to apply changes")
    else:
        logger.info("\n✅ refactor complete")
        print(
            '   Verify with: python -c "from workflows.dags import INSPECT_DAG; print(INSPECT_DAG.id)"'
        )
        logger.info("   then remove old: rm -rf src dir", SRC_DIR=SRC_DIR)

    return 0


if __name__ == "__main__":
    exit(main())
