#!/usr/bin/env python3
"""
Check for pickle usage (ADR-0088).

This is a CI DETECTION SCRIPT that scans the codebase for violations.
It intentionally contains the pattern `pickle.load` in grep commands.

Whitelist: This file is excluded from ADR-0088 checks because it must
contain the detection pattern to find violations.

Pickle is forbidden for security reasons - use JSON or msgpack instead.

Usage:
    python3 ci/check_pickle_usage.py
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

__dora_meta__ = {
    "component_name": "CheckPickleUsage",
    "module_version": "1.0.0",
    "status": "active",
}


def main() -> int:
    """Check for pickle.load usage."""
    print("🥒 Checking for pickle usage (ADR-0088)...")

    result = subprocess.run(
        [
            "grep",
            "-rn",
            r"pickle\.load",
            "--exclude-dir=.venv",
            "--exclude-dir=venv",
            "--exclude-dir=__pycache__",
            "--exclude-dir=tests",
            "--exclude-dir=current_work",
            "--exclude-dir=ci",
            "--include=*.py",
            ".",
        ],
        capture_output=True,
        text=True,
        cwd=Path(__file__).parent.parent,
    )

    excludes = ["# noqa"]

    violations = []
    for line in result.stdout.splitlines():
        if not any(exc in line for exc in excludes):
            violations.append(line)

    if violations:
        print("❌ ADR-0088: pickle is forbidden (security):")
        for v in violations:
            print(v)
        print()
        print("Fix: Use json.loads() or msgpack instead")
        return 1

    print("✅ No pickle usage found")
    return 0


__dora_footer__ = {
    "governance_level": "medium",
    "compliance_required": True,
}

if __name__ == "__main__":
    sys.exit(main())
