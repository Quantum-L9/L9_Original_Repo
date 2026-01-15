"""
L9 Memory - Query Classifier
Version: 1.0.0

Classifies queries into patterns for adaptive retrieval weighting.
Implements memory_spec_v3.0.yaml retrieval.query_classifier contract.

Patterns:
- entity_lookup: "Who is X?", "What is Y?"
- reasoning_trace: "Why did agent decide X?", "Show reasoning for packet Y"
- temporal: "What happened last week?", "Recent changes to X"
- exploratory: "Tell me about X", "Explore Y"
- factual: "What is the value of X?", "Get fact Y"
- default: Fallback pattern
"""

from __future__ import annotations

import structlog
import re
from functools import lru_cache

logger = structlog.get_logger(__name__)


class QueryClassifier:
    """
    Classifies queries into retrieval patterns for adaptive weighting.

    Per memory_spec_v3.0.yaml retrieval.query_classifier:
    - Patterns: entity_lookup, reasoning_trace, temporal, exploratory, factual, default
    - Used by RetrievalPipeline to adjust bundle weights
    """

    def __init__(self):
        """Initialize query classifier with pattern matchers."""
        # Entity lookup patterns
        self._entity_patterns = [
            r"\b(who|what|where|which)\s+(is|are|was|were)\s+",
            r"\b(find|get|show|list)\s+(me\s+)?(the\s+)?(entity|person|thing|object)\s+",
            r"\b(lookup|search)\s+for\s+",
        ]

        # Reasoning trace patterns
        self._reasoning_patterns = [
            r"\b(why|how)\s+(did|does|will)\s+",
            r"\b(show|explain|trace|reconstruct)\s+(me\s+)?(the\s+)?(reasoning|decision|chain|path)",
            r"\b(decision|reasoning|chain)\s+(for|of|about)",
            r"\b(packet|decision)\s+[a-f0-9-]{36}",  # UUID pattern
        ]

        # Temporal patterns
        self._temporal_patterns = [
            r"\b(recent|latest|last|previous|earlier|before|after)\s+",
            r"\b(what|when)\s+happened\s+(last|recent|yesterday|today|this\s+week)",
            r"\b(changes|updates|events)\s+(to|in|for)\s+",
            r"\b(since|until|during|between)\s+",
        ]

        # Exploratory patterns
        self._exploratory_patterns = [
            r"\b(tell\s+me|explore|learn|discover|investigate)\s+(about|more\s+about)?\s+",
            r"\b(what\s+do\s+we\s+know|what\s+can\s+you\s+tell\s+me)\s+",
            r"\b(overview|summary|context)\s+(of|for|about)",
        ]

        # Factual patterns
        self._factual_patterns = [
            r"\b(get|retrieve|fetch|return)\s+(the\s+)?(value|fact|data|info)\s+(of|for)",
            r"\b(what\s+is\s+the\s+value|what\s+is\s+the\s+fact)\s+",
            r"\b(fact|value|data)\s+(about|for|of)",
        ]

        logger.info("QueryClassifier initialized")

    def classify_query(self, query: str) -> str:
        """
        Classify a query into one of the retrieval patterns.

        Args:
            query: Natural language query string

        Returns:
            Pattern name: entity_lookup, reasoning_trace, temporal, exploratory, factual, or default
        """
        if not query or not query.strip():
            return "default"

        query_lower = query.lower().strip()

        # Check patterns in priority order
        # 1. Reasoning trace (most specific)
        for pattern in self._reasoning_patterns:
            if re.search(pattern, query_lower, re.IGNORECASE):
                logger.debug("Query classified as reasoning_trace", query=query[:50])
                return "reasoning_trace"

        # 2. Entity lookup
        for pattern in self._entity_patterns:
            if re.search(pattern, query_lower, re.IGNORECASE):
                logger.debug("Query classified as entity_lookup", query=query[:50])
                return "entity_lookup"

        # 3. Temporal
        for pattern in self._temporal_patterns:
            if re.search(pattern, query_lower, re.IGNORECASE):
                logger.debug("Query classified as temporal", query=query[:50])
                return "temporal"

        # 4. Factual
        for pattern in self._factual_patterns:
            if re.search(pattern, query_lower, re.IGNORECASE):
                logger.debug("Query classified as factual", query=query[:50])
                return "factual"

        # 5. Exploratory
        for pattern in self._exploratory_patterns:
            if re.search(pattern, query_lower, re.IGNORECASE):
                logger.debug("Query classified as exploratory", query=query[:50])
                return "exploratory"

        # 6. Default fallback
        logger.debug("Query classified as default", query=query[:50])
        return "default"

    def get_weight_overrides(self, pattern: str) -> dict[str, float]:
        """
        Get weight overrides for a query pattern.

        Per memory_spec_v3.0.yaml retrieval.bundle weight_range specifications:
        - recent: [0.1, 0.6]
        - semantic_hits: [0.2, 0.5]
        - graph_context: [0.1, 0.5]
        - facts: [0.1, 0.4]

        Args:
            pattern: Query pattern name

        Returns:
            Dict with weight overrides for bundle sources
        """
        # Pattern-specific weight adjustments
        overrides = {
            "entity_lookup": {
                "graph_context": 0.5,  # Higher weight for entity lookups
                "semantic_hits": 0.3,
                "recent": 0.1,
                "facts": 0.1,
            },
            "reasoning_trace": {
                "recent": 0.6,  # Higher weight for recent reasoning
                "graph_context": 0.2,
                "semantic_hits": 0.1,
                "facts": 0.1,
            },
            "temporal": {
                "recent": 0.6,  # Temporal queries favor recent
                "semantic_hits": 0.2,
                "graph_context": 0.1,
                "facts": 0.1,
            },
            "exploratory": {
                "semantic_hits": 0.5,  # Exploratory favors semantic
                "graph_context": 0.3,
                "recent": 0.1,
                "facts": 0.1,
            },
            "factual": {
                "facts": 0.4,  # Factual queries favor facts
                "semantic_hits": 0.3,
                "recent": 0.2,
                "graph_context": 0.1,
            },
            "default": {
                "semantic_hits": 0.4,  # Default balanced
                "recent": 0.3,
                "graph_context": 0.2,
                "facts": 0.1,
            },
        }

        return overrides.get(pattern, overrides["default"])

    # =========================================================================
    # Strategy Determination (GMP-80-A6)
    # =========================================================================

    def determine_retrieval_strategy(
        self,
        query: str,
        context: dict | None = None,
    ) -> tuple[str, str]:
        """
        Determine the optimal retrieval strategy based on query and context.

        Maps query patterns to frontier-grade retrieval strategies:
        - core_identity: Identity tier facts (values, preferences, goals)
        - project_context: Project-scoped facts
        - temporal_recall: Time-based episode retrieval
        - association: Graph-based fact-episode linking
        - uncertainty_fill: High-confidence facts for uncertainty reduction
        - semantic_search: Standard semantic similarity (fallback)

        Args:
            query: Natural language query
            context: Optional context dict with project_id, agent_uncertainty, etc.

        Returns:
            Tuple of (strategy_name, reason)
        """
        context = context or {}
        query_lower = query.lower().strip()

        # First classify the query pattern
        pattern = self.classify_query(query)

        # Identity keywords trigger core_identity strategy
        identity_keywords = [
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
        if any(kw in query_lower for kw in identity_keywords):
            return "core_identity", "Query contains identity/preference keywords"

        # High uncertainty triggers uncertainty_fill
        agent_uncertainty = context.get("agent_uncertainty", 0.5)
        if agent_uncertainty > 0.7:
            return (
                "uncertainty_fill",
                f"High agent uncertainty ({agent_uncertainty:.1%})",
            )

        # Project context keywords with project_id
        project_keywords = [
            "project",
            "current work",
            "this task",
            "scope",
            "requirement",
        ]
        if context.get("project_id") and any(
            kw in query_lower for kw in project_keywords
        ):
            return (
                "project_context",
                f"Project-scoped query (project: {context.get('project_id')})",
            )

        # Pattern-based strategy mapping
        pattern_to_strategy = {
            "entity_lookup": ("core_identity", "Entity lookup maps to identity facts"),
            "reasoning_trace": (
                "temporal_recall",
                "Reasoning trace requires temporal search",
            ),
            "temporal": (
                "temporal_recall",
                "Temporal query requires time-based search",
            ),
            "exploratory": (
                "association",
                "Exploratory query uses graph-based linking",
            ),
            "factual": ("semantic_search", "Factual query uses semantic search"),
            "default": ("semantic_search", "Default fallback to semantic search"),
        }

        strategy, reason = pattern_to_strategy.get(
            pattern, ("semantic_search", "Unknown pattern fallback")
        )

        return strategy, f"{reason} (pattern: {pattern})"


# Singleton instance
@lru_cache(maxsize=1)
def get_query_classifier() -> QueryClassifier:
    """Get singleton QueryClassifier instance. CACHED."""
    return QueryClassifier()
