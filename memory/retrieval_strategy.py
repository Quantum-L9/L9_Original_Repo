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

# ============================================================================
__dora_meta__ = {
    "component_name": "Strategy-Based Retrieval",
    "module_version": "3.1.0",
    "created_by": "Igor Beylin",
    "created_at": "2026-01-15T15:23:54Z",
    "updated_at": "2026-01-17T23:47:56Z",
    "layer": "learning",
    "domain": "data_models",
    "module_name": "retrieval_strategy",
    "type": "dataclass",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": ["Anthropic API", "OpenAI API"],
        "memory_layers": ["semantic_memory"],
        "imported_by": [
            "memory.retrieval",
            "tests.memory.test_frontier_memory_pipeline",
        ],
    },
}
# ============================================================================

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import TYPE_CHECKING, Any
from uuid import UUID

import structlog

if TYPE_CHECKING:
    from memory.identity_tier import IdentityTierService
    from memory.substrate_repository import SubstrateRepository

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
    project_id: str | None = None
    session_id: UUID | None = None
    agent_id: str | None = None

    # Agent state
    agent_uncertainty: float = 0.5  # 0.0 = certain, 1.0 = uncertain

    # Time context
    time_window_days: int = 7  # For temporal queries
    reference_time: datetime = field(default_factory=datetime.utcnow)

    # Entity context (extracted from query)
    entities: list[str] = field(default_factory=list)

    # Explicit strategy override (if any)
    strategy_override: RetrievalStrategy | None = None


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
    context: StrategyContext | None = None

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
        repository: SubstrateRepository | None = None,
        identity_service: IdentityTierService | None = None,
        strategy_determiner: StrategyDeterminer | None = None,
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

    def set_repository(self, repository: SubstrateRepository) -> None:
        """Set or update the repository reference."""
        self._repository = repository

    def set_identity_service(self, service: IdentityTierService) -> None:
        """Set or update the identity service reference."""
        self._identity_service = service

    # =========================================================================
    # Main Entry Point
    # =========================================================================

    async def retrieve(
        self,
        query: str,
        context: StrategyContext | None = None,
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
        start_time = datetime.now(timezone.utc)

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
        execution_time_ms = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000

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

        if strategy == RetrievalStrategy.PROJECT_CONTEXT:
            return await self._execute_project_context(context, max_results)

        if strategy == RetrievalStrategy.TEMPORAL_RECALL:
            return await self._execute_temporal_recall(context, max_results)

        if strategy == RetrievalStrategy.ASSOCIATION:
            return await self._execute_association(context, max_results)

        if strategy == RetrievalStrategy.UNCERTAINTY_FILL:
            return await self._execute_uncertainty_fill(context, max_results)

        # SEMANTIC_SEARCH (fallback)
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
                "event_timestamp": (
                    e.event_timestamp.isoformat() if e.event_timestamp else None
                ),
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
                                    "event_timestamp": (
                                        e.event_timestamp.isoformat()
                                        if e.event_timestamp
                                        else None
                                    ),
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
        Execute UNCERTAINTY_FILL strategy (Enhanced v3.2).

        Smart retrieval based on what the agent is *actually* uncertain about.
        Uses topic-specific retrieval and dynamic importance thresholds.

        Features:
        - Topic-aware: Uses query entities to find relevant facts
        - Dynamic thresholds: Adjusts importance filter based on uncertainty level
        - Contradiction detection: Flags conflicting facts
        - Tier priority: Identity > Project > Session > General
        """
        logger.debug(
            f"Executing UNCERTAINTY_FILL strategy: "
            f"uncertainty={context.agent_uncertainty}, "
            f"entities={context.entities}, "
            f"query='{context.query[:50]}...'"
        )

        if not self._repository:
            return []

        # Dynamic importance threshold based on uncertainty level
        # High uncertainty (0.9) → accept lower confidence facts (0.5)
        # Low uncertainty (0.3) → require high confidence facts (0.8)
        importance_threshold = max(0.5, 0.9 - (context.agent_uncertainty * 0.4))
        logger.debug(f"Dynamic importance threshold: {importance_threshold:.2f}")

        results = []
        seen_fact_texts = set()  # For contradiction detection

        # Phase 1: Topic-specific retrieval (if entities available)
        if context.entities and self._repository:
            for entity in context.entities[:5]:  # Limit to 5 entities
                # Search by subject in triplets
                facts = await self._repository.get_semantic_facts_by_subject(
                    subject=entity,
                    limit=max_results,
                )

                for f in facts:
                    if f.importance >= importance_threshold:
                        # Check for potential contradictions
                        fact_key = f.fact_text.lower().strip()
                        is_potential_contradiction = any(
                            self._facts_may_contradict(fact_key, seen)
                            for seen in seen_fact_texts
                        )
                        seen_fact_texts.add(fact_key)

                        results.append(
                            {
                                "fact_id": str(f.fact_id),
                                "fact_text": f.fact_text,
                                "tier": f.tier,
                                "importance": f.importance,
                                "confidence": f.confidence,
                                "matched_entity": entity,
                                "potential_contradiction": is_potential_contradiction,
                                "strategy": RetrievalStrategy.UNCERTAINTY_FILL.value,
                                "retrieval_reason": "topic_match",
                            }
                        )

        # Phase 2: Tier-based retrieval (prioritized by tier importance)
        tier_priority = ["identity", "project", "session", "general"]
        tier_weights = {"identity": 1.0, "project": 0.9, "session": 0.8, "general": 0.7}

        for tier in tier_priority:
            if len(results) >= max_results * 2:
                break  # Have enough candidates

            facts = await self._repository.get_semantic_facts_by_tier(
                tier=tier,
                limit=max_results,
            )

            # Apply dynamic threshold
            high_importance_facts = [
                f for f in facts if f.importance >= importance_threshold
            ]

            for f in high_importance_facts:
                # Skip if already added via topic search
                if any(r["fact_id"] == str(f.fact_id) for r in results):
                    continue

                # Check for potential contradictions
                fact_key = f.fact_text.lower().strip()
                is_potential_contradiction = any(
                    self._facts_may_contradict(fact_key, seen)
                    for seen in seen_fact_texts
                )
                seen_fact_texts.add(fact_key)

                # Apply tier weight to importance for ranking
                weighted_importance = f.importance * tier_weights.get(tier, 0.7)

                results.append(
                    {
                        "fact_id": str(f.fact_id),
                        "fact_text": f.fact_text,
                        "tier": f.tier,
                        "importance": f.importance,
                        "weighted_importance": weighted_importance,
                        "confidence": f.confidence,
                        "potential_contradiction": is_potential_contradiction,
                        "strategy": RetrievalStrategy.UNCERTAINTY_FILL.value,
                        "retrieval_reason": "tier_search",
                    }
                )

        # Sort by: topic matches first, then weighted importance
        results.sort(
            key=lambda x: (
                x.get("retrieval_reason") == "topic_match",  # Topic matches first
                x.get("weighted_importance", x["importance"]),  # Then by importance
            ),
            reverse=True,
        )

        # Flag any contradictions found
        contradictions = [r for r in results if r.get("potential_contradiction")]
        if contradictions:
            logger.warning(
                f"UNCERTAINTY_FILL found {len(contradictions)} potential contradictions",
                contradictions=[c["fact_text"][:50] for c in contradictions[:3]],
            )

        return results[:max_results]

    def _facts_may_contradict(self, fact1: str, fact2: str) -> bool:
        """
        Simple heuristic to detect potential contradictions.

        Checks for negation patterns or conflicting assertions about same subject.
        """
        # Negation patterns
        negation_words = {
            "not",
            "never",
            "no",
            "isn't",
            "aren't",
            "doesn't",
            "don't",
            "won't",
            "can't",
        }

        words1 = set(fact1.split())
        words2 = set(fact2.split())

        # Check if one has negation the other doesn't
        has_negation1 = bool(words1 & negation_words)
        has_negation2 = bool(words2 & negation_words)

        if has_negation1 != has_negation2:
            # Check if they share significant words (potential contradiction)
            # Remove common stop words
            stop_words = {
                "is",
                "are",
                "the",
                "a",
                "an",
                "to",
                "of",
                "in",
                "for",
                "on",
                "with",
            }
            significant1 = words1 - stop_words - negation_words
            significant2 = words2 - stop_words - negation_words

            # If they share >50% significant words, might be contradiction
            if significant1 and significant2:
                overlap = len(significant1 & significant2)
                min_len = min(len(significant1), len(significant2))
                if min_len > 0 and overlap / min_len > 0.5:
                    return True

        return False

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


_strategy_retriever: StrategyBasedRetriever | None = None


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


# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "MEM-LEAR-048",
    "governance_level": "high",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": [
        "async",
        "data-models",
        "dataclass",
        "debugging",
        "event-driven",
        "learning",
        "logging",
        "tracing",
    ],
    "keywords": [
        "based",
        "description",
        "determine",
        "determiner",
        "episodes",
        "facts",
        "frontier",
        "identity",
    ],
    "business_value": "Implements frontier-grade strategy-based retrieval that selects the appropriate retrieval approach based on query type and context. core_identity: Retrieve Tier 1 identity facts (values, preferences, ",
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
