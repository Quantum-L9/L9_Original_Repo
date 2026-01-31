"""
Unit Tests for runtime/kernel_state.py

Tests the KernelState dataclass which provides the audit trail for kernel
operations (GODMODE Part 1.1 + Part 7.2).

Version: 1.0.0
"""

from datetime import datetime, timezone


class TestKernelStateCreation:
    """Test KernelState instantiation and factory function."""

    def test_default_kernel_state_values(self):
        """KernelState has correct default values."""
        from runtime.kernel_state import KernelState

        state = KernelState()

        assert state.owner == "igor"
        assert state.agent_id == "l-cto"
        assert state.agent_name == "l_cto"
        assert state.mode == "executive"
        assert state.initialized is False
        assert state.active_kernels == {}
        assert state.boot_overlay == {}
        assert state.activation_context == {}
        assert state.decisions == []
        assert state.escalations == []
        assert state.tools_executed == []
        assert state.confidence_calibrations == {}
        assert state.kernel_snapshots == []

    def test_create_kernel_state_factory(self):
        """create_kernel_state() produces valid KernelState."""
        from runtime.kernel_state import create_kernel_state

        state = create_kernel_state(agent_id="test-agent", session_id="test-session")

        assert state.agent_id == "test-agent"
        assert state.session_id == "test-session"
        assert state.initialized is False
        assert isinstance(state.timestamp, datetime)

    def test_create_kernel_state_auto_session_id(self):
        """create_kernel_state() generates session_id when not provided."""
        from runtime.kernel_state import create_kernel_state

        state = create_kernel_state(agent_id="test-agent")

        assert state.session_id.startswith("session_")
        assert len(state.session_id) > len("session_")

    def test_kernel_state_custom_values(self):
        """KernelState accepts custom values."""
        from runtime.kernel_state import KernelState

        state = KernelState(
            owner="test-owner",
            agent_id="custom-agent",
            mode="developer",
            initialized=True,
        )

        assert state.owner == "test-owner"
        assert state.agent_id == "custom-agent"
        assert state.mode == "developer"
        assert state.initialized is True


class TestDecisionLogging:
    """Test decision logging (GODMODE Part 7.1)."""

    def test_log_decision_appends_to_list(self):
        """log_decision() adds entry to decisions list."""
        from runtime.kernel_state import KernelState

        state = KernelState()

        state.log_decision(
            intent="Execute memory search",
            reasoning="User requested relevant context",
            confidence=0.95,
            outcome="pending",
            kernel_source="EXECUTION_KERNEL",
        )

        assert len(state.decisions) == 1
        decision = state.decisions[0]
        assert decision["intent"] == "Execute memory search"
        assert decision["reasoning"] == "User requested relevant context"
        assert decision["confidence"] == 0.95
        assert decision["outcome"] == "pending"
        assert decision["kernel_source"] == "EXECUTION_KERNEL"
        assert "timestamp" in decision

    def test_log_decision_multiple_entries(self):
        """Multiple decisions are tracked in order."""
        from runtime.kernel_state import KernelState

        state = KernelState()

        state.log_decision("Intent 1", "Reason 1", 0.9)
        state.log_decision("Intent 2", "Reason 2", 0.8)
        state.log_decision("Intent 3", "Reason 3", 0.7)

        assert len(state.decisions) == 3
        assert state.decisions[0]["intent"] == "Intent 1"
        assert state.decisions[1]["intent"] == "Intent 2"
        assert state.decisions[2]["intent"] == "Intent 3"

    def test_log_decision_default_outcome(self):
        """log_decision() uses 'pending' as default outcome."""
        from runtime.kernel_state import KernelState

        state = KernelState()
        state.log_decision("Test intent", "Test reason", 0.85)

        assert state.decisions[0]["outcome"] == "pending"


class TestEscalationLogging:
    """Test escalation logging (GODMODE Part 3.3)."""

    def test_log_escalation_appends_to_list(self):
        """log_escalation() adds entry to escalations list."""
        from runtime.kernel_state import KernelState

        state = KernelState()

        state.log_escalation(
            category="SAFETY_VIOLATION",
            issue="Forbidden pattern detected",
            severity="HIGH",
            trigger="rm -rf in params",
            action="HALT_EXECUTION",
        )

        assert len(state.escalations) == 1
        escalation = state.escalations[0]
        assert escalation["category"] == "SAFETY_VIOLATION"
        assert escalation["issue"] == "Forbidden pattern detected"
        assert escalation["severity"] == "HIGH"
        assert escalation["trigger"] == "rm -rf in params"
        assert escalation["action"] == "HALT_EXECUTION"
        assert escalation["awaiting"] == "IGOR"  # No resolution = awaiting Igor
        assert "timestamp" in escalation

    def test_log_escalation_with_resolution(self):
        """Resolved escalation does not await Igor."""
        from runtime.kernel_state import KernelState

        state = KernelState()

        state.log_escalation(
            category="LOW_CONFIDENCE",
            issue="Confidence below threshold",
            severity="MEDIUM",
            resolution="User confirmed action",
        )

        assert state.escalations[0]["awaiting"] is None
        assert state.escalations[0]["resolution"] == "User confirmed action"

    def test_get_pending_escalations(self):
        """get_pending_escalations() returns only unresolved escalations."""
        from runtime.kernel_state import KernelState

        state = KernelState()

        state.log_escalation("CAT1", "Issue 1", "HIGH")  # Pending
        state.log_escalation(
            "CAT2", "Issue 2", "LOW", resolution="Resolved"
        )  # Resolved
        state.log_escalation("CAT3", "Issue 3", "CRITICAL")  # Pending

        pending = state.get_pending_escalations()

        assert len(pending) == 2
        assert pending[0]["issue"] == "Issue 1"
        assert pending[1]["issue"] == "Issue 3"

    def test_get_critical_escalations(self):
        """get_critical_escalations() returns only CRITICAL severity."""
        from runtime.kernel_state import KernelState

        state = KernelState()

        state.log_escalation("CAT1", "Issue 1", "HIGH")
        state.log_escalation("CAT2", "Issue 2", "CRITICAL")
        state.log_escalation("CAT3", "Issue 3", "LOW")
        state.log_escalation("CAT4", "Issue 4", "CRITICAL")

        critical = state.get_critical_escalations()

        assert len(critical) == 2
        assert critical[0]["severity"] == "CRITICAL"
        assert critical[1]["severity"] == "CRITICAL"


class TestToolExecutionLogging:
    """Test tool execution logging (GODMODE Part 7.1)."""

    def test_log_tool_execution_success(self):
        """log_tool_execution() logs successful execution."""
        from runtime.kernel_state import KernelState

        state = KernelState()

        state.log_tool_execution(
            tool_id="memory_search",
            params={"query": "test"},
            status="success",
            result={"hits": 5},
        )

        assert len(state.tools_executed) == 1
        execution = state.tools_executed[0]
        assert execution["tool"] == "memory_search"
        assert execution["params"] == {"query": "test"}
        assert execution["status"] == "success"
        assert execution["result"] == {"hits": 5}
        assert execution["error"] is None

    def test_log_tool_execution_blocked(self):
        """log_tool_execution() logs blocked execution."""
        from runtime.kernel_state import KernelState

        state = KernelState()

        state.log_tool_execution(
            tool_id="dangerous_tool",
            params={"cmd": "rm -rf /"},
            status="blocked",
            error="Forbidden pattern detected",
        )

        execution = state.tools_executed[0]
        assert execution["status"] == "blocked"
        assert execution["result"] is None  # Result cleared on non-success
        assert execution["error"] == "Forbidden pattern detected"

    def test_log_tool_execution_failure(self):
        """log_tool_execution() logs failed execution."""
        from runtime.kernel_state import KernelState

        state = KernelState()

        state.log_tool_execution(
            tool_id="api_call",
            params={"url": "http://example.com"},
            status="failure",
            error="Connection timeout",
        )

        execution = state.tools_executed[0]
        assert execution["status"] == "failure"
        assert execution["error"] == "Connection timeout"


class TestSessionExport:
    """Test session export functionality (GODMODE Part 7.2)."""

    def test_export_session_memory_structure(self):
        """export_session_memory() returns complete session state."""
        from runtime.kernel_state import KernelState

        state = KernelState(
            owner="igor",
            agent_id="l-cto",
            mode="executive",
            session_id="test-session-123",
        )
        state.initialized = True
        state.active_kernels = {"master": True, "safety": True}

        # Add some data
        state.log_decision("Test decision", "Test reason", 0.9)
        state.log_escalation("CAT", "Issue", "HIGH")
        state.log_tool_execution("tool1", {}, "success")

        export = state.export_session_memory()

        assert export["session_id"] == "test-session-123"
        assert export["owner"] == "igor"
        assert export["agent_id"] == "l-cto"
        assert export["mode"] == "executive"
        assert export["initialized"] is True
        assert "master" in export["active_kernels"]
        assert "safety" in export["active_kernels"]
        assert len(export["decisions_made"]) == 1
        assert len(export["escalations"]) == 1
        assert len(export["tools_executed"]) == 1
        assert "start_time" in export

    def test_export_session_memory_empty_state(self):
        """export_session_memory() works with empty state."""
        from runtime.kernel_state import KernelState

        state = KernelState()
        export = state.export_session_memory()

        assert export["decisions_made"] == []
        assert export["escalations"] == []
        assert export["tools_executed"] == []


class TestSummary:
    """Test summary generation."""

    def test_summary_returns_correct_counts(self):
        """summary() returns accurate counts."""
        from runtime.kernel_state import KernelState

        state = KernelState(mode="developer")
        state.active_kernels = {"k1": True, "k2": True, "k3": True}

        state.log_decision("D1", "R1", 0.9)
        state.log_decision("D2", "R2", 0.8)
        state.log_tool_execution("t1", {}, "success")
        state.log_escalation("CAT1", "I1", "CRITICAL")
        state.log_escalation("CAT2", "I2", "HIGH", resolution="Done")

        summary = state.summary()

        assert summary["mode"] == "developer"
        assert summary["active_kernels"] == 3
        assert summary["decisions_logged"] == 2
        assert summary["tools_executed"] == 1
        assert summary["escalations"] == 2
        assert summary["pending_escalations"] == 1  # One resolved
        assert summary["critical_escalations"] == 1


class TestTimestamps:
    """Test timestamp handling."""

    def test_decision_timestamp_format(self):
        """Decision timestamps are ISO format."""
        from runtime.kernel_state import KernelState

        state = KernelState()
        state.log_decision("Test", "Reason", 0.9)

        timestamp = state.decisions[0]["timestamp"]
        # Should be parseable as ISO datetime
        datetime.fromisoformat(timestamp)

    def test_escalation_timestamp_format(self):
        """Escalation timestamps are ISO format."""
        from runtime.kernel_state import KernelState

        state = KernelState()
        state.log_escalation("CAT", "Issue", "HIGH")

        timestamp = state.escalations[0]["timestamp"]
        datetime.fromisoformat(timestamp)

    def test_tool_execution_timestamp_format(self):
        """Tool execution timestamps are ISO format."""
        from runtime.kernel_state import KernelState

        state = KernelState()
        state.log_tool_execution("tool", {}, "success")

        timestamp = state.tools_executed[0]["timestamp"]
        datetime.fromisoformat(timestamp)
