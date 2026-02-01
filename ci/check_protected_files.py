#!/usr/bin/env python3
"""
CI Check: Protected Files Modification Guard
============================================

Detects modifications to protected files that require explicit human-in-loop
(HIL) approval before changes can be merged.

GOVERNANCE RULE:
Protected files are critical infrastructure that can break production deployment.
ALL changes to these files MUST be:
1. Explicitly approved by Igor (HIL_APPROVED marker in commit message)
2. Reviewed in PR before merge
3. Never auto-merged or fast-fingered

PROTECTED FILES:
- docker-compose.yml           # Local dev infrastructure
- docker-compose.prod.yml      # PRODUCTION deployment - ULTRA CRITICAL
- deploy/nginx/nginx.conf      # Nginx routing config
- .env.example                 # Environment template
- config/di_config.py          # Dependency injection wiring
- config/di_async_config.py    # Async DI wiring
- core/agents/executor.py      # Core execution loop
- memory/substrate_service.py  # Memory ingestion pipeline

COMMIT MESSAGE REQUIREMENTS:
Changes to protected files require commit message with:
  HIL_APPROVED: <reason for change>

Example:
  git commit -m "Add Redis stream proxy

  HIL_APPROVED: Adding nginx stream block to expose Redis on port 30379
  for external tool cache access. Tested locally."

Exit codes:
- 0: No protected file violations (or properly approved)
- 1: Protected files modified without approval
- 2: Script error

Created: 2026-01-31
Lesson: Agent modified docker-compose.prod.yml without permission, breaking trust.
"""

from __future__ import annotations

import argparse
import subprocess
import sys

# =============================================================================
# PROTECTED FILES LIST — Modify with extreme caution
# =============================================================================
PROTECTED_FILES = [
    # Infrastructure - ULTRA CRITICAL
    "docker-compose.yml",
    "docker-compose.prod.yml",
    "docker-compose.override.yml",
    # Nginx routing
    "deploy/nginx/nginx.conf",
    # Environment configuration
    ".env.example",
    ".env.production",
    # Core wiring
    "config/di_config.py",
    "config/di_async_config.py",
    # Critical runtime
    "core/agents/executor.py",
    "memory/substrate_service.py",
    "memory/memory_substrate_service.py",
    # Kernel loading
    "core/kernels/kernel_loader.py",
    # WebSocket orchestration
    "runtime/websocket_orchestrator.py",
]

# Approval markers in commit message
APPROVAL_MARKERS = [
    "HIL_APPROVED:",
    "IGOR_APPROVED:",
    "PROTECTED_FILE_CHANGE:",
]


class ProtectedFileViolation:
    """Represents a protected file modification without approval."""

    def __init__(self, file: str, status: str):
        self.file = file
        self.status = status  # M=modified, A=added, D=deleted

    def __str__(self) -> str:
        status_map = {"M": "Modified", "A": "Added", "D": "Deleted", "R": "Renamed"}
        action = status_map.get(self.status[0], self.status)
        return f"  [{action}] {self.file}"


def get_changed_files(base_ref: str = "origin/main") -> list[tuple[str, str]]:
    """Get list of changed files compared to base ref.

    Returns list of (status, filepath) tuples.
    """
    try:
        result = subprocess.run(
            ["git", "diff", "--name-status", base_ref, "HEAD"],
            capture_output=True,
            text=True,
            check=True,
        )
        changes = []
        for line in result.stdout.strip().split("\n"):
            if line:
                parts = line.split("\t", 1)
                if len(parts) == 2:
                    status, filepath = parts
                    changes.append((status, filepath))
        return changes
    except subprocess.CalledProcessError:
        # If no base ref, check staged files
        result = subprocess.run(
            ["git", "diff", "--name-status", "--cached"],
            capture_output=True,
            text=True,
        )
        changes = []
        for line in result.stdout.strip().split("\n"):
            if line:
                parts = line.split("\t", 1)
                if len(parts) == 2:
                    status, filepath = parts
                    changes.append((status, filepath))
        return changes


def get_commit_message() -> str:
    """Get the current commit message (HEAD or staged)."""
    try:
        result = subprocess.run(
            ["git", "log", "-1", "--format=%B"],
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout
    except subprocess.CalledProcessError:
        return ""


def has_approval_marker(commit_msg: str) -> bool:
    """Check if commit message contains approval marker."""
    for marker in APPROVAL_MARKERS:
        if marker in commit_msg:
            return True
    return False


def check_protected_files(
    changes: list[tuple[str, str]], commit_msg: str
) -> list[ProtectedFileViolation]:
    """Check if any protected files are modified without approval."""
    violations = []

    for status, filepath in changes:
        # Check if file matches any protected pattern
        for protected in PROTECTED_FILES:
            if filepath == protected or filepath.endswith(f"/{protected}"):
                # Check for approval marker
                if not has_approval_marker(commit_msg):
                    violations.append(ProtectedFileViolation(filepath, status))
                break

    return violations


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Check for protected file modifications without approval"
    )
    parser.add_argument(
        "--base-ref",
        type=str,
        default="origin/main",
        help="Base git ref to compare against",
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Show verbose output"
    )
    args = parser.parse_args()

    print("=" * 70)
    print("  PROTECTED FILES MODIFICATION CHECK")
    print("=" * 70)
    print()

    # Get changes and commit message
    changes = get_changed_files(args.base_ref)
    commit_msg = get_commit_message()

    if args.verbose:
        print(f"Checking {len(changes)} changed file(s)...")
        print(f"Protected files: {len(PROTECTED_FILES)}")
        print()

    # Check for violations
    violations = check_protected_files(changes, commit_msg)

    if violations:
        print(
            f"❌ FAILED: {len(violations)} protected file(s) modified without approval:\n"
        )
        for v in violations:
            print(v)

        print("\n" + "=" * 70)
        print("PROTECTED FILES REQUIRE HUMAN-IN-LOOP (HIL) APPROVAL")
        print("=" * 70)
        print("""
These files are critical infrastructure. Unauthorized changes can break
production deployment and waste hours of debugging.

TO FIX:

1. If change is intentional and approved, amend commit message:

   git commit --amend -m "Your commit message

   HIL_APPROVED: Reason for changing protected file"

2. If change was accidental, revert it:

   git checkout origin/main -- <protected_file>

3. If you're an AI agent: STOP. Ask Igor for approval BEFORE modifying
   any protected file. Show the proposed changes and wait for "approved".

PROTECTED FILES LIST:
""")
        for pf in PROTECTED_FILES:
            print(f"  - {pf}")

        print()
        return 1

    # Check if any protected files were touched (even with approval)
    approved_changes = []
    for status, filepath in changes:
        for protected in PROTECTED_FILES:
            if filepath == protected or filepath.endswith(f"/{protected}"):
                approved_changes.append(filepath)
                break

    if approved_changes:
        print("✅ PASSED: Protected file changes are approved")
        print("   Approval marker found in commit message")
        print("   Changed protected files:")
        for f in approved_changes:
            print(f"     - {f}")
    else:
        print("✅ PASSED: No protected files modified")

    return 0


if __name__ == "__main__":
    sys.exit(main())
