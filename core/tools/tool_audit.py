"""
Tool Audit Trail + Cost Tracking

Harvested from: L9-Implementation-Suite-Ready-to-Deploy.md
Purpose: Audit trail for all tool executions with cost estimation.
"""

from __future__ import annotations

# ============================================================================
__dora_meta__ = {
    "component_name": "Tool Audit",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2026-01-06T15:07:54Z",
    "updated_at": "2026-01-17T23:47:56Z",
    "layer": "foundation",
    "domain": "tool_registry",
    "module_name": "tool_audit",
    "type": "dataclass",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": ["PostgreSQL"],
        "memory_layers": ["working_memory"],
        "imported_by": ["api.server"],
    },
}
# ============================================================================

import asyncio
import json
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any
from uuid import uuid4

import structlog

if TYPE_CHECKING:
    from memory.substrate_service import MemorySubstrateService

import contextlib

from core.decorators import must_stay_async
from services.tool_feedback_service import (
    ToolFeedbackEntry,
    get_tool_feedback_service,
)

logger = structlog.get_logger(__name__)


@dataclass
class ToolAuditEntry:
    """Record of single tool execution"""

    tool_name: str
    agent_id: str
    input_data: dict
    output_data: dict
    duration_ms: float
    tokens_used: int = 0
    cost_usd: float = 0.0
    error: str | None = None
    timestamp: str | None = None
    request_id: str | None = None

    def __post_init__(self):
        """
        Initializes missing timestamp and request ID for a ToolAuditEntry instance.
        Args:
            self: The ToolAuditEntry object being initialized.
        """
        if not self.timestamp:
            self.timestamp = datetime.now(UTC).isoformat()
        if not self.request_id:
            self.request_id = str(uuid4())


class ToolCostEstimator:
    """Estimate cost per tool call"""

    # Cost mappings (update with actual pricing)
    COST_PER_TOOL = {
        "search_web": 0.001,
        "python_execute": 0.005,
        "git_commit": 0.002,
        "memory_write": 0.0001,
        "memory_search": 0.0005,
        "llm_analyze": 0.01,
        "gmp_run": 0.05,
    }

    def estimate(self, tool_name: str, input_data: dict, output_data: dict) -> float:
        """Estimate tool execution cost"""
        base_cost = self.COST_PER_TOOL.get(tool_name, 0.001)

        # Adjust by input/output size
        input_tokens = len(json.dumps(input_data).split()) * 0.25
        output_tokens = len(json.dumps(output_data).split()) * 0.25
        token_cost = (input_tokens + output_tokens) * 0.00001

        return base_cost + token_cost


class ToolAuditService:
    """
    Initializes the ToolAuditService for tracking tool execution history and cost estimation within the audit trail system.

    Args:
        substrate_service: MemorySubstrateService instance for storing audit data.
        buffer_size: Maximum number of audit entries before auto-flush.


    Raises:
        TypeError: If substrate_service is not a MemorySubstrateService instance.
    """

    """Audit trail for all tool executions"""

    def __init__(
        self,
        substrate_service: MemorySubstrateService,
        buffer_size: int = 100,
    ):
        """
        Initializes the ToolAuditService for tracking tool execution history and cost estimation within the audit trail system.

        Args:
            substrate_service: MemorySubstrateService instance for storing audit data.
            buffer_size: Maximum number of audit entries to buffer before flushing.


        Raises:
            TypeError: If substrate_service is not an instance of MemorySubstrateService.
        """
        self.substrate = substrate_service
        self.buffer_size = buffer_size
        self.local_buffer: list[ToolAuditEntry] = []
        self.cost_estimator = ToolCostEstimator()
        self._flush_task: asyncio.Task | None = None

    @must_stay_async("callers use await")
    async def start(self) -> None:
        """Start background flush task"""
        self._flush_task = asyncio.create_task(self._auto_flush())
        logger.info("Tool audit service started")

    async def stop(self) -> None:
        """Stop background flush"""
        if self._flush_task:
            self._flush_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._flush_task
        await self.flush()
        logger.info("Tool audit service stopped")

    async def log_execution(self, entry: ToolAuditEntry) -> None:
        """Log tool execution (buffered)"""
        self.local_buffer.append(entry)

        if len(self.local_buffer) >= self.buffer_size:
            await self.flush()

    async def flush(self) -> None:
        """Flush buffer to persistent storage"""
        if not self.local_buffer:
            return

        # Atomic swap: take current buffer, replace with empty list
        buffer_copy, self.local_buffer = self.local_buffer, []

        flush_error: Exception | None = None

        # Store in Postgres if available
        if hasattr(self.substrate, "postgres_pool") and self.substrate.postgres_pool:
            async with self.substrate.postgres_pool.acquire() as conn:
                try:
                    await conn.executemany(
                        """
                        INSERT INTO tool_audit_log (
                            tool_name, agent_id, input_data, output_data,
                            duration_ms, tokens_used, cost_usd, error, timestamp, request_id
                        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
                    """,
                        [
                            (
                                e.tool_name,
                                e.agent_id,
                                json.dumps(e.input_data),
                                json.dumps(e.output_data),
                                e.duration_ms,
                                e.tokens_used,
                                e.cost_usd,
                                e.error,
                                e.timestamp,
                                e.request_id,
                            )
                            for e in buffer_copy
                        ],
                    )
                except Exception as exc:
                    flush_error = exc

        if flush_error is not None:
            logger.exception(
                "audit_flush_failed",
                entry_count=len(buffer_copy),
            )
            # Prepend failed entries BEFORE any new ones added during the write
            self.local_buffer = buffer_copy + self.local_buffer
        else:
            logger.info("Flushed audit entries", count=len(buffer_copy))

    async def _auto_flush(self) -> None:
        """Periodically flush buffer"""
        while True:
            try:
                await asyncio.sleep(60)
                await self.flush()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Auto-flush error", error=str(e))

    @must_stay_async("callers use await")
    async def get_tool_metrics(
        self,
        agent_id: str | None = None,
        period: str = "24h",
    ) -> dict:
        """Get tool usage metrics"""
        if (
            not hasattr(self.substrate, "postgres_pool")
            or not self.substrate.postgres_pool
        ):
            return {"error": "PostgreSQL not available"}

        where_clause = "WHERE 1=1"
        params = []

        if agent_id:
            where_clause += " AND agent_id = $1"
            params = [agent_id]

        # Time period filter
        if period == "24h":
            time_filter = " AND timestamp > NOW() - INTERVAL '24 hours'"
        elif period == "7d":
            time_filter = " AND timestamp > NOW() - INTERVAL '7 days'"
        elif period == "30d":
            time_filter = " AND timestamp > NOW() - INTERVAL '30 days'"
        else:
            time_filter = ""

        try:
            async with self.substrate.postgres_pool.acquire() as conn:
                rows = await conn.fetch(
                    f"""
                    SELECT
                        tool_name,
                        COUNT(*) as call_count,
                        COUNT(CASE WHEN error IS NULL THEN 1 END) as success_count,
                        AVG(duration_ms) as avg_duration_ms,
                        SUM(cost_usd) as total_cost
                    FROM tool_audit_log
                    {where_clause}
                    {time_filter}
                    GROUP BY tool_name
                    ORDER BY total_cost DESC
                """,
                    *params,
                )

            metrics = {}
            total_cost = 0.0

            for row in rows:
                tool_name = row["tool_name"]
                metrics[tool_name] = {
                    "call_count": row["call_count"],
                    "success_count": row["success_count"],
                    "avg_duration_ms": float(row["avg_duration_ms"] or 0),
                    "cost_usd": float(row["total_cost"] or 0),
                }
                total_cost += float(row["total_cost"] or 0)

            return {
                "metrics_by_tool": metrics,
                "total_cost_usd": total_cost,
                "period": period,
                "agent_id": agent_id,
            }

        except Exception as e:
            logger.error("Error getting tool metrics", error=str(e))
            return {"error": str(e)}


async def execute_tool_with_audit(
    tool_name: str,
    agent_id: str,
    input_data: dict,
    executor: Any,
    audit_service: ToolAuditService,
    substrate_service: MemorySubstrateService,  # NEW
) -> Any:
    """Execute tool with automatic audit logging"""

    start_time = time.time()
    request_id = str(uuid4())

    try:
        # Execute tool
        output = await executor.call(tool_name, input_data)
        duration_ms = (time.time() - start_time) * 1000

        # Estimate cost
        cost = audit_service.cost_estimator.estimate(
            tool_name,
            input_data,
            output or {},
        )

        # Log success
        entry = ToolAuditEntry(
            tool_name=tool_name,
            agent_id=agent_id,
            input_data=input_data,
            output_data=output or {},
            duration_ms=duration_ms,
            cost_usd=cost,
            request_id=request_id,
        )

        await audit_service.log_execution(entry)

        # --------------------------------------------------------------
        # NEW: Record feedback for learning
        # --------------------------------------------------------------
        try:
            feedback_service = get_tool_feedback_service(substrate_service)

            # Optional context hints from input_data, preserved if present
            task_query = input_data.get("_task_query", "")
            task_type = input_data.get("_task_type")
            session_id = input_data.get("_session_id")
            confidence_score = input_data.get("_tool_confidence")
            discovery_rank = input_data.get("_tool_rank")

            # Embedding is resolved in the discovery path; for audit-only calls we can
            # store an empty vector (or let discovery skip feedback).
            # Here we bootstrap with an empty list, and rely on discovery-aware calls
            # to populate task_embedding properly.
            task_embedding = input_data.get("_task_embedding", [])

            feedback_entry = ToolFeedbackEntry(
                task_query=task_query or tool_name,
                task_embedding=task_embedding,
                task_type=task_type,
                session_id=session_id,
                tool_name=tool_name,
                success=True,
                execution_time_ms=duration_ms,
                error_type=None,
                agent_id=agent_id,
                confidence_score=confidence_score,
                discovery_rank=discovery_rank,
                request_id=request_id,
            )
            await feedback_service.record_outcome(feedback_entry)
        except Exception as e:
            logger.debug("Tool feedback recording failed (success path)", error=str(e))
        # --------------------------------------------------------------

        return output

    except Exception as e:
        duration_ms = (time.time() - start_time) * 1000

        # Log failure
        entry = ToolAuditEntry(
            tool_name=tool_name,
            agent_id=agent_id,
            input_data=input_data,
            output_data={},
            duration_ms=duration_ms,
            error=str(e),
            request_id=request_id,
        )

        await audit_service.log_execution(entry)

        # --------------------------------------------------------------
        # NEW: Record failed feedback for learning
        # --------------------------------------------------------------
        try:
            feedback_service = get_tool_feedback_service(substrate_service)

            task_query = input_data.get("_task_query", "")
            task_type = input_data.get("_task_type")
            session_id = input_data.get("_session_id")
            confidence_score = input_data.get("_tool_confidence")
            discovery_rank = input_data.get("_tool_rank")
            task_embedding = input_data.get("_task_embedding", [])

            feedback_entry = ToolFeedbackEntry(
                task_query=task_query or tool_name,
                task_embedding=task_embedding,
                task_type=task_type,
                session_id=session_id,
                tool_name=tool_name,
                success=False,
                execution_time_ms=duration_ms,
                error_type=type(e).__name__,
                agent_id=agent_id,
                confidence_score=confidence_score,
                discovery_rank=discovery_rank,
                request_id=request_id,
            )
            await feedback_service.record_outcome(feedback_entry)
        except Exception as fe:
            logger.debug("Tool feedback recording failed (error path)", error=str(fe))
        # --------------------------------------------------------------

        raise


# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "COR-FOUN-015",
    "governance_level": "critical",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": ["core.decorators", "memory.substrate_service"],
    "tags": [
        "async",
        "audit-tool",
        "dataclass",
        "foundation",
        "logging",
        "metrics",
        "serialization",
        "service",
        "testing",
        "tool-registry",
    ],
    "keywords": [
        "audit",
        "cost",
        "entry",
        "estimate",
        "estimator",
        "execute",
        "execution",
        "flush",
    ],
    "business_value": "Provides tool audit components including ToolAuditEntry, ToolCostEstimator, ToolAuditService",
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
