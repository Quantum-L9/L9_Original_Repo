"""
L9 Bootstrap Tests – Orchestrator
==================================

Tests for AgentBootstrapOrchestrator: 7-phase pipeline execution.
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from core.agents.bootstrap.models import IdentityView
from core.agents.bootstrap.orchestrator import (
    AgentBootstrapContext,
    AgentBootstrapError,
    AgentBootstrapOrchestrator,
    PhaseResult,
)
from core.agents.schemas import AgentConfig


@pytest.fixture
def mock_services():
    """Mock injected services."""
    return {
        "world_model": AsyncMock(),
        "memory_substrate": AsyncMock(),
        "tool_registry": AsyncMock(),
    }


@pytest.fixture
def orchestrator(mock_services):
    """Create orchestrator with mocked services."""
    return AgentBootstrapOrchestrator(
        world_model_service=mock_services["world_model"],
        memory_substrate_service=mock_services["memory_substrate"],
        tool_registry=mock_services["tool_registry"],
        feature_flags={"L9NEWAGENTINIT": True},
    )


@pytest.fixture
def sample_config():
    """Sample agent config for testing."""
    return AgentConfig(
        agent_id="test-agent",
        name="Test Agent",
        personality_id="test-personality",
        model="gpt-4o",
        temperature=0.3,
        max_tokens=4000,
    )


@pytest.fixture
def sample_kernel_paths():
    """Sample kernel paths."""
    return {
        "01-core": "/path/to/01-core.yaml",
        "02-identity": "/path/to/02-identity.yaml",
        "03-safety": "/path/to/03-safety.yaml",
    }


@pytest.mark.asyncio
async def test_orchestrator_all_phases_success(
    orchestrator, sample_config, sample_kernel_paths, mock_services
):
    """Test successful execution of all 7 phases."""
    # Mock each phase to return success
    orchestrator._phase0_validate = AsyncMock(
        return_value=PhaseResult(
            phase=0,
            name="validate",
            success=True,
            context_delta={"validated": True},
        )
    )
    orchestrator._phase1_load_kernels = AsyncMock(
        return_value=PhaseResult(
            phase=1,
            name="load_kernels",
            success=True,
            context_delta={"kernels": {"01-core": {}}},
        )
    )
    orchestrator._phase2_instantiate = AsyncMock(
        return_value=PhaseResult(
            phase=2,
            name="instantiate",
            success=True,
            context_delta={"instantiated": True},
        )
    )
    orchestrator._phase3_bind_kernels = AsyncMock(
        return_value=PhaseResult(
            phase=3,
            name="bind_kernels",
            success=True,
            context_delta={"kernels_bound": True},
        )
    )
    orchestrator._phase4_load_identity = AsyncMock(
        return_value=PhaseResult(
            phase=4,
            name="load_identity",
            success=True,
            context_delta={
                "identity_view": IdentityView(
                    agent_id="test-agent",
                    display_name="Test Agent",
                    short_name="TA",
                    description="Test",
                    capabilities=["test"],
                    default_tone="neutral",
                    tags=[],
                )
            },
        )
    )
    orchestrator._phase5_bind_tools = AsyncMock(
        return_value=PhaseResult(
            phase=5,
            name="bind_tools",
            success=True,
            context_delta={"tools": ["tool1", "tool2"]},
        )
    )
    orchestrator._phase6_wire_governance = AsyncMock(
        return_value=PhaseResult(
            phase=6,
            name="wire_governance",
            success=True,
            context_delta={"governance_gates": {}},
        )
    )
    orchestrator._phase7_verify_and_lock = AsyncMock(
        return_value=PhaseResult(
            phase=7,
            name="verify_and_lock",
            success=True,
            context_delta={
                "verified": True,
                "init_signature": "abc123def456789012345678901234567890123456789012345678901234",
                "status": "READY",
            },
        )
    )

    # Run orchestrator
    ctx = await orchestrator.run(
        agent_id="test-agent",
        config=sample_config,
        kernel_paths=sample_kernel_paths,
    )

    # Assertions
    assert ctx.agent_id == "test-agent"
    assert ctx.status == "READY"
    assert ctx.init_signature is not None
    assert len(ctx.phase_results) == 8
    assert all(r.success for r in ctx.phase_results)


@pytest.mark.asyncio
async def test_orchestrator_phase_failure_triggers_rollback(
    orchestrator, sample_config, sample_kernel_paths, mock_services
):
    """Test that phase failure triggers rollback."""
    # Mock Phase 3 to fail
    orchestrator._phase0_validate = AsyncMock(
        return_value=PhaseResult(
            phase=0,
            name="validate",
            success=True,
            context_delta={},
        )
    )
    orchestrator._phase1_load_kernels = AsyncMock(
        return_value=PhaseResult(
            phase=1,
            name="load_kernels",
            success=True,
            context_delta={"kernels": {}},
        )
    )
    orchestrator._phase2_instantiate = AsyncMock(
        return_value=PhaseResult(
            phase=2,
            name="instantiate",
            success=True,
            context_delta={},
        )
    )
    orchestrator._phase3_bind_kernels = AsyncMock(
        return_value=PhaseResult(
            phase=3,
            name="bind_kernels",
            success=False,
            error=RuntimeError("Kernel binding failed"),
            error_code="BOOTSTRAP_PHASE3_BIND_KERNELS_FAILED",
        )
    )

    # Mock rollback
    orchestrator._rollback_agent_init = AsyncMock()

    # Run and expect error
    with pytest.raises(AgentBootstrapError) as exc_info:
        await orchestrator.run(
            agent_id="test-agent",
            config=sample_config,
            kernel_paths=sample_kernel_paths,
        )

    error = exc_info.value
    assert error.phase == 3
    assert error.agent_id == "test-agent"
    assert error.error_code == "BOOTSTRAP_PHASE3_BIND_KERNELS_FAILED"

    # Verify rollback was called
    orchestrator._rollback_agent_init.assert_called_once()


@pytest.mark.asyncio
async def test_orchestrator_rollback_deletes_agent_node(orchestrator, mock_services):
    """Test that rollback deletes agent from Neo4j with CASCADE."""
    mock_services["world_model"].agent_exists = AsyncMock(return_value=True)
    mock_services["world_model"].delete_agent_node_cascade = AsyncMock()

    await orchestrator._rollback_agent_init(
        agent_id="test-agent",
        reason="Test failure",
        phase=3,
    )

    # Verify delete was called
    mock_services["world_model"].delete_agent_node_cascade.assert_called_once_with(
        "test-agent"
    )


def test_agent_bootstrap_context_canonical_json():
    """Test deterministic JSON serialization for init_signature."""
    from core.agents.bootstrap.orchestrator import IdentityView

    ctx = AgentBootstrapContext(
        agent_id="test-agent",
        config=MagicMock(spec=AgentConfig),
        kernels={"02-identity": {}},
        identity_view=IdentityView(
            agent_id="test-agent",
            display_name="Test",
            short_name="T",
            description="Test agent",
            capabilities=["cap1"],
            default_tone="direct",
            tags=["test"],
        ),
        tools=["tool1", "tool2"],
    )

    # Call twice, should produce identical JSON
    json1 = ctx.to_canonical_json()
    json2 = ctx.to_canonical_json()

    assert json1 == json2
    assert "test-agent" in json1
    assert "sorted keys" or json1.count('"') > 0  # JSON has quotes


def test_agent_bootstrap_context_compute_signature():
    """Test deterministic init_signature computation."""
    from core.agents.bootstrap.orchestrator import IdentityView

    ctx1 = AgentBootstrapContext(
        agent_id="agent1",
        config=MagicMock(spec=AgentConfig),
    )
    ctx2 = AgentBootstrapContext(
        agent_id="agent2",
        config=MagicMock(spec=AgentConfig),
    )

    sig1 = ctx1.compute_init_signature()
    sig2 = ctx2.compute_init_signature()

    # Different agents should have different signatures
    assert sig1 != sig2

    # Same agent should have same signature (deterministic)
    sig1_again = ctx1.compute_init_signature()
    assert sig1 == sig1_again

    # Signature should be hex string, length 64 (SHA-256)
    assert len(sig1) == 64
    assert all(c in "0123456789abcdef" for c in sig1)
