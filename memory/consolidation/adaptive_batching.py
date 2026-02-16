"""
Adaptive Batching for Consolidation Workloads

Dynamically adjusts batch sizes based on:
- System load (CPU/memory pressure)
- Database connection pool availability
- Historical performance metrics

Prevents resource exhaustion during heavy consolidation periods.

Usage:
    from memory.consolidation.adaptive_batching import AdaptiveBatcher

    batcher = AdaptiveBatcher(min_batch=10, max_batch=100)
    batch_size = await batcher.get_optimal_batch_size()
"""

__dora_meta__ = {
    "component_name": "Adaptive Batching",
    "module_version": "1.0.0",
    "created_by": "Auto-fix ADR-0014",
    "created_at": "2026-02-13T23:37:34.996180+00:00",
    "updated_at": "2026-02-13T23:37:34.996180+00:00",
    "layer": "core",
    "domain": "memory",
    "module_name": "memory.consolidation.adaptive_batching",
    "type": "module",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": [],
        "memory_layers": [],
        "imported_by": [],
    },
}


from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import psutil
import structlog

from core.decorators import must_stay_async

logger = structlog.get_logger(__name__)


@dataclass
class SystemMetrics:
    """
    Current system resource utilization.

    Attributes:
        cpu_percent: CPU usage (0-100)
        memory_percent: Memory usage (0-100)
        available_db_connections: Number of free database connections
        timestamp: When metrics were collected
    """

    cpu_percent: float
    memory_percent: float
    available_db_connections: int
    timestamp: datetime


@dataclass
class BatchPerformance:
    """
    Historical performance of a batch size.

    Attributes:
        batch_size: Number of items in batch
        avg_duration_ms: Average processing time
        success_rate: Percentage of successful batches (0-1)
        samples: Number of observations
    """

    batch_size: int
    avg_duration_ms: float
    success_rate: float
    samples: int


class AdaptiveBatcher:
    """
    Dynamically adjusts batch sizes for consolidation operations.

    Strategy:
    - Start with default batch size
    - Monitor system resources (CPU, memory, DB connections)
    - Reduce batch size if resources are constrained
    - Increase batch size if resources are abundant
    - Track performance metrics to optimize over time

    Example:
        batcher = AdaptiveBatcher(min_batch=10, max_batch=100, default_batch=50)

        for chunk in data:
            batch_size = await batcher.get_optimal_batch_size()
            batch = chunk[:batch_size]

            start = time.time()
            await process_batch(batch)
            duration = time.time() - start

            await batcher.record_batch_result(batch_size, duration, success=True)
    """

    def __init__(
        self,
        min_batch: int = 10,
        max_batch: int = 100,
        default_batch: int = 50,
        cpu_threshold: float = 80.0,
        memory_threshold: float = 85.0,
        min_db_connections: int = 5,
    ):
        """
        Initialize the adaptive batcher.

        Args:
            min_batch: Minimum batch size (never go below this)
            max_batch: Maximum batch size (never exceed this)
            default_batch: Starting batch size
            cpu_threshold: Reduce batch if CPU usage exceeds this (%)
            memory_threshold: Reduce batch if memory usage exceeds this (%)
            min_db_connections: Reduce batch if fewer connections available
        """
        self.min_batch = min_batch
        self.max_batch = max_batch
        self.current_batch = default_batch
        self.cpu_threshold = cpu_threshold
        self.memory_threshold = memory_threshold
        self.min_db_connections = min_db_connections

        # Performance tracking
        self.performance_history: dict[int, BatchPerformance] = {}
        self.adjustment_cooldown = timedelta(seconds=10)
        self.last_adjustment = datetime.now(tz=UTC)

        logger.info(
            f"AdaptiveBatcher initialized: batch_range=[{min_batch}, {max_batch}], "
            f"default={default_batch}"
        )

    @must_stay_async("callers use await")
    async def get_system_metrics(self, db_pool=None) -> SystemMetrics:
        """
        Collect current system resource metrics.

        Args:
            db_pool: Optional database connection pool to check availability

        Returns:
            SystemMetrics with current resource utilization
        """
        cpu_percent = psutil.cpu_percent(interval=0.1)
        memory_percent = psutil.virtual_memory().percent

        # Check database connection pool
        available_db_connections = 10  # Default fallback
        if db_pool and hasattr(db_pool, "get_size"):
            available_db_connections = db_pool.get_size() - db_pool.get_busy_count()

        return SystemMetrics(
            cpu_percent=cpu_percent,
            memory_percent=memory_percent,
            available_db_connections=available_db_connections,
            timestamp=datetime.now(tz=UTC),
        )

    def _is_resource_constrained(self, metrics: SystemMetrics) -> bool:
        """
        Determine if system resources are under pressure.

        Args:
            metrics: Current system metrics

        Returns:
            True if resources are constrained
        """
        return (
            metrics.cpu_percent > self.cpu_threshold
            or metrics.memory_percent > self.memory_threshold
            or metrics.available_db_connections < self.min_db_connections
        )

    def _get_performance_score(self, batch_size: int) -> float | None:
        """
        Get performance score for a batch size (higher = better).

        Score formula: (success_rate * 1000) / avg_duration_ms

        Args:
            batch_size: Batch size to score

        Returns:
            Performance score, or None if no history
        """
        perf = self.performance_history.get(batch_size)
        if not perf or perf.samples < 3:  # Need at least 3 samples
            return None

        # Higher success rate and lower duration = better score
        return (perf.success_rate * 1000) / max(perf.avg_duration_ms, 1)

    async def get_optimal_batch_size(self, db_pool=None) -> int:
        """
        Calculate optimal batch size based on current conditions.

        Args:
            db_pool: Optional database pool for connection availability check

        Returns:
            Recommended batch size (between min_batch and max_batch)
        """
        metrics = await self.get_system_metrics(db_pool)

        # Check if we should adjust (respect cooldown)
        if datetime.now(tz=UTC) - self.last_adjustment < self.adjustment_cooldown:
            return self.current_batch

        # If resources are constrained, reduce batch size
        if self._is_resource_constrained(metrics):
            new_batch = max(self.min_batch, int(self.current_batch * 0.75))

            if new_batch != self.current_batch:
                logger.warning(
                    f"Resources constrained (CPU={metrics.cpu_percent:.1f}%, "
                    f"MEM={metrics.memory_percent:.1f}%, "
                    f"DB_CONN={metrics.available_db_connections}), "
                    f"reducing batch: {self.current_batch} -> {new_batch}"
                )
                self.current_batch = new_batch
                self.last_adjustment = datetime.now(tz=UTC)

        # If resources are abundant, consider increasing batch size
        elif (
            metrics.cpu_percent < self.cpu_threshold * 0.6
            and metrics.memory_percent < self.memory_threshold * 0.6
            and self.current_batch < self.max_batch
        ):
            # Check if larger batch has good historical performance
            candidate_batch = min(self.max_batch, int(self.current_batch * 1.25))
            candidate_score = self._get_performance_score(candidate_batch)
            current_score = self._get_performance_score(self.current_batch)

            # Only increase if candidate has better or unknown performance
            if candidate_score is None or (
                current_score and candidate_score > current_score
            ):
                logger.info(
                    f"Resources abundant, increasing batch: "
                    f"{self.current_batch} -> {candidate_batch}"
                )
                self.current_batch = candidate_batch
                self.last_adjustment = datetime.now(tz=UTC)

        return self.current_batch

    @must_stay_async("callers use await")
    async def record_batch_result(
        self, batch_size: int, duration_ms: float, success: bool
    ) -> None:
        """
        Record the result of a batch operation for learning.

        Args:
            batch_size: Size of the batch that was processed
            duration_ms: How long processing took (milliseconds)
            success: Whether the batch succeeded
        """
        if batch_size not in self.performance_history:
            self.performance_history[batch_size] = BatchPerformance(
                batch_size=batch_size,
                avg_duration_ms=duration_ms,
                success_rate=1.0 if success else 0.0,
                samples=1,
            )
        else:
            perf = self.performance_history[batch_size]

            # Update running averages
            total_samples = perf.samples + 1
            perf.avg_duration_ms = (
                perf.avg_duration_ms * perf.samples + duration_ms
            ) / total_samples
            perf.success_rate = (
                perf.success_rate * perf.samples + (1.0 if success else 0.0)
            ) / total_samples
            perf.samples = total_samples

        logger.debug(
            f"Recorded batch result: size={batch_size}, duration={duration_ms:.1f}ms, "
            f"success={success}"
        )

    def get_performance_report(self) -> dict:
        """
        Get summary of batch performance across all sizes.

        Returns:
            Dictionary with performance statistics
        """
        if not self.performance_history:
            return {"message": "No performance data collected yet"}

        report = {
            "current_batch_size": self.current_batch,
            "batch_sizes_tested": len(self.performance_history),
            "performance_by_size": [],
        }

        for batch_size in sorted(self.performance_history.keys()):
            perf = self.performance_history[batch_size]
            score = self._get_performance_score(batch_size)

            report["performance_by_size"].append(
                {
                    "batch_size": batch_size,
                    "avg_duration_ms": round(perf.avg_duration_ms, 2),
                    "success_rate": round(perf.success_rate * 100, 1),
                    "samples": perf.samples,
                    "performance_score": round(score, 2) if score else None,
                }
            )

        return report
