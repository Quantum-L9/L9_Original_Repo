"""ci/check_adr_enforcement_manifest.py — Verify every accepted ADR
has an enforcement entry in config/adr-enforcement.yaml.

Exit codes:
    0 - All ADRs covered (empty enforcement[] is a warning, not a failure)
    1 - ADRs missing from manifest entirely (blocks CI)
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import yaml

MANIFEST = Path("config/adr-enforcement.yaml")
ADR_DIR = Path("readme/adr")


def main() -> int:
    manifest = yaml.safe_load(MANIFEST.read_text())

    # All ADR IDs in manifest (rules + exempt)
    covered = {str(r["adr"]).zfill(4) for r in manifest["rules"]}
    covered |= {str(r["adr"]).zfill(4) for r in manifest.get("exempt", [])}

    # All ADR files on disk
    adr_ids = set()
    for f in ADR_DIR.glob("*.md"):
        match = re.match(r"^(\d{4})-", f.name)
        if match:
            adr_ids.add(match.group(1))

    missing = sorted(adr_ids - covered)
    unenforced = [
        str(r["adr"]).zfill(4) for r in manifest["rules"] if not r.get("enforcement")
    ]

    # Missing from manifest entirely = ERROR (blocks CI)
    if missing:
        print("❌ ADRs missing from manifest entirely:")  # noqa: ADR-0019
        print(f"  {', '.join(missing)}")  # noqa: ADR-0019
        print()  # noqa: ADR-0019
        print("Fix: Run 'python3 ci/auto_stub_adr_enforcement.py' to add stubs,")  # noqa: ADR-0019
        print("     or manually add entries to config/adr-enforcement.yaml")  # noqa: ADR-0019
        return 1

    # Empty enforcement = WARNING (visible but doesn't block CI)
    if unenforced:
        print(
            f"⚠️  {len(unenforced)} ADR(s) with empty enforcement[]: {', '.join(unenforced)}"
        )  # noqa: ADR-0019
        print("   These need enforcement mechanisms added before full coverage.")  # noqa: ADR-0019

    print(f"✅ All {len(adr_ids)} ADRs covered in manifest")  # noqa: ADR-0019
    return 0


if __name__ == "__main__":
    sys.exit(main())
