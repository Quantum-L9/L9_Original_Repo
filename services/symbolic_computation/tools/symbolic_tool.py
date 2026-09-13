"""
SymPy Agent Tool
=================

L9 agent tool for symbolic computation.
Registered in the tool registry for use by all agents.

Version: 6.0.0
"""

from __future__ import annotations

from core.decorators import must_stay_async


from typing import Any

import structlog

from services.symbolic_computation.config import get_config
from services.symbolic_computation.core.cache_manager import CacheManager
from services.symbolic_computation.core.code_generator import CodeGenerator
from services.symbolic_computation.core.expression_evaluator import ExpressionEvaluator
from services.symbolic_computation.core.metrics import MetricsCollector
from services.symbolic_computation.core.optimizer import Optimizer
from services.symbolic_computation.core.validator import ExpressionValidator

logger = structlog.get_logger(__name__)


class SymPyTool:
    """
    L9 Agent Tool for symbolic computation.

    Provides agents with:
    - Expression evaluation (multiple backends)
    - Code generation (C, Fortran, Cython, Python)
    - Expression optimization (simplify, CSE)
    - Expression validation

    Registered as:
    - symbolic_evaluate
    - symbolic_codegen
    - symbolic_optimize

    Example (from agent):
        result = await self.tools.symbolic_evaluate(
            expression="x**2 + 2*x + 1",
            variables={"x": 3}
        )
    """

    # Tool metadata
    name = "sympy_tool"
    description = "High-performance symbolic computation with SymPy"
    requires_approval = False
    category = "computation"

    def __init__(
        self,
        redis_client: Any | None = None,
        postgres_client: Any | None = None,
    ):
        """
        Initialize the SymPy tool.

        Args:
            redis_client: Optional Redis client for caching
            postgres_client: Optional Postgres client for metrics
        """
        self.config = get_config()
        self.logger = logger.bind(tool="sympy")

        # Initialize components
        self.cache = CacheManager(redis_client=redis_client)
        self.metrics = MetricsCollector(postgres_client=postgres_client)
        self.evaluator = ExpressionEvaluator(
            cache_manager=self.cache,
            metrics_collector=self.metrics,
        )
        self.generator = CodeGenerator(metrics_collector=self.metrics)
        self.optimizer = Optimizer()
        self.validator = ExpressionValidator()

        self.logger.info("sympy_tool_initialized")

    @must_stay_async("callers use await")
    async def evaluate(
        self,
        expression: str,
        variables: dict[str, float] | None = None,
        backend: str = "numpy",
    ) -> dict[str, Any]:
        """
        Evaluate a symbolic expression numerically.

        Args:
            expression: SymPy expression as string
            variables: Variable name to value mapping
            backend: Numerical backend (numpy, math, mpmath)

        Returns:
            Dict with result, execution_time_ms, cache_hit, error
        """
        variables = variables or {}

        self.logger.info(
            "tool_evaluate_called",
            expr_len=len(expression),
            backend=backend,
        )

        # Validate first
        validation = self.validator.validate(expression)
        if not validation.is_valid:
            return {
                "result": None,
                "error": f"Validation failed: {'; '.join(validation.errors)}",
                "execution_time_ms": 0,
                "cache_hit": False,
            }

        # Evaluate
        result = await self.evaluator.evaluate_expression(
            expr=expression,
            variables=variables,
            backend=backend,
        )

        return {
            "result": result.result,
            "execution_time_ms": result.execution_time_ms,
            "cache_hit": result.cache_hit,
            "backend_used": result.backend_used,
            "error": result.error,
        }

    @must_stay_async("callers use await")
    async def generate_code(
        self,
        expression: str,
        variables: list[str],
        language: str = "C",
        function_name: str = "evaluate",
    ) -> dict[str, Any]:
        """
        Generate compilable code from expression.

        Args:
            expression: SymPy expression as string
            variables: List of variable names
            language: Target language (C, Fortran, Cython, Python)
            function_name: Name for generated function

        Returns:
            Dict with source_code, language, function_name, success, error
        """
        self.logger.info(
            "tool_generate_code_called",
            expr_len=len(expression),
            language=language,
        )

        # Validate
        validation = self.validator.validate(expression)
        if not validation.is_valid:
            return {
                "source_code": "",
                "language": language,
                "function_name": function_name,
                "success": False,
                "error": f"Validation failed: {'; '.join(validation.errors)}",
            }

        # Generate
        result = await self.generator.generate_code(
            expr=expression,
            variables=variables,
            language=language,
            function_name=function_name,
        )

        return {
            "source_code": result.source_code,
            "language": result.language,
            "function_name": result.function_name,
            "success": result.success,
            "execution_time_ms": result.execution_time_ms,
            "error": result.error_message,
        }

    def optimize(
        self,
        expression: str,
        strategies: list[str] | None = None,
    ) -> dict[str, Any]:
        """
        Optimize expression for faster evaluation.

        Args:
            expression: SymPy expression as string
            strategies: Optimization strategies (simplify, expand, factor, cse)

        Returns:
            Dict with original, optimized, reduction_percent
        """
        strategies = strategies or ["simplify"]

        self.logger.info(
            "tool_optimize_called",
            expr_len=len(expression),
            strategies=strategies,
        )

        # Validate
        validation = self.validator.validate(expression)
        if not validation.is_valid:
            return {
                "original": expression,
                "optimized": expression,
                "error": f"Validation failed: {'; '.join(validation.errors)}",
            }

        # Count original ops
        original_ops = self.optimizer.count_operations(expression)

        # Optimize
        optimized = self.optimizer.optimize_expression(
            expression,
            strategies=strategies,
        )

        # Count optimized ops
        optimized_ops = self.optimizer.count_operations(optimized)

        reduction = (
            ((original_ops - optimized_ops) / original_ops * 100)
            if original_ops > 0
            else 0.0
        )

        return {
            "original": expression,
            "optimized": str(optimized),
            "original_ops": original_ops,
            "optimized_ops": optimized_ops,
            "reduction_percent": round(reduction, 2),
            "strategies_applied": strategies,
        }

    def validate(self, expression: str) -> dict[str, Any]:
        """
        Validate an expression.

        Args:
            expression: Expression to validate

        Returns:
            Dict with is_valid, errors, warnings, dangerous_functions_found
        """
        result = self.validator.validate(expression)

        return {
            "is_valid": result.is_valid,
            "expression_length": result.expression_length,
            "errors": result.errors,
            "warnings": result.warnings,
            "dangerous_functions_found": result.dangerous_functions_found,
        }

    def get_tool_definitions(self) -> list[dict[str, Any]]:
        """
        Get tool definitions for registration in L9 tool registry.

        Returns:
            List of tool definition dicts
        """
        return [
            {
                "name": "symbolic_evaluate",
                "description": "Evaluate a symbolic expression numerically",
                "parameters": {
                    "expression": {"type": "string", "required": True},
                    "variables": {"type": "object", "required": False},
                    "backend": {
                        "type": "string",
                        "required": False,
                        "default": "numpy",
                    },
                },
                "category": "computation",
                "requires_approval": False,
            },
            {
                "name": "symbolic_codegen",
                "description": "Generate compilable code from expression",
                "parameters": {
                    "expression": {"type": "string", "required": True},
                    "variables": {"type": "array", "required": True},
                    "language": {"type": "string", "required": False, "default": "C"},
                    "function_name": {
                        "type": "string",
                        "required": False,
                        "default": "evaluate",
                    },
                },
                "category": "computation",
                "requires_approval": False,
            },
            {
                "name": "symbolic_optimize",
                "description": "Optimize expression for faster evaluation",
                "parameters": {
                    "expression": {"type": "string", "required": True},
                    "strategies": {
                        "type": "array",
                        "required": False,
                        "default": ["simplify"],
                    },
                },
                "category": "computation",
                "requires_approval": False,
            },
        ]


# Factory function for tool registration
def create_sympy_tool(
    redis_client: Any | None = None,
    postgres_client: Any | None = None,
) -> SymPyTool:
    """
    Create a SymPyTool instance.

    This is the factory function used by L9 tool registry.

    Args:
        redis_client: Optional Redis client
        postgres_client: Optional Postgres client

    Returns:
        Configured SymPyTool instance
    """
    return SymPyTool(
        redis_client=redis_client,
        postgres_client=postgres_client,
    )


# Runtime execution trace - updated automatically on every execution
