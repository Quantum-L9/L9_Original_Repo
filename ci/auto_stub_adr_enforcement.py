#!/usr/bin/env python3
"""ci/auto_stub_adr_enforcement.py — Auto-add manifest stubs for new ADRs.

When a new ADR file is added to readme/adr/, this script detects it and
appends a stub entry to config/adr-enforcement.yaml so CI doesn't fail.

The stub is added under 'rules:' with enforcement: [] so the manifest
check passes (ADR is covered) but the empty enforcement is visible as
a gap to fill later.

Usage:
    python3 ci/auto_stub_adr_enforcement.py          # Check and auto-stub
    python3 ci/auto_stub_adr_enforcement.py --dry-run # Show what would be added
    python3 ci/auto_stub_adr_enforcement.py --exempt   # Add as exempt instead of rule

Exit codes:
    0 - No new ADRs or stubs added successfully
    1 - Error reading files
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import structlog

logger = structlog.get_logger(__name__)

L9_ROOT = Path(__file__).parent.parent
MANIFEST = L9_ROOT / "config" / "adr-enforcement.yaml"
ADR_DIR = L9_ROOT / "readme" / "adr"


def get_adr_title(adr_file: Path) -> str:
    """Extract title from ADR markdown file."""
    try:
        for line in adr_file.read_text().splitlines():
            line = line.strip()
            if line.startswith("# ") and not line.startswith("# ADR"):
                return line.lstrip("# ").strip()
            if line.startswith("# ADR"):
                # "# ADR 0012: Memory DAG Pipeline" → "Memory DAG Pipeline"
                match = re.match(r"#\s*ADR\s+\d+:\s*(.*)", line)
                if match:
                    return match.group(1).strip()
    except Exception:
        logger.debug("auto_stub_adr.title_extraction_failed", file=str(adr_file))
    return adr_file.stem.split("-", 1)[-1].replace("-", " ").title()


def get_covered_ids(manifest_text: str) -> set[str]:
    """Extract all ADR IDs already in the manifest."""
    import yaml

    data = yaml.safe_load(manifest_text)
    covered = set()
    for r in data.get("rules", []):
        covered.add(str(r["adr"]).zfill(4))
    for r in data.get("exempt", []):
        covered.add(str(r["adr"]).zfill(4))
    return covered


def get_adr_ids_on_disk() -> dict[str, Path]:
    """Get all numbered ADR files."""
    adrs = {}
    for f in ADR_DIR.glob("*.md"):
        match = re.match(r"^(\d{4})-", f.name)
        if match:
            adrs[match.group(1)] = f
    return adrs


def build_rule_stub(adr_id: str, title: str) -> str:
    """Build a YAML rule stub with empty enforcement."""
    return (
        f'\n  - adr: "{adr_id}"\n'
        f'    title: "{title}"\n'
        f"    enforcement: []  # TODO: Add enforcement mechanism\n"
    )


def build_exempt_stub(adr_id: str, title: str) -> str:
    """Build a YAML exempt stub."""
    return (
        f'\n  - adr: "{adr_id}"\n    reason: "{title} — TODO: Add exemption reason"\n'
    )


def main() -> int:
    dry_run = "--dry-run" in sys.argv
    as_exempt = "--exempt" in sys.argv

    if not MANIFEST.exists():
        print("❌ Manifest not found: config/adr-enforcement.yaml")  # noqa: ADR-0019
        return 1

    manifest_text = MANIFEST.read_text()
    covered = get_covered_ids(manifest_text)
    disk_adrs = get_adr_ids_on_disk()

    missing = sorted(set(disk_adrs.keys()) - covered)

    if not missing:
        print("✅ All ADRs already in manifest — nothing to stub")  # noqa: ADR-0019
        return 0

    stubs: list[str] = []
    for adr_id in missing:
        title = get_adr_title(disk_adrs[adr_id])
        if as_exempt:
            stub = build_exempt_stub(adr_id, title)
        else:
            stub = build_rule_stub(adr_id, title)
        stubs.append(stub)

        action = "exempt" if as_exempt else "rule (enforcement: [])"
        if dry_run:
            print(f"  Would add {adr_id}: {title} as {action}")  # noqa: ADR-0019
        else:
            print(f"  Added {adr_id}: {title} as {action}")  # noqa: ADR-0019

    if dry_run:
        print(f"\n🔍 Dry run: {len(missing)} ADR(s) would be stubbed")  # noqa: ADR-0019
        return 0

    # Append stubs to the manifest
    if as_exempt:
        # Append at end of file (exempt section is last)
        combined = manifest_text.rstrip("\n") + "".join(stubs) + "\n"
    else:
        # Insert before the exempt section
        # Find "# ===" comment block that precedes "exempt:"
        marker = "# =========================================================================\n# EXEMPT"
        idx = manifest_text.find(marker)
        if idx == -1:
            # Try simpler marker
            idx = manifest_text.find("\nexempt:")
        if idx != -1:
            combined = manifest_text[:idx] + "".join(stubs) + "\n" + manifest_text[idx:]
        else:
            combined = manifest_text.rstrip("\n") + "".join(stubs) + "\n"

    MANIFEST.write_text(combined)

    # Re-stage the manifest so the commit includes the update
    import subprocess

    subprocess.run(  # noqa: S603 — trusted cmd, no shell
        ["git", "add", str(MANIFEST)],  # noqa: S607 — trusted system command
        cwd=L9_ROOT,
        capture_output=True,
    )

    print(f"\n✅ Stubbed {len(missing)} new ADR(s) into manifest")  # noqa: ADR-0019
    print("   ⚠️  Fill in enforcement mechanisms before merging!")  # noqa: ADR-0019
    return 0


if __name__ == "__main__":
    sys.exit(main())
