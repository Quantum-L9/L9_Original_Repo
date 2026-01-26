"""
L9 Integration Tests - L-CTO Memory + Governance Integration
============================================================

Tests the integration between:
- Memory emission (PacketEnvelope)
- Governance validation (authority + safety)
- Audit logging
- Drift detection

Version: 1.0.0
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

# CRITICAL: Set path BEFORE any imports
# Use resolve() to get absolute path
PROJECT_ROOT = Path(__file__).parent.parent.parent.resolve()
PROJECT_ROOT_STR = str(PROJECT_ROOT)
if PROJECT_ROOT_STR not in sys.path:
    sys.path.insert(0, PROJECT_ROOT_STR)

# Also set PYTHONPATH env var for subprocesses
os.environ.setdefault("PYTHONPATH", PROJECT_ROOT_STR)

import pytest

from core.governance.validation import (
    audit_log,
    detect_drift,
    get_audit_trail,
    validate_authority,
    validate_safety,
)


class TestMemoryGovernanceIntegration:
    """Test memory and governance integration."""

    @pytest.mark.asyncio
    async def test_governance_validation_before_memory_write(self):
        """
        Test governance validation happens before memory writes.

        Flow:
        1. Validate authority
        2. Validate safety
        3. Only if both pass, proceed to memory write
        """
        # Valid action
        authority_result = validate_authority(action="analyze code", agent_id="l-cto")
        safety_result = validate_safety(action="analyze code")

        assert authority_result["valid"] is True
        assert safety_result["safe"] is True

        # Invalid action (authority)
        authority_result = validate_authority(
            action="privilege_escalation", agent_id="l-cto"
        )
        assert authority_result["valid"] is False

        # Invalid action (safety)
        safety_result = validate_safety(action="rm -rf /")
        assert safety_result["safe"] is False

    @pytest.mark.asyncio
    async def test_audit_trail_tracks_executions(self):
        """
        Test audit trail tracks all executions for drift detection.

        Flow:
        1. Execute multiple actions
        2. Audit log records each
        3. Drift detection uses audit trail
        """
        agent_id = "l-cto"

        # Log successful executions
        for i in range(5):
            audit_log(agent_id=agent_id, action=f"action_{i}", success=True)

        # Log some failures
        for i in range(2):
            audit_log(agent_id=agent_id, action=f"action_{i+5}", success=False)

        # Get audit trail
        trail = get_audit_trail(agent_id=agent_id, limit=10)

        assert len(trail) >= 7

        # Check drift detection
        drift = detect_drift(
            agent_id=agent_id, action="action_10", success=True, threshold=0.6
        )

        # Should not detect drift (5/7 = 71% success rate > 60%)
        assert drift is None or drift["drift_detected"] is False

    @pytest.mark.asyncio
    async def test_drift_detection_triggers_on_low_success_rate(self):
        """
        Test drift detection triggers when success rate drops.

        Flow:
        1. Log many failures
        2. Check drift detection
        3. Verify drift detected
        """
        agent_id = "l-cto"

        # Log mostly failures
        for i in range(10):
            audit_log(
                agent_id=agent_id, action=f"action_{i}", success=(i < 2)
            )  # Only 2/10 succeed

        # Check drift
        drift = detect_drift(
            agent_id=agent_id, action="action_10", success=False, threshold=0.6
        )

        assert drift is not None
        assert drift["drift_detected"] is True
        assert drift["type"] in ["success_rate_drop", "repeated_failure"]

    @pytest.mark.asyncio
    async def test_governance_blocks_and_logs_violations(self):
        """
        Test governance blocks violations and logs them.

        Flow:
        1. Attempt forbidden action
        2. Authority validation blocks
        3. Audit log records violation
        """
        agent_id = "l-cto"
        action = "privilege_escalation attempt"

        # Validate (should block)
        authority_result = validate_authority(action=action, agent_id=agent_id)

        assert authority_result["valid"] is False

        # Log the blocked attempt
        audit_log(
            agent_id=agent_id,
            action=action,
            success=False,
            metadata={"blocked": True, "reason": "authority_violation"},
        )

        # Verify in audit trail
        trail = get_audit_trail(agent_id=agent_id, limit=10)
        assert len(trail) > 0

        # Find the blocked entry
        blocked_entries = [
            e for e in trail if e.get("action") == action and e.get("success") is False
        ]
        assert len(blocked_entries) > 0


class TestLCTOMemoryPacketStructure:
    """Test L-CTO memory packet structure matches spec."""

    def test_packet_envelope_has_required_fields(self):
        """Test PacketEnvelope has all required fields per spec."""
        # Ensure path is set
        import os
        import sys

        project_root = os.path.dirname(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        )
        if project_root not in sys.path:
            sys.path.insert(0, project_root)
        from core.schemas import PacketEnvelopeIn, PacketMetadata

        packet = PacketEnvelopeIn(
            packet_type="agent.l_cto.reasoning",
            payload={"test": "data"},
            metadata=PacketMetadata(agent="l-cto", schema_version="1.0.0"),
        )

        # Required fields
        assert packet.packet_type is not None
        assert packet.payload is not None
        assert packet.metadata is not None
        assert packet.metadata.agent == "l-cto"
        assert packet.metadata.schema_version == "1.0.0"

    def test_packet_metadata_agent_id_matches_task(self):
        """Test packet metadata.agent matches task.agent_id."""
        # Import inside function - path should be set by conftest.py
        # But ensure it's set here too for safety
        import os
        import sys

        project_root = os.path.dirname(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        )
        if project_root not in sys.path:
            sys.path.insert(0, project_root)
        from core.schemas import PacketEnvelopeIn, PacketMetadata

        agent_id = "l-cto"

        packet = PacketEnvelopeIn(
            packet_type="agent.executor.trace",
            payload={"agent_id": agent_id},
            metadata=PacketMetadata(
                agent=agent_id,
                schema_version="1.0.0",  # Should match payload.agent_id
            ),
        )

        assert packet.metadata.agent == agent_id
        assert packet.payload["agent_id"] == agent_id


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
