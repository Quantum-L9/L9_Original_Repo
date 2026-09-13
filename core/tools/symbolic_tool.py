"""
L9 Symbolic Computation Tool
============================

L9 Tool wrapper for symbolic computation capabilities.
Provides compute and codegen tool functions for L-CTO and agents.

Version: 1.0.0
"""

from __future__ import annotations

from core.decorators import must_stay_async


from typing import Any

import structlog

from runtime.tool_registry import register_tool
from services.symbolic_computation import (
    CodeGenResult,
    ComputationResult,
    SymbolicComputation,
)

logger = structlog.get_logger(__name__)

# Global singleton instance
_symbolic_engine: SymbolicComputation | None = None


def get_symbolic_engine() -> SymbolicComputation:
    """
    Get or create the symbolic computation engine singleton.

    Returns:
        SymbolicComputation engine instance
    """
    global _symbolic_engine
    if _symbolic_engine is None:
        _symbolic_engine = SymbolicComputation(
            cache_size=128,
            enable_metrics=True,
        )
        logger.info("symbolic_engine_initialized")
    return _symbolic_engine


class SymbolicComputationTool:
    """
    L9 Tool wrapper for symbolic computation.

    Provides async methods that match L9 tool executor patterns.
    """

    def __init__(self):
        """Initialize the tool wrapper."""
        self._engine = get_symbolic_engine()

    async def compute(
        self,
        expression: str,
        variables: dict[str, float | list[float]],
        backend: str = "numpy",
        **kwargs: Any,
    ) -> dict[str, Any]:
        """
        Compute a symbolic expression with given variable values.

        Args:
            expression: Mathematical expression (e.g., "x**2 + sin(x)")
            variables: Variable values (e.g., {"x": 1.0})
            backend: Computational backend ("numpy", "math", "mpmath", "sympy")

        Returns:
            Dict with computation result
        """
        try:
            result: ComputationResult = await self._engine.compute(
                expression=expression,
                variables=variables,
                backend=backend,
            )

            logger.info(
                "symbolic_compute_complete",
                expression=expression[:50],
                success=result.success,
                execution_time_ms=round(result.execution_time_ms, 2),
            )

            return {
                "status": "success" if result.success else "error",
                "result": result.result,
                "expression": result.expression_str,
                "backend": result.backend_used.value,
                "execution_time_ms": result.execution_time_ms,
                "error": result.error_message,
                "metadata": result.metadata,
            }

        except Exception as e:
            logger.error("symbolic_compute_failed", error=str(e))
            return {
                "status": "error",
                "error": str(e),
            }

    @must_stay_async("callers use await")
    async def generate_code(
        self,
        expression: str,
        variables: list[str],
        language: str = "C",
        function_name: str = "generated_func",
        compile: bool = False,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """
        Generate code from a symbolic expression.

        Args:
            expression: Mathematical expression
            variables: List of variable names
            language: Target language ("C", "Fortran", "Python", "Cython")
            function_name: Name for generated function
            compile: Whether to compile the code

        Returns:
            Dict with generated code
        """
        try:
            result: CodeGenResult = await self._engine.generate_code(
                expression=expression,
                variables=variables,
                language=language,
                function_name=function_name,
                compile=compile,
            )

            logger.info(
                "symbolic_codegen_complete",
                function_name=function_name,
                language=language,
                success=result.success,
                compiled=result.compiled,
            )

            return {
                "status": "success" if result.success else "error",
                "source_code": result.source_code,
                "language": result.language.value,
                "compiled": result.compiled,
                "compilation_output": result.compilation_output,
                "error": result.error_message,
                "metadata": result.metadata,
            }

        except Exception as e:
            logger.error("symbolic_codegen_failed", error=str(e))
            return {
                "status": "error",
                "error": str(e),
            }

    async def health_check(self) -> dict[str, Any]:
        """
        Check health of symbolic computation engine.

        Returns:
            Health status dict
        """
        return await self._engine.health_check()

    def optimize(
        self,
        expression: str,
        strategies: list[str] | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """
        Optimize a symbolic expression for faster evaluation.

        Args:
            expression: Mathematical expression
            strategies: Optimization strategies ("simplify", "expand", "factor", "cse")

        Returns:
            Dict with original and optimized expressions
        """
        strategies = strategies or ["simplify"]

        try:
            # Use sympy optimization functions
            from sympy import cse, expand, factor, simplify, sympify

            expr = sympify(expression)
            optimized = expr

            for strategy in strategies:
                if strategy == "simplify":
                    optimized = simplify(optimized)
                elif strategy == "expand":
                    optimized = expand(optimized)
                elif strategy == "factor":
                    optimized = factor(optimized)
                elif strategy == "cse":
                    # Common subexpression elimination returns (replacements, reduced)
                    _replacements, reduced = cse(optimized)
                    if reduced:
                        optimized = reduced[0]

            logger.info(
                "symbolic_optimize_complete",
                expression=expression[:50],
                strategies=strategies,
            )

            return {
                "status": "success",
                "original": expression,
                "optimized": str(optimized),
                "strategies_applied": strategies,
            }

        except Exception as e:
            logger.error("symbolic_optimize_failed", error=str(e))
            return {
                "status": "error",
                "error": str(e),
            }


# ============================================================================
# TOOL EXECUTOR FUNCTIONS
# ============================================================================
# These are the functions wired into TOOL_EXECUTORS in runtime/l_tools.py


@register_tool(category="symbolic", priority=10, description="symbolic_compute tool")
@register_tool(category="symbolic", priority=10, description="symbolic_compute tool")
@must_stay_async("callers use await")
async def symbolic_compute(
    expression: str,
    variables: dict[str, float | list[float]],
    backend: str = "numpy",
    **kwargs: Any,
) -> dict[str, Any]:
    """
    Compute a symbolic expression with given variable values.

    This is an L9 tool executor function.

    Args:
        expression: Mathematical expression (e.g., "x**2 + sin(x)")
        variables: Variable values (e.g., {"x": 1.0})
        backend: Computational backend ("numpy", "math", "mpmath", "sympy")

    Returns:
        Dict with computation result
    """
    tool = SymbolicComputationTool()
    return await tool.compute(
        expression=expression,
        variables=variables,
        backend=backend,
        **kwargs,
    )


@register_tool(category="symbolic", priority=10, description="symbolic_codegen tool")
@register_tool(category="symbolic", priority=10, description="symbolic_codegen tool")
@must_stay_async("callers use await")
async def symbolic_codegen(
    expression: str,
    variables: list[str],
    language: str = "C",
    function_name: str = "generated_func",
    compile: bool = False,
    **kwargs: Any,
) -> dict[str, Any]:
    """
    Generate code from a symbolic expression.

    This is an L9 tool executor function.

    Args:
        expression: Mathematical expression
        variables: List of variable names
        language: Target language ("C", "Fortran", "Python", "Cython")
        function_name: Name for generated function
        compile: Whether to compile the code

    Returns:
        Dict with generated code
    """
    tool = SymbolicComputationTool()
    return await tool.generate_code(
        expression=expression,
        variables=variables,
        language=language,
        function_name=function_name,
        compile=compile,
        **kwargs,
    )


def symbolic_optimize(
    expression: str,
    strategies: list[str] | None = None,
    **kwargs: Any,
) -> dict[str, Any]:
    """
    Optimize a symbolic expression for faster evaluation.

    This is an L9 tool executor function.

    Args:
        expression: Mathematical expression
        strategies: Optimization strategies ("simplify", "expand", "factor", "cse")

    Returns:
        Dict with original and optimized expressions
    """
    tool = SymbolicComputationTool()
    return tool.optimize(
        expression=expression,
        strategies=strategies,
        **kwargs,
    )


# Runtime execution trace - updated automatically on every execution
