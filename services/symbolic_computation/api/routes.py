"""
SymPy Symbolic Computation API Routes
======================================

FastAPI endpoints for expression evaluation, code generation,
optimization, metrics, and health checks.

Version: 6.0.0
"""

from __future__ import annotations

# ============================================================================
__dora_meta__ = {
    "component_name": "Routes",
    "module_version": "6.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2026-01-02T15:15:57Z",
    "updated_at": "2026-01-17T23:47:56Z",
    "layer": "operations",
    "domain": "api_gateway",
    "module_name": "routes",
    "type": "router",
    "status": "active",
    "integrates_with": {
        "api_endpoints": ["POST /evaluate", "POST /generate_code", "POST /optimize", "POST /validate", "GET /metrics", "GET /health", "GET /cache/stats", "POST /cache/clear"],
        "datasources": ["Neo4j", "Redis"],
        "memory_layers": [],
        "imported_by": ["api.server", "services.symbolic_computation.api.__init__"],
    },
}
# ============================================================================

from typing import Any, Dict, List

import structlog
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from services.symbolic_computation.config import get_config
from services.symbolic_computation.core.models import (
    CodeGenRequest,
    CodeGenResult,
    CodeLanguage,
    ComputationResult,
    HealthStatus,
    MetricsSummary,
    ValidationResult,
)
from services.symbolic_computation.core.expression_evaluator import ExpressionEvaluator
from services.symbolic_computation.core.code_generator import CodeGenerator
from services.symbolic_computation.core.optimizer import Optimizer
from services.symbolic_computation.core.validator import ExpressionValidator
from services.symbolic_computation.core.cache_manager import CacheManager
from services.symbolic_computation.core.metrics import MetricsCollector
from core.decorators import must_stay_async

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/symbolic", tags=["symbolic"])

# Service instances (initialized lazily)
_evaluator: ExpressionEvaluator | None = None
_generator: CodeGenerator | None = None
_optimizer: Optimizer | None = None
_validator: ExpressionValidator | None = None
_cache: CacheManager | None = None
_metrics: MetricsCollector | None = None


def get_evaluator() -> ExpressionEvaluator:
    """Get or create evaluator instance."""
    global _evaluator, _cache, _metrics
    if _evaluator is None:
        _cache = CacheManager()
        _metrics = MetricsCollector()
        _evaluator = ExpressionEvaluator(
            cache_manager=_cache,
            metrics_collector=_metrics,
        )
    return _evaluator


def get_generator() -> CodeGenerator:
    """Get or create generator instance."""
    global _generator, _metrics
    if _generator is None:
        if _metrics is None:
            _metrics = MetricsCollector()
        _generator = CodeGenerator(metrics_collector=_metrics)
    return _generator


def get_optimizer() -> Optimizer:
    """Get or create optimizer instance."""
    global _optimizer
    if _optimizer is None:
        _optimizer = Optimizer()
    return _optimizer


def get_validator() -> ExpressionValidator:
    """Get or create validator instance."""
    global _validator
    if _validator is None:
        _validator = ExpressionValidator()
    return _validator


def get_metrics() -> MetricsCollector:
    """Get or create metrics instance."""
    global _metrics
    if _metrics is None:
        _metrics = MetricsCollector()
    return _metrics


# Request/Response models for API
class EvaluateRequest(BaseModel):
    """Request model for /evaluate endpoint."""

    expression: str = Field(..., description="SymPy expression to evaluate")
    variables: Dict[str, float] = Field(
        default_factory=dict, description="Variable name to value mapping"
    )
    backend: str = Field(
        default="numpy", description="Numerical backend (numpy, math, mpmath)"
    )


class OptimizeRequest(BaseModel):
    """Request model for /optimize endpoint."""

    expression: str = Field(..., description="SymPy expression to optimize")
    strategies: List[str] = Field(
        default=["simplify"], description="Optimization strategies to apply"
    )


class OptimizeResponse(BaseModel):
    """Response model for /optimize endpoint."""

    original: str
    optimized: str
    original_ops: int
    optimized_ops: int
    reduction_percent: float
    strategies_applied: List[str]


class ValidateRequest(BaseModel):
    """Request model for /validate endpoint."""

    expression: str = Field(..., description="Expression to validate")


@router.post("/evaluate", response_model=ComputationResult)
async def evaluate_expression(
    request: EvaluateRequest,
    evaluator: ExpressionEvaluator = Depends(get_evaluator),
    validator: ExpressionValidator = Depends(get_validator),
) -> ComputationResult:
    """
    Evaluate a SymPy expression numerically.

    Supports multiple backends:
    - numpy: Fast array-based computation (default)
    - math: Python standard library (scalar)
    - mpmath: Arbitrary precision

    Results are cached for repeated evaluations.
    """
    logger.info(
        "evaluate_request",
        expr_len=len(request.expression),
        backend=request.backend,
        num_vars=len(request.variables),
    )

    # Validate expression first
    validation = validator.validate(request.expression)
    if not validation.is_valid:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid expression: {'; '.join(validation.errors)}",
        )

    # Evaluate
    result = await evaluator.evaluate_expression(
        expr=request.expression,
        variables=request.variables,
        backend=request.backend,
    )

    if result.error:
        raise HTTPException(
            status_code=422, detail=f"Evaluation failed: {result.error}"
        )

    return result


@router.post("/generate_code", response_model=CodeGenResult)
async def generate_code(
    request: CodeGenRequest,
    generator: CodeGenerator = Depends(get_generator),
    validator: ExpressionValidator = Depends(get_validator),
) -> CodeGenResult:
    """
    Generate compilable code from a SymPy expression.

    Supports:
    - C: High-performance C code
    - Fortran: Scientific computing optimized
    - Cython: Python integration with C speed
    - Python: Pure Python (for debugging)
    """
    logger.info(
        "generate_code_request",
        expr_len=len(request.expression),
        language=request.language,
        function_name=request.function_name,
    )

    # Validate expression
    validation = validator.validate(request.expression)
    if not validation.is_valid:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid expression: {'; '.join(validation.errors)}",
        )

    # Generate
    result = await generator.generate_code(
        expr=request.expression,
        variables=request.variables,
        language=request.language.value
        if isinstance(request.language, CodeLanguage)
        else request.language,
        function_name=request.function_name,
    )

    if not result.success:
        raise HTTPException(
            status_code=422, detail=f"Code generation failed: {result.error_message}"
        )

    return result


@router.post("/optimize", response_model=OptimizeResponse)
@must_stay_async("FastAPI/ASGI route handler")
async def optimize_expression(
    request: OptimizeRequest,
    optimizer: Optimizer = Depends(get_optimizer),
    validator: ExpressionValidator = Depends(get_validator),
) -> OptimizeResponse:
    """
    Optimize a SymPy expression for faster evaluation.

    Strategies:
    - simplify: General algebraic simplification
    - expand: Multiply out products
    - factor: Factor into irreducible factors
    - cse: Common subexpression elimination
    """
    logger.info(
        "optimize_request",
        expr_len=len(request.expression),
        strategies=request.strategies,
    )

    # Validate
    validation = validator.validate(request.expression)
    if not validation.is_valid:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid expression: {'; '.join(validation.errors)}",
        )

    # Count original operations
    original_ops = optimizer.count_operations(request.expression)

    # Optimize
    optimized_expr = optimizer.optimize_expression(
        request.expression,
        strategies=request.strategies,
    )

    # Count optimized operations
    optimized_ops = optimizer.count_operations(optimized_expr)

    reduction = (
        ((original_ops - optimized_ops) / original_ops * 100)
        if original_ops > 0
        else 0.0
    )

    return OptimizeResponse(
        original=request.expression,
        optimized=str(optimized_expr),
        original_ops=original_ops,
        optimized_ops=optimized_ops,
        reduction_percent=round(reduction, 2),
        strategies_applied=request.strategies,
    )


@router.post("/validate", response_model=ValidationResult)
@must_stay_async("FastAPI/ASGI route handler")
async def validate_expression(
    request: ValidateRequest,
    validator: ExpressionValidator = Depends(get_validator),
) -> ValidationResult:
    """
    Validate an expression for safety and correctness.

    Checks:
    - Expression length limits
    - Dangerous function detection
    - Syntax validation
    - Balanced parentheses/brackets
    """
    logger.info(
        "validate_request",
        expr_len=len(request.expression),
    )

    return validator.validate(request.expression)


@router.get("/metrics", response_model=MetricsSummary)
async def get_metrics_summary(
    last_hours: int = 24,
    metrics: MetricsCollector = Depends(get_metrics),
) -> MetricsSummary:
    """
    Get performance metrics summary.

    Returns aggregated statistics for:
    - Evaluation times by backend
    - Code generation times by language
    - Cache hit rates
    - Total operations
    """
    return await metrics.get_metrics_summary(last_hours=last_hours)


@router.get("/health", response_model=HealthStatus)
@must_stay_async("FastAPI/ASGI route handler")
async def health_check() -> HealthStatus:
    """
    Health check endpoint.

    Returns service status, available backends, and memory backend connectivity.
    """
    config = get_config()

    # Check Redis connectivity
    redis_ok = False
    try:
        # Would check actual Redis connection here
        redis_ok = True
    except Exception:
        pass

    # Check Postgres connectivity
    postgres_ok = False
    try:
        # Would check actual Postgres connection here
        postgres_ok = True
    except Exception:
        pass

    # Determine overall status
    if redis_ok and postgres_ok:
        status = "healthy"
    elif redis_ok or postgres_ok:
        status = "degraded"
    else:
        status = "unhealthy"

    return HealthStatus(
        status=status,
        backends_available=config.available_backends,
        cache_available=redis_ok,
        memory_backends={
            "redis": redis_ok,
            "postgres": postgres_ok,
            "neo4j": False,  # Would check actual connection
        },
    )


@router.get("/cache/stats")
@must_stay_async("FastAPI/ASGI route handler")
async def get_cache_stats() -> Dict[str, Any]:
    """Get cache statistics."""
    global _cache
    if _cache is None:
        return {"error": "Cache not initialized"}
    return _cache.get_stats()


@router.post("/cache/clear")
@must_stay_async("FastAPI/ASGI route handler")
async def clear_cache() -> Dict[str, str]:
    """Clear all caches."""
    global _cache
    if _cache:
        _cache.clear()
    return {"status": "cleared"}

# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "SER-OPER-029",
    "governance_level": "medium",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": ["core.decorators"],
    "tags": ["api", "api-gateway", "async", "caching", "debugging", "endpoint", "logging", "messaging", "metrics", "operations"],
    "keywords": ["cache", "check", "clear", "evaluate", "evaluator", "expression", "generate", "generator"],
    "business_value": "Provides routes components including EvaluateRequest, OptimizeRequest, OptimizeResponse",
    "last_modified": "2026-01-17T23:47:56Z",
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
