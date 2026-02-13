"""World-model aware working memory adapter.

Bridges MemorySubstrateService (world model, semantic memory, packets)
with the Redis-backed WorkingMemoryService (ephemeral, repo-scoped state).

This adapter does NOT own persistence. It:
- reads packets / semantic memory via MemorySubstrateService
- enriches / summarizes world-model context for a given agent+repo+branch
- delegates ephemeral state to WorkingMemoryService (via call sites)

Scope: helper utilities only; no side effects beyond substrate queries.
"""

from __future__ import annotations

from collections.abc import Iterable
from datetime import UTC, datetime, timedelta, timezone
from typing import Any

import structlog

from core.decorators import must_stay_async
from core.schemas import SemanticSearchRequest
from memory.substrate_service import MemorySubstrateService

logger = structlog.get_logger(__name__)


class WorkingMemoryAdapter:
    """World-model aware helper for agent working memory.

    This is a thin, non-invasive adapter that lets agents hydrate their
    repo-scoped working memory with context from the substrate world model
    and semantic memory, without changing core substrate semantics.

    Responsibilities:
    - Build world-model informed context snapshots per (agent_id, repo_id, branch)
    - Query recent packets (insights, reflections, execution plans) for that agent
    - Run targeted semantic search scoped by agent and repo

    It deliberately does NOT:
    - write packets
    - mutate world model
    - touch Redis directly (that remains the job of WorkingMemoryService)
    """

    def __init__(self, substrate: MemorySubstrateService) -> None:
        self._substrate = substrate

    # ---------------------------------------------------------------------
    # High-level API
    # ---------------------------------------------------------------------

    @must_stay_async("callers use await")
    async def build_world_model_context(
        self,
        *,
        agent_id: str,
        repo_id: str,
        branch: str,
        max_packets: int = 50,
        lookback_minutes: int = 60,
    ) -> dict[str, Any]:
        """Assemble a world-model aware context snapshot for working memory.

        This is intended to be called by higher-level agent kernels before
        hydrating or updating WorkingMemoryService.

        It pulls:
        - recent substrate packets for this agent (insight, reflection, execution_plan)
        - a lightweight semantic summary over those packets' content

        Returns a pure-JSON payload that call sites can merge into
        `WorkingMemorySnapshot.recent_decisions`, `open_hypotheses`, etc.
        """

        since = datetime.now(UTC) - timedelta(minutes=lookback_minutes)

        packets_result = await self._substrate.query_packets(
            packet_types=["insight", "reflection", "execution_plan"],
            limit=max_packets,
            since=since,
            agent_id=agent_id,
        )

        packets: list[dict[str, Any]] = packets_result.get("packets", [])

        logger.debug(
            "working_memory_adapter.world_model_context.packets",
            agent_id=agent_id,
            repo_id=repo_id,
            branch=branch,
            packet_count=len(packets),
        )

        # Extract short summaries from packets if available
        summaries: list[str] = []
        hypotheses: list[str] = []

        for p in packets:
            meta = p.get("metadata", {}) or {}
            summary = meta.get("summary") or p.get("summary")
            if summary:
                summaries.append(str(summary))

            # Treat explicit_hypotheses / hypotheses fields as candidate signals
            for key in ("explicit_hypotheses", "hypotheses"):
                value = meta.get(key) or p.get(key)
                if isinstance(value, str):
                    hypotheses.append(value)
                elif isinstance(value, Iterable):
                    hypotheses.extend(str(v) for v in value)

        world_model_context = {
            "agent_id": agent_id,
            "repo_id": repo_id,
            "branch": branch,
            "packet_count": len(packets),
            "summaries": summaries,
            "hypotheses": hypotheses,
            "since": since.isoformat(),
            "generated_at": datetime.now(UTC).isoformat(),
        }

        return world_model_context

    @must_stay_async("callers use await")
    async def semantic_recall_for_intent(
        self,
        *,
        agent_id: str,
        query: str,
        top_k: int = 8,
        min_score: float = 0.5,
    ) -> list[dict[str, Any]]:
        """Run agent-scoped semantic search to support working memory updates.

        This lets AGENT_WORKING_MEMORY pull back semantically relevant
        memories tied to the current intent, without embedding directly.
        """

        request = SemanticSearchRequest(
            query=query,
            top_k=top_k,
            min_score=min_score,
            agent_id=agent_id,
        )

        result = await self._substrate.semantic_search(request)

        logger.debug(
            "working_memory_adapter.semantic_recall",
            agent_id=agent_id,
            query=query[:80],
            hit_count=len(result.hits),
        )

        # Normalize hits into plain dicts for WorkingMemoryService call sites
        recalled: list[dict[str, Any]] = []
        for h in result.hits:
            payload = dict(h.payload or {})
            payload["embedding_id"] = h.embedding_id
            payload["score"] = h.score
            recalled.append(payload)

        return recalled
