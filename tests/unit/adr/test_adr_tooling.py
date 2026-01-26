"""
Tests for ADR tooling (validator, indexer, generator)
"""

from __future__ import annotations

import tempfile
from datetime import date
from pathlib import Path

import pytest

from tools.adr.adr_generator import generate_adr, slugify
from tools.adr.adr_indexer import build_index, extract_adr_metadata, get_next_adr_number
from tools.adr.adr_validator import validate_adr, validate_all_adrs

# Fixtures


@pytest.fixture
def temp_adr_dir():
    """Create a temporary ADR directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        adr_dir = Path(tmpdir) / "adr"
        adr_dir.mkdir()
        yield adr_dir


@pytest.fixture
def sample_adr_content():
    """Sample ADR content for testing."""
    return """# ADR-0042: Use Protocol Buffers for IPC

## Status

**Status:** Accepted
**Date:** 2026-01-20
**Author:** @test-user
**Stakeholders:** @team1, @team2
**Supersedes:** None
**Superseded by:** None

## Context

We need a serialization format for inter-process communication.

## Decision

Use Protocol Buffers for IPC.

## Rationale

Protocol Buffers are fast, compact, and have good language support.

## Alternatives Considered

### Alternative 1: JSON
- **Pros:** Human-readable
- **Cons:** Slower, larger
- **Why rejected:** Performance requirements

### Alternative 2: MessagePack
- **Pros:** Fast, compact
- **Cons:** Less tooling support
- **Why rejected:** Tooling ecosystem

## Consequences

### Positive
- Fast serialization
- Compact messages

### Negative
- Learning curve
- Schema management

### Neutral
- Requires protoc compiler

## Implementation

### Migration Path
1. Define .proto schemas
2. Generate code
3. Migrate existing code

### Rollback Strategy
Revert to JSON if issues arise.

### Validation
Run benchmarks to verify performance.

## Metadata

**Category:** Architecture
**Impact:** High
**Tier:** T2
**Related PRs:** #100, #101
**Related ADRs:** ADR-0041, ADR-0043
**References:** https://protobuf.dev/

## Notes

This is a test ADR.
"""


@pytest.fixture
def template_content():
    """Sample template content for testing."""
    return """# ADR-XXXX: [Title]

## Status

**Status:** [Proposed | Accepted | Deprecated | Superseded]
**Date:** YYYY-MM-DD
**Author:** @username

## Context

[What is the issue that we're seeing that is motivating this decision or change?]

## Decision

[What is the change that we're proposing and/or doing?]

## Rationale

[Why are we making this decision? What are the driving factors?]

## Alternatives Considered

### Alternative 1: [Name]
- **Pros:** ...
- **Cons:** ...
- **Why rejected:** ...

## Consequences

### Positive
- [Benefit 1]

### Negative
- [Trade-off 1]

### Neutral
- [Impact 1]

## Implementation

### Migration Path
[How do we transition from current state to new state?]

### Rollback Strategy
[How do we revert if this decision proves problematic?]

### Validation
[How do we verify this decision is working as intended?]

## Metadata

**Category:** [Architecture | Infrastructure | Process | Tooling]
**Impact:** [High | Medium | Low]
**Tier:** [T1 | T2 | T3]
**Related PRs:** #XX, #YY
**Related ADRs:** ADR-AAA, ADR-BBB
**References:** [Links to docs, RFCs, etc.]

## Notes

[Any additional context, follow-up items, or open questions]
"""


# Tests for adr_generator.py


def test_slugify():
    """Test slugify function."""
    assert slugify("Use Protocol Buffers") == "use-protocol-buffers"
    assert slugify("TypedDict vs Pydantic") == "typeddict-vs-pydantic"
    assert slugify("ADR System!") == "adr-system"
    assert slugify("Multiple   Spaces") == "multiple-spaces"
    assert slugify("Special@Chars#Here") == "specialcharshere"


def test_generate_adr(temp_adr_dir, template_content):
    """Test ADR generation."""
    # Create template
    template_file = temp_adr_dir / "template.md"
    with open(template_file, "w") as f:
        f.write(template_content)

    # Generate ADR
    adr_file = generate_adr(
        adr_dir=temp_adr_dir,
        number="0042",
        title="Use Protocol Buffers",
        author="test-user",
        category="architecture",
        tier="t2",
    )

    assert adr_file.exists()
    assert adr_file.name == "0042-use-protocol-buffers.md"

    # Check content
    with open(adr_file) as f:
        content = f.read()

    assert "ADR-0042: Use Protocol Buffers" in content
    assert "@test-user" in content
    assert "Architecture" in content
    assert "T2" in content
    assert date.today().isoformat() in content
    assert "Proposed" in content


def test_generate_adr_without_template(temp_adr_dir):
    """Test ADR generation without template."""
    with pytest.raises(FileNotFoundError):
        generate_adr(
            adr_dir=temp_adr_dir,
            number="0042",
            title="Test ADR",
        )


# Tests for adr_indexer.py


def test_extract_adr_metadata(temp_adr_dir, sample_adr_content):
    """Test ADR metadata extraction."""
    # Create ADR file
    adr_file = temp_adr_dir / "0042-use-protocol-buffers.md"
    with open(adr_file, "w") as f:
        f.write(sample_adr_content)

    # Extract metadata
    metadata = extract_adr_metadata(adr_file)

    assert metadata is not None
    assert metadata["id"] == "0042"
    assert metadata["title"] == "Use Protocol Buffers for IPC"
    assert metadata["status"] == "accepted"
    assert metadata["date"] == "2026-01-20"
    assert metadata["author"] == "test-user"
    assert metadata["category"] == "architecture"
    assert metadata["impact"] == "high"
    assert metadata["tier"] == "t2"
    assert 100 in metadata["related_prs"]
    assert 101 in metadata["related_prs"]
    assert "0041" in metadata["related_adrs"]
    assert "0043" in metadata["related_adrs"]


def test_extract_adr_metadata_missing_file(temp_adr_dir):
    """Test metadata extraction for missing file."""
    adr_file = temp_adr_dir / "9999-missing.md"
    metadata = extract_adr_metadata(adr_file)
    assert metadata is None


def test_build_index(temp_adr_dir, sample_adr_content):
    """Test ADR index building."""
    # Create multiple ADR files
    for i in range(1, 4):
        adr_file = temp_adr_dir / f"000{i}-test-adr-{i}.md"
        content = sample_adr_content.replace("0042", f"000{i}")
        with open(adr_file, "w") as f:
            f.write(content)

    # Build index
    index = build_index(temp_adr_dir)

    assert "version" in index
    assert "last_updated" in index
    assert "adrs" in index
    assert len(index["adrs"]) == 3
    assert index["adrs"][0]["id"] == "0001"
    assert index["adrs"][1]["id"] == "0002"
    assert index["adrs"][2]["id"] == "0003"


def test_build_index_empty_dir(temp_adr_dir):
    """Test index building for empty directory."""
    index = build_index(temp_adr_dir)
    assert len(index["adrs"]) == 0


def test_get_next_adr_number(temp_adr_dir, sample_adr_content):
    """Test getting next ADR number."""
    # Empty directory
    assert get_next_adr_number(temp_adr_dir) == "0001"

    # Create some ADRs
    for i in [1, 2, 5]:
        adr_file = temp_adr_dir / f"000{i}-test.md"
        with open(adr_file, "w") as f:
            f.write(sample_adr_content)

    # Next number should be 6 (after 5)
    assert get_next_adr_number(temp_adr_dir) == "0006"


# Tests for adr_validator.py


def test_validate_adr_valid(temp_adr_dir, sample_adr_content):
    """Test validation of valid ADR."""
    adr_file = temp_adr_dir / "0042-use-protocol-buffers.md"
    with open(adr_file, "w") as f:
        f.write(sample_adr_content)

    issues = validate_adr(adr_file)
    assert len(issues) == 0


def test_validate_adr_missing_sections(temp_adr_dir):
    """Test validation of ADR with missing sections."""
    adr_file = temp_adr_dir / "0042-incomplete.md"
    with open(adr_file, "w") as f:
        f.write("# ADR-0042: Incomplete ADR\n\nSome content.")

    issues = validate_adr(adr_file)
    assert len(issues) > 0
    assert any("Missing required section" in issue for issue in issues)


def test_validate_adr_invalid_status(temp_adr_dir, sample_adr_content):
    """Test validation of ADR with invalid status."""
    content = sample_adr_content.replace("Accepted", "InvalidStatus")
    adr_file = temp_adr_dir / "0042-invalid-status.md"
    with open(adr_file, "w") as f:
        f.write(content)

    issues = validate_adr(adr_file)
    assert any("Invalid status" in issue for issue in issues)


def test_validate_adr_invalid_category(temp_adr_dir, sample_adr_content):
    """Test validation of ADR with invalid category."""
    content = sample_adr_content.replace("Architecture", "InvalidCategory")
    adr_file = temp_adr_dir / "0042-invalid-category.md"
    with open(adr_file, "w") as f:
        f.write(content)

    issues = validate_adr(adr_file)
    assert any("Invalid category" in issue for issue in issues)


def test_validate_adr_invalid_tier(temp_adr_dir, sample_adr_content):
    """Test validation of ADR with invalid tier."""
    content = sample_adr_content.replace("T2", "T9")
    adr_file = temp_adr_dir / "0042-invalid-tier.md"
    with open(adr_file, "w") as f:
        f.write(content)

    issues = validate_adr(adr_file)
    assert any("Invalid tier" in issue for issue in issues)


def test_validate_adr_number_mismatch(temp_adr_dir, sample_adr_content):
    """Test validation of ADR with number mismatch."""
    adr_file = temp_adr_dir / "0042-test.md"
    content = sample_adr_content.replace("ADR-0042", "ADR-0099")
    with open(adr_file, "w") as f:
        f.write(content)

    issues = validate_adr(adr_file)
    assert any("number mismatch" in issue for issue in issues)


def test_validate_adr_template_placeholders(temp_adr_dir, template_content):
    """Test validation of ADR with template placeholders."""
    adr_file = temp_adr_dir / "0042-template.md"
    with open(adr_file, "w") as f:
        f.write(template_content)

    issues = validate_adr(adr_file)
    assert len(issues) > 0
    assert any("placeholder" in issue.lower() for issue in issues)


def test_validate_all_adrs(temp_adr_dir, sample_adr_content):
    """Test validation of all ADRs."""
    # Create valid ADR
    valid_adr = temp_adr_dir / "0001-valid.md"
    with open(valid_adr, "w") as f:
        f.write(sample_adr_content.replace("0042", "0001"))

    # Create invalid ADR
    invalid_adr = temp_adr_dir / "0002-invalid.md"
    with open(invalid_adr, "w") as f:
        f.write("# ADR-0002: Invalid\n\nIncomplete content.")

    # Validate all
    results = validate_all_adrs(temp_adr_dir)

    assert len(results) == 2
    assert len(results[valid_adr]) == 0  # No issues
    assert len(results[invalid_adr]) > 0  # Has issues


def test_validate_adr_missing_file(temp_adr_dir):
    """Test validation of missing file."""
    adr_file = temp_adr_dir / "9999-missing.md"
    issues = validate_adr(adr_file)
    assert len(issues) == 1
    assert "not found" in issues[0]
