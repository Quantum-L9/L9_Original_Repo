"""Tests for ImportanceRecipe — deterministic importance scoring."""

from __future__ import annotations

from memory.importance_recipe import (
    ImportanceInputs,
    ImportanceUpdate,
    access_boost,
    compute_importance,
    outcome_boost,
    tier_weight,
)


class TestTierWeight:
    def test_procedural_highest(self) -> None:
        assert tier_weight("procedural") > tier_weight("semantic")
        assert tier_weight("semantic") > tier_weight("episodic")

    def test_unknown_segment_gets_default(self) -> None:
        assert tier_weight("unknown") == 0.50

    def test_case_insensitive(self) -> None:
        assert tier_weight("PROCEDURAL") == tier_weight("procedural")


class TestAccessBoost:
    def test_zero_access_gives_base(self) -> None:
        boost = access_boost(0, 0.0)
        assert 0.9 < boost < 1.2

    def test_many_accesses_increase_boost(self) -> None:
        assert access_boost(100, 0.0) > access_boost(1, 0.0)

    def test_old_access_decreases_boost(self) -> None:
        assert access_boost(10, 0.0) > access_boost(10, 1000.0)

    def test_boost_capped_at_2(self) -> None:
        assert access_boost(999999, 0.0) <= 2.0


class TestOutcomeBoost:
    def test_no_signals_gives_base(self) -> None:
        assert outcome_boost(0, False) == 1.0

    def test_reflection_adds_boost(self) -> None:
        assert outcome_boost(0, True) > outcome_boost(0, False)

    def test_success_signals_increase_boost(self) -> None:
        assert outcome_boost(10, False) > outcome_boost(0, False)

    def test_boost_capped_at_1_5(self) -> None:
        assert outcome_boost(999, True) <= 1.5


class TestComputeImportance:
    def test_returns_importance_update(self) -> None:
        result = compute_importance(ImportanceInputs())
        assert isinstance(result, ImportanceUpdate)

    def test_raw_importance_in_range(self) -> None:
        result = compute_importance(
            ImportanceInputs(
                segment="procedural",
                access_count=50,
                success_signal_count=10,
                has_reflection=True,
            ),
        )
        assert 0.0 <= result.raw_importance <= 1.0

    def test_procedural_higher_than_episodic(self) -> None:
        proc = compute_importance(ImportanceInputs(segment="procedural"))
        epi = compute_importance(ImportanceInputs(segment="episodic"))
        assert proc.raw_importance > epi.raw_importance

    def test_computed_at_is_timezone_aware(self) -> None:
        result = compute_importance(ImportanceInputs())
        assert result.computed_at.tzinfo is not None
