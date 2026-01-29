"""
SymPy Metrics Collector
========================

Performance metrics collection and storage for symbolic computations.
Stores metrics in PostgreSQL for long-term analysis.

Version: 6.0.0
"""

from __future__ import annotations

# ============================================================================
__dora_meta__ = {
    "component_name": "Metrics",
    "module_version": "6.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2026-01-02T15:15:57Z",
    "updated_at": "2026-01-07T13:35:58Z",
    "layer": "operations",
    "domain": "symbolic_computation",
    "module_name": "metrics",
    "type": "service",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": ["PostgreSQL"],
        "memory_layers": [],
        "imported_by": [
            "services.symbolic_computation.api.routes",
            "services.symbolic_computation.core.__init__",
            "services.symbolic_computation.tools.symbolic_tool",
            "tests.services.symbolic_computation.test_integration",
        ],
    },
}
# ============================================================================

from datetime import datetime, timedelta
from typing import Any

import structlog

from services.symbolic_computation.config import SymbolicComputationConfig, get_config
from services.symbolic_computation.core.models import MetricsSummary

logger = structlog.get_logger(__name__)


class MetricsCollector:
    """
    Collect and store performance metrics for symbolic computations.

    Tracks:
    - Expression evaluation times (by backend)
    - Code generation times (by language)
    - Cache hit rates
    - Error rates

    Metrics are stored in PostgreSQL tables:
    - sympy_metrics: evaluation metrics
    - sympy_codegen_metrics: code generation metrics

    Example:
        collector = MetricsCollector()
        await collector.record_evaluation("x**2", "numpy", 1.5, True)
        summary = await collector.get_metrics_summary(last_hours=24)
    """

    def __init__(
        self,
        config: SymbolicComputationConfig | None = None,
        postgres_client: Any | None = None,
    ):
        """
        Initialize the metrics collector.

        Args:
            config: Configuration instance (uses global if not provided)
            postgres_client: Optional Postgres client for persistent storage
        """
        self.config = config or get_config()
        self.postgres_client = postgres_client
        self.logger = logger.bind(component="metrics_collector")

        # In-memory metrics buffer (for when Postgres is unavailable)
        self._evaluation_buffer: list[dict[str, Any]] = []
        self._codegen_buffer: list[dict[str, Any]] = []

        # Aggregated stats
        self._total_evaluations = 0
        self._total_codegens = 0
        self._evaluation_time_sum = 0.0
        self._codegen_time_sum = 0.0
        self._cache_hits = 0
        self._backend_usage: dict[str, int] = {}
        self._language_usage: dict[str, int] = {}

        self.logger.info(
            "metrics_collector_initialized",
            postgres_enabled=postgres_client is not None,
        )

    async def record_evaluation(
        self,
        expr: str,
        backend: str,
        duration_ms: float,
        success: bool,
        cache_hit: bool = False,
    ) -> None:
        """
        Record an expression evaluation metric.

        Args:
            expr: Expression that was evaluated
            backend: Backend used (numpy, math, mpmath)
            duration_ms: Evaluation time in milliseconds
            success: Whether evaluation succeeded
            cache_hit: Whether result was from cache
        """
        expr_hash = self._hash_expression(expr)
        timestamp = datetime.now(timezone.utc)

        metric = {
            "expr_hash": expr_hash,
            "backend": backend,
            "duration_ms": duration_ms,
            "success": success,
            "cache_hit": cache_hit,
            "timestamp": timestamp,
        }

        # Update in-memory stats
        self._total_evaluations += 1
        self._evaluation_time_sum += duration_ms
        if cache_hit:
            self._cache_hits += 1
        self._backend_usage[backend] = self._backend_usage.get(backend, 0) + 1

        # Store in buffer
        self._evaluation_buffer.append(metric)

        # Persist to Postgres if available
        if self.postgres_client:
            await self._persist_evaluation_metric(metric)

        # Prune buffer if too large
        if len(self._evaluation_buffer) > 10000:
            self._evaluation_buffer = self._evaluation_buffer[-5000:]

        self.logger.debug(
            "evaluation_metric_recorded",
            expr_hash=expr_hash,
            backend=backend,
            duration_ms=duration_ms,
        )

    async def record_compilation(
        self,
        expr: str,
        language: str,
        duration_ms: float,
        success: bool,
    ) -> None:
        """
        Record a code generation metric.

        Args:
            expr: Expression that was compiled
            language: Target language (C, Fortran, etc.)
            duration_ms: Generation time in milliseconds
            success: Whether generation succeeded
        """
        expr_hash = self._hash_expression(expr)
        timestamp = datetime.now(timezone.utc)

        metric = {
            "expr_hash": expr_hash,
            "language": language,
            "duration_ms": duration_ms,
            "success": success,
            "timestamp": timestamp,
        }

        # Update in-memory stats
        self._total_codegens += 1
        self._codegen_time_sum += duration_ms
        self._language_usage[language] = self._language_usage.get(language, 0) + 1

        # Store in buffer
        self._codegen_buffer.append(metric)

        # Persist to Postgres if available
        if self.postgres_client:
            await self._persist_codegen_metric(metric)

        # Prune buffer if too large
        if len(self._codegen_buffer) > 10000:
            self._codegen_buffer = self._codegen_buffer[-5000:]

        self.logger.debug(
            "codegen_metric_recorded",
            expr_hash=expr_hash,
            language=language,
            duration_ms=duration_ms,
        )

    async def get_metrics_summary(
        self,
        last_hours: int = 24,
    ) -> MetricsSummary:
        """
        Get summary of performance metrics.

        Args:
            last_hours: Time range for summary (default: 24 hours)

        Returns:
            MetricsSummary with aggregated statistics
        """
        # If Postgres available, query it
        if self.postgres_client:
            return await self._get_postgres_summary(last_hours)

        # Otherwise use in-memory stats
        avg_eval = (
            self._evaluation_time_sum / self._total_evaluations
            if self._total_evaluations > 0
            else 0.0
        )
        avg_codegen = (
            self._codegen_time_sum / self._total_codegens
            if self._total_codegens > 0
            else 0.0
        )
        cache_hit_rate = (
            self._cache_hits / self._total_evaluations * 100
            if self._total_evaluations > 0
            else 0.0
        )

        return MetricsSummary(
            total_evaluations=self._total_evaluations,
            total_code_generations=self._total_codegens,
            avg_evaluation_time_ms=round(avg_eval, 2),
            avg_codegen_time_ms=round(avg_codegen, 2),
            cache_hit_rate=round(cache_hit_rate, 2),
            backend_usage=self._backend_usage.copy(),
            language_usage=self._language_usage.copy(),
            time_range_hours=last_hours,
        )

    async def _persist_evaluation_metric(self, metric: dict[str, Any]) -> None:
        """Persist evaluation metric to PostgreSQL."""
        try:
            await self.postgres_client.execute(
                """
                INSERT INTO sympy_metrics
                (expr_hash, backend, duration_ms, success, cache_hit, timestamp)
                VALUES ($1, $2, $3, $4, $5, $6)
                """,
                metric["expr_hash"],
                metric["backend"],
                metric["duration_ms"],
                metric["success"],
                metric["cache_hit"],
                metric["timestamp"],
            )
        except Exception as e:
            self.logger.warning(
                "persist_evaluation_metric_failed",
                error=str(e),
            )

    async def _persist_codegen_metric(self, metric: dict[str, Any]) -> None:
        """Persist code generation metric to PostgreSQL."""
        try:
            await self.postgres_client.execute(
                """
                INSERT INTO sympy_codegen_metrics
                (expr_hash, language, duration_ms, success, timestamp)
                VALUES ($1, $2, $3, $4, $5)
                """,
                metric["expr_hash"],
                metric["language"],
                metric["duration_ms"],
                metric["success"],
                metric["timestamp"],
            )
        except Exception as e:
            self.logger.warning(
                "persist_codegen_metric_failed",
                error=str(e),
            )

    async def _get_postgres_summary(self, last_hours: int) -> MetricsSummary:
        """Get metrics summary from PostgreSQL."""
        cutoff = datetime.now(timezone.utc) - timedelta(hours=last_hours)

        try:
            # Query evaluation metrics
            eval_result = await self.postgres_client.fetchrow(
                """
                SELECT
                    COUNT(*) as total,
                    AVG(duration_ms) as avg_time,
                    SUM(CASE WHEN cache_hit THEN 1 ELSE 0 END)::float /
                        NULLIF(COUNT(*), 0) * 100 as hit_rate
                FROM sympy_metrics
                WHERE timestamp > $1
                """,
                cutoff,
            )

            # Query codegen metrics
            codegen_result = await self.postgres_client.fetchrow(
                """
                SELECT
                    COUNT(*) as total,
                    AVG(duration_ms) as avg_time
                FROM sympy_codegen_metrics
                WHERE timestamp > $1
                """,
                cutoff,
            )

            # Backend usage
            backend_rows = await self.postgres_client.fetch(
                """
                SELECT backend, COUNT(*) as count
                FROM sympy_metrics
                WHERE timestamp > $1
                GROUP BY backend
                """,
                cutoff,
            )
            backend_usage = {row["backend"]: row["count"] for row in backend_rows}

            # Language usage
            lang_rows = await self.postgres_client.fetch(
                """
                SELECT language, COUNT(*) as count
                FROM sympy_codegen_metrics
                WHERE timestamp > $1
                GROUP BY language
                """,
                cutoff,
            )
            language_usage = {row["language"]: row["count"] for row in lang_rows}

            return MetricsSummary(
                total_evaluations=eval_result["total"] or 0,
                total_code_generations=codegen_result["total"] or 0,
                avg_evaluation_time_ms=round(eval_result["avg_time"] or 0, 2),
                avg_codegen_time_ms=round(codegen_result["avg_time"] or 0, 2),
                cache_hit_rate=round(eval_result["hit_rate"] or 0, 2),
                backend_usage=backend_usage,
                language_usage=language_usage,
                time_range_hours=last_hours,
            )

        except Exception as e:
            self.logger.error(
                "postgres_summary_failed",
                error=str(e),
            )
            # Fall back to in-memory
            return await self.get_metrics_summary(last_hours)

    def _hash_expression(self, expr: str) -> str:
        """Generate hash for expression."""
        import hashlib

        return hashlib.sha256(expr.encode()).hexdigest()[:16]

    def reset(self) -> None:
        """Reset all in-memory metrics."""
        self._evaluation_buffer.clear()
        self._codegen_buffer.clear()
        self._total_evaluations = 0
        self._total_codegens = 0
        self._evaluation_time_sum = 0.0
        self._codegen_time_sum = 0.0
        self._cache_hits = 0
        self._backend_usage.clear()
        self._language_usage.clear()
        self.logger.info("metrics_reset")


# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "SER-OPER-023",
    "governance_level": "medium",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": [
        "async",
        "caching",
        "debugging",
        "logging",
        "metrics",
        "operations",
        "security",
        "service",
        "symbolic-computation",
    ],
    "keywords": [
        "analysis",
        "collector",
        "compilation",
        "evaluation",
        "metrics",
        "record",
        "reset",
        "summary",
    ],
    "business_value": "Implements MetricsCollector for metrics functionality",
    "last_modified": "2026-01-07T13:35:58Z",
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
