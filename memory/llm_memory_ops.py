"""LLMMemoryOps — isolated, testable LLM operations for the memory pipeline.

Three operations, each individually feature-flagged at call sites:
  1. episodic_summarize  — Claude 3.5 Sonnet
  2. semantic_distill    — Claude 3.5 Sonnet
  3. procedural_consolidate — Claude 3.5 Opus

ADR compliance: structlog-only, timezone-aware, builtin generics, explicit zip.
"""

from __future__ import annotations

import asyncio
import os
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Protocol

import structlog

logger = structlog.get_logger(__name__)

__dora_meta__ = {
    "component_name": "LLMMemoryOps",
    "module_version": "1.0.0",
    "status": "active",
}


# ---------------------------------------------------------------------------
# LLM client protocol
# ---------------------------------------------------------------------------


class LLMClient(Protocol):
    """Generic async LLM completion interface."""

    async def complete(
        self,
        prompt: str,
        *,
        model: str,
        max_tokens: int,
        temperature: float,
    ) -> str: ...


# ---------------------------------------------------------------------------
# Result models
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SummarizeResult:
    """Episodic summarization output."""

    summary: str
    key_events: list[str] = field(default_factory=list)
    created_at: datetime = field(
        default_factory=lambda: datetime.now(tz=UTC),
    )


@dataclass(frozen=True)
class DistillResult:
    """Semantic distillation output."""

    facts: list[str] = field(default_factory=list)
    insights: list[str] = field(default_factory=list)
    created_at: datetime = field(
        default_factory=lambda: datetime.now(tz=UTC),
    )


@dataclass(frozen=True)
class ConsolidateResult:
    """Procedural consolidation output."""

    heuristic_candidates: list[dict[str, Any]] = field(default_factory=list)
    synthesis: str = ""
    created_at: datetime = field(
        default_factory=lambda: datetime.now(tz=UTC),
    )


# ---------------------------------------------------------------------------
# Model constants — configurable via env vars, defaults to Phase 1 plan
# ---------------------------------------------------------------------------

EPISODIC_MODEL = os.environ.get("L9_EPISODIC_MODEL", "claude-3-5-sonnet-20241022")
SEMANTIC_MODEL = os.environ.get("L9_SEMANTIC_MODEL", "claude-3-5-sonnet-20241022")
PROCEDURAL_MODEL = os.environ.get("L9_PROCEDURAL_MODEL", "claude-3-5-opus-20240229")


# ---------------------------------------------------------------------------
# LLMMemoryOps
# ---------------------------------------------------------------------------


class LLMMemoryOps:
    """Encapsulates the three LLM operations used by the memory pipeline.

    Each operation is independently callable and fails gracefully, returning
    a fallback result with empty fields rather than raising.
    """

    def __init__(self, *, llm_client: LLMClient) -> None:
        self._llm = llm_client
        logger.info("llm_memory_ops_initialized")

    # ---- 1. Episodic summarization ----

    async def episodic_summarize(
        self,
        episodes: list[str],
        *,
        max_tokens: int = 1024,
        timeout_s: float = 15.0,
    ) -> SummarizeResult:
        """Summarize episodic memory traces into a coherent narrative."""
        if not episodes:
            return SummarizeResult(summary="")

        prompt = (
            "Summarize the following episodic memory traces into a concise "
            "narrative. Extract the key events as a bullet list.\n\n"
            + "\n---\n".join(episodes)
            + "\n\nSUMMARY:\nKEY EVENTS (one per line, prefixed with -):"
        )
        try:
            raw = await asyncio.wait_for(
                self._llm.complete(
                    prompt,
                    model=EPISODIC_MODEL,
                    max_tokens=max_tokens,
                    temperature=0.2,
                ),
                timeout=timeout_s,
            )
            return self._parse_summarize(raw)
        except Exception:
            logger.warning("episodic_summarize_failed", exc_info=True)
            return SummarizeResult(summary="")

    @staticmethod
    def _parse_summarize(raw: str) -> SummarizeResult:
        lines = raw.strip().splitlines()
        summary_parts: list[str] = []
        events: list[str] = []
        in_events = False
        for line in lines:
            stripped = line.strip()
            if stripped.upper().startswith("KEY EVENTS"):
                in_events = True
                continue
            if in_events and stripped.startswith("-"):
                events.append(stripped.lstrip("- ").strip())
            elif not in_events:
                summary_parts.append(stripped)
        return SummarizeResult(
            summary=" ".join(summary_parts).strip(),
            key_events=events,
        )

    # ---- 2. Semantic distillation ----

    async def semantic_distill(
        self,
        content: str,
        *,
        max_tokens: int = 1024,
        timeout_s: float = 15.0,
    ) -> DistillResult:
        """Extract structured facts and insights from content."""
        if not content or not content.strip():
            return DistillResult()

        prompt = (
            "Extract structured facts and insights from the following content.\n"
            "Format:\n"
            "FACT: <factual statement>\n"
            "INSIGHT: <analytical insight>\n\n" + content
        )
        try:
            raw = await asyncio.wait_for(
                self._llm.complete(
                    prompt,
                    model=SEMANTIC_MODEL,
                    max_tokens=max_tokens,
                    temperature=0.1,
                ),
                timeout=timeout_s,
            )
            return self._parse_distill(raw)
        except Exception:
            logger.warning("semantic_distill_failed", exc_info=True)
            return DistillResult()

    @staticmethod
    def _parse_distill(raw: str) -> DistillResult:
        facts: list[str] = []
        insights: list[str] = []
        for line in raw.strip().splitlines():
            stripped = line.strip()
            if stripped.upper().startswith("FACT:"):
                facts.append(stripped.split(":", 1)[1].strip())
            elif stripped.upper().startswith("INSIGHT:"):
                insights.append(stripped.split(":", 1)[1].strip())
        return DistillResult(facts=facts, insights=insights)

    # ---- 3. Procedural consolidation ----

    async def procedural_consolidate(
        self,
        traces: list[str],
        *,
        max_tokens: int = 2048,
        timeout_s: float = 30.0,
    ) -> ConsolidateResult:
        """Consolidate reasoning traces into heuristic candidates.

        Emits candidates only; does NOT auto-apply procedural changes.
        """
        if not traces:
            return ConsolidateResult()

        prompt = (
            "Analyze the following reasoning traces and extract reusable "
            "heuristic patterns. For each heuristic, provide:\n"
            "- name: descriptive name\n"
            "- condition: when to apply\n"
            "- action: what to do\n"
            "- confidence: 0.0-1.0\n\n"
            "SYNTHESIS: <overall synthesis paragraph>\n"
            "HEURISTIC: name=<name>|condition=<cond>|action=<act>|confidence=<conf>\n\n"
            + "\n---\n".join(traces)
        )
        try:
            raw = await asyncio.wait_for(
                self._llm.complete(
                    prompt,
                    model=PROCEDURAL_MODEL,
                    max_tokens=max_tokens,
                    temperature=0.3,
                ),
                timeout=timeout_s,
            )
            return self._parse_consolidate(raw)
        except Exception:
            logger.warning("procedural_consolidate_failed", exc_info=True)
            return ConsolidateResult()

    @staticmethod
    def _parse_consolidate(raw: str) -> ConsolidateResult:
        heuristics: list[dict[str, Any]] = []
        synthesis_parts: list[str] = []
        for line in raw.strip().splitlines():
            stripped = line.strip()
            if stripped.upper().startswith("HEURISTIC:"):
                h_str = stripped.split(":", 1)[1].strip()
                h: dict[str, Any] = {}
                for part in h_str.split("|"):
                    if "=" in part:
                        k, v = part.split("=", 1)
                        k = k.strip()
                        v = v.strip()
                        if k == "confidence":
                            try:
                                h[k] = float(v)
                            except ValueError:
                                h[k] = 0.5
                        else:
                            h[k] = v
                if h:
                    heuristics.append(h)
            elif stripped.upper().startswith("SYNTHESIS:"):
                synthesis_parts.append(stripped.split(":", 1)[1].strip())
            else:
                synthesis_parts.append(stripped)
        return ConsolidateResult(
            heuristic_candidates=heuristics,
            synthesis=" ".join(synthesis_parts).strip(),
        )


__all__ = [
    "ConsolidateResult",
    "DistillResult",
    "LLMClient",
    "LLMMemoryOps",
    "SummarizeResult",
]

__dora_footer__ = {
    "governance_level": "medium",
    "compliance_required": True,
}
