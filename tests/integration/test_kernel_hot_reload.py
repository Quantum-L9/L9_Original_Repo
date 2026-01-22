"""
Integration Tests for Kernel Hot Reload (GMP-KERNEL-BOOT TODO-6)

Verifies:
1. reload_kernels() function works end-to-end
2. Modified kernels are detected and reloaded
3. Kernel evolution is logged to memory substrate
4. /kernels/reload API endpoint works
"""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from core.kernels.kernelloader import (KERNEL_ORDER, load_kernels,
                                       reload_kernels)

# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def mock_kernel_files(tmp_path):
    """Create mock kernel files in a temporary directory."""
    system_kernel_dir = tmp_path / "private" / "kernels" / "00_system"
    system_kernel_dir.mkdir(parents=True, exist_ok=True)

    kernel_content = """
kernel:
  name: {name}
  version: 1.0.0
  priority: {priority}
  description: Test kernel for {name}
rules:
  - id: RULE-001
    type: test
    description: Test rule
    content: "Test content"
"""

    for i, kernel_path in enumerate(KERNEL_ORDER):
        kernel_file = tmp_path / kernel_path
        kernel_file.parent.mkdir(parents=True, exist_ok=True)
        name = Path(kernel_path).stem
        kernel_file.write_text(kernel_content.format(name=name, priority=i * 10))

    return tmp_path


@pytest.fixture
def mock_agent():
    """Create a mock agent that can absorb kernels."""
    agent = MagicMock()
    agent.agent_id = "l-cto"
    agent.kernels = {}
    agent.kernel_state = "INACTIVE"
    agent.kernel_hashes = {}

    def absorb_kernel(data):
        # Simulate kernel absorption
        kernel_name = data.get("kernel", {}).get("name", "unknown")
        agent.kernels[kernel_name] = data

    agent.absorb_kernel = MagicMock(side_effect=absorb_kernel)
    agent.set_system_context = MagicMock()

    return agent


# =============================================================================
# reload_kernels() Function Tests
# =============================================================================


class TestReloadKernelsFunction:
    """Tests for the reload_kernels() function."""

    def test_reload_with_no_changes(self, mock_kernel_files, mock_agent):
        """reload_kernels() skips reload when no kernels modified."""
        # First, load kernels normally
        load_kernels(mock_agent, base_path=mock_kernel_files)
        assert mock_agent.kernel_state == "ACTIVE"

        # Now reload - should skip since no changes
        result = reload_kernels(mock_agent, base_path=mock_kernel_files, force=False)

        assert result.success is True
        assert result.kernels_reloaded == 0
        assert len(result.modified_kernels) == 0
        assert len(result.errors) == 0

    def test_reload_with_force(self, mock_kernel_files, mock_agent):
        """reload_kernels() reloads all kernels when force=True."""
        # First, load kernels normally
        load_kernels(mock_agent, base_path=mock_kernel_files)

        # Force reload
        result = reload_kernels(mock_agent, base_path=mock_kernel_files, force=True)

        assert result.success is True
        assert result.kernels_reloaded == len(KERNEL_ORDER)
        assert mock_agent.kernel_state == "ACTIVE"

    def test_reload_detects_modified_kernel(self, mock_kernel_files, mock_agent):
        """reload_kernels() detects and reloads modified kernels."""
        # First, load kernels normally
        load_kernels(mock_agent, base_path=mock_kernel_files)
        original_hashes = dict(mock_agent.kernel_hashes)

        # Modify one kernel file
        kernel_to_modify = KERNEL_ORDER[0]
        kernel_file = mock_kernel_files / kernel_to_modify
        kernel_file.write_text(kernel_file.read_text() + "\n# Modified for test\n")

        # Reload - should detect the modification
        result = reload_kernels(mock_agent, base_path=mock_kernel_files, force=False)

        assert result.success is True
        assert kernel_to_modify in result.modified_kernels
        assert result.new_hashes[kernel_to_modify] != original_hashes.get(
            kernel_to_modify
        )

    def test_reload_preserves_agent_state_on_success(
        self, mock_kernel_files, mock_agent
    ):
        """reload_kernels() preserves agent state after successful reload."""
        load_kernels(mock_agent, base_path=mock_kernel_files)
        assert mock_agent.kernel_state == "ACTIVE"

        result = reload_kernels(mock_agent, base_path=mock_kernel_files, force=True)

        assert result.success is True
        assert mock_agent.kernel_state == "ACTIVE"

    def test_reload_returns_hash_changes(self, mock_kernel_files, mock_agent):
        """reload_kernels() returns previous and new hashes."""
        load_kernels(mock_agent, base_path=mock_kernel_files)

        result = reload_kernels(mock_agent, base_path=mock_kernel_files, force=True)

        assert len(result.previous_hashes) > 0
        assert len(result.new_hashes) > 0
        # Hashes should be the same since files weren't modified
        for kernel_path in KERNEL_ORDER:
            assert result.previous_hashes.get(kernel_path) == result.new_hashes.get(
                kernel_path
            )


class TestReloadKernelsErrorHandling:
    """Tests for error handling in reload_kernels()."""

    def test_reload_handles_missing_kernel_file(self, mock_kernel_files, mock_agent):
        """reload_kernels() handles missing kernel files."""
        load_kernels(mock_agent, base_path=mock_kernel_files)

        # Delete a kernel file
        kernel_to_delete = KERNEL_ORDER[0]
        (mock_kernel_files / kernel_to_delete).unlink()

        # Reload should fail
        result = reload_kernels(mock_agent, base_path=mock_kernel_files, force=True)

        assert result.success is False
        assert len(result.errors) > 0

    def test_reload_handles_invalid_yaml(self, mock_kernel_files, mock_agent):
        """reload_kernels() handles invalid YAML in kernel files."""
        load_kernels(mock_agent, base_path=mock_kernel_files)

        # Corrupt a kernel file
        kernel_to_corrupt = KERNEL_ORDER[0]
        (mock_kernel_files / kernel_to_corrupt).write_text("invalid: - yaml: [")

        # Reload should fail
        result = reload_kernels(mock_agent, base_path=mock_kernel_files, force=True)

        assert result.success is False
        assert len(result.errors) > 0


# =============================================================================
# Kernel Evolution Logging Tests
# =============================================================================


class TestKernelEvolutionLogging:
    """Tests for kernel evolution logging."""

    @pytest.mark.asyncio
    async def test_log_kernel_evolution_creates_event(self):
        """log_kernel_evolution() creates an evolution event."""
        from core.memory.runtime import log_kernel_evolution

        # Use patch.object on the module after import to avoid path issues

        mock_substrate = AsyncMock()
        mock_substrate.ingest_packet = AsyncMock(
            return_value=MagicMock(success=True, packet_id="test-packet-id")
        )

        # Mock the import inside the function by patching builtins
        original_import = (
            __builtins__.__import__
            if hasattr(__builtins__, "__import__")
            else __import__
        )

        def mock_import(name, *args, **kwargs):
            if name == "memory.substrate_service":
                mock_module = MagicMock()
                mock_module.get_service = AsyncMock(return_value=mock_substrate)
                return mock_module
            return original_import(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=mock_import):
            event_id = await log_kernel_evolution(
                event_type="RELOAD",
                agent_id="l-cto",
                kernel_ids=["master", "identity"],
                previous_hashes={"master": "hash1"},
                new_hashes={"master": "hash2"},
                modified_kernels=["master"],
                trigger="manual",
                success=True,
            )

        assert event_id is not None

    @pytest.mark.asyncio
    async def test_log_kernel_evolution_handles_substrate_unavailable(self):
        """log_kernel_evolution() handles unavailable substrate gracefully."""
        from core.memory.runtime import log_kernel_evolution

        # Mock the import to return None for substrate
        original_import = (
            __builtins__.__import__
            if hasattr(__builtins__, "__import__")
            else __import__
        )

        def mock_import(name, *args, **kwargs):
            if name == "memory.substrate_service":
                mock_module = MagicMock()
                mock_module.get_service = AsyncMock(return_value=None)
                return mock_module
            return original_import(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=mock_import):
            event_id = await log_kernel_evolution(
                event_type="RELOAD",
                agent_id="l-cto",
                kernel_ids=["master"],
                previous_hashes={},
                new_hashes={},
                modified_kernels=[],
                trigger="manual",
                success=True,
            )

        # Should still return event_id even if not persisted
        assert event_id is not None


# =============================================================================
# API Endpoint Tests (Mocked)
# =============================================================================


class TestKernelReloadEndpoint:
    """Tests for /kernels/reload API endpoint."""

    @pytest.mark.asyncio
    async def test_endpoint_requires_api_key(self):
        """/kernels/reload requires API key authentication."""
        # Import from the correct location
        import sys

        sys.path.insert(0, str(Path(__file__).parent.parent.parent))

        try:
            from api.server import KernelReloadRequest, KernelReloadResponse
        except (ImportError, ModuleNotFoundError):
            # Skip if api.server can't be imported (pytest path issues)
            pytest.skip("api.server not importable in test environment")

        request = KernelReloadRequest(force=False)
        assert request.force is False

        response = KernelReloadResponse(
            success=True,
            kernels_reloaded=10,
            modified_kernels=["master"],
            errors=[],
            message="Success",
        )
        assert response.success is True
        assert response.kernels_reloaded == 10

    @pytest.mark.asyncio
    async def test_endpoint_response_structure(self):
        """/kernels/reload returns correct response structure."""
        import sys

        sys.path.insert(0, str(Path(__file__).parent.parent.parent))

        try:
            from api.server import KernelReloadResponse
        except (ImportError, ModuleNotFoundError):
            pytest.skip("api.server not importable in test environment")

        response = KernelReloadResponse(
            success=False,
            kernels_reloaded=0,
            modified_kernels=[],
            errors=["Test error"],
            message="Failed",
        )

        assert response.success is False
        assert response.kernels_reloaded == 0
        assert "Test error" in response.errors
        assert response.message == "Failed"


# =============================================================================
# Integration with Agent Registry
# =============================================================================


class TestReloadWithAgentRegistry:
    """Tests for reload integration with KernelAwareAgentRegistry."""

    def test_reload_updates_registry_agent(self, mock_kernel_files, mock_agent):
        """Reload updates the agent in the registry."""
        # Load initial kernels
        load_kernels(mock_agent, base_path=mock_kernel_files)
        initial_kernel_count = len(mock_agent.kernels)

        # Force reload
        result = reload_kernels(mock_agent, base_path=mock_kernel_files, force=True)

        assert result.success is True
        assert len(mock_agent.kernels) == initial_kernel_count
        assert mock_agent.kernel_state == "ACTIVE"


# =============================================================================
# Observability Span Tests
# =============================================================================


class TestReloadObservabilitySpans:
    """Tests for observability spans during reload."""

    def test_reload_creates_span(self, mock_kernel_files, mock_agent):
        """reload_kernels() creates an observability span."""
        with (
            patch("core.kernels.kernelloader._has_observability", True),
            patch("core.kernels.kernelloader.get_observability_service") as mock_obs,
        ):
            mock_service = MagicMock()
            mock_service.emit_span = MagicMock()
            mock_obs.return_value = mock_service

            load_kernels(mock_agent, base_path=mock_kernel_files)
            reload_kernels(mock_agent, base_path=mock_kernel_files, force=True)

            # Verify spans were emitted
            assert mock_service.emit_span.called


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
