#!/usr/bin/env python3
"""ci/check_dag_validation_single_point.py — ADR-0012 enforcement.

Ensures packet validation occurs ONLY in the canonical pipeline:
  intake_node (substrate_dag.py) → substrate_service.py → ingestion.py

Any PacketValidator.validate() call outside these files (and tests)
indicates a duplicate validation path that violates ADR-0012's
Single Pipeline Principle.

Exit codes:
    0 - No violations
    1 - Duplicate validation paths found
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

L9_ROOT = Path(__file__).parent.parent

# Files ALLOWED to call PacketValidator.validate()
ALLOWED_CALLERS = {
    "memory/substrate_dag.py",
    "memory/substrate_service.py",
    "memory/ingestion.py",
    "memory/validators/packet_validator.py",
}

# Directories where validation calls are always allowed
ALLOWED_DIRS = {
    "tests",
    "codegen",
    ".backup",
    "current_work",
    "ci",
    "scripts",
    "igor",
    "tools",
}

SKIP_DIRS = {
    ".git",
    ".venv",
    "venv",
    "__pycache__",
    "node_modules",
    ".pytest_cache",
    ".mypy_cache",
}

# Patterns that indicate duplicate validation
VALIDATION_PATTERNS = [
    re.compile(r"PacketValidator\.validate\("),
    re.compile(r"PacketValidator\(\)\.validate\("),
]

# noqa marker for intentional exceptions
NOQA_MARKER = "# noqa: ADR-0012"


def main() -> int:
    violations: list[str] = []

    for pyfile in sorted(L9_ROOT.rglob("*.py")):
        if not pyfile.is_file():
            continue

        # Skip excluded directories
        if any(d in pyfile.parts for d in SKIP_DIRS):
            continue

        rel = str(pyfile.relative_to(L9_ROOT))

        # Skip allowed directories
        if any(rel.startswith(d + "/") or rel.startswith(d + "\\") for d in ALLOWED_DIRS):
            continue

        # Skip allowed files
        if rel.replace("\\", "/") in ALLOWED_CALLERS:
            continue

        try:
            content = pyfile.read_text(encoding="utf-8")
        except (UnicodeDecodeError, PermissionError):
            continue

        lines = content.splitlines()
        in_docstring = False
        for line_num, line in enumerate(lines, 1):
            stripped = line.strip()

            # Track triple-quote docstrings
            triple_count = stripped.count('"""') + stripped.count("'''")
            if triple_count == 1:
                in_docstring = not in_docstring
                continue
            if in_docstring:
                continue

            # Skip comment-only lines
            if stripped.startswith("#"):
                continue

            # Skip noqa lines
            if NOQA_MARKER in line:
                continue

            for pattern in VALIDATION_PATTERNS:
                if pattern.search(line):
                    violations.append(
                        f"  {rel}:{line_num}: {stripped}"
                    )

    if violations:
        print("❌ ADR-0012: Duplicate validation paths detected!")  # noqa: ADR-0019 - CI script
        print()  # noqa: ADR-0019
        print("PacketValidator.validate() must only be called from:")  # noqa: ADR-0019
        print("  - memory/substrate_dag.py (intake_node)")  # noqa: ADR-0019
        print("  - memory/substrate_service.py (write_packet)")  # noqa: ADR-0019
        print("  - memory/ingestion.py (ingest_packet)")  # noqa: ADR-0019
        print()  # noqa: ADR-0019
        print(f"Found {len(violations)} violation(s):")  # noqa: ADR-0019
        for v in violations:
            print(v)  # noqa: ADR-0019
        print()  # noqa: ADR-0019
        print("Fix: Remove duplicate validation. Use ingest_packet() instead.")  # noqa: ADR-0019
        print("Escape hatch: Add '# noqa: ADR-0012' if intentional.")  # noqa: ADR-0019
        return 1

    print("✅ ADR-0012: All validation flows through canonical pipeline")  # noqa: ADR-0019
    return 0


if __name__ == "__main__":
    sys.exit(main())
