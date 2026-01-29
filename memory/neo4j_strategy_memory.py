"""
L9 Neo4j Strategy Memory Service
=================================

Production Neo4j-backed implementation of IStrategyMemoryService.

Provides:
- Hybrid retrieval (embedding + graph + symbolic)
- Strategy recording with Neo4j persistence
- Feedback loop with exponential smoothing

Phase 0: Retrieval-only with manual seeding
Phase 1: Auto-capture of successful executions

Version: 1.0.0
Created: 2026-01-20
GMP: GMP-102 Strategy Memory Phase 0-1
"""

from __future__ import annotations

# ============================================================================
__dora_meta__ = {
    "component_name": "Neo4j Strategy Memory Service",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2026-01-20T00:00:00Z",
    "updated_at": "2026-01-20T00:00:00Z",
    "layer": "learning",
    "domain": "strategy_memory",
    "module_name": "neo4j_strategy_memory",
    "type": "service",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": ["Neo4j", "PostgreSQL"],
        "memory_layers": ["semantic_memory", "graph_memory"],
        "imported_by": ["memory.__init__", "orchestration.plan_executor"],
    },
}
# ============================================================================

import contextlib
import hashlib
import json
import uuid
from datetime import datetime
from typing import Any

import structlog

from core.decorators import must_stay_async
from memory.strategymemory import (
    IStrategyMemoryService,
    StrategyCandidate,
    StrategyFeedback,
    StrategyRetrievalRequest,
)

logger = structlog.get_logger(__name__)


# =============================================================================
# Configuration
# =============================================================================


class StrategyMemoryConfig:
    """Configuration for Neo4j Strategy Memory Service."""

    # Hybrid scoring weights (must sum to 1.0)
    EMBEDDING_WEIGHT: float = 0.4
    GRAPH_WEIGHT: float = 0.4
    SYMBOLIC_WEIGHT: float = 0.2

    # Score update parameters
    SMOOTHING_ALPHA: float = 0.3  # Exponential smoothing factor

    # Retrieval thresholds
    DEFAULT_MIN_CONFIDENCE: float = 0.6
    DEFAULT_MAX_RESULTS: int = 5

    # Embedding dimensions (must match substrate layer)
    EMBEDDING_DIM: int = 1536

    # Schema version for compatibility
    SCHEMA_VERSION: str = "1.0.0"


# =============================================================================
# Neo4j Strategy Memory Service
# =============================================================================


class Neo4jStrategyMemoryService(IStrategyMemoryService):
    """
    Production Neo4j-backed Strategy Memory Service.

    Implements hybrid retrieval:
    - 40% Embedding similarity (cosine, via pgvector or Neo4j)
    - 40% Graph structure similarity (graph_signature hash match)
    - 20% Symbolic tag matching

    Phase 0: Retrieval + manual seeding
    Phase 1: Auto-capture on successful execution
    """

    def __init__(
        self,
        neo4j_client: Any,
        semantic_service: Any | None = None,
        config: StrategyMemoryConfig | None = None,
    ):
        """
        Initialize Neo4j Strategy Memory Service.

        Args:
            neo4j_client: Neo4j client instance (memory.graph_client.Neo4jClient)
            semantic_service: Optional semantic service for embedding generation
            config: Optional configuration overrides
        """
        self._neo4j = neo4j_client
        self._semantic = semantic_service
        self._config = config or StrategyMemoryConfig()

        logger.info(
            "Neo4jStrategyMemoryService initialized",
            embedding_weight=self._config.EMBEDDING_WEIGHT,
            graph_weight=self._config.GRAPH_WEIGHT,
            symbolic_weight=self._config.SYMBOLIC_WEIGHT,
            schema_version=self._config.SCHEMA_VERSION,
        )

    # =========================================================================
    # IStrategyMemoryService Implementation
    # =========================================================================

    @must_stay_async("callers use await")
    async def retrieve_strategies(
        self,
        request: StrategyRetrievalRequest,
        limit: int = 3,
    ) -> list[StrategyCandidate]:
        """
        Retrieve matching strategies using hybrid scoring.

        Scoring formula:
        score = 0.4 * embedding_sim + 0.4 * graph_sim + 0.2 * tag_sim

        Args:
            request: Retrieval request with task context
            limit: Maximum candidates to return

        Returns:
            List of StrategyCandidate sorted by score descending
        """
        if not self._neo4j or not await self._neo4j.is_available():
            logger.warning("Neo4j not available, returning empty results")
            return []

        try:
            # Build retrieval query
            candidates = await self._retrieve_candidates(request)

            # Compute hybrid scores
            scored_candidates = await self._score_candidates(candidates, request)

            # Filter by confidence threshold
            min_conf = request.min_confidence or self._config.DEFAULT_MIN_CONFIDENCE
            filtered = [c for c in scored_candidates if c.confidence >= min_conf]

            # Sort by score and limit
            filtered.sort(key=lambda c: c.score, reverse=True)
            result = filtered[:limit]

            logger.info(
                "strategy_retrieval_complete",
                task_id=request.task_id,
                task_kind=request.task_kind,
                total_candidates=len(candidates),
                after_scoring=len(scored_candidates),
                after_filter=len(filtered),
                returned=len(result),
            )

            return result

        except Exception as e:
            logger.error(
                "strategy_retrieval_failed",
                task_id=request.task_id,
                error=str(e),
                exc_info=True,
            )
            return []

    @must_stay_async("callers use await")
    async def record_new_strategy(
        self,
        task_id: str,
        description: str,
        plan_payload: dict[str, Any],
        context_embedding: list[float],
        tags: list[str] | None = None,
    ) -> str:
        """
        Record a new strategy to Neo4j.

        Args:
            task_id: ID of the task that produced this strategy
            description: Human-readable description
            plan_payload: Serialized ExecutionPlan
            context_embedding: Task context embedding (1536-dim)
            tags: Optional categorization tags

        Returns:
            strategy_id of the newly created strategy
        """
        if not self._neo4j or not await self._neo4j.is_available():
            logger.error("Neo4j not available, cannot record strategy")
            raise RuntimeError("Neo4j not available")

        strategy_id = f"str_{uuid.uuid4().hex[:12]}"
        graph_signature = self._compute_graph_signature(plan_payload)
        now = datetime.now(timezone.utc).isoformat()

        # Extract task_kind from payload if available
        task_kind = plan_payload.get("task_kind", "unknown")

        query = """
        CREATE (s:Strategy {
            id: $id,
            name: $name,
            description: $description,
            task_kind: $task_kind,
            context_embedding: $embedding,
            graph_signature: $graph_sig,
            plan_payload: $payload_json,
            performance_score: 1.0,
            generality_score: 0.0,
            confidence: 1.0,
            usage_count: 0,
            success_count: 0,
            failure_count: 0,
            tags: $tags,
            created_at: datetime($created_at),
            last_used: datetime($created_at),
            schema_version: $schema_version
        })
        RETURN s.id as strategy_id
        """

        params = {
            "id": strategy_id,
            "name": f"Strategy for {task_id}",
            "description": description,
            "task_kind": task_kind,
            "embedding": context_embedding,
            "graph_sig": graph_signature,
            "payload_json": json.dumps(plan_payload),
            "tags": tags or [],
            "created_at": now,
            "schema_version": self._config.SCHEMA_VERSION,
        }

        try:
            await self._neo4j.execute_query(query, params)

            logger.info(
                "strategy_recorded",
                strategy_id=strategy_id,
                task_id=task_id,
                task_kind=task_kind,
                tags=tags,
                graph_signature=graph_signature[:16] + "...",
            )

            return strategy_id

        except Exception as e:
            logger.error(
                "strategy_record_failed",
                task_id=task_id,
                error=str(e),
                exc_info=True,
            )
            raise

    @must_stay_async("callers use await")
    async def update_strategy_outcome(
        self,
        feedback: StrategyFeedback,
    ) -> None:
        """
        Update strategy scores based on execution outcome.

        Uses exponential smoothing:
        new_score = α * outcome_score + (1-α) * old_score

        Args:
            feedback: Feedback from strategy execution
        """
        if not self._neo4j or not await self._neo4j.is_available():
            logger.warning("Neo4j not available, cannot update strategy")
            return

        alpha = self._config.SMOOTHING_ALPHA

        # Update strategy and create execution record
        query = """
        MATCH (s:Strategy {id: $strategy_id})
        SET s.performance_score = $alpha * $outcome_score + (1 - $alpha) * s.performance_score,
            s.usage_count = s.usage_count + 1,
            s.success_count = CASE WHEN $success THEN s.success_count + 1 ELSE s.success_count END,
            s.failure_count = CASE WHEN NOT $success THEN s.failure_count + 1 ELSE s.failure_count END,
            s.last_used = datetime($timestamp)
        WITH s
        CREATE (s)-[:EXECUTED_AS]->(e:Execution {
            id: $execution_id,
            strategy_id: $strategy_id,
            task_id: $task_id,
            success: $success,
            outcome_score: $outcome_score,
            execution_time_ms: $exec_time,
            resource_cost: $resource_cost,
            failure_reason: $failure_reason,
            was_adapted: $was_adapted,
            adaptation_distance: $adaptation_distance,
            timestamp: datetime($timestamp)
        })
        RETURN s.performance_score as new_score
        """

        params = {
            "strategy_id": feedback.strategy_id,
            "task_id": feedback.task_id,
            "success": feedback.success,
            "outcome_score": feedback.outcome_score,
            "exec_time": feedback.execution_time_ms,
            "resource_cost": feedback.resource_cost,
            "failure_reason": feedback.metadata.get("failure_reason"),
            "was_adapted": feedback.was_adapted,
            "adaptation_distance": feedback.adaptation_distance,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "execution_id": f"exec_{uuid.uuid4().hex[:12]}",
            "alpha": alpha,
        }

        try:
            await self._neo4j.execute_query(query, params)

            logger.info(
                "strategy_outcome_updated",
                strategy_id=feedback.strategy_id,
                task_id=feedback.task_id,
                success=feedback.success,
                outcome_score=feedback.outcome_score,
            )

        except Exception as e:
            logger.error(
                "strategy_outcome_update_failed",
                strategy_id=feedback.strategy_id,
                error=str(e),
                exc_info=True,
            )

    # =========================================================================
    # Internal Methods
    # =========================================================================

    async def _retrieve_candidates(
        self,
        request: StrategyRetrievalRequest,
    ) -> list[dict[str, Any]]:
        """
        Retrieve candidate strategies from Neo4j.

        Phase 0: Simple tag and task_kind filtering
        Future: Add embedding similarity search
        """
        # Build filter conditions
        conditions = ["s.schema_version = $schema_version"]
        params: dict[str, Any] = {
            "schema_version": self._config.SCHEMA_VERSION,
            "limit": request.max_results or self._config.DEFAULT_MAX_RESULTS,
        }

        # Filter by task_kind if provided
        if request.task_kind:
            conditions.append("s.task_kind = $task_kind")
            params["task_kind"] = request.task_kind

        # Filter by tags if provided
        if request.tags:
            conditions.append("any(tag IN s.tags WHERE tag IN $tags)")
            params["tags"] = request.tags

        where_clause = " AND ".join(conditions) if conditions else "true"

        query = f"""
        MATCH (s:Strategy)
        WHERE {where_clause}
        RETURN s {{
            .id,
            .name,
            .description,
            .task_kind,
            .context_embedding,
            .graph_signature,
            .plan_payload,
            .performance_score,
            .generality_score,
            .confidence,
            .usage_count,
            .tags
        }} as strategy
        ORDER BY s.performance_score DESC, s.last_used DESC
        LIMIT $limit
        """

        result = await self._neo4j.execute_query(query, params)
        return [r["strategy"] for r in result] if result else []

    async def _score_candidates(
        self,
        candidates: list[dict[str, Any]],
        request: StrategyRetrievalRequest,
    ) -> list[StrategyCandidate]:
        """
        Compute hybrid scores for candidates.

        Score = 0.4 * embedding_sim + 0.4 * graph_sim + 0.2 * tag_sim
        """
        scored = []

        for cand in candidates:
            # Embedding similarity (Phase 0: use stored confidence as proxy)
            embedding_sim = await self._compute_embedding_similarity(
                request.context_embedding,
                cand.get("context_embedding", []),
            )

            # Graph similarity (Phase 0: binary match on graph_signature)
            graph_sim = self._compute_graph_similarity(
                request.goal_description,
                cand.get("graph_signature", ""),
            )

            # Tag similarity
            tag_sim = self._compute_tag_similarity(
                request.tags,
                cand.get("tags", []),
            )

            # Compute hybrid score
            score = (
                self._config.EMBEDDING_WEIGHT * embedding_sim
                + self._config.GRAPH_WEIGHT * graph_sim
                + self._config.SYMBOLIC_WEIGHT * tag_sim
            )

            # Parse plan_payload
            plan_payload = {}
            if cand.get("plan_payload"):
                try:
                    plan_payload = json.loads(cand["plan_payload"])
                except json.JSONDecodeError:
                    logger.warning(
                        "Failed to parse plan_payload",
                        strategy_id=cand.get("id"),
                    )

            candidate = StrategyCandidate(
                strategy_id=cand["id"],
                description=cand.get("description", ""),
                confidence=score,  # Use hybrid score as confidence
                score=score,
                plan_payload=plan_payload,
                performance_score=cand.get("performance_score", 0.0),
                usage_count=cand.get("usage_count", 0),
                tags=cand.get("tags", []),
            )

            scored.append(candidate)

        return scored

    async def _compute_embedding_similarity(
        self,
        query_embedding: list[float],
        stored_embedding: list[float],
    ) -> float:
        """
        Compute cosine similarity between embeddings.

        Phase 0: Simple cosine similarity
        Future: Use pgvector or Neo4j vector index
        """
        if not query_embedding or not stored_embedding:
            return 0.5  # Neutral score if no embedding

        if len(query_embedding) != len(stored_embedding):
            return 0.5  # Dimension mismatch

        # Cosine similarity
        try:
            import numpy as np

            q = np.array(query_embedding)
            s = np.array(stored_embedding)

            dot = np.dot(q, s)
            norm_q = np.linalg.norm(q)
            norm_s = np.linalg.norm(s)

            if norm_q == 0 or norm_s == 0:
                return 0.5

            similarity = dot / (norm_q * norm_s)
            # Normalize to 0-1 range (cosine is -1 to 1)
            return float((similarity + 1) / 2)

        except ImportError:
            # Fallback without numpy
            return 0.5

    def _compute_graph_similarity(
        self,
        goal_description: str,
        stored_signature: str,
    ) -> float:
        """
        Compute graph structure similarity.

        Phase 0: Simple hash-based matching
        Future: Graph edit distance via Neo4j GDS
        """
        if not stored_signature:
            return 0.0

        # Phase 0: Partial string match on description
        # This is a placeholder - real implementation would use graph structure
        goal_lower = goal_description.lower()
        sig_lower = stored_signature.lower()

        # Check for common task patterns in signature
        common_patterns = ["research", "deploy", "analyze", "report", "code"]
        matches = sum(1 for p in common_patterns if p in goal_lower and p in sig_lower)

        return min(matches / 3.0, 1.0)

    def _compute_tag_similarity(
        self,
        request_tags: list[str],
        stored_tags: list[str],
    ) -> float:
        """
        Compute tag overlap similarity.

        Returns: Jaccard similarity coefficient
        """
        if not request_tags or not stored_tags:
            return 0.5  # Neutral if no tags to compare

        request_set = {t.lower() for t in request_tags}
        stored_set = {t.lower() for t in stored_tags}

        intersection = len(request_set & stored_set)
        union = len(request_set | stored_set)

        if union == 0:
            return 0.5

        return intersection / union

    def _compute_graph_signature(
        self,
        plan_payload: dict[str, Any],
    ) -> str:
        """
        Compute a hash signature of the plan structure.

        Used for graph edit distance approximation.
        """
        # Extract structural elements (not values)
        structure = self._extract_structure(plan_payload)
        structure_str = json.dumps(structure, sort_keys=True)
        return hashlib.sha256(structure_str.encode()).hexdigest()

    def _extract_structure(self, obj: Any, depth: int = 0) -> Any:
        """
        Extract structural skeleton from object.

        Removes specific values, keeps structure.
        """
        if depth > 5:
            return "..."

        if isinstance(obj, dict):
            return {k: self._extract_structure(v, depth + 1) for k, v in obj.items()}
        if isinstance(obj, list):
            if not obj:
                return []
            # Sample first element's structure
            return [self._extract_structure(obj[0], depth + 1)]
        if isinstance(obj, str):
            return "str"
        if isinstance(obj, (int, float)):
            return "num"
        if isinstance(obj, bool):
            return "bool"
        if obj is None:
            return "null"
        return str(type(obj).__name__)

    # =========================================================================
    # Utility Methods
    # =========================================================================

    async def get_strategy_by_id(self, strategy_id: str) -> StrategyCandidate | None:
        """
        Get a specific strategy by ID.

        Args:
            strategy_id: Strategy UUID

        Returns:
            StrategyCandidate if found, None otherwise
        """
        if not self._neo4j or not await self._neo4j.is_available():
            return None

        query = """
        MATCH (s:Strategy {id: $id})
        RETURN s {
            .id,
            .description,
            .plan_payload,
            .performance_score,
            .usage_count,
            .tags
        } as strategy
        """

        result = await self._neo4j.execute_query(query, {"id": strategy_id})

        if not result:
            return None

        cand = result[0]["strategy"]
        plan_payload = {}
        if cand.get("plan_payload"):
            with contextlib.suppress(json.JSONDecodeError):
                plan_payload = json.loads(cand["plan_payload"])

        return StrategyCandidate(
            strategy_id=cand["id"],
            description=cand.get("description", ""),
            confidence=cand.get("performance_score", 0.0),
            score=cand.get("performance_score", 0.0),
            plan_payload=plan_payload,
            performance_score=cand.get("performance_score", 0.0),
            usage_count=cand.get("usage_count", 0),
            tags=cand.get("tags", []),
        )

    async def list_strategies(
        self,
        limit: int = 20,
        min_score: float = 0.0,
    ) -> list[StrategyCandidate]:
        """
        List all strategies, optionally filtered by minimum score.

        Args:
            limit: Maximum strategies to return
            min_score: Minimum performance score filter

        Returns:
            List of StrategyCandidate
        """
        if not self._neo4j or not await self._neo4j.is_available():
            return []

        query = """
        MATCH (s:Strategy)
        WHERE s.performance_score >= $min_score
        RETURN s {
            .id,
            .description,
            .plan_payload,
            .performance_score,
            .usage_count,
            .tags
        } as strategy
        ORDER BY s.performance_score DESC
        LIMIT $limit
        """

        result = await self._neo4j.execute_query(
            query, {"min_score": min_score, "limit": limit}
        )

        strategies = []
        for r in result or []:
            cand = r["strategy"]
            plan_payload = {}
            if cand.get("plan_payload"):
                with contextlib.suppress(json.JSONDecodeError):
                    plan_payload = json.loads(cand["plan_payload"])

            strategies.append(
                StrategyCandidate(
                    strategy_id=cand["id"],
                    description=cand.get("description", ""),
                    confidence=cand.get("performance_score", 0.0),
                    score=cand.get("performance_score", 0.0),
                    plan_payload=plan_payload,
                    performance_score=cand.get("performance_score", 0.0),
                    usage_count=cand.get("usage_count", 0),
                    tags=cand.get("tags", []),
                )
            )

        return strategies

    async def delete_strategy(self, strategy_id: str) -> bool:
        """
        Delete a strategy and its executions.

        Args:
            strategy_id: Strategy UUID to delete

        Returns:
            True if deleted, False if not found
        """
        if not self._neo4j or not await self._neo4j.is_available():
            return False

        query = """
        MATCH (s:Strategy {id: $id})
        OPTIONAL MATCH (s)-[:EXECUTED_AS]->(e:Execution)
        DETACH DELETE s, e
        RETURN count(s) as deleted
        """

        result = await self._neo4j.execute_query(query, {"id": strategy_id})

        if result and result[0].get("deleted", 0) > 0:
            logger.info("strategy_deleted", strategy_id=strategy_id)
            return True

        return False


# =============================================================================
# Factory Function
# =============================================================================


def create_neo4j_strategy_memory(
    neo4j_client: Any,
    semantic_service: Any | None = None,
) -> Neo4jStrategyMemoryService:
    """
    Factory function to create Neo4j Strategy Memory Service.

    Args:
        neo4j_client: Neo4j client instance
        semantic_service: Optional semantic service for embeddings

    Returns:
        Configured Neo4jStrategyMemoryService
    """
    return Neo4jStrategyMemoryService(
        neo4j_client=neo4j_client,
        semantic_service=semantic_service,
    )


# ============================================================================
# DORA FOOTER META - AUTO-GENERATED
# ============================================================================
__dora_footer__ = {
    "component_id": "MEM-STRAT-001",
    "governance_level": "high",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [
        "memory.strategymemory",
        "memory.graph_client",
        "core.decorators",
    ],
    "tags": [
        "async",
        "graph-db",
        "learning",
        "neo4j",
        "service",
        "strategy",
    ],
    "keywords": [
        "retrieval",
        "hybrid-scoring",
        "feedback-loop",
        "exponential-smoothing",
    ],
    "business_value": "Enables strategy reuse for repeat task optimization",
    "last_modified": "2026-01-20T00:00:00Z",
    "modified_by": "GMP-102",
    "change_summary": "Initial implementation of Neo4j-backed Strategy Memory",
}
# ============================================================================
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
