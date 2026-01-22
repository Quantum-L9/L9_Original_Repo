"""
L9 Symbolic Computation Tool
============================

L9 Tool wrapper for symbolic computation capabilities.
Provides compute and codegen tool functions for L-CTO and agents.

Version: 1.0.0
"""

from __future__ import annotations

# ============================================================================
__dora_meta__ = {
    "component_name": "Symbolic Tool",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2026-01-02T15:15:57Z",
    "updated_at": "2026-01-07T13:35:57Z",
    "layer": "foundation",
    "domain": "tool_registry",
    "module_name": "symbolic_tool",
    "type": "adapter",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": [],
        "memory_layers": [],
        "imported_by": ["runtime.l_tools"],
    },
}
# ============================================================================

from typing import Any, Dict, List, Optional, Union

import structlog

from runtime.tool_registry import register_tool
from services.symbolic_computation import (CodeGenResult, ComputationResult,
                                           SymbolicComputation)

logger = structlog.get_logger(__name__)

# Global singleton instance
_symbolic_engine: Optional[SymbolicComputation] = None


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
        variables: Dict[str, Union[float, List[float]]],
        backend: str = "numpy",
        **kwargs: Any,
    ) -> Dict[str, Any]:
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

    async def generate_code(
        self,
        expression: str,
        variables: List[str],
        language: str = "C",
        function_name: str = "generated_func",
        compile: bool = False,
        **kwargs: Any,
    ) -> Dict[str, Any]:
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

    async def health_check(self) -> Dict[str, Any]:
        """
        Check health of symbolic computation engine.

        Returns:
            Health status dict
        """
        return await self._engine.health_check()

    def optimize(
        self,
        expression: str,
        strategies: Optional[List[str]] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
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
                    replacements, reduced = cse(optimized)
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
async def symbolic_compute(
    expression: str,
    variables: Dict[str, Union[float, List[float]]],
    backend: str = "numpy",
    **kwargs: Any,
) -> Dict[str, Any]:
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
async def symbolic_codegen(
    expression: str,
    variables: List[str],
    language: str = "C",
    function_name: str = "generated_func",
    compile: bool = False,
    **kwargs: Any,
) -> Dict[str, Any]:
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
    strategies: Optional[List[str]] = None,
    **kwargs: Any,
) -> Dict[str, Any]:
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


# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "COR-FOUN-020",
    "governance_level": "critical",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": [
        "adapter",
        "async",
        "caching",
        "foundation",
        "logging",
        "messaging",
        "metrics",
        "tool-registry",
    ],
    "keywords": [
        "check",
        "codegen",
        "computation",
        "compute",
        "engine",
        "generate",
        "health",
        "optimize",
    ],
    "business_value": "Provides compute and codegen tool functions for L-CTO and agents. Version: 1.0.0",
    "last_modified": "2026-01-07T13:35:57Z",
    "modified_by": "L9_Codegen_Engine",
    "change_summary": "Initial generation with DORA compliance",
}
# ============================================================================
# L9 DORA BLOCK - AUTO-UPDATED - DO NOT EDIT
# Runtime execution trace - updated automatically on every execution
# ============================================================================
__l9_trace__ = {
    "trace_id": "",
    "task": "",
    "timestamp": "",
    "patterns_used": [],
    "graph": {"nodes": [], "edges": []},
    "inputs": {},
    "outputs": {},
    "metrics": {"confidence": "", "errors_detected": [], "stability_score": ""},
}
# ============================================================================
# END L9 DORA BLOCK
# ============================================================================
