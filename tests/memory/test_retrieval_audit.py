"""
Tests for memory retrieval utilities - ranking and temporal decay.
"""

import sys
from datetime import datetime, timedelta
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from memory.retrieval import apply_temporal_decay, reciprocal_rank_fusion


class TestReciprocalRankFusion:
    """Tests for reciprocal rank fusion algorithm."""

    def test_basic_fusion(self):
        """Basic RRF should combine rankings."""
        rankings = [["a", "b", "c"], ["b", "c", "a"]]
        scores = reciprocal_rank_fusion(rankings, k=60)

        assert "a" in scores
        assert "b" in scores
        assert "c" in scores
        assert all(score > 0 for score in scores.values())

    def test_consistent_winner(self):
        """Item ranked first in both lists should score highest."""
        rankings = [["a", "b", "c"], ["a", "c", "b"]]
        scores = reciprocal_rank_fusion(rankings, k=60)

        assert scores["a"] > scores["b"]
        assert scores["a"] > scores["c"]

    def test_consensus_ranking(self):
        """Item ranked well in both lists should beat one-list-only."""
        rankings = [["a", "b", "c"], ["b", "c", "a"]]
        scores = reciprocal_rank_fusion(rankings, k=60)

        # "b" is 2nd + 1st = better than "a" which is 1st + 3rd
        assert scores["b"] > scores["c"]

    def test_single_ranking(self):
        """Single ranking should still produce scores."""
        rankings = [["a", "b", "c"]]
        scores = reciprocal_rank_fusion(rankings, k=60)

        assert scores["a"] > scores["b"] > scores["c"]

    def test_empty_rankings(self):
        """Empty rankings should return empty scores."""
        scores = reciprocal_rank_fusion([], k=60)
        assert scores == {}

    def test_k_parameter_effect(self):
        """Lower k should amplify rank differences."""
        rankings = [["a", "b", "c"]]

        scores_k1 = reciprocal_rank_fusion(rankings, k=1)
        scores_k100 = reciprocal_rank_fusion(rankings, k=100)

        # With k=1: 1/(1+1)=0.5, 1/(1+2)=0.33, 1/(1+3)=0.25
        # With k=100: 1/(100+1)≈0.0099, 1/(100+2)≈0.0098, 1/(100+3)≈0.0097
        # Ratio of top to bottom is higher with lower k
        ratio_k1 = scores_k1["a"] / scores_k1["c"]
        ratio_k100 = scores_k100["a"] / scores_k100["c"]

        assert ratio_k1 > ratio_k100


class TestTemporalDecay:
    """Tests for temporal decay function."""

    def test_no_decay_for_recent(self):
        """Very recent items should have minimal decay."""
        now = datetime.now(timezone.utc)
        score = apply_temporal_decay(1.0, now, half_life_days=30)

        assert score > 0.99  # Essentially no decay

    def test_half_decay_at_half_life(self):
        """Score should be halved at exactly one half-life."""
        now = datetime.now(timezone.utc)
        half_life = 30
        old = now - timedelta(days=half_life)

        score = apply_temporal_decay(
            1.0, old, half_life_days=half_life, reference_time=now
        )

        assert 0.49 < score < 0.51  # Approximately 0.5

    def test_quarter_decay_at_two_half_lives(self):
        """Score should be quartered at two half-lives."""
        now = datetime.now(timezone.utc)
        half_life = 30
        very_old = now - timedelta(days=half_life * 2)

        score = apply_temporal_decay(
            1.0, very_old, half_life_days=half_life, reference_time=now
        )

        assert 0.24 < score < 0.26  # Approximately 0.25

    def test_recent_beats_old(self):
        """Recent items should always score higher than old ones."""
        now = datetime.now(timezone.utc)
        recent = now - timedelta(days=1)
        old = now - timedelta(days=60)

        recent_score = apply_temporal_decay(
            1.0, recent, half_life_days=30, reference_time=now
        )
        old_score = apply_temporal_decay(
            1.0, old, half_life_days=30, reference_time=now
        )

        assert recent_score > old_score

    def test_preserves_relative_scores(self):
        """Decay should preserve relative ordering of base scores."""
        now = datetime.now(timezone.utc)
        timestamp = now - timedelta(days=15)

        high_decayed = apply_temporal_decay(
            1.0, timestamp, half_life_days=30, reference_time=now
        )
        low_decayed = apply_temporal_decay(
            0.5, timestamp, half_life_days=30, reference_time=now
        )

        assert high_decayed > low_decayed
        # Ratio should be preserved
        assert abs(high_decayed / low_decayed - 2.0) < 0.01

    def test_future_timestamp_no_decay(self):
        """Future timestamps should not have negative decay."""
        now = datetime.now(timezone.utc)
        future = now + timedelta(days=10)

        score = apply_temporal_decay(1.0, future, half_life_days=30, reference_time=now)

        assert score == 1.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
