"""
L9 Core Governance - Approval Manager (Persistent)
===================================================

Manages approval of high-risk tasks that require Igor's explicit approval.
Now includes governance pattern creation for closed-loop learning.

ARCHITECTURE NOTE (GMP-104):
    This module provides PERSISTENT approval management via memory substrate.
    All approval decisions are stored as packets and queryable across sessions.

    For SESSION-BASED approval management (in-memory with checkpoints),
    see: core/governance/approval_manager.py

    Key differences:
    - This module: is_approved() queries memory substrate packets
    - approval_manager.py: uses in-memory _pending/_decisions dicts

    Both are valid — choose based on persistence requirements.

Version: 1.2.1 (GMP-104: Architecture documentation)
"""

from __future__ import annotations

# ============================================================================
__dora_meta__ = {
    "component_name": "Approval Manager",
    "module_version": "1.2.0 (Enhanced with high-risk tool detection)",
    "created_by": "Igor Beylin",
    "created_at": "2025-12-25T20:16:35Z",
    "updated_at": "2026-01-14T15:03:00Z",
    "layer": "foundation",
    "domain": "governance",
    "module_name": "approvals",
    "type": "service",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": ["Slack API"],
        "memory_layers": ["working_memory"],
        "imported_by": [
            "api.routes.commands",
            "core.agents.executor",
            "core.tools.registry_adapter",
            "tests.integration.test_closed_loop_learning",
            "tests.integration.test_l_bootstrap",
        ],
    },
}
# ============================================================================

from datetime import UTC, datetime
from typing import Any

import structlog

from core.schemas import PacketEnvelopeIn, PacketMetadata
from memory.governance_patterns import (
    DecisionType,
    GovernancePattern,
    extract_conditions_from_reason,
)

logger = structlog.get_logger(__name__)

# GMP-104: Tool risk classification loaded from config/policies/high_risk_tools.yaml
from core.governance.tool_risk_policy import (
    get_high_risk_tools_with_descriptions,
)

HIGH_RISK_TOOLS = get_high_risk_tools_with_descriptions()


class ApprovalManager:
    """Manages approval of high-risk tasks."""

    def __init__(
        self, substrate_service=None, slack_client=None, notification_channel=None
    ):
        """
        Initialize ApprovalManager.

        Args:
            substrate_service: Optional memory substrate service for storing approval records
            slack_client: Optional Slack client for notifications
            notification_channel: Slack channel for approval requests
        """
        self._substrate = substrate_service
        self._slack_client = slack_client
        self._notification_channel = notification_channel

        # Cache of permanent approvals (tool_id -> True)
        self._permanent_approvals: dict[str, bool] = {}

    def requires_approval(self, tool_id: str) -> bool:
        """
        Check if a tool requires Igor approval.

        Args:
            tool_id: Tool identifier

        Returns:
            True if tool requires approval
        """
        return tool_id in HIGH_RISK_TOOLS

    def get_high_risk_tools(self) -> list[str]:
        """Get list of high-risk tool IDs"""
        return list(HIGH_RISK_TOOLS.keys())

    async def request_approval(
        self,
        tool_id: str,
        task_id: str,
        agent_id: str,
        arguments: dict[str, Any],
        operation_summary: str | None = None,
    ) -> str:
        """
        Create an approval request for a high-risk operation.

        Args:
            tool_id: Tool being requested
            task_id: Task requesting the tool
            agent_id: Agent making the request
            arguments: Tool arguments
            operation_summary: Human-readable summary

        Returns:
            Request ID for tracking
        """
        from uuid import uuid4

        request_id = str(uuid4())

        if operation_summary is None:  # nosemgrep: l9-singleton-requires-lock
            operation_summary = HIGH_RISK_TOOLS.get(tool_id, f"Execute {tool_id}")

        # Store approval request
        await self._substrate.write_packet(
            packet_in=PacketEnvelopeIn(
                packet_type="approval_request",
                payload={
                    "request_id": request_id,
                    "tool_id": tool_id,
                    "task_id": task_id,
                    "agent_id": agent_id,
                    "operation_summary": operation_summary,
                    "arguments": arguments,
                    "status": "pending",
                    "created_at": datetime.now(UTC).isoformat(),
                },
                metadata=PacketMetadata(agent="approval_manager"),
            )
        )

        # Send Slack notification if available
        if self._slack_client and self._notification_channel:
            try:
                await self._notify_slack(request_id, tool_id, operation_summary)
            except Exception as e:
                logger.warning(f"Failed to send Slack notification: {e}")

        logger.info(
            "Approval request created",
            request_id=request_id,
            tool_id=tool_id,
            task_id=task_id,
        )

        return request_id

    async def _notify_slack(
        self,
        request_id: str,
        tool_id: str,
        operation_summary: str,
    ) -> None:
        """Send Slack notification for approval request"""
        if not self._slack_client:
            return

        message = (
            f"🔐 *Approval Required*\n"
            f"• Tool: `{tool_id}`\n"
            f"• Operation: {operation_summary}\n"
            f"• Request ID: `{request_id}`\n\n"
            f"Reply: `/approve {request_id}` or `/reject {request_id} [reason]`"
        )

        await self._slack_client.post_message(
            channel=self._notification_channel,
            text=message,
        )

    async def check_tool_approved(self, tool_id: str, task_id: str) -> bool:
        """
        Check if a tool execution is approved for a specific task.

        Args:
            tool_id: Tool identifier
            task_id: Task identifier

        Returns:
            True if approved (permanent or task-specific)
        """
        # Check permanent approvals first
        if tool_id in self._permanent_approvals:
            return True

        # Check for approved request for this task
        results = await self._substrate.search_packets_by_type(
            packet_type="approval_record",
            limit=100,
        )

        for result in results:
            payload = result.get("payload", {})
            if payload.get("task_id") == task_id:
                return True

        return False

    async def grant_permanent_approval(
        self, tool_id: str, approved_by: str = "Igor"
    ) -> bool:
        """
        Grant permanent approval for a tool (applies to all future calls).

        Args:
            tool_id: Tool to approve permanently
            approved_by: Who granted approval (must be Igor)

        Returns:
            True if granted
        """
        if approved_by != "Igor":
            logger.warning(f"Unauthorized permanent approval attempt by {approved_by}")
            return False

        self._permanent_approvals[tool_id] = True

        # Store permanently in memory
        await self._substrate.write_packet(
            packet_in=PacketEnvelopeIn(
                packet_type="permanent_approval",
                payload={
                    "tool_id": tool_id,
                    "approved_by": approved_by,
                    "timestamp": datetime.now(UTC).isoformat(),
                },
                metadata=PacketMetadata(agent="approval_manager"),
            )
        )

        logger.info(f"Permanent approval granted for tool {tool_id} by {approved_by}")
        return True

    async def approve_task(
        self,
        task_id: str,
        approved_by: str,
        reason: str | None = None,
        tool_name: str | None = None,
        task_type: str | None = None,
        context: dict[str, Any] | None = None,
    ) -> bool:
        """
        Approve a task. Only Igor can approve.

        Also creates a governance pattern for closed-loop learning.

        Args:
            task_id: Task identifier
            approved_by: Approver identifier (must be "Igor")
            reason: Optional approval reason
            tool_name: Tool being approved (for pattern creation)
            task_type: Type of task (for pattern creation)
            context: Additional context (files, summary, etc.)

        Returns:
            True if approved, False if unauthorized
        """
        if approved_by != "Igor":
            logger.warning(f"Unauthorized approval attempt by {approved_by}")
            return False

        # Write approval record
        await self._substrate.write_packet(
            packet_in=PacketEnvelopeIn(
                packet_type="approval_record",
                payload={
                    "task_id": task_id,
                    "approved_by": approved_by,
                    "timestamp": datetime.now(UTC).isoformat(),
                    "reason": reason or "",
                },
                metadata=PacketMetadata(agent="approval_manager"),
            )
        )

        # Create governance pattern for learning
        await self._write_governance_pattern(
            task_id=task_id,
            decision=DecisionType.APPROVED,
            reason=reason or "",
            tool_name=tool_name or "unknown",
            task_type=task_type or "general",
            context=context or {},
        )

        logger.info(f"Task {task_id} approved by Igor")
        return True

    async def reject_task(
        self,
        task_id: str,
        rejected_by: str,
        reason: str,
        tool_name: str | None = None,
        task_type: str | None = None,
        context: dict[str, Any] | None = None,
    ) -> bool:
        """
        Reject a task. Only Igor can reject.

        Also creates a governance pattern for closed-loop learning.

        Args:
            task_id: Task identifier
            rejected_by: Rejector identifier (must be "Igor")
            reason: Rejection reason (required)
            tool_name: Tool being rejected (for pattern creation)
            task_type: Type of task (for pattern creation)
            context: Additional context (files, summary, etc.)

        Returns:
            True if rejected, False if unauthorized
        """
        if rejected_by != "Igor":
            logger.warning(f"Unauthorized rejection attempt by {rejected_by}")
            return False

        # Write rejection record
        await self._substrate.write_packet(
            packet_in=PacketEnvelopeIn(
                packet_type="rejection_record",
                payload={
                    "task_id": task_id,
                    "rejected_by": rejected_by,
                    "timestamp": datetime.now(UTC).isoformat(),
                    "reason": reason,
                },
                metadata=PacketMetadata(agent="approval_manager"),
            )
        )

        # Create governance pattern for learning
        await self._write_governance_pattern(
            task_id=task_id,
            decision=DecisionType.REJECTED,
            reason=reason,
            tool_name=tool_name or "unknown",
            task_type=task_type or "general",
            context=context or {},
        )

        logger.info(f"Task {task_id} rejected by Igor")
        return True

    async def is_approved(self, task_id: str) -> bool:
        """
        Check if task is approved.

        Args:
            task_id: Task identifier

        Returns:
            True if approved, False otherwise
        """
        results = await self._substrate.search_packets_by_type(
            packet_type="approval_record",
            limit=100,
        )
        # Filter by task_id in payload
        for result in results:
            if result.get("payload", {}).get("task_id") == task_id:
                return True
        return False

    async def get_test_results_summary(self, task_id: str) -> dict[str, Any] | None:
        """
        Get test results summary for a task to include in approval decision.

        Args:
            task_id: Task identifier

        Returns:
            Dict with test summary or None if no results
        """
        try:
            results = await self._substrate.search_packets_by_type(
                packet_type="test_results",
                limit=10,
            )

            for result in results:
                if result.get("payload", {}).get("parent_task_id") == task_id:
                    payload = result["payload"]
                    return {
                        "tests_generated": payload.get("tests_generated", 0),
                        "tests_passed": payload.get("tests_passed", 0),
                        "tests_failed": payload.get("tests_failed", 0),
                        "coverage_percent": payload.get("coverage_percent"),
                        "recommendations": payload.get("recommendations", []),
                        "success": payload.get("success", False),
                    }

            return None

        except Exception as e:
            logger.warning(f"Failed to get test results for task {task_id}: {e}")
            return None

    def format_approval_request_with_tests(
        self,
        task_id: str,
        proposal_summary: str,
        test_summary: dict[str, Any] | None,
    ) -> str:
        """
        Format an approval request message including test results.

        Args:
            task_id: Task identifier
            proposal_summary: Summary of the proposal
            test_summary: Test results summary from get_test_results_summary

        Returns:
            Formatted approval request string
        """
        parts = [
            f"**APPROVAL REQUEST: {task_id[:8]}...**\n",
            f"**Proposal:** {proposal_summary}\n",
        ]

        if test_summary:
            parts.append("\n**Test Results:**")
            parts.append(f"- Tests Generated: {test_summary['tests_generated']}")
            parts.append(f"- Tests Passed: {test_summary['tests_passed']}")
            parts.append(f"- Tests Failed: {test_summary['tests_failed']}")

            if test_summary.get("coverage_percent") is not None:
                parts.append(f"- Coverage: {test_summary['coverage_percent']}%")

            if test_summary.get("recommendations"):
                parts.append("\n**Recommendations:**")
                for rec in test_summary["recommendations"][:3]:
                    parts.append(f"- {rec}")

            if test_summary["tests_failed"] > 0:
                parts.append("\n⚠️ **WARNING: Tests failed. Review before approving.**")
            elif test_summary["tests_generated"] == 0:
                parts.append("\n⚠️ **WARNING: No tests generated for this proposal.**")
        else:
            parts.append("\n*No test results available for this proposal.*")

        parts.append("\n\nReply with 'approve' or 'reject [reason]'")

        return "\n".join(parts)

    async def _write_governance_pattern(
        self,
        task_id: str,
        decision: DecisionType,
        reason: str,
        tool_name: str,
        task_type: str,
        context: dict[str, Any],
    ) -> None:
        """
        Write a governance pattern to memory for closed-loop learning.

        Args:
            task_id: Task identifier
            decision: Approved or rejected
            reason: Reason for decision
            tool_name: Tool involved
            task_type: Type of task
            context: Additional context
        """
        # Extract conditions from reason text
        conditions = extract_conditions_from_reason(reason)

        # Create pattern
        pattern = GovernancePattern(
            task_id=task_id,
            tool_name=tool_name,
            task_type=task_type,
            decision=decision,
            reason=reason,
            context=context,
            conditions=conditions,
        )

        # Write to governance_patterns segment
        try:
            await self._substrate.write_packet(
                packet_in=PacketEnvelopeIn(
                    packet_type="governance_pattern",
                    payload=pattern.to_packet_payload(),
                    metadata={
                        "segment": "governance_patterns",
                        "searchable": True,
                    },
                )
            )
            logger.info(
                f"Governance pattern created for task {task_id}",
                decision=decision.value,
                conditions=conditions,
            )
        except Exception as e:
            logger.warning(f"Failed to write governance pattern: {e}")


# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "COR-FOUN-085",
    "governance_level": "critical",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": ["core.schemas", "memory.governance_patterns"],
    "tags": [
        "async",
        "auth",
        "caching",
        "foundation",
        "governance",
        "logging",
        "messaging",
        "service",
        "testing",
    ],
    "keywords": [
        "approval",
        "approve",
        "approved",
        "check",
        "detection",
        "format",
        "governance",
        "grant",
    ],
    "business_value": "Implements ApprovalManager for approvals functionality",
    "last_modified": "2026-01-14T15:03:00Z",
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
