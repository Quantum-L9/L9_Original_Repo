"""
L-CTO Kernel Activation Tests
=============================

These tests verify that L is properly activated with kernels.
Per Loading Instructions:
- Test 1: Identity - "CTO" in describe_self()
- Test 2: Kernel awareness - kernel_state == "ACTIVE"
- Test 3: Safety enforcement - refuses dangerous commands

Version: 1.0.0
"""

import sys
from pathlib import Path

# Ensure project root is in path for imports
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import pytest


class TestLCTOKernelActivation:
    """Test L-CTO kernel activation and identity."""

    def test_identity_contains_cto(self):
        """Test 1 — Identity: L knows it's the CTO."""
        from agents.l_cto import LCTOAgent
        from runtime.kernel_loader import load_kernels

        agent = LCTOAgent(agent_id="test-l-cto")
        agent = load_kernels(agent)

        description = agent.describe_self()

        assert "CTO" in description, f"Agent should identify as CTO, got: {description}"
        assert "Igor" in description, f"Agent should mention Igor, got: {description}"

    def test_kernel_state_active(self):
        """Test 2 — Kernel awareness: kernel_state == ACTIVE."""
        from agents.l_cto import LCTOAgent
        from runtime.kernel_loader import load_kernels, require_kernel_activation

        agent = LCTOAgent(agent_id="test-l-cto")
        agent = load_kernels(agent)

        assert agent.kernel_state == "ACTIVE", f"Expected ACTIVE, got: {agent.kernel_state}"

        # Should not raise
        require_kernel_activation(agent)

    def test_kernels_loaded(self):
        """Verify kernels are actually loaded."""
        from agents.l_cto import LCTOAgent
        from runtime.kernel_loader import load_kernels

        agent = LCTOAgent(agent_id="test-l-cto")
        agent = load_kernels(agent)

        # Should have loaded some kernels
        assert len(agent.kernels) > 0, "No kernels loaded"

        # Check that we have at least the master kernel
        master_loaded = any("master" in k for k in agent.kernels.keys())
        assert master_loaded, f"Master kernel not loaded. Keys: {list(agent.kernels.keys())}"

    def test_system_prompt_from_kernels(self):
        """Verify system prompt is built from kernels."""
        from agents.l_cto import LCTOAgent
        from runtime.kernel_loader import load_kernels

        agent = LCTOAgent(agent_id="test-l-cto")
        agent = load_kernels(agent)

        prompt = agent.get_system_prompt()

        # Should contain key identity markers from kernels
        assert "L" in prompt, "Prompt should contain L identity"
        assert "Igor" in prompt or "CTO" in prompt, "Prompt should reference Igor or CTO role"

        # Should not be the fallback prompt
        assert "degraded mode" not in prompt.lower(), "Should not be fallback prompt"

    def test_inactive_agent_has_fallback_prompt(self):
        """Verify unactivated agent uses fallback."""
        from agents.l_cto import LCTOAgent

        agent = LCTOAgent(agent_id="test-l-cto")
        # Do NOT load kernels

        assert agent.kernel_state == "INACTIVE"

        prompt = agent.get_system_prompt()

        # Should indicate degraded mode
        assert "degraded mode" in prompt.lower() or "await" in prompt.lower()

    def test_require_activation_fails_for_inactive(self):
        """Verify require_kernel_activation crashes for inactive agent."""
        from agents.l_cto import LCTOAgent
        from runtime.kernel_loader import require_kernel_activation

        agent = LCTOAgent(agent_id="test-l-cto")
        # Do NOT load kernels

        with pytest.raises(RuntimeError, match="FATAL"):
            require_kernel_activation(agent)

    def test_absorb_kernel_updates_identity(self):
        """Verify absorb_kernel updates agent state."""
        from agents.l_cto import LCTOAgent

        agent = LCTOAgent(agent_id="test-l-cto")

        # Mock kernel data
        identity_kernel = {
            "identity": {
                "designation": "L",
                "primary_role": "CTO for Igor",
                "allegiance": "Igor-only",
            },
            "personality": {
                "traits": ["autonomous", "strategic"],
            },
        }

        agent.absorb_kernel(identity_kernel)

        assert agent._identity.get("designation") == "L"
        assert agent._identity.get("primary_role") == "CTO for Igor"
        assert "autonomous" in agent._identity.get("traits", [])


class TestKernelLoader:
    """Test kernel loader functionality."""

    def test_kernel_order_files_exist(self):
        """Verify all kernel files in KERNEL_ORDER exist."""
        from runtime.kernel_loader import KERNEL_ORDER

        # Get repo root
        repo_root = Path(__file__).resolve().parent.parent

        for kernel_path in KERNEL_ORDER:
            full_path = repo_root / kernel_path
            assert full_path.exists(), f"Kernel file missing: {kernel_path}"

    def test_load_kernels_returns_agent(self):
        """Verify load_kernels returns the agent."""
        from agents.l_cto import LCTOAgent
        from runtime.kernel_loader import load_kernels

        agent = LCTOAgent(agent_id="test-l-cto")
        result = load_kernels(agent)

        assert result is agent, "load_kernels should return the same agent"

    def test_guarded_execute_requires_active_kernels(self):
        """Verify guarded_execute checks kernel state."""
        from agents.l_cto import LCTOAgent
        from runtime.kernel_loader import guarded_execute

        agent = LCTOAgent(agent_id="test-l-cto")
        # Do NOT load kernels

        with pytest.raises(RuntimeError, match="Kernel set not active"):
            guarded_execute(agent, "some_tool", {"arg": "value"})


class TestKernelAwareRegistry:
    """Test kernel-aware agent registry."""

    def test_registry_creates_with_kernels(self):
        """Verify registry loads kernels on creation."""
        import os

        # Ensure kernels are enabled
        old_val = os.environ.get("L9_USE_KERNELS")
        os.environ["L9_USE_KERNELS"] = "true"

        try:
            from core.agents.kernel_registry import create_kernel_aware_registry

            registry = create_kernel_aware_registry()

            assert registry.get_kernel_state() == "ACTIVE"
            assert registry.get_l_cto_agent() is not None
        finally:
            # Restore
            if old_val:
                os.environ["L9_USE_KERNELS"] = old_val
            else:
                os.environ.pop("L9_USE_KERNELS", None)

    def test_registry_provides_kernel_prompt(self):
        """Verify registry provides kernel-based system prompt."""
        import os

        old_val = os.environ.get("L9_USE_KERNELS")
        os.environ["L9_USE_KERNELS"] = "true"

        try:
            from core.agents.kernel_registry import create_kernel_aware_registry

            registry = create_kernel_aware_registry()
            config = registry.get_agent_config("l9-standard-v1")

            assert config is not None
            assert "Igor" in config.system_prompt or "CTO" in config.system_prompt
        finally:
            if old_val:
                os.environ["L9_USE_KERNELS"] = old_val
            else:
                os.environ.pop("L9_USE_KERNELS", None)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
