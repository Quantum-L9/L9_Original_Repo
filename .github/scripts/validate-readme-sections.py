#!/usr/bin/env python3
"""
Validate that README.md sections match README.meta.yaml specifications.

This script ensures documentation structure consistency.
Required sections from README.meta.yaml must all be present in README.md.
"""

# ============================================================================
__dora_meta__ = {
    "component_name": "Validate-Readme-Sections",
    "module_version": "1.0.0",
    "created_by": "L9_Codegen_Engine",
    "created_at": "2026-01-18T02:07:37Z",
    "updated_at": "2026-01-18T02:07:37Z",
    "layer": "operations",
    "domain": ".dora",
    "module_name": "validate-readme-sections",
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

import sys
from pathlib import Path
import yaml
import re

SUBSYSTEMS = ["agents", "memory", "tools", "api"]


def validate_readme_sections(subsystem: str) -> bool:
    """Validate README.md has all required sections from meta."""
    meta_file = Path(f"l9/core/{subsystem}/README.meta.yaml")
    readme_file = Path(f"l9/core/{subsystem}/README.md")

    if not meta_file.exists():
        print(f"⚠️  {subsystem}: No README.meta.yaml found")
        return True  # Not a hard error if meta doesn't exist yet

    if not readme_file.exists():
        print(f"❌ {subsystem}: README.md missing!")
        return False

    # Parse metadata
    with open(meta_file) as f:
        meta = yaml.safe_load(f)

    # Parse README
    readme_content = readme_file.read_text()

    # Extract sections from README (h2 headers starting with #)
    readme_sections = set(re.findall(r"^## (\w+)", readme_content, re.MULTILINE))

    # Check required sections
    required = {k for k, v in meta["sections"].items() if v.get("required", False)}
    found = required & readme_sections
    missing = required - readme_sections

    if missing:
        print(f"❌ {subsystem}: Missing required sections: {', '.join(missing)}")
        return False

    print(f"✅ {subsystem}: All required sections present")
    return True


def main():
    results = [validate_readme_sections(s) for s in SUBSYSTEMS]
    if not all(results):
        sys.exit(1)
    print("\n✨ All README.md files match metadata!")
    return 0


if __name__ == "__main__":
    sys.exit(main())

# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": ".DO-OPER-001",
    "governance_level": "medium",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": [".dora", "api", "cli", "config", "filesystem", "operations"],
    "keywords": ["readme", "sections", "validate"],
    "business_value": "This script ensures documentation structure consistency. Required sections from README.meta.yaml must all be present in README.md.",
    "last_modified": "2026-01-18T02:07:37Z",
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
