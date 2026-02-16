#!/usr/bin/env python3
"""
Validate that protected files are not modified without approval.

Protected files include LCTO-owned paths, subsystem-owned paths, and patterns
(Dockerfile, .github/workflows/*.yml, runtime/*, Makefile, etc.). L (CTO) must
follow the same protected-file policy as everyone else—no exemption.

This runs on every PR and blocks changes to protected surfaces.

Approval bypass: Include one of the following markers in the commit message
to allow protected file changes:
  HIL_APPROVED: <reason>
  IGOR_APPROVED: <reason>
  PROTECTED_FILE_CHANGE: <reason>

GMP-143: Consolidated from ci/check_protected_files.py (deleted) into this
single canonical script. Protected file list sourced from
core.governance.protected_files_policy (config/policies/protected_files.yaml).
"""

# ============================================================================
__dora_meta__ = {
    "component_name": "Validate-Protected-Files",
    "module_version": "1.0.0",
    "created_by": "L9_Codegen_Engine",
    "created_at": "2026-01-18T02:07:37Z",
    "updated_at": "2026-01-18T02:07:37Z",
    "layer": "operations",
    "domain": ".dora",
    "module_name": "validate-protected-files",
    "type": "cli",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": ["Redis"],
        "memory_layers": [],
        "imported_by": [],
    },
}
# ============================================================================

import subprocess
import sys
from pathlib import Path

# Add project root to path for imports
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# GMP-104: Load protected files from config/policies/protected_files.yaml
from core.governance.protected_files_policy import (
    get_all_protected_files,
    get_lcto_controlled_files,
    get_subsystem_protected_files,
    is_protected,
)

PROTECTED_BY_LCTO = get_lcto_controlled_files()
SUBSYSTEM_PROTECTED = get_subsystem_protected_files()
ALL_PROTECTED = get_all_protected_files()

# GMP-143: Approval markers (merged from ci/check_protected_files.py)
APPROVAL_MARKERS = [
    "HIL_APPROVED:",
    "IGOR_APPROVED:",
    "PROTECTED_FILE_CHANGE:",
]


def get_changed_files() -> set[str]:
    """Get files changed in current PR (assumes git environment)."""
    try:
        # Get diff between main and HEAD
        result = subprocess.run(
            ["git", "diff", "--name-only", "origin/main...HEAD"],  # noqa: S607 — trusted system command
            capture_output=True,
            text=True,
            check=True,
        )
        return (
            set(result.stdout.strip().split("\n")) if result.stdout.strip() else set()
        )
    except subprocess.CalledProcessError:
        # Fallback if no git history (e.g., first PR)
        return set()


def get_commit_message() -> str:
    """Get the HEAD commit message for approval marker check."""
    try:
        result = subprocess.run(
            ["git", "log", "-1", "--format=%B"],  # noqa: S607 — trusted system command
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout
    except subprocess.CalledProcessError:
        return ""


def has_approval_marker(commit_msg: str) -> bool:
    """Check if commit message contains an approval marker."""
    return any(marker in commit_msg for marker in APPROVAL_MARKERS)


def validate_protected_files() -> bool:
    """Check that protected files were not modified without approval."""
    changed = get_changed_files()
    violations = {f for f in changed if is_protected(f)}

    if not violations:
        print("✅ No protected files modified")  # noqa: ADR-0019
        return True

    # GMP-143: Check for approval bypass in commit message
    commit_msg = get_commit_message()
    if has_approval_marker(commit_msg):
        print("✅ Protected file changes are APPROVED via commit message marker")  # noqa: ADR-0019
        for f in sorted(violations):
            print(f"   - {f}")  # noqa: ADR-0019
        return True

    # No approval — report violations
    print("❌ PROTECTED FILES MODIFIED WITHOUT APPROVAL:")  # noqa: ADR-0019
    for f in sorted(violations):
        subsystem = None
        for sub, files in SUBSYSTEM_PROTECTED.items():
            if f in files:
                subsystem = f"(Subsystem: {sub})"
                break

        lcto = " (LCTO-controlled)" if f in PROTECTED_BY_LCTO else ""
        print(f"   - {f}{lcto}{subsystem or ''}")  # noqa: ADR-0019

    print("\n📋 To modify protected files, you must either:")  # noqa: ADR-0019
    print("   1. Get approval from L (CTO) and add to commit message:")  # noqa: ADR-0019
    print("      HIL_APPROVED: <reason for change>")  # noqa: ADR-0019
    print("   2. Or revert the change:")  # noqa: ADR-0019
    print("      git checkout origin/main -- <protected_file>")  # noqa: ADR-0019
    return False


def main():
    if not validate_protected_files():
        sys.exit(1)
    print("\n✨ Protected file validation passed!")  # noqa: ADR-0019
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
    "tags": [".dora", "cli", "filesystem", "operations", "realtime", "subprocess"],
    "keywords": ["changed", "files", "protected", "validate"],
    "business_value": "This runs on every PR and blocks changes to protected surfaces.",
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
