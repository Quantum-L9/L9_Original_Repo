#!/usr/bin/env python3
"""
Validate that README.md sections match readme_config.yaml specifications.

This script ensures documentation structure consistency.
Reads from SINGLE SOURCE OF TRUTH: config/subsystems/readme_config.yaml

MIGRATION NOTE (2026-01-25):
- Replaced per-subsystem README.meta.yaml with centralized readme_config.yaml
- All subsystem metadata now in one file
"""

# ============================================================================
__dora_meta__ = {
    "component_name": "Validate-Readme-Sections",
    "module_version": "2.0.0",
    "created_by": "L9_Codegen_Engine",
    "created_at": "2026-01-18T02:07:37Z",
    "updated_at": "2026-01-25T16:30:00Z",
    "layer": "operations",
    "domain": ".dora",
    "module_name": "validate-readme-sections",
    "type": "cli",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": ["config/subsystems/readme_config.yaml"],
        "memory_layers": [],
        "imported_by": [],
    },
}
# ============================================================================

import re
import sys
from pathlib import Path
from typing import Any

import yaml

CONFIG_PATH = "config/subsystems/readme_config.yaml"


def load_config() -> dict[str, Any]:
    """Load subsystem configuration from YAML."""
    config_file = Path(CONFIG_PATH)
    if not config_file.exists():
        print(f"❌ Config file not found: {config_file}")  # noqa: ADR-0019
        sys.exit(1)

    with open(config_file) as f:
        return yaml.safe_load(f)


def validate_readme_for_subsystem(
    key: str, sub_config: dict[str, Any], defaults: dict[str, Any]
) -> bool:
    """Validate README.md has all required sections from config."""
    subsystem_path = sub_config["path"]
    readme_file = Path(f"{subsystem_path}/README.md")

    if not readme_file.exists():
        print(f"❌ {key}: README.md missing at {subsystem_path}/README.md")  # noqa: ADR-0019
        return False

    # Get section requirements (from subsystem config or defaults)
    sections_config = sub_config.get("sections", defaults.get("sections", {}))

    if not sections_config:
        # No section requirements defined, pass
        print(f"✅ {key}: No section requirements defined (pass)")  # noqa: ADR-0019
        return True

    # Parse README
    readme_content = readme_file.read_text()

    # Extract sections from README (h2 headers starting with ##)
    # Match headers like "## Overview", "## Key Components", etc.
    readme_sections_raw = re.findall(r"^## ([^\n]+)", readme_content, re.MULTILINE)
    # Normalize: lowercase, remove spaces
    readme_sections = {
        s.lower().replace(" ", "").replace("-", "") for s in readme_sections_raw
    }

    # Check required sections
    required = {
        k.lower()
        for k, v in sections_config.items()
        if isinstance(v, dict) and v.get("required", False)
    }

    # Map config section names to possible README header variations
    section_aliases = {
        "overview": ["overview"],
        "responsibilities": ["responsibilities", "responsibilitiesandboundaries"],
        "components": ["components", "keycomponents"],
        "datamodels": ["datamodels", "datamodelsandcontracts", "models"],
        "apisurface": ["apisurface", "api", "apisurface(public)"],
        "configuration": ["configuration", "config"],
        "observability": ["observability", "logging", "metrics"],
        "testing": ["testing", "tests", "unittests"],
        "airules": ["airules", "aiusagerules", "aicollaboration"],
    }

    missing = []
    for req in required:
        # Check if any alias is present
        aliases = section_aliases.get(req, [req])
        found = any(alias in readme_sections for alias in aliases)
        if not found:
            missing.append(req)

    if missing:
        print(f"❌ {key}: Missing required sections: {', '.join(missing)}")  # noqa: ADR-0019
        print(f"   Found sections: {', '.join(sorted(readme_sections))}")  # noqa: ADR-0019
        return False

    print(f"✅ {key}: All required sections present")  # noqa: ADR-0019
    return True


def main():
    config = load_config()
    defaults = config.get("defaults", {})
    subsystems = config.get("subsystems", {})

    if not subsystems:
        print("❌ No subsystems defined in config")  # noqa: ADR-0019
        return 1

    results = []
    for key, sub_config in subsystems.items():
        if sub_config.get("skip", False):
            continue
        results.append(validate_readme_for_subsystem(key, sub_config, defaults))

    passed = sum(results)
    failed = len(results) - passed

    print(f"\n📊 Results: {passed} passed, {failed} failed")  # noqa: ADR-0019

    if not all(results):
        print("\n❌ Some README.md files missing required sections!")  # noqa: ADR-0019
        return 1

    print("\n✨ All README.md files match configuration!")  # noqa: ADR-0019
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
    "dependencies": ["config/subsystems/readme_config.yaml"],
    "tags": [".dora", "api", "cli", "config", "filesystem", "operations"],
    "keywords": ["readme", "sections", "validate"],
    "business_value": "This script ensures documentation structure consistency. Required sections from readme_config.yaml must all be present in README.md.",
    "last_modified": "2026-01-25T16:30:00Z",
    "modified_by": "README Pipeline Consolidation",
    "change_summary": "Migrated from README.meta.yaml to readme_config.yaml",
}
# ============================================================================
