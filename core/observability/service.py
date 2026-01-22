"""
Main observability service orchestration.

Manages span export, metrics computation, failure detection, and service lifecycle.
"""

# ============================================================================
__dora_meta__ = {
    "component_name": "Service",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2026-01-06T15:07:54Z",
    "updated_at": "2026-01-17T23:47:56Z",
    "layer": "foundation",
    "domain": "core",
    "module_name": "service",
    "type": "service",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": [],
        "memory_layers": ["working_memory"],
        "imported_by": [
            "api.routes.observability",
            "api.server",
            "core.kernels.kernelloader",
            "core.observability.__init__",
            "core.singleton_registry",
            "tests.core.observability.test_observability_integration",
        ],
    },
}
# ============================================================================

import asyncio
from collections import defaultdict
from datetime import datetime
from typing import Any, Dict, List, Optional

import structlog

from core.decorators import must_stay_async

from .config import ObservabilitySettings, load_config
from .models import FailureClass, FailureSignal, Span, TraceContext

logger = structlog.get_logger(__name__)


class ObservabilityService:
    """Main service for observability subsystem."""

    _instance: Optional["ObservabilityService"] = None
    _lock = asyncio.Lock()

    def __init__(
        self,
        config: Optional[ObservabilitySettings] = None,
        substrate_service: Optional[Any] = None,
    ):
        """Initialize observability service."""
        self.config = config or load_config()
        self.substrate_service = substrate_service
        self.spans: List[Span] = []
        self.failures: List[FailureSignal] = []
        self.exporters: List[Any] = []
        self._trace_context: Optional[TraceContext] = None
        self._prometheus_exporter: Optional[Any] = None
        self._jaeger_exporter: Optional[Any] = None
        self._setup_logging()
        logger.info(
            "ObservabilityService initialized",
            extra={
                "sampling_rate": self.config.sampling_rate,
                "exporters": self.config.exporters,
            },
        )

    def _setup_logging(self) -> None:
        """Configure logging (structlog is pre-configured at module level)."""
        # structlog loggers are configured globally; this method is a no-op
        # to preserve API compatibility. Log level is controlled via structlog
        # configuration, not per-service.

    @classmethod
    def get(cls) -> Optional["ObservabilityService"]:
        """Get global instance."""
        return cls._instance

    @classmethod
    def set_global(cls, service: "ObservabilityService") -> None:
        """Set global instance."""
        cls._instance = service

    @must_stay_async("callers use await")
    async def initialize_exporters(self) -> None:
        """Initialize configured exporters."""
        from .exporters import (ConsoleExporter, JSONFileExporter,
                                SubstrateExporter)
        from .jaeger_exporter import initialize_jaeger_exporter
        from .prometheus_exporter import initialize_exporter

        # Initialize Prometheus exporter (always available if prometheus_client installed)
        self._prometheus_exporter = initialize_exporter()

        # Initialize Jaeger exporter if enabled
        if self.config.jaeger_enabled or "jaeger" in self.config.exporters:
            self._jaeger_exporter = initialize_jaeger_exporter(
                jaeger_endpoint=self.config.jaeger_endpoint,
                service_name="l9-observability",
            )
        else:
            self._jaeger_exporter = None

        for exporter_name in self.config.exporters:
            try:
                if exporter_name == "console":
                    self.exporters.append(ConsoleExporter())
                elif exporter_name == "file":
                    self.exporters.append(
                        JSONFileExporter(self.config.file_export_path)
                    )
                elif exporter_name == "substrate":
                    if self.substrate_service and self.config.substrate_enabled:
                        self.exporters.append(SubstrateExporter(self.substrate_service))
                elif exporter_name == "jaeger":
                    # Jaeger exporter is handled separately (uses OpenTelemetry, not SpanExporter interface)
                    pass
                # datadog, honeycomb etc. would go here in extended implementation
                else:
                    logger.warning(f"Unknown exporter: {exporter_name}")
            except Exception as exc:
                logger.error(f"Failed to initialize exporter {exporter_name}: {exc}")

    def current_trace_context(self) -> TraceContext:
        """Get current trace context (create if needed)."""
        if not self._trace_context:
            self._trace_context = TraceContext()
        return self._trace_context

    def set_trace_context(self, ctx: TraceContext) -> None:
        """Set trace context (e.g., from incoming request headers)."""
        self._trace_context = ctx

    def export_span(self, span: Span) -> None:
        """Export a span to all configured exporters."""
        if not self.config.enabled:
            return

        # Apply sampling decision
        ctx = self.current_trace_context()
        if span.status == SpanStatus.ERROR:
            sample = self.config.error_sampling_rate >= 1.0
        else:
            sample = ctx.is_sampled

        if not sample:
            return

        # Store locally
        self.spans.append(span)

        # Export to Jaeger (if enabled)
        if self._jaeger_exporter:
            try:
                self._jaeger_exporter.export_span(span)
            except Exception as exc:
                logger.debug(f"Jaeger export failed: {exc}")

        # Export to Prometheus (if enabled)
        if self._prometheus_exporter:
            try:
                self._prometheus_exporter.record_span(
                    span_name=span.name,
                    status=span.status.value,
                    kind=(
                        span.kind.value
                        if hasattr(span.kind, "value")
                        else str(span.kind)
                    ),
                    duration_ms=span.duration_ms,
                )

                # Record specialized span types
                from .models import (ContextAssemblySpan, LLMGenerationSpan,
                                     ToolCallSpan)

                if isinstance(span, LLMGenerationSpan):
                    self._prometheus_exporter.record_llm_call(
                        model=span.model,
                        status=span.status.value,
                        prompt_tokens=span.prompt_tokens,
                        completion_tokens=span.completion_tokens,
                        cost_usd=span.cost_usd,
                    )
                elif isinstance(span, ToolCallSpan):
                    self._prometheus_exporter.record_tool_call(
                        tool_name=span.tool_name,
                        status=span.status.value,
                    )
                elif isinstance(span, ContextAssemblySpan):
                    self._prometheus_exporter.record_context_assembly(
                        strategy=span.strategy,
                        tokens=span.tokens_used,
                    )
            except Exception as exc:
                logger.debug(f"Prometheus export failed: {exc}")

        # Export via all backends (async, non-blocking)
        for exporter in self.exporters:
            try:
                if hasattr(exporter, "export_async"):
                    asyncio.create_task(exporter.export_async([span]))
                else:
                    exporter.export([span])
            except Exception as exc:
                logger.error(f"Export failed: {exc}")

    @must_stay_async("callers use await")
    async def compute_metrics(self) -> Dict[str, Any]:
        """Compute SRE metrics from recent spans."""
        if not self.spans:
            return {
                "span_count": 0,
                "error_count": 0,
                "error_rate": 0.0,
                "p95_latency_ms": 0,
                "p99_latency_ms": 0,
            }

        durations = [s.duration_ms for s in self.spans if s.duration_ms]
        errors = [s for s in self.spans if s.status.value == "ERROR"]

        durations.sort()
        p50_idx = max(0, len(durations) // 2)
        p95_idx = max(0, int(len(durations) * 0.95) - 1)
        p99_idx = max(0, int(len(durations) * 0.99) - 1)

        metrics = {
            "span_count": len(self.spans),
            "error_count": len(errors),
            "error_rate": len(errors) / len(self.spans) if self.spans else 0.0,
            "p50_latency_ms": durations[p50_idx] if p50_idx < len(durations) else 0,
            "p95_latency_ms": durations[p95_idx] if p95_idx < len(durations) else 0,
            "p99_latency_ms": durations[p99_idx] if p99_idx < len(durations) else 0,
            "timestamp": datetime.utcnow().isoformat(),
        }

        # Update Prometheus metrics
        if self._prometheus_exporter:
            try:
                self._prometheus_exporter.update_sre_metrics(metrics)
            except Exception as exc:
                logger.debug(f"Failed to update Prometheus SRE metrics: {exc}")

        return metrics

    @must_stay_async("callers use await")
    async def update_agent_kpis(self) -> None:
        """Update agent KPI metrics in Prometheus."""
        if not self._prometheus_exporter:
            return

        from .aggregation import MetricsAggregator

        # Group spans by agent
        agent_spans = defaultdict(list)
        for span in self.spans:
            if hasattr(span, "attributes") and "agent_id" in span.attributes:
                agent_id = span.attributes["agent_id"]
                agent_spans[agent_id].append(span)

        # Compute KPIs for each agent
        for agent_name, spans in agent_spans.items():
            try:
                kpis = MetricsAggregator.compute_agent_kpis(spans, agent_name)
                if kpis:
                    self._prometheus_exporter.update_agent_kpi(
                        agent_name=agent_name,
                        success_rate=kpis.get("success_rate", 0.0),
                        tool_efficiency=kpis.get("tool_efficiency", 0.0),
                        cost_usd=kpis.get("total_cost_usd", 0.0),
                    )
            except Exception as exc:
                logger.debug(f"Failed to update agent KPI for {agent_name}: {exc}")

    @must_stay_async("callers use await")
    async def detect_failures(self) -> List[FailureSignal]:
        """Detect failures from recent spans."""
        signals = []

        for span in self.spans:
            # Tool timeout
            if (
                span.name.startswith("tool.")
                and span.duration_ms
                and span.duration_ms > 30000
            ):
                signals.append(
                    FailureSignal(
                        failure_class=FailureClass.TOOL_TIMEOUT,
                        span_id=span.span_id,
                        trace_id=span.trace_id,
                        context={"tool": span.name, "duration_ms": span.duration_ms},
                    )
                )

            # Tool error
            if span.name.startswith("tool.") and span.status.value == "ERROR":
                signals.append(
                    FailureSignal(
                        failure_class=FailureClass.TOOL_ERROR,
                        span_id=span.span_id,
                        trace_id=span.trace_id,
                        context={"tool": span.name, "error": span.error},
                    )
                )

            # Governance denial
            if (
                span.name.startswith("governance.")
                and hasattr(span, "policy_result")
                and span.policy_result == "deny"
            ):
                signals.append(
                    FailureSignal(
                        failure_class=FailureClass.GOVERNANCE_DENIED,
                        span_id=span.span_id,
                        trace_id=span.trace_id,
                        context={"policy": span.name},
                    )
                )

            # Context overflow
            if hasattr(span, "overflow_event") and span.overflow_event:
                signals.append(
                    FailureSignal(
                        failure_class=FailureClass.CONTEXT_WINDOW_EXCEEDED,
                        span_id=span.span_id,
                        trace_id=span.trace_id,
                        context={"tokens_used": span.attributes.get("tokens_used")},
                    )
                )

        self.failures.extend(signals)

        # Record failure signals to Prometheus
        if self._prometheus_exporter:
            for signal in signals:
                try:
                    self._prometheus_exporter.record_failure_signal(
                        failure_class=(
                            signal.failure_class.value
                            if hasattr(signal.failure_class, "value")
                            else str(signal.failure_class)
                        )
                    )
                except Exception as exc:
                    logger.debug(
                        f"Failed to record failure signal to Prometheus: {exc}"
                    )

        return signals

    async def shutdown(self) -> None:
        """Graceful shutdown."""
        logger.info("ObservabilityService shutting down...")
        # Flush remaining spans
        for exporter in self.exporters:
            try:
                if hasattr(exporter, "flush"):
                    await exporter.flush()
            except Exception as exc:
                logger.error(f"Flush failed: {exc}")
        logger.info("ObservabilityService shutdown complete")


async def initialize_observability(
    config: Optional[ObservabilitySettings] = None,
    substrate_service: Optional[Any] = None,
) -> ObservabilityService:
    """
    Initialize and return global observability service.

    Call this once at application startup.
    """
    if ObservabilityService.get() is not None:
        return ObservabilityService.get()

    config = config or load_config()
    service = ObservabilityService(config=config, substrate_service=substrate_service)
    await service.initialize_exporters()
    ObservabilityService.set_global(service)
    return service


def get_observability_service() -> Optional[ObservabilityService]:
    """
    Get the global observability service instance.

    Returns None if observability hasn't been initialized.
    This is the preferred way to access the service from other modules.
    """
    return ObservabilityService.get()


# Import SpanStatus for export_span
from .models import SpanStatus

# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "COR-FOUN-057",
    "governance_level": "critical",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": ["core.decorators"],
    "tags": [
        "api",
        "async",
        "core",
        "debugging",
        "event-driven",
        "foundation",
        "logging",
        "metrics",
        "service",
        "tracing",
    ],
    "keywords": [
        "agent",
        "compute",
        "current",
        "detect",
        "detection",
        "export",
        "exporters",
        "failures",
    ],
    "business_value": "Implements ObservabilityService for service functionality",
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
