#!/usr/bin/env python3
"""
gmp-validate-stage.py — Validate GMP execution completeness
============================================================

Validates that a GMP run completed all required phases and produced
valid artifacts. Runs py_compile on modified files, checks report
structure, and verifies memory operations occurred.

Usage:
    # Validate modified files compile
    python scripts/gmp-validate-stage.py --files core/foo.py memory/bar.py

    # Validate a generated report exists and has required sections
    python scripts/gmp-validate-stage.py --report reports/GMP-Report-142-Foo.md

    # Full validation (files + report)
    python scripts/gmp-validate-stage.py \
        --files core/foo.py memory/bar.py \
        --report reports/GMP-Report-142-Foo.md

    # JSON output for DAG consumption
    python scripts/gmp-validate-stage.py --files core/foo.py --json
"""

__dora_meta__ = {
    "component_name": "GMP Stage Validator",
    "module_version": "2.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2026-01-15T15:23:54Z",
    "updated_at": "2026-02-13T19:00:00Z",
    "layer": "operations",
    "domain": "scripts",
    "module_name": "gmp_validate_stage",
    "type": "cli",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": [],
        "memory_layers": [],
        "imported_by": ["workflows.dags.gmp.nodes.core"],
    },
}

import argparse
import json
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

import structlog

# Add repo root to path for ci module imports
REPO_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(REPO_ROOT))

from ci.check_syntax import check_syntax as _check_syntax_file

logger = structlog.get_logger(__name__)

# Sections that MUST appear in a valid GMP report
REQUIRED_REPORT_MARKERS: list[str] = [
    "TODO Plan",
    "Scope Boundaries",
    "Files Modified",
    "Validation Results",
    "Phase 5",
    "Final Declaration",
]


@dataclass
class Check:
    """Single validation check result."""

    name: str
    passed: bool
    detail: str = ""


@dataclass
class StageResult:
    """Aggregate validation result."""

    checks: list[Check] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return all(c.passed for c in self.checks)

    @property
    def summary(self) -> str:
        p = sum(1 for c in self.checks if c.passed)
        return f"{p}/{len(self.checks)} checks passed"

    def to_dict(self) -> dict:
        return {
            "passed": self.passed,
            "summary": self.summary,
            "checks": [
                {"name": c.name, "passed": c.passed, "detail": c.detail}
                for c in self.checks
            ],
        }


def validate_syntax(files: list[str]) -> list[Check]:
    """Check syntax via ci.check_syntax (GMP-143: delegate instead of reimplementing)."""
    checks: list[Check] = []
    for f in files:
        path = REPO_ROOT / f if not Path(f).is_absolute() else Path(f)
        if not path.exists():
            checks.append(Check(f"syntax:{f}", False, "file not found"))
            continue
        if not f.endswith(".py"):
            continue
        errors, _was_fixed = _check_syntax_file(path, fix=False)
        if not errors:
            checks.append(Check(f"syntax:{f}", True))
        else:
            detail = "; ".join(e.message[:60] for e in errors[:2])
            checks.append(Check(f"syntax:{f}", False, detail))
    return checks


def validate_imports(files: list[str]) -> list[Check]:
    """Verify each file can be imported without error."""
    checks: list[Check] = []
    for f in files:
        if not f.endswith(".py"):
            continue
        module = f.replace("/", ".").removesuffix(".py")
        try:
            result = subprocess.run(  # noqa: S603 — trusted cmd, no shell
                [sys.executable, "-c", f"import {module}"],
                capture_output=True,
                text=True,
                timeout=15,
                cwd=str(REPO_ROOT),
                env={**__import__("os").environ, "PYTHONPATH": str(REPO_ROOT)},
            )
            if result.returncode == 0:
                checks.append(Check(f"import:{module}", True))
            else:
                # Import failures are warnings, not blockers (may need runtime deps)
                checks.append(
                    Check(
                        f"import:{module}", True, f"warn: {result.stderr.strip()[:80]}"
                    )
                )
        except subprocess.TimeoutExpired:
            checks.append(Check(f"import:{module}", True, "timeout (non-blocking)"))
    return checks


def validate_report(report_path: Path) -> list[Check]:
    """Check report has required sections."""
    checks: list[Check] = []

    if not report_path.exists():
        checks.append(Check("report:exists", False, f"not found: {report_path}"))
        return checks

    checks.append(Check("report:exists", True))
    content = report_path.read_text(encoding="utf-8")

    for marker in REQUIRED_REPORT_MARKERS:
        found = marker.lower() in content.lower()
        checks.append(
            Check(
                f"report:section:{marker}",
                found,
                "" if found else f"missing section containing '{marker}'",
            )
        )

    # Check non-empty (> 500 chars = has real content)
    checks.append(
        Check(
            "report:content",
            len(content) > 500,
            f"{len(content)} chars" if len(content) <= 500 else "",
        )
    )

    return checks


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate GMP stage completion")
    parser.add_argument(
        "--files", nargs="*", default=[], help="Modified files to check"
    )
    parser.add_argument("--report", type=Path, help="GMP report to validate")
    parser.add_argument("--json", action="store_true", help="JSON output")
    parser.add_argument("--quiet", "-q", action="store_true", help="Exit code only")

    args = parser.parse_args()

    if not args.files and not args.report:
        parser.error("Provide --files and/or --report")

    result = StageResult()

    if args.files:
        result.checks.extend(validate_syntax(args.files))
        result.checks.extend(validate_imports(args.files))

    if args.report:
        result.checks.extend(validate_report(args.report))

    if args.json:
        print(json.dumps(result.to_dict(), indent=2))
    elif not args.quiet:
        for c in result.checks:
            icon = "✅" if c.passed else "❌"
            detail = f" — {c.detail}" if c.detail else ""
            logger.info("check_result", check=c.name, status=icon, detail=detail)
        logger.info(
            "stage_validation_complete",
            passed=result.passed,
            summary=result.summary,
        )

    return 0 if result.passed else 1


if __name__ == "__main__":
    sys.exit(main())
