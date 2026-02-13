"""
Mandatory Audit Logging with Circuit Breaker and Fallback

GOVERNANCE INVARIANT: Audit logging must be mandatory (no silent failures).
If both DB and file fallback fail, the operation MUST be rejected.

This module provides:
- AuditLogger: Main class for audit logging with circuit breaker
- Fail-closed semantics: Operations fail if audit cannot be recorded
- File fallback: When DB fails, logs to local JSONL file
- Alert mechanism: Logs warnings when using fallback storage
"""

# ============================================================================
__dora_meta__ = {
    "component_name": "Audit",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2026-01-15T11:17:09Z",
    "updated_at": "2026-01-17T23:47:56Z",
    "layer": "integration",
    "domain": "mcp_integration",
    "module_name": "audit",
    "type": "service",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": [],
        "memory_layers": ["semantic_memory"],
        "imported_by": ["tests.memory.test_governance_invariants"],
    },
}
# ============================================================================

import json
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime, timezone
from pathlib import Path
from typing import Any

import aiofiles
import structlog

from core.decorators import must_stay_async
from core.observability.circuit_breaker import CircuitBreaker, CircuitBreakerConfig
from src.config import settings

logger = structlog.get_logger(__name__)


class AuditLogger:
    """
    Audit logger with circuit breaker and file fallback.

    GOVERNANCE: Fail-closed semantics - if audit cannot be recorded anywhere,
    the operation MUST fail with RuntimeError.

    Flow:
    1. Try DB write (with circuit breaker)
    2. If DB fails, try file fallback
    3. If both fail, raise RuntimeError (fail-closed)
    """

    def __init__(
        self,
        execute_fn: Callable[..., Awaitable[Any]],
        fallback_path: str | None = None,
        failure_threshold: int = 3,
        recovery_timeout: int = 60,
    ):
        """
        Initialize audit logger.

        Args:
            execute_fn: Async function to execute DB queries
            fallback_path: Path to fallback JSONL file (default from settings)
            failure_threshold: Circuit breaker failure threshold
            recovery_timeout: Circuit breaker recovery timeout in seconds
        """
        self.execute_fn = execute_fn
        self.fallback_path = Path(fallback_path or settings.AUDIT_FALLBACK_PATH)

        # Ensure fallback directory exists
        try:
            self.fallback_path.parent.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            logger.warning(
                "Failed to create audit fallback directory",
                path=str(self.fallback_path.parent),
                error=str(e),
            )

        self.circuit_breaker = CircuitBreaker(
            CircuitBreakerConfig(
                failure_threshold=failure_threshold,
                window_seconds=60,
                reset_timeout=recovery_timeout,
                name="audit_logger",
            )
        )

    @must_stay_async("callers use await")
    async def log(
        self,
        tool_name: str,
        agent_id: str,
        caller_id: str,
        project_id: str,
        input_data: dict[str, Any],
        output_data: dict[str, Any],
        duration_ms: float,
        error: str | None = None,
    ) -> None:
        """
        Log audit event. Fails request if both DB and fallback fail (fail-closed).

        GOVERNANCE: This method MUST raise RuntimeError if audit cannot be recorded.
        This ensures that operations without audit trails are rejected.

        Args:
            tool_name: Name of the MCP tool invoked
            agent_id: ID of the agent (user_id)
            caller_id: Caller identity ("L" or "C")
            project_id: Project isolation ID
            input_data: Tool input arguments
            output_data: Tool output result
            duration_ms: Execution time in milliseconds
            error: Error message if operation failed

        Raises:
            RuntimeError: If audit cannot be recorded to either DB or fallback file
        """
        event = {
            "timestamp": datetime.now(UTC).isoformat(),
            "tool_name": tool_name,
            "agent_id": agent_id,
            "caller_id": caller_id,
            "project_id": project_id,
            "input_data": input_data,
            "output_data": output_data,
            "duration_ms": duration_ms,
            "error": error,
        }

        # Try DB first (with circuit breaker)
        if not self.circuit_breaker.is_open():
            try:
                await self.execute_fn(
                    """
                    INSERT INTO tool_audit_log (
                        tool_name, agent_id, caller, project_id,
                        input_data, output_data, duration_ms, error, timestamp
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, NOW())
                    """,
                    tool_name,
                    agent_id,
                    caller_id,
                    project_id,
                    json.dumps(input_data),
                    json.dumps(output_data),
                    duration_ms,
                    error,
                )
                self.circuit_breaker.record_success()
                return  # Success - audit recorded to DB
            except Exception as e:
                self.circuit_breaker.record_failure(str(e))
                logger.error(
                    "Audit DB write failed, attempting fallback",
                    error=str(e),
                    circuit_state=self.circuit_breaker.get_state(),
                )
        else:
            logger.warning(
                "Audit circuit breaker open, using fallback",
                circuit_state=self.circuit_breaker.get_state(),
            )

        # Fallback: Write to local JSONL file
        try:
            async with aiofiles.open(self.fallback_path, "a") as f:
                await f.write(json.dumps(event) + "\n")

            logger.warning(
                "Audit written to fallback file",
                path=str(self.fallback_path),
                tool_name=tool_name,
            )

            # Alert on fallback (important for monitoring)
            await self._alert_audit_fallback(event)
            return  # Success - audit recorded to file fallback

        except Exception as fallback_error:
            # FAIL-CLOSED: Both DB and fallback failed - reject operation
            logger.critical(
                "AUDIT FAILURE: Both DB and fallback failed - rejecting operation",
                db_circuit_state=self.circuit_breaker.get_state(),
                fallback_error=str(fallback_error),
                fallback_path=str(self.fallback_path),
                tool_name=tool_name,
            )
            raise RuntimeError(
                f"Audit logging required but unavailable. "
                f"DB circuit: {self.circuit_breaker.get_state()}, "
                f"Fallback error: {fallback_error}"
            ) from fallback_error

    @must_stay_async("callers use await")
    async def _alert_audit_fallback(self, event: dict[str, Any]) -> None:
        """
        Alert that audit is using fallback storage.

        This is a warning-level alert that should trigger monitoring.
        Future enhancement: Send to Slack webhook, email, or PagerDuty.
        """
        logger.warning(
            "ALERT: Audit using fallback storage",
            tool_name=event.get("tool_name"),
            caller_id=event.get("caller_id"),
            fallback_path=str(self.fallback_path),
        )
        # TODO: Implement Slack webhook or email alert
        # For now, just logging is sufficient for monitoring


# Singleton pattern for audit logger
_audit_logger: AuditLogger | None = None


def get_audit_logger(
    execute_fn: Callable[..., Awaitable[Any]] | None = None,
) -> AuditLogger:
    """
    Get or create audit logger singleton.

    Args:
        execute_fn: Async function to execute DB queries (required on first call)

    Returns:
        AuditLogger singleton instance

    Raises:
        RuntimeError: If called without execute_fn before initialization
    """
    global _audit_logger
    if _audit_logger is None:
        if execute_fn is None:
            raise RuntimeError(
                "AuditLogger not initialized - provide execute_fn on first call"
            )
        _audit_logger = AuditLogger(
            execute_fn=execute_fn,
            fallback_path=settings.AUDIT_FALLBACK_PATH,
            failure_threshold=settings.AUDIT_CIRCUIT_BREAKER_THRESHOLD,
            recovery_timeout=settings.AUDIT_CIRCUIT_BREAKER_TIMEOUT,
        )
    return _audit_logger


def reset_audit_logger() -> None:
    """Reset audit logger singleton (useful for testing)."""
    global _audit_logger
    _audit_logger = None


__all__ = ["AuditLogger", "get_audit_logger", "reset_audit_logger"]

# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "MCP-INTE-002",
    "governance_level": "medium",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": ["core.decorators", "core.observability.circuit_breaker"],
    "tags": [
        "async",
        "audit-tool",
        "event-driven",
        "filesystem",
        "integration",
        "logging",
        "mcp-integration",
        "messaging",
        "monitoring",
        "serialization",
    ],
    "keywords": [
        "audit",
        "breaker",
        "circuit",
        "fail",
        "fallback",
        "governance",
        "logger",
        "logging",
    ],
    "business_value": "AuditLogger: Main class for audit logging with circuit breaker Fail-closed semantics: Operations fail if audit cannot be recorded File fallback: When DB fails, logs to local JSONL file Alert mechanism",
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
