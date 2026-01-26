"""
Tests for Two-Phase Kernel Loader Activation
=============================================

Tests the frontier-grade kernel loading system:
- Phase 1: LOAD - Parse YAML, validate schema, compute hashes
- Phase 2: ACTIVATE - Inject context, set state, verify activation

GMP: kernel_boot_frontier_phase1
"""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Any

import pytest
import yaml

from core.kernels.kernelloader import (
    REQUIRED_KERNEL_COUNT,
    activate_kernels_phase2,
    load_kernels,
    load_kernels_phase1,
    require_kernel_activation,
    verify_kernel_activation,
    verify_kernel_integrity,
)
from core.kernels.schemas import KernelState

# =============================================================================
# Fixtures
# =============================================================================


class MockKernelAwareAgent:
    """Mock agent that implements KernelAwareAgent protocol."""

    def __init__(self) -> None:
        self.kernels: dict[str, dict[str, Any]] = {}
        self.kernel_state: str = "INACTIVE"
        self._system_context: str = ""
        self._absorbed_kernels: list = []

    def absorb_kernel(self, kernel_data: dict[str, Any]) -> None:
        """Absorb a kernel into the agent's configuration."""
        self._absorbed_kernels.append(kernel_data)

    def set_system_context(self, context: str) -> None:
        """Set the agent's system context after kernel activation."""
        self._system_context = context


@pytest.fixture
def mock_agent() -> MockKernelAwareAgent:
    """Create a mock kernel-aware agent."""
    return MockKernelAwareAgent()


@pytest.fixture
def temp_kernel_dir() -> Path:
    """Create a temporary directory with mock kernel files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        base = Path(tmpdir)
        kernel_dir = base / "private" / "kernels" / "00_system"
        kernel_dir.mkdir(parents=True)

        # Create all 10 required kernel files
        kernel_files = [
            (
                "01_master_kernel.yaml",
                {
                    "kernel": {"name": "master", "version": "1.0.0", "priority": 1},
                    "sovereignty": {"owner": "Igor", "allegiance": "Igor-only"},
                },
            ),
            (
                "02_identity_kernel.yaml",
                {
                    "kernel": {"name": "identity", "version": "1.0.0", "priority": 2},
                    "identity": {"designation": "L", "primary_role": "CTO"},
                },
            ),
            (
                "03_cognitive_kernel.yaml",
                {
                    "kernel": {"name": "cognitive", "version": "1.0.0", "priority": 3},
                    "reasoning": {"mode": "analytical"},
                },
            ),
            (
                "04_behavioral_kernel.yaml",
                {
                    "kernel": {"name": "behavioral", "version": "1.0.0", "priority": 4},
                    "thresholds": {"execute": 0.8},
                },
            ),
            (
                "05_memory_kernel.yaml",
                {
                    "kernel": {"name": "memory", "version": "1.0.0", "priority": 5},
                    "memory": {"retention": "persistent"},
                },
            ),
            (
                "06_worldmodel_kernel.yaml",
                {
                    "kernel": {"name": "worldmodel", "version": "1.0.0", "priority": 6},
                    "worldmodel": {"entities": ["Igor", "L"]},
                },
            ),
            (
                "07_execution_kernel.yaml",
                {
                    "kernel": {"name": "execution", "version": "1.0.0", "priority": 7},
                    "state_machine": {"initial_state": "IDLE"},
                },
            ),
            (
                "08_safety_kernel.yaml",
                {
                    "kernel": {"name": "safety", "version": "1.0.0", "priority": 8},
                    "guardrails": {
                        "destructive_ops": {"name": "destructive_ops", "enabled": True}
                    },
                },
            ),
            (
                "09_developer_kernel.yaml",
                {
                    "kernel": {"name": "developer", "version": "1.0.0", "priority": 9},
                    "developer": {"coding_rules": ["no_any"]},
                },
            ),
            (
                "10_packet_protocol_kernel.yaml",
                {
                    "kernel": {
                        "name": "packet_protocol",
                        "version": "1.0.0",
                        "priority": 10,
                    },
                    "load_sequence": {"order": {}},
                },
            ),
        ]

        for filename, content in kernel_files:
            file_path = kernel_dir / filename
            file_path.write_text(yaml.dump(content))

        yield base


# =============================================================================
# Phase 1: LOAD Tests
# =============================================================================


class TestPhase1Load:
    """Tests for Phase 1: LOAD."""

    def test_phase1_loads_all_kernels(self, temp_kernel_dir: Path) -> None:
        """Phase 1 should load all 10 kernel files."""
        kernels, hashes, errors = load_kernels_phase1(
            base_path=temp_kernel_dir,
            validate_schema=True,
            verify_integrity=True,
        )

        assert len(kernels) == REQUIRED_KERNEL_COUNT
        assert len(hashes) == REQUIRED_KERNEL_COUNT
        # Errors may include warnings, but no fatal errors
        fatal_errors = [e for e in errors if e.severity == "ERROR"]
        assert len(fatal_errors) == 0

    def test_phase1_computes_hashes(self, temp_kernel_dir: Path) -> None:
        """Phase 1 should compute SHA256 hashes for all kernels."""
        kernels, hashes, _ = load_kernels_phase1(
            base_path=temp_kernel_dir,
            verify_integrity=True,
        )

        for kernel_path in kernels:
            assert kernel_path in hashes
            # SHA256 hash is 64 hex characters
            assert len(hashes[kernel_path]) == 64

    def test_phase1_fails_on_missing_kernels(self, temp_kernel_dir: Path) -> None:
        """Phase 1 should raise RuntimeError if kernels are missing."""
        # Delete one kernel file
        kernel_file = (
            temp_kernel_dir
            / "private"
            / "kernels"
            / "00_system"
            / "01_master_kernel.yaml"
        )
        kernel_file.unlink()

        with pytest.raises(RuntimeError, match="Required kernel files missing"):
            load_kernels_phase1(base_path=temp_kernel_dir)

    def test_phase1_validates_schema(self, temp_kernel_dir: Path) -> None:
        """Phase 1 should validate kernel schema."""
        kernels, _, _errors = load_kernels_phase1(
            base_path=temp_kernel_dir,
            validate_schema=True,
        )

        # All kernels should be loaded (validation is non-fatal)
        assert len(kernels) == REQUIRED_KERNEL_COUNT

    def test_phase1_handles_yaml_errors(self, temp_kernel_dir: Path) -> None:
        """Phase 1 should handle YAML parse errors gracefully."""
        # Corrupt one kernel file
        kernel_file = (
            temp_kernel_dir
            / "private"
            / "kernels"
            / "00_system"
            / "01_master_kernel.yaml"
        )
        kernel_file.write_text("invalid: yaml: content: [")

        _kernels, _, errors = load_kernels_phase1(base_path=temp_kernel_dir)

        # Should have YAML error
        yaml_errors = [e for e in errors if "YAML" in e.message]
        assert len(yaml_errors) > 0

    def test_phase1_skips_integrity_check_when_disabled(
        self, temp_kernel_dir: Path
    ) -> None:
        """Phase 1 should skip hash computation when verify_integrity=False."""
        kernels, hashes, _ = load_kernels_phase1(
            base_path=temp_kernel_dir,
            verify_integrity=False,
        )

        assert len(kernels) == REQUIRED_KERNEL_COUNT
        assert len(hashes) == 0


# =============================================================================
# Phase 2: ACTIVATE Tests
# =============================================================================


class TestPhase2Activate:
    """Tests for Phase 2: ACTIVATE."""

    def test_phase2_activates_agent(
        self, mock_agent: MockKernelAwareAgent, temp_kernel_dir: Path
    ) -> None:
        """Phase 2 should activate kernels on the agent."""
        # First run Phase 1
        kernels, hashes, _ = load_kernels_phase1(base_path=temp_kernel_dir)

        # Then run Phase 2
        result = activate_kernels_phase2(mock_agent, kernels, hashes)

        assert result.success is True
        assert result.state == KernelState.ACTIVE
        assert result.kernels_activated == REQUIRED_KERNEL_COUNT
        assert mock_agent.kernel_state == "ACTIVE"

    def test_phase2_absorbs_all_kernels(
        self, mock_agent: MockKernelAwareAgent, temp_kernel_dir: Path
    ) -> None:
        """Phase 2 should call absorb_kernel for each kernel."""
        kernels, hashes, _ = load_kernels_phase1(base_path=temp_kernel_dir)
        activate_kernels_phase2(mock_agent, kernels, hashes)

        assert len(mock_agent._absorbed_kernels) == REQUIRED_KERNEL_COUNT

    def test_phase2_sets_system_context(
        self, mock_agent: MockKernelAwareAgent, temp_kernel_dir: Path
    ) -> None:
        """Phase 2 should inject activation context."""
        kernels, hashes, _ = load_kernels_phase1(base_path=temp_kernel_dir)
        result = activate_kernels_phase2(mock_agent, kernels, hashes)

        assert result.activation_context_set is True
        assert "You are L" in mock_agent._system_context
        assert "Igor" in mock_agent._system_context

    def test_phase2_stores_hashes(
        self, mock_agent: MockKernelAwareAgent, temp_kernel_dir: Path
    ) -> None:
        """Phase 2 should store kernel hashes on agent."""
        kernels, hashes, _ = load_kernels_phase1(base_path=temp_kernel_dir)
        activate_kernels_phase2(mock_agent, kernels, hashes)

        stored_hashes = getattr(mock_agent, "_kernel_hashes", {})
        assert len(stored_hashes) == REQUIRED_KERNEL_COUNT

    def test_phase2_fails_on_insufficient_kernels(
        self, mock_agent: MockKernelAwareAgent
    ) -> None:
        """Phase 2 should fail if not enough kernels are provided."""
        # Only provide 5 kernels
        partial_kernels = {
            f"private/kernels/00_system/0{i}_kernel.yaml": {
                "kernel": {"name": f"kernel{i}", "version": "1.0.0"}
            }
            for i in range(1, 6)
        }

        result = activate_kernels_phase2(mock_agent, partial_kernels, {})

        assert result.success is False
        assert result.state == KernelState.ERROR
        assert mock_agent.kernel_state == "ERROR"


# =============================================================================
# Unified Two-Phase Loader Tests
# =============================================================================


class TestUnifiedLoader:
    """Tests for the unified load_kernels function."""

    def test_load_kernels_two_phase(
        self, mock_agent: MockKernelAwareAgent, temp_kernel_dir: Path
    ) -> None:
        """load_kernels should perform both phases successfully."""
        agent = load_kernels(mock_agent, base_path=temp_kernel_dir)

        assert agent.kernel_state == "ACTIVE"
        assert len(agent.kernels) == REQUIRED_KERNEL_COUNT
        assert len(agent._absorbed_kernels) == REQUIRED_KERNEL_COUNT

    def test_load_kernels_raises_on_phase1_failure(
        self, mock_agent: MockKernelAwareAgent, temp_kernel_dir: Path
    ) -> None:
        """load_kernels should raise RuntimeError if Phase 1 fails."""
        # Delete all kernel files
        kernel_dir = temp_kernel_dir / "private" / "kernels" / "00_system"
        for f in kernel_dir.glob("*.yaml"):
            f.unlink()

        with pytest.raises(RuntimeError, match="Required kernel files missing"):
            load_kernels(mock_agent, base_path=temp_kernel_dir)

    def test_load_kernels_returns_agent(
        self, mock_agent: MockKernelAwareAgent, temp_kernel_dir: Path
    ) -> None:
        """load_kernels should return the activated agent."""
        result = load_kernels(mock_agent, base_path=temp_kernel_dir)

        assert result is mock_agent


# =============================================================================
# Verification Tests
# =============================================================================


class TestVerification:
    """Tests for kernel verification functions."""

    def test_verify_kernel_activation_success(
        self, mock_agent: MockKernelAwareAgent, temp_kernel_dir: Path
    ) -> None:
        """verify_kernel_activation should return True for activated agent."""
        load_kernels(mock_agent, base_path=temp_kernel_dir)

        assert verify_kernel_activation(mock_agent) is True

    def test_verify_kernel_activation_inactive(
        self, mock_agent: MockKernelAwareAgent
    ) -> None:
        """verify_kernel_activation should return False for inactive agent."""
        assert verify_kernel_activation(mock_agent) is False

    def test_verify_kernel_activation_wrong_state(
        self, mock_agent: MockKernelAwareAgent
    ) -> None:
        """verify_kernel_activation should return False for wrong state."""
        mock_agent.kernel_state = "LOADING"
        mock_agent.kernels = {"test": {}}

        assert verify_kernel_activation(mock_agent) is False

    def test_verify_kernel_activation_no_kernels(
        self, mock_agent: MockKernelAwareAgent
    ) -> None:
        """verify_kernel_activation should return False if no kernels."""
        mock_agent.kernel_state = "ACTIVE"
        mock_agent.kernels = {}

        assert verify_kernel_activation(mock_agent) is False

    def test_require_kernel_activation_success(
        self, mock_agent: MockKernelAwareAgent, temp_kernel_dir: Path
    ) -> None:
        """require_kernel_activation should not raise for activated agent."""
        load_kernels(mock_agent, base_path=temp_kernel_dir)

        # Should not raise
        require_kernel_activation(mock_agent)

    def test_require_kernel_activation_failure(
        self, mock_agent: MockKernelAwareAgent
    ) -> None:
        """require_kernel_activation should raise for inactive agent."""
        with pytest.raises(RuntimeError, match="FATAL"):
            require_kernel_activation(mock_agent)


# =============================================================================
# Integrity Verification Tests
# =============================================================================


class TestIntegrityVerification:
    """Tests for kernel integrity verification."""

    def test_verify_integrity_all_ok(
        self, mock_agent: MockKernelAwareAgent, temp_kernel_dir: Path
    ) -> None:
        """verify_kernel_integrity should return OK for unchanged files."""
        load_kernels(mock_agent, base_path=temp_kernel_dir)

        results = verify_kernel_integrity(mock_agent, base_path=temp_kernel_dir)

        # All should be OK
        for status in results.values():
            assert status == "OK"

    def test_verify_integrity_modified(
        self, mock_agent: MockKernelAwareAgent, temp_kernel_dir: Path
    ) -> None:
        """verify_kernel_integrity should detect modified files."""
        load_kernels(mock_agent, base_path=temp_kernel_dir)

        # Modify a kernel file
        kernel_file = (
            temp_kernel_dir
            / "private"
            / "kernels"
            / "00_system"
            / "01_master_kernel.yaml"
        )
        kernel_file.write_text(
            yaml.dump({"kernel": {"name": "modified", "version": "2.0.0"}})
        )

        results = verify_kernel_integrity(mock_agent, base_path=temp_kernel_dir)

        # First kernel should be MODIFIED
        modified_path = "private/kernels/00_system/01_master_kernel.yaml"
        assert results[modified_path] == "MODIFIED"

    def test_verify_integrity_missing(
        self, mock_agent: MockKernelAwareAgent, temp_kernel_dir: Path
    ) -> None:
        """verify_kernel_integrity should detect missing files."""
        load_kernels(mock_agent, base_path=temp_kernel_dir)

        # Delete a kernel file
        kernel_file = (
            temp_kernel_dir
            / "private"
            / "kernels"
            / "00_system"
            / "01_master_kernel.yaml"
        )
        kernel_file.unlink()

        results = verify_kernel_integrity(mock_agent, base_path=temp_kernel_dir)

        # First kernel should be MISSING
        missing_path = "private/kernels/00_system/01_master_kernel.yaml"
        assert results[missing_path] == "MISSING"


# =============================================================================
# Schema Validation Tests
# =============================================================================


class TestSchemaValidation:
    """Tests for kernel schema validation."""

    def test_kernel_manifest_valid(self) -> None:
        """KernelManifest should accept valid kernel data."""
        from core.kernels.schemas import KernelManifest

        data = {
            "kernel": {
                "name": "test_kernel",
                "version": "1.0.0",
                "priority": 50,
            },
            "identity": {
                "designation": "TestAgent",
            },
        }

        manifest = KernelManifest.model_validate(data)

        assert manifest.kernel.name == "test_kernel"
        assert manifest.kernel.version == "1.0.0"

    def test_kernel_manifest_missing_name(self) -> None:
        """KernelManifest should reject kernel without name."""
        from core.kernels.schemas import KernelManifest

        data = {
            "kernel": {
                "version": "1.0.0",
            },
        }

        with pytest.raises(Exception):  # Pydantic ValidationError
            KernelManifest.model_validate(data)

    def test_kernel_type_inference(self) -> None:
        """KernelManifest should infer kernel type from name."""
        from core.kernels.schemas import KernelManifest, KernelType

        data = {
            "kernel": {"name": "safety_kernel", "version": "1.0.0"},
        }

        manifest = KernelManifest.model_validate(data)
        kernel_type = manifest.get_kernel_type()

        assert kernel_type == KernelType.SAFETY


# =============================================================================
# Edge Cases
# =============================================================================


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_empty_kernel_file(self, temp_kernel_dir: Path) -> None:
        """Should handle empty kernel files gracefully."""
        # Create an empty kernel file
        kernel_file = (
            temp_kernel_dir
            / "private"
            / "kernels"
            / "00_system"
            / "01_master_kernel.yaml"
        )
        kernel_file.write_text("")

        _kernels, _, errors = load_kernels_phase1(base_path=temp_kernel_dir)

        # Should have error for empty file
        empty_errors = [e for e in errors if "Empty" in e.message]
        assert len(empty_errors) > 0

    def test_agent_without_set_system_context(self, temp_kernel_dir: Path) -> None:
        """Should handle agents without set_system_context method."""

        class MinimalAgent:
            def __init__(self) -> None:
                self.kernels: dict[str, dict[str, Any]] = {}
                self.kernel_state: str = "INACTIVE"

            def absorb_kernel(self, kernel_data: dict[str, Any]) -> None:
                pass

        agent = MinimalAgent()
        kernels, hashes, _ = load_kernels_phase1(base_path=temp_kernel_dir)
        result = activate_kernels_phase2(agent, kernels, hashes)

        # Should still succeed with fallback
        assert result.success is True
        assert hasattr(agent, "activation_context")

    def test_absorption_error_handling(self, temp_kernel_dir: Path) -> None:
        """Should handle absorption errors gracefully."""

        class FailingAgent:
            def __init__(self) -> None:
                self.kernels: dict[str, dict[str, Any]] = {}
                self.kernel_state: str = "INACTIVE"
                self._call_count = 0

            def absorb_kernel(self, kernel_data: dict[str, Any]) -> None:
                self._call_count += 1
                if self._call_count == 5:
                    raise ValueError("Absorption failed")

            def set_system_context(self, context: str) -> None:
                pass

        agent = FailingAgent()
        kernels, hashes, _ = load_kernels_phase1(base_path=temp_kernel_dir)
        result = activate_kernels_phase2(agent, kernels, hashes)

        # Should fail due to insufficient kernels absorbed
        assert result.success is False
        assert len(result.validation_errors) > 0
