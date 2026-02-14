"""PipelineRouter — single orchestration entrypoint for memory ingest + query.

Composes existing pipelines (IngestionPipeline, RetrievalPipeline, HybridRAG)
and adds query-rewrite + tier-blending to produce assembled context sections.

ADR compliance: structlog-only, timezone-aware, builtin generics, explicit zip.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from datetime import UTC, datetime, timezone
from enum import Enum
from typing import Any, Protocol

import structlog

logger = structlog.get_logger(__name__)

__dora_meta__ = {
    "component_name": "PipelineRouter",
    "module_version": "1.0.0",
    "status": "active",
}


# ---------------------------------------------------------------------------
# Public data models
# ---------------------------------------------------------------------------


class MemoryTier(str, Enum):
    """Memory retrieval tiers."""

    EPISODIC = "episodic"
    SEMANTIC = "semantic"
    PROCEDURAL = "procedural"


@dataclass(frozen=True)
class TierRetrievalConfig:
    """Per-tier retrieval knobs."""

    tiers: tuple[MemoryTier, ...] = (
        MemoryTier.EPISODIC,
        MemoryTier.SEMANTIC,
        MemoryTier.PROCEDURAL,
    )
    top_k_per_tier: int = 10
    min_score: float = 0.35
    enable_query_rewrite: bool = True
    rewrite_timeout_s: float = 5.0
    retrieval_timeout_s: float = 15.0


@dataclass(frozen=True)
class LLMConfig:
    """LLM model + budget constraints for router operations."""

    rewrite_model: str = "gpt-4.1-mini"
    summarize_model: str = "claude-3-5-sonnet-20241022"
    max_rewrite_tokens: int = 256
    max_summarize_tokens: int = 1024
    temperature: float = 0.2


@dataclass(frozen=True)
class CallerContext:
    """Caller identity passed through the router for governance scoping."""

    agent_id: str = "unknown"
    caller_id: str = "unknown"
    trace_id: str = ""
    correlation_id: str = ""


@dataclass(frozen=True)
class ContextSection:
    """A single assembled context section from a memory tier."""

    tier: MemoryTier
    content: str
    sources: list[dict[str, Any]] = field(default_factory=list)
    score: float = 0.0
    retrieved_at: datetime = field(
        default_factory=lambda: datetime.now(tz=UTC),
    )


@dataclass(frozen=True)
class RouterResult:
    """Aggregated result from a router query operation."""

    sections: list[ContextSection] = field(default_factory=list)
    rewritten_query: str = ""
    expansions: list[str] = field(default_factory=list)
    latency_ms: float = 0.0
    tiers_queried: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Protocol interfaces (for DI — avoids hard imports)
# ---------------------------------------------------------------------------


class IngestionService(Protocol):
    """Protocol matching IngestionPipeline.ingest(...)."""

    async def ingest(self, envelope: Any, **kwargs: Any) -> Any: ...


class RetrievalService(Protocol):
    """Protocol matching RetrievalPipeline public API."""

    async def search(
        self,
        query: str,
        top_k: int = 10,
        **kwargs: Any,
    ) -> list[Any]: ...


class ImportanceService(Protocol):
    """Protocol matching ImportanceManager update API."""

    async def update_importance(
        self,
        packet_id: str,
        delta: float,
        reason: str,
        **kwargs: Any,
    ) -> None: ...


class QueryRewriteService(Protocol):
    """Protocol matching QueryRewriter.rewrite(...)."""

    async def rewrite(
        self,
        query: str,
        *,
        model: str,
        max_tokens: int,
        timeout_s: float,
    ) -> Any: ...


class ContextBuilderService(Protocol):
    """Protocol matching HierarchicalContextBuilder.build(...)."""

    async def build(self, sections: list[Any], **kwargs: Any) -> list[Any]: ...


# ---------------------------------------------------------------------------
# PipelineRouter
# ---------------------------------------------------------------------------


class PipelineRouter:
    """Orchestrates memory ingest + query across tiers with LLM enrichment.

    Design:
    - Fail-loud on construction errors (missing required services).
    - Graceful degradation on optional enrichment (query rewrite, summarize).
    - All LLM calls bounded by explicit timeouts and token budgets.
    """

    def __init__(
        self,
        *,
        ingestion: IngestionService,
        retrieval: RetrievalService,
        importance: ImportanceService | None = None,
        rewriter: QueryRewriteService | None = None,
        context_builder: ContextBuilderService | None = None,
    ) -> None:
        if ingestion is None:
            raise ValueError("ingestion service is required — fail-loud per ADR-0055")
        if retrieval is None:
            raise ValueError("retrieval service is required — fail-loud per ADR-0055")

        self._ingestion = ingestion
        self._retrieval = retrieval
        self._importance = importance
        self._rewriter = rewriter
        self._context_builder = context_builder
        logger.info(
            "pipeline_router_initialized",
            has_rewriter=rewriter is not None,
            has_importance=importance is not None,
            has_context_builder=context_builder is not None,
        )

    # ---- Ingest ----

    async def ingest(
        self,
        envelope: Any,
        *,
        segment: str = "episodic",
        caller: CallerContext | None = None,
    ) -> Any:
        """Ingest a PacketEnvelope via the existing IngestionPipeline."""
        _caller = caller or CallerContext()
        t0 = time.monotonic()
        log = logger.bind(
            trace_id=_caller.trace_id,
            correlation_id=_caller.correlation_id,
            agent_id=_caller.agent_id,
            segment=segment,
            stage="ingest",
        )
        log.info("pipeline_router_ingest_start")
        try:
            result = await self._ingestion.ingest(envelope, segment=segment)
            elapsed_ms = (time.monotonic() - t0) * 1000
            log.info("pipeline_router_ingest_complete", latency_ms=round(elapsed_ms, 2))
            return result
        except Exception:
            log.error("pipeline_router_ingest_failed", exc_info=True)
            raise

    # ---- Query ----

    async def query(
        self,
        query: str,
        *,
        tier_cfg: TierRetrievalConfig | None = None,
        llm_cfg: LLMConfig | None = None,
        caller: CallerContext | None = None,
    ) -> RouterResult:
        """Run tier-blended retrieval with optional query rewrite."""
        _tier_cfg = tier_cfg or TierRetrievalConfig()
        _llm_cfg = llm_cfg or LLMConfig()
        _caller = caller or CallerContext()
        t0 = time.monotonic()
        log = logger.bind(
            trace_id=_caller.trace_id,
            correlation_id=_caller.correlation_id,
            agent_id=_caller.agent_id,
            stage="query",
        )

        # Step 1: Query rewrite (graceful degradation)
        rewritten = query
        expansions: list[str] = []
        if _tier_cfg.enable_query_rewrite and self._rewriter is not None:
            try:
                rw_result = await self._rewriter.rewrite(
                    query,
                    model=_llm_cfg.rewrite_model,
                    max_tokens=_llm_cfg.max_rewrite_tokens,
                    timeout_s=_tier_cfg.rewrite_timeout_s,
                )
                rewritten = getattr(rw_result, "rewritten_query", query)
                expansions = getattr(rw_result, "expansions", [])
                log.info(
                    "query_rewrite_complete",
                    original=query,
                    rewritten=rewritten,
                    expansion_count=len(expansions),
                )
            except Exception:
                log.warning("query_rewrite_failed_graceful_degradation", exc_info=True)
                rewritten = query
                expansions = []

        # Step 2: Tier-blended retrieval
        all_queries = [rewritten, *expansions]
        sections: list[ContextSection] = []
        tiers_queried: list[str] = []

        for tier in _tier_cfg.tiers:
            tier_hits: list[dict[str, Any]] = []
            seen_ids: set[str] = set()

            for q in all_queries:
                try:
                    hits = await self._retrieval.search(
                        q,
                        top_k=_tier_cfg.top_k_per_tier,
                        tier=tier.value,
                    )
                    for hit in hits:
                        hit_id = str(getattr(hit, "packet_id", id(hit)))
                        if hit_id not in seen_ids:
                            seen_ids.add(hit_id)
                            tier_hits.append(
                                {"hit": hit, "source_query": q, "tier": tier.value},
                            )
                except Exception:
                    log.warning(
                        "tier_retrieval_failed",
                        tier=tier.value,
                        query=q,
                        exc_info=True,
                    )

            if tier_hits:
                best_score = max(
                    (getattr(h["hit"], "score", 0.0) for h in tier_hits),
                    default=0.0,
                )
                content_parts = [
                    str(getattr(h["hit"], "content", h["hit"]))
                    for h in tier_hits
                    if getattr(h["hit"], "score", 1.0) >= _tier_cfg.min_score
                ]
                sections.append(
                    ContextSection(
                        tier=tier,
                        content="\n\n".join(content_parts),
                        sources=tier_hits,
                        score=best_score,
                    ),
                )
            tiers_queried.append(tier.value)

        elapsed_ms = (time.monotonic() - t0) * 1000
        log.info(
            "pipeline_router_query_complete",
            latency_ms=round(elapsed_ms, 2),
            sections_count=len(sections),
            tiers_queried=tiers_queried,
        )

        return RouterResult(
            sections=sections,
            rewritten_query=rewritten,
            expansions=expansions,
            latency_ms=round(elapsed_ms, 2),
            tiers_queried=tiers_queried,
        )

    # ---- Context build (thin wrapper) ----

    async def build_context(
        self,
        sections: list[ContextSection],
        **kwargs: Any,
    ) -> list[Any]:
        """Delegate to HierarchicalContextBuilder if available."""
        if self._context_builder is not None:
            return await self._context_builder.build(sections, **kwargs)
        return [s.content for s in sections]


__all__ = [
    "CallerContext",
    "ContextBuilderService",
    "ContextSection",
    "ImportanceService",
    "IngestionService",
    "LLMConfig",
    "MemoryTier",
    "PipelineRouter",
    "QueryRewriteService",
    "RetrievalService",
    "RouterResult",
    "TierRetrievalConfig",
]

__dora_footer__ = {
    "governance_level": "medium",
    "compliance_required": True,
}
