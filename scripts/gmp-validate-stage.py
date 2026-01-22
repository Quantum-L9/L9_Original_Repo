#!/usr/bin/env python3
"""
GMP Stage Validation Script
Validates that a completed stage meets all success criteria.

Usage:
    python scripts/gmp-validate-stage.py --stage 2 --report reports/GMP-Stage-2-Report-*.md
"""

# ============================================================================
__dora_meta__ = {
    "component_name": "Gmp-Validate-Stage",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2026-01-15T15:23:54Z",
    "updated_at": "2026-01-17T23:47:56Z",
    "layer": "operations",
    "domain": "scripts",
    "module_name": "gmp-validate-stage",
    "type": "dataclass",
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
import hashlib
import json
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, List


@dataclass
class ValidationResult:
    """Result of a single validation check."""

    check_name: str
    passed: bool
    expected: Any
    actual: Any
    error_message: str = ""


class GMPStageValidator:
    """Validates GMP stage execution against canonical requirements."""

    REQUIRED_REPORT_SECTIONS = [
        "EXECUTION REPORT",
        "TODO PLAN LOCKED",
        "TODO INDEX HASH",
        "PHASE CHECKLIST STATUS",
        "FILES MODIFIED LINE RANGES",
        "TODO CHANGE MAP",
        "ENFORCEMENT VALIDATION RESULTS",
        "PHASE 5 RECURSIVE VERIFICATION",
        "FINAL DEFINITION OF DONE",
        "FINAL DECLARATION CHECKLIST",
    ]

    FINAL_DECLARATION = (
        "All phases 0–6 complete. No assumptions. No drift. "
        "Scope locked. Execution terminated. Output verified."
    )

    def __init__(self, stage_id: int, report_path: Path, config_path: Path):
        self.stage_id = stage_id
        self.report_path = report_path
        self.config_path = config_path
        self.results: List[ValidationResult] = []

        with open(config_path) as f:
            import yaml

            self.config = yaml.safe_load(f)

    def validate_all(self) -> bool:
        """Run all validation checks."""
        print(f"🔍 Validating Stage {self.stage_id}...")
        print(f"📄 Report: {self.report_path}")
        print(f"⚙️  Config: {self.config_path}\n")

        self.validate_report_structure()
        self.validate_todo_hash_integrity()
        self.validate_phase_checklist()
        self.validate_file_surfaces()
        self.validate_protected_systems()
        self.validate_test_coverage()
        self.validate_final_declaration()

        return self.print_results()

    def validate_report_structure(self):
        """Ensure report contains all 10 required sections."""
        with open(self.report_path) as f:
            report_content = f.read()

        for section in self.REQUIRED_REPORT_SECTIONS:
            found = section in report_content
            self.results.append(
                ValidationResult(
                    check_name=f"Report contains '{section}'",
                    passed=found,
                    expected=True,
                    actual=found,
                    error_message=(
                        "" if found else f"Missing required section: {section}"
                    ),
                )
            )

    def validate_todo_hash_integrity(self):
        """Verify TODO plan hash matches locked plan."""
        with open(self.report_path) as f:
            report = f.read()

        # Extract TODO plan section
        match = re.search(
            r"## TODO PLAN LOCKED\n(.*?)## TODO INDEX HASH", report, re.DOTALL
        )
        if not match:
            self.results.append(
                ValidationResult(
                    "TODO hash integrity", False, "Hash present", "Section not found"
                )
            )
            return

        todo_plan = match.group(1).strip()
        calculated_hash = hashlib.sha256(todo_plan.encode()).hexdigest()[:16]

        # Extract reported hash
        hash_match = re.search(r"## TODO INDEX HASH\n`([a-f0-9]+)`", report)
        if not hash_match:
            self.results.append(
                ValidationResult(
                    "TODO hash integrity", False, "Hash present", "Hash not found"
                )
            )
            return

        reported_hash = hash_match.group(1)
        passed = calculated_hash == reported_hash

        self.results.append(
            ValidationResult(
                "TODO hash integrity",
                passed,
                calculated_hash,
                reported_hash,
                "" if passed else "TODO plan was modified after Phase 0 lock",
            )
        )

    def validate_phase_checklist(self):
        """Ensure all phases 0-6 are marked complete."""
        with open(self.report_path) as f:
            report = f.read()

        phase_pattern = r"\[x\] Phase \d: "
        phases_complete = len(re.findall(phase_pattern, report, re.IGNORECASE))

        self.results.append(
            ValidationResult(
                "All phases (0-6) complete",
                phases_complete >= 7,
                7,
                phases_complete,
                (
                    ""
                    if phases_complete >= 7
                    else f"Only {phases_complete}/7 phases marked complete"
                ),
            )
        )

    def validate_file_surfaces(self):
        """Verify only allowed files were modified."""
        allowed_create = set(self.config["scope"]["allowed_file_surfaces"]["create"])
        allowed_modify = set(self.config["scope"]["allowed_file_surfaces"]["modify"])

        with open(self.report_path) as f:
            report = f.read()

        # Extract modified files from report
        file_pattern = r"### `(.+?)`"
        modified_files = set(re.findall(file_pattern, report))

        unauthorized = modified_files - allowed_create - allowed_modify

        self.results.append(
            ValidationResult(
                "File surface scope compliance",
                len(unauthorized) == 0,
                "Only allowed files modified",
                (
                    f"{len(unauthorized)} unauthorized files"
                    if unauthorized
                    else "All authorized"
                ),
                f"Unauthorized files: {unauthorized}" if unauthorized else "",
            )
        )

    def validate_protected_systems(self):
        """Ensure protected systems were not modified."""
        protected = self.config["scope"]["protected_systems"]

        with open(self.report_path) as f:
            report = f.read()

        violations = [sys for sys in protected if sys in report]

        self.results.append(
            ValidationResult(
                "Protected systems untouched",
                len(violations) == 0,
                "No protected systems modified",
                f"{len(violations)} violations" if violations else "None",
                f"Violations: {violations}" if violations else "",
            )
        )

    def validate_test_coverage(self):
        """Run pytest coverage and check threshold."""
        threshold = 85.0

        try:
            result = subprocess.run(
                ["pytest", "--cov=memory/consolidation", "--cov-report=json"],
                capture_output=True,
                text=True,
                timeout=60,
            )

            with open("coverage.json") as f:
                cov_data = json.load(f)
                coverage = cov_data["totals"]["percent_covered"]

            self.results.append(
                ValidationResult(
                    f"Test coverage >= {threshold}%",
                    coverage >= threshold,
                    f">= {threshold}%",
                    f"{coverage:.1f}%",
                    "" if coverage >= threshold else "Coverage below threshold",
                )
            )
        except Exception as e:
            self.results.append(
                ValidationResult(
                    "Test coverage check", False, f">= {threshold}%", "Error", str(e)
                )
            )

    def validate_final_declaration(self):
        """Check for verbatim final declaration."""
        with open(self.report_path) as f:
            report = f.read()

        found = self.FINAL_DECLARATION in report

        self.results.append(
            ValidationResult(
                "Final declaration present",
                found,
                self.FINAL_DECLARATION,
                "Present" if found else "Missing",
                "" if found else "Report must end with canonical final declaration",
            )
        )

    def print_results(self) -> bool:
        """Print validation results and return overall pass/fail."""
        print("\n" + "=" * 80)
        print(f"📊 STAGE {self.stage_id} VALIDATION RESULTS")
        print("=" * 80 + "\n")

        passed_count = sum(1 for r in self.results if r.passed)
        total_count = len(self.results)

        for result in self.results:
            status = "✅" if result.passed else "❌"
            print(f"{status} {result.check_name}")
            if not result.passed:
                print(f"   Expected: {result.expected}")
                print(f"   Actual: {result.actual}")
                if result.error_message:
                    print(f"   Error: {result.error_message}")
            print()

        print("=" * 80)
        print(f"TOTAL: {passed_count}/{total_count} checks passed")

        if passed_count == total_count:
            print("✅ STAGE VALIDATION: PASSED")
            return True
        else:
            print("❌ STAGE VALIDATION: FAILED")
            return False


def main():
    parser = argparse.ArgumentParser(description="Validate GMP stage execution")
    parser.add_argument("--stage", type=int, required=True, help="Stage number (2-8)")
    parser.add_argument(
        "--report", type=Path, required=True, help="Path to stage report"
    )
    parser.add_argument("--config", type=Path, help="Path to stage config (optional)")

    args = parser.parse_args()

    if not args.config:
        args.config = Path(f"prompts/.stage-config/stage-{args.stage}-*.yaml")

    validator = GMPStageValidator(args.stage, args.report, args.config)
    success = validator.validate_all()

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()

# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "SCR-OPER-001",
    "governance_level": "medium",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": [
        "auth",
        "cli",
        "config",
        "dataclass",
        "filesystem",
        "messaging",
        "operations",
        "scripts",
        "security",
        "serialization",
    ],
    "keywords": [
        "all",
        "checklist",
        "coverage",
        "declaration",
        "final",
        "gmp",
        "hash",
        "integrity",
    ],
    "business_value": "Provides gmp-validate-stage components including ValidationResult, GMPStageValidator",
    "last_modified": "2026-01-17T23:47:56Z",
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
