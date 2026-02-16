"""
L9 Memory Substrate - Retrieval Pipeline
Version: 1.3.0

Hybrid and structured search features:
- Semantic search (vector similarity)
- Hybrid search (semantic + structured filters)
- Reciprocal rank fusion (multi-source ranking)
- Cross-encoder neural re-ranking (Stage 3 complete)
- Temporal decay (recency weighting)
- Thread reconstruction
- Lineage traversal
- Fact/insight retrieval
- Replay chain reconstruction

All operations are async-safe with proper logging.

Changelog:
- v1.3.0: Added cross-encoder re-ranking for improved retrieval quality
- v1.2.0: Added reciprocal_rank_fusion, apply_temporal_decay
- v1.1.0: Initial hybrid search
"""

from __future__ import annotations

from core.decorators import must_stay_async
from core.singleton_auto_registry import register_singleton

# ============================================================================
__dora_meta__ = {
    "component_name": "Retrieval Pipeline",
    "module_version": "1.3.0",
    "created_by": "Igor Beylin",
    "created_at": "2025-12-09T01:02:49Z",
    "updated_at": "2026-01-17T23:47:56Z",
    "layer": "learning",
    "domain": "memory_substrate",
    "module_name": "retrieval",
    "type": "service",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": ["PostgreSQL"],
        "memory_layers": ["semantic_memory", "working_memory"],
        "imported_by": [
            "api.memory.router",
            "core.agents.adaptive_prompting",
            "core.singleton_registry",
            "memory.__init__",
            "tests.memory.test_e2e_memory_audit",
            "tests.memory.test_retrieval_audit",
        ],
    },
}
# ============================================================================

import math
from datetime import UTC, datetime
from functools import lru_cache
from typing import TYPE_CHECKING, Any
from uuid import UUID

import structlog

if TYPE_CHECKING:
    from memory.substrate_repository import SubstrateRepository
    from memory.substrate_semantic import SemanticService

import contextlib

from core.schemas import SemanticHit, SemanticSearchResult
from memory.cross_encoder_reranker import (
    get_cross_encoder_reranker,
    is_cross_encoder_available,
)
from memory.governance_gate import (
    build_scope_project_filter,
    require_governance_context,
)
from memory.substrate_models import KnowledgeFactRow, PacketStoreRow

logger = structlog.get_logger(__name__)


# =============================================================================
# Ranking Utilities
# =============================================================================


def reciprocal_rank_fusion(
    rankings: list[list[str]],
    k: int = 60,
) -> dict[str, float]:
    """
    Combine multiple rankings using Reciprocal Rank Fusion (RRF).

    RRF is effective for combining results from different retrieval systems
    (e.g., semantic search + keyword search + graph traversal).

    Formula: RRF(d) = Σ 1 / (k + rank(d))

    Args:
        rankings: List of rankings, each is a list of item IDs in ranked order
        k: Constant to prevent high ranks from dominating (default 60)

    Returns:
        Dict mapping item IDs to their fused scores (higher = better)

    Example:
        >>> rankings = [["a", "b", "c"], ["b", "c", "a"]]
        >>> scores = reciprocal_rank_fusion(rankings, k=60)
        >>> # "b" ranks 2nd and 1st, so scores highest
    """
    scores: dict[str, float] = {}

    for ranking in rankings:
        for rank, item_id in enumerate(ranking, start=1):
            if item_id not in scores:
                scores[item_id] = 0.0
            scores[item_id] += 1.0 / (k + rank)

    return scores


def apply_temporal_decay(
    score: float,
    timestamp: datetime,
    half_life_days: float = 30.0,
    reference_time: datetime | None = None,
) -> float:
    """
    Apply exponential temporal decay to a score based on age.

    Newer items get higher scores, with exponential decay based on
    half-life. Useful for recency-weighted retrieval.

    Formula: decayed_score = score * 2^(-age_days / half_life_days)

    Args:
        score: Original score to decay
        timestamp: Timestamp of the item
        half_life_days: Days until score is halved (default 30)
        reference_time: Reference time for age calculation (default: now)

    Returns:
        Decayed score value

    Example:
        >>> now = datetime.now(timezone.utc)
        >>> recent_score = apply_temporal_decay(1.0, now, half_life_days=30)
        >>> # recent_score ≈ 1.0
        >>> old = now - timedelta(days=30)
        >>> old_score = apply_temporal_decay(1.0, old, half_life_days=30)
        >>> # old_score ≈ 0.5
    """
    if reference_time is None:
        reference_time = datetime.now(UTC)

    age_days = (reference_time - timestamp).total_seconds() / 86400.0

    if age_days < 0:
        # Future timestamp - no decay
        return score

    decay_factor = math.pow(2, -age_days / half_life_days)
    return score * decay_factor


class RetrievalPipeline:
    """
    Memory retrieval pipeline with hybrid search capabilities.

    Supports:
    - Pure semantic search (vector similarity)
    - Hybrid search (semantic + metadata filters)
    - Thread reconstruction
    - Lineage graph traversal
    - Knowledge fact queries
    """

    def __init__(
        self,
        repository=None,
        semantic_service=None,
    ):
        """
        Initialize retrieval pipeline.

        Args:
            repository: SubstrateRepository instance
            semantic_service: SemanticService for embedding queries
        """
        self._repository = repository
        self._semantic_service = semantic_service
        logger.info("RetrievalPipeline initialized")

    def set_repository(self, repository: SubstrateRepository) -> None:
        """Set or update the repository reference."""
        self._repository = repository

    def set_semantic_service(self, service: SemanticService) -> None:
        """Set or update the semantic service reference."""
        self._semantic_service = service

    # =========================================================================
    # Semantic Search
    # =========================================================================

    @must_stay_async("callers use await")
    async def semantic_search(
        self,
        query: str,
        top_k: int = 10,
        agent_id: str | None = None,
        tags: list[str] | None = None,
        tag_boost_factor: float = 1.15,
    ) -> SemanticSearchResult:
        """
        Perform semantic search using vector similarity.

        When tags are provided, results are filtered to memories with at least
        one matching tag and scores are boosted for tag matches (increased accuracy).

        Args:
            query: Natural language search query
            top_k: Number of results to return
            agent_id: Optional agent filter
            tags: Optional list of tags to filter and boost by (uses packet_store + payload tags)
            tag_boost_factor: Score multiplier when hit tags match (default 1.15)

        Returns:
            SemanticSearchResult with hits
        """
        logger.debug(f"Semantic search: query='{query[:50]}...', top_k={top_k}")

        if self._semantic_service is None:
            logger.warning("Semantic service not configured")
            return SemanticSearchResult(query=query, hits=[])

        tags_include = tags
        tags_boost = tags

        hits = await self._semantic_service.search(
            query=query,
            top_k=top_k,
            agent_id=agent_id,
            tags_include=tags_include,
            tags_boost=tags_boost,
            tag_boost_factor=tag_boost_factor,
        )

        return SemanticSearchResult(
            query=query,
            hits=[
                SemanticHit(
                    embedding_id=h.get("embedding_id") or h.embedding_id,
                    score=h.get("score") or h.score,
                    payload=h.get("payload") or h.payload,
                )
                for h in hits
            ],
        )

    # =========================================================================
    # Keyword Search (Full-Text Search)
    # =========================================================================

    @must_stay_async("callers use await")
    async def keyword_search(
        self,
        query: str,
        top_k: int = 10,
        packet_type: str | None = None,
    ) -> list[dict[str, Any]]:
        """
        Perform full-text search using PostgreSQL FTS (to_tsvector/plainto_tsquery).

        Searches the envelope JSONB payload for keyword matches.
        Uses ts_rank for relevance scoring.

        Args:
            query: Natural language search query
            top_k: Number of results to return
            packet_type: Optional filter by packet type

        Returns:
            List of dicts with packet_id, score, and content
        """
        logger.debug(f"Keyword search: query='{query[:50]}...', top_k={top_k}")

        if self._repository is None:
            logger.warning("Repository not configured for keyword search")
            return []

        # GMP-70: Governance scope filtering
        ctx = require_governance_context("retrieval.keyword_search")
        filter_clause, filter_params, next_idx = build_scope_project_filter(
            ctx, param_idx=3, table_alias="packet_store"
        )

        try:
            async with self._repository.acquire() as conn:
                # Build base query with FTS
                # Search in envelope payload text content
                base_query = """
                    SELECT
                        packet_id,
                        packet_type,
                        timestamp,
                        ts_rank(
                            to_tsvector('english', COALESCE(
                                envelope->'payload'->>'text',
                                envelope->'payload'->>'content',
                                envelope->'payload'->>'description',
                                envelope->'payload'->>'message',
                                envelope->'payload'->>'summary',
                                ''
                            )),
                            plainto_tsquery('english', $1)
                        ) as rank,
                        envelope
                    FROM packet_store
                    WHERE to_tsvector('english', COALESCE(
                        envelope->'payload'->>'text',
                        envelope->'payload'->>'content',
                        envelope->'payload'->>'description',
                        envelope->'payload'->>'message',
                        envelope->'payload'->>'summary',
                        ''
                    )) @@ plainto_tsquery('english', $1)
                """

                # Add packet_type filter if specified
                if packet_type:
                    base_query += f" AND packet_type = ${next_idx}"
                    filter_params = [*list(filter_params), packet_type]
                    next_idx += 1

                # Add governance scope filter
                base_query += f" {filter_clause}"

                # Order and limit
                base_query += " ORDER BY rank DESC LIMIT $2"

                rows = await conn.fetch(base_query, query, top_k, *filter_params)

                results = [
                    {
                        "packet_id": str(r["packet_id"]),
                        "packet_type": r["packet_type"],
                        "score": float(r["rank"]) if r["rank"] else 0.0,
                        "timestamp": (
                            r["timestamp"].isoformat() if r["timestamp"] else None
                        ),
                        "payload": (
                            r["envelope"].get("payload", {}) if r["envelope"] else {}
                        ),
                    }
                    for r in rows
                ]

                logger.debug(f"Keyword search returned {len(results)} results")
                return results

        except Exception as e:
            logger.error(f"Keyword search failed: {e}", exc_info=True)
            return []

    # =========================================================================
    # Hybrid Search
    # =========================================================================

    @must_stay_async("callers use await")
    async def hybrid_search(
        self,
        query: str,
        top_k: int = 10,
        filters: dict[str, Any] | None = None,
        agent_id: str | None = None,
        min_score: float = 0.5,
        rrf_k: int = 60,
        temporal_half_life_days: float = 30.0,
        use_cross_encoder: bool = True,
    ) -> dict[str, Any]:
        """
        Perform hybrid search combining semantic and structured filters.

        Uses Reciprocal Rank Fusion (RRF) to combine rankings from semantic
        search and structured filtering, with optional temporal decay to
        prefer more recent results.

        Stage 3 Complete: Now includes optional cross-encoder neural re-ranking
        for improved retrieval quality.

        Args:
            query: Natural language search query
            top_k: Number of results to return
            filters: Structured filters (packet_type, tags, date_range, etc.)
            agent_id: Optional agent filter
            min_score: Minimum similarity score threshold
            rrf_k: RRF constant (higher = less weight to top ranks, default 60)
            temporal_half_life_days: Days until score halves due to age (default 30)
            use_cross_encoder: Whether to apply cross-encoder re-ranking (default True)

        Returns:
            Dict with semantic_hits, filtered_packets, and combined results
        """
        logger.debug(f"Hybrid search: query='{query[:50]}...', filters={filters}")

        filters = filters or {}

        # Step 1: Parallel retrieval - Semantic + Keyword search
        import asyncio

        tag_list: list[str] | None = None
        if filters.get("tags"):
            t = filters["tags"]
            tag_list = t if isinstance(t, list) else [t]
        semantic_task = self.semantic_search(
            query=query,
            top_k=top_k * 2,  # Get more to allow filtering
            agent_id=agent_id,
            tags=tag_list,
        )
        keyword_task = self.keyword_search(
            query=query,
            top_k=top_k * 2,
            packet_type=filters.get("packet_type"),
        )

        semantic_result, keyword_results = await asyncio.gather(
            semantic_task, keyword_task
        )

        # Filter semantic by score
        semantic_hits = [h for h in semantic_result.hits if h.score >= min_score]

        # Step 2: Get packet IDs from semantic results
        packet_ids = []
        for hit in semantic_hits:
            packet_id = hit.payload.get("packet_id")
            if packet_id:
                with contextlib.suppress(ValueError, TypeError):
                    packet_ids.append(UUID(packet_id))

        # Add keyword result packet IDs
        for kw_hit in keyword_results:
            packet_id = kw_hit.get("packet_id")
            if packet_id:
                try:
                    pid = UUID(packet_id)
                    if pid not in packet_ids:
                        packet_ids.append(pid)
                except (ValueError, TypeError):
                    pass

        # Step 3: Apply structured filters (batch fetch replaces N+1 loop)
        filtered_packets = []

        if packet_ids and self._repository:
            batch_ids = packet_ids[: top_k * 2]
            if hasattr(self._repository, "get_packets_batch"):
                # Single query for all packets (O(1) round-trips)
                packets_map = await self._repository.get_packets_batch(batch_ids)
                for pid in batch_ids:
                    packet = packets_map.get(pid)
                    if packet and self._matches_filters(packet, filters):
                        filtered_packets.append(packet)
            else:
                # Fallback: legacy N+1 path (remove once get_packets_batch deployed)
                for pid in batch_ids:
                    packet = await self._repository.get_packet(pid)
                    if packet and self._matches_filters(packet, filters):
                        filtered_packets.append(packet)

        # Step 4: Combine and rank with 3-way RRF + temporal decay
        # Build rankings for RRF: semantic, keyword, and filter-match
        semantic_ranking = [
            hit.payload.get("packet_id")
            for hit in semantic_hits
            if hit.payload.get("packet_id")
        ]
        keyword_ranking = [
            kw_hit.get("packet_id")
            for kw_hit in keyword_results
            if kw_hit.get("packet_id")
        ]
        filter_ranking = [str(p.packet_id) for p in filtered_packets]

        # Compute RRF scores across all three rankings (3-way fusion)
        rrf_scores = reciprocal_rank_fusion(
            [semantic_ranking, keyword_ranking, filter_ranking],
            k=rrf_k,
        )

        combined = []
        seen_packet_ids = set()

        # Add semantic hits with RRF scores
        for hit in semantic_hits:
            packet_id = hit.payload.get("packet_id")
            if not packet_id or packet_id in seen_packet_ids:
                continue
            seen_packet_ids.add(packet_id)

            matching_packet = next(
                (p for p in filtered_packets if str(p.packet_id) == packet_id), None
            )

            # Use RRF score if available, else fall back to semantic score
            base_score = rrf_scores.get(packet_id, hit.score)

            # Apply temporal decay if we have a timestamp
            if matching_packet and matching_packet.timestamp:
                final_score = apply_temporal_decay(
                    base_score,
                    matching_packet.timestamp,
                    half_life_days=temporal_half_life_days,
                )
            else:
                final_score = base_score

            combined.append(
                {
                    "score": final_score,
                    "rrf_score": rrf_scores.get(packet_id),
                    "semantic_score": hit.score,
                    "keyword_score": None,
                    "embedding_id": str(hit.embedding_id),
                    "packet_id": packet_id,
                    "payload": hit.payload,
                    "packet": (
                        matching_packet.model_dump(mode="json")
                        if matching_packet
                        else None
                    ),
                    "source": "semantic",
                }
            )

        # Add keyword-only results (not in semantic hits)
        for kw_hit in keyword_results:
            packet_id = kw_hit.get("packet_id")
            if not packet_id or packet_id in seen_packet_ids:
                continue
            seen_packet_ids.add(packet_id)

            matching_packet = next(
                (p for p in filtered_packets if str(p.packet_id) == packet_id), None
            )

            # Use RRF score for keyword-only results
            base_score = rrf_scores.get(packet_id, kw_hit.get("score", 0.0))

            # Apply temporal decay if we have a timestamp
            if matching_packet and matching_packet.timestamp:
                final_score = apply_temporal_decay(
                    base_score,
                    matching_packet.timestamp,
                    half_life_days=temporal_half_life_days,
                )
            else:
                final_score = base_score

            combined.append(
                {
                    "score": final_score,
                    "rrf_score": rrf_scores.get(packet_id),
                    "semantic_score": None,
                    "keyword_score": kw_hit.get("score"),
                    "embedding_id": None,
                    "packet_id": packet_id,
                    "payload": kw_hit.get("payload", {}),
                    "packet": (
                        matching_packet.model_dump(mode="json")
                        if matching_packet
                        else None
                    ),
                    "source": "keyword",
                }
            )

        # Sort by final score and limit
        combined.sort(key=lambda x: x["score"], reverse=True)
        combined = combined[:top_k]

        # Step 5: Optional cross-encoder re-ranking (Stage 3 completion)
        cross_encoder_used = False
        cross_encoder_time_ms = 0.0

        if use_cross_encoder and combined and is_cross_encoder_available():
            try:
                reranker = get_cross_encoder_reranker()
                rerank_result = reranker.rerank(
                    query=query,
                    candidates=combined,
                    top_k=top_k,
                    text_key="payload",
                    fallback_text_keys=["content", "fact_text", "observation"],
                )

                if rerank_result.reranker_used:
                    combined = rerank_result.results
                    cross_encoder_used = True
                    cross_encoder_time_ms = rerank_result.reranking_time_ms
                    logger.debug(
                        "Cross-encoder re-ranking applied",
                        candidates=rerank_result.candidates_reranked,
                        time_ms=cross_encoder_time_ms,
                    )

            except Exception as e:
                logger.warning(
                    f"Cross-encoder re-ranking failed, using RRF results: {e}"
                )

        return {
            "query": query,
            "filters": filters,
            "semantic_hits": len(semantic_hits),
            "keyword_hits": len(keyword_results),
            "filtered_count": len(filtered_packets),
            "fusion_type": (
                "4-way_rrf_cross_encoder" if cross_encoder_used else "3-way_rrf"
            ),
            "cross_encoder_used": cross_encoder_used,
            "cross_encoder_time_ms": cross_encoder_time_ms,
            "results": combined,
        }

    def _matches_filters(self, packet: PacketStoreRow, filters: dict[str, Any]) -> bool:
        """Check if packet matches structured filters."""
        # Filter by packet_type
        if "packet_type" in filters:
            if packet.packet_type != filters["packet_type"]:
                return False

        # Filter by tags
        if "tags" in filters:
            required_tags = filters["tags"]
            if isinstance(required_tags, str):
                required_tags = [required_tags]
            if not any(tag in packet.tags for tag in required_tags):
                return False

        # Filter by date range
        if "after" in filters:
            after = filters["after"]
            if isinstance(after, str):
                after = datetime.fromisoformat(after)
            if packet.timestamp < after:
                return False

        if "before" in filters:
            before = filters["before"]
            if isinstance(before, str):
                before = datetime.fromisoformat(before)
            if packet.timestamp > before:
                return False

        return True

    # =========================================================================
    # Thread Reconstruction
    # =========================================================================

    @must_stay_async("callers use await")
    async def fetch_thread(
        self,
        thread_id: UUID,
        limit: int = 100,
        order: str = "asc",
    ) -> list[dict[str, Any]]:
        """
        Reconstruct a conversation thread.

        Fetches all packets belonging to a thread in chronological order.

        Args:
            thread_id: Thread UUID
            limit: Maximum packets to return
            order: "asc" (oldest first) or "desc" (newest first)

        Returns:
            List of packets in thread order
        """
        logger.debug(f"Fetching thread: {thread_id}")

        if self._repository is None:
            return []

        # GMP-70: Governance scope filtering
        ctx = require_governance_context("retrieval.fetch_thread")
        filter_clause, filter_params, _ = build_scope_project_filter(
            ctx, param_idx=3, table_alias="packet_store"
        )

        async with self._repository.acquire() as conn:
            order_clause = "ASC" if order == "asc" else "DESC"

            rows = await conn.fetch(
                f"""
                SELECT * FROM packet_store
                WHERE thread_id = $1
                {filter_clause}
                ORDER BY timestamp {order_clause}
                LIMIT $2
                """,  # noqa: S608, ADR-0087 — internal SQL clauses, user values parameterized
                thread_id,
                limit,
                *filter_params,
            )

            return [
                {
                    "packet_id": str(r["packet_id"]),
                    "packet_type": r["packet_type"],
                    "timestamp": r["timestamp"].isoformat() if r["timestamp"] else None,
                    "envelope": r["envelope"],
                    "tags": r.get("tags", []),
                }
                for r in rows
            ]

    # =========================================================================
    # Lineage Traversal
    # =========================================================================

    @must_stay_async("callers use await")
    async def fetch_lineage(
        self,
        packet_id: UUID,
        direction: str = "ancestors",
        max_depth: int = 10,
    ) -> dict[str, Any]:
        """
        Traverse packet lineage graph.

        Args:
            packet_id: Starting packet UUID
            direction: "ancestors" (parents) or "descendants" (children)
            max_depth: Maximum traversal depth

        Returns:
            Dict with lineage chain and graph structure
        """
        logger.debug(f"Fetching lineage: {packet_id}, direction={direction}")

        if self._repository is None:
            return {"packet_id": str(packet_id), "chain": [], "depth": 0}

        # GMP-70: Governance scope filtering
        ctx = require_governance_context("retrieval.fetch_lineage")
        filter_clause, filter_params, _ = build_scope_project_filter(
            ctx, param_idx=2, table_alias="packet_store"
        )

        chain = []
        visited = set()
        queue = [(packet_id, 0)]

        while queue and len(chain) < 100:
            current_id, depth = queue.pop(0)

            if depth > max_depth or current_id in visited:
                continue

            visited.add(current_id)

            packet = await self._repository.get_packet(current_id)
            if packet is None:
                continue

            chain.append(
                {
                    "packet_id": str(current_id),
                    "packet_type": packet.packet_type,
                    "timestamp": (
                        packet.timestamp.isoformat() if packet.timestamp else None
                    ),
                    "depth": depth,
                }
            )

            if direction == "ancestors":
                # Traverse up to parents
                parent_ids = packet.parent_ids or []
                for pid in parent_ids:
                    queue.append((pid, depth + 1))
            else:
                # Traverse down to children (with scope filter)
                async with self._repository.acquire() as conn:
                    rows = await conn.fetch(
                        f"""
                        SELECT packet_id FROM packet_store
                        WHERE $1 = ANY(parent_ids)
                        {filter_clause}
                        """,  # noqa: S608, ADR-0087 — filter_clause is internal SQL
                        current_id,
                        *filter_params,
                    )
                    for r in rows:
                        queue.append((r["packet_id"], depth + 1))

        return {
            "packet_id": str(packet_id),
            "direction": direction,
            "chain": chain,
            "depth": max(c["depth"] for c in chain) if chain else 0,
        }

    # =========================================================================
    # Knowledge Facts & Insights
    # =========================================================================

    @must_stay_async("callers use await")
    async def fetch_facts(
        self,
        subject: str | None = None,
        predicate: str | None = None,
        source_packet: UUID | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """
        Fetch knowledge facts from the substrate.

        Args:
            subject: Filter by subject
            predicate: Filter by predicate
            source_packet: Filter by source packet
            limit: Maximum facts to return

        Returns:
            List of knowledge facts
        """
        logger.debug(f"Fetching facts: subject={subject}, predicate={predicate}")

        if self._repository is None:
            return []

        # GMP-70: Governance scope filtering
        ctx = require_governance_context("retrieval.fetch_facts")
        filter_clause, filter_params, _ = build_scope_project_filter(
            ctx, param_idx=2, table_alias="packet_store"
        )

        if source_packet:
            facts = await self._repository.get_facts_by_packet(source_packet, limit)
        elif subject:
            facts = await self._repository.get_facts_by_subject(
                subject, predicate, limit
            )
        else:
            # Fetch recent facts (with scope filter via JOIN)
            async with self._repository.acquire() as conn:
                rows = await conn.fetch(
                    f"""
                    SELECT knowledge_facts.*
                    FROM knowledge_facts
                    INNER JOIN packet_store ON packet_store.packet_id = knowledge_facts.source_packet
                    WHERE TRUE {filter_clause}
                    ORDER BY knowledge_facts.created_at DESC
                    LIMIT $1
                    """,  # noqa: S608, ADR-0087 — filter_clause is internal SQL
                    limit,
                    *filter_params,
                )
                facts = [
                    KnowledgeFactRow(
                        fact_id=r["fact_id"],
                        subject=r["subject"],
                        predicate=r["predicate"],
                        object=r["object"],
                        confidence=r["confidence"],
                        source_packet=r["source_packet"],
                        created_at=r["created_at"],
                    )
                    for r in rows
                ]

        return [f.model_dump(mode="json") for f in facts]

    @must_stay_async("callers use await")
    async def fetch_insights(
        self,
        packet_id: UUID | None = None,
        insight_type: str | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """
        Fetch extracted insights from the substrate.

        Args:
            packet_id: Filter by source packet
            insight_type: Filter by insight type
            limit: Maximum insights to return

        Returns:
            List of insights (stored as insight-type packets)
        """
        logger.debug(f"Fetching insights: packet_id={packet_id}, type={insight_type}")

        if self._repository is None:
            return []

        # GMP-70: Governance scope filtering
        ctx = require_governance_context("retrieval.fetch_insights")
        filter_clause, filter_params, _ = build_scope_project_filter(
            ctx, param_idx=3, table_alias="packet_store"
        )

        async with self._repository.acquire() as conn:
            if packet_id:
                rows = await conn.fetch(
                    f"""
                    SELECT * FROM packet_store
                    WHERE packet_type = 'insight'
                    AND envelope->>'source_packet' = $1
                    {filter_clause}
                    ORDER BY timestamp DESC
                    LIMIT $2
                    """,  # noqa: S608, ADR-0087 — filter_clause is internal SQL
                    str(packet_id),
                    limit,
                    *filter_params,
                )
            elif insight_type:
                rows = await conn.fetch(
                    f"""
                    SELECT * FROM packet_store
                    WHERE packet_type = 'insight'
                    AND envelope->'payload'->>'insight_type' = $1
                    {filter_clause}
                    ORDER BY timestamp DESC
                    LIMIT $2
                    """,  # noqa: S608, ADR-0087 — filter_clause is internal SQL
                    insight_type,
                    limit,
                    *filter_params,
                )
            else:
                filter_clause_2, filter_params_2, _ = build_scope_project_filter(
                    ctx, param_idx=2, table_alias="packet_store"
                )
                rows = await conn.fetch(
                    f"""
                    SELECT * FROM packet_store
                    WHERE packet_type = 'insight'
                    {filter_clause_2}
                    ORDER BY timestamp DESC
                    LIMIT $1
                    """,  # noqa: S608, ADR-0087 — filter_clause is internal SQL
                    limit,
                    *filter_params_2,
                )

        return [
            {
                "packet_id": str(r["packet_id"]),
                "timestamp": r["timestamp"].isoformat() if r["timestamp"] else None,
                "envelope": r["envelope"],
            }
            for r in rows
        ]

    # =========================================================================
    # Replay Chain
    # =========================================================================

    @must_stay_async("callers use await")
    async def replay_chain(
        self,
        start_packet_id: UUID,
        end_packet_id: UUID | None = None,
        include_reasoning: bool = True,
    ) -> dict[str, Any]:
        """
        Reconstruct the event/action chain between two packets.

        Useful for debugging and understanding agent decision paths.

        Args:
            start_packet_id: Starting packet
            end_packet_id: Optional ending packet
            include_reasoning: Include reasoning traces

        Returns:
            Dict with chain of events and reasoning
        """
        logger.debug(f"Replaying chain: {start_packet_id} -> {end_packet_id}")

        if self._repository is None:
            return {"start": str(start_packet_id), "chain": []}

        # Get lineage from start
        lineage = await self.fetch_lineage(start_packet_id, "descendants", max_depth=50)

        # Batch-fetch all packets in the lineage chain (replaces N+1 loop)
        lineage_items = lineage.get("chain", [])
        all_pids = []
        for item in lineage_items:
            try:
                all_pids.append(UUID(item["packet_id"]))
            except (ValueError, TypeError):
                pass
            if end_packet_id and item.get("packet_id") == str(end_packet_id):
                break

        packets_map: dict = {}
        if all_pids and hasattr(self._repository, "get_packets_batch"):
            packets_map = await self._repository.get_packets_batch(all_pids)

        chain = []
        for item in lineage_items:
            packet_id = UUID(item["packet_id"])
            packet = packets_map.get(packet_id)
            if packet is None and not packets_map:
                # Fallback: individual fetch if batch not available
                packet = await self._repository.get_packet(packet_id)

            entry = {
                "packet_id": item["packet_id"],
                "packet_type": item["packet_type"],
                "timestamp": item["timestamp"],
                "payload": packet.envelope.get("payload") if packet else None,
            }

            # Add reasoning if requested
            if include_reasoning:
                traces = await self._repository.get_reasoning_traces(
                    packet_id=packet_id, limit=1
                )
                if traces:
                    entry["reasoning"] = traces[0].model_dump(mode="json")

            chain.append(entry)

            # Stop if we reached end packet
            if end_packet_id and packet_id == end_packet_id:
                break

        return {
            "start": str(start_packet_id),
            "end": str(end_packet_id) if end_packet_id else None,
            "chain": chain,
            "length": len(chain),
        }

    # =========================================================================
    # Tier-Aware Retrieval (GMP-80-A5: Identity Tier)
    # =========================================================================

    @must_stay_async("callers use await")
    async def get_identity_context(
        self,
        max_facts: int = 20,
        format_type: str = "markdown",
    ) -> str:
        """
        Get identity tier facts for context injection.

        Identity facts are permanent, high-importance core knowledge
        that defines the agent's identity, values, and goals.

        Args:
            max_facts: Maximum identity facts to include
            format_type: Output format ("markdown", "json", "text")

        Returns:
            Formatted string with identity facts
        """
        logger.debug(f"Getting identity context: max_facts={max_facts}")

        if self._repository is None:
            return ""

        # Get identity tier facts (highest importance first)
        facts = await self._repository.get_semantic_facts_by_tier(
            tier="identity",
            limit=max_facts,
        )

        if not facts:
            return ""

        # Format based on type
        if format_type == "json":
            import json

            return json.dumps(
                [
                    {
                        "fact": f.fact_text,
                        "importance": f.importance,
                        "tags": f.tags,
                    }
                    for f in facts
                ],
                indent=2,
            )

        if format_type == "text":
            return "\n".join([f"- {f.fact_text}" for f in facts])

        # markdown (default)
        lines = ["## Identity Core Facts\n"]
        for f in facts:
            lines.append(f"- {f.fact_text}")
        return "\n".join(lines)

    @must_stay_async("callers use await")
    async def hierarchical_search(
        self,
        query: str,
        tiers: list[str] | None = None,
        max_per_tier: int = 5,
        min_score: float = 0.5,
    ) -> dict[str, Any]:
        """
        Search across memory tiers with precedence.

        Searches facts in tier order (identity > project > session > general)
        and returns results grouped by tier.

        Args:
            query: Search query
            tiers: Optional list of tiers to search (default: all)
            max_per_tier: Maximum results per tier
            min_score: Minimum relevance score

        Returns:
            Dict with results grouped by tier
        """
        logger.debug(f"Hierarchical search: query='{query[:50]}...', tiers={tiers}")

        if self._repository is None:
            return {"results": {}, "total": 0}

        # Default to all tiers in precedence order
        tier_order = tiers or ["identity", "project", "session", "general"]

        results: dict[str, list[dict[str, Any]]] = {}
        total = 0

        for tier in tier_order:
            # Get facts from this tier
            tier_facts = await self._repository.get_semantic_facts_by_tier(
                tier=tier,
                limit=max_per_tier * 2,  # Get more to filter
            )

            if not tier_facts:
                results[tier] = []
                continue

            # Simple relevance scoring (query term matching)
            query_terms = set(query.lower().split())
            scored_facts = []

            for fact in tier_facts:
                fact_terms = set(fact.fact_text.lower().split())
                overlap = len(query_terms & fact_terms)

                if overlap > 0:
                    score = overlap / len(query_terms)
                    # Boost by importance
                    score = score * 0.7 + fact.importance * 0.3

                    if score >= min_score:
                        scored_facts.append(
                            {
                                "fact_id": str(fact.fact_id),
                                "fact_text": fact.fact_text,
                                "tier": tier,
                                "importance": fact.importance,
                                "score": round(score, 3),
                                "tags": fact.tags,
                            }
                        )

            # Sort by score and take top N
            scored_facts.sort(key=lambda x: x["score"], reverse=True)
            results[tier] = scored_facts[:max_per_tier]
            total += len(results[tier])

        return {
            "results": results,
            "total": total,
            "tier_order": tier_order,
        }

    async def get_tier_stats(self) -> dict[str, Any]:
        """
        Get statistics about facts in each memory tier.

        Returns:
            Dict with tier statistics
        """
        if self._repository is None:
            return {}

        stats = {}

        for tier in ["identity", "project", "session", "general"]:
            facts = await self._repository.get_semantic_facts_by_tier(
                tier=tier,
                limit=1000,
            )

            if facts:
                avg_importance = sum(f.importance for f in facts) / len(facts)
                stats[tier] = {
                    "count": len(facts),
                    "avg_importance": round(avg_importance, 3),
                }
            else:
                stats[tier] = {"count": 0, "avg_importance": 0}

        return stats

    # =========================================================================
    # Strategy-Based Retrieval (GMP-80-A6)
    # =========================================================================

    @must_stay_async("callers use await")
    async def strategy_search(
        self,
        query: str,
        context: dict[str, Any] | None = None,
        max_results: int = 10,
        use_ranking: bool = True,
    ) -> dict[str, Any]:
        """
        Execute strategy-based retrieval.

        This is the frontier-grade retrieval method that:
        1. Analyzes the query to determine intent
        2. Selects the optimal retrieval strategy
        3. Executes strategy-specific retrieval
        4. Optionally ranks results using multi-factor scoring

        Strategies:
        - core_identity: Identity tier facts (values, preferences, goals)
        - project_context: Project-scoped facts
        - temporal_recall: Time-based episode retrieval
        - association: Graph-based fact-episode linking
        - uncertainty_fill: High-confidence facts for uncertainty reduction
        - semantic_search: Standard semantic similarity (fallback)

        Args:
            query: Natural language query
            context: Optional context dict with:
                - project_id: Current project
                - session_id: Current session
                - agent_id: Agent making the query
                - agent_uncertainty: Agent's uncertainty level (0.0-1.0)
            max_results: Maximum results to return
            use_ranking: Whether to apply multi-factor ranking

        Returns:
            Dict with strategy, results, and metadata
        """
        from memory.query_classifier import get_query_classifier
        from memory.retrieval_ranking import get_multi_factor_ranker
        from memory.retrieval_strategy import StrategyContext, get_strategy_retriever

        context = context or {}

        # Determine strategy using query classifier
        classifier = get_query_classifier()
        strategy_name, strategy_reason = classifier.determine_retrieval_strategy(
            query=query,
            context=context,
        )

        logger.info(
            f"Strategy search: strategy={strategy_name}",
            query=query[:50],
            reason=strategy_reason,
        )

        # Build strategy context
        strategy_context = StrategyContext(
            query=query,
            query_pattern=classifier.classify_query(query),
            project_id=context.get("project_id"),
            session_id=context.get("session_id"),
            agent_id=context.get("agent_id"),
            agent_uncertainty=context.get("agent_uncertainty", 0.5),
            entities=context.get("entities", []),
        )

        # Execute strategy
        retriever = get_strategy_retriever()
        if retriever._repository is None and self._repository:
            retriever.set_repository(self._repository)

        result = await retriever.retrieve(
            query=query,
            context=strategy_context,
            max_results=max_results,
        )

        # Apply multi-factor ranking if requested
        if use_ranking and result.results:
            ranker = get_multi_factor_ranker()
            ranked_results = ranker.rank_dicts(
                items=result.results,
                agent_uncertainty=context.get("agent_uncertainty", 0.5),
            )
            result.results = ranked_results

        return {
            "strategy": result.strategy.value,
            "strategy_reason": result.strategy_reason,
            "results": result.results,
            "total_results": len(result.results),
            "execution_time_ms": result.execution_time_ms,
            "query": query,
            "context": {
                "project_id": context.get("project_id"),
                "agent_uncertainty": context.get("agent_uncertainty", 0.5),
            },
        }

    # =========================================================================
    # Unified Search Dispatcher
    # =========================================================================

    @must_stay_async("callers use await")
    async def search(
        self,
        query: str,
        agent_id: str | None = None,
        limit: int = 10,
        min_similarity: float = 0.5,
        scope: str = "cursor",  # Valid: developer, global, cursor, l-private, agent
        force_mode: str | None = None,
    ) -> list[dict[str, Any]]:
        """
        Unified search dispatcher with automatic query classification.

        Routes queries through QueryClassifier to select the optimal
        retrieval strategy. Replaces direct calls to individual search
        methods for most use cases.

        Classification to Strategy mapping:
            factual      -> keyword_search()
            conceptual   -> semantic_search()
            relational   -> graph_enriched_search()
            temporal     -> hierarchical_search()
            ambiguous    -> hybrid_search() (RRF fusion)
            strategic    -> strategy_search()

        Args:
            query: Natural language search query.
            agent_id: Agent context for scoped search.
            limit: Maximum results to return.
            min_similarity: Minimum similarity threshold.
            scope: RLS scope ("shared", "private", etc.).
            force_mode: Override classification with explicit mode.

        Returns:
            List of result dicts with scores and metadata.
        """
        from memory.query_classifier import QueryClassifier

        # Classify or use forced mode
        if force_mode:
            query_type = force_mode
        else:
            classifier = QueryClassifier()
            query_type = classifier.classify_query(query)

        logger.info(
            "retrieval_search_dispatched",
            query_type=query_type,
            query_preview=query[:80],
            limit=limit,
        )

        # Route to appropriate strategy based on classify_query() output:
        # entity_lookup, reasoning_trace, temporal, exploratory, factual, default
        if query_type == "factual":
            return await self.keyword_search(
                query=query,
                top_k=limit,
            )
        if query_type == "entity_lookup":
            return await self.graph_enriched_search(
                query=query,
                agent_id=agent_id,
                limit=limit,
                min_similarity=min_similarity,
                scope=scope,
            )
        if query_type == "temporal":
            return await self.hierarchical_search(
                query=query,
                max_per_tier=limit,
            )
        if query_type == "reasoning_trace":
            return await self.strategy_search(
                query=query,
                max_results=limit,
            )
        if query_type == "exploratory":
            return await self.semantic_search(
                query=query,
                agent_id=agent_id,
                top_k=limit,
            )
        # "default" or unknown
        return await self.hybrid_search(
            query=query,
            agent_id=agent_id,
            top_k=limit,
            min_score=min_similarity,
        )

    # =========================================================================
    # Graph-Enriched Search
    # =========================================================================

    @must_stay_async("callers use await")
    async def graph_enriched_search(
        self,
        query: str,
        agent_id: str | None = None,
        limit: int = 10,
        min_similarity: float = 0.5,
        scope: str = "cursor",  # Valid: developer, global, cursor, l-private, agent
    ) -> list[dict[str, Any]]:
        """
        Graph-enriched search: vector similarity + Neo4j relationship context.

        Wraps HybridRAGPipeline.search() into the RetrievalPipeline interface.
        Results include both semantic similarity AND graph-derived context
        (related entities, causal chains, relationship paths).

        Args:
            query: Natural language search query.
            agent_id: Agent context for scoped search.
            limit: Maximum results.
            min_similarity: Minimum vector similarity threshold.
            scope: RLS scope.

        Returns:
            List of result dicts with vector + graph enrichment.
        """
        from memory.graph_client import get_neo4j_client
        from memory.hybrid_rag import EnrichmentStrategy, HybridRAGPipeline

        neo4j = await get_neo4j_client()
        if not neo4j or not neo4j.is_available():
            logger.info(
                "graph_enriched_search: Neo4j unavailable, falling back to semantic",
            )
            return await self.semantic_search(
                query=query,
                agent_id=agent_id,
                top_k=limit,
            )

        pipeline = HybridRAGPipeline(
            semantic_service=self._semantic_service,
            neo4j_client=neo4j,
        )

        hybrid_result = await pipeline.search(
            query=query,
            limit=limit,
            min_similarity=min_similarity,
            strategy=EnrichmentStrategy.EXTENDED,
            enrich_top_n=min(5, limit),
        )

        # Convert HybridResult objects to standard result dicts
        results: list[dict[str, Any]] = []
        for hr in hybrid_result.results:
            result_dict: dict[str, Any] = {
                "packet_id": str(hr.vector_hit.packet_id),
                "content": hr.vector_hit.content,
                "similarity": hr.vector_hit.similarity,
                "combined_score": hr.combined_score,
                "ranking_factors": hr.ranking_factors,
                "kind": hr.vector_hit.kind,
                "source_id": hr.vector_hit.source_id,
                "thread_id": hr.vector_hit.thread_id,
                "search_mode": "graph_enriched",
            }

            if hr.enrichment:
                result_dict["related_entities"] = hr.enrichment.related_entities
                result_dict["relationship_paths"] = hr.enrichment.relationship_paths
                result_dict["causal_chain"] = hr.enrichment.causal_chain
                result_dict["entity_count"] = hr.enrichment.entity_count
                result_dict["relationship_count"] = hr.enrichment.relationship_count

            results.append(result_dict)

        logger.info(
            "graph_enriched_search: Complete",
            query_preview=query[:50],
            results_count=len(results),
            enriched_count=hybrid_result.enriched_count,
            total_entities=hybrid_result.total_entities_found,
        )

        return results


# =============================================================================
# Singleton / Factory
# =============================================================================


@lru_cache(maxsize=1)
@register_singleton(
    name="retrieval_pipeline",
    lifecycle="lazy",
    description="Memory retrieval pipeline for semantic and graph-based search",
)
def get_retrieval_pipeline() -> RetrievalPipeline:
    """Get or create the retrieval pipeline singleton. CACHED."""
    return RetrievalPipeline()


def init_retrieval_pipeline(
    repository: SubstrateRepository,
    semantic_service: SemanticService | None = None,
) -> RetrievalPipeline:
    """Initialize the retrieval pipeline with dependencies."""
    pipeline = get_retrieval_pipeline()
    pipeline.set_repository(repository)
    if semantic_service:
        pipeline.set_semantic_service(semantic_service)
    return pipeline


# =============================================================================
# Governance Pattern Retrieval (for closed-loop learning)
# =============================================================================


@must_stay_async("callers use await")
async def get_governance_patterns(
    tool_name: str | None = None,
    task_type: str | None = None,
    decision: str | None = None,
    limit: int = 5,
) -> list[dict[str, Any]]:
    """
    Retrieve governance patterns for adaptive prompting.

    Searches the governance_patterns segment for patterns matching
    the specified criteria, enabling L to learn from past decisions.

    Args:
        tool_name: Filter by tool name (e.g., "gmprun", "git_commit")
        task_type: Filter by task type (e.g., "infrastructure_change")
        decision: Filter by decision ("approved" or "rejected")
        limit: Maximum number of patterns to return

    Returns:
        List of governance pattern dicts sorted by relevance/recency
    """

    pipeline = get_retrieval_pipeline()

    if pipeline._repository is None:
        logger.warning("Retrieval pipeline not initialized, cannot get patterns")
        return []

    try:
        # Query governance_pattern packets
        async with pipeline._repository.acquire() as conn:
            # Build query with filters
            # Note: packet_store uses packet_id (not id), envelope (not payload), timestamp (not created_at)
            query = """
                SELECT packet_id, packet_type, envelope, provenance, timestamp
                FROM packet_store
                WHERE packet_type = 'governance_pattern'
            """
            params = []
            param_idx = 1

            if tool_name:
                query += f" AND envelope->'payload'->>'tool_name' = ${param_idx}"
                params.append(tool_name)
                param_idx += 1

            if task_type:
                query += f" AND envelope->'payload'->>'task_type' = ${param_idx}"
                params.append(task_type)
                param_idx += 1

            if decision:
                query += f" AND envelope->'payload'->>'decision' = ${param_idx}"
                params.append(decision)
                param_idx += 1

            query += f" ORDER BY timestamp DESC LIMIT ${param_idx}"
            params.append(limit)

            rows = await conn.fetch(query, *params)

            patterns = []
            for row in rows:
                try:
                    envelope = row["envelope"]
                    if isinstance(envelope, str):
                        import json

                        envelope = json.loads(envelope)
                    # Extract payload from envelope
                    payload = envelope.get("payload", envelope)
                    patterns.append(payload)
                except Exception as e:
                    logger.warning(f"Failed to parse pattern: {e}")

            logger.info(
                f"Retrieved {len(patterns)} governance patterns",
                tool_name=tool_name,
                task_type=task_type,
            )
            return patterns

    except Exception as e:
        logger.error(f"Failed to retrieve governance patterns: {e}")
        return []


# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "MEM-LEAR-031",
    "governance_level": "critical",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [
        "core.schemas",
        "memory.cross_encoder_reranker",
        "memory.governance_gate",
        "memory.query_classifier",
        "memory.retrieval_ranking",
    ],
    "tags": [
        "async",
        "caching",
        "debugging",
        "event-driven",
        "learning",
        "logging",
        "memory-substrate",
        "messaging",
        "queue",
        "serialization",
    ],
    "keywords": [
        "added",
        "apply",
        "chain",
        "cross",
        "decay",
        "encoder",
        "facts",
        "fetch",
    ],
    "business_value": "Implements RetrievalPipeline for retrieval functionality",
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
