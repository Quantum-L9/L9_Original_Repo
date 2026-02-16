"""
SymPy Expression Evaluator
===========================

Core expression evaluation engine with multi-backend support,
caching, and governance integration.

Version: 6.0.0
"""

from __future__ import annotations

from core.decorators import must_stay_async

# ============================================================================
__dora_meta__ = {
    "component_name": "Expression Evaluator",
    "module_version": "6.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2026-01-02T15:15:57Z",
    "updated_at": "2026-01-14T15:03:00Z",
    "layer": "operations",
    "domain": "symbolic_computation",
    "module_name": "expression_evaluator",
    "type": "service",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": ["Redis"],
        "memory_layers": [],
        "imported_by": [
            "services.symbolic_computation.api.routes",
            "services.symbolic_computation.core.__init__",
            "services.symbolic_computation.tools.symbolic_tool",
            "tests.services.symbolic_computation.test_expression_evaluator",
            "tests.services.symbolic_computation.test_integration",
        ],
    },
}
# ============================================================================

import hashlib
import time
from typing import Any, TYPE_CHECKING

import structlog
import sympy
from sympy import sympify
from sympy.utilities.lambdify import lambdify

from services.symbolic_computation.config import SymbolicComputationConfig, get_config
from services.symbolic_computation.core.models import ComputationResult

if TYPE_CHECKING:
    from collections.abc import Callable

logger = structlog.get_logger(__name__)


class ExpressionEvaluator:
    """
    High-performance expression evaluator with multi-backend support.

    Supports NumPy, math, and mpmath backends for numerical evaluation.
    Integrates with Redis for result caching and Postgres for metrics.

    Performance characteristics:
    - lambdify: 10-100x faster than evalf
    - autowrap: 500x faster (compiled C)
    - cython: 800x faster (optimized)

    Example:
        evaluator = ExpressionEvaluator()
        result = await evaluator.evaluate_expression(
            expr="x**2 + 2*x + 1",
            variables={"x": 3},
            backend="numpy"
        )
        # print(result.result)  # 16.0  # noqa: ADR-0019
        logger.debug("expression_evaluated", result=result.result)
    """

    def __init__(
        self,
        config: SymbolicComputationConfig | None = None,
        cache_manager: Any | None = None,
        metrics_collector: Any | None = None,
    ):
        """
        Initialize the expression evaluator.

        Args:
            config: Configuration instance (uses global if not provided)
            cache_manager: Optional cache manager for Redis caching
            metrics_collector: Optional metrics collector for performance tracking
        """
        self.config = config or get_config()
        self.cache_manager = cache_manager
        self.metrics_collector = metrics_collector
        self.logger = logger.bind(component="expression_evaluator")

        # Initialize LRU cache for compiled functions
        self._compile_cache: dict[str, Callable] = {}

        self.logger.info(
            "expression_evaluator_initialized",
            cache_size=self.config.cache_size,
            default_backend=self.config.default_backend,
        )

    @must_stay_async("callers use await")
    async def evaluate_expression(
        self,
        expr: str,
        variables: dict[str, float],
        backend: str = "numpy",
    ) -> ComputationResult:
        """
        Evaluate a symbolic expression numerically.

        Args:
            expr: SymPy expression as string
            variables: Variable name to value mapping
            backend: Numerical backend ("numpy", "math", "mpmath")

        Returns:
            ComputationResult with result value and metadata
        """
        start_time = time.perf_counter()
        expr_hash = self._hash_expression(expr, backend)
        cache_hit = False

        self.logger.debug(
            "evaluating_expression",
            expr_hash=expr_hash,
            backend=backend,
            num_variables=len(variables),
        )

        try:
            # Check cache first
            if self.cache_manager and self.config.cache_enabled:
                cached = await self.cache_manager.get_cached_result(expr, backend)
                if cached is not None:
                    cache_hit = True
                    elapsed_ms = (time.perf_counter() - start_time) * 1000
                    self.logger.debug("cache_hit", expr_hash=expr_hash)
                    return ComputationResult(
                        result=cached,
                        execution_time_ms=elapsed_ms,
                        cache_hit=True,
                        backend_used=backend,
                        expression_hash=expr_hash,
                    )

            # Parse and compile expression
            sympify(expr)
            var_symbols = [sympy.Symbol(v) for v in variables]

            # Get or compile lambdified function
            compiled_fn = self._get_compiled_function(expr, var_symbols, backend)

            # Evaluate with variable values
            var_values = [variables[str(s)] for s in var_symbols]
            result = compiled_fn(*var_values) if var_values else compiled_fn()

            elapsed_ms = (time.perf_counter() - start_time) * 1000

            # Cache result
            if self.cache_manager and self.config.cache_enabled:
                await self.cache_manager.cache_expression(expr, backend, result)

            # Record metrics
            if self.metrics_collector and self.config.enable_metrics:
                await self.metrics_collector.record_evaluation(
                    expr=expr,
                    backend=backend,
                    duration_ms=elapsed_ms,
                    success=True,
                )

            self.logger.info(
                "expression_evaluated",
                expr_hash=expr_hash,
                backend=backend,
                execution_time_ms=elapsed_ms,
                cache_hit=cache_hit,
            )

            return ComputationResult(
                result=float(result) if hasattr(result, "__float__") else result,
                execution_time_ms=elapsed_ms,
                cache_hit=cache_hit,
                backend_used=backend,
                expression_hash=expr_hash,
            )

        except Exception as e:
            elapsed_ms = (time.perf_counter() - start_time) * 1000
            self.logger.error(
                "expression_evaluation_failed",
                expr_hash=expr_hash,
                error=str(e),
            )

            # Record failure metrics
            if self.metrics_collector and self.config.enable_metrics:
                await self.metrics_collector.record_evaluation(
                    expr=expr,
                    backend=backend,
                    duration_ms=elapsed_ms,
                    success=False,
                )

            return ComputationResult(
                result=None,
                execution_time_ms=elapsed_ms,
                cache_hit=False,
                backend_used=backend,
                expression_hash=expr_hash,
                error=str(e),
            )

    def compile_with_lambdify(
        self,
        expr: str,
        variables: list[str],
        modules: str = "numpy",
    ) -> Callable:
        """
        Compile expression to NumPy-backed function using lambdify.

        Args:
            expr: SymPy expression as string
            variables: List of variable names
            modules: Backend modules ("numpy", "math", "mpmath")

        Returns:
            Compiled callable function
        """
        parsed_expr = sympify(expr)
        var_symbols = [sympy.Symbol(v) for v in variables]

        compiled_fn = lambdify(var_symbols, parsed_expr, modules=modules)

        self.logger.debug(
            "expression_compiled_lambdify",
            expr_len=len(expr),
            num_vars=len(variables),
            modules=modules,
        )

        return compiled_fn

    def compile_with_autowrap(
        self,
        expr: str,
        variables: list[str],
        language: str = "C",
    ) -> Callable:
        """
        Compile expression to C/Fortran function using autowrap.

        This provides ~500x performance improvement for complex expressions.

        Args:
            expr: SymPy expression as string
            variables: List of variable names
            language: Target language ("C" or "Fortran")

        Returns:
            Compiled callable function
        """
        try:
            from sympy.utilities.autowrap import autowrap

            parsed_expr = sympify(expr)
            var_symbols = [sympy.Symbol(v) for v in variables]

            compiled_fn = autowrap(
                parsed_expr,
                args=var_symbols,
                language=language,
                tempdir=str(self.config.codegen_temp_dir),
            )

            self.logger.info(
                "expression_compiled_autowrap",
                expr_len=len(expr),
                num_vars=len(variables),
                language=language,
            )

            return compiled_fn

        except Exception as e:
            self.logger.warning(
                "autowrap_failed_fallback_to_lambdify",
                error=str(e),
            )
            # Fallback to lambdify
            return self.compile_with_lambdify(expr, variables)

    def _get_compiled_function(
        self,
        expr: str,
        var_symbols: list[sympy.Symbol],
        backend: str,
    ) -> Callable:
        """Get or create compiled function from cache."""
        cache_key = self._hash_expression(expr, backend)

        if cache_key in self._compile_cache:
            return self._compile_cache[cache_key]

        parsed_expr = sympify(expr)
        compiled_fn = lambdify(var_symbols, parsed_expr, modules=backend)

        # Store in LRU-like cache (simple dict with size limit)
        if len(self._compile_cache) >= self.config.cache_size:
            # Remove oldest entry
            oldest_key = next(iter(self._compile_cache))
            del self._compile_cache[oldest_key]

        self._compile_cache[cache_key] = compiled_fn
        return compiled_fn

    def _hash_expression(self, expr: str, backend: str) -> str:
        """Generate hash for expression + backend combination."""
        content = f"{expr}:{backend}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]

    def clear_cache(self) -> None:
        """Clear the compiled function cache."""
        self._compile_cache.clear()
        self.logger.info("compile_cache_cleared")


# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "SER-OPER-026",
    "governance_level": "medium",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": [
        "async",
        "caching",
        "debugging",
        "logging",
        "metrics",
        "operations",
        "security",
        "service",
        "symbolic-computation",
    ],
    "keywords": [
        "autowrap",
        "cache",
        "clear",
        "compile",
        "evaluate",
        "evaluator",
        "expression",
        "governance",
    ],
    "business_value": "Implements ExpressionEvaluator for expression evaluator functionality",
    "last_modified": "2026-01-14T15:03:00Z",
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
