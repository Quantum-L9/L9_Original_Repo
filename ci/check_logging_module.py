#!/usr/bin/env python3
"""
Check for stdlib logging module usage (ADR-0019).

Use structlog instead of stdlib logging.

Usage:
    python3 ci/check_logging_module.py
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path



def main() -> int:
    """Check for stdlib logging imports."""
    print("📝 Checking for stdlib logging module (ADR-0019)...")

    result = subprocess.run(
        ["grep", "-rn", r"^import logging$\|^from logging import",
         "--exclude-dir=.venv", "--exclude-dir=venv", "--exclude-dir=__pycache__",
         "--exclude-dir=tests", "--exclude-dir=ci", "--exclude-dir=scripts",
         "--exclude-dir=current_work", "--exclude-dir=.cursor", "--exclude-dir=workflows", "--exclude-dir=igor",
         "--include=*.py", "."],
        capture_output=True, text=True, cwd=Path(__file__).parent.parent
    )

    excludes = [
        "config/logging",
        "core/observability", "# noqa"
    ]

    violations = []
    for line in result.stdout.splitlines():
        if not any(exc in line for exc in excludes):
            violations.append(line)

    if violations:
        print("❌ ADR-0019: stdlib logging module forbidden:")
        for v in violations[:20]:
            print(v)
        print()
        print("Fix: Use structlog instead")
        print("  import structlog")
        print("  logger = structlog.get_logger()")
        return 1

    print("✅ No stdlib logging module usage")
    return 0



if __name__ == "__main__":
    sys.exit(main())
