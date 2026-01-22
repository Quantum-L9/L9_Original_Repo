"""
Unit Tests for runtime/execution_gate.py

Tests the guarded_execute contract which is THE enforcement mechanism
for the kernel system (GODMODE Part 2).

Version: 1.0.0
"""

from unittest.mock import MagicMock

import pytest


class TestGuardedExecuteContract:
    """Test the guarded_execute function (GODMODE Part 2)."""

    def _create_mock_agent(
        self,
        initialized: bool = True,
        owner: str = "igor",
        boot_overlay: dict = None,
    ):
        """Create a mock agent with kernel_state."""
        from runtime.kernel_state import KernelState

        agent = MagicMock()
        agent.kernel_state = KernelState(
            owner=owner,
            initialized=initialized,
        )
        agent.boot_overlay = boot_overlay or {}
        return agent

    def test_guarded_execute_fails_without_kernel_state(self):
        """Execution fails if agent has no kernel_state."""
        from runtime.execution_gate import guarded_execute

        agent = MagicMock()
        agent.kernel_state = None

        with pytest.raises(RuntimeError) as exc_info:
            guarded_execute(agent, "memory_search", {"query": "test"})

        assert "Kernel set not active" in str(exc_info.value)
        assert "kernel_state.initialized == False" in str(exc_info.value)

    def test_guarded_execute_fails_if_not_initialized(self):
        """Execution fails if kernel_state.initialized is False."""
        from runtime.execution_gate import guarded_execute

        agent = self._create_mock_agent(initialized=False)

        with pytest.raises(RuntimeError) as exc_info:
            guarded_execute(agent, "memory_search", {"query": "test"})

        assert "Kernel set not active" in str(exc_info.value)

    def test_guarded_execute_fails_for_non_igor_owner(self):
        """Execution fails if owner is not Igor."""
        from runtime.execution_gate import guarded_execute

        agent = self._create_mock_agent(owner="malicious_user")

        with pytest.raises(RuntimeError) as exc_info:
            guarded_execute(agent, "memory_search", {"query": "test"})

        assert "Non-Igor execution attempted" in str(exc_info.value)
        assert "expected: igor" in str(exc_info.value)

        # Should have logged escalation
        assert len(agent.kernel_state.escalations) == 1
        assert agent.kernel_state.escalations[0]["category"] == "OWNERSHIP"
        assert agent.kernel_state.escalations[0]["severity"] == "CRITICAL"

    def test_guarded_execute_blocks_unauthorized_tool(self):
        """Unknown tools are blocked, not executed."""
        from runtime.execution_gate import guarded_execute

        agent = self._create_mock_agent()

        result = guarded_execute(agent, "unknown_dangerous_tool", {"cmd": "anything"})

        assert result["status"] == "blocked"
        assert "not authorized" in result["reason"]
        assert result["escalation"] == "SAFETY_KERNEL"

        # Should have logged escalation
        assert any(
            e["category"] == "UNAUTHORIZED_TOOL" for e in agent.kernel_state.escalations
        )


class TestSafetyScanning:
    """Test pre-execution safety scanning (GODMODE Part 3)."""

    def test_safety_scan_blocks_rm_rf(self):
        """Safety scan blocks 'rm -rf' pattern."""
        from runtime.execution_gate import _run_safety_scan

        result = _run_safety_scan("shell_exec", {"command": "rm -rf /important"})

        assert result["blocked"] is True
        assert "rm -rf" in result["reason"]

    def test_safety_scan_blocks_drop_table(self):
        """Safety scan blocks SQL DROP TABLE."""
        from runtime.execution_gate import _run_safety_scan

        result = _run_safety_scan("sql_query", {"query": "DROP TABLE users;"})

        assert result["blocked"] is True
        assert "DROP TABLE" in result["reason"]

    def test_safety_scan_blocks_fork_bomb(self):
        """Safety scan blocks fork bomb pattern."""
        from runtime.execution_gate import _run_safety_scan

        result = _run_safety_scan("shell_exec", {"command": ":(){:|:&};:"})

        assert result["blocked"] is True

    def test_safety_scan_blocks_eval(self):
        """Safety scan blocks eval() in code."""
        from runtime.execution_gate import _run_safety_scan

        result = _run_safety_scan("code_exec", {"code": "eval(user_input)"})

        assert result["blocked"] is True
        assert "eval(" in result["reason"]

    def test_safety_scan_blocks_etc_passwd(self):
        """Safety scan blocks /etc/passwd access."""
        from runtime.execution_gate import _run_safety_scan

        result = _run_safety_scan("file_read", {"path": "/etc/passwd"})

        assert result["blocked"] is True
        assert "/etc/passwd" in result["reason"]

    def test_safety_scan_allows_safe_params(self):
        """Safety scan allows normal parameters."""
        from runtime.execution_gate import _run_safety_scan

        result = _run_safety_scan("memory_search", {"query": "find related topics"})

        assert result["blocked"] is False

    def test_safety_scan_case_insensitive(self):
        """Safety scan is case-insensitive."""
        from runtime.execution_gate import _run_safety_scan

        result = _run_safety_scan("sql_query", {"query": "drop TABLE Users"})

        assert result["blocked"] is True


class TestToolAuthorization:
    """Test tool authorization matrix."""

    def _create_mock_agent(self, boot_overlay: dict = None):
        """Create a mock agent."""
        from runtime.kernel_state import KernelState

        agent = MagicMock()
        agent.kernel_state = KernelState(initialized=True)
        agent.boot_overlay = boot_overlay or {}
        return agent

    def test_high_trust_tools_in_default_matrix(self):
        """HIGH_TRUST tools are in default authorization matrix."""
        from runtime.execution_gate import DEFAULT_TOOL_AUTHORIZATION

        high_trust_tools = [
            "memory_search",
            "memory_hybrid_search",
            "memory_get_packet",
            "neo4j_query",
            "kernel_read",
        ]

        for tool in high_trust_tools:
            assert tool in DEFAULT_TOOL_AUTHORIZATION
            assert DEFAULT_TOOL_AUTHORIZATION[tool]["class"] == "HIGH_TRUST"

    def test_low_trust_tools_require_confirmation(self):
        """LOW_TRUST tools require confirmation."""
        from runtime.execution_gate import DEFAULT_TOOL_AUTHORIZATION

        low_trust_tools = [
            "memory_write",
            "gmp_run",
            "git_commit",
            "mac_agent_exec_task",
        ]

        for tool in low_trust_tools:
            assert tool in DEFAULT_TOOL_AUTHORIZATION
            assert DEFAULT_TOOL_AUTHORIZATION[tool]["class"] == "LOW_TRUST"
            assert DEFAULT_TOOL_AUTHORIZATION[tool]["requires_confirmation"] is True

    def test_boot_overlay_overrides_defaults(self):
        """Boot overlay can override default tool authorization."""
        from runtime.execution_gate import _get_tool_authorization

        custom_auth = {"memory_search": {"class": "RESTRICTED", "blocked": True}}

        agent = self._create_mock_agent(
            boot_overlay={"tool_authorization_matrix": custom_auth}
        )

        result = _get_tool_authorization(agent, "memory_search")

        assert result["class"] == "RESTRICTED"
        assert result["blocked"] is True

    def test_unknown_tool_returns_none(self):
        """Unknown tools return None for authorization."""
        from runtime.execution_gate import _get_tool_authorization

        agent = self._create_mock_agent()

        result = _get_tool_authorization(agent, "completely_unknown_tool")

        assert result is None


class TestConfidenceEscalation:
    """Test confidence-based escalation (GODMODE Part 4.2)."""

    def test_should_escalate_below_threshold(self):
        """Confidence below 70% should escalate."""
        from runtime.execution_gate import should_escalate_on_confidence

        assert should_escalate_on_confidence(0.50) is True
        assert should_escalate_on_confidence(0.69) is True
        assert should_escalate_on_confidence(0.65) is True

    def test_should_not_escalate_above_threshold(self):
        """Confidence at or above 70% should not escalate."""
        from runtime.execution_gate import should_escalate_on_confidence

        assert should_escalate_on_confidence(0.70) is False
        assert should_escalate_on_confidence(0.80) is False
        assert should_escalate_on_confidence(0.95) is False

    def test_custom_threshold(self):
        """Custom threshold works correctly."""
        from runtime.execution_gate import should_escalate_on_confidence

        # With 80% threshold
        assert should_escalate_on_confidence(0.75, threshold=0.80) is True
        assert should_escalate_on_confidence(0.80, threshold=0.80) is False


class TestModeSelection:
    """Test mode selection based on confidence (GODMODE Part 1.2)."""

    def test_executive_mode_at_high_confidence(self):
        """Confidence >= 80% selects executive mode."""
        from runtime.execution_gate import select_mode_based_on_confidence

        assert select_mode_based_on_confidence(0.95) == "executive"
        assert select_mode_based_on_confidence(0.80) == "executive"
        assert select_mode_based_on_confidence(0.85) == "executive"

    def test_developer_mode_at_medium_confidence(self):
        """Confidence 70-79% selects developer mode."""
        from runtime.execution_gate import select_mode_based_on_confidence

        assert select_mode_based_on_confidence(0.75) == "developer"
        assert select_mode_based_on_confidence(0.70) == "developer"
        assert select_mode_based_on_confidence(0.79) == "developer"

    def test_ask_mode_at_low_confidence(self):
        """Confidence < 70% selects ask mode."""
        from runtime.execution_gate import select_mode_based_on_confidence

        assert select_mode_based_on_confidence(0.69) == "ask"
        assert select_mode_based_on_confidence(0.50) == "ask"
        assert select_mode_based_on_confidence(0.30) == "ask"


class TestEscalateToIgor:
    """Test escalation formatting."""

    def test_escalate_to_igor_formats_message(self):
        """escalate_to_igor() produces formatted message."""
        from runtime.execution_gate import escalate_to_igor
        from runtime.kernel_state import KernelState

        state = KernelState()

        message = escalate_to_igor(
            kernel_state=state,
            issue="Uncertain about best approach",
            confidence=0.55,
            options=[
                "Option A: Do X",
                "Option B: Do Y",
                "Option C: Ask more questions",
            ],
            context={"tool": "complex_operation"},
        )

        assert "ESCALATION" in message
        assert "55%" in message
        assert "Option A: Do X" in message
        assert "Option B: Do Y" in message
        assert "Awaiting Igor's decision" in message

    def test_escalate_to_igor_logs_escalation(self):
        """escalate_to_igor() logs the escalation."""
        from runtime.execution_gate import escalate_to_igor
        from runtime.kernel_state import KernelState

        state = KernelState()

        escalate_to_igor(
            kernel_state=state,
            issue="Test issue",
            confidence=0.60,
            options=["A", "B"],
            context={},
        )

        assert len(state.escalations) == 1
        assert state.escalations[0]["category"] == "LOW_CONFIDENCE"
        assert state.escalations[0]["severity"] == "MEDIUM"


class TestForbiddenPatterns:
    """Test FORBIDDEN_PATTERNS constant."""

    def test_forbidden_patterns_has_shell_category(self):
        """FORBIDDEN_PATTERNS includes shell category."""
        from runtime.execution_gate import FORBIDDEN_PATTERNS

        assert "shell" in FORBIDDEN_PATTERNS
        assert "rm -rf" in FORBIDDEN_PATTERNS["shell"]
        assert "chmod 777" in FORBIDDEN_PATTERNS["shell"]

    def test_forbidden_patterns_has_sql_category(self):
        """FORBIDDEN_PATTERNS includes SQL category."""
        from runtime.execution_gate import FORBIDDEN_PATTERNS

        assert "sql" in FORBIDDEN_PATTERNS
        assert "DROP TABLE" in FORBIDDEN_PATTERNS["sql"]
        assert "DROP DATABASE" in FORBIDDEN_PATTERNS["sql"]

    def test_forbidden_patterns_has_code_category(self):
        """FORBIDDEN_PATTERNS includes code category."""
        from runtime.execution_gate import FORBIDDEN_PATTERNS

        assert "code" in FORBIDDEN_PATTERNS
        assert "eval(" in FORBIDDEN_PATTERNS["code"]
        assert "exec(" in FORBIDDEN_PATTERNS["code"]

    def test_forbidden_patterns_has_filesystem_category(self):
        """FORBIDDEN_PATTERNS includes filesystem category."""
        from runtime.execution_gate import FORBIDDEN_PATTERNS

        assert "filesystem" in FORBIDDEN_PATTERNS
        assert "/etc/passwd" in FORBIDDEN_PATTERNS["filesystem"]
        assert "~/.ssh" in FORBIDDEN_PATTERNS["filesystem"]


class TestPublicAPI:
    """Test public API exports."""

    def test_all_exports_are_importable(self):
        """All __all__ exports are importable."""
        from runtime.execution_gate import (DEFAULT_TOOL_AUTHORIZATION,
                                            FORBIDDEN_PATTERNS,
                                            escalate_to_igor, guarded_execute,
                                            select_mode_based_on_confidence,
                                            should_escalate_on_confidence)

        assert callable(guarded_execute)
        assert callable(should_escalate_on_confidence)
        assert callable(escalate_to_igor)
        assert callable(select_mode_based_on_confidence)
        assert isinstance(DEFAULT_TOOL_AUTHORIZATION, dict)
        assert isinstance(FORBIDDEN_PATTERNS, dict)
