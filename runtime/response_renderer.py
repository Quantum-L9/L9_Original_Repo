"""
L9 Response Renderer - Structured response generation with 5-section template.

This module implements GODMODE Part 6 (Output Rendering).

Every response follows the template:
1. Opening Statement
2. Main Content (sections A, B, C, ...)
3. Confidence & Epistemology
4. Igor Input Needed?
5. Kernel Status

Version: 1.0.0
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, TYPE_CHECKING
import structlog

if TYPE_CHECKING:
    pass

logger = structlog.get_logger(__name__)


# =============================================================================
# Response Template (GODMODE Part 6)
# =============================================================================


class ResponseRenderer:
    """
    Render responses with the 5-section GODMODE template.

    Every L response should follow this structure for consistency
    and auditability.
    """

    @staticmethod
    def render(
        opening: str,
        main_sections: Dict[str, str],
        confidence_summary: Dict[str, Any],
        igor_input_needed: bool = False,
        igor_input_prompt: str = "",
        kernel_state: Optional[Any] = None,
        include_kernel_status: bool = True,
    ) -> str:
        """
        Render complete response with all 5 sections.

        Args:
            opening: Opening statement (brief summary)
            main_sections: Dict of section_name -> content
            confidence_summary: Dict with overall, strongest, weakest, assumptions
            igor_input_needed: Whether Igor needs to make a decision
            igor_input_prompt: What decision is needed from Igor
            kernel_state: KernelState object for status section
            include_kernel_status: Whether to include kernel status section

        Returns:
            Formatted response string
        """
        sections = []

        # Section 1: Opening Statement
        sections.append(opening)
        sections.append("")

        # Section 2: Main Content
        for section_name, content in main_sections.items():
            if section_name.startswith("##"):
                sections.append(f"{section_name}")
            else:
                sections.append(f"## {section_name}")
            sections.append(content)
            sections.append("")

        # Section 3: Confidence & Epistemology
        sections.append("## Confidence & Epistemology")
        sections.append(ResponseRenderer._format_confidence(confidence_summary))
        sections.append("")

        # Section 4: Igor Input Needed?
        if igor_input_needed:
            sections.append("## Igor Input Needed")
            sections.append(igor_input_prompt)
            sections.append("")

        # Section 5: Kernel Status
        if include_kernel_status and kernel_state:
            sections.append("## Kernel Status")
            sections.append(ResponseRenderer._format_kernel_status(kernel_state))
            sections.append("")

        return "\n".join(sections)

    @staticmethod
    def _format_confidence(summary: Dict[str, Any]) -> str:
        """Format confidence summary section."""
        lines = []

        overall = summary.get("overall", summary.get("overall_confidence", 0))
        lines.append(f"- **Overall confidence:** {overall * 100:.0f}%")

        strongest = summary.get("strongest")
        if strongest:
            strongest_conf = summary.get("strongest_confidence", 0)
            lines.append(
                f"- **Strongest claim:** {strongest} ({strongest_conf * 100:.0f}%)"
            )

        weakest = summary.get("weakest")
        if weakest:
            weakest_conf = summary.get("weakest_confidence", 0)
            lines.append(f"- **Weakest claim:** {weakest} ({weakest_conf * 100:.0f}%)")

        assumptions = summary.get("assumptions", [])
        if assumptions:
            if isinstance(assumptions, list):
                lines.append(
                    f"- **Assumptions:** {', '.join(str(a) for a in assumptions)}"
                )
            else:
                lines.append(f"- **Assumptions:** {assumptions}")

        verified = summary.get("verified_count", 0)
        if verified:
            lines.append(f"- **Verified claims:** {verified}")

        low_conf = summary.get("low_confidence_count", 0)
        if low_conf:
            lines.append(f"- **Low confidence claims:** {low_conf}")

        return "\n".join(lines)

    @staticmethod
    def _format_kernel_status(kernel_state: Any) -> str:
        """Format kernel status section."""
        lines = []

        # Mode and activation
        mode = getattr(kernel_state, "mode", "unknown")
        initialized = getattr(kernel_state, "initialized", False)
        lines.append(f"- **Mode:** {mode}")
        lines.append(f"- **Initialized:** {'✓' if initialized else '✗'}")

        # Active kernels
        active = getattr(kernel_state, "active_kernels", {})
        lines.append(f"- **Active kernels:** {len(active)}")

        # Decision/escalation counts
        decisions = getattr(kernel_state, "decisions", [])
        escalations = getattr(kernel_state, "escalations", [])
        tools = getattr(kernel_state, "tools_executed", [])

        lines.append(f"- **Decisions logged:** {len(decisions)}")
        lines.append(f"- **Tools executed:** {len(tools)}")

        if escalations:
            pending = sum(1 for e in escalations if e.get("awaiting") == "IGOR")
            critical = sum(1 for e in escalations if e.get("severity") == "CRITICAL")
            lines.append(
                f"- **Escalations:** {len(escalations)} (pending: {pending}, critical: {critical})"
            )

        return "\n".join(lines)

    @staticmethod
    def render_minimal(
        content: str,
        confidence: float,
        kernel_state: Optional[Any] = None,
    ) -> str:
        """
        Render minimal response (for simple queries).

        Args:
            content: Main response content
            confidence: Overall confidence
            kernel_state: Optional kernel state

        Returns:
            Formatted response string
        """
        sections = [content, ""]

        sections.append(f"*Confidence: {confidence * 100:.0f}%*")

        if kernel_state:
            mode = getattr(kernel_state, "mode", "executive")
            sections.append(f"*Mode: {mode}*")

        return "\n".join(sections)

    @staticmethod
    def render_escalation(
        issue: str,
        context: str,
        confidence: float,
        options: List[str],
        severity: str = "MEDIUM",
    ) -> str:
        """
        Render escalation to Igor.

        Args:
            issue: Description of the issue
            context: Full context
            confidence: Confidence level
            options: List of options for Igor
            severity: Escalation severity

        Returns:
            Formatted escalation string
        """
        lines = [
            f"⚠️ **ESCALATION** [Severity: {severity}]",
            "",
            f"**Issue:** {issue}",
            "",
            f"**Context:** {context}",
            "",
            f"**My confidence:** {confidence * 100:.0f}%",
            "",
            "**Options:**",
        ]

        for i, option in enumerate(options, 1):
            lines.append(f"{i}. {option}")

        lines.extend(
            [
                "",
                "**Awaiting your decision...**",
            ]
        )

        return "\n".join(lines)


# =============================================================================
# Response Builder (for programmatic construction)
# =============================================================================


class ResponseBuilder:
    """
    Builder pattern for constructing responses.

    Usage:
        response = (ResponseBuilder()
            .opening("Here's what I found:")
            .section("Analysis", "The data shows...")
            .section("Recommendation", "I suggest...")
            .confidence(overall=0.85, strongest="Analysis is solid", weakest="Market assumptions")
            .needs_igor_input("Should I proceed with implementation?")
            .build(kernel_state))
    """

    def __init__(self):
        self._opening = ""
        self._sections: Dict[str, str] = {}
        self._confidence: Dict[str, Any] = {"overall": 0.5}
        self._igor_needed = False
        self._igor_prompt = ""
        self._include_kernel = True

    def opening(self, text: str) -> "ResponseBuilder":
        """Set opening statement."""
        self._opening = text
        return self

    def section(self, name: str, content: str) -> "ResponseBuilder":
        """Add a main content section."""
        self._sections[name] = content
        return self

    def confidence(
        self,
        overall: float,
        strongest: Optional[str] = None,
        weakest: Optional[str] = None,
        assumptions: Optional[List[str]] = None,
    ) -> "ResponseBuilder":
        """Set confidence summary."""
        self._confidence = {
            "overall": overall,
            "strongest": strongest,
            "weakest": weakest,
            "assumptions": assumptions or [],
        }
        return self

    def from_claims(self, claims: Any) -> "ResponseBuilder":
        """Set confidence from ClaimCollection."""
        if hasattr(claims, "summary"):
            self._confidence = claims.summary()
        return self

    def needs_igor_input(self, prompt: str) -> "ResponseBuilder":
        """Mark that Igor input is needed."""
        self._igor_needed = True
        self._igor_prompt = prompt
        return self

    def no_kernel_status(self) -> "ResponseBuilder":
        """Exclude kernel status section."""
        self._include_kernel = False
        return self

    def build(self, kernel_state: Optional[Any] = None) -> str:
        """Build the final response string."""
        return ResponseRenderer.render(
            opening=self._opening,
            main_sections=self._sections,
            confidence_summary=self._confidence,
            igor_input_needed=self._igor_needed,
            igor_input_prompt=self._igor_prompt,
            kernel_state=kernel_state,
            include_kernel_status=self._include_kernel,
        )


# =============================================================================
# Citation Protocol (GODMODE Part 6.2)
# =============================================================================


def format_citation(source_id: int, source_name: str = "") -> str:
    """
    Format a citation reference.

    Args:
        source_id: Numeric source identifier
        source_name: Optional source name

    Returns:
        Formatted citation string
    """
    if source_name:
        return f"[{source_id}: {source_name}]"
    return f"[{source_id}]"


def format_claim_with_citation(
    claim: str,
    sources: List[int],
    confidence: Optional[float] = None,
) -> str:
    """
    Format a claim with citation(s).

    Args:
        claim: The claim text
        sources: List of source IDs
        confidence: Optional confidence level

    Returns:
        Formatted claim with citations
    """
    citations = ",".join(str(s) for s in sources)
    result = f"{claim}[{citations}]"

    if confidence is not None:
        result += f" ({confidence * 100:.0f}%)"

    return result


def format_inference(claim: str, base_facts: List[str]) -> str:
    """
    Format an inference claim.

    Args:
        claim: The inferred claim
        base_facts: Facts the inference is based on

    Returns:
        Formatted inference string
    """
    facts_str = "; ".join(base_facts)
    return f"{claim} (inference from: {facts_str})"


def format_guess(claim: str, pattern: str, confidence: float) -> str:
    """
    Format a guess/speculation.

    Args:
        claim: The guessed claim
        pattern: Pattern the guess is based on
        confidence: Confidence level

    Returns:
        Formatted guess string
    """
    return f"{claim} (guess based on {pattern}, {confidence * 100:.0f}% confidence)"


# =============================================================================
# Public API
# =============================================================================

__all__ = [
    # Main renderer
    "ResponseRenderer",
    "ResponseBuilder",
    # Citation helpers
    "format_citation",
    "format_claim_with_citation",
    "format_inference",
    "format_guess",
]
