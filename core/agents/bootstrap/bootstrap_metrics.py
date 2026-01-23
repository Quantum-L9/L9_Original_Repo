"""
L9 Bootstrap - Prometheus Metrics
Version: 1.0.0

Prometheus metrics for bootstrap operations.
Implements BOOTSTRAP_IMPLEMENTATION_GUIDE monitoring requirements.

Metrics tracked:
- Phase duration (histogram per phase)
- Phase errors (counter)
- Rollbacks (counter)
- Init signatures generated (counter)
"""

from __future__ import annotations

# ============================================================================
__dora_meta__ = {
    "component_name": "Prometheus Metrics",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2026-01-15T15:23:54Z",
    "updated_at": "2026-01-17T23:47:56Z",
    "layer": "foundation",
    "domain": "agent_execution",
    "module_name": "bootstrap_metrics",
    "type": "tracker",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": [],
        "memory_layers": [],
        "imported_by": [],
    },
}
# ============================================================================

import time
import structlog
from contextlib import contextmanager
from typing import Generator

try:
    from prometheus_client import Counter, Histogram, Gauge

    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False

    # Stub classes for when prometheus_client is not installed
    class Counter:
        def __init__(self, *args, **kwargs):
            pass

        def labels(self, **kwargs):
            return self

        def inc(self, amount=1):
            pass

    class Histogram:
        def __init__(self, *args, **kwargs):
            pass

        def labels(self, **kwargs):
            return self

        def observe(self, value):
            pass

    class Gauge:
        def __init__(self, *args, **kwargs):
            pass

        def labels(self, **kwargs):
            return self

        def set(self, value):
            pass


logger = structlog.get_logger(__name__)


# =============================================================================
# Metric Definitions
# =============================================================================

# Phase duration histogram (per phase, per agent)
BOOTSTRAP_PHASE_DURATION = Histogram(
    "l9_bootstrap_phase_duration_seconds",
    "Time to complete each bootstrap phase",
    ["phase", "agent_id"],
    buckets=[0.01, 0.025, 0.05, 0.1, 0.15, 0.25, 0.5, 1.0, 2.5],
)

# Phase errors counter
BOOTSTRAP_PHASE_ERRORS = Counter(
    "l9_bootstrap_phase_errors_total",
    "Total bootstrap phase errors",
    ["phase", "agent_id", "error_type"],
)

# Rollbacks counter
BOOTSTRAP_ROLLBACKS = Counter(
    "l9_bootstrap_rollbacks_total",
    "Total bootstrap rollbacks triggered",
    ["agent_id", "failed_phase"],
)

# Init signatures generated counter
BOOTSTRAP_INIT_SIGNATURES = Counter(
    "l9_bootstrap_init_signatures_generated_total",
    "Total init signatures successfully generated",
    ["agent_id"],
)

# Bootstrap success/failure counter
BOOTSTRAP_TOTAL = Counter(
    "l9_bootstrap_total",
    "Total bootstrap attempts",
    ["agent_id", "status"],
)

# Active bootstraps gauge
ACTIVE_BOOTSTRAPS = Gauge(
    "l9_active_bootstraps",
    "Number of currently running bootstraps",
)

# Kernels bound gauge (per agent)
KERNELS_BOUND = Gauge(
    "l9_kernels_bound",
    "Number of kernels bound to agent",
    ["agent_id"],
)

# Tools bound gauge (per agent)
TOOLS_BOUND = Gauge(
    "l9_tools_bound",
    "Number of tools bound to agent",
    ["agent_id"],
)


# =============================================================================
# Metrics Helper Class
# =============================================================================


class BootstrapMetrics:
    """
    Helper class for bootstrap metric instrumentation.

    Provides context managers and methods for recording bootstrap metrics.
    """

    def __init__(self, agent_id: str):
        """
        Initialize metrics helper for an agent.

        Args:
            agent_id: Agent identifier for labeling metrics
        """
        self.agent_id = agent_id

    @contextmanager
    def time_phase(self, phase: int) -> Generator[None, None, None]:
        """
        Context manager to time a bootstrap phase.

        Args:
            phase: Phase number (0-7)

        Yields:
            None (timing is automatic)
        """
        phase_name = f"phase_{phase}"
        start = time.perf_counter()
        try:
            yield
        except Exception as e:
            BOOTSTRAP_PHASE_ERRORS.labels(
                phase=phase_name,
                agent_id=self.agent_id,
                error_type=type(e).__name__,
            ).inc()
            raise
        finally:
            duration = time.perf_counter() - start
            BOOTSTRAP_PHASE_DURATION.labels(
                phase=phase_name,
                agent_id=self.agent_id,
            ).observe(duration)

            logger.debug(
                "bootstrap.phase.metrics",
                agent_id=self.agent_id,
                phase=phase,
                duration_ms=duration * 1000,
            )

    @contextmanager
    def track_bootstrap(self) -> Generator[None, None, None]:
        """
        Context manager to track full bootstrap execution.

        Yields:
            None
        """
        ACTIVE_BOOTSTRAPS.inc()
        status = "success"
        try:
            yield
        except Exception:
            status = "failure"
            raise
        finally:
            ACTIVE_BOOTSTRAPS.dec()
            BOOTSTRAP_TOTAL.labels(
                agent_id=self.agent_id,
                status=status,
            ).inc()

    def record_rollback(self, failed_phase: int) -> None:
        """
        Record a bootstrap rollback.

        Args:
            failed_phase: Phase number that triggered rollback
        """
        BOOTSTRAP_ROLLBACKS.labels(
            agent_id=self.agent_id,
            failed_phase=f"phase_{failed_phase}",
        ).inc()

        logger.warning(
            "bootstrap.rollback.metrics",
            agent_id=self.agent_id,
            failed_phase=failed_phase,
        )

    def record_init_signature(self) -> None:
        """Record successful init signature generation."""
        BOOTSTRAP_INIT_SIGNATURES.labels(
            agent_id=self.agent_id,
        ).inc()

    def set_kernels_bound(self, count: int) -> None:
        """
        Set number of kernels bound.

        Args:
            count: Number of kernels bound
        """
        KERNELS_BOUND.labels(
            agent_id=self.agent_id,
        ).set(count)

    def set_tools_bound(self, count: int) -> None:
        """
        Set number of tools bound.

        Args:
            count: Number of tools bound
        """
        TOOLS_BOUND.labels(
            agent_id=self.agent_id,
        ).set(count)


# =============================================================================
# Module-level helper
# =============================================================================


def get_bootstrap_metrics(agent_id: str) -> BootstrapMetrics:
    """
    Get metrics helper for an agent's bootstrap.

    Args:
        agent_id: Agent identifier

    Returns:
        BootstrapMetrics instance
    """
    return BootstrapMetrics(agent_id)


# =============================================================================
# Public API
# =============================================================================

__all__ = [
    "BootstrapMetrics",
    "get_bootstrap_metrics",
    "BOOTSTRAP_PHASE_DURATION",
    "BOOTSTRAP_PHASE_ERRORS",
    "BOOTSTRAP_ROLLBACKS",
    "BOOTSTRAP_INIT_SIGNATURES",
    "BOOTSTRAP_TOTAL",
    "ACTIVE_BOOTSTRAPS",
    "KERNELS_BOUND",
    "TOOLS_BOUND",
    "PROMETHEUS_AVAILABLE",
]

# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "COR-FOUN-045",
    "governance_level": "critical",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": [
        "agent-execution",
        "api",
        "debugging",
        "foundation",
        "logging",
        "metrics",
        "monitoring",
        "tracker",
    ],
    "keywords": [
        "bootstrap",
        "bound",
        "counter",
        "gauge",
        "histogram",
        "kernels",
        "labels",
        "metrics",
    ],
    "business_value": "Implements BOOTSTRAP_IMPLEMENTATION_GUIDE monitoring requirements. Phase duration (histogram per phase) Phase errors (counter) Rollbacks (counter) Init signatures generated (counter)",
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
