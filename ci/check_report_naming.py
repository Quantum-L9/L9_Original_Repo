#!/usr/bin/env python3
"""
CI Check: GMP Report Naming Convention
======================================

Enforces correct naming for GMP reports in the reports/ directory.

CORRECT FORMAT:
    GMP-Report-XXX-Description-Here.md

Where:
- GMP-Report- is the REQUIRED prefix
- XXX is the GMP number (e.g., 129, AUDIT, etc.)
- Description-Here uses kebab-case
- .md extension required

INCORRECT FORMATS (will FAIL CI):
    Report_GMP-XXX-...     # Wrong: underscore and reversed order
    GMP_Report_XXX-...     # Wrong: underscores
    gmp-report-xxx-...     # Wrong: lowercase
    GMP-XXX-Report-...     # Wrong: Report not after GMP-

Exit codes:
- 0: All report names valid
- 1: Invalid report names found
- 2: Script error

Created: 2026-01-31
"""

from __future__ import annotations

# ============================================================================
__dora_meta__ = {
    "component_name": "Check Report Naming",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2026-01-31T20:27:26Z",
    "updated_at": "2026-01-31T22:21:50Z",
    "layer": "operations",
    "domain": "ci",
    "module_name": "check_report_naming",
    "type": "cli",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": [],
        "memory_layers": [],
        "imported_by": [],
    },
}
# ============================================================================

import argparse
import re
import sys
from pathlib import Path

# Correct pattern: GMP-Report-XXX-Description.md
CORRECT_PATTERN = re.compile(r"^GMP-Report-[A-Za-z0-9]+-[A-Za-z0-9-]+\.md$")

# Invalid patterns to detect and reject (case-sensitive to catch wrong casing)
INVALID_PATTERNS = [
    (re.compile(r"^Report_GMP"), "Report_GMP format is wrong - use GMP-Report-"),
    (
        re.compile(r"^Report_gmp", re.IGNORECASE),
        "Report_ prefix is wrong - use GMP-Report-",
    ),
    (re.compile(r"^GMP_Report"), "GMP_Report with underscore - use GMP-Report-"),
    (re.compile(r"^report-gmp"), "Lowercase report-gmp - use GMP-Report-"),
    (re.compile(r"^gmp-report-"), "Lowercase gmp-report - use GMP-Report-"),
    (re.compile(r"^Gmp-Report"), "Wrong casing Gmp - use GMP-Report-"),
]

# Files to skip (not GMP reports)
SKIP_FILES = {
    "README.md",
    ".DS_Store",
}


class NamingViolation:
    """Represents a report naming violation."""

    def __init__(self, filename: str, reason: str):
        self.filename = filename
        self.reason = reason

    def __str__(self) -> str:
        return f"  ❌ {self.filename}\n     → {self.reason}"


def check_reports_dir(reports_dir: Path) -> list[NamingViolation]:
    """Check all files in reports/ for naming violations."""
    violations = []

    if not reports_dir.exists():
        return violations

    for filepath in reports_dir.iterdir():
        if not filepath.is_file():
            continue

        filename = filepath.name

        # Skip non-report files
        if filename in SKIP_FILES:
            continue

        # Skip non-markdown files
        if not filename.endswith(".md"):
            continue

        # Skip files that don't look like GMP reports
        if not any(keyword in filename.lower() for keyword in ["gmp", "report"]):
            continue

        # Check for invalid patterns first
        for pattern, reason in INVALID_PATTERNS:
            if pattern.match(filename):
                violations.append(NamingViolation(filename, reason))
                break
        else:
            # Check if it matches the correct pattern
            if not CORRECT_PATTERN.match(filename):
                # Only flag if it looks like it's trying to be a GMP report
                if "gmp" in filename.lower() and "report" in filename.lower():
                    violations.append(
                        NamingViolation(
                            filename,
                            "Does not match GMP-Report-XXX-Description.md format",
                        )
                    )

    return violations


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Check GMP report naming convention")
    parser.add_argument(
        "--base-path",
        type=Path,
        default=Path(__file__).parent.parent,
        help="Base path of the repository",
    )
    args = parser.parse_args()

    reports_dir = args.base_path / "reports"

    print("=" * 60)
    print("  GMP REPORT NAMING CHECK")
    print("=" * 60)
    print()
    print(f"Checking: {reports_dir}")
    print()

    violations = check_reports_dir(reports_dir)

    if violations:
        print(f"❌ FAILED: Found {len(violations)} naming violation(s):\n")
        for v in violations:
            print(v)
            print()

        print("=" * 60)
        print("CORRECT FORMAT:")
        print("=" * 60)
        print("""
    GMP-Report-XXX-Description-Here.md

Examples:
    ✅ GMP-Report-129-Memory-Pipeline-Governance.md
    ✅ GMP-Report-AUDIT-Combined-Orchestrators.md
    ✅ GMP-Report-130-Fix-CI-Gates.md

Wrong formats:
    ❌ Report_GMP-129-...      (reversed, underscore)
    ❌ GMP_Report_129-...      (underscores)
    ❌ gmp-report-129-...      (lowercase)
""")
        return 1

    print("✅ PASSED: All GMP report names follow correct convention")
    print("   Format: GMP-Report-XXX-Description.md")
    return 0


if __name__ == "__main__":
    sys.exit(main())
# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "CI-OPER-007",
    "governance_level": "medium",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": ["ci", "cli", "filesystem", "operations"],
    "keywords": ["check", "dir", "naming", "report", "reports", "violation"],
    "business_value": "Implements NamingViolation for check report naming functionality",
    "last_modified": "2026-01-31T22:21:50Z",
    "modified_by": "L9_Codegen_Engine",
    "change_summary": "Initial generation with DORA compliance",
}
# ============================================================================
# L9 DORA BLOCK - AUTO-UPDATED - DO NOT EDIT
# Runtime execution trace - updated automatically on every execution
# ============================================================================
__l9_trace__ = {
    "trace_id": "",
    "task": "",
    "timestamp": "",
    "patterns_used": [],
    "graph": {"nodes": [], "edges": []},
    "inputs": {},
    "outputs": {},
    "metrics": {"confidence": "", "errors_detected": [], "stability_score": ""},
}
# ============================================================================
# END L9 DORA BLOCK
# ============================================================================
