"""
L9 Tool Feedback Learning - Self-Improvement Engine
===================================================

GMP-TFL-001: Periodic analysis engine for tool outcome data.

Responsibilities:
- Refresh materialized view tool_success_rates_24h
- Detect degraded tools / underutilized high-performers
- Emit alerts into tool_learning_alerts and Prometheus metrics
"""

from __future__ import annotations

# ============================================================================
__dora_meta__ = {
    "component_name": "Self-Improvement Engine",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2026-01-25T14:50:13Z",
    "updated_at": "2026-01-25T14:49:28Z",
    "layer": "operations",
    "domain": "services",
    "module_name": "tool_learning_engine",
    "type": "dataclass",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": [],
        "memory_layers": ["working_memory"],
        "imported_by": [
            "services.tool_learning_scheduler",
            "tests.services.test_tool_learning_engine",
        ],
    },
}
# ============================================================================

from dataclasses import dataclass

import structlog

from config.settings import get_integration_settings

logger = structlog.get_logger(__name__)


@dataclass
class ToolHealthSnapshot:
    """
    Represents a snapshot of tool health metrics used for self-improvement analysis within the tool learning engine.

    Args:
        tool_name: Name of the tool being monitored.
        task_type: Optional type of task associated with the tool.
        success_rate: Proportion of successful executions.
        avg_latency_ms: Average execution latency in milliseconds.
        usage_count: Total number of times the tool was used.
    """

    tool_name: str
    task_type: str | None
    success_rate: float
    avg_latency_ms: float
    usage_count: int


class ToolLearningEngine:
    """Daily analysis engine over tool_execution_feedback and success rates."""

    def __init__(self, substrate_service: MemorySubstrateService) -> None:
        """Initialize the tool learning engine.

        Args:
            substrate_service: Memory substrate service for database access.
        """
        self.substrate = substrate_service

    async def _refresh_materialized_view(self) -> None:
        """Refresh the tool_success_rates_24h materialized view.

        Calls the refresh_tool_success_rates() stored procedure.
        Silently skips if no postgres_pool is available.
        """
        if not getattr(self.substrate, "postgres_pool", None):
            logger.debug("Tool learning: no postgres_pool, skipping MV refresh")
            return

        try:
            async with self.substrate.postgres_pool.acquire() as conn:
                await conn.execute("SELECT refresh_tool_success_rates()")
            logger.info("Tool learning: refreshed tool_success_rates_24h")
        except Exception as exc:
            logger.error(
                "Tool learning: refresh_tool_success_rates failed", error=str(exc)
            )

    async def _load_health_snapshots(self) -> list[ToolHealthSnapshot]:
        """Load tool health snapshots from the materialized view.

        Returns:
            List of ToolHealthSnapshot objects from tool_success_rates_24h.
        """
        if not getattr(self.substrate, "postgres_pool", None):
            return []

        try:
            async with self.substrate.postgres_pool.acquire() as conn:
                rows = await conn.fetch(
                    """
                    SELECT
                        tool_name,
                        task_type,
                        success_rate,
                        avg_latency_ms,
                        total_executions
                    FROM tool_success_rates_24h
                    """
                )

            snapshots: list[ToolHealthSnapshot] = []
            for row in rows:
                snapshots.append(
                    ToolHealthSnapshot(
                        tool_name=row["tool_name"],
                        task_type=row["task_type"],
                        success_rate=float(row["success_rate"] or 0.0),
                        avg_latency_ms=float(row["avg_latency_ms"] or 0.0),
                        usage_count=int(row["total_executions"] or 0),
                    )
                )
            return snapshots

        except Exception as exc:
            logger.error("Tool learning: load_health_snapshots failed", error=str(exc))
            return []

    async def _insert_alert(
        self,
        tool_name: str,
        alert_type: str,
        severity: str,
        snapshot: ToolHealthSnapshot,
        message: str,
    ) -> None:
        """Insert a tool learning alert into the database.

        Args:
            tool_name: Name of the tool.
            alert_type: Type of alert (e.g., 'degraded').
            severity: Alert severity (e.g., 'warning').
            snapshot: ToolHealthSnapshot with current metrics.
            message: Human-readable alert message.
        """
        if not getattr(self.substrate, "postgres_pool", None):
            return

        try:
            async with self.substrate.postgres_pool.acquire() as conn:
                await conn.execute(
                    """
                    INSERT INTO tool_learning_alerts (
                        tool_name,
                        alert_type,
                        severity,
                        success_rate,
                        avg_latency_ms,
                        usage_count,
                        message
                    )
                    VALUES ($1, $2, $3, $4, $5, $6, $7)
                    """,
                    tool_name,
                    alert_type,
                    severity,
                    snapshot.success_rate,
                    snapshot.avg_latency_ms,
                    snapshot.usage_count,
                    message,
                )
        except Exception as exc:
            logger.error("Tool learning: insert_alert failed", error=str(exc))

    async def daily_analysis(self) -> None:
        """
        Entry point for cron / scheduler.

        Steps:
        - Refresh MV
        - Load snapshots
        - Emit alerts for degraded and high-latency tools
        """
        settings = get_integration_settings()
        if not settings.l9_tool_feedback_enabled:
            logger.info("Tool learning: disabled via settings")
            return

        await self._refresh_materialized_view()
        snapshots = await self._load_health_snapshots()

        if not snapshots:
            logger.info("Tool learning: no snapshots available, skipping")
            return

        success_threshold = settings.l9_tool_alert_success_threshold
        min_usage = 10

        for snap in snapshots:
            if snap.usage_count < min_usage:
                continue

            if snap.success_rate < success_threshold:
                await self._insert_alert(
                    tool_name=snap.tool_name,
                    alert_type="degraded",
                    severity="warning",
                    snapshot=snap,
                    message=(
                        f"Tool {snap.tool_name} has success_rate={snap.success_rate:.2f} "
                        f"below threshold={success_threshold:.2f} "
                        f"(usage={snap.usage_count}, latency={snap.avg_latency_ms:.1f}ms)"
                    ),
                )

        logger.info(
            "Tool learning: daily analysis complete",
            snapshots=len(snapshots),
            success_threshold=success_threshold,
            min_usage=min_usage,
        )


# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "SER-OPER-002",
    "governance_level": "medium",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": [
        "async",
        "dataclass",
        "debugging",
        "engine",
        "logging",
        "messaging",
        "metrics",
        "operations",
        "scheduling",
        "services",
    ],
    "keywords": [
        "analysis",
        "daily",
        "engine",
        "health",
        "improvement",
        "learning",
        "snapshot",
        "tool",
    ],
    "business_value": "Provides tool learning engine components including ToolHealthSnapshot, ToolLearningEngine",
    "last_modified": "2026-01-25T14:49:28Z",
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
