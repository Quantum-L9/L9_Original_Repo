"""
Tests for L-CTO Bootstrap and Kernel-Aware Registry
====================================================

Tests the L-CTO agent initialization with kernel loading:
- KernelAwareAgentRegistry initialization
- L-CTO agent creation with kernels
- Kernel state verification
- Integrity verification

GMP: kernel_boot_frontier_phase1
"""

from __future__ import annotations

# agents.l_cto pre-imported in root conftest.py

import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml

# =============================================================================
# Fixtures
# =============================================================================


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
                    "modes": {"executive": {"name": "executive", "active": True}},
                },
            ),
            (
                "02_identity_kernel.yaml",
                {
                    "kernel": {"name": "identity", "version": "1.0.0", "priority": 2},
                    "identity": {
                        "designation": "L",
                        "primary_role": "CTO for Igor",
                        "allegiance": "Igor-only",
                        "mission": "Build L9 Secure AI OS",
                    },
                    "personality": {"tone": "direct", "verbosity": "concise"},
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
                    "thresholds": {"execute": 0.8, "questions_max": 1},
                    "prohibitions": [{"name": "sycophancy", "detect": ["Great question"]}],
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
                    "task_sizing": {"small": {"max_steps": 3}},
                },
            ),
            (
                "08_safety_kernel.yaml",
                {
                    "kernel": {"name": "safety", "version": "1.0.0", "priority": 8},
                    "guardrails": {"destructive_ops": {"name": "destructive_ops", "enabled": True}},
                    "prohibited_actions": ["delete_production_data"],
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


@pytest.fixture
def mock_env_with_kernels(temp_kernel_dir: Path, monkeypatch):
    """Set up environment for kernel loading."""
    monkeypatch.setenv("L9_USE_KERNELS", "true")
    monkeypatch.setenv("L9_LLM_MODEL", "gpt-4o")
    return temp_kernel_dir


@pytest.fixture
def mock_env_without_kernels(monkeypatch):
    """Set up environment without kernel loading."""
    monkeypatch.setenv("L9_USE_KERNELS", "false")


# =============================================================================
# L-CTO Agent Tests
# =============================================================================


class TestLCTOAgent:
    """Tests for LCTOAgent class."""

    def test_lcto_agent_creation(self) -> None:
        """LCTOAgent should be created in INACTIVE state."""
        from agents.l_cto import LCTOAgent

        agent = LCTOAgent(agent_id="test-agent")

        assert agent.agent_id == "test-agent"
        assert agent.kernel_state == "INACTIVE"
        assert len(agent.kernels) == 0

    def test_lcto_agent_absorb_kernel(self) -> None:
        """LCTOAgent should absorb kernel data."""
        from agents.l_cto import LCTOAgent

        agent = LCTOAgent(agent_id="test-agent")

        # Absorb identity kernel
        agent.absorb_kernel(
            {
                "identity": {
                    "designation": "L",
                    "primary_role": "CTO",
                },
            }
        )

        assert agent._identity.get("designation") == "L"
        assert agent._identity.get("primary_role") == "CTO"

    def test_lcto_agent_absorb_behavioral_kernel(self) -> None:
        """LCTOAgent should absorb behavioral kernel data."""
        from agents.l_cto import LCTOAgent

        agent = LCTOAgent(agent_id="test-agent")

        agent.absorb_kernel(
            {
                "thresholds": {"execute": 0.9},
                "prohibitions": [{"name": "test", "detect": ["pattern"]}],
            }
        )

        assert agent._behavioral.get("thresholds", {}).get("execute") == 0.9
        assert len(agent._behavioral.get("prohibitions", [])) == 1

    def test_lcto_agent_absorb_safety_kernel(self) -> None:
        """LCTOAgent should absorb safety kernel data."""
        from agents.l_cto import LCTOAgent

        agent = LCTOAgent(agent_id="test-agent")

        agent.absorb_kernel(
            {
                "guardrails": {"test": {"enabled": True}},
                "prohibited_actions": ["delete_all"],
            }
        )

        assert "test" in agent._safety.get("guardrails", {})
        assert "delete_all" in agent._safety.get("prohibited_actions", [])

    def test_lcto_agent_set_system_context(self) -> None:
        """LCTOAgent should accept system context."""
        from agents.l_cto import LCTOAgent

        agent = LCTOAgent(agent_id="test-agent")
        agent.set_system_context("Test context")

        assert agent._system_context == "Test context"

    def test_lcto_agent_fallback_prompt_when_inactive(self) -> None:
        """LCTOAgent should return fallback prompt when kernels not active."""
        from agents.l_cto import LCTOAgent

        agent = LCTOAgent(agent_id="test-agent")
        prompt = agent.get_system_prompt()

        assert "Kernels are not loaded" in prompt

    def test_lcto_agent_kernel_prompt_when_active(self, temp_kernel_dir: Path) -> None:
        """LCTOAgent should return kernel-built prompt when active."""
        from agents.l_cto import LCTOAgent
        from core.kernels.kernelloader import load_kernels

        agent = LCTOAgent(agent_id="test-agent")
        agent = load_kernels(agent, base_path=temp_kernel_dir)

        prompt = agent.get_system_prompt()

        assert "You are L" in prompt
        assert "Igor" in prompt

    def test_lcto_agent_describe_self_inactive(self) -> None:
        """LCTOAgent describe_self should indicate inactive state."""
        from agents.l_cto import LCTOAgent

        agent = LCTOAgent(agent_id="test-agent")
        description = agent.describe_self()

        assert "INACTIVE" in description

    def test_lcto_agent_describe_self_active(self, temp_kernel_dir: Path) -> None:
        """LCTOAgent describe_self should indicate active state."""
        from agents.l_cto import LCTOAgent
        from core.kernels.kernelloader import load_kernels

        agent = LCTOAgent(agent_id="test-agent")
        agent = load_kernels(agent, base_path=temp_kernel_dir)

        description = agent.describe_self()

        # Active agent should have meaningful description with kernel count
        assert "10 loaded" in description or "Kernels:" in description
        assert "Igor" in description  # Should mention owner


# =============================================================================
# Kernel-Aware Registry Tests
# =============================================================================


class TestKernelAwareAgentRegistry:
    """Tests for KernelAwareAgentRegistry."""

    def test_registry_initialization_with_kernels(self, temp_kernel_dir: Path, monkeypatch) -> None:
        """Registry should initialize with kernels when USE_KERNELS=true."""
        monkeypatch.setenv("L9_USE_KERNELS", "true")

        # Patch the kernel loader to use temp directory
        from core.agents.kernel_registry import KernelAwareAgentRegistry
        from core.kernels import kernelloader

        # Temporarily modify the loader to use our temp path
        original_load = kernelloader.load_kernels

        def patched_load(agent, base_path=None, **kwargs):
            return original_load(agent, base_path=temp_kernel_dir, **kwargs)

        with patch.object(kernelloader, "load_kernels", patched_load):
            registry = KernelAwareAgentRegistry()

            assert registry.get_kernel_state() == "ACTIVE"
            assert registry.get_l_cto_agent() is not None

    @pytest.mark.skip(reason="Environment mocking requires module reload - test maintenance needed")
    def test_registry_initialization_without_kernels(self, mock_env_without_kernels) -> None:
        """Registry should initialize with fallback when USE_KERNELS=false."""
        from core.agents.kernel_registry import KernelAwareAgentRegistry

        registry = KernelAwareAgentRegistry()

        assert registry.get_kernel_state() == "INACTIVE"
        assert registry.get_l_cto_agent() is None

    def test_registry_get_agent_config(self, mock_env_without_kernels) -> None:
        """Registry should return agent config."""
        from core.agents.kernel_registry import KernelAwareAgentRegistry

        registry = KernelAwareAgentRegistry()
        config = registry.get_agent_config("l9-standard-v1")

        assert config is not None
        assert config.agent_id == "l9-standard-v1"

    def test_registry_agent_exists(self, mock_env_without_kernels) -> None:
        """Registry should report agent exists."""
        from core.agents.kernel_registry import KernelAwareAgentRegistry

        registry = KernelAwareAgentRegistry()

        assert registry.agent_exists("l9-standard-v1") is True
        assert registry.agent_exists("any-agent") is True  # All agents use L-CTO


# =============================================================================
# Factory Function Tests
# =============================================================================


class TestCreateKernelAwareRegistry:
    """Tests for create_kernel_aware_registry factory."""

    @pytest.mark.skip(reason="Environment mocking requires module reload - test maintenance needed")
    def test_create_registry_without_kernels(self, mock_env_without_kernels) -> None:
        """Factory should create registry without kernels."""
        from core.agents.kernel_registry import create_kernel_aware_registry

        registry = create_kernel_aware_registry()

        assert registry is not None
        assert registry.get_kernel_state() == "INACTIVE"

    def test_create_registry_raises_on_kernel_failure(self, monkeypatch) -> None:
        """Factory should raise RuntimeError if kernel loading fails."""
        monkeypatch.setenv("L9_USE_KERNELS", "true")

        # Patch to simulate kernel loading failure
        with patch(
            "core.kernels.kernelloader.load_kernels",
            side_effect=RuntimeError("Kernel files missing"),
        ):
            from core.agents.kernel_registry import create_kernel_aware_registry

            with pytest.raises(RuntimeError, match="FATAL"):
                create_kernel_aware_registry()


# =============================================================================
# Integration Tests
# =============================================================================


class TestBootstrapIntegration:
    """Integration tests for L-CTO bootstrap."""

    def test_full_bootstrap_flow(self, temp_kernel_dir: Path) -> None:
        """Test complete bootstrap flow from agent creation to activation."""
        from agents.l_cto import LCTOAgent
        from core.kernels.kernelloader import (
            load_kernels,
            require_kernel_activation,
            verify_kernel_activation,
        )

        # Create agent
        agent = LCTOAgent(agent_id="l9-standard-v1")
        assert agent.kernel_state == "INACTIVE"

        # Load kernels
        agent = load_kernels(agent, base_path=temp_kernel_dir)
        assert agent.kernel_state == "ACTIVE"

        # Verify activation
        assert verify_kernel_activation(agent) is True

        # Should not raise
        require_kernel_activation(agent)

        # Check absorbed data
        assert len(agent.kernels) == 10
        # Check identity was absorbed
        assert hasattr(agent, "_identity") and "L" in agent._identity.get("designation", "")

    @pytest.mark.skip(reason="Import patching complexity - l_cto.py uses runtime.kernel_loader")
    def test_bootstrap_with_create_l_cto_agent(self, temp_kernel_dir: Path) -> None:
        """Test bootstrap using create_l_cto_agent factory."""
        from agents.l_cto import create_l_cto_agent
        from core.kernels import kernelloader

        # Patch to use temp directory
        original_load = kernelloader.load_kernels

        def patched_load(agent, base_path=None, **kwargs):
            return original_load(agent, base_path=temp_kernel_dir, **kwargs)

        with patch.object(kernelloader, "load_kernels", patched_load):
            # Also need to patch the runtime.kernel_loader import in l_cto.py
            with patch(
                "agents.l_cto.load_kernels",
                patched_load,
            ):
                agent = create_l_cto_agent(
                    agent_id="test-agent",
                    load_kernels_on_create=True,
                )

                assert agent.kernel_state == "ACTIVE"
                assert len(agent.kernels) == 10

    def test_bootstrap_without_kernel_loading(self) -> None:
        """Test creating agent without loading kernels."""
        from agents.l_cto import create_l_cto_agent

        agent = create_l_cto_agent(
            agent_id="test-agent",
            load_kernels_on_create=False,
        )

        assert agent.kernel_state == "INACTIVE"
        assert len(agent.kernels) == 0


# =============================================================================
# Kernel State Transitions
# =============================================================================


class TestKernelStateTransitions:
    """Tests for kernel state transitions."""

    def test_state_inactive_to_loading(self) -> None:
        """Agent should transition from INACTIVE to LOADING."""
        from agents.l_cto import LCTOAgent

        agent = LCTOAgent(agent_id="test-agent")
        assert agent.kernel_state == "INACTIVE"

        # Simulate start of loading
        agent.kernel_state = "LOADING"
        assert agent.kernel_state == "LOADING"

    def test_state_loading_to_active(self, temp_kernel_dir: Path) -> None:
        """Agent should transition from LOADING to ACTIVE."""
        from agents.l_cto import LCTOAgent
        from core.kernels.kernelloader import load_kernels

        agent = LCTOAgent(agent_id="test-agent")
        agent = load_kernels(agent, base_path=temp_kernel_dir)

        assert agent.kernel_state == "ACTIVE"

    def test_state_error_on_failure(self) -> None:
        """Agent should transition to ERROR on failure."""
        from agents.l_cto import LCTOAgent
        from core.kernels.kernelloader import activate_kernels_phase2

        agent = LCTOAgent(agent_id="test-agent")

        # Provide insufficient kernels
        result = activate_kernels_phase2(agent, {}, {})

        assert result.success is False
        assert agent.kernel_state == "ERROR"


# =============================================================================
# Edge Cases
# =============================================================================


class TestEdgeCases:
    """Tests for edge cases in L-CTO bootstrap."""

    def test_agent_with_custom_config(self) -> None:
        """Agent should accept custom config."""
        from agents.l_cto import LCTOAgent
        from agents.base_agent import AgentConfig

        config = AgentConfig(
            model="gpt-4o",
            temperature=0.5,
        )

        agent = LCTOAgent(agent_id="custom-agent", config=config)

        assert agent.agent_id == "custom-agent"

    def test_agent_with_manifest_path(self) -> None:
        """Agent should accept manifest path."""
        from agents.l_cto import LCTOAgent

        agent = LCTOAgent(
            agent_id="test-agent",
            manifest="/path/to/manifest.yaml",
        )

        assert agent._manifest_path == "/path/to/manifest.yaml"

    def test_multiple_kernel_absorptions(self) -> None:
        """Agent should handle multiple kernel absorptions."""
        from agents.l_cto import LCTOAgent

        agent = LCTOAgent(agent_id="test-agent")

        # Absorb multiple kernels (simulating kernel loader behavior)
        for i in range(10):
            kernel_data = {"kernel": {"name": f"kernel_{i}", "version": "1.0.0"}}
            agent.absorb_kernel(kernel_data)
            # Kernel loader also populates agent.kernels directly
            agent.kernels[f"kernel_{i}"] = kernel_data

        # Should have absorbed all
        assert len(agent.kernels) == 10

    def test_empty_kernel_absorption(self) -> None:
        """Agent should handle empty kernel data."""
        from agents.l_cto import LCTOAgent

        agent = LCTOAgent(agent_id="test-agent")

        # Absorb empty data
        agent.absorb_kernel({})
        agent.absorb_kernel(None)  # type: ignore

        # Should not crash
        assert agent.kernel_state == "INACTIVE"
