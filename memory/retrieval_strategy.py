"""
L9 Memory Substrate - Strategy-Based Retrieval
Version: 3.1.0

Implements frontier-grade strategy-based retrieval that selects the
appropriate retrieval approach based on query type and context.

Strategies:
- core_identity: Retrieve Tier 1 identity facts (values, preferences, goals)
- project_context: Retrieve project-scoped facts and context
- temporal_recall: Retrieve recent episodes by time range
- association: Find linked facts + episodes (graph traversal)
- uncertainty_fill: Fill knowledge gaps with high-confidence facts

Based on frontier AI lab patterns (Anthropic, OpenAI, DeepMind).
"""

from __future__ import annotations

import structlog
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Optional
from uuid import UUID

logger = structlog.get_logger(__name__)


# =============================================================================
# Retrieval Strategy Enum
# =============================================================================


class RetrievalStrategy(str, Enum):
    """
    Frontier-grade retrieval strategies.

    Each strategy targets a specific type of information need:
    - CORE_IDENTITY: Core facts about agent identity/values (Tier 1)
    - PROJECT_CONTEXT: Project-scoped working memory (Tier 2)
    - TEMPORAL_RECALL: Time-based episode retrieval (Tier 3)
    - ASSOCIATION: Graph-based fact-episode linking
    - UNCERTAINTY_FILL: High-confidence facts to reduce uncertainty
    - SEMANTIC_SEARCH: Standard semantic similarity (fallback)
    """

    CORE_IDENTITY = "core_identity"
    PROJECT_CONTEXT = "project_context"
    TEMPORAL_RECALL = "temporal_recall"
    ASSOCIATION = "association"
    UNCERTAINTY_FILL = "uncertainty_fill"
    SEMANTIC_SEARCH = "semantic_search"  # Default fallback

    @property
    def description(self) -> str:
        """Human-readable description of the strategy."""
        descriptions = {
            RetrievalStrategy.CORE_IDENTITY: "Retrieve identity tier facts (values, preferences, goals)",
            RetrievalStrategy.PROJECT_CONTEXT: "Retrieve project-scoped facts and context",
            RetrievalStrategy.TEMPORAL_RECALL: "Retrieve recent episodes by time range",
            RetrievalStrategy.ASSOCIATION: "Find linked facts and episodes via graph traversal",
            RetrievalStrategy.UNCERTAINTY_FILL: "Fill knowledge gaps with high-confidence facts",
            RetrievalStrategy.SEMANTIC_SEARCH: "Standard semantic similarity search",
        }
        return descriptions.get(self, "Unknown strategy")


# =============================================================================
# Strategy Context
# =============================================================================


@dataclass
class StrategyContext:
    """
    Context for strategy-based retrieval.

    Contains all information needed to determine and execute
    the appropriate retrieval strategy.
    """

    # Query information
    query: str = ""
    query_pattern: str = "default"  # From QueryClassifier

    # Context information
    project_id: Optional[str] = None
    session_id: Optional[UUID] = None
    agent_id: Optional[str] = None

    # Agent state
    agent_uncertainty: float = 0.5  # 0.0 = certain, 1.0 = uncertain

    # Time context
    time_window_days: int = 7  # For temporal queries
    reference_time: datetime = field(default_factory=datetime.utcnow)

    # Entity context (extracted from query)
    entities: list[str] = field(default_factory=list)

    # Explicit strategy override (if any)
    strategy_override: Optional[RetrievalStrategy] = None


# =============================================================================
# Strategy Result
# =============================================================================


@dataclass
class StrategyResult:
    """
    Result from strategy-based retrieval.
    """

    strategy: RetrievalStrategy
    results: list[dict[str, Any]] = field(default_factory=list)

    # Metadata
    query: str = ""
    total_results: int = 0
    execution_time_ms: float = 0.0

    # Context used
    context: Optional[StrategyContext] = None

    # Explanation of why this strategy was chosen
    strategy_reason: str = ""


# =============================================================================
# Strategy Determiner
# =============================================================================


class StrategyDeterminer:
    """
    Determines the optimal retrieval strategy based on query and context.

    Maps query patterns (from QueryClassifier) to frontier retrieval strategies,
    considering context like project scope, agent uncertainty, and time relevance.
    """

    # Query pattern to strategy mapping
    PATTERN_STRATEGY_MAP = {
        # Identity-related patterns
        "entity_lookup": RetrievalStrategy.CORE_IDENTITY,
        "factual": RetrievalStrategy.SEMANTIC_SEARCH,
        # Temporal patterns
        "temporal": RetrievalStrategy.TEMPORAL_RECALL,
        "reasoning_trace": RetrievalStrategy.TEMPORAL_RECALL,
        # Exploratory patterns (use association)
        "exploratory": RetrievalStrategy.ASSOCIATION,
        # Default fallback
        "default": RetrievalStrategy.SEMANTIC_SEARCH,
    }

    # Identity trigger keywords
    IDENTITY_KEYWORDS = [
        "preference",
        "prefer",
        "value",
        "goal",
        "identity",
        "who am i",
        "what do i",
        "my style",
        "i like",
        "i want",
        "always",
        "never",
        "principle",
        "belief",
        "core",
    ]

    # Project context trigger keywords
    PROJECT_KEYWORDS = [
        "project",
        "current work",
        "this task",
        "our goal",
        "scope",
        "requirement",
        "specification",
        "constraint",
    ]

    # Temporal trigger keywords
    TEMPORAL_KEYWORDS = [
        "recent",
        "last",
        "yesterday",
        "today",
        "this week",
        "when did",
        "what happened",
        "history",
        "before",
        "after",
    ]

    def __init__(self):
        """Initialize strategy determiner."""
        logger.info("StrategyDeterminer initialized")

    def determine_strategy(
        self,
        context: StrategyContext,
    ) -> tuple[RetrievalStrategy, str]:
        """
        Determine the optimal retrieval strategy.

        Args:
            context: StrategyContext with query and context information

        Returns:
            Tuple of (strategy, reason)
        """
        # Check for explicit override
        if context.strategy_override:
            return context.strategy_override, "Explicit strategy override"

        query_lower = context.query.lower()

        # Check for identity keywords first (highest priority)
        if self._has_identity_keywords(query_lower):
            return (
                RetrievalStrategy.CORE_IDENTITY,
                "Query contains identity/preference keywords",
            )

        # Check for high uncertainty (agent needs confident facts)
        if context.agent_uncertainty > 0.7:
            return (
                RetrievalStrategy.UNCERTAINTY_FILL,
                f"High agent uncertainty ({context.agent_uncertainty:.1%})",
            )

        # Check for project context keywords
        if context.project_id and self._has_project_keywords(query_lower):
            return (
                RetrievalStrategy.PROJECT_CONTEXT,
                f"Project-scoped query (project: {context.project_id})",
            )

        # Check for temporal keywords
        if self._has_temporal_keywords(query_lower):
            return RetrievalStrategy.TEMPORAL_RECALL, "Query contains temporal keywords"

        # Use pattern-based mapping
        pattern = context.query_pattern
        strategy = self.PATTERN_STRATEGY_MAP.get(
            pattern, RetrievalStrategy.SEMANTIC_SEARCH
        )
        reason = f"Based on query pattern: {pattern}"

        # Override to association for exploratory patterns with entities
        if pattern == "exploratory" and context.entities:
            strategy = RetrievalStrategy.ASSOCIATION
            reason = f"Exploratory query with entities: {context.entities}"

        return strategy, reason

    def _has_identity_keywords(self, query: str) -> bool:
        """Check if query contains identity-related keywords."""
        return any(kw in query for kw in self.IDENTITY_KEYWORDS)

    def _has_project_keywords(self, query: str) -> bool:
        """Check if query contains project context keywords."""
        return any(kw in query for kw in self.PROJECT_KEYWORDS)

    def _has_temporal_keywords(self, query: str) -> bool:
        """Check if query contains temporal keywords."""
        return any(kw in query for kw in self.TEMPORAL_KEYWORDS)


# =============================================================================
# Strategy-Based Retriever
# =============================================================================


class StrategyBasedRetriever:
    """
    Executes strategy-based retrieval using the determined strategy.

    This is the main entry point for frontier-grade retrieval.
    Instead of simple vector search, it:
    1. Analyzes the query to determine intent
    2. Selects the optimal retrieval strategy
    3. Executes strategy-specific retrieval
    4. Ranks results using multi-factor scoring
    """

    def __init__(
        self,
        repository=None,
        identity_service=None,
        strategy_determiner: Optional[StrategyDeterminer] = None,
    ):
        """
        Initialize StrategyBasedRetriever.

        Args:
            repository: SubstrateRepository instance
            identity_service: IdentityTierService instance
            strategy_determiner: Optional custom strategy determiner
        """
        self._repository = repository
        self._identity_service = identity_service
        self._strategy_determiner = strategy_determiner or StrategyDeterminer()
        logger.info("StrategyBasedRetriever initialized")

    def set_repository(self, repository) -> None:
        """Set or update the repository reference."""
        self._repository = repository

    def set_identity_service(self, service) -> None:
        """Set or update the identity service reference."""
        self._identity_service = service

    # =========================================================================
    # Main Entry Point
    # =========================================================================

    async def retrieve(
        self,
        query: str,
        context: Optional[StrategyContext] = None,
        max_results: int = 10,
    ) -> StrategyResult:
        """
        Execute strategy-based retrieval.

        This is the main entry point for frontier-grade retrieval.

        Args:
            query: Natural language query
            context: Optional StrategyContext (will create default if not provided)
            max_results: Maximum results to return

        Returns:
            StrategyResult with retrieved items and metadata
        """
        start_time = datetime.utcnow()

        # Create context if not provided
        if context is None:
            context = StrategyContext(query=query)
        else:
            context.query = query

        # Determine strategy
        strategy, reason = self._strategy_determiner.determine_strategy(context)
        logger.info(f"Strategy determined: {strategy.value} - {reason}")

        # Execute strategy
        results = await self._execute_strategy(strategy, context, max_results)

        # Calculate execution time
        execution_time_ms = (datetime.utcnow() - start_time).total_seconds() * 1000

        return StrategyResult(
            strategy=strategy,
            results=results,
            query=query,
            total_results=len(results),
            execution_time_ms=execution_time_ms,
            context=context,
            strategy_reason=reason,
        )

    # =========================================================================
    # Strategy Execution
    # =========================================================================

    async def _execute_strategy(
        self,
        strategy: RetrievalStrategy,
        context: StrategyContext,
        max_results: int,
    ) -> list[dict[str, Any]]:
        """Execute the determined strategy."""

        if strategy == RetrievalStrategy.CORE_IDENTITY:
            return await self._execute_core_identity(context, max_results)

        elif strategy == RetrievalStrategy.PROJECT_CONTEXT:
            return await self._execute_project_context(context, max_results)

        elif strategy == RetrievalStrategy.TEMPORAL_RECALL:
            return await self._execute_temporal_recall(context, max_results)

        elif strategy == RetrievalStrategy.ASSOCIATION:
            return await self._execute_association(context, max_results)

        elif strategy == RetrievalStrategy.UNCERTAINTY_FILL:
            return await self._execute_uncertainty_fill(context, max_results)

        else:  # SEMANTIC_SEARCH (fallback)
            return await self._execute_semantic_search(context, max_results)

    async def _execute_core_identity(
        self,
        context: StrategyContext,
        max_results: int,
    ) -> list[dict[str, Any]]:
        """
        Execute CORE_IDENTITY strategy.

        Retrieves identity tier facts (values, preferences, goals).
        No similarity threshold - just get the facts.
        """
        logger.debug("Executing CORE_IDENTITY strategy")

        if self._identity_service:
            facts = await self._identity_service.get_identity_facts(limit=max_results)
            return [
                {
                    "fact_id": str(f.fact_id),
                    "fact_text": f.fact_text,
                    "tier": "identity",
                    "importance": f.importance,
                    "tags": f.tags,
                    "source": "identity_tier",
                    "strategy": RetrievalStrategy.CORE_IDENTITY.value,
                }
                for f in facts
            ]

        # Fallback to repository
        if self._repository:
            facts = await self._repository.get_semantic_facts_by_tier(
                tier="identity",
                limit=max_results,
            )
            return [
                {
                    "fact_id": str(f.fact_id),
                    "fact_text": f.fact_text,
                    "tier": "identity",
                    "importance": f.importance,
                    "tags": f.tags,
                    "strategy": RetrievalStrategy.CORE_IDENTITY.value,
                }
                for f in facts
            ]

        return []

    async def _execute_project_context(
        self,
        context: StrategyContext,
        max_results: int,
    ) -> list[dict[str, Any]]:
        """
        Execute PROJECT_CONTEXT strategy.

        Retrieves project-scoped facts from Tier 2.
        """
        logger.debug(
            f"Executing PROJECT_CONTEXT strategy: project={context.project_id}"
        )

        if not self._repository:
            return []

        # Get project tier facts
        facts = await self._repository.get_semantic_facts_by_tier(
            tier="project",
            limit=max_results * 2,  # Get more to filter
        )

        # Filter by project_id if specified
        if context.project_id:
            facts = [f for f in facts if context.project_id in f.tags or not f.tags]

        return [
            {
                "fact_id": str(f.fact_id),
                "fact_text": f.fact_text,
                "tier": "project",
                "importance": f.importance,
                "tags": f.tags,
                "project_id": context.project_id,
                "strategy": RetrievalStrategy.PROJECT_CONTEXT.value,
            }
            for f in facts[:max_results]
        ]

    async def _execute_temporal_recall(
        self,
        context: StrategyContext,
        max_results: int,
    ) -> list[dict[str, Any]]:
        """
        Execute TEMPORAL_RECALL strategy.

        Retrieves recent episodes by time range.
        """
        logger.debug(
            f"Executing TEMPORAL_RECALL strategy: window={context.time_window_days}d"
        )

        if not self._repository:
            return []

        # Calculate time range
        end_time = context.reference_time
        start_time = end_time - timedelta(days=context.time_window_days)

        # Get events in time range
        events = await self._repository.get_events_by_time_range(
            start_time=start_time,
            end_time=end_time,
            entities=context.entities if context.entities else None,
            limit=max_results,
        )

        return [
            {
                "event_id": str(e.event_id),
                "observation": e.observation,
                "event_timestamp": e.event_timestamp.isoformat()
                if e.event_timestamp
                else None,
                "entities": e.entities,
                "severity": e.severity,
                "strategy": RetrievalStrategy.TEMPORAL_RECALL.value,
            }
            for e in events
        ]

    async def _execute_association(
        self,
        context: StrategyContext,
        max_results: int,
    ) -> list[dict[str, Any]]:
        """
        Execute ASSOCIATION strategy.

        Finds linked facts + episodes via graph traversal.
        """
        logger.debug(f"Executing ASSOCIATION strategy: entities={context.entities}")

        if not self._repository:
            return []

        results = []

        # First get semantic facts matching query terms
        if context.entities:
            for entity in context.entities[:3]:  # Limit entity queries
                facts = await self._repository.get_semantic_facts_by_subject(
                    subject=entity,
                    limit=max_results // 2,
                )

                for fact in facts:
                    # Get linked episodes for each fact
                    episodes = await self._repository.get_events_for_fact(
                        fact_id=fact.fact_id,
                        limit=3,
                    )

                    results.append(
                        {
                            "fact_id": str(fact.fact_id),
                            "fact_text": fact.fact_text,
                            "tier": fact.tier,
                            "importance": fact.importance,
                            "linked_episodes": [
                                {
                                    "event_id": str(e.event_id),
                                    "observation": e.observation,
                                    "event_timestamp": e.event_timestamp.isoformat()
                                    if e.event_timestamp
                                    else None,
                                }
                                for e in episodes
                            ],
                            "strategy": RetrievalStrategy.ASSOCIATION.value,
                        }
                    )

        # Fallback to tier search if no entities
        if not results:
            facts = await self._repository.get_semantic_facts_by_tier(
                tier="general",
                limit=max_results,
            )
            results = [
                {
                    "fact_id": str(f.fact_id),
                    "fact_text": f.fact_text,
                    "tier": f.tier,
                    "importance": f.importance,
                    "linked_episodes": [],
                    "strategy": RetrievalStrategy.ASSOCIATION.value,
                }
                for f in facts
            ]

        return results[:max_results]

    async def _execute_uncertainty_fill(
        self,
        context: StrategyContext,
        max_results: int,
    ) -> list[dict[str, Any]]:
        """
        Execute UNCERTAINTY_FILL strategy.

        Retrieves highest-confidence facts to reduce agent uncertainty.
        """
        logger.debug(
            f"Executing UNCERTAINTY_FILL strategy: uncertainty={context.agent_uncertainty}"
        )

        if not self._repository:
            return []

        # Get high-importance facts from all tiers
        results = []

        for tier in ["identity", "project", "session", "general"]:
            facts = await self._repository.get_semantic_facts_by_tier(
                tier=tier,
                limit=max_results,
            )

            # Filter by high importance (> 0.7)
            high_importance_facts = [f for f in facts if f.importance >= 0.7]

            for f in high_importance_facts:
                results.append(
                    {
                        "fact_id": str(f.fact_id),
                        "fact_text": f.fact_text,
                        "tier": f.tier,
                        "importance": f.importance,
                        "confidence": f.confidence,
                        "strategy": RetrievalStrategy.UNCERTAINTY_FILL.value,
                    }
                )

        # Sort by importance descending
        results.sort(key=lambda x: x["importance"], reverse=True)

        return results[:max_results]

    async def _execute_semantic_search(
        self,
        context: StrategyContext,
        max_results: int,
    ) -> list[dict[str, Any]]:
        """
        Execute SEMANTIC_SEARCH strategy (fallback).

        Standard semantic similarity search across all tiers.
        """
        logger.debug("Executing SEMANTIC_SEARCH strategy (fallback)")

        if not self._repository:
            return []

        # Simple search across tiers by importance
        results = []

        for tier in ["identity", "project", "session", "general"]:
            facts = await self._repository.get_semantic_facts_by_tier(
                tier=tier,
                limit=max_results // 4,
            )

            for f in facts:
                # Simple term matching score
                query_terms = set(context.query.lower().split())
                fact_terms = set(f.fact_text.lower().split())
                overlap = len(query_terms & fact_terms)

                if overlap > 0 or tier == "identity":  # Always include identity
                    score = (
                        overlap / max(len(query_terms), 1)
                    ) * 0.7 + f.importance * 0.3

                    results.append(
                        {
                            "fact_id": str(f.fact_id),
                            "fact_text": f.fact_text,
                            "tier": f.tier,
                            "importance": f.importance,
                            "relevance_score": round(score, 3),
                            "strategy": RetrievalStrategy.SEMANTIC_SEARCH.value,
                        }
                    )

        # Sort by relevance score
        results.sort(key=lambda x: x.get("relevance_score", 0), reverse=True)

        return results[:max_results]


# =============================================================================
# Singleton / Factory
# =============================================================================


_strategy_retriever: Optional[StrategyBasedRetriever] = None


def get_strategy_retriever() -> StrategyBasedRetriever:
    """Get or create the StrategyBasedRetriever singleton."""
    global _strategy_retriever
    if _strategy_retriever is None:
        _strategy_retriever = StrategyBasedRetriever()
    return _strategy_retriever


def init_strategy_retriever(
    repository,
    identity_service=None,
) -> StrategyBasedRetriever:
    """Initialize the StrategyBasedRetriever with dependencies."""
    retriever = get_strategy_retriever()
    retriever.set_repository(repository)
    if identity_service:
        retriever.set_identity_service(identity_service)
    return retriever
