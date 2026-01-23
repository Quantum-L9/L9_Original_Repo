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

from typing import Any, Dict, Optional, Protocol, runtime_checkable
from enum import Enum


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
        trace_id: Optional[str] = None,
        parent_span_id: Optional[str] = None,
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
        error: Optional[str] = None,
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
        self, span: Any, name: str, attributes: Optional[Dict[str, Any]] = None
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
        self, name: str, value: float = 1.0, labels: Optional[Dict[str, str]] = None
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
        self, name: str, value: float, labels: Optional[Dict[str, str]] = None
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
        self, name: str, value: float, labels: Optional[Dict[str, str]] = None
    ) -> None:
        """
        Record a histogram value.

        Args:
            name: Metric name
            value: Value to record
            labels: Optional metric labels
        """
        ...

    def get_metrics(self) -> Dict[str, Any]:
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
    def parent_span_id(self) -> Optional[str]:
        """Get parent span ID."""
        ...

    def to_headers(self) -> Dict[str, str]:
        """
        Convert context to HTTP headers.

        Returns:
            Dictionary of headers
        """
        ...

    @classmethod
    def from_headers(cls, headers: Dict[str, str]) -> "TraceContext":
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
        context: Optional[Dict[str, Any]] = None,
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

    async def check_health(self) -> Dict[str, Any]:
        """
        Check system health.

        Returns:
            Health status dictionary with component statuses
        """
        ...

    async def check_component(self, component_name: str) -> bool:
        """
        Check specific component health.

        Args:
            component_name: Component to check

        Returns:
            True if healthy
        """
        ...

    def get_health_summary(self) -> Dict[str, Any]:
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

    async def health_check(self) -> Dict[str, Any]:
        """Check service health."""
        ...


__all__ = [
    "SpanEmitter",
    "MetricsCollector",
    "TraceContext",
    "LogExporter",
    "HealthChecker",
    "ObservabilityService",
    "SpanKind",
    "SpanStatus",
]
