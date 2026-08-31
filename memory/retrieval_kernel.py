"""
L9 Retrieval Kernel — 3-Tier Retrieval Cascade
===============================================
L9-native replacement for CursorRetrievalKernel.

Retrieval tiers (fastest → richest):
  1. Working Memory Cache (Redis) — session-scoped, sub-ms
  2. Semantic Search (Postgres/pgvector) — semantic recall
  3. Graph Context (Neo4j) — relational context

Each tier has an independent timeout. On failure, the kernel logs a
warning and falls through to the next tier (ADR-0055: observability =
graceful degradation).
"""

from __future__ import annotations

# ============================================================================
__dora_meta__ = {
    "component_name": "L9 Retrieval Kernel",
    "module_version": "1.0.0",
    "created_by": "Manus Agent",
    "created_at": "2026-02-19T12:00:00Z",
    "updated_at": "2026-02-19T12:00:00Z",
    "layer": "core",
    "domain": "memory",
    "module_name": "memory.retrieval_kernel",
    "type": "service",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": ["Redis", "PostgreSQL", "Neo4j"],
        "memory_layers": ["working_memory", "semantic_memory"],
        "imported_by": [],
    },
}
# ============================================================================

import asyncio
from typing import Any, Protocol, runtime_checkable

import structlog
from pydantic import BaseModel, Field

from core.decorators import must_stay_async

logger = structlog.get_logger(__name__)


# =============================================================================
# Result Model
# =============================================================================


class RetrievalHit(BaseModel):
    """A single retrieval result from any tier."""

    source_tier: str = Field(
        ..., description="'working_memory', 'semantic', or 'graph'"
    )
    content: str = Field(..., description="Retrieved content text")
    score: float = Field(
        default=0.0, description="Relevance score (0.0–1.0 where applicable)"
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Tier-specific metadata"
    )

    model_config = {"extra": "forbid"}


# =============================================================================
# Backend Protocols (ADR-0026)
# =============================================================================


@runtime_checkable
class WorkingMemoryBackend(Protocol):
    """Protocol for working memory cache reads."""

    async def hydrate(self, repo_id: str, branch: str) -> Any: ...


@runtime_checkable
class SemanticSearchBackend(Protocol):
    """Protocol for semantic vector search."""

    async def search_packets(
        self,
        query: str,
        top_k: int = 5,
        **kwargs: Any,
    ) -> list[Any]: ...


@runtime_checkable
class GraphContextBackend(Protocol):
    """Protocol for graph-based context retrieval."""

    async def query_history(
        self,
        session_id: str,
        limit: int = 10,
    ) -> list[Any]: ...


# =============================================================================
# L9 Retrieval Kernel
# =============================================================================


class L9RetrievalKernel:
    """
    3-tier retrieval cascade for L9 agents.

    Each tier is optional and injected via Protocol-based DI.
    Missing tiers are silently skipped. Timeouts are per-tier.

    Usage::

        kernel = L9RetrievalKernel(
            working_memory=wmc_service,
            semantic=substrate_service,
            graph=graph_memory,
        )
        hits = await kernel.retrieve(
            agent_id="agent:research",
            query="What did Igor decide about the DAG?",
        )
    """

    __slots__ = (
        "_graph",
        "_graph_timeout",
        "_semantic",
        "_semantic_timeout",
        "_wm_timeout",
        "_working_memory",
    )

    def __init__(
        self,
        *,
        working_memory: WorkingMemoryBackend | None = None,
        semantic: SemanticSearchBackend | None = None,
        graph: GraphContextBackend | None = None,
        wm_timeout: float = 1.0,
        semantic_timeout: float = 5.0,
        graph_timeout: float = 5.0,
    ) -> None:
        """
        Initialise the retrieval kernel.

        Args:
            working_memory: Redis-backed working memory service.
            semantic: Postgres/pgvector semantic search service.
            graph: Neo4j graph context service.
            wm_timeout: Timeout in seconds for working memory tier.
            semantic_timeout: Timeout in seconds for semantic tier.
            graph_timeout: Timeout in seconds for graph tier.
        """
        self._working_memory = working_memory
        self._semantic = semantic
        self._graph = graph
        self._wm_timeout = wm_timeout
        self._semantic_timeout = semantic_timeout
        self._graph_timeout = graph_timeout
        logger.info(
            "retrieval_kernel.init",
            has_working_memory=working_memory is not None,
            has_semantic=semantic is not None,
            has_graph=graph is not None,
        )

    @must_stay_async("callers use await")
    async def retrieve(
        self,
        *,
        agent_id: str,
        thread_id: str | None = None,
        query: str,
        top_k: int = 5,
    ) -> list[RetrievalHit]:
        """
        Execute the 3-tier retrieval cascade.

        Args:
            agent_id: The agent requesting context.
            thread_id: Optional thread/session ID for scoping.
            query: Natural language query for semantic search.
            top_k: Maximum results per tier.

        Returns:
            Combined list of RetrievalHit from all available tiers,
            ordered by tier priority (working memory first).
        """
        hits: list[RetrievalHit] = []

        # ── Tier 1: Working Memory Cache ────────────────────────────────
        if self._working_memory is not None:
            tier_hits = await self._retrieve_working_memory(
                agent_id=agent_id,
                thread_id=thread_id,
                top_k=top_k,
            )
            hits.extend(tier_hits)

        # ── Tier 2: Semantic Search ─────────────────────────────────────
        if self._semantic is not None:
            tier_hits = await self._retrieve_semantic(
                query=query,
                agent_id=agent_id,
                top_k=top_k,
            )
            hits.extend(tier_hits)

        # ── Tier 3: Graph Context ───────────────────────────────────────
        if self._graph is not None and thread_id:
            tier_hits = await self._retrieve_graph(
                thread_id=thread_id,
                top_k=top_k,
            )
            hits.extend(tier_hits)

        logger.info(
            "retrieval_kernel.retrieve.complete",
            agent_id=agent_id,
            thread_id=thread_id,
            total_hits=len(hits),
            tiers_hit=[h.source_tier for h in hits[:3]],
        )

        return hits

    # --------------------------------------------------------------------- #
    # Tier implementations
    # --------------------------------------------------------------------- #

    async def _retrieve_working_memory(
        self,
        *,
        agent_id: str,
        thread_id: str | None,
        top_k: int,
    ) -> list[RetrievalHit]:
        """Tier 1: Working memory cache (Redis)."""
        try:
            snapshot = await asyncio.wait_for(
                self._working_memory.hydrate(  # type: ignore[union-attr]
                    repo_id=agent_id,
                    branch=thread_id or "main",
                ),
                timeout=self._wm_timeout,
            )
            if snapshot is None:
                return []

            # Extract content from snapshot
            content_str = ""
            if hasattr(snapshot, "intent") and snapshot.intent:
                content_str = snapshot.intent
            elif hasattr(snapshot, "__dict__"):
                content_str = str(snapshot.__dict__)
            else:
                content_str = str(snapshot)

            if not content_str:
                return []

            return [
                RetrievalHit(
                    source_tier="working_memory",
                    content=content_str[:2000],
                    score=1.0,
                    metadata={
                        "agent_id": agent_id,
                        "thread_id": thread_id,
                    },
                ),
            ]
        except TimeoutError:
            logger.warning(
                "retrieval_kernel.working_memory.timeout",
                agent_id=agent_id,
                timeout=self._wm_timeout,
            )
            return []
        except Exception as exc:
            logger.warning(
                "retrieval_kernel.working_memory.error",
                agent_id=agent_id,
                error=str(exc),
            )
            return []

    async def _retrieve_semantic(
        self,
        *,
        query: str,
        agent_id: str,
        top_k: int,
    ) -> list[RetrievalHit]:
        """Tier 2: Semantic search (Postgres/pgvector)."""
        try:
            results = await asyncio.wait_for(
                self._semantic.search_packets(  # type: ignore[union-attr]
                    query=query,
                    top_k=top_k,
                ),
                timeout=self._semantic_timeout,
            )
            hits: list[RetrievalHit] = []
            for result in results:
                content = ""
                score = 0.0
                meta: dict[str, Any] = {}

                if hasattr(result, "payload"):
                    content = str(result.payload)
                elif isinstance(result, dict):
                    content = str(result.get("payload", result))
                else:
                    content = str(result)

                if hasattr(result, "score"):
                    score = float(result.score)
                elif isinstance(result, dict) and "score" in result:
                    score = float(result["score"])

                if hasattr(result, "metadata"):
                    meta = dict(result.metadata) if result.metadata else {}
                elif isinstance(result, dict) and "metadata" in result:
                    meta = dict(result["metadata"])

                hits.append(
                    RetrievalHit(
                        source_tier="semantic",
                        content=content[:2000],
                        score=score,
                        metadata=meta,
                    )
                )
            return hits
        except TimeoutError:
            logger.warning(
                "retrieval_kernel.semantic.timeout",
                agent_id=agent_id,
                timeout=self._semantic_timeout,
            )
            return []
        except Exception as exc:
            logger.warning(
                "retrieval_kernel.semantic.error",
                agent_id=agent_id,
                error=str(exc),
            )
            return []

    async def _retrieve_graph(
        self,
        *,
        thread_id: str,
        top_k: int,
    ) -> list[RetrievalHit]:
        """Tier 3: Graph context (Neo4j)."""
        try:
            results = await asyncio.wait_for(
                self._graph.query_history(  # type: ignore[union-attr]
                    session_id=thread_id,
                    limit=top_k,
                ),
                timeout=self._graph_timeout,
            )
            hits: list[RetrievalHit] = []
            for result in results:
                content = ""
                if hasattr(result, "content"):
                    content = str(result.content)
                elif isinstance(result, dict):
                    content = str(result.get("content", result))
                else:
                    content = str(result)

                hits.append(
                    RetrievalHit(
                        source_tier="graph",
                        content=content[:2000],
                        score=0.8,
                        metadata={"thread_id": thread_id},
                    )
                )
            return hits
        except TimeoutError:
            logger.warning(
                "retrieval_kernel.graph.timeout",
                thread_id=thread_id,
                timeout=self._graph_timeout,
            )
            return []
        except Exception as exc:
            logger.warning(
                "retrieval_kernel.graph.error",
                thread_id=thread_id,
                error=str(exc),
            )
            return []


# =============================================================================
# Sorted public API
# =============================================================================

__all__ = [
    "GraphContextBackend",
    "L9RetrievalKernel",
    "RetrievalHit",
    "SemanticSearchBackend",
    "WorkingMemoryBackend",
]
