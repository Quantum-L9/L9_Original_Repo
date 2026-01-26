"""
Tests for Guarded Execution
===========================

Tests the kernel-aware guarded execution flow:
- Kernel state verification before tool dispatch
- Behavioral constraint enforcement
- Safety constraint enforcement
- Integration with executor

GMP: kernel_boot_frontier_phase1
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from core.agents.schemas import (
    AgentConfig,
    AgentTask,
    ToolBinding,
    ToolCallRequest,
    ToolCallResult,
)

# =============================================================================
# Fixtures
# =============================================================================


class MockKernelAwareAgent:
    """Mock agent with kernel state."""

    def __init__(
        self,
        kernel_state: str = "ACTIVE",
        kernels: dict[str, Any] | None = None,
        behavioral: dict[str, Any] | None = None,
        safety: dict[str, Any] | None = None,
    ) -> None:
        self.agent_id = "test-agent"
        self.kernel_state = kernel_state
        # Note: Use 'is None' check, not 'or', to allow empty dict
        self.kernels = {"kernel1": {}, "kernel2": {}} if kernels is None else kernels
        self._behavioral = behavioral or {}
        self._safety = safety or {}


class MockToolRegistry:
    """Mock tool registry with dispatch_tool_call."""

    def __init__(self) -> None:
        self._dispatch_result = ToolCallResult(
            call_id=uuid4(),
            tool_id="test_tool",
            success=True,
            result={"data": "test"},
        )

    async def dispatch_tool_call(
        self,
        tool_id: str,
        arguments: dict[str, Any],
        context: dict[str, Any],
    ) -> ToolCallResult:
        return self._dispatch_result


@pytest.fixture
def mock_agent() -> MockKernelAwareAgent:
    """Create a mock kernel-aware agent."""
    return MockKernelAwareAgent()


@pytest.fixture
def mock_registry() -> MockToolRegistry:
    """Create a mock tool registry."""
    return MockToolRegistry()


# =============================================================================
# ExecutorToolRegistry.guarded_execute Tests
# =============================================================================


class TestGuardedExecute:
    """Tests for ExecutorToolRegistry.guarded_execute."""

    @pytest.mark.asyncio
    async def test_guarded_execute_success(
        self, mock_agent: MockKernelAwareAgent
    ) -> None:
        """guarded_execute should succeed with active kernels."""
        from core.tools.registry_adapter import ExecutorToolRegistry

        registry = ExecutorToolRegistry(governance_enabled=False)

        # Mock the dispatch_tool_call method
        registry.dispatch_tool_call = AsyncMock(
            return_value=ToolCallResult(
                call_id=uuid4(),
                tool_id="test_tool",
                success=True,
                result={"data": "test"},
            )
        )

        result = await registry.guarded_execute(
            agent=mock_agent,
            tool_id="test_tool",
            arguments={"arg1": "value1"},
            context={"task_id": "test-task"},
        )

        assert result.success is True
        assert result.tool_id == "test_tool"

    @pytest.mark.asyncio
    async def test_guarded_execute_fails_inactive_kernels(self) -> None:
        """guarded_execute should fail if kernels not active."""
        from core.tools.registry_adapter import ExecutorToolRegistry

        registry = ExecutorToolRegistry(governance_enabled=False)

        agent = MockKernelAwareAgent(kernel_state="INACTIVE")

        result = await registry.guarded_execute(
            agent=agent,
            tool_id="test_tool",
            arguments={},
        )

        assert result.success is False
        assert "not active" in result.error.lower()

    @pytest.mark.asyncio
    async def test_guarded_execute_fails_no_kernels(self) -> None:
        """guarded_execute should fail if no kernels loaded."""
        from core.tools.registry_adapter import ExecutorToolRegistry

        registry = ExecutorToolRegistry(governance_enabled=False)

        agent = MockKernelAwareAgent(kernel_state="ACTIVE", kernels={})

        result = await registry.guarded_execute(
            agent=agent,
            tool_id="test_tool",
            arguments={},
        )

        assert result.success is False
        assert "no kernels" in result.error.lower()

    @pytest.mark.asyncio
    async def test_guarded_execute_blocks_prohibited_tool(self) -> None:
        """guarded_execute should block tools prohibited by behavioral kernel."""
        from core.tools.registry_adapter import ExecutorToolRegistry

        registry = ExecutorToolRegistry(governance_enabled=False)

        agent = MockKernelAwareAgent(
            kernel_state="ACTIVE",
            kernels={"k1": {}},
            behavioral={"prohibited_tools": ["dangerous_tool"]},
        )

        result = await registry.guarded_execute(
            agent=agent,
            tool_id="dangerous_tool",
            arguments={},
        )

        assert result.success is False
        assert "prohibited" in result.error.lower()

    @pytest.mark.asyncio
    async def test_guarded_execute_blocks_prohibited_action(self) -> None:
        """guarded_execute should block actions prohibited by safety kernel."""
        from core.tools.registry_adapter import ExecutorToolRegistry

        registry = ExecutorToolRegistry(governance_enabled=False)

        agent = MockKernelAwareAgent(
            kernel_state="ACTIVE",
            kernels={"k1": {}},
            safety={"prohibited_actions": ["delete_production"]},
        )

        result = await registry.guarded_execute(
            agent=agent,
            tool_id="delete_production_data",
            arguments={},
        )

        assert result.success is False
        assert "prohibited" in result.error.lower()

    @pytest.mark.asyncio
    async def test_guarded_execute_passes_context(
        self, mock_agent: MockKernelAwareAgent
    ) -> None:
        """guarded_execute should pass context to dispatch_tool_call."""
        from core.tools.registry_adapter import ExecutorToolRegistry

        registry = ExecutorToolRegistry(governance_enabled=False)

        captured_context = {}

        async def capture_dispatch(tool_id, arguments, context):
            captured_context.update(context)
            return ToolCallResult(
                call_id=uuid4(),
                tool_id=tool_id,
                success=True,
            )

        registry.dispatch_tool_call = capture_dispatch

        await registry.guarded_execute(
            agent=mock_agent,
            tool_id="test_tool",
            arguments={"arg1": "value1"},
            context={"task_id": "test-task", "custom": "data"},
        )

        assert captured_context.get("task_id") == "test-task"
        assert captured_context.get("custom") == "data"
        assert captured_context.get("agent_id") == "test-agent"


# =============================================================================
# Executor Integration Tests
# =============================================================================

# NOTE: These tests are skipped when tests/memory shadows the memory module.
# The shadowing occurs because pytest adds tests/ to sys.path, and tests/memory/__init__.py
# is found before the real memory module. This is a known pytest issue with package naming.


@pytest.mark.skipif(
    True,  # Skip until tests/memory naming conflict is resolved
    reason="tests/memory shadows memory module in pytest environment",
)
class TestExecutorGuardedIntegration:
    """Tests for executor integration with guarded execution."""

    def test_executor_set_kernel_aware_agent(self) -> None:
        """Executor should accept kernel-aware agent."""
        from core.agents.executor import AgentExecutorService

        # Create minimal mocks
        aios_runtime = MagicMock()
        tool_registry = MagicMock()
        substrate_service = MagicMock()
        agent_registry = MagicMock()

        executor = AgentExecutorService(
            aios_runtime=aios_runtime,
            tool_registry=tool_registry,
            substrate_service=substrate_service,
            agent_registry=agent_registry,
        )

        agent = MockKernelAwareAgent()
        executor.set_kernel_aware_agent(agent)

        assert executor._kernel_aware_agent is agent

    def test_executor_get_kernel_aware_agent_active(self) -> None:
        """Executor should return agent when kernels active."""
        from core.agents.executor import AgentExecutorService

        executor = AgentExecutorService(
            aios_runtime=MagicMock(),
            tool_registry=MagicMock(),
            substrate_service=MagicMock(),
            agent_registry=MagicMock(),
        )

        agent = MockKernelAwareAgent(kernel_state="ACTIVE")
        executor.set_kernel_aware_agent(agent)

        result = executor._get_kernel_aware_agent()

        assert result is agent

    def test_executor_get_kernel_aware_agent_inactive(self) -> None:
        """Executor should return None when kernels inactive."""
        from core.agents.executor import AgentExecutorService

        executor = AgentExecutorService(
            aios_runtime=MagicMock(),
            tool_registry=MagicMock(),
            substrate_service=MagicMock(),
            agent_registry=MagicMock(),
        )

        agent = MockKernelAwareAgent(kernel_state="INACTIVE")
        executor.set_kernel_aware_agent(agent)

        result = executor._get_kernel_aware_agent()

        assert result is None

    def test_executor_get_kernel_aware_agent_none(self) -> None:
        """Executor should return None when no agent set."""
        from core.agents.executor import AgentExecutorService

        executor = AgentExecutorService(
            aios_runtime=MagicMock(),
            tool_registry=MagicMock(),
            substrate_service=MagicMock(),
            agent_registry=MagicMock(),
        )

        result = executor._get_kernel_aware_agent()

        assert result is None


# =============================================================================
# Kernel State Transition Tests
# =============================================================================


class TestKernelStateGuards:
    """Tests for kernel state guards in guarded execution."""

    @pytest.mark.asyncio
    async def test_guard_loading_state(self) -> None:
        """guarded_execute should fail if kernel_state is LOADING."""
        from core.tools.registry_adapter import ExecutorToolRegistry

        registry = ExecutorToolRegistry(governance_enabled=False)
        agent = MockKernelAwareAgent(kernel_state="LOADING")

        result = await registry.guarded_execute(
            agent=agent,
            tool_id="test_tool",
            arguments={},
        )

        assert result.success is False
        assert "LOADING" in result.error

    @pytest.mark.asyncio
    async def test_guard_error_state(self) -> None:
        """guarded_execute should fail if kernel_state is ERROR."""
        from core.tools.registry_adapter import ExecutorToolRegistry

        registry = ExecutorToolRegistry(governance_enabled=False)
        agent = MockKernelAwareAgent(kernel_state="ERROR")

        result = await registry.guarded_execute(
            agent=agent,
            tool_id="test_tool",
            arguments={},
        )

        assert result.success is False
        assert "ERROR" in result.error

    @pytest.mark.asyncio
    async def test_guard_validating_state(self) -> None:
        """guarded_execute should fail if kernel_state is VALIDATING."""
        from core.tools.registry_adapter import ExecutorToolRegistry

        registry = ExecutorToolRegistry(governance_enabled=False)
        agent = MockKernelAwareAgent(kernel_state="VALIDATING")

        result = await registry.guarded_execute(
            agent=agent,
            tool_id="test_tool",
            arguments={},
        )

        assert result.success is False
        assert "VALIDATING" in result.error


# =============================================================================
# Edge Cases
# =============================================================================


class TestGuardedExecuteEdgeCases:
    """Edge case tests for guarded execution."""

    @pytest.mark.asyncio
    async def test_agent_without_kernel_state(self) -> None:
        """guarded_execute should fail if agent has no kernel_state."""
        from core.tools.registry_adapter import ExecutorToolRegistry

        registry = ExecutorToolRegistry(governance_enabled=False)

        class AgentWithoutKernelState:
            agent_id = "test"
            kernels = {"k1": {}}
            # No kernel_state attribute

        agent = AgentWithoutKernelState()

        result = await registry.guarded_execute(
            agent=agent,
            tool_id="test_tool",
            arguments={},
        )

        assert result.success is False

    @pytest.mark.asyncio
    async def test_agent_without_kernels_attribute(self) -> None:
        """guarded_execute should fail if agent has no kernels attribute."""
        from core.tools.registry_adapter import ExecutorToolRegistry

        registry = ExecutorToolRegistry(governance_enabled=False)

        class AgentWithoutKernels:
            agent_id = "test"
            kernel_state = "ACTIVE"
            # No kernels attribute

        agent = AgentWithoutKernels()

        result = await registry.guarded_execute(
            agent=agent,
            tool_id="test_tool",
            arguments={},
        )

        assert result.success is False

    @pytest.mark.asyncio
    async def test_empty_context(self, mock_agent: MockKernelAwareAgent) -> None:
        """guarded_execute should handle empty context."""
        from core.tools.registry_adapter import ExecutorToolRegistry

        registry = ExecutorToolRegistry(governance_enabled=False)
        registry.dispatch_tool_call = AsyncMock(
            return_value=ToolCallResult(
                call_id=uuid4(),
                tool_id="test_tool",
                success=True,
            )
        )

        result = await registry.guarded_execute(
            agent=mock_agent,
            tool_id="test_tool",
            arguments={},
            context=None,
        )

        assert result.success is True

    @pytest.mark.asyncio
    async def test_dispatch_failure_propagates(
        self, mock_agent: MockKernelAwareAgent
    ) -> None:
        """guarded_execute should propagate dispatch failures."""
        from core.tools.registry_adapter import ExecutorToolRegistry

        registry = ExecutorToolRegistry(governance_enabled=False)
        registry.dispatch_tool_call = AsyncMock(
            return_value=ToolCallResult(
                call_id=uuid4(),
                tool_id="test_tool",
                success=False,
                error="Tool execution failed",
            )
        )

        result = await registry.guarded_execute(
            agent=mock_agent,
            tool_id="test_tool",
            arguments={},
        )

        assert result.success is False
        assert "failed" in result.error.lower()


# =============================================================================
# Safety Constraint Tests
# =============================================================================


# =============================================================================
# Governance Engine Tests (T3.3)
# =============================================================================


class TestGovernanceEngineIntegration:
    """Tests for governance engine integration with guarded execution."""

    @pytest.mark.asyncio
    async def test_guarded_execution_invokes_governance_engine(self) -> None:
        """guarded_execute should invoke governance engine when attached."""
        from uuid import uuid4

        from core.governance.schemas import EvaluationResult, PolicyEffect
        from core.tools.registry_adapter import ExecutorToolRegistry

        registry = ExecutorToolRegistry(governance_enabled=True)

        # Create mock governance engine
        mock_engine = MagicMock()
        mock_engine.evaluate = AsyncMock(
            return_value=EvaluationResult(
                request_id=uuid4(),
                allowed=True,
                effect=PolicyEffect.ALLOW,
                policy_id="test-policy",
                policy_name="Test Policy",
                reason="Allowed by test policy",
            )
        )

        registry.set_governance_engine(mock_engine)
        registry.dispatch_tool_call = AsyncMock(
            return_value=ToolCallResult(
                call_id=uuid4(),
                tool_id="test_tool",
                success=True,
            )
        )

        agent = MockKernelAwareAgent()

        result = await registry.guarded_execute(
            agent=agent,
            tool_id="test_tool",
            arguments={"arg1": "value1"},
        )

        # Verify governance engine was called
        assert mock_engine.evaluate.called
        assert result.success is True

    @pytest.mark.asyncio
    async def test_guarded_execution_denies_on_governance_deny(self) -> None:
        """guarded_execute should deny when governance engine denies."""
        from uuid import uuid4

        from core.governance.schemas import EvaluationResult, PolicyEffect
        from core.tools.registry_adapter import ExecutorToolRegistry

        registry = ExecutorToolRegistry(governance_enabled=True)

        # Create mock governance engine that denies
        mock_engine = MagicMock()
        mock_engine.evaluate = AsyncMock(
            return_value=EvaluationResult(
                request_id=uuid4(),
                allowed=False,
                effect=PolicyEffect.DENY,
                policy_id="deny-policy",
                policy_name="Deny Policy",
                reason="Denied by governance policy",
            )
        )

        registry.set_governance_engine(mock_engine)

        agent = MockKernelAwareAgent()

        result = await registry.guarded_execute(
            agent=agent,
            tool_id="test_tool",
            arguments={},
        )

        assert result.success is False
        assert "governance denied" in result.error.lower()

    @pytest.mark.asyncio
    async def test_guarded_execution_continues_on_governance_error(self) -> None:
        """guarded_execute should continue if governance check fails."""
        from core.tools.registry_adapter import ExecutorToolRegistry

        registry = ExecutorToolRegistry(governance_enabled=True)

        # Create mock governance engine that raises exception
        mock_engine = MagicMock()
        mock_engine.evaluate = AsyncMock(
            side_effect=RuntimeError("Governance unavailable")
        )

        registry.set_governance_engine(mock_engine)
        registry.dispatch_tool_call = AsyncMock(
            return_value=ToolCallResult(
                call_id=uuid4(),
                tool_id="test_tool",
                success=True,
            )
        )

        agent = MockKernelAwareAgent()

        result = await registry.guarded_execute(
            agent=agent,
            tool_id="test_tool",
            arguments={},
        )

        # Should still succeed (governance error is soft failure)
        assert result.success is True


# =============================================================================
# Audit Trail Tests (T3.3)
# =============================================================================


class TestAuditTrailEmission:
    """Tests for audit trail emission with kernel metadata."""

    @pytest.mark.asyncio
    async def test_guarded_execution_emits_audit_with_kernel_metadata(
        self, mock_agent: MockKernelAwareAgent
    ) -> None:
        """guarded_execute should emit ToolAuditEntry with kernel metadata."""
        from core.tools.registry_adapter import ExecutorToolRegistry

        registry = ExecutorToolRegistry(governance_enabled=False)
        registry.dispatch_tool_call = AsyncMock(
            return_value=ToolCallResult(
                call_id=uuid4(),
                tool_id="test_tool",
                success=True,
                result={"data": "test"},
            )
        )

        # Add kernel metadata to agent
        mock_agent._kernel_hashes = {"kernel1": "abc123", "kernel2": "def456"}
        mock_agent._kernel_version = "1.0.0"

        # Patch log_tool_invocation to capture calls
        # Note: We patch importlib.import_module to return a mock module
        mock_log = AsyncMock()
        mock_audit_module = MagicMock()
        mock_audit_module.log_tool_invocation = mock_log
        mock_audit_module.ToolAuditEntry = MagicMock()

        with patch(
            "importlib.import_module",
            return_value=mock_audit_module,
        ):
            result = await registry.guarded_execute(
                agent=mock_agent,
                tool_id="test_tool",
                arguments={"arg1": "value1"},
                principal_id="test-principal",
            )

            assert result.success is True

            # Verify audit was logged
            assert mock_log.called
            call_args = mock_log.call_args
            assert call_args.kwargs["tool_id"] == "test_tool"
            assert call_args.kwargs["agent_id"] == "test-agent"
            assert call_args.kwargs["success"] is True

    @pytest.mark.asyncio
    async def test_guarded_execution_continues_on_audit_error(
        self, mock_agent: MockKernelAwareAgent
    ) -> None:
        """guarded_execute should continue if audit emission fails."""
        from core.tools.registry_adapter import ExecutorToolRegistry

        registry = ExecutorToolRegistry(governance_enabled=False)
        registry.dispatch_tool_call = AsyncMock(
            return_value=ToolCallResult(
                call_id=uuid4(),
                tool_id="test_tool",
                success=True,
            )
        )

        # Patch importlib.import_module to raise exception (simulates audit module failure)
        original_import = __import__("importlib").import_module

        def failing_import(name):
            if name == "memory.tool_audit":
                raise RuntimeError("Audit service unavailable")
            return original_import(name)

        with patch(
            "importlib.import_module",
            side_effect=failing_import,
        ):
            result = await registry.guarded_execute(
                agent=mock_agent,
                tool_id="test_tool",
                arguments={},
            )

            # Should still succeed (audit error is best-effort)
            assert result.success is True


class TestSafetyConstraints:
    """Tests for safety constraint enforcement."""

    @pytest.mark.asyncio
    async def test_partial_match_prohibited_action(self) -> None:
        """guarded_execute should block partial matches of prohibited actions."""
        from core.tools.registry_adapter import ExecutorToolRegistry

        registry = ExecutorToolRegistry(governance_enabled=False)

        agent = MockKernelAwareAgent(
            kernel_state="ACTIVE",
            kernels={"k1": {}},
            safety={"prohibited_actions": ["delete"]},
        )

        # Tool name contains "delete"
        result = await registry.guarded_execute(
            agent=agent,
            tool_id="file_delete_tool",
            arguments={},
        )

        assert result.success is False
        assert "delete" in result.error.lower()

    @pytest.mark.asyncio
    async def test_case_insensitive_prohibited_action(self) -> None:
        """guarded_execute should check prohibited actions case-insensitively."""
        from core.tools.registry_adapter import ExecutorToolRegistry

        registry = ExecutorToolRegistry(governance_enabled=False)

        agent = MockKernelAwareAgent(
            kernel_state="ACTIVE",
            kernels={"k1": {}},
            safety={"prohibited_actions": ["DELETE"]},
        )

        # Tool name in lowercase
        result = await registry.guarded_execute(
            agent=agent,
            tool_id="delete_file",
            arguments={},
        )

        assert result.success is False

    @pytest.mark.asyncio
    async def test_allowed_tool_not_blocked(
        self, mock_agent: MockKernelAwareAgent
    ) -> None:
        """guarded_execute should allow tools not in prohibited lists."""
        from core.tools.registry_adapter import ExecutorToolRegistry

        registry = ExecutorToolRegistry(governance_enabled=False)
        registry.dispatch_tool_call = AsyncMock(
            return_value=ToolCallResult(
                call_id=uuid4(),
                tool_id="safe_tool",
                success=True,
            )
        )

        mock_agent._behavioral = {"prohibited_tools": ["dangerous_tool"]}
        mock_agent._safety = {"prohibited_actions": ["delete"]}

        result = await registry.guarded_execute(
            agent=mock_agent,
            tool_id="safe_tool",
            arguments={},
        )

        assert result.success is True


# =============================================================================
# AgentExecutorService Kernel Enforcement Tests
# =============================================================================


class TestExecutorKernelEnforcement:
    """Tests for executor fail-closed kernel enforcement."""

    @pytest.mark.asyncio
    async def test_executor_blocks_when_kernel_agent_missing(self) -> None:
        """Executor should fail closed when guarded execution lacks kernel agent."""
        from core.agents.agent_instance import AgentInstance
        from core.agents.executor import AgentExecutorService

        tool_registry = MagicMock()
        tool_registry.guarded_execute = AsyncMock()
        tool_registry.dispatch_tool_call = AsyncMock()

        executor = AgentExecutorService(
            aios_runtime=MagicMock(),
            tool_registry=tool_registry,
            substrate_service=MagicMock(),
            agent_registry=MagicMock(),
        )

        executor._bind_memory_context = AsyncMock(return_value={})
        executor._emit_packet = AsyncMock()

        task = AgentTask(agent_id="test-agent")
        config = AgentConfig(
            agent_id="test-agent",
            tools=[ToolBinding(tool_id="test_tool")],
        )
        instance = AgentInstance(config=config, task=task)

        tool_call = ToolCallRequest(
            tool_id="test_tool",
            arguments={},
            task_id=task.id,
            iteration=0,
        )

        result = await executor._dispatch_tool_call(instance, tool_call)

        assert result.success is False
        assert result.error == "KERNEL_ENFORCEMENT_REQUIRED"
        tool_registry.dispatch_tool_call.assert_not_called()
        tool_registry.guarded_execute.assert_not_called()
