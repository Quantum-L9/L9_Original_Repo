"""
L9 Observability Protocols - Core Abstractions
===============================================

Frontier-grade protocol definitions for observability subsystem following Dependency Inversion Principle.

**Top Frontier AI Lab Quality** - Production-ready abstractions for observability operations.

Features:
- ✅ Protocol-based abstractions for tracing, metrics, and logging
- ✅ Type-safe interfaces with comprehensive type hints
- ✅ Enables dependency injection and testing
- ✅ Supports multiple exporters (Jaeger, Prometheus, OpenTelemetry)
- ✅ Hot-swappable implementations

Protocols:
- SpanEmitter: Distributed tracing span emission
- MetricsCollector: Metrics collection and aggregation
- TraceContext: Trace context propagation
- LogExporter: Structured log export
- HealthChecker: System health monitoring

Version: 1.0.0
GMP: di-dip-phase1-abstractions
Author: Top Frontier AI Lab
"""

from __future__ import annotations

from core.decorators import must_stay_async

# ============================================================================
__dora_meta__ = {
    "component_name": "Observability Protocols",
    "module_version": "1.0.0",
    "created_by": "L9 DI/DIP Upgrade",
    "created_at": "2026-01-20T12:00:00Z",
    "updated_at": "2026-01-20T12:00:00Z",
    "layer": "foundation",
    "domain": "abstractions",
    "module_name": "observability_protocols",
    "type": "protocol",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": ["Jaeger", "Prometheus"],
        "memory_layers": [],
        "imported_by": [
            "core.observability.service",
            "core.di.container",
            "tests.unit.test_observability_protocols",
        ],
    },
}
# ============================================================================

from enum import Enum
from typing import Any, Protocol, runtime_checkable


class SpanKind(str, Enum):
    """Span kind enumeration."""

    INTERNAL = "internal"
    SERVER = "server"
    CLIENT = "client"
    PRODUCER = "producer"
    CONSUMER = "consumer"
    KERNEL_LOAD = "kernel_load"
    KERNEL_ACTIVATION = "kernel_activation"


class SpanStatus(str, Enum):
    """Span status enumeration."""

    OK = "ok"
    ERROR = "error"
    UNSET = "unset"


@runtime_checkable
class SpanEmitter(Protocol):
    """
    Protocol for distributed tracing span emission.

    Implementations must provide span creation, management, and
    emission to tracing backends.

    Example implementations:
    - JaegerSpanEmitter: Jaeger tracing backend
    - OpenTelemetrySpanEmitter: OpenTelemetry backend
    - NoOpSpanEmitter: No-op for testing/disabled tracing
    """

    def start_span(
        self,
        name: str,
        trace_id: str | None = None,
        parent_span_id: str | None = None,
        kind: SpanKind = SpanKind.INTERNAL,
        **attributes: Any,
    ) -> Any:
        """
        Start a new span.

        Args:
            name: Span name
            trace_id: Optional trace ID (creates new if None)
            parent_span_id: Optional parent span ID
            kind: Span kind
            **attributes: Additional span attributes

        Returns:
            Span object
        """
        ...

    def finish_span(
        self,
        span: Any,
        status: SpanStatus = SpanStatus.OK,
        error: str | None = None,
    ) -> None:
        """
        Finish a span.

        Args:
            span: Span object to finish
            status: Final span status
            error: Optional error message
        """
        ...

    def emit_span(self, span: Any) -> None:
        """
        Emit span to backend.

        Args:
            span: Span object to emit
        """
        ...

    def add_span_event(
        self, span: Any, name: str, attributes: dict[str, Any] | None = None
    ) -> None:
        """
        Add event to span.

        Args:
            span: Span object
            name: Event name
            attributes: Optional event attributes
        """
        ...


@runtime_checkable
class MetricsCollector(Protocol):
    """
    Protocol for metrics collection and aggregation.

    Implementations must provide counter, gauge, and histogram
    metrics with labels support.

    Example implementations:
    - PrometheusMetricsCollector: Prometheus metrics
    - StatsdMetricsCollector: StatsD metrics
    - InMemoryMetricsCollector: Testing metrics
    """

    def increment_counter(
        self, name: str, value: float = 1.0, labels: dict[str, str] | None = None
    ) -> None:
        """
        Increment a counter metric.

        Args:
            name: Metric name
            value: Increment value
            labels: Optional metric labels
        """
        ...

    def set_gauge(
        self, name: str, value: float, labels: dict[str, str] | None = None
    ) -> None:
        """
        Set a gauge metric.

        Args:
            name: Metric name
            value: Gauge value
            labels: Optional metric labels
        """
        ...

    def record_histogram(
        self, name: str, value: float, labels: dict[str, str] | None = None
    ) -> None:
        """
        Record a histogram value.

        Args:
            name: Metric name
            value: Value to record
            labels: Optional metric labels
        """
        ...

    def get_metrics(self) -> dict[str, Any]:
        """
        Get all collected metrics.

        Returns:
            Dictionary of metrics
        """
        ...


@runtime_checkable
class TraceContext(Protocol):
    """
    Protocol for trace context propagation.

    Implementations must provide trace context creation and
    propagation across service boundaries.

    Example implementations:
    - W3CTraceContext: W3C Trace Context standard
    - B3TraceContext: Zipkin B3 format
    - CustomTraceContext: Custom propagation format
    """

    @property
    def trace_id(self) -> str:
        """Get trace ID."""
        ...

    @property
    def span_id(self) -> str:
        """Get current span ID."""
        ...

    @property
    def parent_span_id(self) -> str | None:
        """Get parent span ID."""
        ...

    def to_headers(self) -> dict[str, str]:
        """
        Convert context to HTTP headers.

        Returns:
            Dictionary of headers
        """
        ...

    @classmethod
    def from_headers(cls, headers: dict[str, str]) -> TraceContext:
        """
        Create context from HTTP headers.

        Args:
            headers: HTTP headers

        Returns:
            TraceContext instance
        """
        ...


@runtime_checkable
class LogExporter(Protocol):
    """
    Protocol for structured log export.

    Implementations must provide structured logging with
    context and metadata support.

    Example implementations:
    - StructlogExporter: Structlog-based logging
    - JSONLogExporter: JSON-formatted logs
    - CloudWatchExporter: AWS CloudWatch logs
    """

    def log(
        self,
        level: str,
        message: str,
        context: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> None:
        """
        Log a message with context.

        Args:
            level: Log level (debug, info, warning, error, critical)
            message: Log message
            context: Optional context dictionary
            **kwargs: Additional log fields
        """
        ...

    def debug(self, message: str, **kwargs: Any) -> None:
        """Log debug message."""
        ...

    def info(self, message: str, **kwargs: Any) -> None:
        """Log info message."""
        ...

    def warning(self, message: str, **kwargs: Any) -> None:
        """Log warning message."""
        ...

    def error(self, message: str, **kwargs: Any) -> None:
        """Log error message."""
        ...

    def critical(self, message: str, **kwargs: Any) -> None:
        """Log critical message."""
        ...


@runtime_checkable
class HealthChecker(Protocol):
    """
    Protocol for system health monitoring.

    Implementations must provide health check capabilities
    for system components and dependencies.

    Example implementations:
    - ComponentHealthChecker: Individual component checks
    - AggregateHealthChecker: Aggregate health status
    - RemoteHealthChecker: Remote service health checks
    """

    @must_stay_async("callers use await")
    async def check_health(self) -> dict[str, Any]:
        """
        Check system health.

        Returns:
            Health status dictionary with component statuses
        """
        ...

    @must_stay_async("callers use await")
    async def check_component(self, component_name: str) -> bool:
        """
        Check specific component health.

        Args:
            component_name: Component to check

        Returns:
            True if healthy
        """
        ...

    def get_health_summary(self) -> dict[str, Any]:
        """
        Get health summary.

        Returns:
            Summary of health checks
        """
        ...


@runtime_checkable
class ObservabilityService(Protocol):
    """
    Protocol for unified observability service.

    Implementations must provide unified interface for all
    observability operations (tracing, metrics, logging).

    Example implementations:
    - StandardObservabilityService: Full observability stack
    - LightweightObservabilityService: Minimal observability
    - NoOpObservabilityService: Disabled observability
    """

    def emit_span(self, span: Any) -> None:
        """Emit a span."""
        ...

    def record_metric(
        self, name: str, value: float, metric_type: str = "counter"
    ) -> None:
        """Record a metric."""
        ...

    def log_event(self, level: str, message: str, **kwargs: Any) -> None:
        """Log an event."""
        ...

    @must_stay_async("callers use await")
    async def health_check(self) -> dict[str, Any]:
        """Check service health."""
        ...


__all__ = [
    "HealthChecker",
    "LogExporter",
    "MetricsCollector",
    "ObservabilityService",
    "SpanEmitter",
    "SpanKind",
    "SpanStatus",
    "TraceContext",
]

# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "COR-FOUN-114",
    "governance_level": "critical",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": [
        "async",
        "data-models",
        "debugging",
        "enum",
        "event-driven",
        "exporter",
        "foundation",
        "messaging",
        "metrics",
        "monitoring",
    ],
    "keywords": [
        "abstractions",
        "check",
        "checker",
        "collector",
        "component",
        "core",
        "counter",
        "critical",
    ],
    "business_value": "Provides observability protocols components including SpanKind, SpanStatus, SpanEmitter",
    "last_modified": "2026-01-24T13:02:52Z",
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
