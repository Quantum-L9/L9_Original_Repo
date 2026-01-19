"""
L9 Memory Substrate - Retrieval Pipeline
Version: 1.2.0

Hybrid and structured search features:
- Semantic search (vector similarity)
- Hybrid search (semantic + structured filters)
- Reciprocal rank fusion (multi-source ranking)
- Temporal decay (recency weighting)
- Thread reconstruction
- Lineage traversal
- Fact/insight retrieval
- Replay chain reconstruction

All operations are async-safe with proper logging.

Changelog:
- v1.2.0: Added reciprocal_rank_fusion, apply_temporal_decay
- v1.1.0: Initial hybrid search
"""

from __future__ import annotations

import math
import structlog
from datetime import datetime
from functools import lru_cache
from typing import Any, Optional
from uuid import UUID

from core.schemas import SemanticHit, SemanticSearchResult
from memory.substrate_models import KnowledgeFactRow, PacketStoreRow
from memory.governance_gate import (
    build_scope_project_filter,
    ensure_governance_context,
    require_governance_context,
)

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
    reference_time: Optional[datetime] = None,
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
        >>> now = datetime.utcnow()
        >>> recent_score = apply_temporal_decay(1.0, now, half_life_days=30)
        >>> # recent_score ≈ 1.0
        >>> old = now - timedelta(days=30)
        >>> old_score = apply_temporal_decay(1.0, old, half_life_days=30)
        >>> # old_score ≈ 0.5
    """
    if reference_time is None:
        reference_time = datetime.utcnow()
    
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

    def set_repository(self, repository) -> None:
        """Set or update the repository reference."""
        self._repository = repository

    def set_semantic_service(self, service) -> None:
        """Set or update the semantic service reference."""
        self._semantic_service = service

    # =========================================================================
    # Semantic Search
    # =========================================================================

    async def semantic_search(
        self,
        query: str,
        top_k: int = 10,
        agent_id: Optional[str] = None,
    ) -> SemanticSearchResult:
        """
        Perform semantic search using vector similarity.

        Args:
            query: Natural language search query
            top_k: Number of results to return
            agent_id: Optional agent filter

        Returns:
            SemanticSearchResult with hits
        """
        logger.debug(f"Semantic search: query='{query[:50]}...', top_k={top_k}")

        if self._semantic_service is None:
            logger.warning("Semantic service not configured")
            return SemanticSearchResult(query=query, hits=[])

        hits = await self._semantic_service.search(
            query=query,
            top_k=top_k,
            agent_id=agent_id,
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
    # Hybrid Search
    # =========================================================================

    async def hybrid_search(
        self,
        query: str,
        top_k: int = 10,
        filters: Optional[dict[str, Any]] = None,
        agent_id: Optional[str] = None,
        min_score: float = 0.5,
    ) -> dict[str, Any]:
        """
        Perform hybrid search combining semantic and structured filters.

        Args:
            query: Natural language search query
            top_k: Number of results to return
            filters: Structured filters (packet_type, tags, date_range, etc.)
            agent_id: Optional agent filter
            min_score: Minimum similarity score threshold

        Returns:
            Dict with semantic_hits, filtered_packets, and combined results
        """
        logger.debug(f"Hybrid search: query='{query[:50]}...', filters={filters}")

        filters = filters or {}

        # Step 1: Semantic search
        semantic_result = await self.semantic_search(
            query=query,
            top_k=top_k * 2,  # Get more to allow filtering
            agent_id=agent_id,
        )

        # Filter by score
        semantic_hits = [h for h in semantic_result.hits if h.score >= min_score]

        # Step 2: Get packet IDs from semantic results
        packet_ids = []
        for hit in semantic_hits:
            packet_id = hit.payload.get("packet_id")
            if packet_id:
                try:
                    packet_ids.append(UUID(packet_id))
                except (ValueError, TypeError):
                    pass

        # Step 3: Apply structured filters
        filtered_packets = []

        if packet_ids and self._repository:
            for pid in packet_ids[:top_k]:
                packet = await self._repository.get_packet(pid)
                if packet and self._matches_filters(packet, filters):
                    filtered_packets.append(packet)

        # Step 4: Combine and rank
        combined = []
        for hit in semantic_hits:
            packet_id = hit.payload.get("packet_id")
            matching_packet = next(
                (p for p in filtered_packets if str(p.packet_id) == packet_id), None
            )
            combined.append(
                {
                    "score": hit.score,
                    "embedding_id": str(hit.embedding_id),
                    "packet_id": packet_id,
                    "payload": hit.payload,
                    "packet": matching_packet.model_dump(mode="json")
                    if matching_packet
                    else None,
                }
            )

        # Sort by score and limit
        combined.sort(key=lambda x: x["score"], reverse=True)
        combined = combined[:top_k]

        return {
            "query": query,
            "filters": filters,
            "semantic_hits": len(semantic_hits),
            "filtered_count": len(filtered_packets),
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

        ctx = require_governance_context("retrieval.fetch_thread")
        async with self._repository.acquire() as conn:
            order_clause = "ASC" if order == "asc" else "DESC"
            filter_clause, params, _ = build_scope_project_filter(
                ctx, param_idx=3, table_alias="packet_store"
            )

            rows = await conn.fetch(
                f"""
                SELECT * FROM packet_store
                WHERE thread_id = $1
                {filter_clause}
                ORDER BY timestamp {order_clause}
                LIMIT $2
                """,
                thread_id,
                limit,
                *params,
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

        ctx = require_governance_context("retrieval.fetch_lineage")
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
                    "timestamp": packet.timestamp.isoformat()
                    if packet.timestamp
                    else None,
                    "depth": depth,
                }
            )

            if direction == "ancestors":
                # Traverse up to parents
                parent_ids = packet.parent_ids or []
                for pid in parent_ids:
                    queue.append((pid, depth + 1))
            else:
                # Traverse down to children
                async with self._repository.acquire() as conn:
                    filter_clause, params, _ = build_scope_project_filter(
                        ctx, param_idx=2, table_alias="packet_store"
                    )
                    rows = await conn.fetch(
                        f"""
                        SELECT packet_id FROM packet_store
                        WHERE $1 = ANY(parent_ids)
                        {filter_clause}
                        """,
                        current_id,
                        *params,
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

    async def fetch_facts(
        self,
        subject: Optional[str] = None,
        predicate: Optional[str] = None,
        source_packet: Optional[UUID] = None,
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

        if source_packet:
            facts = await self._repository.get_facts_by_packet(source_packet, limit)
        elif subject:
            facts = await self._repository.get_facts_by_subject(
                subject, predicate, limit
            )
        else:
            ctx = require_governance_context("retrieval.fetch_facts")
            # Fetch recent facts
            async with self._repository.acquire() as conn:
                filter_clause, params, _ = build_scope_project_filter(
                    ctx, param_idx=2, table_alias="packet_store"
                )
                rows = await conn.fetch(
                    f"""
                    SELECT knowledge_facts.*
                    FROM knowledge_facts
                    INNER JOIN packet_store ON packet_store.packet_id = knowledge_facts.source_packet
                    WHERE TRUE
                    {filter_clause}
                    ORDER BY created_at DESC
                    LIMIT $1
                    """,
                    limit,
                    *params,
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

    async def fetch_insights(
        self,
        packet_id: Optional[UUID] = None,
        insight_type: Optional[str] = None,
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

        ctx = require_governance_context("retrieval.fetch_insights")
        async with self._repository.acquire() as conn:
            filter_clause, params, param_idx = build_scope_project_filter(
                ctx, param_idx=3, table_alias="packet_store"
            )
            if packet_id:
                rows = await conn.fetch(
                    f"""
                    SELECT * FROM packet_store
                    WHERE packet_type = 'insight'
                    AND envelope->>'source_packet' = $1
                    {filter_clause}
                    ORDER BY timestamp DESC
                    LIMIT $2
                    """,
                    str(packet_id),
                    limit,
                    *params,
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
                    """,
                    insight_type,
                    limit,
                    *params,
                )
            else:
                filter_clause, params, _ = build_scope_project_filter(
                    ctx, param_idx=2, table_alias="packet_store"
                )
                rows = await conn.fetch(
                    f"""
                    SELECT * FROM packet_store
                    WHERE packet_type = 'insight'
                    {filter_clause}
                    ORDER BY timestamp DESC
                    LIMIT $1
                    """,
                    limit,
                    *params,
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

    async def replay_chain(
        self,
        start_packet_id: UUID,
        end_packet_id: Optional[UUID] = None,
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

        chain = []
        for item in lineage["chain"]:
            packet_id = UUID(item["packet_id"])
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


# =============================================================================
# Singleton / Factory
# =============================================================================

@lru_cache(maxsize=1)
def get_retrieval_pipeline() -> RetrievalPipeline:
    """Get or create the retrieval pipeline singleton. CACHED."""
    return RetrievalPipeline()


def init_retrieval_pipeline(repository, semantic_service=None) -> RetrievalPipeline:
    """Initialize the retrieval pipeline with dependencies."""
    pipeline = get_retrieval_pipeline()
    pipeline.set_repository(repository)
    if semantic_service:
        pipeline.set_semantic_service(semantic_service)
    return pipeline


# =============================================================================
# Governance Pattern Retrieval (for closed-loop learning)
# =============================================================================


async def get_governance_patterns(
    tool_name: Optional[str] = None,
    task_type: Optional[str] = None,
    decision: Optional[str] = None,
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
        async with ensure_governance_context("retrieval.get_governance_patterns") as ctx:
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
                filter_clause, filter_params, param_idx = build_scope_project_filter(
                    ctx, param_idx=1, table_alias="packet_store"
                )
                params.extend(filter_params)
                query += f" {filter_clause}"

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
