"""
L9 Memory - Checkpoint Metrics
Version: 1.0.0

Prometheus metrics for checkpoint operations.
Implements memory_spec_v3.0.yaml observability requirements.

Responsibilities:
- Track checkpoint create/restore latency
- Count operations (success/failure)
- Monitor checkpoint sizes and storage
- Expose metrics for Prometheus scraping
"""

from __future__ import annotations

# ============================================================================
__dora_meta__ = {
    "component_name": "Checkpoint Metrics",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2026-01-15T11:17:09Z",
    "updated_at": "2026-01-17T23:47:56Z",
    "layer": "learning",
    "domain": "memory_substrate",
    "module_name": "checkpoint_metrics",
    "type": "tracker",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": [],
        "memory_layers": [],
        "imported_by": ["memory.__init__", "memory.agent_persistence"],
    },
}
# ============================================================================

import time
from contextlib import contextmanager
from typing import TYPE_CHECKING

import structlog

if TYPE_CHECKING:
    from collections.abc import Generator

try:
    from prometheus_client import (  # noqa: F401 — REGISTRY used conditionally
        REGISTRY,
        Counter,
        Gauge,
        Histogram,
    )

    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False

    # Stub classes for when prometheus_client is not installed
    class Counter:
        """Stub Counter class for when prometheus_client is not installed.

        Provides a no-op implementation that allows code to run without
        the prometheus_client dependency.
        """

        def __init__(self, *args, **kwargs) -> None:
            """Initialize stub Counter (no-op)."""
            pass

        def labels(self, **kwargs) -> Counter:
            """Return self for method chaining (no-op)."""
            return self

        def inc(self, amount: int = 1) -> None:
            """Increment counter (no-op)."""
            pass

    class Histogram:
        """Stub Histogram class for when prometheus_client is not installed.

        Provides a no-op implementation that allows code to run without
        the prometheus_client dependency.
        """

        def __init__(self, *args, **kwargs) -> None:
            """Initialize stub Histogram (no-op)."""
            pass

        def labels(self, **kwargs) -> Histogram:
            """Return self for method chaining (no-op)."""
            return self

        def observe(self, value: float) -> None:
            """Record observation (no-op)."""
            pass

    class Gauge:
        """Stub Gauge class for when prometheus_client is not installed.

        Provides a no-op implementation that allows code to run without
        the prometheus_client dependency.
        """

        def __init__(self, *args, **kwargs) -> None:
            """Initialize stub Gauge (no-op)."""
            pass

        def labels(self, **kwargs) -> Gauge:
            """Return self for method chaining (no-op)."""
            return self

        def set(self, value: float) -> None:
            """Set gauge value (no-op)."""
            pass

        def inc(self, amount: int = 1) -> None:
            """Increment gauge (no-op)."""
            pass

        def dec(self, amount: int = 1) -> None:
            """Decrement gauge (no-op)."""
            pass


logger = structlog.get_logger(__name__)


# =============================================================================
# Metric Definitions
# =============================================================================

# Latency histograms
CHECKPOINT_CREATE_LATENCY = Histogram(
    "l9_checkpoint_create_latency_seconds",
    "Time to create a checkpoint",
    ["agent_id", "reason"],
    buckets=[0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
)

CHECKPOINT_RESTORE_LATENCY = Histogram(
    "l9_checkpoint_restore_latency_seconds",
    "Time to restore a checkpoint",
    ["agent_id"],
    buckets=[0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
)

CHECKPOINT_VALIDATE_LATENCY = Histogram(
    "l9_checkpoint_validate_latency_seconds",
    "Time to validate checkpoint integrity",
    ["agent_id"],
    buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5],
)

# Operation counters
CHECKPOINT_CREATE_TOTAL = Counter(
    "l9_checkpoint_create_total",
    "Total checkpoints created",
    ["agent_id", "reason", "status"],
)

CHECKPOINT_RESTORE_TOTAL = Counter(
    "l9_checkpoint_restore_total",
    "Total checkpoint restore attempts",
    ["agent_id", "status"],
)

CHECKPOINT_DELETE_TOTAL = Counter(
    "l9_checkpoint_delete_total",
    "Total checkpoints deleted",
    ["agent_id", "reason"],
)

CHECKPOINT_VALIDATION_TOTAL = Counter(
    "l9_checkpoint_validation_total",
    "Total checkpoint validations",
    ["agent_id", "status"],
)

CHECKPOINT_CORRUPTION_DETECTED = Counter(
    "l9_checkpoint_corruption_detected_total",
    "Total corrupted checkpoints detected",
    ["agent_id"],
)

# Size histograms
CHECKPOINT_SIZE_BYTES = Histogram(
    "l9_checkpoint_size_bytes",
    "Size of checkpoint state in bytes",
    ["agent_id"],
    buckets=[100, 500, 1000, 5000, 10000, 50000, 100000, 500000, 1000000],
)

# Gauges
ACTIVE_CHECKPOINTS = Gauge(
    "l9_active_checkpoints",
    "Number of active checkpoints per agent",
    ["agent_id"],
)

# Connection Pool Gauges (GMP-105 Batch 2)
CHECKPOINT_POOL_SIZE = Gauge(
    "l9_checkpoint_pool_size",
    "Total connections in checkpoint database pool",
)

CHECKPOINT_POOL_AVAILABLE = Gauge(
    "l9_checkpoint_pool_available",
    "Available connections in checkpoint database pool",
)

CHECKPOINT_POOL_WAITING = Gauge(
    "l9_checkpoint_pool_requests_waiting",
    "Requests waiting for checkpoint database pool connection",
)


# =============================================================================
# Metric Helpers
# =============================================================================


class CheckpointMetrics:
    """
    Helper class for checkpoint metric instrumentation.

    Provides context managers and methods for recording metrics.
    """

    def __init__(self, agent_id: str):
        """
        Initialize metrics helper for an agent.

        Args:
            agent_id: Agent identifier for labeling metrics
        """
        self.agent_id = agent_id

    @contextmanager
    def time_create(self, reason: str) -> Generator[None, None, None]:
        """
        Context manager to time checkpoint creation.

        Args:
            reason: Checkpoint trigger reason

        Yields:
            None (timing is automatic)
        """
        start = time.perf_counter()
        status = "success"
        try:
            yield
        except Exception:
            status = "error"
            raise
        finally:
            duration = time.perf_counter() - start
            CHECKPOINT_CREATE_LATENCY.labels(
                agent_id=self.agent_id,
                reason=reason,
            ).observe(duration)
            CHECKPOINT_CREATE_TOTAL.labels(
                agent_id=self.agent_id,
                reason=reason,
                status=status,
            ).inc()

            logger.debug(
                "checkpoint.create.metrics",
                agent_id=self.agent_id,
                reason=reason,
                duration_ms=duration * 1000,
                status=status,
            )

    @contextmanager
    def time_restore(self) -> Generator[None, None, None]:
        """
        Context manager to time checkpoint restoration.

        Yields:
            None (timing is automatic)
        """
        start = time.perf_counter()
        status = "success"
        try:
            yield
        except Exception:
            status = "error"
            raise
        finally:
            duration = time.perf_counter() - start
            CHECKPOINT_RESTORE_LATENCY.labels(
                agent_id=self.agent_id,
            ).observe(duration)
            CHECKPOINT_RESTORE_TOTAL.labels(
                agent_id=self.agent_id,
                status=status,
            ).inc()

            logger.debug(
                "checkpoint.restore.metrics",
                agent_id=self.agent_id,
                duration_ms=duration * 1000,
                status=status,
            )

    @contextmanager
    def time_validate(self) -> Generator[None, None, None]:
        """
        Context manager to time checkpoint validation.

        Yields:
            None (timing is automatic)
        """
        start = time.perf_counter()
        status = "success"
        try:
            yield
        except Exception:
            status = "error"
            raise
        finally:
            duration = time.perf_counter() - start
            CHECKPOINT_VALIDATE_LATENCY.labels(
                agent_id=self.agent_id,
            ).observe(duration)

            logger.debug(
                "checkpoint.validate.metrics",
                agent_id=self.agent_id,
                duration_ms=duration * 1000,
                status=status,
            )

    def record_size(self, size_bytes: int) -> None:
        """
        Record checkpoint size.

        Args:
            size_bytes: Size of checkpoint state in bytes
        """
        CHECKPOINT_SIZE_BYTES.labels(
            agent_id=self.agent_id,
        ).observe(size_bytes)

    def record_delete(self, count: int, reason: str = "retention") -> None:
        """
        Record checkpoint deletion.

        Args:
            count: Number of checkpoints deleted
            reason: Deletion reason (retention, manual, etc.)
        """
        CHECKPOINT_DELETE_TOTAL.labels(
            agent_id=self.agent_id,
            reason=reason,
        ).inc(count)

    def record_corruption(self) -> None:
        """Record detected checkpoint corruption."""
        CHECKPOINT_CORRUPTION_DETECTED.labels(
            agent_id=self.agent_id,
        ).inc()

    def record_validation(self, valid: bool) -> None:
        """
        Record validation result.

        Args:
            valid: Whether checkpoint was valid
        """
        CHECKPOINT_VALIDATION_TOTAL.labels(
            agent_id=self.agent_id,
            status="valid" if valid else "invalid",
        ).inc()

    def set_active_count(self, count: int) -> None:
        """
        Set active checkpoint count for agent.

        Args:
            count: Number of active checkpoints
        """
        ACTIVE_CHECKPOINTS.labels(
            agent_id=self.agent_id,
        ).set(count)


# =============================================================================
# Pool Stats Helper (GMP-105 Batch 2)
# =============================================================================


def record_pool_stats(
    pool_size: int = -1,
    pool_available: int = -1,
    requests_waiting: int = -1,
) -> None:
    """
    Record checkpoint connection pool statistics.

    Updates Prometheus gauges for pool monitoring.
    Called periodically or on-demand to update pool health metrics.

    Args:
        pool_size: Total connections in pool (-1 if unknown)
        pool_available: Available connections (-1 if unknown)
        requests_waiting: Requests waiting for connection (-1 if unknown)
    """
    if pool_size >= 0:
        CHECKPOINT_POOL_SIZE.set(pool_size)
    if pool_available >= 0:
        CHECKPOINT_POOL_AVAILABLE.set(pool_available)
    if requests_waiting >= 0:
        CHECKPOINT_POOL_WAITING.set(requests_waiting)

    logger.debug(
        "checkpoint.pool.stats.updated",
        pool_size=pool_size,
        pool_available=pool_available,
        requests_waiting=requests_waiting,
    )


def get_pool_stats_dict() -> dict:
    """
    Get current pool stats as a dictionary.

    Returns dict with pool_size, pool_available, requests_waiting.
    Values are -1 if metrics not yet recorded.

    Returns:
        Dict with pool statistics
    """
    # Note: Prometheus Gauge doesn't have a native "get" method,
    # so we return placeholder indicating "check Prometheus endpoint"
    return {
        "pool_size": "check /metrics",
        "pool_available": "check /metrics",
        "requests_waiting": "check /metrics",
        "prometheus_available": PROMETHEUS_AVAILABLE,
    }


# =============================================================================
# Module-level helper
# =============================================================================


def get_metrics(agent_id: str) -> CheckpointMetrics:
    """
    Get metrics helper for an agent.

    Args:
        agent_id: Agent identifier

    Returns:
        CheckpointMetrics instance
    """
    return CheckpointMetrics(agent_id)


# =============================================================================
# Public API
# =============================================================================

__all__ = [
    "ACTIVE_CHECKPOINTS",
    "CHECKPOINT_CORRUPTION_DETECTED",
    "CHECKPOINT_CREATE_LATENCY",
    "CHECKPOINT_CREATE_TOTAL",
    "CHECKPOINT_DELETE_TOTAL",
    "CHECKPOINT_POOL_AVAILABLE",
    "CHECKPOINT_POOL_SIZE",
    "CHECKPOINT_POOL_WAITING",
    "CHECKPOINT_RESTORE_LATENCY",
    "CHECKPOINT_RESTORE_TOTAL",
    "CHECKPOINT_SIZE_BYTES",
    "CHECKPOINT_VALIDATE_LATENCY",
    "CHECKPOINT_VALIDATION_TOTAL",
    "PROMETHEUS_AVAILABLE",
    "CheckpointMetrics",
    "get_metrics",
    "get_pool_stats_dict",
    "record_pool_stats",
]

# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "MEM-LEAR-006",
    "governance_level": "critical",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": [
        "debugging",
        "learning",
        "logging",
        "memory-substrate",
        "metrics",
        "monitoring",
        "rest-api",
        "tracker",
    ],
    "keywords": [
        "active",
        "checkpoint",
        "corruption",
        "count",
        "counter",
        "create",
        "delete",
        "gauge",
    ],
    "business_value": "Implements memory_spec_v3.0.yaml observability requirements.",
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
