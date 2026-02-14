"""Tests for ranking extensions — importance + salience inputs.

Coverage:
  - Default weights produce identical behavior to base ranker
  - Importance-weighted ranking changes order when present
  - Salience-weighted ranking changes order when present
  - None fields are correctly ignored
  - Backward-compatible default
"""

from __future__ import annotations

import pytest

from memory.ranking_extensions import (
    ExtendedRankingItem,
    ExtendedWeights,
    compute_extended_score,
    rank_extended,
)

# ---------------------------------------------------------------------------
# Backward compatibility
# ---------------------------------------------------------------------------


class TestRankingBackwardCompatibility:
    def test_default_weights_ignore_importance(self) -> None:
        item = ExtendedRankingItem(
            item="test",
            semantic_score=0.8,
            recency_score=0.6,
            importance_score=1.0,
        )
        score_default = compute_extended_score(item, ExtendedWeights.default())
        # importance_weight=0.0 so importance_score is ignored
        expected = 0.5 * 0.8 + 0.3 * 0.6
        assert abs(score_default - expected) < 1e-6

    def test_default_weights_ignore_salience(self) -> None:
        item = ExtendedRankingItem(
            item="test",
            semantic_score=0.5,
            recency_score=0.5,
            decayed_salience=1.0,
        )
        score = compute_extended_score(item, ExtendedWeights.default())
        expected = 0.5 * 0.5 + 0.3 * 0.5
        assert abs(score - expected) < 1e-6


# ---------------------------------------------------------------------------
# Importance-weighted ranking
# ---------------------------------------------------------------------------


class TestImportanceWeightedRanking:
    def test_importance_changes_score(self) -> None:
        weights = ExtendedWeights.with_importance()
        item_high = ExtendedRankingItem(
            item="high",
            semantic_score=0.5,
            recency_score=0.5,
            importance_score=1.0,
            decayed_salience=0.5,
        )
        item_low = ExtendedRankingItem(
            item="low",
            semantic_score=0.5,
            recency_score=0.5,
            importance_score=0.1,
            decayed_salience=0.5,
        )
        assert compute_extended_score(item_high, weights) > compute_extended_score(
            item_low,
            weights,
        )

    def test_rank_extended_orders_by_importance(self) -> None:
        weights = ExtendedWeights.with_importance()
        items = [
            ExtendedRankingItem(
                item="low",
                semantic_score=0.5,
                recency_score=0.5,
                importance_score=0.1,
                decayed_salience=0.5,
            ),
            ExtendedRankingItem(
                item="high",
                semantic_score=0.5,
                recency_score=0.5,
                importance_score=1.0,
                decayed_salience=0.5,
            ),
        ]
        ranked = rank_extended(items, weights)
        assert ranked[0].item == "high"
        assert ranked[1].item == "low"


# ---------------------------------------------------------------------------
# Salience-weighted ranking
# ---------------------------------------------------------------------------


class TestSalienceWeightedRanking:
    def test_salience_heavy_prefers_high_salience(self) -> None:
        weights = ExtendedWeights.salience_heavy()
        item_fresh = ExtendedRankingItem(
            item="fresh",
            semantic_score=0.5,
            recency_score=0.5,
            importance_score=0.5,
            decayed_salience=0.95,
        )
        item_stale = ExtendedRankingItem(
            item="stale",
            semantic_score=0.5,
            recency_score=0.5,
            importance_score=0.5,
            decayed_salience=0.1,
        )
        ranked = rank_extended([item_stale, item_fresh], weights)
        assert ranked[0].item == "fresh"


# ---------------------------------------------------------------------------
# None field handling
# ---------------------------------------------------------------------------


class TestNoneFieldHandling:
    def test_none_importance_treated_as_absent(self) -> None:
        weights = ExtendedWeights.with_importance()
        item = ExtendedRankingItem(
            item="test",
            semantic_score=0.8,
            recency_score=0.6,
            importance_score=None,
            decayed_salience=None,
        )
        score = compute_extended_score(item, weights)
        # Only semantic + recency contribute
        expected = 0.4 * 0.8 + 0.2 * 0.6
        assert abs(score - expected) < 1e-6


# ---------------------------------------------------------------------------
# Weight presets
# ---------------------------------------------------------------------------


class TestWeightPresets:
    def test_default_preset(self) -> None:
        w = ExtendedWeights.default()
        assert w.importance_weight == 0.0
        assert w.salience_weight == 0.0

    def test_with_importance_preset(self) -> None:
        w = ExtendedWeights.with_importance()
        assert w.importance_weight > 0
        assert w.salience_weight > 0

    def test_salience_heavy_preset(self) -> None:
        w = ExtendedWeights.salience_heavy()
        assert w.salience_weight > w.semantic_weight
