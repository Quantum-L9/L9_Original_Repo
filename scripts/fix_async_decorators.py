#!/usr/bin/env python3
"""
Migrate from '# NOTE: Must stay async' comments to @must_stay_async decorator.

This script:
1. Finds all files with the old comment pattern
2. Removes the comment
3. Adds the import for must_stay_async
4. Adds the @must_stay_async(reason) decorator

Usage:
    python scripts/fix_async_decorators.py --dry-run  # Preview changes
    python scripts/fix_async_decorators.py            # Apply changes
"""

# ============================================================================
__dora_meta__ = {
    "component_name": "Fix Async Decorators",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2026-01-17T14:57:53Z",
    "updated_at": "2026-01-17T23:47:56Z",
    "layer": "operations",
    "domain": "scripts",
    "module_name": "fix_async_decorators",
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

import os
import re
import sys
from pathlib import Path

import structlog

# Directories to skip

logger = structlog.get_logger(__name__)

SKIP_DIRS = {
    "tests",
    "current_work",
    "codegen",
    "igor",
    "__pycache__",
    "venv",
    ".git",
    ".cursor",
    "_archived",
}

# Map comment patterns to decorator reasons
REASON_MAP = {
    "FastAPI/ASGI route handler requires async def": "FastAPI/ASGI route handler",
    "FastAPI/ASGI route handler": "FastAPI/ASGI route handler",
    "async context manager protocol (__aenter__/__aexit__)": "async context manager protocol",
    "async context manager protocol": "async context manager protocol",
    "interface contract, callers use `await`": "interface contract",
    "callers use `await`, changing would break API": "callers use await",
    "callers use `await`": "callers use await",
    "LangGraph node protocol requires async callable": "LangGraph node protocol",
    "LangGraph node protocol": "LangGraph node protocol",
    "FastAPI health endpoint convention": "health endpoint",
    "health endpoint convention": "health endpoint",
    "placeholder for future await implementation": "future await planned",
    "future await implementation": "future await planned",
}

# Comment pattern to match
COMMENT_PATTERN = re.compile(r"^(\s*)# NOTE: Must stay async - (.+)\.\s*$")

# Import line to add
IMPORT_LINE = "from core.decorators import must_stay_async"


def extract_reason(comment_text: str) -> str:
    """Extract and normalize the reason from a comment."""
    # Try exact match first
    if comment_text in REASON_MAP:
        return REASON_MAP[comment_text]

    # Try partial matches
    for pattern, reason in REASON_MAP.items():
        if pattern in comment_text or comment_text in pattern:
            return reason

    # Fallback: use the comment text itself (cleaned up)
    return comment_text.rstrip(".")


def has_import(lines: list[str], import_line: str) -> bool:
    """Check if the import already exists."""
    return any(import_line in line for line in lines)


def find_import_insert_position(lines: list[str]) -> int:
    """Find the best position to insert the import."""
    last_import_idx = 0
    in_docstring = False
    docstring_char = None

    for i, line in enumerate(lines):
        stripped = line.strip()

        # Track docstrings
        if not in_docstring:
            if stripped.startswith('"""') or stripped.startswith("'''"):
                docstring_char = stripped[:3]
                if stripped.count(docstring_char) >= 2:
                    # Single-line docstring
                    continue
                in_docstring = True
                continue
        else:
            if docstring_char and docstring_char in stripped:
                in_docstring = False
                continue
            continue

        # Track imports
        if stripped.startswith("import ") or stripped.startswith("from "):
            last_import_idx = i + 1

        # Stop at first class or function definition
        if (
            stripped.startswith("class ")
            or stripped.startswith("def ")
            or stripped.startswith("async def")
        ):
            break

    return last_import_idx


def process_file(filepath: str, dry_run: bool = True) -> dict:
    """Process a single file, removing comments and adding decorators."""
    result = {
        "filepath": filepath,
        "comments_removed": 0,
        "decorators_added": 0,
        "import_added": False,
        "changes": [],
    }

    try:
        with open(filepath) as f:
            lines = f.readlines()
    except Exception as e:
        result["error"] = str(e)
        return result

    new_lines = []
    i = 0
    needs_import = False

    while i < len(lines):
        line = lines[i]
        match = COMMENT_PATTERN.match(line)

        if match:
            indent = match.group(1)
            comment_text = match.group(2)
            reason = extract_reason(comment_text)

            # Check if next line is async def
            if i + 1 < len(lines) and "async def" in lines[i + 1]:
                # Remove the comment (don't add it)
                result["comments_removed"] += 1

                # Add decorator instead
                decorator_line = f'{indent}@must_stay_async("{reason}")\n'
                new_lines.append(decorator_line)
                result["decorators_added"] += 1
                result["changes"].append(
                    f'Line {i + 1}: comment → @must_stay_async("{reason}")'
                )
                needs_import = True

                i += 1
                continue

        new_lines.append(line)
        i += 1

    # Add import if needed
    if needs_import and not has_import(new_lines, "must_stay_async"):
        insert_pos = find_import_insert_position(new_lines)
        new_lines.insert(insert_pos, IMPORT_LINE + "\n")
        result["import_added"] = True
        result["changes"].insert(0, f"Line {insert_pos + 1}: Added import")

    # Write changes
    if not dry_run and result["comments_removed"] > 0:
        try:
            with open(filepath, "w") as f:
                f.writelines(new_lines)
        except Exception as e:
            result["error"] = str(e)

    return result


def main():
    """
    Finds Python files with old async decorator comments, removes comments, and adds import statement.



    Raises:
        OSError: If file operations fail during processing.
    """
    dry_run = "--dry-run" in sys.argv

    if dry_run:
        logger.info("=== dry run mode - no files will be modified ===\n")

    # Find all Python files with the comment pattern
    root = Path(".")
    files_with_comments = []

    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [
            d for d in dirnames if d not in SKIP_DIRS and not d.startswith(".")
        ]

        for filename in filenames:
            if filename.endswith(".py"):
                filepath = os.path.join(dirpath, filename)
                try:
                    with open(filepath) as f:
                        content = f.read()
                    if "# NOTE: Must stay async" in content:
                        files_with_comments.append(filepath)
                except Exception:
                    logger.debug("fix_async_decorators.file_read_failed", filepath=filepath)

    logger.info("found {len(files_with_comments)} files with async comments\n")

    # Process each file
    total_comments = 0
    total_decorators = 0
    total_imports = 0

    for filepath in sorted(files_with_comments):
        result = process_file(filepath, dry_run)

        if result.get("error"):
            logger.error("  ✗ filepath: {result['error']}", filepath=filepath)
            continue

        if result["comments_removed"] > 0:
            total_comments += result["comments_removed"]
            total_decorators += result["decorators_added"]
            if result["import_added"]:
                total_imports += 1

            logger.info("  ✓ filepath", filepath=filepath)
            for change in result["changes"][:3]:
                logger.info("      change", change=change)
            if len(result["changes"]) > 3:
                logger.info("      ... and {len(result['changes']) - 3} more")

    logger.info("\n=== summary ===")
    logger.info("comments removed: total comments", total_comments=total_comments)
    logger.info("decorators added: total decorators", total_decorators=total_decorators)
    logger.info("imports added: total imports", total_imports=total_imports)

    if dry_run:
        logger.info("\n=== dry run - run without --dry-run to apply changes ===")


if __name__ == "__main__":
    main()

# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "SCR-OPER-001",
    "governance_level": "medium",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": [
        "api",
        "async",
        "caching",
        "cli",
        "filesystem",
        "operations",
        "scripts",
        "testing",
    ],
    "keywords": [
        "async",
        "decorators",
        "extract",
        "find",
        "fix",
        "insert",
        "position",
        "process",
    ],
    "business_value": "1. Finds all files with the old comment pattern 2. Removes the comment 3. Adds the import for must_stay_async 4. Adds the @must_stay_async(reason) decorator python scripts/fix_async_decorators.py --dr",
    "last_modified": "2026-01-17T23:47:56Z",
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
