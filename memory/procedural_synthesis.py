"""ProceduralSynthesis — research-grade procedural synthesis via LLM.

Runs Claude 3.5 Opus over aggregated reasoning traces and outputs structured
heuristic candidates for governance review. Does NOT auto-apply changes.

ADR compliance: structlog-only, timezone-aware, builtin generics, explicit zip.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime, timezone
from typing import Any

import structlog

from memory.llm_memory_ops import LLMMemoryOps

logger = structlog.get_logger(__name__)

__dora_meta__ = {
    "component_name": "ProceduralSynthesis",
    "module_version": "1.0.0",
    "status": "active",
}


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class HeuristicCandidate:
    """A single heuristic candidate extracted from traces."""

    name: str
    condition: str
    action: str
    confidence: float
    source_trace_ids: list[str] = field(default_factory=list)
    created_at: datetime = field(
        default_factory=lambda: datetime.now(tz=UTC),
    )


@dataclass(frozen=True)
class SynthesisReport:
    """Full synthesis report with candidates + narrative."""

    candidates: list[HeuristicCandidate] = field(default_factory=list)
    synthesis_narrative: str = ""
    trace_count: int = 0
    created_at: datetime = field(
        default_factory=lambda: datetime.now(tz=UTC),
    )


# ---------------------------------------------------------------------------
# ProceduralSynthesizer
# ---------------------------------------------------------------------------


class ProceduralSynthesizer:
    """Research-grade procedural synthesis from reasoning traces.

    Emits heuristic candidates for governance review; does not auto-apply
    procedural changes to the system.
    """

    def __init__(self, *, llm_ops: LLMMemoryOps) -> None:
        self._llm_ops = llm_ops
        logger.info("procedural_synthesizer_initialized")

    async def synthesize(
        self,
        traces: list[dict[str, Any]],
        *,
        max_tokens: int = 2048,
        timeout_s: float = 30.0,
    ) -> SynthesisReport:
        """Run procedural consolidation over traces.

        Args:
            traces: list of dicts with 'trace_id' and 'content' keys.
            max_tokens: LLM budget for consolidation.
            timeout_s: hard timeout for LLM call.

        Returns:
            SynthesisReport with heuristic candidates.
        """
        if not traces:
            return SynthesisReport()

        trace_texts = [str(t.get("content", "")) for t in traces]
        trace_ids = [str(t.get("trace_id", "")) for t in traces]

        result = await self._llm_ops.procedural_consolidate(
            trace_texts,
            max_tokens=max_tokens,
            timeout_s=timeout_s,
        )

        candidates = [
            HeuristicCandidate(
                name=h.get("name", "unnamed"),
                condition=h.get("condition", ""),
                action=h.get("action", ""),
                confidence=float(h.get("confidence", 0.5)),
                source_trace_ids=trace_ids,
            )
            for h in result.heuristic_candidates
        ]

        report = SynthesisReport(
            candidates=candidates,
            synthesis_narrative=result.synthesis,
            trace_count=len(traces),
        )

        logger.info(
            "procedural_synthesis_complete",
            trace_count=len(traces),
            candidate_count=len(candidates),
        )
        return report


__all__ = [
    "HeuristicCandidate",
    "ProceduralSynthesizer",
    "SynthesisReport",
]

__dora_footer__ = {
    "governance_level": "medium",
    "compliance_required": True,
}
