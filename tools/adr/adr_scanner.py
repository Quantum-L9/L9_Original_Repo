"""
Thin wrapper around ADREnforcementValidator for CI and CLI use.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from .adr_enforcer import ADREnforcementValidator


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description="L9 ADR Repository Scanner")
    parser.add_argument(
        "--output",
        type=str,
        help="Write JSON report to this path.",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit non-zero if any violations are found.",
    )

    args = parser.parse_args()

    validator = ADREnforcementValidator(repo_root=Path.cwd())
    report = validator.scan_repo()
    data = report.to_dict()
    print(json.dumps(data, indent=2))

    if args.output:
        out = Path(args.output)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(data, indent=2), encoding="utf-8")

    if args.strict and report.total_violations > 0:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
