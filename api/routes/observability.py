"""
Observability API Router.

Exposes telemetry, metrics, failures, and circuit breaker status via REST API.

GMP-91: Created to expose core/observability service via HTTP endpoints.
"""

# ============================================================================
__dora_meta__ = {
    "component_name": "Observability",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2026-01-17T14:57:53Z",
    "updated_at": "2026-01-17T23:47:56Z",
    "layer": "operations",
    "domain": "api_gateway",
    "module_name": "observability",
    "type": "router",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [
            "GET /metrics",
            "GET /failures",
            "GET /spans",
            "GET /health",
            "GET /circuit-breakers",
        ],
        "datasources": [],
        "memory_layers": [],
        "imported_by": ["api.server"],
    },
}
# ============================================================================

from typing import List, Optional, Dict, Any
from datetime import datetime
from fastapi import APIRouter, Query
from pydantic import BaseModel, Field

from core.decorators import must_stay_async

router = APIRouter(tags=["observability"])

# AUTO-REGISTRATION (Phase 2 Auto-Wiring)
from api.routes.registry import router_registry

router_registry.register(
    router=router,
    prefix="/observability",
    tags=["observability"],
    display_name="Observability SRE",
)


# ============================================================================
# Response Models
# ============================================================================


class SREMetricsResponse(BaseModel):
    """Response for SRE metrics endpoint."""

    span_count: int = 0
    error_count: int = 0
    error_rate: float = 0.0
    p50_latency_ms: float = 0
    p95_latency_ms: float = 0
    p99_latency_ms: float = 0
    timestamp: str = ""


class FailureResponse(BaseModel):
    """Response for a single failure signal."""

    failure_class: str
    span_id: str
    trace_id: str
    timestamp: datetime
    context: Dict[str, Any] = Field(default_factory=dict)
    auto_recovery_applied: bool = False
    recovery_action: Optional[str] = None


class FailuresListResponse(BaseModel):
    """Response for failures list endpoint."""

    failures: List[FailureResponse]
    total: int


class SpanSummary(BaseModel):
    """Summary of a span for API response."""

    trace_id: str
    span_id: str
    name: str
    kind: str
    status: str
    start_time: datetime
    duration_ms: Optional[float] = None
    error: Optional[str] = None


class SpansListResponse(BaseModel):
    """Response for spans list endpoint."""

    spans: List[SpanSummary]
    total: int


class CircuitBreakerStatus(BaseModel):
    """Status of a circuit breaker."""

    name: str
    state: str  # CLOSED, OPEN, HALF_OPEN
    failure_count: int
    success_count: int
    last_failure_time: Optional[datetime] = None
    recovery_time: Optional[datetime] = None


class CircuitBreakersResponse(BaseModel):
    """Response for circuit breakers endpoint."""

    circuit_breakers: List[CircuitBreakerStatus]


class HealthResponse(BaseModel):
    """Response for observability health endpoint."""

    status: str  # healthy, degraded, unhealthy
    service_initialized: bool
    exporters_active: List[str]
    prometheus_enabled: bool
    jaeger_enabled: bool
    span_count: int
    failure_count: int
    timestamp: str


# ============================================================================
# Endpoints
# ============================================================================


@router.get("/metrics", response_model=SREMetricsResponse)
@must_stay_async("FastAPI route handler")
async def get_metrics() -> SREMetricsResponse:
    """
    Get SRE metrics computed from recent spans.

    Returns latency percentiles (p50, p95, p99), error rates, and span counts.
    """
    from core.observability.service import get_observability_service

    service = get_observability_service()
    if not service:
        return SREMetricsResponse(
            timestamp=datetime.utcnow().isoformat(),
        )

    metrics = await service.compute_metrics()
    return SREMetricsResponse(
        span_count=metrics.get("span_count", 0),
        error_count=metrics.get("error_count", 0),
        error_rate=metrics.get("error_rate", 0.0),
        p50_latency_ms=metrics.get("p50_latency_ms", 0),
        p95_latency_ms=metrics.get("p95_latency_ms", 0),
        p99_latency_ms=metrics.get("p99_latency_ms", 0),
        timestamp=metrics.get("timestamp", datetime.utcnow().isoformat()),
    )


@router.get("/failures", response_model=FailuresListResponse)
@must_stay_async("FastAPI route handler")
async def get_failures(
    limit: int = Query(
        default=100, ge=1, le=1000, description="Max failures to return"
    ),
    failure_class: Optional[str] = Query(
        default=None, description="Filter by failure class"
    ),
) -> FailuresListResponse:
    """
    Get recent failure signals detected by the observability system.

    Optionally filter by failure class (TOOL_TIMEOUT, TOOL_ERROR, etc.)
    """
    from core.observability.service import get_observability_service

    service = get_observability_service()
    if not service:
        return FailuresListResponse(failures=[], total=0)

    # Detect new failures first
    await service.detect_failures()

    failures = service.failures
    if failure_class:
        failures = [f for f in failures if f.failure_class.value == failure_class]

    # Apply limit
    failures = failures[-limit:]

    return FailuresListResponse(
        failures=[
            FailureResponse(
                failure_class=f.failure_class.value
                if hasattr(f.failure_class, "value")
                else str(f.failure_class),
                span_id=f.span_id,
                trace_id=f.trace_id,
                timestamp=f.timestamp,
                context=f.context,
                auto_recovery_applied=f.auto_recovery_applied,
                recovery_action=f.recovery_action,
            )
            for f in failures
        ],
        total=len(failures),
    )


@router.get("/spans", response_model=SpansListResponse)
@must_stay_async("FastAPI route handler")
async def get_spans(
    limit: int = Query(default=100, ge=1, le=1000, description="Max spans to return"),
    status: Optional[str] = Query(
        default=None, description="Filter by status (OK, ERROR, UNSET)"
    ),
    name_prefix: Optional[str] = Query(
        default=None, description="Filter by span name prefix"
    ),
) -> SpansListResponse:
    """
    Get recent spans from the observability service.

    Optionally filter by status or span name prefix.
    """
    from core.observability.service import get_observability_service

    service = get_observability_service()
    if not service:
        return SpansListResponse(spans=[], total=0)

    spans = service.spans

    # Apply filters
    if status:
        spans = [s for s in spans if s.status.value == status]
    if name_prefix:
        spans = [s for s in spans if s.name.startswith(name_prefix)]

    # Apply limit (most recent)
    spans = spans[-limit:]

    return SpansListResponse(
        spans=[
            SpanSummary(
                trace_id=s.trace_id,
                span_id=s.span_id,
                name=s.name,
                kind=s.kind.value if hasattr(s.kind, "value") else str(s.kind),
                status=s.status.value if hasattr(s.status, "value") else str(s.status),
                start_time=s.start_time,
                duration_ms=s.duration_ms,
                error=s.error,
            )
            for s in spans
        ],
        total=len(spans),
    )


@router.get("/health", response_model=HealthResponse)
@must_stay_async("FastAPI route handler")
async def get_health() -> HealthResponse:
    """
    Get observability service health status.

    Returns initialization status, active exporters, and span/failure counts.
    """
    from core.observability.service import get_observability_service

    service = get_observability_service()
    if not service:
        return HealthResponse(
            status="unhealthy",
            service_initialized=False,
            exporters_active=[],
            prometheus_enabled=False,
            jaeger_enabled=False,
            span_count=0,
            failure_count=0,
            timestamp=datetime.utcnow().isoformat(),
        )

    # Determine health status
    status = "healthy"
    if not service.exporters and not service._prometheus_exporter:
        status = "degraded"

    exporters_active = [type(e).__name__ for e in service.exporters]
    if service._prometheus_exporter:
        exporters_active.append("PrometheusExporter")
    if service._jaeger_exporter:
        exporters_active.append("JaegerExporter")

    return HealthResponse(
        status=status,
        service_initialized=True,
        exporters_active=exporters_active,
        prometheus_enabled=service._prometheus_exporter is not None,
        jaeger_enabled=service._jaeger_exporter is not None,
        span_count=len(service.spans),
        failure_count=len(service.failures),
        timestamp=datetime.utcnow().isoformat(),
    )


@router.get("/circuit-breakers", response_model=CircuitBreakersResponse)
@must_stay_async("FastAPI route handler")
async def get_circuit_breakers() -> CircuitBreakersResponse:
    """
    Get status of all circuit breakers in the system.

    Returns state (CLOSED/OPEN/HALF_OPEN) and statistics for each circuit breaker.
    """
    from core.observability.circuit_breaker import CircuitBreakerRegistry

    registry = CircuitBreakerRegistry.get_instance()
    if not registry:
        return CircuitBreakersResponse(circuit_breakers=[])

    breakers = []
    for name, cb in registry._breakers.items():
        stats = cb.get_stats()
        breakers.append(
            CircuitBreakerStatus(
                name=name,
                state=cb.get_state(),
                failure_count=stats.get("failure_count", 0),
                success_count=stats.get("success_count", 0),
                last_failure_time=stats.get("last_failure_time"),
                recovery_time=stats.get("recovery_time"),
            )
        )

    return CircuitBreakersResponse(circuit_breakers=breakers)


# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "API-OPER-020",
    "governance_level": "medium",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [
        "core.decorators",
        "core.observability.circuit_breaker",
        "core.observability.service",
    ],
    "tags": [
        "api",
        "api-gateway",
        "async",
        "endpoint",
        "metrics",
        "operations",
        "pydantic",
        "rest-api",
        "router",
        "tracing",
    ],
    "keywords": [
        "breaker",
        "breakers",
        "circuit",
        "failure",
        "failures",
        "health",
        "metrics",
        "observability",
    ],
    "business_value": "Provides observability components including SREMetricsResponse, FailureResponse, FailuresListResponse",
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
