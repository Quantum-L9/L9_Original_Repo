"""Tests for memory.intake_leverage — scoring, query, and integration with
ImportanceManager/NeuralDecayScheduler terminology.
"""

from __future__ import annotations

import pytest

from memory.intake_leverage import (
    _LEVERAGE_QUERY,
    IntakeLeverageQuery,
    IntakeLeverageScorer,
    IntakeTier,
    LeverageCandidate,
    RoleWeight,
    score_intake_leverage,
)


class TestRoleWeights:
    """RoleWeight enum values match ImportanceManager elevation semantics."""

    def test_system_highest(self) -> None:
        assert RoleWeight.SYSTEM.value == 0.90

    def test_user_mid(self) -> None:
        assert RoleWeight.USER.value == 0.50

    def test_tool_lowest(self) -> None:
        assert RoleWeight.TOOL.value == 0.30

    def test_ordering(self) -> None:
        assert (
            RoleWeight.SYSTEM > RoleWeight.ASSISTANT > RoleWeight.USER > RoleWeight.TOOL
        )


class TestIntakeTier:
    """IntakeTier aligns with NeuralDecayScheduler tier modifiers."""

    def test_identity_value(self) -> None:
        assert IntakeTier.IDENTITY.value == "identity"

    def test_episodic_value(self) -> None:
        assert IntakeTier.EPISODIC.value == "episodic"


class TestScoreIntakeLeverage:
    """score_intake_leverage() computes correct weighted scores."""

    def test_defaults_user_general(self) -> None:
        result = score_intake_leverage()
        score = result["importance"]
        assert 0.0 <= score <= 1.0
        assert result["roi_estimate"] is None
        assert result["estimated_time_saved_minutes"] is None

    def test_system_identity_max(self) -> None:
        result = score_intake_leverage(
            role="system", tier="identity", recent_access_count=50
        )
        assert result["importance"] >= 0.85

    def test_tool_session_min(self) -> None:
        result = score_intake_leverage(
            role="tool", tier="session", recent_access_count=0
        )
        assert result["importance"] <= 0.35

    def test_access_count_boost(self) -> None:
        low = score_intake_leverage(recent_access_count=0)
        high = score_intake_leverage(recent_access_count=50)
        assert high["importance"] > low["importance"]

    def test_unknown_role_fallback(self) -> None:
        result = score_intake_leverage(role="nonexistent_role")
        assert 0.0 <= result["importance"] <= 1.0

    def test_unknown_tier_fallback(self) -> None:
        result = score_intake_leverage(tier="nonexistent_tier")
        assert 0.0 <= result["importance"] <= 1.0

    def test_roi_passthrough(self) -> None:
        result = score_intake_leverage(
            roi_estimate=2.5, estimated_time_saved_minutes=60.0
        )
        assert result["roi_estimate"] == 2.5
        assert result["estimated_time_saved_minutes"] == 60.0

    def test_custom_scorer(self) -> None:
        scorer = IntakeLeverageScorer(
            role_weight_factor=0.8,
            tier_modifier_factor=0.1,
            access_pattern_factor=0.1,
        )
        result = score_intake_leverage(scorer=scorer, role="system")
        assert result["importance"] >= 0.7

    def test_clamped_to_unit_interval(self) -> None:
        result = score_intake_leverage(
            role="system", tier="identity", recent_access_count=1000
        )
        assert result["importance"] <= 1.0


class TestLeverageCandidate:
    """LeverageCandidate uses importance_score."""

    def test_importance_score(self) -> None:
        c = LeverageCandidate(
            packet_id="pkt-001",
            packet_type="agent_task_submitted",
            importance_score=0.72,
        )
        assert c.importance_score == 0.72

    def test_frozen(self) -> None:
        c = LeverageCandidate(
            packet_id="pkt-002",
            packet_type="agent_task_submitted",
        )
        with pytest.raises(AttributeError):
            c.importance_score = 0.99  # type: ignore[misc]


class TestIntakeLeverageQuery:
    """IntakeLeverageQuery filters by importance_score."""

    def test_defaults(self) -> None:
        q = IntakeLeverageQuery()
        assert q.min_importance_score == 0.0
        assert q.limit == 20

    def test_importance_filter(self) -> None:
        q = IntakeLeverageQuery(min_importance_score=0.5)
        assert q.min_importance_score == 0.5


class TestLeverageQuerySQL:
    """SQL template uses importance_score."""

    def test_has_importance_filter(self) -> None:
        assert "importance_score >= $1" in _LEVERAGE_QUERY

    def test_importance_ordering(self) -> None:
        assert "importance_score DESC" in _LEVERAGE_QUERY

    def test_selects_importance(self) -> None:
        assert "importance_score" in _LEVERAGE_QUERY
        assert "access_count" in _LEVERAGE_QUERY
