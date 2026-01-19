#!/usr/bin/env python3
"""
GMP Report Validator v3.2.0
Validates GMP reports against gmp-report-contract.yaml

Usage:
    python3 scripts/validate_gmp_report.py reports/GMP-Report-074-Retention-Engine.md
    python3 scripts/validate_gmp_report.py --all  # Validate all reports
"""

import re
import sys
from pathlib import Path
from dataclasses import dataclass


@dataclass
class ValidationResult:
    valid: bool
    errors: list[str]
    warnings: list[str]
    file: str


# Contract constants (from gmp-report-contract.yaml)
NAMING_PATTERN = r"GMP-Report-(\d{3})-([A-Za-z0-9-]+)\.md"
REQUIRED_SECTIONS = [
    "TODO PLAN",
    "PHASES",
    "CHANGES",
    "TODO → CHANGE MAP",
    "VALIDATION",
    "VERIFICATION",
    "DECLARATION",
]
FORBIDDEN_SECTIONS = ["YNP RECOMMENDATION", "NEXT STEPS"]
VALID_TIERS = ["KERNEL_TIER", "RUNTIME_TIER", "INFRA_TIER", "UX_TIER"]
VALID_STATUSES = ["✅ COMPLETE", "⚠️ PARTIAL", "❌ FAILED"]
VALID_ACTIONS = ["CREATE", "INSERT", "REPLACE", "DELETE", "WRAP"]


def validate_naming(filepath: Path) -> list[str]:
    """Validate file naming convention."""
    errors = []
    filename = filepath.name

    if not re.match(NAMING_PATTERN, filename):
        errors.append(
            f"NAMING: '{filename}' doesn't match pattern 'GMP-Report-###-Description.md'"
        )

    return errors


def validate_header(content: str) -> tuple[list[str], list[str]]:
    """Validate header fields."""
    errors = []
    warnings = []

    # Check ID with 3-digit format
    id_match = re.search(r"\*\*ID:\*\*\s*GMP-(\d+)", content)
    if id_match:
        gmp_id = id_match.group(1)
        if len(gmp_id) < 3:
            warnings.append(
                f"HEADER: ID 'GMP-{gmp_id}' should be zero-padded to 3 digits (GMP-{gmp_id.zfill(3)})"
            )
    else:
        errors.append("HEADER: Missing or invalid ID field (expected 'GMP-###')")

    # Check Task
    if not re.search(r"\*\*Task:\*\*\s*.+", content):
        errors.append("HEADER: Missing Task field")

    # Check Tier
    tier_match = re.search(r"\*\*Tier:\*\*\s*(\w+)", content)
    if tier_match:
        tier = tier_match.group(1)
        if tier not in VALID_TIERS:
            errors.append(f"HEADER: Invalid Tier '{tier}' (valid: {VALID_TIERS})")
    else:
        warnings.append("HEADER: Missing Tier field")

    # Check Date - must be ISO format YYYY-MM-DD
    date_match = re.search(r"\*\*Date:\*\*\s*(\d{4}-\d{2}-\d{2})", content)
    if date_match:
        date_str = date_match.group(1)
        # Validate it's a real date
        try:
            year, month, day = map(int, date_str.split("-"))
            if not (2024 <= year <= 2030 and 1 <= month <= 12 and 1 <= day <= 31):
                errors.append(
                    f"HEADER: Invalid date '{date_str}' (must be valid YYYY-MM-DD)"
                )
        except ValueError:
            errors.append(f"HEADER: Invalid date format '{date_str}'")
    else:
        errors.append(
            "HEADER: Missing or invalid Date (expected YYYY-MM-DD ISO format)"
        )

    # Check Status
    status_match = re.search(r"\*\*Status:\*\*\s*(.+?)(?:\n|$|\|)", content)
    if status_match:
        status = status_match.group(1).strip()
        if not any(s in status for s in ["✅", "⚠️", "❌"]):
            errors.append(f"HEADER: Invalid Status '{status}'")
    else:
        errors.append("HEADER: Missing Status field")

    return errors, warnings


def validate_sections(content: str) -> tuple[list[str], list[str]]:
    """Validate required and forbidden sections."""
    errors = []
    warnings = []

    # Check required sections
    for section in REQUIRED_SECTIONS:
        if f"## {section}" not in content and f"# {section}" not in content:
            errors.append(f"SECTION: Missing required section '## {section}'")

    # Check forbidden sections
    for section in FORBIDDEN_SECTIONS:
        if section.upper() in content.upper():
            errors.append(f"SECTION: Forbidden section '{section}' found - remove it")

    return errors, warnings


def validate_todo_plan(content: str) -> tuple[list[str], list[str]]:
    """Validate TODO PLAN section."""
    errors = []
    warnings = []

    # Check for TODO table
    if "| ID |" not in content and "| TODO |" not in content:
        warnings.append("TODO_PLAN: No TODO table found")

    # Check for T# format TODOs
    todos = re.findall(r"\| (T\d+) \|", content)
    if not todos:
        warnings.append("TODO_PLAN: No TODOs with T# format found")

    # Check for hash
    if (
        "Hash:" not in content and "TODO" not in content.split("Hash:")[0]
        if "Hash:" in content
        else True
    ):
        warnings.append("TODO_PLAN: Missing Hash summary")

    return errors, warnings


def validate_phases(content: str) -> tuple[list[str], list[str]]:
    """Validate PHASES section."""
    errors = []
    warnings = []

    required_phases = ["0", "1", "2", "3", "4", "5", "6"]

    for phase in required_phases:
        if not re.search(rf"\|\s*{phase}\s*\|", content):
            warnings.append(f"PHASES: Phase {phase} not found in table")

    return errors, warnings


def validate_declaration(content: str) -> tuple[list[str], list[str]]:
    """Validate DECLARATION section."""
    errors = []
    warnings = []

    declaration_section = (
        content.split("## DECLARATION")[-1] if "## DECLARATION" in content else content
    )

    required_phrases = ["0-6", "No assumptions", "No drift"]
    found = 0
    for phrase in required_phrases:
        if phrase.lower() in declaration_section.lower():
            found += 1

    if found < 2:
        warnings.append("DECLARATION: Missing standard declaration phrases")

    return errors, warnings


def validate_density(content: str) -> list[str]:
    """Check for verbose content."""
    warnings = []

    # Check for overly long sections
    sections = content.split("## ")
    for section in sections:
        if len(section.split()) > 500:
            section_name = section.split("\n")[0][:50]
            warnings.append(f"DENSITY: Section '{section_name}...' exceeds 500 words")

    return warnings


def validate_report(filepath: Path) -> ValidationResult:
    """Validate a single GMP report."""
    errors = []
    warnings = []

    # Check file exists
    if not filepath.exists():
        return ValidationResult(
            False, [f"File not found: {filepath}"], [], str(filepath)
        )

    content = filepath.read_text()

    # Run all validations
    errors.extend(validate_naming(filepath))

    h_errors, h_warnings = validate_header(content)
    errors.extend(h_errors)
    warnings.extend(h_warnings)

    s_errors, s_warnings = validate_sections(content)
    errors.extend(s_errors)
    warnings.extend(s_warnings)

    t_errors, t_warnings = validate_todo_plan(content)
    errors.extend(t_errors)
    warnings.extend(t_warnings)

    p_errors, p_warnings = validate_phases(content)
    errors.extend(p_errors)
    warnings.extend(p_warnings)

    d_errors, d_warnings = validate_declaration(content)
    errors.extend(d_errors)
    warnings.extend(d_warnings)

    warnings.extend(validate_density(content))

    return ValidationResult(
        valid=len(errors) == 0, errors=errors, warnings=warnings, file=str(filepath)
    )


def find_reports(base_path: Path) -> list[Path]:
    """Find all GMP reports in reports/ and reports/GMP Reports/."""
    reports = []

    # Active reports
    for f in base_path.glob("GMP-Report-*.md"):
        reports.append(f)
    for f in base_path.glob("GMP_Report_*.md"):  # Old format
        reports.append(f)

    # Archived reports
    archive_path = base_path / "GMP Reports"
    if archive_path.exists():
        for f in archive_path.glob("GMP-Report-*.md"):
            reports.append(f)
        for f in archive_path.glob("GMP_Report_*.md"):  # Old format
            reports.append(f)

    return sorted(reports)


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 validate_gmp_report.py <report.md|--all>")
        sys.exit(1)

    workspace = Path(__file__).parent.parent

    if sys.argv[1] == "--all":
        reports = find_reports(workspace / "reports")
        if not reports:
            print("No GMP reports found")
            sys.exit(0)
    else:
        reports = [Path(sys.argv[1])]

    total_valid = 0
    total_errors = 0

    for report_path in reports:
        result = validate_report(report_path)

        status = "✅ VALID" if result.valid else "❌ INVALID"
        print(f"\n{status}: {result.file}")

        if result.errors:
            for error in result.errors:
                print(f"  ❌ {error}")
            total_errors += len(result.errors)

        if result.warnings:
            for warning in result.warnings:
                print(f"  ⚠️  {warning}")

        if result.valid:
            total_valid += 1

    print(f"\n{'=' * 60}")
    print(f"SUMMARY: {total_valid}/{len(reports)} valid, {total_errors} errors")

    sys.exit(0 if total_errors == 0 else 1)


if __name__ == "__main__":
    main()
