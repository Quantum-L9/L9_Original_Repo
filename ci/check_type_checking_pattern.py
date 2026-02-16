#!/usr/bin/env python3
"""
Check TYPE_CHECKING pattern compliance (ADR-0002).

Files using TYPE_CHECKING must have 'from __future__ import annotations'.

Usage:
    python3 ci/check_type_checking_pattern.py           # Check only
    python3 ci/check_type_checking_pattern.py --fix     # Auto-fix violations
    python3 ci/check_type_checking_pattern.py --dry-run # Show what would be fixed
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

__dora_meta__ = {
    "component_name": "CheckTypeCheckingPattern",
    "module_version": "1.1.0",
    "status": "active",
    "layer": "operations",
    "domain": "ci",
}


def find_files_with_type_checking(repo_root: Path) -> list[Path]:
    """Find all files using TYPE_CHECKING guard."""
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

    files = []
    for line in result.stdout.splitlines():
        if line:
            files.append(repo_root / line)
    return files


def check_file(filepath: Path) -> bool:
    """Check if file has required future import. Returns True if compliant."""
    if not filepath.exists():
        return True

    content = filepath.read_text()
    return "from __future__ import annotations" in content


def fix_file(filepath: Path, dry_run: bool = False) -> bool:
    """Add future import to file. Returns True if fixed."""
    if not filepath.exists():
        return False

    content = filepath.read_text()

    if "from __future__ import annotations" in content:
        return False  # Already has it

    lines = content.split("\n")
    new_lines = []
    inserted = False

    for i, line in enumerate(lines):
        # Skip shebang and initial comments/docstrings
        if not inserted:
            # Insert after shebang if present
            if i == 0 and line.startswith("#!"):
                new_lines.append(line)
                continue

            # Insert after module docstring if present
            if line.strip().startswith('"""') or line.strip().startswith("'''"):
                # Find end of docstring
                new_lines.append(line)
                if line.count('"""') == 2 or line.count("'''") == 2:
                    # Single line docstring
                    pass
                else:
                    # Multi-line docstring - keep adding until we find the end
                    continue

            # Insert before first import or code
            if (
                line.startswith("import ")
                or line.startswith("from ")
                or (line.strip() and not line.startswith("#") and not line.startswith('"""') and not line.startswith("'''"))
            ):
                if dry_run:
                    print(f"  Would add 'from __future__ import annotations' to {filepath}")  # noqa: ADR-0019
                else:
                    new_lines.append("from __future__ import annotations")
                    new_lines.append("")
                inserted = True

        new_lines.append(line)

    if not inserted:
        # File has no imports or code yet, add at the end
        if dry_run:
            print(f"  Would add 'from __future__ import annotations' to {filepath}")  # noqa: ADR-0019
        else:
            new_lines.insert(0, "from __future__ import annotations")
            new_lines.insert(1, "")
        inserted = True

    if not dry_run and inserted:
        filepath.write_text("\n".join(new_lines))

    return inserted


def main() -> int:
    """Check TYPE_CHECKING pattern."""
    parser = argparse.ArgumentParser(
        description="Check TYPE_CHECKING pattern compliance (ADR-0002)"
    )
    parser.add_argument(
        "--fix",
        action="store_true",
        help="Auto-fix violations by adding 'from __future__ import annotations'",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be fixed without making changes",
    )
    args = parser.parse_args()

    print("🔍 Checking TYPE_CHECKING pattern (ADR-0002)...")  # noqa: ADR-0019

    repo_root = Path(__file__).parent.parent
    files = find_files_with_type_checking(repo_root)

    violations = []
    for filepath in files:
        if not check_file(filepath):
            violations.append(filepath)

    if not violations:
        print("✅ TYPE_CHECKING pattern correct")  # noqa: ADR-0019
        return 0

    if args.fix or args.dry_run:
        fixed_count = 0
        for filepath in violations:
            if fix_file(filepath, dry_run=args.dry_run):
                fixed_count += 1
                if not args.dry_run:
                    print(f"  ✅ Fixed: {filepath}")  # noqa: ADR-0019

        if args.dry_run:
            print(f"\n📋 Would fix {fixed_count} file(s)")  # noqa: ADR-0019
            return 1 if violations else 0
        print(f"\n✅ Fixed {fixed_count} file(s)")  # noqa: ADR-0019
        return 0

    # Check-only mode - report violations
    for filepath in violations:
        rel_path = filepath.relative_to(repo_root)
        print(f"❌ {rel_path}: TYPE_CHECKING requires 'from __future__ import annotations'")  # noqa: ADR-0019

    print()  # noqa: ADR-0019
    print("Fix: Run with --fix to auto-fix, or add manually:")  # noqa: ADR-0019
    print("  from __future__ import annotations")  # noqa: ADR-0019
    return 1


__dora_footer__ = {
    "governance_level": "medium",
    "compliance_required": True,
}

if __name__ == "__main__":
    sys.exit(main())
