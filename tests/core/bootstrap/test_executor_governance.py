"""
L9 Core Agents - Executor Governance Tests
==========================================

Tests for governance validation in AgentExecutorService:
- Pre-execution authority validation
- Pre-execution safety validation
- Post-execution audit logging
- Blocked execution returns status="blocked"

Version: 1.0.0
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from core.agents.executor import AgentExecutorService
from core.agents.schemas import AgentConfig, AgentTask, AgentType


class TestExecutorGovernanceValidation:
    """Test governance validation in executor."""

    @pytest.fixture
    def mock_aios_runtime(self):
        """Mock AIOS runtime."""
        mock = AsyncMock()
        mock.execute_reasoning = AsyncMock(
            return_value=MagicMock(
                result_type="response",
                content="Test response",
                tokens_used=10,
            )
        )
        return mock

    @pytest.fixture
    def mock_tool_registry(self):
        """Mock tool registry.

        Note: get_approved_tools is synchronous (per ToolRegistryProtocol),
        dispatch_tool_call and get_relevant_tools are asynchronous.
        """
        mock = MagicMock()
        mock.get_approved_tools = MagicMock(return_value=[])
        mock.dispatch_tool_call = AsyncMock()
        # get_relevant_tools is async and returns empty by default (fail-closed: no fallback)
        mock.get_relevant_tools = AsyncMock(return_value=[])
        return mock

    @pytest.fixture
    def mock_substrate_service(self):
        """Mock substrate service."""
        mock = AsyncMock()
        mock.write_packet = AsyncMock()
        return mock

    @pytest.fixture
    def mock_agent_registry(self):
        """Mock agent registry."""
        mock = MagicMock()
        mock.get_agent_config = MagicMock(
            return_value=AgentConfig(
                agent_id="l-cto",
                personality_id="l-cto",
                system_prompt="Test prompt",
            )
        )
        mock.agent_exists = MagicMock(return_value=True)
        return mock

    @pytest.fixture
    def executor(
        self,
        mock_aios_runtime,
        mock_tool_registry,
        mock_substrate_service,
        mock_agent_registry,
    ):
        """Create executor with mocks."""
        return AgentExecutorService(
            aios_runtime=mock_aios_runtime,
            tool_registry=mock_tool_registry,
            substrate_service=mock_substrate_service,
            agent_registry=mock_agent_registry,
        )

    @pytest.mark.asyncio
    async def test_blocks_authority_violation(self, executor):
        """Executor should block tasks with authority violations."""
        task = AgentTask(
            id=uuid4(),
            agent_id="l-cto",
            agent_type=AgentType.ANALYST,
            payload={"message": "privilege_escalation attempt"},
        )

        result = await executor.start_agent_task(task)

        assert result.status == "blocked"
        assert "Authority violation" in result.error
        # Should not call AIOS runtime
        assert not executor._aios_runtime.execute_reasoning.called

    @pytest.mark.asyncio
    async def test_blocks_safety_violation(self, executor):
        """Executor should block tasks with safety violations."""
        task = AgentTask(
            id=uuid4(),
            agent_id="l-cto",
            agent_type=AgentType.ANALYST,
            payload={"message": "rm -rf /"},
        )

        result = await executor.start_agent_task(task)

        assert result.status == "blocked"
        assert "Safety violation" in result.error
        # Should not call AIOS runtime
        assert not executor._aios_runtime.execute_reasoning.called

    @pytest.mark.asyncio
    async def test_allows_valid_task(self, executor):
        """Executor should allow valid tasks."""
        task = AgentTask(
            id=uuid4(),
            agent_id="l-cto",
            agent_type=AgentType.ANALYST,
            payload={"message": "What is L9?"},
        )

        result = await executor.start_agent_task(task)

        # Should not be blocked
        assert result.status != "blocked"
        # Should call AIOS runtime
        assert executor._aios_runtime.execute_reasoning.called

    @pytest.mark.asyncio
    async def test_audit_logs_execution(self, executor):
        """Executor should audit log all executions."""
        task = AgentTask(
            id=uuid4(),
            agent_id="l-cto",
            agent_type=AgentType.ANALYST,
            payload={"message": "Test message"},
        )

        with patch("core.governance.validation.audit_log") as mock_audit:
            await executor.start_agent_task(task)

            # Verify audit log was called
            assert mock_audit.called
            call_kwargs = mock_audit.call_args.kwargs
            # audit_log uses keyword arguments
            assert call_kwargs.get("agent_id") == "l-cto"
            assert "Test message" in call_kwargs.get("action", "")
            assert "metadata" in call_kwargs

    @pytest.mark.asyncio
    async def test_governance_validation_blocks_on_import_error(self, executor):
        """If governance validation unavailable, execution is BLOCKED (fail-closed)."""
        task = AgentTask(
            id=uuid4(),
            agent_id="l-cto",
            agent_type=AgentType.ANALYST,
            payload={"message": "Test"},
        )

        # Mock ImportError for governance validation
        # validate_authority is imported inside the executor method, so patch the source
        with patch(
            "core.governance.validation.validate_authority",
            side_effect=ImportError("Module not found"),
        ):
            result = await executor.start_agent_task(task)

            # Should BLOCK (fail-closed) - governance validation is required
            assert result.status == "blocked"
            assert "Governance validation unavailable" in result.error
            # Should NOT call AIOS runtime
            assert not executor._aios_runtime.execute_reasoning.called


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
