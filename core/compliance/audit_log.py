"""
L9 Compliance - Audit Logger
============================

Logs Igor commands and high-risk operations to audit trail.

All audit entries are PacketEnvelopes stored in memory substrate
with kind="AUDIT" and immutable=True.

Version: 1.1.0 (GMP-11, GMP-21)

Audit Types:
- command: Igor command executions
- approval: Approval/rejection decisions
- tool_execution: Tool call audit
- memory_write: Memory substrate write operations
"""

from __future__ import annotations

# ============================================================================
__dora_meta__ = {
    "component_name": "Audit Logger",
    "module_version": "1.1.0 (GMP-11, GMP-21)",
    "created_by": "Igor Beylin",
    "created_at": "2026-01-02T15:15:57Z",
    "updated_at": "2026-01-17T23:47:56Z",
    "layer": "foundation",
    "domain": "core",
    "module_name": "audit_log",
    "type": "service",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": [],
        "memory_layers": ["working_memory"],
        "imported_by": [
            "api.routes.commands",
            "core.compliance.__init__",
            "memory.slack_ingest",
            "tests.integration.test_compliance_audit",
            "tests.integration.test_igor_commands",
        ],
    },
}
# ============================================================================

from datetime import datetime
from typing import Any, Optional

import structlog

logger = structlog.get_logger(__name__)


class AuditLogger:
    """
    Audit logger for Igor commands and high-risk operations.

    All audit entries are stored as immutable PacketEnvelopes
    in the memory substrate.
    """

    def __init__(self, substrate_service: Optional[Any] = None):
        """
        Initialize AuditLogger.

        Args:
            substrate_service: Memory substrate service for storing audit entries
        """
        self._substrate = substrate_service

    async def log_command(
        self,
        command_id: str,
        command_type: str,
        user_id: str,
        action: str,
        risk_level: str,
        raw_text: str,
        result: Optional[dict[str, Any]] = None,
        error: Optional[str] = None,
        timestamp: Optional[str] = None,
    ) -> bool:
        """
        Log a command execution to audit trail.

        Args:
            command_id: Unique command identifier
            command_type: Type of command (propose_gmp, analyze, etc.)
            user_id: User who issued the command
            action: Action being logged (start, complete, failed)
            risk_level: Risk level of the command
            raw_text: Original command text
            result: Optional result data
            error: Optional error message
            timestamp: Optional ISO timestamp (defaults to now)

        Returns:
            True if logged successfully, False otherwise
        """
        timestamp = timestamp or datetime.utcnow().isoformat()

        audit_entry = {
            "audit_type": "command",
            "command_id": command_id,
            "command_type": command_type,
            "user_id": user_id,
            "action": action,
            "risk_level": risk_level,
            "raw_text": raw_text,
            "result": result,
            "error": error,
            "timestamp": timestamp,
        }

        logger.info(
            "Audit log entry",
            command_id=command_id,
            command_type=command_type,
            action=action,
            user_id=user_id,
        )

        if self._substrate is None:
            logger.debug("No substrate service, audit entry logged to console only")
            return True

        try:
            from core.schemas import PacketEnvelopeIn

            packet = PacketEnvelopeIn(
                packet_type="audit_command",
                payload=audit_entry,
                metadata={
                    "immutable": True,
                    "retention_years": 7,
                    "source": "igor-command-interface",
                },
            )

            await self._substrate.write_packet(packet_in=packet)
            return True

        except Exception as e:
            logger.error("Failed to write audit entry to substrate", error=str(e))
            return False

    async def log_approval(
        self,
        task_id: str,
        approved_by: str,
        approved: bool,
        reason: Optional[str] = None,
        timestamp: Optional[str] = None,
    ) -> bool:
        """
        Log an approval decision to audit trail.

        Args:
            task_id: Task being approved/rejected
            approved_by: User who made the decision
            approved: Whether the task was approved
            reason: Optional reason for decision
            timestamp: Optional ISO timestamp

        Returns:
            True if logged successfully, False otherwise
        """
        timestamp = timestamp or datetime.utcnow().isoformat()

        audit_entry = {
            "audit_type": "approval",
            "task_id": task_id,
            "approved_by": approved_by,
            "approved": approved,
            "reason": reason,
            "timestamp": timestamp,
        }

        logger.info(
            "Audit approval entry",
            task_id=task_id,
            approved_by=approved_by,
            approved=approved,
        )

        if self._substrate is None:
            logger.debug("No substrate service, audit entry logged to console only")
            return True

        try:
            from core.schemas import PacketEnvelopeIn

            packet = PacketEnvelopeIn(
                packet_type="audit_approval",
                payload=audit_entry,
                metadata={
                    "immutable": True,
                    "retention_years": 7,
                    "source": "approval-manager",
                },
            )

            await self._substrate.write_packet(packet_in=packet)
            return True

        except Exception as e:
            logger.error("Failed to write approval audit to substrate", error=str(e))
            return False

    async def log_tool_execution(
        self,
        tool_name: str,
        agent_id: str,
        input_data: dict[str, Any],
        output_data: dict[str, Any],
        success: bool,
        approved_by: Optional[str] = None,
        approval_timestamp: Optional[str] = None,
        execution_timestamp: Optional[str] = None,
    ) -> bool:
        """
        Log a tool execution to audit trail.

        Args:
            tool_name: Name of tool executed
            agent_id: Agent that executed the tool
            input_data: Tool input parameters
            output_data: Tool output data
            success: Whether execution succeeded
            approved_by: Who approved the tool (if high-risk)
            approval_timestamp: When approval was granted
            execution_timestamp: When tool was executed

        Returns:
            True if logged successfully, False otherwise
        """
        execution_timestamp = execution_timestamp or datetime.utcnow().isoformat()

        audit_entry = {
            "audit_type": "tool_execution",
            "tool_name": tool_name,
            "agent_id": agent_id,
            "input": input_data,
            "output": output_data,
            "success": success,
            "approved_by": approved_by,
            "approval_timestamp": approval_timestamp,
            "execution_timestamp": execution_timestamp,
        }

        logger.info(
            "Audit tool execution",
            tool_name=tool_name,
            agent_id=agent_id,
            success=success,
        )

        if self._substrate is None:
            return True

        try:
            from core.schemas import PacketEnvelopeIn

            packet = PacketEnvelopeIn(
                packet_type="audit_tool",
                payload=audit_entry,
                metadata={
                    "immutable": True,
                    "retention_years": 7,
                    "source": "tool-executor",
                },
            )

            await self._substrate.write_packet(packet_in=packet)
            return True

        except Exception as e:
            logger.error("Failed to write tool audit to substrate", error=str(e))
            return False

    async def log_memory_write(
        self,
        agent_id: str,
        segment: str,
        content_type: str,
        size_bytes: int,
        packet_type: Optional[str] = None,
        thread_id: Optional[str] = None,
        timestamp: Optional[str] = None,
    ) -> bool:
        """
        Log a memory write to audit trail.

        Args:
            agent_id: Agent that performed the write
            segment: Memory segment written to
            content_type: Type of content written
            size_bytes: Size of content in bytes
            packet_type: Type of packet written
            thread_id: Thread ID if applicable
            timestamp: Optional ISO timestamp

        Returns:
            True if logged successfully, False otherwise
        """
        timestamp = timestamp or datetime.utcnow().isoformat()

        audit_entry = {
            "audit_type": "memory_write",
            "agent_id": agent_id,
            "segment": segment,
            "content_type": content_type,
            "size_bytes": size_bytes,
            "packet_type": packet_type,
            "thread_id": thread_id,
            "timestamp": timestamp,
        }

        logger.info(
            "Audit memory write",
            agent_id=agent_id,
            segment=segment,
            content_type=content_type,
            size_bytes=size_bytes,
        )

        if self._substrate is None:
            # GMP-68: Return False when substrate is None (audit was not logged)
            return False

        try:
            from core.schemas import PacketEnvelopeIn

            packet = PacketEnvelopeIn(
                packet_type="audit_memory_write",
                payload=audit_entry,
                metadata={
                    "immutable": True,
                    "retention_years": 7,
                    "source": "memory-substrate",
                },
            )

            await self._substrate.write_packet(packet_in=packet)
            return True

        except Exception as e:
            logger.error("Failed to write memory audit to substrate", error=str(e))
            return False


async def log_command_to_audit(
    substrate_service: Any,
    command_id: str,
    command_type: str,
    user_id: str,
    action: str,
    risk_level: str,
    raw_text: str,
    result: Optional[dict[str, Any]] = None,
    error: Optional[str] = None,
) -> bool:
    """
    Convenience function to log a command to audit trail.

    Args:
        substrate_service: Memory substrate service
        command_id: Unique command identifier
        command_type: Type of command
        user_id: User who issued the command
        action: Action being logged
        risk_level: Risk level of the command
        raw_text: Original command text
        result: Optional result data
        error: Optional error message

    Returns:
        True if logged successfully, False otherwise
    """
    audit_logger = AuditLogger(substrate_service)
    return await audit_logger.log_command(
        command_id=command_id,
        command_type=command_type,
        user_id=user_id,
        action=action,
        risk_level=risk_level,
        raw_text=raw_text,
        result=result,
        error=error,
    )


__all__ = [
    "AuditLogger",
    "log_command_to_audit",
]

# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "COR-FOUN-066",
    "governance_level": "critical",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": ["core.schemas"],
    "tags": [
        "async",
        "audit-tool",
        "core",
        "debugging",
        "foundation",
        "logging",
        "messaging",
        "service",
    ],
    "keywords": [
        "approval",
        "audit",
        "command",
        "compliance",
        "execution",
        "igor",
        "log",
        "logger",
    ],
    "business_value": "Implements AuditLogger for audit log functionality",
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
