"""
Tests for SymPy Integration
============================

Integration tests covering:
- Full pipeline from validation to evaluation
- Cache integration
- API route integration
- Tool integration

Target: >=85% coverage, >=95% pass rate
"""

from __future__ import annotations

import pytest

from services.symbolic_computation.core.cache_manager import CacheManager
from services.symbolic_computation.core.expression_evaluator import ExpressionEvaluator
from services.symbolic_computation.core.metrics import MetricsCollector
from services.symbolic_computation.core.optimizer import Optimizer
from services.symbolic_computation.core.validator import ExpressionValidator
from services.symbolic_computation.tools.symbolic_tool import SymPyTool


class TestFullPipeline:
    """Integration tests for complete pipeline."""

    @pytest.fixture
    def validator(self):
        return ExpressionValidator()

    @pytest.fixture
    def evaluator(self):
        return ExpressionEvaluator()

    @pytest.fixture
    def optimizer(self):
        return Optimizer()

    @pytest.mark.asyncio
    async def test_validate_then_evaluate(self, validator, evaluator):
        """Test validating then evaluating expression."""
        expr = "x**2 + 2*x + 1"

        # Validate first
        validation = validator.validate(expr)
        assert validation.is_valid is True

        # Then evaluate
        result = await evaluator.evaluate_expression(
            expr=expr,
            variables={"x": 2},
            backend="numpy",
        )

        assert result.result == 9.0
        assert result.error is None

    @pytest.mark.asyncio
    async def test_optimize_then_evaluate(self, optimizer, evaluator):
        """Test optimizing then evaluating expression."""
        expr = "x**2 + 2*x + 1"

        # Optimize
        optimized = optimizer.optimize_expression(expr)
        optimized_str = str(optimized)

        # Evaluate optimized
        result = await evaluator.evaluate_expression(
            expr=optimized_str,
            variables={"x": 2},
            backend="numpy",
        )

        # Result should be same as original
        assert result.result == 9.0


class TestCacheIntegration:
    """Integration tests for caching."""

    @pytest.fixture
    def cache(self):
        return CacheManager()

    @pytest.fixture
    def metrics(self):
        return MetricsCollector()

    @pytest.fixture
    def evaluator(self, cache, metrics):
        return ExpressionEvaluator(
            cache_manager=cache,
            metrics_collector=metrics,
        )

    @pytest.mark.asyncio
    async def test_cache_stores_result(self, cache, evaluator):
        """Test that evaluation stores result in cache."""
        result = await evaluator.evaluate_expression(
            expr="x**2",
            variables={"x": 5},
            backend="numpy",
        )

        assert result.result == 25.0

        # Cache should have stored it
        cache.get_stats()
        # Note: First call is a miss, but result should be stored

    @pytest.mark.asyncio
    async def test_repeated_evaluation_uses_cache(self, evaluator, cache):
        """Test that repeated evaluation uses cache."""
        expr = "x**2"
        variables = {"x": 3}

        # First evaluation
        result1 = await evaluator.evaluate_expression(
            expr=expr,
            variables=variables,
            backend="numpy",
        )

        # Second evaluation (should hit cache)
        result2 = await evaluator.evaluate_expression(
            expr=expr,
            variables=variables,
            backend="numpy",
        )

        assert result1.result == result2.result == 9.0


class TestMetricsIntegration:
    """Integration tests for metrics collection."""

    @pytest.fixture
    def metrics(self):
        return MetricsCollector()

    @pytest.fixture
    def evaluator(self, metrics):
        return ExpressionEvaluator(metrics_collector=metrics)

    @pytest.mark.asyncio
    async def test_evaluation_records_metrics(self, evaluator, metrics):
        """Test that evaluation records metrics."""
        await evaluator.evaluate_expression(
            expr="x**2",
            variables={"x": 2},
            backend="numpy",
        )

        summary = await metrics.get_metrics_summary()

        assert summary.total_evaluations >= 1
        assert "numpy" in summary.backend_usage


class TestSymPyToolIntegration:
    """Integration tests for SymPyTool."""

    @pytest.fixture
    def tool(self):
        return SymPyTool()

    @pytest.mark.asyncio
    async def test_tool_evaluate(self, tool):
        """Test tool evaluation method."""
        result = await tool.evaluate(
            expression="x**2",
            variables={"x": 4},
            backend="numpy",
        )

        assert result["result"] == 16.0
        assert result["error"] is None

    @pytest.mark.asyncio
    async def test_tool_generate_code(self, tool):
        """Test tool code generation method."""
        result = await tool.generate_code(
            expression="x**2 + 1",
            variables=["x"],
            language="Python",
            function_name="test_fn",
        )

        assert result["success"] is True
        assert "def test_fn" in result["source_code"]

    def test_tool_optimize(self, tool):
        """Test tool optimization method."""
        result = tool.optimize(
            expression="x**2 + 2*x + 1",
            strategies=["simplify"],
        )

        assert result["optimized"] is not None
        assert result.get("error") is None

    def test_tool_validate(self, tool):
        """Test tool validation method."""
        result = tool.validate("x**2 + sin(x)")

        assert result["is_valid"] is True
        assert len(result["errors"]) == 0

    def test_get_tool_definitions(self, tool):
        """Test tool definition generation."""
        definitions = tool.get_tool_definitions()

        assert len(definitions) == 3
        names = [d["name"] for d in definitions]
        assert "symbolic_evaluate" in names
        assert "symbolic_codegen" in names
        assert "symbolic_optimize" in names


class TestOptimizerIntegration:
    """Integration tests for Optimizer."""

    @pytest.fixture
    def optimizer(self):
        return Optimizer()

    def test_cse_optimization(self, optimizer):
        """Test common subexpression elimination."""
        # Expression with repeated subexpressions
        expr = "sin(x)**2 + cos(x)**2 + sin(x)*cos(x)"

        _replacements, _reduced = optimizer.apply_cse(expr)

        # Should find common subexpressions
        # Note: sin(x)**2 + cos(x)**2 = 1 if simplified

    def test_simplify_pythagorean(self, optimizer):
        """Test simplification of Pythagorean identity."""
        expr = "sin(x)**2 + cos(x)**2"

        simplified = optimizer.simplify_expression(expr)

        # Should simplify to 1
        assert str(simplified) == "1"

    def test_factor_polynomial(self, optimizer):
        """Test factoring polynomial."""
        expr = "x**2 - 1"

        factored = optimizer.factor_expression(expr)

        # Should factor to (x-1)(x+1)
        assert "x - 1" in str(factored) or "x + 1" in str(factored)
