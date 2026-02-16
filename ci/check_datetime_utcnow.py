#!/usr/bin/env python3
"""
Check for deprecated datetime.utcnow() usage (ADR-0083).

This is a CI DETECTION SCRIPT that scans the codebase for violations.
It intentionally contains the patterns it detects (in grep commands).

Whitelist: This file is excluded from ADR-0083 checks because it must
contain the detection pattern `.utcnow()` to find violations.

Usage:
    python3 ci/check_datetime_utcnow.py
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

__dora_meta__ = {
    "component_name": "CheckDatetimeUtcnow",
    "module_version": "1.0.0",
    "status": "active",
}


def main() -> int:
    """Check for datetime.utcnow() usage."""
    print("🕐 Checking for deprecated datetime.utcnow() (ADR-0083)...")

    result = subprocess.run(
        [
            "grep",
            "-rn",
            r"\.utcnow()",
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
        print("❌ ADR-0083: datetime.utcnow() is deprecated:")
        for v in violations:
            print(v)
        print()
        print("Fix: Use datetime.now(UTC) instead")
        print("  from datetime import UTC, datetime")
        print("  timestamp = datetime.now(UTC)")
        return 1

    print("✅ No deprecated datetime.utcnow() usage")
    return 0


__dora_footer__ = {
    "governance_level": "medium",
    "compliance_required": True,
}

if __name__ == "__main__":
    sys.exit(main())
