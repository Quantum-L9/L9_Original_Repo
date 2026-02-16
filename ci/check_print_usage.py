#!/usr/bin/env python3
"""
Check for print() usage in production code (ADR-0019).

Usage:
    python3 ci/check_print_usage.py
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

__dora_meta__ = {
    "component_name": "CheckPrintUsage",
    "module_version": "1.0.0",
    "status": "active",
}


def main() -> int:
    """Check for print() in production code."""
    print("🖨️ Checking for print() in production code (ADR-0019)...")

    result = subprocess.run(
        ["grep", "-rn", r"^\s*print(",
         "--exclude-dir=.venv", "--exclude-dir=venv", "--exclude-dir=__pycache__",
         "--exclude-dir=tests", "--exclude-dir=ci", "--exclude-dir=scripts", "--exclude-dir=tools",
         "--exclude-dir=current_work", "--exclude-dir=mcp_memory", "--exclude-dir=local_dashboard",
         "--exclude-dir=.cursor", "--exclude-dir=workflows", "--exclude-dir=igor",
         "--include=*.py", "."],
        capture_output=True, text=True, cwd=Path(__file__).parent.parent
    )

    # Additional post-filter exclusions
    excludes = [
        "# noqa", "__main__.py",
        "agents/cursor/",
        "core/codegen/"  # CLI executors use print() for user feedback
    ]

    violations = []
    for line in result.stdout.splitlines():
        if not any(exc in line for exc in excludes):
            violations.append(line)

    if violations:
        print("❌ ADR-0019: print() forbidden in production code:")
        for v in violations[:20]:  # Limit output
            print(v)
        print()
        print("Fix: Use structlog.get_logger() instead")
        print("Add '# noqa: ADR-0019' to suppress if necessary")
        return 1

    print("✅ No print() in production code")
    return 0


__dora_footer__ = {
    "governance_level": "medium",
    "compliance_required": True,
}

if __name__ == "__main__":
    sys.exit(main())
