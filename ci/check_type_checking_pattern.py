#!/usr/bin/env python3
"""
Check TYPE_CHECKING pattern compliance (ADR-0002).

Files using TYPE_CHECKING must have 'from __future__ import annotations'.

Usage:
    python3 ci/check_type_checking_pattern.py
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

__dora_meta__ = {
    "component_name": "CheckTypeCheckingPattern",
    "module_version": "1.0.0",
    "status": "active",
}


def main() -> int:
    """Check TYPE_CHECKING pattern."""
    print("🔍 Checking TYPE_CHECKING pattern (ADR-0002)...")

    repo_root = Path(__file__).parent.parent

    # Find files with TYPE_CHECKING
    result = subprocess.run(
        [
            "grep",
            "-rl",
            "if TYPE_CHECKING:",
            "--exclude-dir=.venv",
            "--exclude-dir=venv",
            "--exclude-dir=__pycache__",
            "--exclude-dir=tests",
            "--exclude-dir=current_work",
            "--include=*.py",
            ".",
        ],
        capture_output=True,
        text=True,
        cwd=repo_root,
    )

    excludes = []  # All filtering done at grep level

    files_with_type_checking = []
    for line in result.stdout.splitlines():
        if line and not any(exc in line for exc in excludes):
            files_with_type_checking.append(line)

    failed = False
    for filepath in files_with_type_checking:
        full_path = repo_root / filepath
        if not full_path.exists():
            continue

        content = full_path.read_text()
        if "from __future__ import annotations" not in content:
            print(
                f"❌ {filepath}: TYPE_CHECKING requires 'from __future__ import annotations'"
            )
            failed = True

    if failed:
        print()
        print("Fix: Add at top of file:")
        print("  from __future__ import annotations")
        return 1

    print("✅ TYPE_CHECKING pattern correct")
    return 0


__dora_footer__ = {
    "governance_level": "medium",
    "compliance_required": True,
}

if __name__ == "__main__":
    sys.exit(main())
