"""RankingExtensions — importance + decayed-salience inputs for MultiFactorRanker.

Extends the existing ranking system to accept importance_score and
decayed_salience as optional inputs. When absent, weighting is unchanged.

ADR compliance: structlog-only, timezone-aware, builtin generics, explicit zip.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import structlog

logger = structlog.get_logger(__name__)

__dora_meta__ = {
    "component_name": "RankingExtensions",
    "module_version": "1.0.0",
    "status": "active",
}


# ---------------------------------------------------------------------------
# Extended ranking item
# ---------------------------------------------------------------------------


@dataclass
class ExtendedRankingItem:
    """A ranking item with optional importance and salience fields."""

    item: Any
    semantic_score: float = 0.0
    recency_score: float = 0.0
    importance_score: float | None = None
    decayed_salience: float | None = None


# ---------------------------------------------------------------------------
# Weight presets with importance/salience support
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ExtendedWeights:
    """Weighting factors including importance and salience.

    When importance_weight and salience_weight are 0.0, behavior is identical
    to the base MultiFactorRanker (backward-compatible default).
    """

    semantic_weight: float = 0.5
    recency_weight: float = 0.3
    importance_weight: float = 0.0
    salience_weight: float = 0.0

    @staticmethod
    def default() -> ExtendedWeights:
        """Backward-compatible weights (no importance/salience)."""
        return ExtendedWeights()

    @staticmethod
    def with_importance() -> ExtendedWeights:
        """Weights that include importance scoring."""
        return ExtendedWeights(
            semantic_weight=0.4,
            recency_weight=0.2,
            importance_weight=0.3,
            salience_weight=0.1,
        )

    @staticmethod
    def salience_heavy() -> ExtendedWeights:
        """Weights emphasizing decayed salience."""
        return ExtendedWeights(
            semantic_weight=0.3,
            recency_weight=0.15,
            importance_weight=0.2,
            salience_weight=0.35,
        )


# ---------------------------------------------------------------------------
# Extended ranking function
# ---------------------------------------------------------------------------


def compute_extended_score(
    item: ExtendedRankingItem,
    weights: ExtendedWeights | None = None,
) -> float:
    """Compute a blended ranking score with optional importance + salience.

    Falls back to semantic + recency only when importance/salience are None.
    """
    w = weights or ExtendedWeights.default()

    score = (
        w.semantic_weight * item.semantic_score + w.recency_weight * item.recency_score
    )

    if item.importance_score is not None and w.importance_weight > 0:
        score += w.importance_weight * item.importance_score

    if item.decayed_salience is not None and w.salience_weight > 0:
        score += w.salience_weight * item.decayed_salience

    return score


def rank_extended(
    items: list[ExtendedRankingItem],
    weights: ExtendedWeights | None = None,
) -> list[ExtendedRankingItem]:
    """Rank items using extended scoring. Returns sorted copy (desc)."""
    scored = [(compute_extended_score(item, weights), item) for item in items]
    scored.sort(key=lambda pair: pair[0], reverse=True)
    ranked = [item for _, item in scored]

    logger.debug(
        "extended_ranking_complete",
        item_count=len(ranked),
        top_score=round(scored[0][0], 4) if scored else 0.0,
    )
    return ranked


__all__ = [
    "ExtendedRankingItem",
    "ExtendedWeights",
    "compute_extended_score",
    "rank_extended",
]

__dora_footer__ = {
    "governance_level": "medium",
    "compliance_required": True,
}
