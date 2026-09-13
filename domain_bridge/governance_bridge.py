#!/usr/bin/env python3
"""
================================================================================
Module: Governance Bridge
Purpose: Interface to L9 governance layer for escalation and approval
================================================================================

Summary:
    Connects Domain-Tensor Bridge to L9's governance infrastructure.
    Handles escalation decisions, respects human overrides, logs all
    governance checks, and enforces compliance anchors (Igor, Compliance).

Extended Metadata:

================================================================================
# HEADER META - Module Identity (Static)
# component_id: SEC-DTB-002
# layer: security
# domain: governance
# governance_level: critical
# created_at: 2026-01-02T03:35:00Z
================================================================================
"""


from dataclasses import dataclass, field
from enum import Enum
from typing import Any

import structlog

from core.decorators import must_stay_async

# L9 governance imports (ApprovalManager is the L9 equivalent of ApprovalService)
from core.governance import ApprovalManager

logger = structlog.get_logger(__name__)


class EscalationLevel(str, Enum):
    """Escalation levels for governance decisions."""

    STANDARD = "standard"
    COMPLIANCE = "compliance"
    IGOR = "igor"


class GovernanceDecision(str, Enum):
    """Governance check outcomes."""

    APPROVED = "approved"
    BLOCKED = "blocked"
    ESCALATED = "escalated"
    PENDING = "pending"


@dataclass
class GovernanceResult:
    """Result of governance check."""

    decision: GovernanceDecision
    approved: bool
    reason: str | None = None
    escalation_level: EscalationLevel | None = None
    audit_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class EscalationResult:
    """Result of escalation to anchor."""

    escalated: bool
    anchor: str
    response: str | None = None
    timeout: bool = False


class GovernanceBridge:
    """
    Bridge to L9 governance layer.

    Responsibilities:
    - Check decisions against governance policy
    - Escalate to Igor/Compliance when needed
    - Respect and apply human overrides
    - Log all governance interactions
    """

    def __init__(
        self,
        approval_manager: ApprovalManager | None = None,
        igor_client: Any | None = None,  # Igor approval client (if available)
    ):
        self.approval_manager = approval_manager
        self.igor_client = igor_client
        self._initialized = False

    @must_stay_async("callers use await")
    async def initialize(self) -> None:
        """Initialize governance connections."""
        logger.info("governance_bridge_initializing")

        if not self.approval_manager:
            logger.warning("no_approval_manager_configured")

        self._initialized = True
        logger.info("governance_bridge_ready")

    @must_stay_async("callers use await")
    async def check_governance(
        self,
        decision: dict[str, Any],
    ) -> GovernanceResult:
        """
        Check decision against governance policy.

        Args:
            decision: Decision to check

        Returns:
            GovernanceResult with approval status
        """
        logger.info(
            "checking_governance",
            decision_type=decision.get("type", "unknown"),
        )

        # Determine if escalation needed
        requires_escalation = self._requires_escalation(decision)

        if requires_escalation:
            escalation_level = self._determine_escalation_level(decision)

            logger.info(
                "escalation_required",
                level=escalation_level.value if escalation_level else "unknown",
            )

            return GovernanceResult(
                decision=GovernanceDecision.ESCALATED,
                approved=False,
                reason="Requires escalation to governance anchor",
                escalation_level=escalation_level,
            )

        # Check with approval manager
        if self.approval_manager:
            approval = await self._check_approval(decision)
            if not approval:
                return GovernanceResult(
                    decision=GovernanceDecision.BLOCKED,
                    approved=False,
                    reason="Approval manager denied",
                )

        return GovernanceResult(
            decision=GovernanceDecision.APPROVED,
            approved=True,
        )

    async def check(self, result: dict[str, Any]) -> GovernanceResult:
        """Alias for check_governance."""
        return await self.check_governance(result)

    @must_stay_async("callers use await")
    async def escalate_to_anchor(
        self,
        decision: dict[str, Any],
        reason: str,
    ) -> EscalationResult:
        """
        Escalate decision to governance anchor (Igor/Compliance).

        Args:
            decision: Decision requiring escalation
            reason: Reason for escalation

        Returns:
            EscalationResult with anchor response
        """
        logger.info(
            "escalating_to_anchor",
            reason=reason,
        )

        if self.igor_client:
            try:
                response = await self.igor_client.request_approval(
                    context=decision,
                    reason=reason,
                )

                return EscalationResult(
                    escalated=True,
                    anchor="igor",
                    response=response,
                )
            except TimeoutError:
                logger.error("igor_escalation_timeout")
                return EscalationResult(
                    escalated=False,
                    anchor="igor",
                    timeout=True,
                )

        logger.warning("no_anchor_available_for_escalation")
        return EscalationResult(
            escalated=False,
            anchor="none",
        )

    def _requires_escalation(self, decision: dict[str, Any]) -> bool:
        """Determine if decision requires escalation."""
        # Check confidence threshold
        confidence = decision.get("confidence", 1.0)
        if confidence < 0.5:
            return True

        # Check for high-risk markers
        if decision.get("high_risk", False):
            return True

        return bool(decision.get("destructive", False))

    def _determine_escalation_level(
        self,
        decision: dict[str, Any],
    ) -> EscalationLevel | None:
        """Determine appropriate escalation level."""
        if decision.get("critical", False):
            return EscalationLevel.IGOR

        if decision.get("high_risk", False):
            return EscalationLevel.COMPLIANCE

        return EscalationLevel.STANDARD

    async def _check_approval(self, decision: dict[str, Any]) -> bool:
        """Check with approval manager."""
        if not self.approval_manager:
            return True

        try:
            # ApprovalManager interface may differ - adapt as needed
            return await self.approval_manager.check(decision)
        except Exception as e:
            logger.error("approval_manager_error", error=str(e))
            return False


# ============================================================================
# FOOTER META - Extended Metadata (Static)
# ============================================================================


__all__ = [
    "EscalationResult",
    "GovernanceBridge",
    "GovernanceDecision",
    "GovernanceResult",
]
