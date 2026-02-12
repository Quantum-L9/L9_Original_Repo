"""
Unit tests for Policy Conflict Resolution Engine.

Tests:
- Priority-based resolution
- CRITICAL policy override
- Conflict detection at same priority
- Escalation logic
"""

import pytest

from core.governance.policy_engine import PolicyConflictResolver
from core.governance.policy_models import (
    GovernanceDecision,
    PolicyDecision,
    PolicyPriority,
    PolicyResult,
)


def test_single_policy_allow():
    """Test single ALLOW policy."""
    results = [
        PolicyResult(
            decision=PolicyDecision.ALLOW,
            priority=PolicyPriority.HIGH,
            reason="User authorized",
            policy_name="AuthPolicy",
        )
    ]

    decision = PolicyConflictResolver.resolve(results)

    assert decision.final_decision == PolicyDecision.ALLOW
    assert decision.has_conflict is False
    assert len(decision.policy_results) == 1


def test_single_policy_deny():
    """Test single DENY policy."""
    results = [
        PolicyResult(
            decision=PolicyDecision.DENY,
            priority=PolicyPriority.MEDIUM,
            reason="Insufficient permissions",
            policy_name="PermissionPolicy",
        )
    ]

    decision = PolicyConflictResolver.resolve(results)

    assert decision.final_decision == PolicyDecision.DENY
    assert decision.has_conflict is False


def test_critical_deny_overrides_all():
    """Test CRITICAL DENY always wins."""
    results = [
        PolicyResult(
            decision=PolicyDecision.ALLOW,
            priority=PolicyPriority.HIGH,
            reason="Role permitted",
            policy_name="RolePolicy",
        ),
        PolicyResult(
            decision=PolicyDecision.DENY,
            priority=PolicyPriority.CRITICAL,
            reason="Security violation detected",
            policy_name="SecurityPolicy",
        ),
        PolicyResult(
            decision=PolicyDecision.ALLOW,
            priority=PolicyPriority.MEDIUM,
            reason="Department approved",
            policy_name="DepartmentPolicy",
        ),
    ]

    decision = PolicyConflictResolver.resolve(results)

    assert decision.final_decision == PolicyDecision.DENY
    assert decision.has_conflict is False
    assert "SecurityPolicy" in decision.conflict_reason


def test_highest_priority_wins():
    """Test highest priority policy wins when no conflicts."""
    results = [
        PolicyResult(
            decision=PolicyDecision.DENY,
            priority=PolicyPriority.LOW,
            reason="Time restriction",
            policy_name="TimePolicy",
        ),
        PolicyResult(
            decision=PolicyDecision.ALLOW,
            priority=PolicyPriority.HIGH,
            reason="Admin override",
            policy_name="AdminPolicy",
        ),
    ]

    decision = PolicyConflictResolver.resolve(results)

    # HIGH priority ALLOW should override LOW priority DENY
    assert decision.final_decision == PolicyDecision.ALLOW
    assert decision.has_conflict is False


def test_conflict_at_same_priority():
    """Test conflict detection when same priority policies disagree."""
    results = [
        PolicyResult(
            decision=PolicyDecision.ALLOW,
            priority=PolicyPriority.HIGH,
            reason="Policy A allows",
            policy_name="PolicyA",
        ),
        PolicyResult(
            decision=PolicyDecision.DENY,
            priority=PolicyPriority.HIGH,
            reason="Policy B denies",
            policy_name="PolicyB",
        ),
    ]

    decision = PolicyConflictResolver.resolve(results)

    assert decision.final_decision == PolicyDecision.REQUIRE_ESCALATION
    assert decision.has_conflict is True
    assert "PolicyA" in decision.conflict_reason
    assert "PolicyB" in decision.conflict_reason


def test_multiple_same_priority_no_conflict():
    """Test multiple policies at same priority with same decision."""
    results = [
        PolicyResult(
            decision=PolicyDecision.ALLOW,
            priority=PolicyPriority.MEDIUM,
            reason="Reason A",
            policy_name="PolicyA",
        ),
        PolicyResult(
            decision=PolicyDecision.ALLOW,
            priority=PolicyPriority.MEDIUM,
            reason="Reason B",
            policy_name="PolicyB",
        ),
    ]

    decision = PolicyConflictResolver.resolve(results)

    # Same decision, no conflict
    assert decision.final_decision == PolicyDecision.ALLOW
    assert decision.has_conflict is False


def test_empty_policy_results():
    """Test behavior with no policy results."""
    results = []

    decision = PolicyConflictResolver.resolve(results)

    assert decision.final_decision == PolicyDecision.REQUIRE_ESCALATION
    assert "No policies evaluated" in decision.conflict_reason


def test_explain_decision():
    """Test decision explanation generation."""
    results = [
        PolicyResult(
            decision=PolicyDecision.ALLOW,
            priority=PolicyPriority.HIGH,
            reason="Test reason",
            policy_name="TestPolicy",
        )
    ]

    decision = PolicyConflictResolver.resolve(results)
    explanation = PolicyConflictResolver.explain_decision(decision)

    assert "ALLOW" in explanation
    assert "TestPolicy" in explanation
    assert "Test reason" in explanation
    assert "HIGH" in explanation


def test_complex_multi_priority_scenario():
    """Test complex scenario with multiple priorities."""
    results = [
        PolicyResult(
            decision=PolicyDecision.ALLOW,
            priority=PolicyPriority.LOW,
            reason="Default allow",
            policy_name="DefaultPolicy",
        ),
        PolicyResult(
            decision=PolicyDecision.DENY,
            priority=PolicyPriority.MEDIUM,
            reason="Rate limit exceeded",
            policy_name="RateLimitPolicy",
        ),
        PolicyResult(
            decision=PolicyDecision.ALLOW,
            priority=PolicyPriority.HIGH,
            reason="Premium user",
            policy_name="PremiumPolicy",
        ),
        PolicyResult(
            decision=PolicyDecision.ALLOW,
            priority=PolicyPriority.CRITICAL,
            reason="Emergency override",
            policy_name="EmergencyPolicy",
        ),
    ]

    decision = PolicyConflictResolver.resolve(results)

    # CRITICAL ALLOW should win
    assert decision.final_decision == PolicyDecision.ALLOW
    assert decision.has_conflict is False


def test_governance_decision_to_dict():
    """Test GovernanceDecision serialization."""
    results = [
        PolicyResult(
            decision=PolicyDecision.ALLOW,
            priority=PolicyPriority.HIGH,
            reason="Test",
            policy_name="Test",
        )
    ]

    decision = GovernanceDecision(
        final_decision=PolicyDecision.ALLOW,
        policy_results=results,
        has_conflict=False,
        conflict_reason=None,
    )

    d = decision.to_dict()

    assert d["final_decision"] == "ALLOW"
    assert d["has_conflict"] is False
    assert d["num_policies_evaluated"] == 1
    assert len(d["policy_details"]) == 1
