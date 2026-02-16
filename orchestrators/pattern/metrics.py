"""
L9 Pattern Orchestrator - Prometheus Metrics
=============================================

Metrics for observability of pattern pipeline execution.

Version: 1.0.0
"""

from __future__ import annotations

# ============================================================================
__dora_meta__ = {
    "component_name": "Prometheus Metrics",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2026-01-16T00:01:54Z",
    "updated_at": "2026-01-17T23:47:56Z",
    "layer": "intelligence",
    "domain": "orchestration",
    "module_name": "metrics",
    "type": "tracker",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": [],
        "memory_layers": [],
        "imported_by": [
            "orchestrators.pattern.orchestrator",
            "tests.orchestrators.test_pattern_orchestrator",
        ],
    },
}
# ============================================================================

from contextlib import contextmanager
from time import perf_counter

import structlog
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Generator

logger = structlog.get_logger(__name__)

# Try to import prometheus_client, fallback to no-op if not available
try:
    from prometheus_client import Counter, Gauge, Histogram

    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False
    logger.warning("prometheus_client not installed, metrics will be no-op")


# =============================================================================
# Metric Definitions
# =============================================================================

if PROMETHEUS_AVAILABLE:
    # Pipeline-level metrics
    PIPELINE_EXECUTIONS = Counter(
        "l9_pattern_pipeline_executions_total",
        "Total pipeline executions",
        ["subsystem", "status"],
    )
    PIPELINE_DURATION = Histogram(
        "l9_pattern_pipeline_duration_seconds",
        "Pipeline execution duration",
        ["subsystem"],
        buckets=[0.1, 0.5, 1.0, 5.0, 10.0, 30.0, 60.0, 120.0, 300.0],
    )
    PIPELINE_ACTIVE = Gauge(
        "l9_pattern_pipeline_active",
        "Currently active pipeline executions",
        ["subsystem"],
    )

    # Node-level metrics
    NODE_EXECUTIONS = Counter(
        "l9_pattern_node_executions_total",
        "Total node executions",
        ["subsystem", "node_id", "status"],
    )
    NODE_DURATION = Histogram(
        "l9_pattern_node_duration_seconds",
        "Node execution duration",
        ["subsystem", "node_id"],
        buckets=[0.1, 0.5, 1.0, 5.0, 10.0, 30.0, 60.0],
    )

    # Agent call metrics
    AGENT_CALLS = Counter(
        "l9_pattern_agent_calls_total",
        "Total agent invocations",
        ["subsystem", "role", "status"],
    )
    AGENT_LATENCY = Histogram(
        "l9_pattern_agent_latency_seconds",
        "Agent invocation latency",
        ["subsystem", "role"],
        buckets=[0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0],
    )

    # Validation metrics
    VALIDATION_RESULTS = Counter(
        "l9_pattern_validation_results_total",
        "Schema validation results",
        ["subsystem", "node_id", "result"],
    )

    # Memory write metrics
    MEMORY_WRITES = Counter(
        "l9_pattern_memory_writes_total",
        "Memory segment writes",
        ["subsystem", "segment"],
    )


# =============================================================================
# Metrics Helper Class
# =============================================================================


class PatternMetrics:
    """
    Metrics helper for pattern orchestrator.

    Provides context managers for timing and recording metrics.
    Falls back to no-op if prometheus_client is not installed.
    """

    def __init__(self, subsystem: str):
        """Initialize metrics for a subsystem."""
        self.subsystem = subsystem
        self._start_time: float | None = None

    @contextmanager
    def track_pipeline(self) -> Generator[None, None, None]:
        """Context manager for tracking pipeline execution."""
        self._start_time = perf_counter()

        if PROMETHEUS_AVAILABLE:
            PIPELINE_ACTIVE.labels(subsystem=self.subsystem).inc()

        try:
            yield
        finally:
            duration = perf_counter() - self._start_time

            if PROMETHEUS_AVAILABLE:
                PIPELINE_ACTIVE.labels(subsystem=self.subsystem).dec()
                PIPELINE_DURATION.labels(subsystem=self.subsystem).observe(duration)

    def record_pipeline_result(self, status: str) -> None:
        """Record pipeline completion status."""
        if PROMETHEUS_AVAILABLE:
            PIPELINE_EXECUTIONS.labels(
                subsystem=self.subsystem,
                status=status,
            ).inc()

    @contextmanager
    def track_node(self, node_id: str) -> Generator[None, None, None]:
        """Context manager for tracking node execution."""
        start = perf_counter()

        try:
            yield
        finally:
            duration = perf_counter() - start

            if PROMETHEUS_AVAILABLE:
                NODE_DURATION.labels(
                    subsystem=self.subsystem,
                    node_id=node_id,
                ).observe(duration)

    def record_node_result(self, node_id: str, status: str) -> None:
        """Record node completion status."""
        if PROMETHEUS_AVAILABLE:
            NODE_EXECUTIONS.labels(
                subsystem=self.subsystem,
                node_id=node_id,
                status=status,
            ).inc()

    @contextmanager
    def track_agent_call(self, role: str) -> Generator[None, None, None]:
        """Context manager for tracking agent invocations."""
        start = perf_counter()

        try:
            yield
        finally:
            duration = perf_counter() - start

            if PROMETHEUS_AVAILABLE:
                AGENT_LATENCY.labels(
                    subsystem=self.subsystem,
                    role=role,
                ).observe(duration)

    def record_agent_result(self, role: str, status: str) -> None:
        """Record agent invocation result."""
        if PROMETHEUS_AVAILABLE:
            AGENT_CALLS.labels(
                subsystem=self.subsystem,
                role=role,
                status=status,
            ).inc()

    def record_validation_result(self, node_id: str, passed: bool) -> None:
        """Record schema validation result."""
        if PROMETHEUS_AVAILABLE:
            VALIDATION_RESULTS.labels(
                subsystem=self.subsystem,
                node_id=node_id,
                result="pass" if passed else "fail",
            ).inc()

    def record_memory_write(self, segment: str) -> None:
        """Record memory segment write."""
        if PROMETHEUS_AVAILABLE:
            MEMORY_WRITES.labels(
                subsystem=self.subsystem,
                segment=segment,
            ).inc()


# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "ORC-INTE-023",
    "governance_level": "high",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": ["intelligence", "logging", "metrics", "orchestration", "tracker"],
    "keywords": [
        "agent",
        "memory",
        "metrics",
        "orchestrator",
        "pattern",
        "pipeline",
        "prometheus",
        "record",
    ],
    "business_value": "Implements PatternMetrics for metrics functionality",
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
