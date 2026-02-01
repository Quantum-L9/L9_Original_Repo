#!/usr/bin/env python3
"""
CI Check: Definition of Done Enforcement (ADR-0091)
===================================================

Blocks PRs/commits that don't meet Definition of Done criteria:

1. No incomplete markers (TODO, FIXME, HACK, NotImplementedError) in diff
2. Auth/config changes must have corresponding healthcheck updates
3. No placeholder code (pass # placeholder, raise NotImplementedError)

Exit codes:
- 0: DoD criteria met
- 1: DoD violations found
- 2: Script error

Created: 2026-02-01
ADR: ADR-0091 (Definition of Done)
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

# =============================================================================
# INCOMPLETE MARKERS — Block if found in diff
# =============================================================================
INCOMPLETE_MARKERS = [
    (r"#\s*TODO:", "TODO marker — complete before merging"),
    (r"#\s*FIXME:", "FIXME marker — fix before merging"),
    (r"#\s*HACK:", "HACK marker — clean up before merging"),
    (r"#\s*XXX:", "XXX marker — address before merging"),
    (r"pass\s*#\s*placeholder", "Placeholder pass statement"),
    (r"raise NotImplementedError", "NotImplementedError — implement before merging"),
    (r"\.\.\.\s*#\s*TODO", "Ellipsis placeholder"),
]

# Markers that are allowed with justification comment
ALLOWED_WITH_JUSTIFICATION = [
    r"#\s*TODO:\s*\(DEFERRED:",  # Explicitly deferred
    r"#\s*FIXME:\s*\(KNOWN:",    # Known issue, tracked
]

# =============================================================================
# AUTH CHANGE PATTERNS — Require healthcheck review
# =============================================================================
AUTH_PATTERNS = [
    r"--requirepass",
    r"REDIS_PASSWORD",
    r"POSTGRES_PASSWORD",
    r"NEO4J_PASSWORD",
    r"--auth",
    r"AUTH_TOKEN",
    r"API_KEY",
    r"SECRET_KEY",
]

HEALTHCHECK_PATTERNS = [
    r"healthcheck:",
    r"health_check",
    r"HEALTHCHECK",
]

# =============================================================================
# FILES TO SKIP
# =============================================================================
SKIP_PATTERNS = [
    r"__pycache__",
    r"\.pyc$",
    r"\.git/",
    r"node_modules/",
    r"\.env",
    r"migrations/",  # SQL migrations may have TODOs
    r"readme/adr/",  # ADRs may reference TODOs as examples
]


class DoDViolation:
    """Represents a Definition of Done violation."""

    def __init__(
        self, file: str, line_num: int, line: str, marker: str, reason: str
    ):
        self.file = file
        self.line_num = line_num
        self.line = line.strip()[:80]
        self.marker = marker
        self.reason = reason

    def __str__(self) -> str:
        return f"{self.file}:{self.line_num}: {self.reason}\n  → {self.line}"


def should_skip_file(filepath: str) -> bool:
    """Check if file should be skipped."""
    return any(re.search(pattern, filepath) for pattern in SKIP_PATTERNS)


def has_justification(line: str) -> bool:
    """Check if incomplete marker has explicit justification."""
    return any(re.search(pattern, line) for pattern in ALLOWED_WITH_JUSTIFICATION)


def get_diff_lines(base_ref: str = "origin/main") -> list[tuple[str, int, str]]:
    """Get added lines from git diff.

    Returns list of (filepath, line_num, line_content) tuples.
    """
    try:
        result = subprocess.run(
            ["git", "diff", "-U0", base_ref, "HEAD"],
            capture_output=True,
            text=True,
            check=True,
        )
    except subprocess.CalledProcessError:
        # Fallback to staged diff
        result = subprocess.run(
            ["git", "diff", "-U0", "--cached"],
            capture_output=True,
            text=True,
        )

    lines = []
    current_file = None
    current_line = 0

    for line in result.stdout.split("\n"):
        # New file header
        if line.startswith("+++ b/"):
            current_file = line[6:]
        # Line number header
        elif line.startswith("@@"):
            match = re.search(r"\+(\d+)", line)
            if match:
                current_line = int(match.group(1))
        # Added line
        elif line.startswith("+") and not line.startswith("+++"):
            if current_file and not should_skip_file(current_file):
                lines.append((current_file, current_line, line[1:]))
            current_line += 1

    return lines


def check_incomplete_markers(
    diff_lines: list[tuple[str, int, str]]
) -> list[DoDViolation]:
    """Check for incomplete markers in diff."""
    violations = []

    for filepath, line_num, line in diff_lines:
        for pattern, reason in INCOMPLETE_MARKERS:
            if re.search(pattern, line, re.IGNORECASE):
                if not has_justification(line):
                    violations.append(
                        DoDViolation(filepath, line_num, line, pattern, reason)
                    )
                break

    return violations


def check_auth_healthcheck_consistency(
    diff_lines: list[tuple[str, int, str]]
) -> list[str]:
    """Check if auth changes have corresponding healthcheck updates."""
    warnings = []

    files_with_auth_changes = set()
    files_with_healthcheck_changes = set()

    for filepath, _, line in diff_lines:
        for pattern in AUTH_PATTERNS:
            if re.search(pattern, line, re.IGNORECASE):
                files_with_auth_changes.add(filepath)
                break

        for pattern in HEALTHCHECK_PATTERNS:
            if re.search(pattern, line, re.IGNORECASE):
                files_with_healthcheck_changes.add(filepath)
                break

    # Check compose files specifically
    compose_files = {f for f in files_with_auth_changes if "compose" in f.lower()}

    if compose_files and not files_with_healthcheck_changes:
        warnings.append(
            "⚠️ Auth/password changes in compose files but no healthcheck updates.\n"
            "   Verify healthchecks don't need password parameters."
        )

    return warnings


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Check Definition of Done criteria (ADR-0091)"
    )
    parser.add_argument(
        "--base-ref",
        type=str,
        default="origin/main",
        help="Base git ref to compare against",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Treat warnings as errors",
    )
    args = parser.parse_args()

    print("=" * 70)
    print("  DEFINITION OF DONE CHECK (ADR-0091)")
    print("=" * 70)
    print()

    # Get diff
    diff_lines = get_diff_lines(args.base_ref)
    print(f"Checking {len(diff_lines)} added/modified lines...")
    print()

    exit_code = 0

    # Check incomplete markers
    violations = check_incomplete_markers(diff_lines)
    if violations:
        print(f"❌ INCOMPLETE MARKERS: Found {len(violations)} violation(s):\n")
        for v in violations:
            print(f"  {v}\n")
        exit_code = 1

    # Check auth/healthcheck consistency
    warnings = check_auth_healthcheck_consistency(diff_lines)
    if warnings:
        print("⚠️ AUTH/HEALTHCHECK WARNINGS:\n")
        for w in warnings:
            print(f"  {w}\n")
        if args.strict:
            exit_code = 1

    # Summary
    if exit_code == 0:
        print("✅ PASSED: Definition of Done criteria met")
    else:
        print("\n" + "=" * 70)
        print("DEFINITION OF DONE REQUIREMENTS (ADR-0091)")
        print("=" * 70)
        print("""
Before merging, ensure:

1. ✅ No TODO/FIXME markers (or mark as DEFERRED with justification)
2. ✅ Auth changes include healthcheck updates
3. ✅ All dependencies traced (grep -r for changed entities)
4. ✅ Tests pass (show actual output)
5. ✅ Evidence provided (not "should work")

To defer a TODO intentionally:
  # TODO: (DEFERRED: Tracked in GMP-XXX) Description here
""")

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
