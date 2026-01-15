"""
L9 Response Tagger - Epistemic status and confidence tagging for claims.

This module implements GODMODE Part 4.2 (Confidence Framework) and Part 6 (Output Rendering).

Every claim should be tagged with:
- Confidence level (0.0 - 1.0)
- Epistemic status ([VERIFIED], [INFERRED], [GUESS], etc.)
- Source references (if applicable)

Version: 1.0.0
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional
import structlog

logger = structlog.get_logger(__name__)


# =============================================================================
# Epistemic Status Tags (GODMODE Part 4.2)
# =============================================================================


class EpistemicStatus(Enum):
    """
    Epistemic status tags for claims (GODMODE Part 4.2).

    These tags indicate the provenance and reliability of each claim.
    """

    VERIFIED = "[VERIFIED]"  # Cross-checked, Igor confirmed, authoritative source
    INFERRED = "[INFERRED]"  # Logical inference from verified premises
    MODEL = "[MODEL]"  # Output from L's reasoning/model knowledge
    GUESS = "[GUESS]"  # Educated guess, pattern-based, high uncertainty
    ASSUMPTION = "[ASSUMPTION]"  # Prerequisite assumption, not verified
    UNKNOWN = "[UNKNOWN]"  # Explicitly don't know
    RECALLED = "[RECALLED]"  # Retrieved from memory/prior conversation
    EXTERNAL = "[EXTERNAL]"  # From external source (web, API, tool)


# =============================================================================
# Confidence Levels (GODMODE Part 4.2)
# =============================================================================


class ConfidenceLevel(Enum):
    """
    Confidence level classifications.

    Maps numeric confidence to semantic meaning.
    """

    CERTAIN = "certain"  # 95-100%: Verified fact, hard math, Igor confirmed
    VERY_HIGH = "very_high"  # 90-94%: Multiple authoritative sources
    HIGH = "high"  # 80-89%: Single authoritative source, verified
    MEDIUM = "medium"  # 70-79%: Strong inference, good evidence
    LOW = "low"  # 50-69%: Educated guess, some evidence
    VERY_LOW = "very_low"  # 30-49%: Speculation, weak evidence
    UNKNOWN = "unknown"  # <30%: No reliable basis


def confidence_to_level(confidence: float) -> ConfidenceLevel:
    """
    Convert numeric confidence to ConfidenceLevel.

    Args:
        confidence: Float between 0.0 and 1.0

    Returns:
        ConfidenceLevel enum value
    """
    if confidence >= 0.95:
        return ConfidenceLevel.CERTAIN
    elif confidence >= 0.90:
        return ConfidenceLevel.VERY_HIGH
    elif confidence >= 0.80:
        return ConfidenceLevel.HIGH
    elif confidence >= 0.70:
        return ConfidenceLevel.MEDIUM
    elif confidence >= 0.50:
        return ConfidenceLevel.LOW
    elif confidence >= 0.30:
        return ConfidenceLevel.VERY_LOW
    else:
        return ConfidenceLevel.UNKNOWN


def level_to_confidence_range(level: ConfidenceLevel) -> tuple[float, float]:
    """
    Get the confidence range for a level.

    Args:
        level: ConfidenceLevel enum value

    Returns:
        Tuple of (min, max) confidence values
    """
    ranges = {
        ConfidenceLevel.CERTAIN: (0.95, 1.00),
        ConfidenceLevel.VERY_HIGH: (0.90, 0.94),
        ConfidenceLevel.HIGH: (0.80, 0.89),
        ConfidenceLevel.MEDIUM: (0.70, 0.79),
        ConfidenceLevel.LOW: (0.50, 0.69),
        ConfidenceLevel.VERY_LOW: (0.30, 0.49),
        ConfidenceLevel.UNKNOWN: (0.00, 0.29),
    }
    return ranges.get(level, (0.0, 1.0))


# =============================================================================
# Claim Tagging (GODMODE Part 4.2 + Part 6)
# =============================================================================


def tag_claim(
    claim: str,
    confidence: float,
    status: EpistemicStatus,
    sources: Optional[List[str]] = None,
    inline: bool = True,
) -> str:
    """
    Tag a claim with confidence and epistemic status.

    GODMODE Part 4.2 + Part 6: Every claim should be traceable.

    Args:
        claim: The claim text
        confidence: Confidence level (0.0 - 1.0)
        status: Epistemic status tag
        sources: Optional list of source references
        inline: If True, return inline format; if False, return verbose format

    Returns:
        Tagged claim string

    Examples:
        >>> tag_claim("Python is a programming language", 0.99, EpistemicStatus.VERIFIED)
        'Python is a programming language ([VERIFIED], 99%)'

        >>> tag_claim("This approach will work", 0.75, EpistemicStatus.INFERRED, ["prior experience"])
        'This approach will work[source:1] ([INFERRED], 75%)'
    """
    # Format source references
    sources_str = ""
    if sources:
        source_refs = ",".join([f"source:{i}" for i in range(1, len(sources) + 1)])
        sources_str = f"[{source_refs}]"

    # Format confidence
    confidence_pct = f"{confidence * 100:.0f}%"

    if inline:
        return f"{claim}{sources_str} ({status.value}, {confidence_pct})"
    else:
        # Verbose format for detailed output
        return f"{claim}{sources_str}\n  Status: {status.value}\n  Confidence: {confidence_pct}"


def tag_claim_minimal(
    claim: str,
    confidence: float,
) -> str:
    """
    Tag a claim with just confidence (minimal format).

    Args:
        claim: The claim text
        confidence: Confidence level (0.0 - 1.0)

    Returns:
        Tagged claim string with confidence only
    """
    return f"{claim} ({confidence * 100:.0f}% confidence)"


# =============================================================================
# Claim Builder (for structured responses)
# =============================================================================


class TaggedClaim:
    """
    Structured representation of a tagged claim.

    Useful for building responses with multiple claims.
    """

    def __init__(
        self,
        text: str,
        confidence: float,
        status: EpistemicStatus = EpistemicStatus.MODEL,
        sources: Optional[List[str]] = None,
        reasoning: Optional[str] = None,
    ):
        self.text = text
        self.confidence = confidence
        self.status = status
        self.sources = sources or []
        self.reasoning = reasoning
        self.level = confidence_to_level(confidence)

    def to_inline(self) -> str:
        """Return inline tagged format."""
        return tag_claim(
            self.text, self.confidence, self.status, self.sources, inline=True
        )

    def to_verbose(self) -> str:
        """Return verbose tagged format."""
        return tag_claim(
            self.text, self.confidence, self.status, self.sources, inline=False
        )

    def to_dict(self) -> Dict[str, Any]:
        """Return as dictionary for JSON serialization."""
        return {
            "text": self.text,
            "confidence": self.confidence,
            "confidence_level": self.level.value,
            "status": self.status.value,
            "sources": self.sources,
            "reasoning": self.reasoning,
        }


class ClaimCollection:
    """
    Collection of tagged claims for a response.

    Provides aggregate statistics and formatting.
    """

    def __init__(self):
        self.claims: List[TaggedClaim] = []

    def add(
        self,
        text: str,
        confidence: float,
        status: EpistemicStatus = EpistemicStatus.MODEL,
        sources: Optional[List[str]] = None,
        reasoning: Optional[str] = None,
    ) -> TaggedClaim:
        """Add a claim to the collection."""
        claim = TaggedClaim(text, confidence, status, sources, reasoning)
        self.claims.append(claim)
        return claim

    def overall_confidence(self) -> float:
        """Calculate weighted average confidence."""
        if not self.claims:
            return 0.0
        return sum(c.confidence for c in self.claims) / len(self.claims)

    def strongest_claim(self) -> Optional[TaggedClaim]:
        """Get the claim with highest confidence."""
        if not self.claims:
            return None
        return max(self.claims, key=lambda c: c.confidence)

    def weakest_claim(self) -> Optional[TaggedClaim]:
        """Get the claim with lowest confidence."""
        if not self.claims:
            return None
        return min(self.claims, key=lambda c: c.confidence)

    def by_status(self, status: EpistemicStatus) -> List[TaggedClaim]:
        """Get claims with a specific status."""
        return [c for c in self.claims if c.status == status]

    def verified_claims(self) -> List[TaggedClaim]:
        """Get all verified claims."""
        return self.by_status(EpistemicStatus.VERIFIED)

    def assumptions(self) -> List[TaggedClaim]:
        """Get all assumption claims."""
        return self.by_status(EpistemicStatus.ASSUMPTION)

    def low_confidence_claims(self, threshold: float = 0.70) -> List[TaggedClaim]:
        """Get claims below confidence threshold."""
        return [c for c in self.claims if c.confidence < threshold]

    def summary(self) -> Dict[str, Any]:
        """
        Generate epistemology summary for response.

        Returns:
            Dict suitable for "Confidence & Epistemology" section
        """
        strongest = self.strongest_claim()
        weakest = self.weakest_claim()

        return {
            "overall_confidence": self.overall_confidence(),
            "claim_count": len(self.claims),
            "strongest": strongest.text if strongest else None,
            "strongest_confidence": strongest.confidence if strongest else None,
            "weakest": weakest.text if weakest else None,
            "weakest_confidence": weakest.confidence if weakest else None,
            "verified_count": len(self.verified_claims()),
            "assumption_count": len(self.assumptions()),
            "low_confidence_count": len(self.low_confidence_claims()),
            "status_breakdown": {
                status.name: len(self.by_status(status))
                for status in EpistemicStatus
                if self.by_status(status)
            },
        }

    def to_list(self) -> List[Dict[str, Any]]:
        """Return all claims as list of dicts."""
        return [c.to_dict() for c in self.claims]


# =============================================================================
# Transparency Levels (GODMODE Part 4.1)
# =============================================================================


class TransparencyLevel(Enum):
    """
    Transparency levels for reasoning output (GODMODE Part 4.1).

    User can request different levels of detail.
    """

    LEVEL_0 = 0  # Summary only, confidence only
    LEVEL_1 = 1  # Standard: decision + reasoning + assumptions + confidence
    LEVEL_2 = 2  # Detailed: full trace + alternatives + epistemic status
    LEVEL_3 = 3  # Kernel trace: full kernel execution + activation log


def format_for_transparency(
    claims: ClaimCollection,
    level: TransparencyLevel = TransparencyLevel.LEVEL_1,
) -> str:
    """
    Format claims collection for a given transparency level.

    Args:
        claims: ClaimCollection to format
        level: Desired transparency level

    Returns:
        Formatted string appropriate for the level
    """
    if level == TransparencyLevel.LEVEL_0:
        # Summary only
        summary = claims.summary()
        return f"Overall confidence: {summary['overall_confidence'] * 100:.0f}%"

    elif level == TransparencyLevel.LEVEL_1:
        # Standard: inline tags
        lines = [c.to_inline() for c in claims.claims]
        summary = claims.summary()
        lines.append(
            f"\nOverall confidence: {summary['overall_confidence'] * 100:.0f}%"
        )
        if summary["assumption_count"] > 0:
            assumptions = claims.assumptions()
            lines.append(f"Assumptions: {', '.join(a.text for a in assumptions)}")
        return "\n".join(lines)

    elif level == TransparencyLevel.LEVEL_2:
        # Detailed: verbose tags
        lines = [c.to_verbose() for c in claims.claims]
        summary = claims.summary()
        lines.append("\n## Epistemology Summary")
        lines.append(
            f"- Overall confidence: {summary['overall_confidence'] * 100:.0f}%"
        )
        lines.append(f"- Verified claims: {summary['verified_count']}")
        lines.append(f"- Assumptions: {summary['assumption_count']}")
        lines.append(f"- Low confidence: {summary['low_confidence_count']}")
        return "\n".join(lines)

    else:  # LEVEL_3
        # Full kernel trace
        lines = ["## Full Claim Analysis"]
        for i, claim in enumerate(claims.claims, 1):
            lines.append(f"\n### Claim {i}")
            lines.append(f"Text: {claim.text}")
            lines.append(f"Status: {claim.status.value}")
            lines.append(f"Confidence: {claim.confidence * 100:.0f}%")
            lines.append(f"Level: {claim.level.value}")
            if claim.sources:
                lines.append(f"Sources: {', '.join(claim.sources)}")
            if claim.reasoning:
                lines.append(f"Reasoning: {claim.reasoning}")

        summary = claims.summary()
        lines.append("\n## Summary Statistics")
        lines.append(f"```json\n{summary}\n```")
        return "\n".join(lines)


# =============================================================================
# Public API
# =============================================================================

__all__ = [
    # Enums
    "EpistemicStatus",
    "ConfidenceLevel",
    "TransparencyLevel",
    # Functions
    "confidence_to_level",
    "level_to_confidence_range",
    "tag_claim",
    "tag_claim_minimal",
    "format_for_transparency",
    # Classes
    "TaggedClaim",
    "ClaimCollection",
]
