"""
Jaeger exporter for Five-Tier Observability spans.

Exports spans to Jaeger via OTLP (OpenTelemetry Protocol) for distributed tracing visualization.
"""

# ============================================================================
__dora_meta__ = {
    "component_name": "Jaeger Exporter",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2026-01-12T15:32:48Z",
    "updated_at": "2026-01-17T23:47:56Z",
    "layer": "foundation",
    "domain": "core",
    "module_name": "jaeger_exporter",
    "type": "service",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": [],
        "memory_layers": [],
        "imported_by": ["core.singleton_registry"],
    },
}
# ============================================================================

from typing import TYPE_CHECKING, Any

import structlog

from core.decorators import must_stay_async

logger = structlog.get_logger(__name__)

# Type-only import for type hints (evaluated at static analysis time)
if TYPE_CHECKING:
    from opentelemetry import trace

# Try to import OpenTelemetry (runtime import)
try:
    from opentelemetry import trace as _trace
    from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor

    OPENTELEMETRY_AVAILABLE = True
    trace = _trace  # Re-export for runtime use
except ImportError:
    OPENTELEMETRY_AVAILABLE = False
    trace = None  # Fallback for runtime
    logger.warning("opentelemetry not installed - Jaeger exporter disabled")


class JaegerExporter:
    """Exports spans to Jaeger via OTLP."""

    def __init__(
        self,
        jaeger_endpoint: str | None = None,
        service_name: str = "l9-observability",
    ):
        """Initialize Jaeger exporter.

        Args:
            jaeger_endpoint: Jaeger OTLP endpoint (default: http://jaeger:4318/v1/traces)
            service_name: Service name for traces
        """
        if not OPENTELEMETRY_AVAILABLE:
            self.enabled = False
            logger.warning("OpenTelemetry not available - Jaeger exporter disabled")
            return

        self.enabled = True
        self.service_name = service_name

        # Default to Jaeger OTLP endpoint in docker network
        self.jaeger_endpoint = jaeger_endpoint or "http://jaeger:4318/v1/traces"

        try:
            # Create OTLP exporter
            otlp_exporter = OTLPSpanExporter(
                endpoint=self.jaeger_endpoint,
            )

            # Create resource with service name
            resource = Resource.create(
                {
                    "service.name": service_name,
                }
            )

            # Create tracer provider
            tracer_provider = TracerProvider(resource=resource)
            tracer_provider.add_span_processor(BatchSpanProcessor(otlp_exporter))

            # Set as global tracer provider
            trace.set_tracer_provider(tracer_provider)

            self.tracer = trace.get_tracer(__name__)

            logger.info(
                "Jaeger exporter initialized",
                endpoint=self.jaeger_endpoint,
                service_name=service_name,
            )
        except Exception as exc:
            self.enabled = False
            logger.error(f"Failed to initialize Jaeger exporter: {exc}")

    def export_span(self, span: Any) -> None:
        """Export a single span to Jaeger.

        Args:
            span: Span object from observability.models
        """
        if not self.enabled or not self.tracer:
            return

        try:
            # Convert L9 Span to OpenTelemetry span
            with self.tracer.start_as_current_span(
                name=span.name,
                kind=self._map_span_kind(span.kind),
            ) as otel_span:
                # Set span attributes
                otel_span.set_attribute("span.id", span.span_id)
                otel_span.set_attribute("trace.id", span.trace_id)

                if span.parent_span_id:
                    otel_span.set_attribute("parent.span.id", span.parent_span_id)

                # Set status
                if span.status.value == "ERROR":
                    otel_span.set_status(trace.Status(trace.StatusCode.ERROR))
                    if span.error:
                        otel_span.record_exception(Exception(span.error))
                else:
                    otel_span.set_status(trace.Status(trace.StatusCode.OK))

                # Add duration
                if span.duration_ms:
                    otel_span.set_attribute("duration_ms", span.duration_ms)

                # Add custom attributes
                if hasattr(span, "attributes") and span.attributes:
                    for key, value in span.attributes.items():
                        # Convert value to string if needed (OTLP attribute values must be strings/numbers/bools)
                        if isinstance(value, (str, int, float, bool)):
                            otel_span.set_attribute(key, value)
                        else:
                            otel_span.set_attribute(key, str(value))

                # Add specialized span attributes
                from .models import ContextAssemblySpan, LLMGenerationSpan, ToolCallSpan

                if isinstance(span, LLMGenerationSpan):
                    otel_span.set_attribute("llm.model", span.model)
                    otel_span.set_attribute("llm.prompt_tokens", span.prompt_tokens)
                    otel_span.set_attribute(
                        "llm.completion_tokens", span.completion_tokens
                    )
                    otel_span.set_attribute("llm.total_tokens", span.total_tokens)
                    otel_span.set_attribute("llm.cost_usd", span.cost_usd)
                elif isinstance(span, ToolCallSpan):
                    otel_span.set_attribute("tool.name", span.tool_name)
                    if span.tool_input:
                        # Convert tool_input dict to attributes (limit size)
                        for key, value in list(span.tool_input.items())[
                            :10
                        ]:  # Limit to 10 attributes
                            attr_key = f"tool.input.{key}"
                            if isinstance(value, (str, int, float, bool)):
                                otel_span.set_attribute(attr_key, value)
                            else:
                                otel_span.set_attribute(
                                    attr_key, str(value)[:200]
                                )  # Truncate long values
                elif isinstance(span, ContextAssemblySpan):
                    otel_span.set_attribute("context.strategy", span.strategy)
                    otel_span.set_attribute("context.tokens_used", span.tokens_used)
                    otel_span.set_attribute(
                        "context.tokens_available", span.tokens_available
                    )
                    otel_span.set_attribute(
                        "context.truncation_occurred", span.truncation_occurred
                    )

                # Set start/end times
                if span.start_time:
                    otel_span.set_attribute("start_time", span.start_time.isoformat())
                if span.end_time:
                    otel_span.set_attribute("end_time", span.end_time.isoformat())
        except Exception as exc:
            logger.debug(f"Failed to export span to Jaeger: {exc}")

    def _map_span_kind(self, kind: Any) -> Any:
        """Map L9 SpanKind to OpenTelemetry SpanKind."""
        if not OPENTELEMETRY_AVAILABLE:
            return None
        from .models import SpanKind

        kind_str = kind.value if hasattr(kind, "value") else str(kind)

        mapping = {
            SpanKind.INTERNAL.value: trace.SpanKind.INTERNAL,
            SpanKind.SERVER.value: trace.SpanKind.SERVER,
            SpanKind.CLIENT.value: trace.SpanKind.CLIENT,
            SpanKind.PRODUCER.value: trace.SpanKind.PRODUCER,
            SpanKind.CONSUMER.value: trace.SpanKind.CONSUMER,
        }

        return mapping.get(kind_str, trace.SpanKind.INTERNAL)

    def export(self, spans: list[Any]) -> None:
        """Export multiple spans to Jaeger.

        Args:
            spans: List of Span objects
        """
        if not self.enabled:
            return

        for span in spans:
            self.export_span(span)

    @must_stay_async("callers use await")
    async def export_async(self, spans: list[Any]) -> None:
        """Export spans asynchronously (same as sync for now)."""
        self.export(spans)

    @must_stay_async("callers use await")
    async def flush(self) -> None:
        """Flush any pending spans."""
        # OpenTelemetry BatchSpanProcessor handles flushing automatically
        pass


# Global exporter instance
_exporter: JaegerExporter | None = None


def get_jaeger_exporter() -> JaegerExporter | None:
    """Get the global Jaeger exporter instance."""
    return _exporter


def initialize_jaeger_exporter(
    jaeger_endpoint: str | None = None,
    service_name: str = "l9-observability",
) -> JaegerExporter | None:
    """Initialize the global Jaeger exporter."""
    global _exporter
    if OPENTELEMETRY_AVAILABLE:
        _exporter = JaegerExporter(
            jaeger_endpoint=jaeger_endpoint,
            service_name=service_name,
        )
        logger.info("Jaeger exporter initialized")
    else:
        _exporter = None
        logger.debug("Jaeger exporter not available (opentelemetry not installed)")
    return _exporter


# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "COR-FOUN-056",
    "governance_level": "critical",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": ["core.decorators"],
    "tags": [
        "async",
        "batch-processing",
        "core",
        "debugging",
        "exporter",
        "foundation",
        "logging",
        "service",
        "static-analysis",
        "tracing",
    ],
    "keywords": [
        "async",
        "export",
        "exporter",
        "flush",
        "initialize",
        "jaeger",
        "span",
        "spans",
    ],
    "business_value": "Implements JaegerExporter for jaeger exporter functionality",
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
