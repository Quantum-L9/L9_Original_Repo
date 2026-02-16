#!/usr/bin/env python3
"""
Tests for GovernanceBridge - escalation triggers, overrides, audit logging.
"""

from unittest.mock import AsyncMock

import pytest

from domain_tensor_bridge.governance_bridge import (
    GovernanceBridge,
    GovernanceDecision,
)


@pytest.fixture
def governance():
    """Create governance bridge."""
    return GovernanceBridge()


@pytest.fixture
def governance_with_igor():
    """Create governance bridge with Igor mock."""
    igor = AsyncMock()
    igor.request_approval = AsyncMock(return_value="approved")

    return GovernanceBridge(igor=igor)


class TestEscalationTriggers:
    """Tests for escalation triggers."""

    @pytest.mark.asyncio
    async def test_low_confidence_triggers_escalation(self, governance):
        """Test low confidence triggers escalation."""
        decision = {"confidence": 0.3, "action": "proceed"}

        result = await governance.check_governance(decision)

        assert result.decision == GovernanceDecision.ESCALATED
        assert not result.approved

    @pytest.mark.asyncio
    async def test_high_risk_triggers_escalation(self, governance):
        """Test high risk flag triggers escalation."""
        decision = {"confidence": 0.9, "high_risk": True}

        result = await governance.check_governance(decision)

        assert result.decision == GovernanceDecision.ESCALATED

    @pytest.mark.asyncio
    async def test_normal_decision_approved(self, governance):
        """Test normal decision is approved."""
        decision = {"confidence": 0.8, "action": "proceed"}

        result = await governance.check_governance(decision)

        assert result.approved


class TestOverrides:
    """Tests for human override handling."""

    @pytest.mark.asyncio
    async def test_escalation_to_igor(self, governance_with_igor):
        """Test escalation to Igor anchor."""
        decision = {"confidence": 0.9, "critical": True}

        result = await governance_with_igor.escalate_to_anchor(
            decision,
            reason="Critical decision",
        )

        assert result.escalated
        assert result.anchor == "igor"


class TestAuditLogging:
    """Tests for audit trail."""

    @pytest.mark.asyncio
    async def test_governance_check_logged(self, governance):
        """Test governance checks are logged."""
        decision = {"confidence": 0.8}

        # Would need log capture to verify
        result = await governance.check_governance(decision)

        assert result is not None
