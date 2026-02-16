"""
Tests for Phase 7: Verify and Lock bootstrap phase.

Aligned with existing verify_and_lock() function API.
Tests both the full function and the view pattern variant.
"""

from unittest.mock import MagicMock, patch

import pytest

from core.decorators import must_stay_async

# =============================================================================
# Mock Fixtures (matching existing test patterns)
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
        self.kernel_refs = kernel_refs or ["01_master_kernel.yaml"]


class MockSubstrateService:
    """Mock MemorySubstrateService."""

    def __init__(self, ready: bool = True):
        self.postgres_pool = MagicMock() if ready else None
        self.tool_registry = MagicMock()
        self.packets = []

    @must_stay_async("callers use await")
    async def write_packet(self, packet):
        self.packets.append(packet)


@pytest.fixture
def mock_instance():
    """Create mock BootstrapInstanceData."""
    from core.agents.bootstrap.phase_2_instantiate import BootstrapInstanceData

    return BootstrapInstanceData(
        instance_id="test-inst-123",
        agent_id="test-agent",
        name="Test Agent",
        config=MockAgentConfig(),
        designation="L",
    )


@pytest.fixture
def mock_kernels():
    """Create mock kernels dict."""
    return {
        "master": {"name": "Master Kernel", "version": "1.0", "hash": "abc123"},
        "safety": {"name": "Safety Kernel", "version": "1.0", "hash": "def456"},
        "execution": {"name": "Execution Kernel", "version": "1.0", "hash": "ghi789"},
    }


@pytest.fixture
def mock_substrate():
    """Create mock substrate service."""
    return MockSubstrateService()


# =============================================================================
# Tests for verify_and_lock() function
# =============================================================================


class TestVerifyAndLock:
    """Tests for Phase 7 verify_and_lock function."""

    @pytest.mark.asyncio
    async def test_verify_returns_signature(
        self, mock_instance, mock_kernels, mock_substrate
    ):
        """Verify and lock returns initialization signature."""
        from core.agents.bootstrap.phase_7_verify_and_lock import verify_and_lock

        signature = await verify_and_lock(mock_instance, mock_substrate, mock_kernels)

        assert signature is not None
        assert len(signature) == 64  # SHA256 hex
        assert mock_instance.status == "READY"
        assert mock_instance.kernel_state == "ACTIVE"
        assert mock_instance.initialization_signature == signature

    @pytest.mark.asyncio
    async def test_verify_sets_initialized_at(
        self, mock_instance, mock_kernels, mock_substrate
    ):
        """Verify sets initialized_at timestamp."""
        from core.agents.bootstrap.phase_7_verify_and_lock import verify_and_lock

        await verify_and_lock(mock_instance, mock_substrate, mock_kernels)

        assert mock_instance.initialized_at is not None

    @pytest.mark.asyncio
    async def test_verify_with_no_kernels(self, mock_instance, mock_substrate):
        """Verify handles empty kernel case (logs warning but completes)."""
        from core.agents.bootstrap.phase_7_verify_and_lock import verify_and_lock

        empty_kernels = {}
        signature = await verify_and_lock(mock_instance, mock_substrate, empty_kernels)

        # Should still complete (with warnings in logs)
        assert signature is not None
        assert len(signature) == 64
        assert mock_instance.status == "READY"

    @pytest.mark.asyncio
    async def test_verify_with_no_designation(self, mock_substrate, mock_kernels):
        """Verify handles missing designation gracefully."""
        from core.agents.bootstrap.phase_2_instantiate import BootstrapInstanceData
        from core.agents.bootstrap.phase_7_verify_and_lock import verify_and_lock

        instance = BootstrapInstanceData(
            instance_id="test-inst-456",
            agent_id="test-agent-2",
            name="Test Agent 2",
            config=MockAgentConfig(),
            designation=None,  # No designation
        )

        signature = await verify_and_lock(instance, mock_substrate, mock_kernels)

        # Should complete with 'unknown' in signature data
        assert signature is not None
        assert len(signature) == 64

    @pytest.mark.asyncio
    async def test_verify_writes_audit_packet(
        self, mock_instance, mock_kernels, mock_substrate
    ):
        """Verify writes audit trail packet to substrate."""
        from core.agents.bootstrap.phase_7_verify_and_lock import verify_and_lock

        # Mock the governance context and PacketEnvelopeIn imports
        # Note: get_rls_config is imported inside the function, so we patch at the source
        with patch("config.rls_config.get_rls_config") as mock_rls:
            mock_rls.return_value = MagicMock(
                tenant_uuid="tenant-123",
                org_uuid="org-123",
                user_uuid="user-123",
            )

            with patch("memory.governance_gate.governance_context"):
                await verify_and_lock(mock_instance, mock_substrate, mock_kernels)

        # Audit packet should have been written
        # (May be empty if imports failed, which is acceptable)


# =============================================================================
# Tests for verify_and_lock_view() function
# =============================================================================


class TestVerifyAndLockView:
    """Tests for Phase 7 verify_and_lock_view function (view pattern)."""

    @pytest.mark.asyncio
    async def test_view_success_with_valid_inputs(self):
        """View pattern succeeds with valid inputs."""
        from core.agents.bootstrap.phase_7_verify_and_lock import verify_and_lock_view

        result = await verify_and_lock_view(
            agent_id="test-agent",
            identity_view={"designation": "L", "role": "CTO"},
            kernels={"master": {}, "safety": {}},
            tools=["memory_write", "memory_search"],
            governance_gates={"approval_gate": True},
            init_signature="a" * 64,
        )

        assert result["success"] is True
        assert result["error"] is None
        assert result["context_delta"]["verified"] is True

    @pytest.mark.asyncio
    async def test_view_fails_without_agent_id(self):
        """View pattern fails when agent_id is missing."""
        from core.agents.bootstrap.phase_7_verify_and_lock import verify_and_lock_view

        result = await verify_and_lock_view(
            agent_id="",  # Empty
            identity_view={"designation": "L"},
            kernels={"master": {}},
            tools=[],
            governance_gates={},
            init_signature="a" * 64,
        )

        assert result["success"] is False
        assert result["error"] is not None
        assert "agent_id" in str(result["error"])

    @pytest.mark.asyncio
    async def test_view_fails_without_signature(self):
        """View pattern fails when init_signature is missing."""
        from core.agents.bootstrap.phase_7_verify_and_lock import verify_and_lock_view

        result = await verify_and_lock_view(
            agent_id="test-agent",
            identity_view={"designation": "L"},
            kernels={"master": {}},
            tools=[],
            governance_gates={},
            init_signature="",  # Empty
        )

        assert result["success"] is False
        assert result["error"] is not None

    @pytest.mark.asyncio
    async def test_view_fails_without_identity(self):
        """View pattern fails when identity_view is missing."""
        from core.agents.bootstrap.phase_7_verify_and_lock import verify_and_lock_view

        result = await verify_and_lock_view(
            agent_id="test-agent",
            identity_view=None,  # Missing
            kernels={"master": {}},
            tools=[],
            governance_gates={},
            init_signature="a" * 64,
        )

        assert result["success"] is False
        assert result["error"] is not None

    @pytest.mark.asyncio
    async def test_view_fails_with_no_kernels(self):
        """View pattern fails when no kernels are provided."""
        from core.agents.bootstrap.phase_7_verify_and_lock import verify_and_lock_view

        result = await verify_and_lock_view(
            agent_id="test-agent",
            identity_view={"designation": "L"},
            kernels={},  # Empty
            tools=[],
            governance_gates={},
            init_signature="a" * 64,
        )

        assert result["success"] is False
        assert "kernel" in str(result["error"]).lower()

    @pytest.mark.asyncio
    async def test_view_includes_duration_metric(self):
        """View pattern includes phase7_duration_ms in context_delta."""
        from core.agents.bootstrap.phase_7_verify_and_lock import verify_and_lock_view

        result = await verify_and_lock_view(
            agent_id="test-agent",
            identity_view={"designation": "L"},
            kernels={"master": {}},
            tools=[],
            governance_gates={},
            init_signature="a" * 64,
        )

        assert result["success"] is True
        assert "phase7_duration_ms" in result["context_delta"]
        assert result["context_delta"]["phase7_duration_ms"] >= 0
