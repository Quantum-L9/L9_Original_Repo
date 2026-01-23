"""
ADR Validator - Validates ADR structure and content

Validates that ADRs follow the standard template and include all required sections.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import List, Dict

REQUIRED_SECTIONS = [
    "# ADR-",
    "## Status",
    "## Context",
    "## Decision",
    "## Rationale",
    "## Alternatives Considered",
    "## Consequences",
    "## Implementation",
    "## Metadata",
]

REQUIRED_STATUS_FIELDS = [
    "**Status:**",
    "**Date:**",
    "**Author:**",
]

REQUIRED_METADATA_FIELDS = [
    "**Category:**",
    "**Impact:**",
    "**Tier:**",
]

VALID_STATUSES = ["Proposed", "Accepted", "Deprecated", "Superseded"]
VALID_CATEGORIES = ["Architecture", "Infrastructure", "Process", "Tooling"]
VALID_IMPACTS = ["High", "Medium", "Low"]
VALID_TIERS = ["T1", "T2", "T3"]


def validate_adr(adr_file: Path) -> List[str]:
    """
    Validate an ADR file.

    Args:
        adr_file: Path to the ADR file

    Returns:
        List of validation issues (empty if valid)
    """
    issues = []

    if not adr_file.exists():
        return [f"File not found: {adr_file}"]

    with open(adr_file, "r") as f:
        content = f.read()

    # Check required sections
    for section in REQUIRED_SECTIONS:
        if section not in content:
            issues.append(f"Missing required section: {section}")

    # Check required status fields
    for field in REQUIRED_STATUS_FIELDS:
        if field not in content:
            issues.append(f"Missing required status field: {field}")

    # Check required metadata fields
    for field in REQUIRED_METADATA_FIELDS:
        if field not in content:
            issues.append(f"Missing required metadata field: {field}")

    # Validate status value
    status_match = re.search(r"\*\*Status:\*\*\s+(\w+)", content)
    if status_match:
        status = status_match.group(1)
        if status not in VALID_STATUSES:
            issues.append(
                f"Invalid status: {status}. Must be one of: {', '.join(VALID_STATUSES)}"
            )

    # Validate category value
    category_match = re.search(r"\*\*Category:\*\*\s+(\w+)", content)
    if category_match:
        category = category_match.group(1)
        if category not in VALID_CATEGORIES:
            issues.append(
                f"Invalid category: {category}. Must be one of: {', '.join(VALID_CATEGORIES)}"
            )

    # Validate impact value
    impact_match = re.search(r"\*\*Impact:\*\*\s+(\w+)", content)
    if impact_match:
        impact = impact_match.group(1)
        if impact not in VALID_IMPACTS:
            issues.append(
                f"Invalid impact: {impact}. Must be one of: {', '.join(VALID_IMPACTS)}"
            )

    # Validate tier value
    tier_match = re.search(r"\*\*Tier:\*\*\s+(T\d)", content)
    if tier_match:
        tier = tier_match.group(1)
        if tier not in VALID_TIERS:
            issues.append(
                f"Invalid tier: {tier}. Must be one of: {', '.join(VALID_TIERS)}"
            )

    # Check ADR number in title matches filename
    title_match = re.search(r"# ADR-(\d{4}):", content)
    filename_match = re.match(r"(\d{4})-", adr_file.name)

    if title_match and filename_match:
        title_number = title_match.group(1)
        filename_number = filename_match.group(1)
        if title_number != filename_number:
            issues.append(
                f"ADR number mismatch: title has {title_number}, filename has {filename_number}"
            )

    # Check for placeholder text that should be replaced
    placeholders = [
        "[Title]",
        "[Proposed | Accepted | Deprecated | Superseded]",
        "YYYY-MM-DD",
        "@username",
        "[What is the issue",
        "[What is the change",
        "[Why are we making",
    ]

    for placeholder in placeholders:
        if placeholder in content:
            issues.append(f"Template placeholder not replaced: {placeholder}")

    return issues


def validate_all_adrs(adr_dir: Path) -> Dict[Path, List[str]]:
    """
    Validate all ADRs in a directory.

    Args:
        adr_dir: Path to the ADR directory

    Returns:
        Dictionary mapping ADR files to their validation issues
    """
    results = {}

    # Find all ADR files (exclude template.md and README.md)
    adr_files = [
        f
        for f in adr_dir.glob("*.md")
        if f.name not in ["template.md", "README.md"] and re.match(r"\d{4}-", f.name)
    ]

    for adr_file in sorted(adr_files):
        issues = validate_adr(adr_file)
        results[adr_file] = issues

    return results


def check_t3_approval(adr_file: Path) -> bool:
    """
    Check if a T3 ADR has required approval.

    Args:
        adr_file: Path to the ADR file

    Returns:
        True if T3 ADR has approval, False otherwise
    """
    with open(adr_file, "r") as f:
        content = f.read()

    # Check if this is a T3 ADR
    tier_match = re.search(r"\*\*Tier:\*\*\s+(T3)", content)
    if not tier_match:
        return True  # Not a T3 ADR, no approval needed

    # Check for approval markers (e.g., "Approved by: @l-cto, @kernel-team")
    approval_patterns = [
        r"Approved by:.*@l-cto",
        r"Approved by:.*@kernel-team",
        r"\*\*Status:\*\*\s+Accepted",  # Accepted status implies approval
    ]

    for pattern in approval_patterns:
        if re.search(pattern, content):
            return True

    return False
