"""RetrievalMultiQuery — multi-query retrieval extension for RetrievalPipeline.

Non-breaking addition: accepts multiple query variants (rewritten + expansions),
calls existing retrieval per variant, merges candidates with dedup, and preserves
provenance (which query produced which hit).

ADR compliance: structlog-only, timezone-aware, builtin generics, explicit zip.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime, timezone
from typing import Any, Protocol

import structlog

logger = structlog.get_logger(__name__)

__dora_meta__ = {
    "component_name": "RetrievalMultiQuery",
    "module_version": "1.0.0",
    "status": "active",
}


# ---------------------------------------------------------------------------
# Protocol for existing retrieval
# ---------------------------------------------------------------------------


class SingleQueryRetriever(Protocol):
    """Protocol matching existing RetrievalPipeline.search(...)."""

    async def search(
        self,
        query: str,
        top_k: int = 10,
        **kwargs: Any,
    ) -> list[Any]: ...


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ProvenancedHit:
    """A retrieval hit with provenance tracking."""

    hit: Any
    source_query: str
    hit_id: str
    score: float = 0.0
    tier: str = ""
    retrieved_at: datetime = field(
        default_factory=lambda: datetime.now(tz=UTC),
    )


@dataclass(frozen=True)
class MultiQueryResult:
    """Merged, deduplicated results from multiple query variants."""

    hits: list[ProvenancedHit] = field(default_factory=list)
    queries_executed: int = 0
    duplicates_removed: int = 0


# ---------------------------------------------------------------------------
# Multi-query retrieval
# ---------------------------------------------------------------------------


async def retrieve_multiquery(
    retriever: SingleQueryRetriever,
    queries: list[str],
    *,
    top_k: int = 10,
    tier: str = "",
    **kwargs: Any,
) -> MultiQueryResult:
    """Execute multiple queries against a single retriever and merge results.

    Preserves provenance for audit: each hit tracks which query produced it.
    Deduplicates by packet_id (or object identity if unavailable).
    """
    all_hits: list[ProvenancedHit] = []
    seen_ids: set[str] = set()
    dupes = 0

    for q in queries:
        if not q or not q.strip():
            continue
        try:
            results = await retriever.search(q, top_k=top_k, tier=tier, **kwargs)
            for hit in results:
                hit_id = str(getattr(hit, "packet_id", id(hit)))
                if hit_id in seen_ids:
                    dupes += 1
                    continue
                seen_ids.add(hit_id)
                all_hits.append(
                    ProvenancedHit(
                        hit=hit,
                        source_query=q,
                        hit_id=hit_id,
                        score=float(getattr(hit, "score", 0.0)),
                        tier=tier,
                    ),
                )
        except Exception:
            logger.warning(
                "multiquery_retrieval_error",
                query=q,
                tier=tier,
                exc_info=True,
            )

    logger.info(
        "multiquery_retrieval_complete",
        queries_count=len(queries),
        total_hits=len(all_hits),
        duplicates_removed=dupes,
    )

    return MultiQueryResult(
        hits=all_hits,
        queries_executed=len(queries),
        duplicates_removed=dupes,
    )


__all__ = [
    "MultiQueryResult",
    "ProvenancedHit",
    "SingleQueryRetriever",
    "retrieve_multiquery",
]

__dora_footer__ = {
    "governance_level": "medium",
    "compliance_required": True,
}
