"""
Approval Manager (Session-Based)

High-risk tool execution requires explicit Igor approval before dispatch.
This module manages the approval workflow for destructive operations.

ARCHITECTURE NOTE (GMP-104):
    This module provides SESSION-BASED approval management with in-memory caches.
    Approvals are tracked in _pending/_decisions dicts with optional checkpointing.

    For PERSISTENT approval management (stored in memory substrate),
    see: core/governance/approvals.py

    Key differences:
    - This module: uses in-memory _pending/_decisions with ApprovalStatus/ApprovalDecision
    - approvals.py: is_approved() queries memory substrate packets

    Both are valid — choose based on persistence requirements:
    - Use this for: FastAPI request-scoped approvals, Cursor executor
    - Use approvals.py for: Long-running tasks, audit trail, closed-loop learning
"""

from __future__ import annotations

# ============================================================================
__dora_meta__ = {
    "component_name": "Approval Manager",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2026-01-06T15:07:54Z",
    "updated_at": "2026-01-17T23:47:56Z",
    "layer": "foundation",
    "domain": "data_models",
    "module_name": "approval_manager",
    "type": "dataclass",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": ["Slack API"],
        "memory_layers": ["working_memory"],
        "imported_by": [
            "agents.cursor.integrations.cursor_executor",
            "api.server",
            "core.governance.approval_gate",
            "tests.integration.test_cursor_langgraph_integration",
        ],
    },
}
# ============================================================================

from dataclasses import dataclass, field
from datetime import timezone, datetime, timedelta
from enum import Enum
from typing import TYPE_CHECKING, Any
from uuid import uuid4

import structlog

if TYPE_CHECKING:
    from memory.substrate_service import MemorySubstrateService

from core.decorators import must_stay_async
from core.governance.tool_risk_policy import get_high_risk_tools_with_descriptions

logger = structlog.get_logger(__name__)


class ApprovalStatus(Enum):
    """Approval request status"""

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"


@dataclass
class ApprovalRequest:
    """Request for Igor approval of high-risk operation"""

    request_id: str
    tool_id: str
    agent_id: str
    task_id: str
    operation_summary: str
    risk_level: str
    arguments: dict[str, Any]
    created_at: datetime = field(default_factory=datetime.utcnow)
    expires_at: datetime | None = None
    status: ApprovalStatus = ApprovalStatus.PENDING

    def __post_init__(self):
        if self.expires_at is None:
            # Default 1 hour expiration
            self.expires_at = self.created_at + timedelta(hours=1)

    def is_expired(self) -> bool:
        return datetime.now(timezone.utc) > self.expires_at


@dataclass
class ApprovalDecision:
    """Decision on an approval request"""

    request_id: str
    status: ApprovalStatus
    approved_by: str | None = None
    approved_at: datetime | None = None
    rejection_reason: str | None = None
    scope: str = "single"  # single, session, permanent

    @property
    def is_approved(self) -> bool:
        return self.status == ApprovalStatus.APPROVED


class ApprovalManager:
    """
    Manages Igor approval workflow for high-risk tool executions.

    Flow:
    1. Executor detects tool requires approval
    2. ApprovalManager.request_approval() creates pending request
    3. Request stored in memory + optional Slack notification
    4. Igor approves/rejects via API or Slack
    5. Executor checks approval before dispatch
    """

    # GMP-104: Tool risk classification loaded from config/policies/high_risk_tools.yaml
    HIGH_RISK_TOOLS = get_high_risk_tools_with_descriptions()

    def __init__(
        self,
        substrate_service: MemorySubstrateService | None = None,
        slack_client: Any | None = None,
        notification_channel: str | None = None,
    ):
        self.substrate = substrate_service
        self.slack_client = slack_client
        self.notification_channel = notification_channel

        # In-memory cache of pending approvals (for fast lookup)
        self._pending: dict[str, ApprovalRequest] = {}
        self._decisions: dict[str, ApprovalDecision] = {}

        # Cache of permanent approvals (tool_id -> approval)
        self._permanent_approvals: dict[str, ApprovalDecision] = {}

    def requires_approval(self, tool_id: str) -> bool:
        """Check if tool requires Igor approval"""
        return tool_id in self.HIGH_RISK_TOOLS

    async def request_approval(
        self,
        tool_id: str,
        agent_id: str,
        task_id: str,
        arguments: dict[str, Any],
        operation_summary: str | None = None,
    ) -> ApprovalRequest:
        """
        Create approval request for high-risk operation.

        Returns:
            ApprovalRequest with PENDING status
        """
        request_id = str(uuid4())

        if operation_summary is None:
            operation_summary = self.HIGH_RISK_TOOLS.get(tool_id, f"Execute {tool_id}")

        request = ApprovalRequest(
            request_id=request_id,
            tool_id=tool_id,
            agent_id=agent_id,
            task_id=task_id,
            operation_summary=operation_summary,
            risk_level="high",
            arguments=arguments,
        )

        # Store in cache
        self._pending[request_id] = request

        # Persist to memory substrate if available
        if self.substrate and hasattr(self.substrate, "write_packet"):
            try:
                from core.schemas import PacketEnvelope

                packet = PacketEnvelope(
                    packet_type="memory_write",
                    payload={
                        "chunk_type": "approval_request",
                        "request_id": request_id,
                        "tool_id": tool_id,
                        "task_id": task_id,
                        "operation_summary": operation_summary,
                        "status": "pending",
                        "created_at": request.created_at.isoformat(),
                        "expires_at": request.expires_at.isoformat(),
                    },
                    metadata={"agent": agent_id},
                )
                await self.substrate.write_packet(packet)
            except Exception as e:
                logger.warning("Failed to persist approval request", error=str(e))

        # Send Slack notification if available
        if self.slack_client and self.notification_channel:
            try:
                await self._notify_slack(request)
            except Exception as e:
                logger.warning("Failed to send Slack notification", error=str(e))

        logger.info(
            "Approval request created",
            request_id=request_id,
            tool_id=tool_id,
            agent_id=agent_id,
        )

        return request

    @must_stay_async("callers use await")
    async def check_approval(
        self,
        request_id: str,
    ) -> ApprovalDecision | None:
        """
        Check if approval request has been decided.

        Returns:
            ApprovalDecision if decided, None if still pending
        """
        # Check cache first
        if request_id in self._decisions:
            return self._decisions[request_id]

        # Check if request exists
        request = self._pending.get(request_id)
        if not request:
            return None

        # Check if expired
        if request.is_expired():
            decision = ApprovalDecision(
                request_id=request_id,
                status=ApprovalStatus.EXPIRED,
            )
            self._decisions[request_id] = decision
            del self._pending[request_id]
            return decision

        return None  # Still pending

    @must_stay_async("callers use await")
    async def check_tool_approved(
        self,
        tool_id: str,
        task_id: str,
    ) -> ApprovalDecision | None:
        """
        Check if a tool execution is approved for a task.

        Checks:
        1. Permanent approvals for this tool
        2. Pending requests for this task

        Returns:
            ApprovalDecision if approved, None if needs approval
        """
        # Check permanent approvals
        if tool_id in self._permanent_approvals:
            return self._permanent_approvals[tool_id]

        # Check for approved request for this task
        for req_id, request in list(self._pending.items()):
            if request.tool_id == tool_id and request.task_id == task_id:
                decision = self._decisions.get(req_id)
                if decision and decision.is_approved:
                    return decision

        return None

    async def approve(
        self,
        request_id: str,
        approved_by: str = "igor",
        scope: str = "single",
    ) -> ApprovalDecision:
        """
        Approve a pending request.

        Args:
            request_id: Request to approve
            approved_by: Who approved (default: igor)
            scope: Approval scope (single, session, permanent)

        Returns:
            ApprovalDecision with APPROVED status
        """
        request = self._pending.get(request_id)
        if not request:
            raise ValueError(f"Request not found: {request_id}")

        if request.is_expired():
            raise ValueError(f"Request expired: {request_id}")

        decision = ApprovalDecision(
            request_id=request_id,
            status=ApprovalStatus.APPROVED,
            approved_by=approved_by,
            approved_at=datetime.now(timezone.utc),
            scope=scope,
        )

        self._decisions[request_id] = decision

        # Handle permanent approval
        if scope == "permanent":
            self._permanent_approvals[request.tool_id] = decision

        # Remove from pending
        del self._pending[request_id]

        logger.info(
            "Approval granted",
            request_id=request_id,
            tool_id=request.tool_id,
            approved_by=approved_by,
            scope=scope,
        )

        # Create checkpoint after approval (per memory_spec_v3.0.yaml on_critical_decision)
        await self._create_approval_checkpoint(
            request=request,
            decision=decision,
        )

        return decision

    async def _create_approval_checkpoint(
        self,
        request: ApprovalRequest,
        decision: ApprovalDecision,
    ) -> None:
        """
        Create a checkpoint after a critical approval decision.

        Per memory_spec_v3.0.yaml checkpoint trigger: on_critical_decision.
        This captures the system state after high-risk tool approvals for recovery.

        Args:
            request: The approval request that was approved
            decision: The approval decision
        """
        if self.substrate is None:
            logger.debug("No substrate service - skipping approval checkpoint")
            return

        try:
            # Get agent persistence service
            persistence = self.substrate.get_agent_persistence()
            if persistence is None:
                logger.debug("No persistence service - skipping approval checkpoint")
                return

            # Determine agent_id from request context or use default
            agent_id = (
                request.context.get("agent_id", "governance")
                if request.context
                else "governance"
            )

            state = {
                "request_id": str(request.request_id),
                "tool_id": request.tool_id,
                "approved_by": decision.approved_by,
                "approved_at": (
                    decision.approved_at.isoformat() if decision.approved_at else None
                ),
                "scope": decision.scope,
                "context": request.context,
            }

            checkpoint_id = await persistence.create_checkpoint(
                agent_id=agent_id,
                state=state,
                reason="on_approval",
            )

            logger.debug(
                "Approval checkpoint created",
                checkpoint_id=str(checkpoint_id),
                request_id=str(request.request_id),
                tool_id=request.tool_id,
            )

        except Exception as e:
            # Best-effort: don't fail approval due to checkpoint failure
            logger.warning(
                "Failed to create approval checkpoint",
                request_id=str(request.request_id),
                error=str(e),
            )

    @must_stay_async("callers use await")
    async def reject(
        self,
        request_id: str,
        rejected_by: str = "igor",
        reason: str | None = None,
    ) -> ApprovalDecision:
        """
        Reject a pending request.
        """
        request = self._pending.get(request_id)
        if not request:
            raise ValueError(f"Request not found: {request_id}")

        decision = ApprovalDecision(
            request_id=request_id,
            status=ApprovalStatus.REJECTED,
            approved_by=rejected_by,
            approved_at=datetime.now(timezone.utc),
            rejection_reason=reason,
        )

        self._decisions[request_id] = decision
        del self._pending[request_id]

        logger.info(
            "Approval rejected",
            request_id=request_id,
            tool_id=request.tool_id,
            reason=reason,
        )

        return decision

    async def _notify_slack(self, request: ApprovalRequest) -> None:
        """Send Slack notification for approval request"""
        if not self.slack_client:
            return

        message = (
            f"🔐 *Approval Required*\n"
            f"• Tool: `{request.tool_id}`\n"
            f"• Agent: `{request.agent_id}`\n"
            f"• Operation: {request.operation_summary}\n"
            f"• Request ID: `{request.request_id}`\n"
            f"• Expires: {request.expires_at.isoformat()}\n\n"
            f"Reply with `/approve {request.request_id}` or `/reject {request.request_id}`"
        )

        await self.slack_client.post_message(
            channel=self.notification_channel,
            text=message,
        )

    def get_pending_requests(self) -> list[ApprovalRequest]:
        """Get all pending approval requests"""
        # Clean up expired requests
        datetime.now(timezone.utc)
        expired = [req_id for req_id, req in self._pending.items() if req.is_expired()]
        for req_id in expired:
            del self._pending[req_id]

        return list(self._pending.values())

    def get_metrics(self) -> dict:
        """Get approval manager metrics"""
        return {
            "pending_count": len(self._pending),
            "decided_count": len(self._decisions),
            "permanent_approvals": len(self._permanent_approvals),
            "high_risk_tools": list(self.HIGH_RISK_TOOLS.keys()),
        }


# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "COR-FOUN-087",
    "governance_level": "critical",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": ["core.decorators", "core.schemas", "memory.substrate_service"],
    "tags": [
        "api",
        "async",
        "caching",
        "data-models",
        "dataclass",
        "debugging",
        "foundation",
        "logging",
        "messaging",
        "metrics",
    ],
    "keywords": [
        "approval",
        "approve",
        "approved",
        "check",
        "decision",
        "expired",
        "manager",
        "metrics",
    ],
    "business_value": "This module manages the approval workflow for destructive operations.",
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
