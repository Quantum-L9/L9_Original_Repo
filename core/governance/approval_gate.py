"""
L9 Cursor Approval Gate
Version: 1.0.0

Cursor-specific governance gate to determine which decisions need Igor approval
and to process responses.

Uses existing ApprovalManager infrastructure.
"""

from __future__ import annotations

# ============================================================================
__dora_meta__ = {
    "component_name": "Approval Gate",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2026-01-11T18:13:39Z",
    "updated_at": "2026-01-14T15:03:00Z",
    "layer": "foundation",
    "domain": "governance",
    "module_name": "approval_gate",
    "type": "dataclass",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": [],
        "memory_layers": ["working_memory"],
        "imported_by": ["tests.integration.test_cursor_langgraph_integration"],
    },
}
# ============================================================================

from dataclasses import dataclass
from datetime import UTC
from typing import Any

import structlog

from core.governance.approval_manager import ApprovalManager, ApprovalStatus
from core.schemas import PacketEnvelope
from core.schemas.capabilities import Capability, ToolName

logger = structlog.get_logger(__name__)


# =============================================================================
# Models
# =============================================================================


@dataclass
class EscalationResult:
    """Result of escalation to Igor."""

    approval_status: ApprovalStatus
    request_id: str | None = None
    rationale: str | None = None
    overrides: dict[str, Any] | None = None
    constraints: dict[str, Any] | None = None


# =============================================================================
# Approval Gate Functions
# =============================================================================


def is_high_impact_decision(decision: dict[str, Any]) -> bool:
    """
    Determine if a decision requires Igor approval.

    Heuristics:
    - Decision type (file mutation, git commit, high-risk tool)
    - Module/file impact (memory substrate, governance, external adapters)
    - Confidence or risk classification
    - Tag patterns (high_risk, production, secrets)

    Args:
        decision: Decision dict from CursorAgentState.decisions[-1]

    Returns:
        True if decision requires approval
    """
    # Check governance bypass flag
    try:
        from config.settings import settings

        if getattr(settings, "l_cto_governance_bypass", False):
            logger.warning(
                "approval_gate.governance_bypass_active",
                decision_type=decision.get("type"),
                reason="L_CTO_GOVERNANCE_BYPASS=true - all decisions auto-approved",
            )
            return False  # No approval needed when bypass is active
    except ImportError:
        pass

    # Check decision type
    decision_type = decision.get("type", "")

    # High-risk decision types
    high_risk_types = {
        "file_mutation",
        "git_commit",
        "git_push",
        "database_write",
        "deploy",
        "tool_execution",
    }

    if decision_type in high_risk_types:
        return True

    # Check tool name if present
    tool_name = decision.get("tool_name")
    if tool_name:
        try:
            tool_enum = ToolName(tool_name)
            # Check if tool requires approval via Capability
            capability = Capability(tool=tool_enum, scope="requires_igor_approval")
            if capability.requires_igor_approval():
                return True
        except (ValueError, AttributeError):
            pass

    # Check file impact
    affected_files = decision.get("affected_files", [])
    critical_modules = {
        "memory/substrate",
        "core/governance",
        "core/agents/executor",
        "runtime/websocket",
        "docker-compose",
    }

    for file_path in affected_files:
        for module in critical_modules:
            if module in file_path:
                return True

    # Check tags
    tags = decision.get("tags", [])
    high_risk_tags = {"high_risk", "production", "secrets", "irreversible"}
    if any(tag in tags for tag in high_risk_tags):
        return True

    # Check confidence (low confidence = higher risk)
    confidence = decision.get("confidence", 1.0)
    return confidence < 0.7


async def escalate_to_igor(
    decision_packet: PacketEnvelope | None,
    approval_manager: ApprovalManager,
    agent_id: str = "cursor",
    task_id: str | None = None,
) -> EscalationResult:
    """
    Escalate decision to Igor via ApprovalManager.

    Args:
        decision_packet: PacketEnvelope containing decision (optional)
        approval_manager: ApprovalManager instance
        agent_id: Agent identifier
        task_id: Task identifier

    Returns:
        EscalationResult with approval status and metadata
    """
    logger.info("Escalating decision to Igor", agent_id=agent_id, task_id=task_id)

    # Extract tool_id and arguments from decision packet
    tool_id = "cursor_decision"  # Default
    arguments = {}
    operation_summary = "Cursor decision requires approval"

    if decision_packet:
        payload = decision_packet.payload if hasattr(decision_packet, "payload") else {}
        tool_id = payload.get("tool_name", "cursor_decision")
        arguments = payload.get("arguments", {})
        operation_summary = payload.get("operation_summary", operation_summary)

    # Create approval request
    try:
        request = await approval_manager.request_approval(
            tool_id=tool_id,
            agent_id=agent_id,
            task_id=task_id or "unknown",
            arguments=arguments,
            operation_summary=operation_summary,
        )

        return EscalationResult(
            approval_status=ApprovalStatus.PENDING,
            request_id=request.request_id,
            rationale="Decision escalated to Igor for approval",
        )
    except Exception as e:
        logger.error("Failed to escalate to Igor", error=str(e))
        return EscalationResult(
            approval_status=ApprovalStatus.REJECTED,
            rationale=f"Escalation failed: {e!s}",
        )


def handle_governance_result(
    escalation_result: EscalationResult,
    state: Any,  # CursorAgentState
) -> Any:  # CursorAgentState
    """
    Handle governance result and update state.

    Args:
        escalation_result: Result from escalate_to_igor()
        state: CursorAgentState to update

    Returns:
        Updated CursorAgentState
    """
    logger.info(
        "Handling governance result",
        status=escalation_result.approval_status.value,
        request_id=escalation_result.request_id,
    )

    # Update approval status
    approval_status = escalation_result.approval_status.value

    if escalation_result.approval_status == ApprovalStatus.APPROVED:
        # Mark decision as approved
        if state.decisions:
            state.decisions[-1]["approval_status"] = "approved"
            state.decisions[-1]["approval_id"] = escalation_result.request_id

        # Add reasoning block
        from datetime import datetime
        from uuid import uuid4

        from core.schemas import StructuredReasoningBlock

        reasoning_block = StructuredReasoningBlock(
            step_id=str(uuid4()),
            timestamp=datetime.now(UTC),
            reasoning_type="governance",
            content=f"Decision approved by Igor: {escalation_result.rationale}",
            confidence=0.9,
        )

        return state.model_copy(
            update={
                "approval_status": "approved",
                "approval_id": escalation_result.request_id,
                "reasoning_trace": [*state.reasoning_trace, reasoning_block],
            }
        )

    if escalation_result.approval_status == ApprovalStatus.REJECTED:
        # Mark decision as rejected
        if state.decisions:
            state.decisions[-1]["approval_status"] = "rejected"
            state.decisions[-1]["rejection_reason"] = escalation_result.rationale

        # Add guidance message
        from datetime import datetime
        from uuid import uuid4

        from core.schemas import StructuredReasoningBlock

        reasoning_block = StructuredReasoningBlock(
            step_id=str(uuid4()),
            timestamp=datetime.now(UTC),
            reasoning_type="governance",
            content=f"Decision rejected: {escalation_result.rationale}",
            confidence=0.9,
        )

        return state.model_copy(
            update={
                "approval_status": "rejected",
                "reasoning_trace": [*state.reasoning_trace, reasoning_block],
            }
        )

    # PENDING or EXPIRED - keep current state, just update status
    return state.model_copy(
        update={
            "approval_status": approval_status,
            "approval_id": escalation_result.request_id,
        }
    )


# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "COR-FOUN-086",
    "governance_level": "critical",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [
        "core.governance.approval_manager",
        "core.schemas",
        "core.schemas.capabilities",
    ],
    "tags": [
        "async",
        "dataclass",
        "foundation",
        "governance",
        "logging",
        "messaging",
        "realtime",
        "security",
        "tracing",
    ],
    "keywords": [
        "approval",
        "cursor",
        "decision",
        "escalate",
        "escalation",
        "gate",
        "governance",
        "handle",
    ],
    "business_value": "Implements EscalationResult for approval gate functionality",
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
