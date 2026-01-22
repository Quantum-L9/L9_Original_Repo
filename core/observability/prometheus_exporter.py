"""
Prometheus exporter for Five-Tier Observability metrics.

Exposes observability metrics to Prometheus for Grafana visualization.
"""

# ============================================================================
__dora_meta__ = {
    "component_name": "Prometheus Exporter",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2026-01-12T15:32:48Z",
    "updated_at": "2026-01-14T15:03:00Z",
    "layer": "foundation",
    "domain": "core",
    "module_name": "prometheus_exporter",
    "type": "utility",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": [],
        "memory_layers": [],
        "imported_by": ["core.singleton_registry"],
    },
}
# ============================================================================

from typing import Any, Dict, Optional

import structlog

logger = structlog.get_logger(__name__)

# Try to import prometheus_client
try:
    from prometheus_client import Counter, Gauge, Histogram, Summary

    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False
    logger.warning("prometheus_client not installed - Prometheus exporter disabled")


class ObservabilityPrometheusExporter:
    """Exports Five-Tier Observability metrics to Prometheus."""

    def __init__(self):
        """Initialize Prometheus metrics."""
        if not PROMETHEUS_AVAILABLE:
            self.enabled = False
            return

        self.enabled = True

        # Span metrics
        self.span_total = Counter(
            "l9_observability_spans_total",
            "Total number of spans observed",
            ["span_name", "status", "kind"],
        )

        self.span_duration = Histogram(
            "l9_observability_span_duration_ms",
            "Span duration in milliseconds",
            ["span_name", "kind"],
            buckets=(1, 5, 10, 25, 50, 100, 250, 500, 1000, 2500, 5000, 10000, 30000),
        )

        # Error metrics
        self.error_total = Counter(
            "l9_observability_errors_total",
            "Total number of errors",
            ["span_name", "failure_class"],
        )

        # SRE metrics (gauges updated periodically)
        self.span_count = Gauge(
            "l9_observability_span_count",
            "Current number of spans in window",
        )

        self.error_count = Gauge(
            "l9_observability_error_count",
            "Current number of errors in window",
        )

        self.error_rate = Gauge(
            "l9_observability_error_rate",
            "Error rate (0.0-1.0)",
        )

        self.p50_latency = Gauge(
            "l9_observability_p50_latency_ms",
            "50th percentile latency in milliseconds",
        )

        self.p95_latency = Gauge(
            "l9_observability_p95_latency_ms",
            "95th percentile latency in milliseconds",
        )

        self.p99_latency = Gauge(
            "l9_observability_p99_latency_ms",
            "99th percentile latency in milliseconds",
        )

        # Failure detection metrics
        self.failure_signals = Counter(
            "l9_observability_failure_signals_total",
            "Total failure signals detected",
            ["failure_class"],
        )

        # Agent KPI metrics
        self.agent_success_rate = Gauge(
            "l9_observability_agent_success_rate",
            "Agent success rate (0.0-1.0)",
            ["agent_name"],
        )

        self.agent_tool_efficiency = Gauge(
            "l9_observability_agent_tool_efficiency",
            "Agent tool efficiency (tasks per tool call)",
            ["agent_name"],
        )

        self.agent_cost_usd = Gauge(
            "l9_observability_agent_cost_usd",
            "Total cost in USD for agent",
            ["agent_name"],
        )

        # LLM call metrics
        self.llm_calls_total = Counter(
            "l9_observability_llm_calls_total",
            "Total LLM API calls",
            ["model", "status"],
        )

        self.llm_tokens_total = Counter(
            "l9_observability_llm_tokens_total",
            "Total LLM tokens consumed",
            ["model", "type"],  # type: prompt, completion
        )

        self.llm_cost_usd = Counter(
            "l9_observability_llm_cost_usd",
            "Total LLM cost in USD",
            ["model"],
        )

        # Tool call metrics
        self.tool_calls_total = Counter(
            "l9_observability_tool_calls_total",
            "Total tool calls",
            ["tool_name", "status"],
        )

        # Context strategy metrics
        self.context_assemblies_total = Counter(
            "l9_observability_context_assemblies_total",
            "Total context window assemblies",
            ["strategy"],
        )

        self.context_tokens = Histogram(
            "l9_observability_context_tokens",
            "Context window size in tokens",
            ["strategy"],
            buckets=(100, 500, 1000, 2000, 4000, 8000, 16000, 32000, 128000),
        )

        logger.info("Observability Prometheus exporter initialized")

    def record_span(
        self,
        span_name: str,
        status: str,
        kind: str,
        duration_ms: Optional[float] = None,
    ) -> None:
        """Record a span observation."""
        if not self.enabled:
            return

        try:
            self.span_total.labels(
                span_name=span_name,
                status=status,
                kind=kind,
            ).inc()

            if duration_ms is not None:
                self.span_duration.labels(
                    span_name=span_name,
                    kind=kind,
                ).observe(duration_ms)

            if status == "ERROR":
                self.error_total.labels(
                    span_name=span_name,
                    failure_class="unknown",
                ).inc()
        except Exception as e:
            logger.warning(f"Failed to record span metric: {e}")

    def record_failure_signal(self, failure_class: str) -> None:
        """Record a failure signal."""
        if not self.enabled:
            return

        try:
            self.failure_signals.labels(failure_class=failure_class).inc()
        except Exception as e:
            logger.warning(f"Failed to record failure signal: {e}")

    def update_sre_metrics(self, metrics: Dict[str, Any]) -> None:
        """Update SRE-level metrics from computed metrics."""
        if not self.enabled:
            return

        try:
            self.span_count.set(metrics.get("span_count", 0))
            self.error_count.set(metrics.get("error_count", 0))
            self.error_rate.set(metrics.get("error_rate", 0.0))
            self.p50_latency.set(metrics.get("p50_latency_ms", 0))
            self.p95_latency.set(metrics.get("p95_latency_ms", 0))
            self.p99_latency.set(metrics.get("p99_latency_ms", 0))
        except Exception as e:
            logger.warning(f"Failed to update SRE metrics: {e}")

    def update_agent_kpi(
        self,
        agent_name: str,
        success_rate: float,
        tool_efficiency: float,
        cost_usd: float,
    ) -> None:
        """Update agent KPI metrics."""
        if not self.enabled:
            return

        try:
            self.agent_success_rate.labels(agent_name=agent_name).set(success_rate)
            self.agent_tool_efficiency.labels(agent_name=agent_name).set(
                tool_efficiency
            )
            self.agent_cost_usd.labels(agent_name=agent_name).set(cost_usd)
        except Exception as e:
            logger.warning(f"Failed to update agent KPI: {e}")

    def record_llm_call(
        self,
        model: str,
        status: str,
        prompt_tokens: int = 0,
        completion_tokens: int = 0,
        cost_usd: float = 0.0,
    ) -> None:
        """Record an LLM API call."""
        if not self.enabled:
            return

        try:
            self.llm_calls_total.labels(model=model, status=status).inc()
            if prompt_tokens > 0:
                self.llm_tokens_total.labels(model=model, type="prompt").inc(
                    prompt_tokens
                )
            if completion_tokens > 0:
                self.llm_tokens_total.labels(model=model, type="completion").inc(
                    completion_tokens
                )
            if cost_usd > 0:
                self.llm_cost_usd.labels(model=model).inc(cost_usd)
        except Exception as e:
            logger.warning(f"Failed to record LLM call: {e}")

    def record_tool_call(self, tool_name: str, status: str) -> None:
        """Record a tool call."""
        if not self.enabled:
            return

        try:
            self.tool_calls_total.labels(tool_name=tool_name, status=status).inc()
        except Exception as e:
            logger.warning(f"Failed to record tool call: {e}")

    def record_context_assembly(self, strategy: str, tokens: int) -> None:
        """Record a context window assembly."""
        if not self.enabled:
            return

        try:
            self.context_assemblies_total.labels(strategy=strategy).inc()
            self.context_tokens.labels(strategy=strategy).observe(tokens)
        except Exception as e:
            logger.warning(f"Failed to record context assembly: {e}")


# Global exporter instance
_exporter: Optional[ObservabilityPrometheusExporter] = None


def get_exporter() -> Optional[ObservabilityPrometheusExporter]:
    """Get the global Prometheus exporter instance."""
    return _exporter


def initialize_exporter() -> Optional[ObservabilityPrometheusExporter]:
    """Initialize the global Prometheus exporter."""
    global _exporter
    if PROMETHEUS_AVAILABLE:
        _exporter = ObservabilityPrometheusExporter()
        logger.info("Observability Prometheus exporter initialized")
    else:
        _exporter = None
        logger.debug(
            "Prometheus exporter not available (prometheus_client not installed)"
        )
    return _exporter


# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "COR-FOUN-055",
    "governance_level": "critical",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": [
        "api",
        "core",
        "debugging",
        "exporter",
        "foundation",
        "logging",
        "metrics",
        "utility",
    ],
    "keywords": [
        "agent",
        "assembly",
        "exporter",
        "failure",
        "initialize",
        "kpi",
        "llm",
        "metrics",
    ],
    "business_value": "Implements ObservabilityPrometheusExporter for prometheus exporter functionality",
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
