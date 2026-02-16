#!/usr/bin/env python3
"""
Check for f-string SQL injection vulnerabilities (ADR-0087).

Usage:
    python3 ci/check_fstring_sql.py
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

__dora_meta__ = {
    "component_name": "CheckFstringSql",
    "module_version": "1.0.0",
    "status": "active",
}


def main() -> int:
    """Check for f-string SQL patterns."""
    print("💉 Checking for f-string SQL injection (ADR-0087)...")

    result = subprocess.run(
        [
            "grep",
            "-rnE",
            r'f"(SELECT|INSERT|UPDATE|DELETE).*\{',
            "--exclude-dir=.venv",
            "--exclude-dir=venv",
            "--exclude-dir=__pycache__",
            "--exclude-dir=tests",
            "--exclude-dir=current_work",
            "--exclude-dir=scripts",
            "--exclude-dir=igor",
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
        print("❌ ADR-0087: f-string SQL is forbidden (injection risk):")
        for v in violations[:20]:  # Limit output
            print(v)
        print()
        print("Fix: Use parameterized queries")
        print("Add '# noqa: ADR-0087' to suppress if safe")
        return 1

    print("✅ No f-string SQL found")
    return 0


__dora_footer__ = {
    "governance_level": "high",
    "compliance_required": True,
}

if __name__ == "__main__":
    sys.exit(main())
