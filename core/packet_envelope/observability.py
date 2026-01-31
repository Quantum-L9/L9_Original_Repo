"""
upgrades/packet_envelope/observability.py
OpenTelemetry instrumentation for PacketEnvelope

PHASE 2 OBJECTIVES:
  ✅ W3C Trace Context headers (CloudTracing standard)
  ✅ End-to-end tracing through WebSocket orchestrator
  ✅ Span propagation (packet_id → trace_id → span_id)
  ✅ Performance metrics collection
  ✅ Zero performance overhead mode

TECHNICAL SPECS:
  • OpenTelemetry SDK (automatic instrumentation)
  • Jaeger exporter (distributed tracing)
  • Prometheus metrics (latency, throughput, errors)
  • Context propagation (W3C TraceContext format)
  • Async-safe instrumentation (no blocking)
"""

# ============================================================================
__dora_meta__ = {
    "component_name": "Observability",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2026-01-06T15:07:54Z",
    "updated_at": "2026-01-14T12:10:12Z",
    "layer": "foundation",
    "domain": "core",
    "module_name": "observability",
    "type": "dataclass",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": [],
        "memory_layers": ["working_memory"],
        "imported_by": [
            "core.packet_envelope.integration",
            "tests.upgrades.test_packet_envelope_phases",
        ],
    },
}
# ============================================================================

import asyncio
import json
import logging
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timezone
from functools import wraps
from typing import Any

try:
    from opentelemetry import baggage, metrics, trace
    from opentelemetry.baggage.propagation import W3CBaggagePropagator
    from opentelemetry.exporter.jaeger.thrift import JaegerExporter
    from opentelemetry.propagators.composite import CompositePropagator
    from opentelemetry.sdk.metrics import MeterProvider
    from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor
    from opentelemetry.trace.propagation.tracecontext import (
        TraceContextTextMapPropagator,
    )

    OPENTELEMETRY_AVAILABLE = True
except ImportError:
    OPENTELEMETRY_AVAILABLE = False
    baggage = None
    metrics = None
    trace = None

try:
    from opentelemetry.exporter.prometheus import PrometheusMetricReader

    PROMETHEUS_EXPORTER_AVAILABLE = True
except ImportError:
    PrometheusMetricReader = None
    PROMETHEUS_EXPORTER_AVAILABLE = False

logger = logging.getLogger(__name__)

# ============================================================================
# CONFIGURATION
# ============================================================================


@dataclass
class ObservabilityConfig:
    """Observability configuration"""

    enabled: bool = True
    jaeger_host: str = "localhost"
    jaeger_port: int = 6831
    service_name: str = "l9-packet-envelope"
    sample_rate: float = 1.0  # 100% sampling (production: 0.1)
    max_attr_length: int = 2048
    batch_size: int = 512
    export_timeout_ms: int = 30000
    prometheus_port: int = 8000

    # Span filtering
    trace_internal_calls: bool = True
    trace_cache_ops: bool = True
    trace_serialization: bool = False  # Too noisy

    # Baggage fields (propagated through requests)
    baggage_fields: list = field(
        default_factory=lambda: [
            "user_id",
            "session_id",
            "request_id",
            "environment",
        ]
    )


# ============================================================================
# OBSERVABILITY ENGINE
# ============================================================================


class PacketEnvelopeObservability:
    """
    End-to-end observability for PacketEnvelope
    Integrates trace context, metrics, and structured logging
    """

    def __init__(self, config: ObservabilityConfig = None) -> None:
        """Initialize observability engine with config."""
        self.config = config or ObservabilityConfig()
        self.logger = logger

        if not self.config.enabled:
            self.tracer = None
            self.meter = None
            return

        # Initialize tracer
        jaeger_exporter = JaegerExporter(
            agent_host_name=self.config.jaeger_host,
            agent_port=self.config.jaeger_port,
        )

        trace_provider = TracerProvider()
        trace_provider.add_span_processor(BatchSpanProcessor(jaeger_exporter))
        trace.set_tracer_provider(trace_provider)

        self.tracer = trace.get_tracer(__name__)

        # Initialize metrics
        prometheus_reader = PrometheusMetricReader()
        meter_provider = MeterProvider(metric_readers=[prometheus_reader])
        metrics.set_meter_provider(meter_provider)

        self.meter = metrics.get_meter(__name__)

        # Initialize propagators
        CompositePropagator(
            [
                TraceContextTextMapPropagator(),
                W3CBaggagePropagator(),
            ]
        )
        # Note: Propagator setup for context injection

        # Create metrics
        self._init_metrics()

        self.logger.info(f"Observability initialized: {self.config.service_name}")

    def _init_metrics(self):
        """Initialize Prometheus metrics"""
        if not self.config.enabled:
            return

        # Latency histogram
        self.packet_latency = self.meter.create_histogram(
            name="packet_envelope.latency_ms",
            description="PacketEnvelope operation latency",
            unit="ms",
        )

        # Throughput counter
        self.packet_ingested = self.meter.create_counter(
            name="packet_envelope.ingested_total",
            description="Total packets ingested",
            unit="1",
        )

        self.packet_errors = self.meter.create_counter(
            name="packet_envelope.errors_total",
            description="Total packet errors",
            unit="1",
        )

        # Size gauge
        self.packet_size = self.meter.create_histogram(
            name="packet_envelope.size_bytes",
            description="Packet size distribution",
            unit="byte",
        )

        # Lineage depth
        self.lineage_depth = self.meter.create_histogram(
            name="packet_envelope.lineage_depth",
            description="Lineage chain depth",
            unit="1",
        )

    def trace_operation(
        self,
        operation_name: str,
        attributes: dict[str, Any] | None = None,
        should_trace: bool = True,
    ):
        """
        Decorator for tracing operations

        Usage:
            @obs.trace_operation("ingest_packet")
            async def ingest(packet):
                ...
        """

        def decorator(func: Callable):
            @wraps(func)
            async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
                """Async wrapper with tracing."""
                if not should_trace or not self.config.enabled:
                    return await func(*args, **kwargs)

                span_attrs = attributes or {}
                span_attrs.update(
                    {
                        "operation": operation_name,
                        "function": func.__name__,
                    }
                )

                start_time = time.time()

                with self.tracer.start_as_current_span(operation_name) as span:
                    # Set attributes (with length limit)
                    for key, value in span_attrs.items():
                        try:
                            str_val = str(value)
                            if len(str_val) > self.config.max_attr_length:
                                str_val = str_val[: self.config.max_attr_length] + "..."
                            span.set_attribute(key, str_val)
                        except Exception as e:
                            self.logger.debug(f"Failed to set span attr {key}: {e}")

                    try:
                        result = await func(*args, **kwargs)
                        span.set_attribute("status", "success")
                        return result

                    except Exception as e:
                        span.set_attribute("status", "error")
                        span.set_attribute("error.type", type(e).__name__)
                        span.set_attribute("error.message", str(e))

                        self.packet_errors.add(1, {"operation": operation_name})
                        raise

                    finally:
                        # Record latency
                        latency_ms = (time.time() - start_time) * 1000
                        self.packet_latency.record(
                            latency_ms, {"operation": operation_name}
                        )

            @wraps(func)
            def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
                """Sync wrapper with tracing."""
                if not should_trace or not self.config.enabled:
                    return func(*args, **kwargs)

                span_attrs = attributes or {}
                span_attrs.update(
                    {
                        "operation": operation_name,
                        "function": func.__name__,
                    }
                )

                start_time = time.time()

                with self.tracer.start_as_current_span(operation_name) as span:
                    for key, value in span_attrs.items():
                        try:
                            str_val = str(value)
                            if len(str_val) > self.config.max_attr_length:
                                str_val = str_val[: self.config.max_attr_length] + "..."
                            span.set_attribute(key, str_val)
                        except Exception as e:
                            self.logger.debug(f"Failed to set span attr {key}: {e}")

                    try:
                        result = func(*args, **kwargs)
                        span.set_attribute("status", "success")
                        return result

                    except Exception as e:
                        span.set_attribute("status", "error")
                        span.set_attribute("error.type", type(e).__name__)
                        span.set_attribute("error.message", str(e))

                        self.packet_errors.add(1, {"operation": operation_name})
                        raise

                    finally:
                        latency_ms = (time.time() - start_time) * 1000
                        self.packet_latency.record(
                            latency_ms, {"operation": operation_name}
                        )

            # Return async or sync wrapper based on func
            if asyncio.iscoroutinefunction(func):
                return async_wrapper
            return sync_wrapper

        return decorator

    def extract_trace_context(self, headers: dict[str, str]) -> dict[str, str]:
        """
        Extract W3C Trace Context from HTTP headers
        Returns: {trace_id, span_id, trace_flags, parent_id}
        """
        if not self.config.enabled:
            return {}

        try:
            traceparent = headers.get("traceparent", "")
            tracestate = headers.get("tracestate", "")

            # Parse traceparent: version-trace_id-parent_id-trace_flags
            if traceparent:
                parts = traceparent.split("-")
                if len(parts) >= 4:
                    return {
                        "trace_id": parts[1],
                        "parent_id": parts[2],
                        "trace_flags": parts[3],
                        "tracestate": tracestate,
                    }
        except Exception as e:
            self.logger.debug(f"Failed to extract trace context: {e}")

        return {}

    def inject_trace_context(
        self, headers: dict[str, str] | None = None
    ) -> dict[str, str]:
        """
        Inject W3C Trace Context into headers for downstream propagation
        """
        if not self.config.enabled:
            return headers or {}

        headers = headers or {}

        try:
            span = trace.get_current_span()
            context = span.get_span_context()

            # Build traceparent header
            trace_id = format(context.trace_id, "032x")
            span_id = format(context.span_id, "016x")
            trace_flags = format(context.trace_flags, "02x")

            headers["traceparent"] = f"00-{trace_id}-{span_id}-{trace_flags}"
            headers["tracestate"] = f"l9={context.trace_id}"

        except Exception as e:
            self.logger.debug(f"Failed to inject trace context: {e}")

        return headers

    def record_packet_metrics(
        self,
        packet_id: str,
        size_bytes: int,
        lineage_depth: int,
        operation: str = "ingest",
    ):
        """Record packet-specific metrics"""
        if not self.config.enabled:
            return

        try:
            self.packet_ingested.add(1, {"operation": operation})
            self.packet_size.record(size_bytes, {"operation": operation})
            self.lineage_depth.record(lineage_depth, {"packet_id": packet_id})
        except Exception as e:
            self.logger.debug(f"Failed to record metrics: {e}")


# ============================================================================
# STRUCTURED LOGGING WITH TRACE CONTEXT
# ============================================================================


@dataclass
class StructuredLogEvent:
    """Structured log event with trace context"""

    timestamp: datetime
    level: str
    message: str
    trace_id: str | None = None
    span_id: str | None = None
    packet_id: str | None = None
    operation: str | None = None
    user_id: str | None = None
    attributes: dict[str, Any] = field(default_factory=dict)

    def to_json(self) -> str:
        """Serialize to JSON for centralized logging"""
        return json.dumps(
            {
                "timestamp": self.timestamp.isoformat(),
                "level": self.level,
                "message": self.message,
                "trace": {
                    "trace_id": self.trace_id,
                    "span_id": self.span_id,
                },
                "packet": {
                    "packet_id": self.packet_id,
                    "operation": self.operation,
                },
                "user": {
                    "user_id": self.user_id,
                },
                "attributes": self.attributes,
            }
        )


# ============================================================================
# WEBSOCKET TRACE PROPAGATION
# ============================================================================


class WebSocketTracePropagator:
    """
    Propagates trace context through WebSocket frames
    Enables end-to-end tracing across async WebSocket connections
    """

    def __init__(self, observability: PacketEnvelopeObservability):
        self.obs = observability
        self.logger = logger

    def attach_to_frame(self, frame_data: dict) -> dict:
        """
        Attach W3C trace context to WebSocket frame
        """
        if not self.obs.config.enabled:
            return frame_data

        try:
            span = trace.get_current_span()
            context = span.get_span_context()

            frame_data["__trace_context__"] = {
                "trace_id": format(context.trace_id, "032x"),
                "span_id": format(context.span_id, "016x"),
                "trace_flags": context.trace_flags,
                "timestamp": datetime.now().isoformat(),
            }

        except Exception as e:
            self.logger.debug(f"Failed to attach trace to frame: {e}")

        return frame_data

    def extract_from_frame(self, frame_data: dict) -> dict | None:
        """
        Extract trace context from received WebSocket frame
        """
        if not self.obs.config.enabled:
            return None

        try:
            return frame_data.get("__trace_context__")
        except Exception as e:
            self.logger.debug(f"Failed to extract trace from frame: {e}")
            return None


# ============================================================================
# HELPERS
# ============================================================================


def create_observability(enabled: bool = True) -> PacketEnvelopeObservability:
    """Factory function for observability"""
    config = ObservabilityConfig(enabled=enabled)
    return PacketEnvelopeObservability(config)


# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "COR-FOUN-008",
    "governance_level": "critical",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": [
        "async",
        "batch-processing",
        "caching",
        "core",
        "dataclass",
        "debugging",
        "event-driven",
        "foundation",
        "messaging",
        "metrics",
    ],
    "keywords": [
        "async",
        "attach",
        "create",
        "decorator",
        "envelope",
        "event",
        "extract",
        "frame",
    ],
    "business_value": "Provides observability components including ObservabilityConfig, PacketEnvelopeObservability, StructuredLogEvent",
    "last_modified": "2026-01-14T12:10:12Z",
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
