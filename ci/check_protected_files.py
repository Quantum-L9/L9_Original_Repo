#!/usr/bin/env python3
"""
CI Check: Protected Files (Gate 16)
====================================

Enforces config/policies/protected_files.yaml by detecting modifications
to protected files in the current commit/PR without HIL_APPROVED marker.

Uses git diff to find changed files and matches them against:
  - lcto_controlled paths
  - subsystem file lists
  - protected_patterns (fnmatch-style globs)

If protected files are modified, the commit message must contain:
  HIL_APPROVED: <reason>

Run: python3 ci/check_protected_files.py
Exit: 0 = pass, 1 = violations found
"""

from __future__ import annotations

__dora_meta__ = {
    "component_name": "Check Protected Files",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2026-02-16T00:00:00Z",
    "updated_at": "2026-02-16T00:00:00Z",
    "layer": "operations",
    "domain": "ci",
    "module_name": "check_protected_files",
    "type": "ci_gate",
    "status": "active",
}

import fnmatch
import subprocess
import sys
from pathlib import Path

import yaml

L9_ROOT = Path(__file__).resolve().parent.parent
POLICY_FILE = L9_ROOT / "config" / "policies" / "protected_files.yaml"


def get_changed_files() -> list[str]:
    """Get files changed in current commit or PR."""
    # Try PR diff first (GitHub Actions sets GITHUB_BASE_REF)
    import os

    base_ref = os.environ.get("GITHUB_BASE_REF")
    if base_ref:
        result = subprocess.run(  # noqa: S603 — trusted cmd, no shell
            ["git", "diff", "--name-only", f"origin/{base_ref}...HEAD"],  # noqa: S607 — trusted system command
            capture_output=True,
            text=True,
            cwd=L9_ROOT,
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip().splitlines()

    # Fall back to last commit diff
    result = subprocess.run(
        ["git", "diff", "--name-only", "HEAD~1", "HEAD"],  # noqa: S607 — trusted system command
        capture_output=True,
        text=True,
        cwd=L9_ROOT,
    )
    if result.returncode == 0 and result.stdout.strip():
        return result.stdout.strip().splitlines()

    # Fall back to staged files (pre-commit context)
    result = subprocess.run(
        ["git", "diff", "--cached", "--name-only"],  # noqa: S607 — trusted system command
        capture_output=True,
        text=True,
        cwd=L9_ROOT,
    )
    if result.returncode == 0:
        return result.stdout.strip().splitlines()

    return []


def get_commit_message() -> str:
    """Get the latest commit message."""
    result = subprocess.run(
        ["git", "log", "-1", "--format=%B"],  # noqa: S607 — trusted system command
        capture_output=True,
        text=True,
        cwd=L9_ROOT,
    )
    return result.stdout.strip() if result.returncode == 0 else ""


def load_protected_paths(policy: dict) -> set[str]:
    """Extract all explicitly protected file paths from policy."""
    paths: set[str] = set()

    pf = policy.get("protected_files", {})

    # lcto_controlled
    for entry in pf.get("lcto_controlled", []):
        if "path" in entry:
            paths.add(entry["path"])

    # subsystems
    for _subsystem, info in pf.get("subsystems", {}).items():
        for f in info.get("files", []):
            paths.add(f)

    return paths


def load_protected_patterns(policy: dict) -> list[str]:
    """Extract fnmatch-style patterns from policy."""
    pf = policy.get("protected_files", {})
    return [
        entry["pattern"]
        for entry in pf.get("protected_patterns", [])
        if "pattern" in entry
    ]


def main() -> int:
    if not POLICY_FILE.exists():
        print(f"⚠️  Policy file not found: {POLICY_FILE}")
        print("   Skipping protected files check")
        return 0

    policy = yaml.safe_load(POLICY_FILE.read_text())
    protected_paths = load_protected_paths(policy)
    protected_patterns = load_protected_patterns(policy)

    changed_files = get_changed_files()
    if not changed_files:
        print("✅ No changed files detected — protected files check passed")
        return 0

    # Find violations
    violations: list[tuple[str, str]] = []
    for f in changed_files:
        # Exact path match
        if f in protected_paths:
            violations.append((f, "explicit protected path"))
            continue

        # Pattern match
        for pattern in protected_patterns:
            if fnmatch.fnmatch(f, pattern):
                violations.append((f, f"matches pattern '{pattern}'"))
                break

    if not violations:
        print(f"✅ {len(changed_files)} changed files checked — no protected file violations")
        return 0

    # Check for HIL_APPROVED marker in commit message
    commit_msg = get_commit_message()
    if "HIL_APPROVED:" in commit_msg:
        print(f"⚠️  {len(violations)} protected file(s) modified — HIL_APPROVED marker found")
        for path, reason in violations:
            print(f"   {path} ({reason})")
        print(f"   Approval: {commit_msg.split('HIL_APPROVED:')[1].strip().splitlines()[0]}")
        return 0

    # Violations without approval
    print(f"❌ {len(violations)} protected file(s) modified without HIL_APPROVED marker:")
    print()
    for path, reason in violations:
        print(f"   {path} ({reason})")
    print()
    print("Fix: Add 'HIL_APPROVED: <reason>' to your commit message")
    print("     or revert changes to protected files.")
    print()
    print("Protected files policy: config/policies/protected_files.yaml")
    return 1


if __name__ == "__main__":
    sys.exit(main())

__dora_footer__ = {
    "governance_level": "high",
    "compliance_required": True,
    "tags": ["ci", "governance", "protected-files", "security"],
    "keywords": ["protected", "files", "hil", "approval", "gate"],
}
