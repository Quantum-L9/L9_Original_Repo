"""
L9 Memory Substrate - Tool Audit Logging
=========================================

Non-blocking helper for logging tool invocations to the memory substrate.
Every tool call via ExecutorToolRegistry.dispatch_tool_call() is logged
as a TOOL_AUDIT packet for observability and governance.

This module is designed for:
- Zero-impact on tool execution latency (fire-and-forget)
- Never failing the tool call itself
- Automatic 24-hour TTL for cleanup
- Full audit trail for governance

Version: 1.0.0
Author: L9 Enterprise
"""

from __future__ import annotations

# ============================================================================
__dora_meta__ = {
    "component_name": "Tool Audit Logging",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2026-01-06T15:07:54Z",
    "updated_at": "2026-01-17T23:47:56Z",
    "layer": "learning",
    "domain": "memory_substrate",
    "module_name": "tool_audit",
    "type": "engine",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": ["PostgreSQL"],
        "memory_layers": ["working_memory"],
        "imported_by": [
            "tests.integration.test_tool_observability_integration",
            "tests.memory.test_tool_audit",
        ],
    },
}
# ============================================================================

import asyncio
from datetime import UTC, datetime, timedelta, timezone
from uuid import UUID, uuid4

import structlog

from core.decorators import must_stay_async
from core.schemas import PacketEnvelopeIn
from memory.substrate_models import MemorySegment
from telemetry.memory_metrics import record_tool_invocation

logger = structlog.get_logger(__name__)

# Default TTL for tool audit packets (24 hours)
TOOL_AUDIT_TTL_HOURS = 24


@must_stay_async("callers use await")
async def log_tool_invocation(
    call_id: UUID,
    tool_id: str,
    agent_id: str,
    task_id: str | None = None,
    status: str = "success",
    duration_ms: int = 0,
    error: str | None = None,
    arguments: dict | None = None,
    result_summary: str | None = None,
) -> None:
    """
    Log a tool invocation to the memory substrate (non-blocking).

    Creates a TOOL_AUDIT packet with full invocation details.
    This function NEVER raises - all errors are caught and logged.

    Args:
        call_id: Unique identifier for this tool call
        tool_id: Canonical tool identifier
        agent_id: Agent that invoked the tool
        task_id: Optional task ID for context
        status: "success" | "failure" | "timeout" | "denied"
        duration_ms: Execution duration in milliseconds
        error: Error message if status is failure
        arguments: Sanitized arguments (optional, for debugging)
        result_summary: Brief summary of result (optional)

    Returns:
        None (fire-and-forget, non-blocking)
    """
    try:
        # Import here to avoid circular dependency

        # Build audit packet payload
        payload = {
            "call_id": str(call_id),
            "tool_id": tool_id,
            "agent_id": agent_id,
            "status": status,
            "duration_ms": duration_ms,
            "timestamp": datetime.now(UTC).isoformat(),
        }

        if task_id:
            payload["task_id"] = task_id
        if error:
            payload["error"] = error[:500]  # Truncate long errors
        if arguments:
            # Sanitize arguments - remove sensitive data
            payload["arguments"] = _sanitize_arguments(arguments)
        if result_summary:
            payload["result_summary"] = result_summary[:200]

        # Create packet envelope
        # Note: PacketEnvelopeIn expects metadata/provenance/confidence as dicts
        packet = PacketEnvelopeIn(
            packet_id=uuid4(),
            packet_type=MemorySegment.TOOL_AUDIT.value,
            payload=payload,
            metadata={
                "schema_version": "1.0.0",
                "agent": agent_id,
                "domain": "tool_audit",
            },
            provenance={
                "source": "ExecutorToolRegistry",
                "tool": tool_id,
            },
            confidence={
                "score": 1.0,  # Tool audit is always high confidence
                "rationale": "Direct tool invocation observation",
            },
            tags=[
                f"tool:{tool_id}",
                f"agent:{agent_id}",
                f"status:{status}",
            ],
            ttl=datetime.now(UTC) + timedelta(hours=TOOL_AUDIT_TTL_HOURS),
        )

        # Fire-and-forget ingestion (don't await in main path)
        asyncio.create_task(_ingest_audit_packet(packet))

        # Also write to dedicated tool_audit_log Postgres table (fire-and-forget)
        asyncio.create_task(
            _write_to_audit_table(
                call_id=call_id,
                tool_id=tool_id,
                agent_id=agent_id,
                status=status,
                duration_ms=duration_ms,
                error=error,
                arguments=payload.get("arguments"),
            )
        )

        # Record Prometheus metrics (real-time observability)
        record_tool_invocation(
            tool_id=tool_id,
            status=status,
            duration_ms=duration_ms,
        )

        logger.debug(
            "Scheduled tool audit packet",
            call_id=str(call_id),
            tool_id=tool_id,
            status=status,
            duration_ms=duration_ms,
        )

    except Exception as e:
        # Never fail the tool call due to audit logging
        logger.warning(
            "Failed to schedule tool audit packet",
            error=str(e),
            call_id=str(call_id),
            tool_id=tool_id,
        )


async def _ingest_audit_packet(packet: PacketEnvelopeIn) -> None:
    """
    Internal: Actually ingest the audit packet (runs in background).

    Catches all exceptions to prevent any impact on calling code.
    """
    try:
        from memory.ingestion import ingest_packet

        result = await ingest_packet(packet)

        if result.status != "ok":
            logger.warning(
                "Tool audit packet ingestion incomplete",
                packet_id=str(packet.packet_id),
                status=result.status,
                error=result.error_message,
            )
    except Exception as e:
        logger.warning(
            "Tool audit packet ingestion failed",
            packet_id=str(packet.packet_id),
            error=str(e),
        )


@must_stay_async("callers use await")
async def _write_to_audit_table(
    call_id: UUID,
    tool_id: str,
    agent_id: str,
    status: str,
    duration_ms: int,
    error: str | None = None,
    arguments: dict | None = None,
) -> None:
    """
    Internal: Write audit entry to dedicated tool_audit_log Postgres table.

    Runs in background, catches all exceptions to prevent impact on calling code.
    """
    try:
        import json
        import os

        import asyncpg

        database_url = os.getenv("MEMORY_DSN") or os.getenv("DATABASE_URL")
        if not database_url:
            return  # No database configured

        conn = await asyncpg.connect(database_url)
        try:
            await conn.execute(
                """
                INSERT INTO tool_audit_log (
                    tool_name, agent_id, input_data, output_data,
                    duration_ms, tokens_used, cost_usd, error, timestamp, request_id
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
                """,
                tool_id,
                agent_id,
                json.dumps(arguments) if arguments else "{}",
                "{}",  # output_data not available at this level
                duration_ms,
                0,  # tokens_used
                0.0,  # cost_usd (could be calculated)
                error,
                datetime.now(UTC),
                call_id,  # Pass UUID directly, not str()
            )
            logger.debug(
                "Tool audit written to Postgres table",
                call_id=str(call_id),
                tool_id=tool_id,
            )
        finally:
            await conn.close()

    except Exception as e:
        logger.warning(
            "Failed to write tool audit to Postgres table",
            call_id=str(call_id),
            tool_id=tool_id,
            error=str(e),
        )


def _sanitize_arguments(arguments: dict) -> dict:
    """
    Sanitize tool arguments for audit logging.

    Removes or masks sensitive fields like passwords, tokens, keys.
    """
    sensitive_keys = {
        "password",
        "api_key",
        "token",
        "secret",
        "credential",
        "auth",
        "key",
    }

    sanitized = {}
    for key, value in arguments.items():
        key_lower = key.lower()
        if any(s in key_lower for s in sensitive_keys):
            sanitized[key] = "[REDACTED]"
        elif isinstance(value, str) and len(value) > 500:
            sanitized[key] = value[:500] + "...[truncated]"
        elif isinstance(value, dict):
            sanitized[key] = _sanitize_arguments(value)
        else:
            sanitized[key] = value

    return sanitized


# =============================================================================
# Public API
# =============================================================================

__all__ = [
    "TOOL_AUDIT_TTL_HOURS",
    "log_tool_invocation",
]

# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "MEM-LEAR-001",
    "governance_level": "critical",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [
        "core.decorators",
        "core.schemas",
        "memory.ingestion",
        "memory.substrate_models",
    ],
    "tags": [
        "api",
        "async",
        "audit-tool",
        "auth",
        "debugging",
        "engine",
        "event-driven",
        "learning",
        "logging",
        "memory-substrate",
    ],
    "keywords": [
        "audit",
        "governance",
        "invocation",
        "log",
        "logging",
        "memory",
        "module",
        "substrate",
    ],
    "business_value": "Zero-impact on tool execution latency (fire-and-forget) Never failing the tool call itself Automatic 24-hour TTL for cleanup Full audit trail for governance Version: 1.0.0 Author: L9 Enterprise",
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
