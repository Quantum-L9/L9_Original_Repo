"""
ADR Indexer - Builds and maintains the ADR index

Creates index.json with metadata for all ADRs for searchability and tooling.
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path


def extract_adr_metadata(adr_file: Path) -> dict | None:
    """
    Extract metadata from an ADR file.

    Args:
        adr_file: Path to the ADR file

    Returns:
        Dictionary of ADR metadata, or None if extraction fails
    """
    if not adr_file.exists():
        return None

    with open(adr_file) as f:
        content = f.read()

    # Extract ADR number from filename
    filename_match = re.match(r"(\d{4})-", adr_file.name)
    if not filename_match:
        return None

    adr_id = filename_match.group(1)

    # Extract title
    title_match = re.search(r"# ADR-\d{4}:\s+(.+)", content)
    title = title_match.group(1).strip() if title_match else "Unknown"

    # Extract status
    status_match = re.search(r"\*\*Status:\*\*\s+(\w+)", content)
    status = status_match.group(1).lower() if status_match else "unknown"

    # Extract date
    date_match = re.search(r"\*\*Date:\*\*\s+([\d-]+)", content)
    date = date_match.group(1) if date_match else "unknown"

    # Extract author
    author_match = re.search(r"\*\*Author:\*\*\s+@?([\w-]+)", content)
    author = author_match.group(1) if author_match else "unknown"

    # Extract category
    category_match = re.search(r"\*\*Category:\*\*\s+(\w+)", content)
    category = category_match.group(1).lower() if category_match else "unknown"

    # Extract impact
    impact_match = re.search(r"\*\*Impact:\*\*\s+(\w+)", content)
    impact = impact_match.group(1).lower() if impact_match else "unknown"

    # Extract tier
    tier_match = re.search(r"\*\*Tier:\*\*\s+(T\d)", content)
    tier = tier_match.group(1).lower() if tier_match else "unknown"

    # Extract related PRs
    related_prs = []
    pr_matches = re.findall(r"#(\d+)", content)
    if pr_matches:
        related_prs = [int(pr) for pr in pr_matches]

    # Extract related ADRs
    related_adrs = []
    adr_matches = re.findall(r"ADR-(\d{4})", content)
    if adr_matches:
        # Exclude self-reference
        related_adrs = [adr for adr in adr_matches if adr != adr_id]

    # Extract tags (from title and content keywords)
    tags = []

    # Add category as tag
    if category != "unknown":
        tags.append(category)

    # Extract keywords from title
    title_words = re.findall(r"\b[a-z]{4,}\b", title.lower())
    tags.extend(title_words[:3])  # Add first 3 keywords from title

    # Remove duplicates
    tags = list(dict.fromkeys(tags))

    return {
        "id": adr_id,
        "title": title,
        "status": status,
        "date": date,
        "author": author,
        "category": category,
        "impact": impact,
        "tier": tier,
        "file": f"docs/adr/{adr_file.name}",
        "tags": tags,
        "related_adrs": related_adrs,
        "related_prs": related_prs,
    }


def build_index(adr_dir: Path) -> dict:
    """
    Build the ADR index from all ADR files.

    Args:
        adr_dir: Path to the ADR directory

    Returns:
        Dictionary containing the ADR index
    """
    adrs = []

    # Find all ADR files (exclude template.md and README.md)
    adr_files = [
        f
        for f in adr_dir.glob("*.md")
        if f.name not in ["template.md", "README.md"] and re.match(r"\d{4}-", f.name)
    ]

    for adr_file in sorted(adr_files):
        metadata = extract_adr_metadata(adr_file)
        if metadata:
            adrs.append(metadata)

    return {
        "version": "1.0.0",
        "last_updated": datetime.now(timezone.utc).isoformat() + "Z",
        "adrs": adrs,
    }


def get_next_adr_number(adr_dir: Path) -> str:
    """
    Get the next available ADR number.

    Args:
        adr_dir: Path to the ADR directory

    Returns:
        Next ADR number as a 4-digit string (e.g., "0042")
    """
    # Find all ADR files
    adr_files = [
        f
        for f in adr_dir.glob("*.md")
        if f.name not in ["template.md", "README.md"] and re.match(r"\d{4}-", f.name)
    ]

    if not adr_files:
        return "0001"

    # Extract numbers
    numbers = []
    for adr_file in adr_files:
        match = re.match(r"(\d{4})-", adr_file.name)
        if match:
            numbers.append(int(match.group(1)))

    # Return next number
    next_number = max(numbers) + 1
    return f"{next_number:04d}"


def update_index_entry(index_path: Path, adr_id: str, updates: dict) -> bool:
    """
    Update a single ADR entry in the index.

    Args:
        index_path: Path to the index.json file
        adr_id: ADR ID to update (e.g., "0042")
        updates: Dictionary of fields to update

    Returns:
        True if update succeeded, False otherwise
    """
    if not index_path.exists():
        return False

    with open(index_path) as f:
        index = json.load(f)

    # Find ADR entry
    for adr in index.get("adrs", []):
        if adr["id"] == adr_id:
            # Update fields
            adr.update(updates)

            # Update last_updated timestamp
            index["last_updated"] = datetime.now(timezone.utc).isoformat() + "Z"

            # Write updated index
            with open(index_path, "w") as f:
                json.dump(index, f, indent=2)

            return True

    return False
