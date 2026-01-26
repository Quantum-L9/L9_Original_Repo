"""
ADR Generator - Generates new ADR files from template

Creates new ADR files with pre-filled metadata and standard structure.
"""

from __future__ import annotations

import re
from datetime import date
from pathlib import Path


def slugify(text: str) -> str:
    """
    Convert text to a URL-friendly slug.

    Args:
        text: Text to slugify

    Returns:
        Slugified text
    """
    # Convert to lowercase
    text = text.lower()

    # Replace spaces and special chars with hyphens
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_]+", "-", text)
    text = re.sub(r"-+", "-", text)

    # Remove leading/trailing hyphens
    return text.strip("-")



def generate_adr(
    adr_dir: Path,
    number: str,
    title: str,
    author: str = "unknown",
    category: str = "architecture",
    tier: str = "t2",
) -> Path:
    """
    Generate a new ADR file from template.

    Args:
        adr_dir: Path to the ADR directory
        number: ADR number (e.g., "0042")
        title: ADR title
        author: ADR author
        category: ADR category (architecture, infrastructure, process, tooling)
        tier: ADR tier (t1, t2, t3)

    Returns:
        Path to the generated ADR file
    """
    # Create filename
    slug = slugify(title)
    filename = f"{number}-{slug}.md"
    adr_file = adr_dir / filename

    # Get today's date
    today = date.today().isoformat()

    # Read template
    template_file = adr_dir / "template.md"
    if not template_file.exists():
        raise FileNotFoundError(f"Template not found: {template_file}")

    with open(template_file) as f:
        content = f.read()

    # Replace placeholders
    content = content.replace("ADR-XXXX", f"ADR-{number}")
    content = content.replace("[Title]", title)
    content = content.replace("YYYY-MM-DD", today)
    content = content.replace("@username", f"@{author}")
    content = content.replace(
        "[Proposed | Accepted | Deprecated | Superseded]", "Proposed"
    )
    content = content.replace(
        "[Architecture | Infrastructure | Process | Tooling]", category.capitalize()
    )
    content = content.replace("[T1 | T2 | T3]", tier.upper())

    # Write ADR file
    with open(adr_file, "w") as f:
        f.write(content)

    return adr_file


def generate_adr_from_pr(
    adr_dir: Path,
    number: str,
    pr_number: int,
    pr_title: str,
    pr_description: str,
    author: str = "unknown",
) -> Path:
    """
    Generate an ADR from a PR.

    This is useful for retroactively documenting decisions made in PRs.

    Args:
        adr_dir: Path to the ADR directory
        number: ADR number (e.g., "0042")
        pr_number: PR number
        pr_title: PR title
        pr_description: PR description
        author: ADR author

    Returns:
        Path to the generated ADR file
    """
    # Extract title from PR title (remove PR number prefix if present)
    title = re.sub(r"^#\d+\s*-?\s*", "", pr_title)

    # Generate base ADR
    adr_file = generate_adr(
        adr_dir=adr_dir,
        number=number,
        title=title,
        author=author,
    )

    # Read generated ADR
    with open(adr_file) as f:
        content = f.read()

    # Add PR context
    context_section = f"""## Context

This decision was made and implemented in PR #{pr_number}.

{pr_description}

[What is the issue that we're seeing that is motivating this decision or change?]
"""

    content = content.replace(
        "[What is the issue that we're seeing that is motivating this decision or change?]",
        context_section,
    )

    # Add PR reference to metadata
    content = content.replace(
        "**Related PRs:** #XX, #YY", f"**Related PRs:** #{pr_number}"
    )

    # Write updated ADR
    with open(adr_file, "w") as f:
        f.write(content)

    return adr_file
