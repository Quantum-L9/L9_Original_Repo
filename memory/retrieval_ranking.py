"""
L9 Memory Substrate - Multi-Factor Retrieval Ranking
Version: 3.1.0

Implements frontier-grade multi-factor ranking for memory retrieval.
Instead of ranking by similarity alone, uses multiple factors:
- similarity: Semantic closeness to query
- recency: How recent the item is
- importance: User-curated importance score
- frequency: How often retrieved before
- uncertainty: Does agent need this to reduce uncertainty?

Based on frontier AI lab patterns (Anthropic, OpenAI, DeepMind).
"""

from __future__ import annotations

# ============================================================================
__dora_meta__ = {
    "component_name": "Multi-Factor Retrieval Ranking",
    "module_version": "3.1.0",
    "created_by": "Igor Beylin",
    "created_at": "2026-01-15T15:23:54Z",
    "updated_at": "2026-01-17T23:47:56Z",
    "layer": "learning",
    "domain": "memory_substrate",
    "module_name": "retrieval_ranking",
    "type": "dataclass",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": ["Anthropic API", "OpenAI API"],
        "memory_layers": [],
        "imported_by": [
            "memory.retrieval",
            "tests.memory.test_frontier_memory_pipeline",
        ],
    },
}
# ============================================================================

import math
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

import structlog

logger = structlog.get_logger(__name__)


# =============================================================================
# Default Ranking Weights
# =============================================================================


@dataclass(frozen=True)
class RankingWeights:
    """
    Configurable weights for multi-factor ranking.

    Weights should sum to 1.0 for normalized scoring.
    """

    similarity: float = 0.30  # Semantic closeness
    recency: float = 0.20  # How recent
    importance: float = 0.25  # User-curated importance
    frequency: float = 0.15  # How often retrieved
    uncertainty: float = 0.10  # Agent uncertainty factor

    # Extended weights (Phase 2 wiring E4) — only active when fields are present
    importance_weight: float = 0.15  # ImportanceManager-managed score blend
    salience_weight: float = 0.10  # NeuralDecayScheduler salience blend

    def __post_init__(self):
        """Validate base weights sum to approximately 1.0."""
        total = (
            self.similarity
            + self.recency
            + self.importance
            + self.frequency
            + self.uncertainty
        )
        if not (0.99 <= total <= 1.01):
            logger.warning(f"Ranking weights sum to {total}, expected ~1.0")

    def to_dict(self) -> dict[str, float]:
        """Convert to dictionary."""
        return {
            "similarity": self.similarity,
            "recency": self.recency,
            "importance": self.importance,
            "frequency": self.frequency,
            "uncertainty": self.uncertainty,
            "importance_weight": self.importance_weight,
            "salience_weight": self.salience_weight,
        }


# Preset weight configurations
WEIGHT_PRESETS = {
    "balanced": RankingWeights(
        similarity=0.30,
        recency=0.20,
        importance=0.25,
        frequency=0.15,
        uncertainty=0.10,
    ),
    "recency_focused": RankingWeights(
        similarity=0.20,
        recency=0.40,
        importance=0.20,
        frequency=0.10,
        uncertainty=0.10,
    ),
    "importance_focused": RankingWeights(
        similarity=0.20,
        recency=0.15,
        importance=0.40,
        frequency=0.15,
        uncertainty=0.10,
    ),
    "similarity_focused": RankingWeights(
        similarity=0.50,
        recency=0.15,
        importance=0.15,
        frequency=0.10,
        uncertainty=0.10,
    ),
    "uncertainty_aware": RankingWeights(
        similarity=0.25,
        recency=0.15,
        importance=0.20,
        frequency=0.10,
        uncertainty=0.30,
    ),
}


# =============================================================================
# Ranking Item
# =============================================================================


@dataclass
class RankingItem:
    """
    An item to be ranked with all factor scores.
    """

    # Item identification
    item_id: str
    item_type: str = "fact"  # fact, event, packet
    content: str = ""

    # Raw factor values
    similarity_score: float = 0.0  # 0.0-1.0
    timestamp: datetime | None = None  # For recency calculation
    importance: float = 0.5  # 0.0-1.0
    access_count: int = 0  # For frequency calculation

    # Computed scores
    recency_score: float = 0.0  # Computed from timestamp
    frequency_score: float = 0.0  # Computed from access_count
    uncertainty_score: float = 0.0  # Based on agent need

    # Extended ranking fields (Phase 2 wiring E4)
    # Both default to None for backward compatibility — existing callers unaffected
    importance_score: float | None = None  # ImportanceManager-managed score
    decayed_salience: float | None = None  # NeuralDecayScheduler salience

    # Final score
    final_score: float = 0.0

    # Metadata
    metadata: dict[str, Any] = field(default_factory=dict)


# =============================================================================
# Multi-Factor Ranker
# =============================================================================


class MultiFactorRanker:
    """
    Ranks retrieval results using multiple factors.

    This replaces simple similarity-based ranking with a
    multi-dimensional scoring approach that considers:
    - Semantic relevance
    - Temporal relevance
    - User-defined importance
    - Usage patterns
    - Agent uncertainty
    """

    def __init__(
        self,
        weights: RankingWeights | None = None,
        recency_half_life_days: float = 30.0,
        frequency_scale: float = 10.0,
    ):
        """
        Initialize MultiFactorRanker.

        Args:
            weights: Ranking weights configuration
            recency_half_life_days: Half-life for recency decay
            frequency_scale: Scale factor for frequency normalization
        """
        self._weights = weights or WEIGHT_PRESETS["balanced"]
        self._recency_half_life_days = recency_half_life_days
        self._frequency_scale = frequency_scale
        logger.info("MultiFactorRanker initialized", weights=self._weights.to_dict())

    def set_weights(self, weights: RankingWeights) -> None:
        """Update ranking weights."""
        self._weights = weights
        logger.info("Ranking weights updated", weights=self._weights.to_dict())

    def use_preset(self, preset_name: str) -> None:
        """Use a preset weight configuration."""
        if preset_name in WEIGHT_PRESETS:
            self._weights = WEIGHT_PRESETS[preset_name]
            logger.info(f"Using weight preset: {preset_name}")
        else:
            logger.warning(f"Unknown preset: {preset_name}, using balanced")
            self._weights = WEIGHT_PRESETS["balanced"]

    # =========================================================================
    # Ranking Methods
    # =========================================================================

    def rank(
        self,
        items: list[RankingItem],
        agent_uncertainty: float = 0.5,
        reference_time: datetime | None = None,
    ) -> list[RankingItem]:
        """
        Rank items using multi-factor scoring.

        Args:
            items: List of RankingItems to rank
            agent_uncertainty: Agent's uncertainty level (0.0-1.0)
            reference_time: Reference time for recency calculation

        Returns:
            Sorted list of RankingItems (highest score first)
        """
        if not items:
            return []

        if reference_time is None:
            reference_time = datetime.now(UTC)

        # Compute scores for each item
        for item in items:
            item.recency_score = self._compute_recency_score(
                item.timestamp, reference_time
            )
            item.frequency_score = self._compute_frequency_score(item.access_count)
            item.uncertainty_score = self._compute_uncertainty_score(
                item, agent_uncertainty
            )
            item.final_score = self._compute_final_score(item)

        # Sort by final score (descending)
        ranked = sorted(items, key=lambda x: x.final_score, reverse=True)

        logger.debug(f"Ranked {len(ranked)} items")
        return ranked

    def rank_dicts(
        self,
        items: list[dict[str, Any]],
        agent_uncertainty: float = 0.5,
        reference_time: datetime | None = None,
    ) -> list[dict[str, Any]]:
        """
        Rank dictionaries using multi-factor scoring.

        Convenience method for ranking raw dict results.

        Args:
            items: List of dicts with scoring fields
            agent_uncertainty: Agent's uncertainty level
            reference_time: Reference time for recency

        Returns:
            Sorted list of dicts with added ranking fields
        """
        # Convert dicts to RankingItems
        ranking_items = []
        for item in items:
            ranking_item = RankingItem(
                item_id=str(
                    item.get("fact_id") or item.get("event_id") or item.get("id", "")
                ),
                item_type=item.get("type", "fact"),
                content=item.get("fact_text")
                or item.get("observation")
                or item.get("content", ""),
                similarity_score=item.get("similarity_score")
                or item.get("relevance_score")
                or item.get("score", 0.0),
                timestamp=self._parse_timestamp(
                    item.get("timestamp")
                    or item.get("event_timestamp")
                    or item.get("created_at")
                ),
                importance=item.get("importance", 0.5),
                access_count=item.get("access_count", 0),
                metadata=item,
            )
            ranking_items.append(ranking_item)

        # Rank
        ranked = self.rank(ranking_items, agent_uncertainty, reference_time)

        # Convert back to dicts with added fields
        results: list[dict[str, Any]] = []
        for ranked_item in ranked:
            result = dict(ranked_item.metadata)
            result["ranking"] = {
                "final_score": round(ranked_item.final_score, 4),
                "recency_score": round(ranked_item.recency_score, 4),
                "frequency_score": round(ranked_item.frequency_score, 4),
                "uncertainty_score": round(ranked_item.uncertainty_score, 4),
            }
            results.append(result)

        return results

    # =========================================================================
    # Score Computation
    # =========================================================================

    def _compute_recency_score(
        self,
        timestamp: datetime | None,
        reference_time: datetime,
    ) -> float:
        """
        Compute recency score using exponential decay.

        Recent items score higher, with exponential decay based on half-life.
        """
        if timestamp is None:
            return 0.5  # Default middle score for items without timestamp

        age_days = (reference_time - timestamp).total_seconds() / 86400.0

        if age_days < 0:
            return 1.0  # Future timestamp = fresh

        # Exponential decay: 2^(-age/half_life)
        decay = math.pow(2, -age_days / self._recency_half_life_days)
        return max(0.0, min(1.0, decay))

    def _compute_frequency_score(self, access_count: int) -> float:
        """
        Compute frequency score using logarithmic scaling.

        More frequently accessed items score higher, but with
        diminishing returns (log scale).
        """
        if access_count <= 0:
            return 0.0

        # Log scaling: log(1 + count) / log(1 + scale)
        score = math.log(1 + access_count) / math.log(1 + self._frequency_scale)
        return max(0.0, min(1.0, score))

    def _compute_uncertainty_score(
        self,
        item: RankingItem,
        agent_uncertainty: float,
    ) -> float:
        """
        Compute uncertainty-based score.

        When agent uncertainty is high, favor high-confidence/important items.
        When uncertainty is low, this factor has minimal impact.
        """
        # High uncertainty + high importance = boost
        # Low uncertainty = all items similar score
        importance_factor = item.importance
        uncertainty_multiplier = agent_uncertainty  # 0.0-1.0

        # Score is higher for important items when uncertainty is high
        return importance_factor * uncertainty_multiplier

    def _compute_final_score(self, item: RankingItem) -> float:
        """
        Compute final weighted score from all factors.

        When importance_score and/or decayed_salience are present on the item
        (Phase 2 wiring E4), they are blended into the final score using
        importance_weight and salience_weight. The existing base score is
        scaled down proportionally so the total remains in [0, 1].

        When the extended fields are None, the formula is mathematically
        identical to the original — zero regression.
        """
        w = self._weights

        base_score = (
            w.similarity * item.similarity_score
            + w.recency * item.recency_score
            + w.importance * item.importance
            + w.frequency * item.frequency_score
            + w.uncertainty * item.uncertainty_score
        )

        # Phase 2 wiring E4: blend extended fields when present
        iw = w.importance_weight if item.importance_score is not None else 0.0
        sw = w.salience_weight if item.decayed_salience is not None else 0.0
        extended_total = iw + sw

        if extended_total > 0.0:
            # Scale base down to make room for extended signals
            scale = 1.0 - extended_total
            score = (
                base_score * scale
                + (item.importance_score or 0.0) * iw
                + (item.decayed_salience or 0.0) * sw
            )
        else:
            score = base_score

        return max(0.0, min(1.0, score))

    def _parse_timestamp(self, value: Any) -> datetime | None:
        """Parse timestamp from various formats."""
        if value is None:
            return None

        if isinstance(value, datetime):
            return value

        if isinstance(value, str):
            try:
                # Try ISO format
                return datetime.fromisoformat(value.replace("Z", "+00:00"))
            except ValueError:
                pass

        return None

    # =========================================================================
    # Utility Methods
    # =========================================================================

    def explain_ranking(self, item: RankingItem) -> dict[str, Any]:
        """
        Get explanation of how an item was ranked.

        Useful for debugging and transparency.
        """
        w = self._weights

        return {
            "item_id": item.item_id,
            "final_score": round(item.final_score, 4),
            "factor_contributions": {
                "similarity": {
                    "weight": w.similarity,
                    "score": round(item.similarity_score, 4),
                    "contribution": round(w.similarity * item.similarity_score, 4),
                },
                "recency": {
                    "weight": w.recency,
                    "score": round(item.recency_score, 4),
                    "contribution": round(w.recency * item.recency_score, 4),
                },
                "importance": {
                    "weight": w.importance,
                    "score": round(item.importance, 4),
                    "contribution": round(w.importance * item.importance, 4),
                },
                "frequency": {
                    "weight": w.frequency,
                    "score": round(item.frequency_score, 4),
                    "contribution": round(w.frequency * item.frequency_score, 4),
                },
                "uncertainty": {
                    "weight": w.uncertainty,
                    "score": round(item.uncertainty_score, 4),
                    "contribution": round(w.uncertainty * item.uncertainty_score, 4),
                },
            },
        }


# =============================================================================
# Singleton / Factory
# =============================================================================


_ranker: MultiFactorRanker | None = None


def get_multi_factor_ranker() -> MultiFactorRanker:
    """Get or create the MultiFactorRanker singleton."""
    global _ranker
    if _ranker is None:
        _ranker = MultiFactorRanker()
    return _ranker


def create_ranker_with_preset(preset_name: str) -> MultiFactorRanker:
    """Create a ranker with a specific weight preset."""
    weights = WEIGHT_PRESETS.get(preset_name, WEIGHT_PRESETS["balanced"])
    return MultiFactorRanker(weights=weights)


# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "MEM-LEAR-015",
    "governance_level": "critical",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": [
        "dataclass",
        "debugging",
        "event-driven",
        "learning",
        "logging",
        "memory-substrate",
    ],
    "keywords": [
        "agent",
        "create",
        "dicts",
        "explain",
        "factor",
        "frontier",
        "importance",
        "memory",
    ],
    "business_value": "Implements frontier-grade multi-factor ranking for memory retrieval. similarity: Semantic closeness to query recency: How recent the item is importance: User-curated importance score frequency: How of",
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
