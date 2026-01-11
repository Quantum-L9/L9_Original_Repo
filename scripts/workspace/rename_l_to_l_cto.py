#!/usr/bin/env python3
"""
Replace all instances of "l" with "l-cto" in the L9 repo.

Handles:
- Import paths: `from l.` → `from l_cto.` (Python modules use underscores)
- Agent IDs: `agent_id="l"` → `agent_id="l-cto"`
- Package references in code

Usage:
    python scripts/rename_l_to_l_cto.py [--dry-run]
"""

import re
import structlog
import os
from pathlib import Path
from typing import List, Tuple

# Directories to process
REPO_ROOT = Path(__file__).parent.parent
TARGET_DIRS = [
    "l-cto",
    "agents",
    "api",
    "core",
    "orchestration",
    "orchestrators",
    "services",
    "tests",
    "scripts",
]

# Files to skip (binary, generated, etc.)
SKIP_PATTERNS = [
    r"\.pyc$",
    r"__pycache__",
    r"\.DS_Store",
    r"\.git",
    r"venv",
    r"node_modules",
    r"\.md$",  # Skip markdown files (user-facing, keep "L")
    r"rename_l_to_l_cto\.py$",  # Don't process this script itself
]

# Replacement patterns: (pattern, replacement, description)
# Order matters - more specific patterns first
REPLACEMENTS = [
    # Import statements (MUST come first - most specific)
    (r"from l\.", r"from l_cto.", "Import from l."),
    (r"import l\.", r"import l_cto.", "Import l."),
    # Agent ID strings - only replace standalone "l" (not "l-cto" or "l_cto")
    (
        r'agent_id\s*=\s*"l"(?![-_])',
        r'agent_id="l-cto"',
        "Agent ID double quote (standalone)",
    ),
    (
        r"agent_id\s*=\s*'l'(?![-_])",
        r"agent_id='l-cto'",
        "Agent ID single quote (standalone)",
    ),
    # String literals - only standalone "l" (not part of "l-cto", "l_cto", "l9", etc.)
    (r'"l"(?![-_a-z0-9])', r'"l-cto"', 'String literal "l" (standalone)'),
    (r"'l'(?![-_a-z0-9])", r"'l-cto'", "String literal 'l' (standalone)"),
]

# More conservative replacements (only in specific contexts)
CONTEXTUAL_REPLACEMENTS = [
    # Agent ID in dict/object contexts - only standalone "l"
    (
        r'["\']agent_id["\']\s*:\s*["\']l["\'](?![-_])',
        r'"agent_id": "l-cto"',
        "Dict agent_id (standalone)",
    ),
    (
        r'agent_id\s*:\s*["\']l["\'](?![-_])',
        r'agent_id: "l-cto"',
        "YAML/JSON agent_id (standalone)",
    ),
]


def should_skip_file(filepath: Path) -> bool:
    """Check if file should be skipped."""
    path_str = str(filepath)
    return any(re.search(pattern, path_str) for pattern in SKIP_PATTERNS)


def replace_in_file(
    filepath: Path, dry_run: bool = False
) -> List[Tuple[int, str, str]]:
    """
    Replace patterns in a single file.

    Returns:
        List of (line_number, old_line, new_line) tuples
    """
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            lines = f.readlines()
    except (UnicodeDecodeError, PermissionError) as e:
        logger.info(f"  ⚠️  Skipping {filepath}: {e}")
        return []

    changes = []
    new_lines = []

    for line_num, line in enumerate(lines, 1):
        original_line = line
        new_line = line

        # Apply all replacements
        for pattern, replacement, desc in REPLACEMENTS:
            if re.search(pattern, new_line):
                new_line = re.sub(pattern, replacement, new_line)

        # Apply contextual replacements
        for pattern, replacement, desc in CONTEXTUAL_REPLACEMENTS:
            if re.search(pattern, new_line):
                new_line = re.sub(pattern, replacement, new_line)

        if new_line != original_line:
            changes.append((line_num, original_line.rstrip(), new_line.rstrip()))
            if not dry_run:
                line = new_line

        new_lines.append(line)

    # Write file if changes were made
    if changes and not dry_run:
        try:
            with open(filepath, "w", encoding="utf-8") as f:
                f.writelines(new_lines)
        except Exception as e:
            logger.error(f"  ❌ Error writing {filepath}: {e}")
            return []

    return changes


def process_directory(directory: Path, dry_run: bool = False) -> dict:
    """Process all files in a directory."""
    stats = {
        "files_processed": 0,
        "files_changed": 0,
        "total_changes": 0,
        "errors": 0,
    }

    if not directory.exists():
        logger.info(f"⚠️  Directory not found: {directory}")
        return stats

    for root, dirs, files in os.walk(directory):
        # Skip hidden directories
        dirs[:] = [d for d in dirs if not d.startswith(".")]

        for filename in files:
            filepath = Path(root) / filename

            if should_skip_file(filepath):
                continue

            # Only process Python files
            if filepath.suffix != ".py":
                continue

            stats["files_processed"] += 1
            changes = replace_in_file(filepath, dry_run=dry_run)

            if changes:
                stats["files_changed"] += 1
                stats["total_changes"] += len(changes)
                logger.info(f"  ✏️  {filepath.relative_to(REPO_ROOT)}: {len(changes)} changes")
                if dry_run:
                    for line_num, old, new in changes[:3]:  # Show first 3
                        logger.info(f"      Line {line_num}:")
                        logger.info(f"        - {old}")
                        logger.info(f"        + {new}")
                    if len(changes) > 3:
                        logger.info(f"      ... and {len(changes) - 3} more")

    return stats


def main():
    """Main entry point."""
    import sys

    dry_run = "--dry-run" in sys.argv or "-n" in sys.argv

    logger.info("=" * 70)
    logger.info("L → l-cto Rename Script")
    logger.info("=" * 70)
    logger.info(f"Mode: {'DRY RUN (no changes)' if dry_run else 'LIVE (will modify files)'}")
    logger.info(f"Repo root: {REPO_ROOT}")

    total_stats = {
        "files_processed": 0,
        "files_changed": 0,
        "total_changes": 0,
        "errors": 0,
    }

    for dir_name in TARGET_DIRS:
        dir_path = REPO_ROOT / dir_name
        if not dir_path.exists():
            logger.info(f"⚠️  Skipping {dir_name} (not found)")
            continue

        logger.info(f"📁 Processing {dir_name}/...")
        stats = process_directory(dir_path, dry_run=dry_run)

        for key in total_stats:
            total_stats[key] += stats[key]

        logger.info(f"   {stats['files_changed']} files changed, {stats['total_changes']} total replacements")

    logger.info("=" * 70)
    logger.info("Summary:")
    logger.info(f"  Files processed: {total_stats['files_processed']}")
    logger.info(f"  Files changed: {total_stats['files_changed']}")
    logger.info(f"  Total replacements: {total_stats['total_changes']}")
    logger.info("=" * 70)

    if dry_run:
        logger.info("💡 Run without --dry-run to apply changes")
    else:
        logger.info("✅ Rename complete!")
        logger.info("⚠️  IMPORTANT NEXT STEPS:")
        logger.info("  1. Review changes with: git diff")
        logger.info("  2. Test imports: python -c 'from l_cto import ...'")
        logger.info("  3. Update any remaining references manually")
        logger.info("  4. Rename directory: mv l-cto l_cto (if needed for Python imports)")



logger = structlog.get_logger(__name__)
if __name__ == "__main__":
    main()
