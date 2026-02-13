"""
Agent Bootstrap Phase Unit Tests
================================

Unit tests for the 7-phase atomic agent bootstrap ceremony.
Tests each phase in isolation. Neo4j operations are naturally skipped
when the client isn't available (offline mode).

Version: 2.2.0 - Simplified for offline testing (no Neo4j mocking needed)
"""

from unittest.mock import MagicMock
from uuid import UUID

import pytest
import structlog

from core.decorators import must_stay_async

logger = structlog.get_logger(__name__)


# =============================================================================
# Mock Fixtures (shared across tests)
# =============================================================================


class MockAgentConfig:
    """Mock AgentConfig for testing."""

    def __init__(
        self,
        agent_id: str = "test-agent",
        name: str = "Test Agent",
        kernel_refs: list | None = None,
    ):
        self.agent_id = agent_id
        self.name = name
        self.kernel_refs = kernel_refs or [
            "01_master_kernel.yaml",
            "02_identity_kernel.yaml",
            "07_execution_kernel.yaml",
            "08_safety_kernel.yaml",
        ]


class MockPostgresConnection:
    """Mock postgres connection."""

    @must_stay_async("callers use await")
    async def execute(self, query: str):
        return None

    @must_stay_async("callers use await")
    async def __aenter__(self):
        return self

    @must_stay_async("callers use await")
    async def __aexit__(self, *args):
        pass


class MockPostgresPool:
    """Mock postgres pool."""

    def acquire(self):
        return MockPostgresConnection()


class MockSubstrateService:
    """Mock MemorySubstrateService."""

    def __init__(self, ready: bool = True):
        self.postgres_pool = MockPostgresPool() if ready else None
        self.tool_registry = MagicMock()
        self.packets = []

    @must_stay_async("callers use await")
    async def write_packet(self, packet):
        self.packets.append(packet)


# =============================================================================
# Phase 0: Validate Blueprint
# =============================================================================


class TestPhase0Validate:
    """Tests for Phase 0: Validate Agent Blueprint"""

    @pytest.mark.asyncio
    async def test_validate_agent_config_success(self):
        """Valid AgentConfig with kernels passes validation."""
        from core.agents.bootstrap.phase_0_validate import validate_agent_blueprint

        config = MockAgentConfig()
        mock_substrate = MockSubstrateService()

        # Neo4j will naturally return None in test environment (offline mode)
        success, error = await validate_agent_blueprint(config, mock_substrate)

        # Should succeed (with Neo4j offline, it's a non-fatal warning)
        assert success is True
        assert error == ""

    @pytest.mark.asyncio
    async def test_validate_agent_config_missing_id(self):
        """AgentConfig without agent_id fails validation."""
        from core.agents.bootstrap.phase_0_validate import validate_agent_blueprint

        config = MockAgentConfig(agent_id="", name="Test Agent")
        mock_substrate = MockSubstrateService()

        success, error = await validate_agent_blueprint(config, mock_substrate)

        assert success is False
        assert "agent_id" in error.lower() or "missing" in error.lower()

    @pytest.mark.asyncio
    async def test_validate_agent_config_missing_name(self):
        """AgentConfig without name fails validation."""
        from core.agents.bootstrap.phase_0_validate import validate_agent_blueprint

        config = MockAgentConfig(agent_id="test", name="")
        mock_substrate = MockSubstrateService()

        success, _error = await validate_agent_blueprint(config, mock_substrate)

        assert success is False


# =============================================================================
# Phase 1: Load Kernels
# =============================================================================


class TestPhase1LoadKernels:
    """Tests for Phase 1: Load Kernels"""

    @pytest.mark.asyncio
    async def test_load_kernels_returns_dict(self):
        """load_and_parse_kernels returns a dict."""
        from core.agents.bootstrap.phase_1_load_kernels import load_and_parse_kernels

        # Use a nonexistent path - function should handle gracefully
        kernels = await load_and_parse_kernels("/tmp/nonexistent")

        # Should return empty dict for nonexistent path
        assert isinstance(kernels, dict)

    @pytest.mark.asyncio
    async def test_load_kernels_real_path(self):
        """Kernels load from real kernel directory if available."""
        from pathlib import Path

        from core.agents.bootstrap.phase_1_load_kernels import load_and_parse_kernels

        kernel_dir = "private/kernels/00_system"

        if Path(kernel_dir).exists():
            kernels = await load_and_parse_kernels(kernel_dir)
            assert isinstance(kernels, dict)
            # If directory exists and has YAML files, we should get some kernels
        else:
            pytest.skip("Kernel directory not available")


# =============================================================================
# Phase 2: Instantiate Agent
# =============================================================================


class TestPhase2Instantiate:
    """Tests for Phase 2: Instantiate Agent"""

    @pytest.mark.asyncio
    async def test_instantiate_agent_creates_instance(self):
        """Agent instance is created with valid UUID."""
        from core.agents.bootstrap.phase_2_instantiate import (
            BootstrapInstanceData,
            instantiate_agent,
        )

        config = MockAgentConfig()
        mock_substrate = MockSubstrateService()

        # Neo4j naturally returns None in test env
        instance = await instantiate_agent(config, mock_substrate)

        assert instance is not None
        assert isinstance(instance, BootstrapInstanceData)
        assert instance.agent_id == "test-agent"
        assert instance.name == "Test Agent"
        # Verify instance_id is valid UUID
        UUID(instance.instance_id)

    @pytest.mark.asyncio
    async def test_instantiate_agent_sets_initial_state(self):
        """Agent instance has correct initial state."""
        from core.agents.bootstrap.phase_2_instantiate import instantiate_agent

        config = MockAgentConfig(agent_id="test-123", name="Test 123")
        mock_substrate = MockSubstrateService()

        instance = await instantiate_agent(config, mock_substrate)

        assert instance.kernel_state == "LOADING"
        assert instance.status == "INITIALIZING"


# =============================================================================
# Phase 3: Bind Kernels
# =============================================================================


class TestPhase3BindKernels:
    """Tests for Phase 3: Bind Kernels"""

    @pytest.mark.asyncio
    @must_stay_async("callers use await")
    async def test_bind_kernels_sets_bound_state(self):
        """Binding kernels updates instance state to BOUND."""
        from core.agents.bootstrap.phase_2_instantiate import BootstrapInstanceData
        from core.agents.bootstrap.phase_3_bind_kernels import bind_kernels_to_agent

        instance = BootstrapInstanceData(
            instance_id="test-inst-123",
            agent_id="test-agent",
            name="Test Agent",
            config=MockAgentConfig(),
        )

        kernels = {
            "master": {"name": "Master", "version": "1.0", "hash": "abc"},
            "identity": {"name": "Identity", "version": "1.0", "hash": "def"},
        }

        mock_substrate = MockSubstrateService()

        # Neo4j naturally returns None - function handles gracefully
        await bind_kernels_to_agent(instance, kernels, mock_substrate)

        # Verify kernel state was updated
        assert instance.kernel_state == "BOUND"


# =============================================================================
# Phase 4: Load Identity
# =============================================================================


class TestPhase4LoadIdentity:
    """Tests for Phase 4: Load Identity"""

    @pytest.mark.asyncio
    async def test_load_identity_sets_defaults(self):
        """Identity uses defaults when file not found."""
        from core.agents.bootstrap.phase_2_instantiate import BootstrapInstanceData
        from core.agents.bootstrap.phase_4_load_identity import load_identity_persona

        instance = BootstrapInstanceData(
            instance_id="test-inst-123",
            agent_id="test-agent",
            name="Test Agent",
            config=MockAgentConfig(),
        )

        mock_substrate = MockSubstrateService()

        # No identity file exists for test-agent, should use defaults
        await load_identity_persona(instance, mock_substrate)

        # Verify defaults were set
        assert instance.designation == "test-agent"
        assert instance.role == "Agent"


# =============================================================================
# Phase 5: Bind Tools
# =============================================================================


class TestPhase5BindTools:
    """Tests for Phase 5: Bind Tools"""

    @pytest.mark.asyncio
    async def test_bind_tools_completes(self):
        """Tool binding completes without error."""
        from core.agents.bootstrap.phase_2_instantiate import BootstrapInstanceData
        from core.agents.bootstrap.phase_5_bind_tools import bind_tools_and_capabilities

        instance = BootstrapInstanceData(
            instance_id="test-inst-123",
            agent_id="test-agent",
            name="Test Agent",
            config=MockAgentConfig(),
        )

        mock_substrate = MockSubstrateService()

        # Should complete without error (Neo4j offline is handled gracefully)
        await bind_tools_and_capabilities(instance, mock_substrate)


# =============================================================================
# Phase 6: Wire Governance
# =============================================================================


class TestPhase6WireGovernance:
    """Tests for Phase 6: Wire Governance"""

    @pytest.mark.asyncio
    async def test_wire_governance_completes(self):
        """Governance wiring completes without error."""
        from core.agents.bootstrap.phase_2_instantiate import BootstrapInstanceData
        from core.agents.bootstrap.phase_6_wire_governance import wire_governance_gates

        instance = BootstrapInstanceData(
            instance_id="test-inst-123",
            agent_id="test-agent",
            name="Test Agent",
            config=MockAgentConfig(),
        )

        kernels = {"safety": {"name": "Safety", "version": "1.0"}}
        mock_substrate = MockSubstrateService()

        # Should complete without error
        await wire_governance_gates(instance, mock_substrate, kernels)


# =============================================================================
# Phase 7: Verify and Lock
# =============================================================================


class TestPhase7VerifyAndLock:
    """Tests for Phase 7: Verify and Lock"""

    @pytest.mark.asyncio
    async def test_verify_returns_signature(self):
        """Verify and lock returns initialization signature."""
        from core.agents.bootstrap.phase_2_instantiate import BootstrapInstanceData
        from core.agents.bootstrap.phase_7_verify_and_lock import verify_and_lock

        instance = BootstrapInstanceData(
            instance_id="test-inst-123",
            agent_id="test-agent",
            name="Test Agent",
            config=MockAgentConfig(),
            designation="L",
        )

        kernels = {
            "master": {"name": "Master"},
            "safety": {"name": "Safety"},
        }
        mock_substrate = MockSubstrateService()

        signature = await verify_and_lock(instance, mock_substrate, kernels)

        assert signature is not None
        assert len(signature) == 64  # SHA256 hex
        assert instance.status == "READY"
        assert instance.kernel_state == "ACTIVE"
        assert instance.initialization_signature == signature

    @pytest.mark.asyncio
    async def test_verify_with_no_kernels(self):
        """Verify handles empty kernel case."""
        from core.agents.bootstrap.phase_2_instantiate import BootstrapInstanceData
        from core.agents.bootstrap.phase_7_verify_and_lock import verify_and_lock

        instance = BootstrapInstanceData(
            instance_id="test-inst-123",
            agent_id="test-agent",
            name="Test Agent",
            config=MockAgentConfig(),
        )

        kernels = {}  # No kernels
        mock_substrate = MockSubstrateService()

        signature = await verify_and_lock(instance, mock_substrate, kernels)

        # Should still complete (with warnings in logs)
        assert signature is not None
        assert len(signature) == 64


# =============================================================================
# Orchestrator Tests
# =============================================================================


class TestBootstrapOrchestrator:
    """Tests for the bootstrap orchestrator"""

    @pytest.mark.asyncio
    @must_stay_async("callers use await")
    async def test_orchestrator_import(self):
        """Orchestrator can be imported without errors."""
        from core.agents.bootstrap.orchestrator import AgentBootstrapOrchestrator

        assert AgentBootstrapOrchestrator is not None

    @pytest.mark.asyncio
    @must_stay_async("callers use await")
    async def test_orchestrator_init(self):
        """Orchestrator can be instantiated."""
        from core.agents.bootstrap.orchestrator import AgentBootstrapOrchestrator

        mock_substrate = MockSubstrateService()
        orchestrator = AgentBootstrapOrchestrator(mock_substrate)

        assert orchestrator.substrate is mock_substrate

    @pytest.mark.asyncio
    async def test_orchestrator_phase_failure_raises(self):
        """Orchestrator raises on phase failure."""
        from core.agents.bootstrap.orchestrator import AgentBootstrapOrchestrator

        config = MockAgentConfig(agent_id="", name="Test")  # Invalid - empty ID
        mock_substrate = MockSubstrateService()

        orchestrator = AgentBootstrapOrchestrator(mock_substrate)

        with pytest.raises(RuntimeError) as exc_info:
            await orchestrator.bootstrap_agent(config)

        assert (
            "Phase 0" in str(exc_info.value) or "failed" in str(exc_info.value).lower()
        )
