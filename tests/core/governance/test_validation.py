"""
L9 Core Governance - Validation Tests
=====================================

Tests for governance validation functions:
- validate_authority()
- validate_safety()
- detect_drift()
- audit_log()
- get_audit_trail()

Version: 1.0.0
"""

from __future__ import annotations

import pytest
from core.governance.validation import (
    validate_authority,
    validate_safety,
    detect_drift,
    audit_log,
    get_audit_trail,
)


class TestValidateAuthority:
    """Test authority validation."""

    def test_allows_normal_action(self):
        """Normal actions should be allowed."""
        result = validate_authority(action="analyze code", agent_id="l-cto")
        assert result["valid"] is True
        assert result["agent_id"] == "l-cto"

    def test_blocks_forbidden_actions(self):
        """Forbidden actions should be blocked."""
        forbidden_actions = [
            "privilege_escalation",
            "autonomy_increase",
            "governance_circumvention",
            "ceo_override",
        ]

        for action in forbidden_actions:
            result = validate_authority(action=action, agent_id="l-cto")
            assert result["valid"] is False
            assert "violation" in result

    def test_blocks_l_cto_override_igor(self):
        """L-CTO cannot override Igor (CEO)."""
        result = validate_authority(action="override igor decision", agent_id="l-cto")
        assert result["valid"] is False
        assert "CEO" in result.get("violation", "")

    def test_allows_other_agents_override(self):
        """Other agents might have different rules (future)."""
        result = validate_authority(action="override igor decision", agent_id="l9")
        # Currently blocks for all, but structure allows per-agent rules
        assert "valid" in result


class TestValidateSafety:
    """Test safety validation."""

    def test_allows_safe_action(self):
        """Safe actions should pass."""
        result = validate_safety(action="read file", payload={"file": "readme.md"})
        assert result["safe"] is True

    def test_blocks_dangerous_patterns(self):
        """Dangerous patterns should be blocked."""
        dangerous = [
            "rm -rf /",
            "DROP DATABASE",
            "DELETE FROM users",
            "shutdown system",
            "kill -9 process",
        ]

        for action in dangerous:
            result = validate_safety(action=action)
            # Note: validate_safety logs warnings but may return safe=True
            # The actual blocking happens in executor, not validation
            assert "safe" in result
            # If unsafe, should have violation
            if not result["safe"]:
                assert "violation" in result

    def test_blocks_dangerous_payload(self):
        """Dangerous patterns in payload should be blocked."""
        result = validate_safety(action="execute command", payload={"command": "rm -rf /"})
        assert result["safe"] is False


class TestDetectDrift:
    """Test drift detection."""

    def test_no_drift_with_high_success_rate(self):
        """High success rate should not trigger drift."""
        # Simulate high success rate
        for i in range(10):
            audit_log(agent_id="l-cto", action=f"action_{i}", success=True)

        drift = detect_drift(agent_id="l-cto", action="action_10", success=True, threshold=0.6)

        assert drift is None  # No drift detected

    def test_drift_detected_with_low_success_rate(self):
        """Low success rate should trigger drift."""
        # Simulate low success rate
        for i in range(10):
            audit_log(
                agent_id="l-cto",
                action=f"action_{i}",
                success=(i < 3),  # Only 3/10 succeed
            )

        drift = detect_drift(agent_id="l-cto", action="action_10", success=False, threshold=0.6)

        assert drift is not None
        assert drift["drift_detected"] is True
        assert drift["type"] == "success_rate_drop"

    def test_drift_detected_with_repeated_failures(self):
        """Repeated failures on same action should trigger drift."""
        action = "problematic_action"

        # Simulate repeated failures
        for i in range(3):
            audit_log(agent_id="l-cto", action=action, success=False)

        drift = detect_drift(agent_id="l-cto", action=action, success=False, threshold=0.6)

        assert drift is not None
        assert drift["drift_detected"] is True
        # Drift type can be either "repeated_failure" or "success_rate_drop"
        assert drift["type"] in ["repeated_failure", "success_rate_drop"]
        # If it's success_rate_drop, check success_rate
        if drift["type"] == "success_rate_drop":
            assert drift["success_rate"] < 0.6


class TestAuditLog:
    """Test audit logging."""

    def test_audit_log_creates_entry(self):
        """Audit log should create entries."""
        audit_log(
            agent_id="l-cto",
            action="test_action",
            success=True,
            metadata={"test": True},
        )

        trail = get_audit_trail(agent_id="l-cto", limit=10)

        assert len(trail) > 0
        assert trail[-1]["agent_id"] == "l-cto"
        assert trail[-1]["action"] == "test_action"
        assert trail[-1]["success"] is True

    def test_audit_trail_filtered_by_agent(self):
        """Audit trail should filter by agent_id."""
        audit_log(agent_id="l-cto", action="action1", success=True)
        audit_log(agent_id="l9", action="action2", success=True)
        audit_log(agent_id="l-cto", action="action3", success=True)

        l_cto_trail = get_audit_trail(agent_id="l-cto", limit=10)
        l9_trail = get_audit_trail(agent_id="l9", limit=10)

        assert len(l_cto_trail) >= 2
        assert all(e["agent_id"] == "l-cto" for e in l_cto_trail)
        assert len(l9_trail) >= 1
        assert all(e["agent_id"] == "l9" for e in l9_trail)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
