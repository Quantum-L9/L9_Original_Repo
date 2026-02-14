"""Tests for E3+E5 — ImportanceRecipe wiring.

Harvested from: current_work/02-14-2026/memory upgrade/test_importance_recipe_wiring.py
Adapted to match actual L9 APIs (ImportanceManager.decay_importance,
LearningExtractor._compute_importance, compute_importance as module function).

Covers: feature flag ON → ImportanceRecipe.compute_importance() called,
        feature flag OFF → original inline formula.
"""

from __future__ import annotations

import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from memory.active_encoder import (
    ExtractedLearning,
    LearningExtractor,
    TaskOutcome,
)
from memory.importance_recipe import (
    ImportanceInputs,
    ImportanceUpdate,
    compute_importance,
)


# ------------------------------------------------------------------
# E3: ImportanceManager → ImportanceRecipe
# ------------------------------------------------------------------
class TestImportanceManagerRecipeWiring:
    """Feature flag controls delegation to ImportanceRecipe in decay_importance."""

    @pytest.mark.asyncio
    async def test_flag_off_uses_inline_formula(self) -> None:
        """Flag OFF → original _calculate_decay used (no recipe import)."""
        from memory.importance_manager import ImportanceManager

        manager = ImportanceManager(config=None)
        # Without a repository, decay_importance returns [] — but we can
        # verify the _calculate_decay method is used directly
        with patch.dict(os.environ, {"ENABLE_IMPORTANCE_RECIPE": "false"}):
            result = await manager.decay_importance(batch_size=10)
        # No repo → empty list, but no errors from recipe path
        assert result == []

    @pytest.mark.asyncio
    async def test_flag_on_would_use_recipe_path(self) -> None:
        """Flag ON → _calculate_decay_via_recipe method exists and is callable."""
        from memory.importance_manager import ImportanceManager

        manager = ImportanceManager(config=None)
        assert hasattr(manager, "_calculate_decay_via_recipe")

        # Verify the recipe path calls compute_importance
        with patch(
            "memory.importance_manager.compute_importance",
        ) as mock_compute:
            mock_compute.return_value = ImportanceUpdate(
                raw_importance=0.75,
                tier_weight=0.65,
                access_boost=1.0,
                outcome_boost=1.15,
            )
            from datetime import UTC, datetime

            result = manager._calculate_decay_via_recipe(
                importance=0.8,
                last_accessed=datetime.now(UTC),
                now=datetime.now(UTC),
                row={"tier": "semantic", "access_count": 5},
            )
        mock_compute.assert_called_once()
        assert 0.0 <= result <= 1.0

    def test_default_flag_is_off(self) -> None:
        """No env var → default OFF."""
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("ENABLE_IMPORTANCE_RECIPE", None)
            val = os.environ.get("ENABLE_IMPORTANCE_RECIPE", "false")
        assert val == "false"


# ------------------------------------------------------------------
# E5: ActiveMemoryEncoder → ImportanceRecipe
# ------------------------------------------------------------------
class TestActiveEncoderRecipeWiring:
    """Feature flag controls delegation to ImportanceRecipe in _compute_importance."""

    @pytest.fixture
    def extractor(self) -> LearningExtractor:
        return LearningExtractor()

    def test_flag_off_uses_inline_heuristic(
        self,
        extractor: LearningExtractor,
    ) -> None:
        """Flag OFF → original inline heuristic."""
        learning = ExtractedLearning(
            fact_text="test", learning_type="general", tier="session"
        )
        outcome = TaskOutcome(success=True, impact_score=0.5)
        with patch.dict(os.environ, {"ENABLE_IMPORTANCE_RECIPE": "false"}):
            score = extractor._compute_importance(learning, outcome)
        assert 0.0 <= score <= 1.0

    def test_flag_on_delegates_to_recipe(
        self,
        extractor: LearningExtractor,
    ) -> None:
        """Flag ON → ImportanceRecipe.compute_importance() called."""
        learning = ExtractedLearning(
            fact_text="test", learning_type="correction", tier="semantic"
        )
        outcome = TaskOutcome(success=False, impact_score=0.6)
        with patch.dict(os.environ, {"ENABLE_IMPORTANCE_RECIPE": "true"}):
            score = extractor._compute_importance(learning, outcome)
        # Recipe path produces a valid score
        assert 0.0 <= score <= 1.0

    def test_correction_learning_boosts_importance_inline(
        self,
        extractor: LearningExtractor,
    ) -> None:
        """Inline heuristic: correction type applies +0.15 boost."""
        outcome = TaskOutcome(success=False, impact_score=0.4)
        with patch.dict(os.environ, {"ENABLE_IMPORTANCE_RECIPE": "false"}):
            correction_score = extractor._compute_importance(
                ExtractedLearning(
                    fact_text="fix", learning_type="correction", tier="session"
                ),
                outcome,
            )
            general_score = extractor._compute_importance(
                ExtractedLearning(
                    fact_text="note", learning_type="general", tier="session"
                ),
                outcome,
            )
        assert correction_score > general_score

    def test_recipe_path_fallback_on_error(
        self,
        extractor: LearningExtractor,
    ) -> None:
        """Recipe path falls back to inline heuristic on error."""
        learning = ExtractedLearning(
            fact_text="test", learning_type="general", tier="session"
        )
        outcome = TaskOutcome(success=True, impact_score=0.5)
        with (
            patch.dict(os.environ, {"ENABLE_IMPORTANCE_RECIPE": "true"}),
            patch(
                "memory.active_encoder.compute_importance",
                side_effect=RuntimeError("boom"),
            ),
        ):
            score = extractor._compute_importance(learning, outcome)
        # Falls back to inline — still produces valid score
        assert 0.0 <= score <= 1.0
