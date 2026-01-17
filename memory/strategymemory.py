"""
L9 Strategy Memory Service
==========================

Provides strategy retrieval and reuse for the PlanExecutor.

This module enables L9 to remember and reuse successful planning strategies,
transforming it from a stateless planner into a learning orchestrator.

Core Concepts:
- StrategyCandidate: A matched strategy with confidence score
- StrategyRetrievalRequest: Query parameters for finding strategies
- StrategyFeedback: Outcome data for updating strategy scores
- IStrategyMemoryService: Abstract interface for strategy operations

Phase 0 Implementation:
- Retrieval-only with optional manual seeding
- No auto-capture (Phase 1)
- No auto-scoring (Phase 2)

Reference: docs/Roadmap-Upgrades/Memory - Strategic Memory/

Version: 1.0.0
Created: 2026-01-05
"""

from __future__ import annotations

import structlog
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field
from core.decorators import must_stay_async

logger = structlog.get_logger(__name__)


# =============================================================================
# Data Models
# =============================================================================


class StrategyCandidate(BaseModel):
    """A strategy candidate returned from retrieval."""

    strategy_id: str = Field(..., description="Unique identifier for this strategy")
    description: str = Field(
        ..., description="Human-readable description of the strategy"
    )
    confidence: float = Field(
        ..., ge=0.0, le=1.0, description="Confidence score (0.0-1.0)"
    )
    score: float = Field(
        ..., ge=0.0, le=1.0, description="Composite match score (0.0-1.0)"
    )
    plan_payload: Dict[str, Any] = Field(
        default_factory=dict,
        description="Serialized plan / ExecutionPlan structure",
    )
    # Phase 2 additions (prepared but not used yet)
    performance_score: float = Field(
        default=0.0, ge=0.0, le=1.0, description="Historical performance score"
    )
    usage_count: int = Field(default=0, ge=0, description="Number of times used")
    tags: List[str] = Field(default_factory=list, description="Strategy tags")


class StrategyRetrievalRequest(BaseModel):
    """Request parameters for strategy retrieval."""

    task_id: str = Field(..., description="ID of the current task")
    task_kind: str = Field(..., description="Type/kind of task")
    goal_description: str = Field(..., description="Natural language goal description")
    context_embedding: List[float] = Field(
        default_factory=list, description="384-dim embedding vector"
    )
    tags: List[str] = Field(default_factory=list, description="Preferred strategy tags")
    # Retrieval parameters
    min_confidence: float = Field(
        default=0.6, ge=0.0, le=1.0, description="Minimum confidence threshold"
    )
    max_results: int = Field(
        default=5, ge=1, le=20, description="Maximum results to return"
    )


class StrategyFeedback(BaseModel):
    """Feedback data for strategy outcome tracking."""

    strategy_id: str = Field(..., description="ID of the strategy that was executed")
    task_id: str = Field(..., description="ID of the task it was applied to")
    success: bool = Field(..., description="Whether execution succeeded")
    outcome_score: float = Field(
        ..., ge=0.0, le=1.0, description="Quality score of the outcome"
    )
    execution_time_ms: int = Field(..., ge=0, description="Execution duration in ms")
    resource_cost: float = Field(
        default=0.0, ge=0.0, description="Resource cost estimate"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Additional feedback metadata"
    )
    # Phase 2 additions
    was_adapted: bool = Field(default=False, description="Whether strategy was adapted")
    adaptation_distance: Optional[int] = Field(
        default=None, description="Graph edit distance if adapted"
    )


# =============================================================================
# Abstract Interface
# =============================================================================


class IStrategyMemoryService(ABC):
    """
    Abstract interface for Strategy Memory operations.

    Implementations may use:
    - Neo4j (graph-based, full HTN support)
    - PostgreSQL + Qdrant (simpler, 80% value)
    - In-memory dict (testing/development)

    All methods are async to support non-blocking I/O.
    """

    @abstractmethod
    @must_stay_async("callers use await")
    async def retrieve_strategies(
        self,
        request: StrategyRetrievalRequest,
        limit: int = 3,
    ) -> List[StrategyCandidate]:
        """
        Retrieve matching strategies for a given task.

        Args:
            request: Retrieval request with task context and preferences
            limit: Maximum number of candidates to return

        Returns:
            List of StrategyCandidate sorted by score descending
        """
        ...

    @abstractmethod
    @must_stay_async("callers use await")
    async def record_new_strategy(
        self,
        task_id: str,
        description: str,
        plan_payload: Dict[str, Any],
        context_embedding: List[float],
        tags: Optional[List[str]] = None,
    ) -> str:
        """
        Record a new successful strategy.

        Args:
            task_id: ID of the task that produced this strategy
            description: Human-readable description
            plan_payload: Serialized ExecutionPlan
            context_embedding: Task context embedding
            tags: Optional tags for categorization

        Returns:
            strategy_id of the newly created strategy
        """
        ...

    @abstractmethod
    @must_stay_async("callers use await")
    async def update_strategy_outcome(
        self,
        feedback: StrategyFeedback,
    ) -> None:
        """
        Update a strategy's scores based on execution outcome.

        Args:
            feedback: Feedback data from strategy execution
        """
        ...


# =============================================================================
# Stub Implementation (Phase 0)
# =============================================================================


class StrategyMemoryService(IStrategyMemoryService):
    """
    Stub implementation for Phase 0 testing.

    This stub:
    - Returns empty lists for retrieval (no strategies seeded yet)
    - Logs calls for debugging
    - Provides foundation for Neo4j-backed implementation

    To enable real retrieval, seed strategies via record_new_strategy()
    or replace with Neo4j-backed implementation.
    """

    def __init__(self) -> None:
        """Initialize the stub service."""
        self._strategies: Dict[str, StrategyCandidate] = {}
        logger.info("StrategyMemoryService initialized (stub mode)")

    @must_stay_async("callers use await")
    async def retrieve_strategies(
        self,
        request: StrategyRetrievalRequest,
        limit: int = 3,
    ) -> List[StrategyCandidate]:
        """
        Retrieve strategies (stub returns empty list).

        In production, this would:
        1. Query Neo4j with semantic + structural + tag similarity
        2. Compute hybrid score
        3. Filter by min_confidence
        4. Return top N candidates
        """
        logger.debug(
            "strategy_retrieval_requested",
            task_id=request.task_id,
            task_kind=request.task_kind,
            has_embedding=len(request.context_embedding) > 0,
            tags=request.tags,
        )

        # Phase 0: Return any manually seeded strategies that match tags
        candidates = []
        for strategy in self._strategies.values():
            # Simple tag matching for Phase 0
            tag_match = not request.tags or any(
                t in strategy.tags for t in request.tags
            )
            if tag_match and strategy.confidence >= request.min_confidence:
                candidates.append(strategy)

        # Sort by score descending
        candidates.sort(key=lambda s: s.score, reverse=True)

        logger.info(
            "strategy_retrieval_complete",
            task_id=request.task_id,
            candidates_found=len(candidates),
            returned=min(len(candidates), limit),
        )

        return candidates[:limit]

    @must_stay_async("callers use await")
    async def record_new_strategy(
        self,
        task_id: str,
        description: str,
        plan_payload: Dict[str, Any],
        context_embedding: List[float],
        tags: Optional[List[str]] = None,
    ) -> str:
        """
        Record a new strategy (stub stores in memory).

        In production, this would:
        1. Create Strategy node in Neo4j
        2. Store context_embedding
        3. Compute graph_signature from plan structure
        4. Link to Task node
        """
        import uuid

        strategy_id = f"str_{uuid.uuid4().hex[:8]}"

        strategy = StrategyCandidate(
            strategy_id=strategy_id,
            description=description,
            confidence=1.0,  # New strategies start with high confidence
            score=0.8,
            plan_payload=plan_payload,
            performance_score=1.0,
            usage_count=0,
            tags=tags or [],
        )

        self._strategies[strategy_id] = strategy

        logger.info(
            "strategy_recorded",
            strategy_id=strategy_id,
            task_id=task_id,
            description=description[:50],
            tags=tags,
        )

        return strategy_id

    @must_stay_async("callers use await")
    async def update_strategy_outcome(
        self,
        feedback: StrategyFeedback,
    ) -> None:
        """
        Update strategy scores (stub logs only).

        In production, this would:
        1. Load strategy from Neo4j
        2. Apply exponential smoothing to performance_score
        3. Increment usage_count
        4. Create Execution node with outcome data
        """
        logger.info(
            "strategy_feedback_received",
            strategy_id=feedback.strategy_id,
            task_id=feedback.task_id,
            success=feedback.success,
            outcome_score=feedback.outcome_score,
            execution_time_ms=feedback.execution_time_ms,
        )

        # Update in-memory score if strategy exists
        if feedback.strategy_id in self._strategies:
            strategy = self._strategies[feedback.strategy_id]
            # Simple exponential smoothing (alpha=0.3)
            alpha = 0.3
            new_perf = (
                alpha * feedback.outcome_score
                + (1 - alpha) * strategy.performance_score
            )
            # Update via new instance (Pydantic immutability)
            self._strategies[feedback.strategy_id] = StrategyCandidate(
                strategy_id=strategy.strategy_id,
                description=strategy.description,
                confidence=strategy.confidence,
                score=strategy.score,
                plan_payload=strategy.plan_payload,
                performance_score=new_perf,
                usage_count=strategy.usage_count + 1,
                tags=strategy.tags,
            )
