"""
L9 Agent Executor Tests – Bootstrap Bridge
===========================================

Tests for AgentExecutorService.bootstrap_agent_from_query().
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from core.agents.bootstrap.models import IdentityView
from core.agents.bootstrap.orchestrator import AgentBootstrapError
from core.agents.executor import AgentExecutorService
from core.agents.schemas import AgentConfig
from core.decorators import must_stay_async


@pytest.fixture
def mock_executor_services():
    """Mock services for AgentExecutorService."""
    return {
        "aios_runtime": AsyncMock(),
        "tool_registry": AsyncMock(),
        "substrate_service": AsyncMock(),
        "agent_registry": AsyncMock(),
    }


@pytest.fixture
def executor(mock_executor_services):
    """Create AgentExecutorService."""
    return AgentExecutorService(
        aios_runtime=mock_executor_services["aios_runtime"],
        tool_registry=mock_executor_services["tool_registry"],
        substrate_service=mock_executor_services["substrate_service"],
        agent_registry=mock_executor_services["agent_registry"],
    )


@pytest.mark.asyncio
@pytest.mark.skip(reason="bootstrap_agent_from_query not yet implemented on executor")
@must_stay_async("callers use await")
async def test_bootstrap_agent_from_query_success(executor):
    """Test successful bootstrap from query."""
    with patch(
        "core.agents.executor.AgentBootstrapOrchestrator"
    ) as mock_orchestrator_class:
        # Mock orchestrator
        mock_orchestrator = AsyncMock()

        # Mock bootstrap context
        mock_ctx = MagicMock()
        mock_ctx.agent_id = "agent-test1234"
        mock_ctx.config = MagicMock(spec=AgentConfig)
        mock_ctx.identity_view = IdentityView(
            agent_id="agent-test1234",
            display_name="Code Reviewer",
            short_name="CR",
            description="Handles code review tasks",
            capabilities=["code_review"],
            default_tone="constructive",
            tags=[],
        )
        mock_ctx.kernels = {"02-identity": {}}
        mock_ctx.tools = ["github_pr_review"]
        mock_ctx.init_signature = "abc123def456"
        mock_ctx.status = "READY"

        mock_orchestrator.run = AsyncMock(return_value=mock_ctx)
        mock_orchestrator_class.return_value = mock_orchestrator

        # Run bootstrap
        agent = await executor.bootstrap_agent_from_query(
            query="create an agent to handle code review tasks",
            kernel_paths={},
        )

        # Assertions
        assert agent is not None
        assert agent.agent_id == "agent-test1234"
        assert agent.status == "READY"
        assert agent.init_signature == "abc123def456"
        assert isinstance(agent.identity, IdentityView)

        # Verify orchestrator was called
        mock_orchestrator_class.assert_called_once()
        mock_orchestrator.run.assert_called_once()


@pytest.mark.asyncio
@pytest.mark.skip(reason="bootstrap_agent_from_query not yet implemented on executor")
async def test_bootstrap_agent_from_query_orchestrator_failure(executor):
    """Test that orchestrator failure is propagated."""
    with patch(
        "core.agents.executor.AgentBootstrapOrchestrator"
    ) as mock_orchestrator_class:
        mock_orchestrator = AsyncMock()
        mock_orchestrator.run = AsyncMock(
            side_effect=AgentBootstrapError(
                phase=3,
                phase_name="bind_kernels",
                agent_id="agent-test",
                root_cause=RuntimeError("Kernel binding failed"),
            )
        )
        mock_orchestrator_class.return_value = mock_orchestrator

        # Run and expect error
        with pytest.raises(AgentBootstrapError) as exc_info:
            await executor.bootstrap_agent_from_query(
                query="create an agent",
                kernel_paths={},
            )

        error = exc_info.value
        assert error.phase == 3
        assert error.agent_id == "agent-test"


@pytest.mark.skip(reason="_parse_bootstrap_query not yet implemented on executor")
def test_executor_parse_bootstrap_query():
    """Test query parsing for agent blueprint extraction."""
    executor = MagicMock(spec=AgentExecutorService)
    executor._parse_bootstrap_query = (
        AgentExecutorService._parse_bootstrap_query.__get__(
            executor, AgentExecutorService
        )
    )

    # Test code review extraction
    blueprint = executor._parse_bootstrap_query(
        "create an agent to handle code review tasks"
    )
    assert blueprint["agent_id"].startswith("agent-")
    assert "code review" in blueprint["config"].purpose.lower()
    assert blueprint["config"].agent_id == blueprint["agent_id"]
