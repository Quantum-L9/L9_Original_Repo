#!/usr/bin/env python3
"""
CI Check: Policy YAML Schema Validation
=========================================

Validates all policy YAML files in config/policies/ parse correctly
and contain required fields for their policy type.

Required fields per policy type:
  - All: id, version
  - Policy files (with 'policies' key): each policy needs id, effect, priority, subjects
  - Tool risk files: tool_risk_classification with high_risk list
  - Rate limit files: rate_limits with at least one category
  - Protected files: protected_files with at least one section

Run: python3 ci/validate_policy_schemas.py
Exit: 0 = pass, 1 = validation errors found
"""

from __future__ import annotations

__dora_meta__ = {
    "component_name": "Validate Policy Schemas",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2026-02-16T00:00:00Z",
    "updated_at": "2026-02-16T00:00:00Z",
    "layer": "operations",
    "domain": "ci",
    "module_name": "validate_policy_schemas",
    "type": "ci_gate",
    "status": "active",
}

import sys
from pathlib import Path

import yaml

L9_ROOT = Path(__file__).resolve().parent.parent
POLICIES_DIR = L9_ROOT / "config" / "policies"


def validate_base_fields(data: dict, filepath: Path) -> list[str]:
    """Validate fields required by all policy files."""
    errors: list[str] = []
    if "id" not in data:
        errors.append(f"{filepath.name}: missing required field 'id'")
    if "version" not in data:
        errors.append(f"{filepath.name}: missing required field 'version'")
    return errors


def validate_policies_list(data: dict, filepath: Path) -> list[str]:
    """Validate the 'policies' list if present."""
    errors: list[str] = []
    policies = data.get("policies")
    if policies is None:
        return errors

    if not isinstance(policies, list):
        errors.append(f"{filepath.name}: 'policies' must be a list")
        return errors

    required_policy_fields = {"id", "effect", "priority", "subjects"}
    valid_effects = {"allow", "deny"}

    for i, policy in enumerate(policies):
        if not isinstance(policy, dict):
            errors.append(f"{filepath.name}: policies[{i}] must be a dict")
            continue

        pid = policy.get("id", f"index-{i}")
        missing = required_policy_fields - set(policy.keys())
        if missing:
            errors.append(
                f"{filepath.name}: policy '{pid}' missing fields: {', '.join(sorted(missing))}"
            )

        effect = policy.get("effect")
        if effect and effect not in valid_effects:
            errors.append(
                f"{filepath.name}: policy '{pid}' has invalid effect '{effect}' (must be allow/deny)"
            )

        priority = policy.get("priority")
        if priority is not None and not isinstance(priority, (int, float)):
            errors.append(
                f"{filepath.name}: policy '{pid}' priority must be numeric, got {type(priority).__name__}"
            )

    return errors


def validate_tool_risk(data: dict, filepath: Path) -> list[str]:
    """Validate tool risk classification structure."""
    errors: list[str] = []
    trc = data.get("tool_risk_classification")
    if trc is None:
        return errors

    if not isinstance(trc, dict):
        errors.append(f"{filepath.name}: 'tool_risk_classification' must be a dict")
        return errors

    high_risk = trc.get("high_risk")
    if high_risk is not None:
        if not isinstance(high_risk, list):
            errors.append(f"{filepath.name}: 'high_risk' must be a list")
        else:
            for i, tool in enumerate(high_risk):
                if isinstance(tool, dict) and "tool_id" not in tool:
                    errors.append(f"{filepath.name}: high_risk[{i}] missing 'tool_id'")

    igor = trc.get("igor_approval_required")
    if igor is not None and not isinstance(igor, list):
        errors.append(f"{filepath.name}: 'igor_approval_required' must be a list")

    return errors


def validate_rate_limits(data: dict, filepath: Path) -> list[str]:
    """Validate rate limits structure."""
    errors: list[str] = []
    rl = data.get("rate_limits")
    if rl is None:
        return errors

    if not isinstance(rl, dict):
        errors.append(f"{filepath.name}: 'rate_limits' must be a dict")
        return errors

    if len(rl) == 0:
        errors.append(
            f"{filepath.name}: 'rate_limits' is empty — must have at least one category"
        )

    return errors


def validate_protected_files(data: dict, filepath: Path) -> list[str]:
    """Validate protected files structure."""
    errors: list[str] = []
    pf = data.get("protected_files")
    if pf is None:
        return errors

    if not isinstance(pf, dict):
        errors.append(f"{filepath.name}: 'protected_files' must be a dict")
        return errors

    # At least one section should exist
    sections = {"lcto_controlled", "subsystems", "protected_patterns"}
    found = sections & set(pf.keys())
    if not found:
        errors.append(
            f"{filepath.name}: 'protected_files' must have at least one of: {', '.join(sorted(sections))}"
        )

    return errors


def validate_scope_access(data: dict, filepath: Path) -> list[str]:
    """Validate memory scope access matrix."""
    errors: list[str] = []
    sam = data.get("scope_access_matrix")
    if sam is None:
        return errors

    if not isinstance(sam, dict):
        errors.append(f"{filepath.name}: 'scope_access_matrix' must be a dict")
        return errors

    for caller, config in sam.items():
        if not isinstance(config, dict):
            errors.append(
                f"{filepath.name}: scope_access_matrix['{caller}'] must be a dict"
            )
            continue
        if "allowed_scopes" not in config:
            errors.append(
                f"{filepath.name}: scope_access_matrix['{caller}'] missing 'allowed_scopes'"
            )

    return errors


def main() -> int:
    if not POLICIES_DIR.exists():
        print(f"⚠️  Policies directory not found: {POLICIES_DIR}")
        return 0

    yaml_files = sorted(POLICIES_DIR.glob("*.yaml"))
    if not yaml_files:
        print("⚠️  No policy YAML files found in config/policies/")
        return 0

    all_errors: list[str] = []
    files_checked = 0

    for filepath in yaml_files:
        files_checked += 1

        # Parse YAML
        try:
            data = yaml.safe_load(filepath.read_text())
        except yaml.YAMLError as e:
            all_errors.append(f"{filepath.name}: YAML parse error: {e}")
            continue

        if not isinstance(data, dict):
            all_errors.append(
                f"{filepath.name}: root must be a YAML mapping, got {type(data).__name__}"
            )
            continue

        # Base field validation
        all_errors.extend(validate_base_fields(data, filepath))

        # Type-specific validation
        all_errors.extend(validate_policies_list(data, filepath))
        all_errors.extend(validate_tool_risk(data, filepath))
        all_errors.extend(validate_rate_limits(data, filepath))
        all_errors.extend(validate_protected_files(data, filepath))
        all_errors.extend(validate_scope_access(data, filepath))

    if all_errors:
        print(f"❌ {len(all_errors)} policy schema error(s) in {files_checked} files:")
        print()
        for error in all_errors:
            print(f"   {error}")
        print()
        print("Fix: Correct the policy YAML files in config/policies/")
        return 1

    print(f"✅ All {files_checked} policy YAML files validated successfully")
    return 0


if __name__ == "__main__":
    sys.exit(main())

__dora_footer__ = {
    "governance_level": "medium",
    "compliance_required": True,
    "tags": ["ci", "governance", "policy", "yaml", "validation"],
    "keywords": ["policy", "schema", "validate", "yaml"],
}
