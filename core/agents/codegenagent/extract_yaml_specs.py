#!/usr/bin/env python3
"""
Extract YAML specs from Chat Transcript - CodeGenAgentv1.0.md

Segregates patches from non-patches based on:
- type field containing: registry_patch, router_patch, singleton_wiring, etc.
- filename containing: _patch, patch_

Outputs:
- core/agents/codegenagent/patches/*.yaml - All patch files
- core/agents/codegenagent/specs/*.yaml   - All non-patch spec files

NOTE: The transcript uses '''yaml (triple single quotes) as delimiters.
"""

__dora_meta__ = {
    "component_name": "Extract Yaml Specs",
    "module_version": "1.0.0",
    "created_by": "Auto-fix ADR-0014",
    "created_at": "2026-02-13T23:37:34.991085+00:00",
    "updated_at": "2026-02-13T23:37:34.991085+00:00",
    "layer": "core",
    "domain": "agents",
    "module_name": "core.agents.codegenagent.extract_yaml_specs",
    "type": "module",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": [],
        "memory_layers": [],
        "imported_by": [],
    },
}


import os
import re
from pathlib import Path

import structlog

# Patch type indicators

logger = structlog.get_logger(__name__)
PATCH_TYPES = [
    "registry_patch",
    "router_patch",
    "singleton_wiring",
    "runtime_patch",
    "kernel_patch",
    "orchestration_patch",
    "patch",
    "governance_patch",
    "memory_patch",
    "agent_bootstrap",
    "compliance_enforcer",
    "security_watchdog",
    "orchestrator_patch",
    "kernel_upgrade",
    "schema_generator",
    "fail_safety",
]

PATCH_FILENAME_PATTERNS = ["_patch", "patch_", "/patch/", "patch."]


def is_patch(yaml_content: str, filename: str) -> bool:
    """Determine if a YAML spec is a patch."""
    # Check type field
    type_match = re.search(r"^type:\s*(.+)$", yaml_content, re.MULTILINE)
    if type_match:
        type_val = type_match.group(1).strip().lower()
        for pt in PATCH_TYPES:
            if pt in type_val:
                return True

    # Check filename for patch indicators
    filename_lower = filename.lower()
    return any(pattern in filename_lower for pattern in PATCH_FILENAME_PATTERNS)


def extract_yaml_blocks(content: str) -> list:
    """Extract all '''yaml blocks from the content."""
    # The transcript uses ''' (three single quotes), not ``` (backticks)
    # Pattern: '''yaml ... '''
    # IMPORTANT: Only match '''yaml that appears at line start or after newline
    # to avoid matching explanatory mentions like "Wrapped in '''yaml for Cursor"

    blocks: list[str] = []

    # Pattern: '''yaml at start of line, capture until closing '''
    # The (?:^|\n) ensures we only match '''yaml at line boundaries
    pattern = r"(?:^|\n)'''yaml\s*(.*?)'''"

    matches = re.findall(pattern, content, re.DOTALL)

    for match in matches:
        # Skip if this looks like prose (no filename: field)
        if "filename:" not in match:
            continue

        # Skip if it's very short (likely a false match from prose)
        if len(match.strip()) < 50:
            continue

        # Extract filename from the yaml content
        filename_match = re.search(r"^filename:\s*(.+)$", match, re.MULTILINE)
        if filename_match:
            filename = filename_match.group(1).strip()
            # Avoid duplicates - keep the LONGER version (more complete spec)
            existing = next((b for b in blocks if b["filename"] == filename), None)
            if existing:
                if len(match) > len(existing["content"]):
                    existing["content"] = match.strip()
                    existing["is_patch"] = is_patch(match, filename)
            else:
                blocks.append(
                    {
                        "filename": filename,
                        "content": match.strip(),
                        "is_patch": is_patch(match, filename),
                    }
                )

    return blocks


def sanitize_filename(filename: str) -> str:
    """Convert a path-like filename to a safe filename."""
    # Replace path separators with underscores
    safe_name = filename.replace("/", "_").replace("\\", "_")
    # Ensure it ends with .yaml
    if not safe_name.endswith(".yaml"):
        # Get extension
        base, _ext = os.path.splitext(safe_name)
        safe_name = base + ".yaml"
    return safe_name


def main():
    """
    Parses the Markdown transcript to extract YAML specifications and segregate patches based on type and filename criteria.

    Args:
        None

    Returns:
        None

    Raises:
        FileNotFoundError: If the transcript file does not exist.
        OSError: If directory creation fails.
    """
    script_dir = Path(__file__).parent
    transcript_path = script_dir / "Chat Transcript - CodeGenAgentv1.0.md"

    # Output directories
    patches_dir = script_dir / "patches"
    specs_dir = script_dir / "specs"

    # Create directories
    patches_dir.mkdir(exist_ok=True)
    specs_dir.mkdir(exist_ok=True)

    # Read the transcript
    logger.info(f"Reading: {transcript_path}")

    # Check if file exists and has content
    if not transcript_path.exists():
        logger.error(f"ERROR: File not found: {transcript_path}")
        logger.info("Please ensure the file is saved first!")
        return

    file_size = transcript_path.stat().st_size
    if file_size == 0:
        logger.error(f"ERROR: File is empty (0 bytes): {transcript_path}")
        logger.info("Please SAVE the file in Cursor first (Cmd+S / Ctrl+S)!")
        return

    with open(transcript_path, encoding="utf-8") as f:
        content = f.read()

    logger.info(f"File size: {len(content)} bytes, {len(content.splitlines())} lines")

    # Extract YAML blocks
    blocks = extract_yaml_blocks(content)
    logger.info(f"Found {len(blocks)} YAML spec blocks")

    if len(blocks) == 0:
        # Debug: show sample of content
        logger.debug("\nDEBUG: First 500 chars of file:")
        logger.info(content[:500])
        logger.info("\nLooking for patterns like '''yaml or '''yaml")
        logger.info(f"Found '''yaml count: {content.count(chr(39) * 3 + 'yaml')}")
        return

    patch_count = 0
    spec_count = 0

    for block in blocks:
        filename = block["filename"]
        safe_filename = sanitize_filename(filename)

        if block["is_patch"]:
            output_path = patches_dir / safe_filename
            patch_count += 1
        else:
            output_path = specs_dir / safe_filename
            spec_count += 1

        # Write the YAML content
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(block["content"])

        logger.info(
            f"  {'[PATCH]' if block['is_patch'] else '[SPEC] '} {filename} -> {output_path.name}"
        )

    logger.info("\nSummary:")
    logger.info(f"  Patches: {patch_count} files in {patches_dir}")
    logger.info(f"  Specs:   {spec_count} files in {specs_dir}")


if __name__ == "__main__":
    main()
