"""
Core symbolic computation functionality.

Implements high-performance symbolic-to-numeric conversion using SymPy utilities.
Provides production-ready interfaces for AI agents to perform mathematical computations.
"""

import asyncio
import time
from typing import Dict, List, Optional, Union, Any, Callable
from functools import lru_cache
import structlog

import sympy as sp
from sympy.utilities.lambdify import lambdify
from sympy.utilities.autowrap import autowrap
from sympy.utilities.codegen import codegen
from sympy.utilities.memoization import recurrence_memo

from .models import (
    ComputationRequest,
    ComputationResult,
    CodeGenRequest,
    CodeGenResult,
    BackendType,
    CodeLanguage,
)
from .exceptions import SymbolicComputationError, EvaluationError, CodeGenerationError
from .logger import get_logger


logger = structlog.get_logger(__name__)
logger = get_logger(__name__)


class ExpressionCache:
    """Thread-safe expression cache using LRU strategy."""

    def __init__(self, maxsize: int = 128):
        """Initialize cache with maximum size."""
        self._cache: Dict[str, Callable] = {}
        self._maxsize = maxsize

    @lru_cache(maxsize=128)
    def get_lambdified(
        self,
        expression: str,
        variables: tuple,
        backend: str
    ) -> Callable:
        """
        Get or create lambdified function with caching.

        Args:
            expression: SymPy expression string
            variables: Tuple of variable names
            backend: Computational backend

        Returns:
            Compiled numerical function
        """
        key = f"{expression}_{variables}_{backend}"
        logger.debug(f"Cache lookup for: {key}")

        try:
            # Parse expression
            expr = sp.sympify(expression)

            # Create symbols
            syms = [sp.Symbol(var) for var in variables]

            # Lambdify with specified backend
            func = lambdify(syms, expr, backend)

            logger.info(f"Lambdified expression: {expression} with backend: {backend}")
            return func

        except Exception as e:
            logger.error(f"Failed to lambdify expression: {str(e)}")
            raise EvaluationError(f"Lambdify failed: {str(e)}")


class ExpressionEvaluator:
    """
    High-performance symbolic expression evaluator.

    Uses SymPy's lambdify for fast numerical evaluation with caching.
    """

    def __init__(self, cache_size: int = 128):
        """
        Initialize evaluator.

        Args:
            cache_size: Maximum number of cached expressions
        """
        self._cache = ExpressionCache(maxsize=cache_size)
        self._metrics: Dict[str, int] = {
            "total_evaluations": 0,
            "cache_hits": 0,
            "cache_misses": 0,
        }

    async def evaluate(
        self,
        request: ComputationRequest
    ) -> ComputationResult:
        """
        Evaluate symbolic expression asynchronously.

        Args:
            request: Computation request with expression and values

        Returns:
            Computation result with numerical values
        """
        start_time = time.time()

        try:
            # Get or create lambdified function
            func = self._cache.get_lambdified(
                request.expression,
                tuple(request.variables),
                request.backend.value
            )

            # Extract values in correct order
            values = [request.values[var] for var in request.variables]

            # Execute computation
            result = await asyncio.to_thread(func, *values)

            execution_time = (time.time() - start_time) * 1000

            self._metrics["total_evaluations"] += 1

            logger.info(
                f"Evaluation successful: {request.expression} = {result} "
                f"({execution_time:.2f}ms)"
            )

            return ComputationResult(
                success=True,
                result=float(result) if hasattr(result, '__float__') else result,
                expression_str=request.expression,
                backend_used=request.backend,
                execution_time_ms=execution_time,
                metadata={"metrics": self._metrics.copy()}
            )

        except Exception as e:
            execution_time = (time.time() - start_time) * 1000
            logger.error(f"Evaluation failed: {str(e)}")

            return ComputationResult(
                success=False,
                result=None,
                expression_str=request.expression,
                backend_used=request.backend,
                execution_time_ms=execution_time,
                error_message=str(e),
                metadata={"metrics": self._metrics.copy()}
            )

    def evaluate_sync(
        self,
        request: ComputationRequest
    ) -> ComputationResult:
        """
        Synchronous version of evaluate.

        Args:
            request: Computation request

        Returns:
            Computation result
        """
        return asyncio.run(self.evaluate(request))

    def get_metrics(self) -> Dict[str, int]:
        """Get evaluation metrics."""
        return self._metrics.copy()


class CodeGenerator:
    """
    Code generator for symbolic expressions.

    Generates optimized, compilable code in various languages using
    SymPy's codegen and autowrap utilities.
    """

    def __init__(self):
        """Initialize code generator."""
        self._generated_count = 0

    async def generate(
        self,
        request: CodeGenRequest
    ) -> CodeGenResult:
        """
        Generate code from symbolic expression.

        Args:
            request: Code generation request

        Returns:
            Generated code and compilation status
        """
        start_time = time.time()

        try:
            # Parse expression
            expr = sp.sympify(request.expression)

            # Create symbols
            syms = [sp.Symbol(var) for var in request.variables]

            if request.compile and request.language == CodeLanguage.PYTHON:
                # Use autowrap for compiled Python extensions
                compiled_func = await asyncio.to_thread(
                    autowrap,
                    expr,
                    args=syms,
                    backend='cython',
                    tempdir='/tmp/sympy_autowrap'
                )

                logger.info(f"Compiled function using autowrap: {request.function_name}")

                return CodeGenResult(
                    success=True,
                    source_code=f"# Compiled using Cython\n# Expression: {request.expression}",
                    language=request.language,
                    compiled=True,
                    compilation_output="Cython compilation successful",
                    metadata={
                        "function": request.function_name,
                        "variables": request.variables
                    }
                )

            else:
                # Use codegen for source code generation
                code_result = await asyncio.to_thread(
                    codegen,
                    (request.function_name, expr),
                    request.language.value,
                    header=True,
                    empty=False
                )

                # Extract source code
                source_code = ""
                for filename, code in code_result:
                    source_code += f"// File: {filename}\n{code}\n\n"

                self._generated_count += 1

                logger.info(
                    f"Generated {request.language.value} code for: "
                    f"{request.function_name}"
                )

                return CodeGenResult(
                    success=True,
                    source_code=source_code,
                    language=request.language,
                    compiled=False,
                    metadata={
                        "function": request.function_name,
                        "variables": request.variables,
                        "generated_count": self._generated_count
                    }
                )

        except Exception as e:
            logger.error(f"Code generation failed: {str(e)}")

            return CodeGenResult(
                success=False,
                source_code=None,
                language=request.language,
                compiled=False,
                error_message=str(e)
            )

    def generate_sync(
        self,
        request: CodeGenRequest
    ) -> CodeGenResult:
        """
        Synchronous version of generate.

        Args:
            request: Code generation request

        Returns:
            Code generation result
        """
        return asyncio.run(self.generate(request))


class SymbolicComputation:
    """
    Main interface for symbolic computation operations.

    Provides unified access to expression evaluation and code generation
    capabilities for AI agents.
    """

    def __init__(
        self,
        cache_size: int = 128,
        enable_metrics: bool = True
    ):
        """
        Initialize symbolic computation engine.

        Args:
            cache_size: Size of expression cache
            enable_metrics: Enable performance metrics
        """
        self.evaluator = ExpressionEvaluator(cache_size=cache_size)
        self.codegen = CodeGenerator()
        self._enable_metrics = enable_metrics

        logger.info("SymbolicComputation engine initialized")

    async def compute(
        self,
        expression: str,
        variables: Dict[str, Union[float, List[float]]],
        backend: str = "numpy"
    ) -> ComputationResult:
        """
        Compute symbolic expression with given variable values.

        Args:
            expression: Mathematical expression
            variables: Variable values
            backend: Numerical backend

        Returns:
            Computation result
        """
        request = ComputationRequest(
            expression=expression,
            variables=list(variables.keys()),
            backend=BackendType(backend),
            values=variables
        )

        return await self.evaluator.evaluate(request)

    async def generate_code(
        self,
        expression: str,
        variables: List[str],
        language: str = "C",
        function_name: str = "generated_func",
        compile: bool = False
    ) -> CodeGenResult:
        """
        Generate code from symbolic expression.

        Args:
            expression: Mathematical expression
            variables: Input variables
            language: Target language
            function_name: Name for generated function
            compile: Whether to compile code

        Returns:
            Code generation result
        """
        request = CodeGenRequest(
            expression=expression,
            variables=variables,
            language=CodeLanguage(language),
            function_name=function_name,
            compile=compile
        )

        return await self.codegen.generate(request)

    async def health_check(self) -> Dict[str, Any]:
        """
        Perform health check on symbolic computation engine.

        Returns:
            Health status dictionary
        """
        try:
            # Test basic computation
            test_result = await self.compute(
                "x + 1",
                {"x": 1.0},
                backend="numpy"
            )

            return {
                "status": "healthy" if test_result.success else "degraded",
                "evaluator_metrics": self.evaluator.get_metrics(),
                "cache_size": 128,
                "test_computation": test_result.success
            }

        except Exception as e:
            logger.error(f"Health check failed: {str(e)}")
            return {
                "status": "unhealthy",
                "error": str(e)
            }



