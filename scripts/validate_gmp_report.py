#!/usr/bin/env python3
"""
validate_gmp_report.py — GMP Report Verification Script
=========================================================

Validates GMP reports against gmp-report-contract.yaml.
Called automatically after report generation to ensure compliance.

Usage:
    # Validate a single report
    python scripts/validate_gmp_report.py reports/GMP-Report-110-Task.md

    # Validate all reports
    python scripts/validate_gmp_report.py --all

    # Validate and output JSON
    python scripts/validate_gmp_report.py reports/GMP-Report-110-Task.md --json

    # Strict mode (warnings become errors)
    python scripts/validate_gmp_report.py reports/GMP-Report-110-Task.md --strict

Version: 1.0.0
"""

import argparse
import json
import os
import re
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Any

import yaml

# ============================================================================
# Configuration
# ============================================================================

REPO_ROOT = Path(os.getenv("L9_REPO_ROOT", "/Users/ib-mac/Projects/L9"))
REPORTS_DIR = REPO_ROOT / "reports"
CONTRACT_PATH = (
    REPO_ROOT / "agents" / "cursor" / "gmp_protocol" / "gmp-report-contract.yaml"
)

# Contract constants (fallback if YAML unavailable)
VALID_TIERS = ["KERNEL_TIER", "RUNTIME_TIER", "INFRA_TIER", "UX_TIER"]
VALID_ACTIONS = ["CREATE", "INSERT", "REPLACE", "DELETE", "WRAP"]
VALID_STATUSES = ["✅ COMPLETE", "⚠️ PARTIAL", "❌ FAILED"]
VALID_TODO_STATUSES = ["✅", "❌", "⚠️"]
VALID_PHASE_STATUSES = ["✅", "❌", "⚠️", "N/A"]
VALID_VALIDATION_RESULTS = ["✅", "✅ PASS", "❌", "❌ FAIL", "⚠️ SKIP", "N/A"]
MINIMUM_VALIDATION_GATES = ["py_compile", "import test"]
REQUIRED_PHASES = [
    (0, "PLANNING"),
    (1, "BASELINE"),
    (2, "IMPLEMENTATION"),
    (3, "ENFORCEMENT"),
    (4, "VALIDATION"),
    (5, "RECURSION"),
    (6, "FINALIZATION"),
]
REQUIRED_VERIFICATION_ITEMS = [
    "All TODOs implemented",
    "No unauthorized changes",
    "No scope drift",
    "Protected files documented",
]
DECLARATION_MUST_CONTAIN = [
    "Phases 0-6 complete",
    "No assumptions",
    "No drift",
]

# ============================================================================
# Data Classes
# ============================================================================


@dataclass
class ValidationIssue:
    """A single validation issue."""

    severity: str  # "error", "warning", "info"
    section: str
    message: str
    line: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "severity": self.severity,
            "section": self.section,
            "message": self.message,
            "line": self.line,
        }


@dataclass
class ValidationResult:
    """Result of validating a report."""

    filepath: str
    valid: bool = True
    errors: List[ValidationIssue] = field(default_factory=list)
    warnings: List[ValidationIssue] = field(default_factory=list)
    info: List[ValidationIssue] = field(default_factory=list)

    # Extracted data
    gmp_id: Optional[str] = None
    task: Optional[str] = None
    tier: Optional[str] = None
    date: Optional[str] = None
    status: Optional[str] = None
    todo_count: int = 0
    change_count: int = 0
    phase_count: int = 0
    validation_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "filepath": self.filepath,
            "valid": self.valid,
            "errors": [e.to_dict() for e in self.errors],
            "warnings": [w.to_dict() for w in self.warnings],
            "info": [i.to_dict() for i in self.info],
            "extracted": {
                "gmp_id": self.gmp_id,
                "task": self.task,
                "tier": self.tier,
                "date": self.date,
                "status": self.status,
                "todo_count": self.todo_count,
                "change_count": self.change_count,
                "phase_count": self.phase_count,
                "validation_count": self.validation_count,
            },
            "summary": {
                "error_count": len(self.errors),
                "warning_count": len(self.warnings),
                "info_count": len(self.info),
            },
        }


# ============================================================================
# Contract Loader
# ============================================================================


def load_contract() -> Dict[str, Any]:
    """Load the GMP report contract YAML."""
    if CONTRACT_PATH.exists():
        try:
            with open(CONTRACT_PATH, "r") as f:
                return yaml.safe_load(f)
        except Exception:
            pass
    return {}


# ============================================================================
# Validator
# ============================================================================


class GMPReportValidator:
    """Validates GMP reports against the contract."""

    def __init__(self, strict: bool = False):
        self.strict = strict
        self.contract = load_contract()

    def validate_file(self, filepath: Path) -> ValidationResult:
        """Validate a single report file."""
        result = ValidationResult(filepath=str(filepath))

        if not filepath.exists():
            result.errors.append(
                ValidationIssue(
                    severity="error",
                    section="FILE",
                    message=f"File not found: {filepath}",
                )
            )
            result.valid = False
            return result

        content = filepath.read_text(encoding="utf-8")
        lines = content.split("\n")

        # Validate filename
        self._validate_filename(filepath.name, result)

        # Validate sections
        self._validate_header(lines, result)
        self._validate_todo_plan(lines, result)
        self._validate_phases(lines, result)
        self._validate_changes(lines, result)
        self._validate_todo_change_map(lines, result)
        self._validate_validation_section(lines, result)
        self._validate_verification(lines, result)
        self._validate_declaration(lines, result)

        # Check for forbidden sections
        self._check_forbidden_sections(lines, result)

        # Consistency checks
        self._validate_consistency(result)

        # Determine validity
        result.valid = len(result.errors) == 0
        if self.strict and len(result.warnings) > 0:
            result.valid = False

        return result

    def _validate_filename(self, filename: str, result: ValidationResult):
        """Validate filename format."""
        pattern = r"^GMP-Report-(\d{3})-[\w-]+\.md$"
        match = re.match(pattern, filename)

        if not match:
            result.errors.append(
                ValidationIssue(
                    severity="error",
                    section="FILENAME",
                    message=f"Invalid filename format: {filename}. Expected: GMP-Report-###-Description.md",
                )
            )
        else:
            gmp_num = match.group(1)
            if not gmp_num.isdigit() or len(gmp_num) != 3:
                result.errors.append(
                    ValidationIssue(
                        severity="error",
                        section="FILENAME",
                        message=f"GMP ID not zero-padded to 3 digits: {gmp_num}",
                    )
                )

    def _validate_header(self, lines: List[str], result: ValidationResult):
        """Validate the header section."""
        header_pattern = r"\*\*ID:\*\*\s*GMP-(\d+)\s*\|\s*\*\*Task:\*\*\s*(.+?)\s*\|\s*\*\*Tier:\*\*\s*(\w+_TIER)\s*\|\s*\*\*Date:\*\*\s*(\d{4}-\d{2}-\d{2})\s*\|\s*\*\*Status:\*\*\s*(.+)"

        header_found = False
        for i, line in enumerate(lines):
            match = re.search(header_pattern, line)
            if match:
                header_found = True
                result.gmp_id = f"GMP-{match.group(1)}"
                result.task = match.group(2).strip()
                result.tier = match.group(3)
                result.date = match.group(4)
                result.status = match.group(5).strip()

                # Validate ID format
                if len(match.group(1)) != 3:
                    result.warnings.append(
                        ValidationIssue(
                            severity="warning",
                            section="HEADER",
                            message=f"GMP ID should be 3 digits: {match.group(1)}",
                            line=i + 1,
                        )
                    )

                # Validate tier
                if result.tier not in VALID_TIERS:
                    result.errors.append(
                        ValidationIssue(
                            severity="error",
                            section="HEADER",
                            message=f"Invalid tier: {result.tier}. Must be one of: {VALID_TIERS}",
                            line=i + 1,
                        )
                    )

                # Validate date
                try:
                    datetime.strptime(result.date, "%Y-%m-%d")
                except ValueError:
                    result.errors.append(
                        ValidationIssue(
                            severity="error",
                            section="HEADER",
                            message=f"Invalid date format: {result.date}. Expected: YYYY-MM-DD",
                            line=i + 1,
                        )
                    )

                # Validate status
                if result.status not in VALID_STATUSES:
                    result.warnings.append(
                        ValidationIssue(
                            severity="warning",
                            section="HEADER",
                            message=f"Non-standard status: {result.status}. Expected: {VALID_STATUSES}",
                            line=i + 1,
                        )
                    )

                # Validate task length
                if len(result.task) > 80:
                    result.warnings.append(
                        ValidationIssue(
                            severity="warning",
                            section="HEADER",
                            message=f"Task exceeds 80 chars: {len(result.task)} chars",
                            line=i + 1,
                        )
                    )

                break

        if not header_found:
            result.errors.append(
                ValidationIssue(
                    severity="error",
                    section="HEADER",
                    message="Header not found or malformed",
                )
            )

    def _validate_todo_plan(self, lines: List[str], result: ValidationResult):
        """Validate TODO PLAN section."""
        in_section = False
        in_table = False
        todos = []
        hash_found = False

        for i, line in enumerate(lines):
            if re.match(r"^##\s*TODO\s*PLAN", line, re.IGNORECASE):
                in_section = True
                continue

            if in_section and line.startswith("## "):
                break

            if in_section:
                # Check for table header
                if "| ID |" in line or "| T# |" in line:
                    in_table = True
                    continue

                # Check for separator
                if re.match(r"^\|[-|]+\|$", line):
                    continue

                # Parse table row
                if in_table and line.startswith("|") and "---" not in line:
                    parts = [p.strip() for p in line.split("|")[1:-1]]
                    if len(parts) >= 4:
                        todos.append(
                            {
                                "id": parts[0],
                                "file": parts[1].strip("`"),
                                "lines": parts[2] if len(parts) > 2 else "",
                                "action": parts[3] if len(parts) > 3 else "",
                                "status": parts[4] if len(parts) > 4 else "✅",
                            }
                        )

                # Check for hash
                if "**Hash:**" in line:
                    hash_found = True
                    hash_match = re.search(r"`(\d+)\s+TODOs", line)
                    if hash_match:
                        claimed_count = int(hash_match.group(1))
                        if claimed_count != len(todos):
                            result.errors.append(
                                ValidationIssue(
                                    severity="error",
                                    section="TODO_PLAN",
                                    message=f"Hash claims {claimed_count} TODOs but found {len(todos)}",
                                    line=i + 1,
                                )
                            )

        result.todo_count = len(todos)

        if not in_section:
            result.errors.append(
                ValidationIssue(
                    severity="error",
                    section="TODO_PLAN",
                    message="TODO PLAN section not found",
                )
            )
        elif len(todos) == 0:
            result.warnings.append(
                ValidationIssue(
                    severity="warning",
                    section="TODO_PLAN",
                    message="No TODO items found in table",
                )
            )

        if not hash_found:
            result.warnings.append(
                ValidationIssue(
                    severity="warning",
                    section="TODO_PLAN",
                    message="Hash line not found",
                )
            )

        # Validate each TODO
        for todo in todos:
            if todo["action"].upper() not in VALID_ACTIONS:
                result.warnings.append(
                    ValidationIssue(
                        severity="warning",
                        section="TODO_PLAN",
                        message=f"Invalid action '{todo['action']}' for {todo['id']}",
                    )
                )

    def _validate_phases(self, lines: List[str], result: ValidationResult):
        """Validate PHASES section."""
        in_section = False
        phases = []

        for i, line in enumerate(lines):
            if re.match(r"^##\s*PHASES", line, re.IGNORECASE):
                in_section = True
                continue

            if in_section and line.startswith("## "):
                break

            if (
                in_section
                and line.startswith("|")
                and "---" not in line
                and "Phase" not in line
                and "#" not in line.split("|")[1]
            ):
                parts = [p.strip() for p in line.split("|")[1:-1]]
                if len(parts) >= 3:
                    try:
                        phase_num = int(parts[0])
                        phases.append(
                            {"phase": phase_num, "name": parts[1], "status": parts[2]}
                        )
                    except ValueError:
                        pass

        result.phase_count = len(phases)

        if not in_section:
            result.errors.append(
                ValidationIssue(
                    severity="error",
                    section="PHASES",
                    message="PHASES section not found",
                )
            )
        elif len(phases) != 7:
            result.warnings.append(
                ValidationIssue(
                    severity="warning",
                    section="PHASES",
                    message=f"Expected 7 phases (0-6), found {len(phases)}",
                )
            )

        # Check each required phase
        for expected_num, expected_name in REQUIRED_PHASES:
            found = False
            for p in phases:
                if p["phase"] == expected_num:
                    found = True
                    if p["name"].upper() != expected_name.upper():
                        result.warnings.append(
                            ValidationIssue(
                                severity="warning",
                                section="PHASES",
                                message=f"Phase {expected_num} should be '{expected_name}', got '{p['name']}'",
                            )
                        )
                    if p["status"] not in VALID_PHASE_STATUSES:
                        result.warnings.append(
                            ValidationIssue(
                                severity="warning",
                                section="PHASES",
                                message=f"Invalid status '{p['status']}' for phase {expected_num}",
                            )
                        )
                    break
            if not found:
                result.errors.append(
                    ValidationIssue(
                        severity="error",
                        section="PHASES",
                        message=f"Missing phase {expected_num} ({expected_name})",
                    )
                )

    def _validate_changes(self, lines: List[str], result: ValidationResult):
        """Validate CHANGES section."""
        in_section = False
        changes = []

        for line in lines:
            if re.match(r"^##\s*CHANGES", line, re.IGNORECASE):
                in_section = True
                continue

            if in_section and line.startswith("## "):
                break

            if (
                in_section
                and line.startswith("|")
                and "---" not in line
                and "File" not in line
            ):
                parts = [p.strip() for p in line.split("|")[1:-1]]
                if len(parts) >= 4:
                    changes.append(
                        {
                            "file": parts[0].strip("`"),
                            "lines": parts[1],
                            "action": parts[2],
                            "description": parts[3],
                        }
                    )

        result.change_count = len(changes)

        if not in_section:
            result.errors.append(
                ValidationIssue(
                    severity="error",
                    section="CHANGES",
                    message="CHANGES section not found",
                )
            )
        elif len(changes) == 0:
            result.warnings.append(
                ValidationIssue(
                    severity="warning",
                    section="CHANGES",
                    message="No changes found in table",
                )
            )

    def _validate_todo_change_map(self, lines: List[str], result: ValidationResult):
        """Validate TODO → CHANGE MAP section."""
        in_section = False
        map_entries = 0

        for line in lines:
            if (
                "TODO" in line
                and "CHANGE" in line
                and "MAP" in line
                and line.startswith("##")
            ):
                in_section = True
                continue

            if in_section and line.startswith("## "):
                break

            if (
                in_section
                and line.startswith("|")
                and "---" not in line
                and "TODO" not in line
            ):
                map_entries += 1

        if not in_section:
            result.errors.append(
                ValidationIssue(
                    severity="error",
                    section="TODO_CHANGE_MAP",
                    message="TODO → CHANGE MAP section not found",
                )
            )
        elif map_entries == 0:
            result.warnings.append(
                ValidationIssue(
                    severity="warning",
                    section="TODO_CHANGE_MAP",
                    message="No mappings found in table",
                )
            )

    def _validate_validation_section(self, lines: List[str], result: ValidationResult):
        """Validate VALIDATION section."""
        in_section = False
        validations = []

        for line in lines:
            if re.match(r"^##\s*VALIDATION\s*$", line, re.IGNORECASE):
                in_section = True
                continue

            if in_section and line.startswith("## "):
                break

            if (
                in_section
                and line.startswith("|")
                and "---" not in line
                and "Gate" not in line
            ):
                parts = [p.strip() for p in line.split("|")[1:-1]]
                if len(parts) >= 2:
                    validations.append({"gate": parts[0], "result": parts[1]})

        result.validation_count = len(validations)

        if not in_section:
            result.errors.append(
                ValidationIssue(
                    severity="error",
                    section="VALIDATION",
                    message="VALIDATION section not found",
                )
            )
        else:
            # Check minimum gates
            gate_names = [v["gate"].lower() for v in validations]
            for required_gate in MINIMUM_VALIDATION_GATES:
                if required_gate.lower() not in gate_names:
                    result.warnings.append(
                        ValidationIssue(
                            severity="warning",
                            section="VALIDATION",
                            message=f"Missing required validation gate: {required_gate}",
                        )
                    )

    def _validate_verification(self, lines: List[str], result: ValidationResult):
        """Validate VERIFICATION section."""
        in_section = False
        items_found = []

        for line in lines:
            if re.match(r"^##\s*VERIFICATION", line, re.IGNORECASE):
                in_section = True
                continue

            if in_section and line.startswith("## "):
                break

            if in_section and line.strip().startswith("- ["):
                # Extract item text
                match = re.search(r"\- \[[x ]\]\s*(.+)", line, re.IGNORECASE)
                if match:
                    items_found.append(match.group(1).strip())

        if not in_section:
            result.errors.append(
                ValidationIssue(
                    severity="error",
                    section="VERIFICATION",
                    message="VERIFICATION section not found",
                )
            )
        else:
            for required_item in REQUIRED_VERIFICATION_ITEMS:
                found = any(
                    required_item.lower() in item.lower() for item in items_found
                )
                if not found:
                    result.warnings.append(
                        ValidationIssue(
                            severity="warning",
                            section="VERIFICATION",
                            message=f"Missing checklist item: {required_item}",
                        )
                    )

    def _validate_declaration(self, lines: List[str], result: ValidationResult):
        """Validate DECLARATION section."""
        in_section = False
        declaration_text = ""

        for line in lines:
            if re.match(r"^##\s*DECLARATION", line, re.IGNORECASE):
                in_section = True
                continue

            if in_section and line.startswith("## "):
                break

            if in_section:
                declaration_text += line + " "

        if not in_section:
            result.errors.append(
                ValidationIssue(
                    severity="error",
                    section="DECLARATION",
                    message="DECLARATION section not found",
                )
            )
        else:
            for required_text in DECLARATION_MUST_CONTAIN:
                if required_text.lower() not in declaration_text.lower():
                    result.errors.append(
                        ValidationIssue(
                            severity="error",
                            section="DECLARATION",
                            message=f"Declaration missing required text: '{required_text}'",
                        )
                    )

    def _check_forbidden_sections(self, lines: List[str], result: ValidationResult):
        """Check for forbidden sections."""
        forbidden = ["YNP RECOMMENDATION", "NEXT STEPS"]

        for i, line in enumerate(lines):
            for f in forbidden:
                if f.lower() in line.lower() and line.startswith("##"):
                    result.warnings.append(
                        ValidationIssue(
                            severity="warning",
                            section="FORBIDDEN",
                            message=f"Found forbidden section: {f}",
                            line=i + 1,
                        )
                    )

    def _validate_consistency(self, result: ValidationResult):
        """Run consistency checks across sections."""
        # Check TODO count matches change count
        if result.todo_count > 0 and result.change_count > 0:
            if result.todo_count != result.change_count:
                result.info.append(
                    ValidationIssue(
                        severity="info",
                        section="CONSISTENCY",
                        message=f"TODO count ({result.todo_count}) differs from change count ({result.change_count})",
                    )
                )

        # Check status matches phases
        if result.status:
            if "COMPLETE" in result.status and result.phase_count < 7:
                result.warnings.append(
                    ValidationIssue(
                        severity="warning",
                        section="CONSISTENCY",
                        message=f"Status is COMPLETE but only {result.phase_count} phases found",
                    )
                )


# ============================================================================
# CLI Interface
# ============================================================================


def print_result(result: ValidationResult, verbose: bool = False):
    """Print validation result to console."""
    status_icon = "✅" if result.valid else "❌"
    print(f"\n{status_icon} {result.filepath}")

    if result.gmp_id:
        print(
            f"   ID: {result.gmp_id} | Task: {result.task[:50]}{'...' if len(result.task or '') > 50 else ''}"
        )
        print(f"   Tier: {result.tier} | Date: {result.date} | Status: {result.status}")

    print(
        f"   TODOs: {result.todo_count} | Changes: {result.change_count} | Phases: {result.phase_count} | Validations: {result.validation_count}"
    )

    if result.errors:
        print(f"\n   🔴 ERRORS ({len(result.errors)}):")
        for e in result.errors:
            line_info = f" (L{e.line})" if e.line else ""
            print(f"      [{e.section}]{line_info}: {e.message}")

    if result.warnings:
        print(f"\n   🟡 WARNINGS ({len(result.warnings)}):")
        for w in result.warnings:
            line_info = f" (L{w.line})" if w.line else ""
            print(f"      [{w.section}]{line_info}: {w.message}")

    if verbose and result.info:
        print(f"\n   ℹ️ INFO ({len(result.info)}):")
        for i in result.info:
            print(f"      [{i.section}]: {i.message}")

    print()


def main():
    parser = argparse.ArgumentParser(
        description="Validate GMP reports against gmp-report-contract.yaml"
    )
    parser.add_argument("files", nargs="*", help="Report files to validate")
    parser.add_argument(
        "--all", action="store_true", help="Validate all reports in reports/"
    )
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    parser.add_argument(
        "--strict", action="store_true", help="Treat warnings as errors"
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Include info messages"
    )
    parser.add_argument("--quiet", "-q", action="store_true", help="Only show summary")

    args = parser.parse_args()

    # Determine files to validate
    files = []
    if args.all:
        files = list(REPORTS_DIR.glob("GMP-Report-*.md"))
    elif args.files:
        files = [Path(f) for f in args.files]
    else:
        parser.print_help()
        sys.exit(1)

    if not files:
        print("No files to validate")
        sys.exit(1)

    # Validate
    validator = GMPReportValidator(strict=args.strict)
    results = []

    for filepath in files:
        result = validator.validate_file(filepath)
        results.append(result)

    # Output
    if args.json:
        output = {
            "timestamp": datetime.now().isoformat(),
            "files_validated": len(results),
            "valid_count": sum(1 for r in results if r.valid),
            "invalid_count": sum(1 for r in results if not r.valid),
            "results": [r.to_dict() for r in results],
        }
        print(json.dumps(output, indent=2))
    else:
        if not args.quiet:
            for result in results:
                print_result(result, verbose=args.verbose)

        # Summary
        valid_count = sum(1 for r in results if r.valid)
        invalid_count = len(results) - valid_count
        total_errors = sum(len(r.errors) for r in results)
        total_warnings = sum(len(r.warnings) for r in results)

        print("=" * 60)
        print(f"SUMMARY: {valid_count}/{len(results)} valid")
        print(f"         {total_errors} errors, {total_warnings} warnings")

        if invalid_count > 0:
            print("\n❌ INVALID REPORTS:")
            for r in results:
                if not r.valid:
                    print(f"   - {r.filepath}")

    # Exit code
    sys.exit(0 if all(r.valid for r in results) else 1)


if __name__ == "__main__":
    main()
