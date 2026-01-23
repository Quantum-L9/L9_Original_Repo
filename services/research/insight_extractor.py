"""
L9 Research Factory - Insight Extractor Agent
Version: 1.0.0

Extracts structured insights from research results.
Used by store_insights node to convert research output into Memory Substrate packets.
"""

# ============================================================================
__dora_meta__ = {
    "component_name": "Insight Extractor Agent",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2025-12-09T01:02:49Z",
    "updated_at": "2026-01-17T23:47:56Z",
    "layer": "operations",
    "domain": "research_services",
    "module_name": "insight_extractor",
    "type": "service",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": [],
        "memory_layers": [],
        "imported_by": ["services.research.research_graph"],
    },
}
# ============================================================================

from typing import Any

import structlog

from core.decorators import must_stay_async

logger = structlog.get_logger(__name__)


class InsightExtractorAgent:
    """
    Agent that extracts structured insights from research results.

    Transforms raw research output into discrete insight packets suitable
    for storage in the Memory Substrate.

    Insight types:
    - finding: Key research finding
    - recommendation: Actionable recommendation
    - observation: Notable observation
    - conclusion: Research conclusion
    """

    def __init__(self, model: str = "gpt-4o"):
        """
        Initialize the insight extractor.

        Args:
            model: LLM model to use for extraction
        """
        self.model = model

    @must_stay_async("callers use await")
    async def extract_insights(
        self,
        query: str,
        summary: str,
        evidence: list[dict[str, Any]],
        quality_score: float = 0.5,
    ) -> list[dict[str, Any]]:
        """
        Extract structured insights from research output.

        Args:
            query: Original research query
            summary: Final research summary
            evidence: List of evidence gathered
            quality_score: Quality score from critic

        Returns:
            List of insight dicts with type, content, confidence, etc.
        """
        insights: list[dict[str, Any]] = []

        if not summary or summary == "Failed to synthesize evidence":
            logger.warning("No valid summary to extract insights from")
            return []

        try:
            # Extract main conclusion as primary insight
            insights.append(
                {
                    "type": "conclusion",
                    "content": summary,
                    "summary": self._create_summary(summary),
                    "evidence_refs": [
                        ev.get("source", "unknown") for ev in evidence[:5]
                    ],
                    "tags": self._extract_tags(query, summary),
                    "confidence": quality_score,
                    "rationale": f"Primary research conclusion with {len(evidence)} evidence sources",
                }
            )

            # Extract findings from evidence
            for i, ev in enumerate(evidence[:10]):  # Limit to top 10
                if ev.get("content"):
                    insights.append(
                        {
                            "type": "finding",
                            "content": ev.get("content", ""),
                            "summary": self._truncate(ev.get("content", ""), 200),
                            "evidence_refs": [ev.get("source", f"evidence_{i}")],
                            "tags": self._extract_tags(query, ev.get("content", "")),
                            "confidence": ev.get("confidence", quality_score * 0.9),
                            "rationale": f"Evidence finding from {ev.get('source', 'research')}",
                        }
                    )

            logger.info(f"Extracted {len(insights)} insights from research")
            return insights

        except Exception as e:
            logger.error(f"Insight extraction failed: {e}")
            # Return at least the summary as a fallback insight
            return [
                {
                    "type": "conclusion",
                    "content": summary,
                    "summary": self._truncate(summary, 200),
                    "evidence_refs": [],
                    "tags": [],
                    "confidence": quality_score * 0.5,
                    "rationale": "Fallback extraction due to processing error",
                }
            ]

    def _create_summary(self, text: str, max_length: int = 300) -> str:
        """Create a brief summary from text."""
        if len(text) <= max_length:
            return text

        # Find a good break point
        truncated = text[:max_length]
        last_period = truncated.rfind(".")
        last_space = truncated.rfind(" ")

        if last_period > max_length * 0.7:
            return truncated[: last_period + 1]
        elif last_space > max_length * 0.7:
            return truncated[:last_space] + "..."
        else:
            return truncated + "..."

    def _truncate(self, text: str, max_length: int = 200) -> str:
        """Truncate text to max length."""
        if len(text) <= max_length:
            return text
        return text[: max_length - 3] + "..."

    def _extract_tags(self, query: str, content: str) -> list[str]:
        """Extract relevant tags from content."""
        # Simple keyword extraction
        tags = []

        # Common research domains
        domains = [
            "plastics",
            "recycling",
            "polymer",
            "HDPE",
            "PET",
            "PP",
            "PVC",
            "sustainability",
            "manufacturing",
            "quality",
            "contamination",
            "supply chain",
            "market",
            "pricing",
            "regulatory",
        ]

        combined = f"{query} {content}".lower()

        for domain in domains:
            if domain.lower() in combined:
                tags.append(domain.lower())

        return tags[:5]  # Limit to 5 tags


# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "SER-OPER-006",
    "governance_level": "medium",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": ["core.decorators"],
    "tags": ["async", "logging", "operations", "research-services", "service"],
    "keywords": [
        "agent",
        "extract",
        "extractor",
        "insight",
        "insights",
        "memory",
        "research",
        "substrate",
    ],
    "business_value": "Implements InsightExtractorAgent for insight extractor functionality",
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
