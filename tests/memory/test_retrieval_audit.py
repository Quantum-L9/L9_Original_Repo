from datetime import datetime, timedelta
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from memory.retrieval import reciprocal_rank_fusion, apply_temporal_decay


def test_reciprocal_rank_fusion_scores():
    rankings = [["a", "b", "c"], ["b", "c", "a"]]
    scores = reciprocal_rank_fusion(rankings, k=60)
    assert scores["a"] > 0
    assert scores["b"] > scores["c"]


def test_apply_temporal_decay_prefers_recent():
    now = datetime.utcnow()
    older = now - timedelta(days=30)
    recent_score = apply_temporal_decay(1.0, now, half_life_days=30)
    older_score = apply_temporal_decay(1.0, older, half_life_days=30)
    assert recent_score > older_score
