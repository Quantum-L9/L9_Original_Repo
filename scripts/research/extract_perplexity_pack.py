#!/usr/bin/env python3
"""
Perplexity Pack Extractor
=========================
Extracts multi-file outputs from Perplexity into individual files.

Usage:
    # From clipboard (macOS):
    pbpaste | python scripts/extract_perplexity_pack.py

    # From file:
    python scripts/extract_perplexity_pack.py < perplexity_output.txt

    # With output directory:
    python scripts/extract_perplexity_pack.py --output-dir ./generated < perplexity_output.txt

This enables token-efficient editing:
1. Perplexity generates multi-file pack (free Labs tokens)
2. This script extracts to individual files
3. Cursor EDITS files surgically (minimal paid tokens)
"""

import argparse
import structlog
import re
import sys
from pathlib import Path


logger = structlog.get_logger(__name__)


def extract_files(content: str, output_dir: str = ".") -> list[dict]:
    """
    Extract files from Perplexity multi-file output.

    Supports formats:
    - ```python:path/to/file.py
    - # File: path/to/file.py
    - # path/to/file.py
    - ## `path/to/file.py`
    """

    files_extracted = []

    # Pattern 1: ```language:filepath or ```filepath
    pattern1 = r"```(?:python|yaml|json|markdown|bash|sh)?:?([\w\/\.\-_]+\.(?:py|yaml|yml|json|md|sh|txt))\n(.*?)```"

    # Pattern 2: # File: filepath or ## File: filepath
    pattern2 = r'#+ ?(?:File:?)?\s*[`"]?([\w\/\.\-_]+\.(?:py|yaml|yml|json|md|sh|txt))[`"]?\s*\n```(?:python|yaml|json|markdown|bash|sh)?\n(.*?)```'

    # Pattern 3: Just filename comment followed by code block
    pattern3 = r"#\s*([\w\/\.\-_]+\.py)\s*\n```python\n(.*?)```"

    # Try each pattern
    for pattern in [pattern1, pattern2, pattern3]:
        matches = re.findall(pattern, content, re.DOTALL | re.MULTILINE)
        for filepath, code in matches:
            # Clean up filepath
            filepath = filepath.strip().lstrip("/")

            # Skip if already extracted
            if any(f["path"] == filepath for f in files_extracted):
                continue

            # Clean up code
            code = code.strip()

            if code and len(code) > 10:  # Skip tiny snippets
                files_extracted.append(
                    {"path": filepath, "content": code, "lines": code.count("\n") + 1}
                )

    # Also try to find YAML specs
    yaml_pattern = r"```yaml\n(.*?)```"
    yaml_matches = re.findall(yaml_pattern, content, re.DOTALL)
    for i, yaml_content in enumerate(yaml_matches):
        if "schema_version" in yaml_content or "module:" in yaml_content:
            # Looks like a Module Spec
            # Try to extract module name
            name_match = re.search(r'id:\s*["\']?(\w+)["\']?', yaml_content)
            if name_match:
                module_name = name_match.group(1)
                filepath = f"specs/{module_name}_spec.yaml"
            else:
                filepath = f"specs/module_spec_{i + 1}.yaml"

            if not any(f["path"] == filepath for f in files_extracted):
                files_extracted.append(
                    {
                        "path": filepath,
                        "content": yaml_content.strip(),
                        "lines": yaml_content.count("\n") + 1,
                    }
                )

    return files_extracted


def write_files(files: list[dict], output_dir: str, dry_run: bool = False) -> None:
    """Write extracted files to disk."""

    output_path = Path(output_dir)

    logger.info(
        f"\n{'[DRY RUN] ' if dry_run else ''}Extracting {len(files)} files to {output_path}/\n"
    )
    logger.info("=" * 60)

    for f in files:
        filepath = output_path / f["path"]

        # Create parent directories
        if not dry_run:
            filepath.parent.mkdir(parents=True, exist_ok=True)

        logger.info(
            f"  {'Would create' if dry_run else 'Creating'}: {f['path']} ({f['lines']} lines)"
        )

        if not dry_run:
            with open(filepath, "w") as fp:
                fp.write(f["content"])
                fp.write("\n")  # Ensure trailing newline

    logger.info("=" * 60)
    logger.info(
        f"\n✅ {'Would extract' if dry_run else 'Extracted'} {len(files)} files"
    )

    if not dry_run:
        logger.info("\nNext steps:")
        logger.info(f"  1. Review files in {output_path}/")
        logger.info("  2. Ask Cursor to edit/wire them into the repo")
        logger.info("  3. Cursor uses search_replace (token-efficient!)")


def main():
    parser = argparse.ArgumentParser(
        description="Extract multi-file packs from Perplexity output"
    )
    parser.add_argument(
        "--output-dir",
        "-o",
        default="./generated",
        help="Output directory for extracted files (default: ./generated)",
    )
    parser.add_argument(
        "--dry-run",
        "-n",
        action="store_true",
        help="Show what would be extracted without writing files",
    )
    parser.add_argument("--input-file", "-i", help="Input file (default: stdin)")

    args = parser.parse_args()

    # Read input
    if args.input_file:
        with open(args.input_file) as f:
            content = f.read()
    else:
        if sys.stdin.isatty():
            logger.info("Paste Perplexity output (Ctrl+D when done):\n")
        content = sys.stdin.read()

    if not content.strip():
        logger.error("Error: No input provided")
        sys.exit(1)

    # Extract files
    files = extract_files(content, args.output_dir)

    if not files:
        logger.info("No files found in input.")
        logger.info("\nExpected formats:")
        logger.info("  ```python:path/to/file.py")
        logger.info("  # File: path/to/file.py")
        logger.info("  ## `path/to/file.py`")
        sys.exit(1)

    # Write files
    write_files(files, args.output_dir, args.dry_run)


if __name__ == "__main__":
    main()
