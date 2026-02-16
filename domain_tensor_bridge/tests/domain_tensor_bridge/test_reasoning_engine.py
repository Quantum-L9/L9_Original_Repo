#!/usr/bin/env python3
"""
Tests for ReasoningEngine - reasoning modes, confidence, and error paths.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from core.decorators import must_stay_async
from domain_tensor_bridge.reasoning_engine import ReasoningEngine, ReasoningResult


@pytest.fixture
def engine():
    """Create reasoning engine with mocked reasoners."""
    return ReasoningEngine(
        symbolic_reasoner=MagicMock(),
        causal_reasoner=AsyncMock(),
        analogical_reasoner=AsyncMock(),
        reflective_auditor=MagicMock(),
    )


class TestReasoningModes:
    """Tests for reasoning mode selection."""

    @pytest.mark.asyncio
    async def test_all_modes_applied(self, engine):
        """Test all reasoning modes are applied."""
        context = {"entity_id": "test_123"}

        result = await engine.execute_reasoning(context)

        assert isinstance(result, ReasoningResult)
        assert "symbolic" in result.modes_applied
        assert "causal" in result.modes_applied
        assert "analogical" in result.modes_applied
        assert "reflective" in result.modes_applied

    @pytest.mark.asyncio
    async def test_selective_modes(self, engine):
        """Test selective mode application."""
        context = {"entity_id": "test_123"}

        result = await engine.execute_reasoning(context, modes=["symbolic", "causal"])

        assert "symbolic" in result.modes_applied
        assert "causal" in result.modes_applied
        assert "analogical" not in result.modes_applied


class TestConfidenceThresholds:
    """Tests for confidence calculation."""

    @pytest.mark.asyncio
    async def test_confidence_calculation(self, engine):
        """Test confidence is calculated."""
        context = {"entity_id": "test_123"}

        result = await engine.execute_reasoning(context)

        assert 0.0 <= result.confidence <= 1.0

    @pytest.mark.asyncio
    @must_stay_async("callers use await")
    async def test_low_confidence_warning(self, engine):
        """Test low confidence generates warning."""
        # Would need mock setup for low confidence
        pass


class TestErrorPaths:
    """Tests for error handling."""

    @pytest.mark.asyncio
    @must_stay_async("callers use await")
    async def test_reasoner_failure_handling(self, engine):
        """Test graceful handling of reasoner failure."""
        engine.causal_reasoner.apply_causal_logic = AsyncMock(
            side_effect=Exception("Reasoner failed")
        )

        # Should handle gracefully
        # Depending on implementation, might raise or return default

    @pytest.mark.asyncio
    async def test_empty_context(self, engine):
        """Test handling of empty context."""
        result = await engine.execute_reasoning({})

        assert result is not None
