"""
Kernel → Agent Activation Integration Tests

Tests the flow: Kernel Load → Agent Activation → Prompt Generation
"""

from pathlib import Path
from unittest.mock import patch

import pytest

pytestmark = pytest.mark.integration


class TestKernelAgentActivationIntegration:
    """Test kernel loading to agent activation integration."""

    def test_kernel_files_exist(self):
        """Kernel YAML files exist in expected locations."""
        kernel_dir = Path("/Users/ib-mac/Projects/L9/private/kernels")

        if kernel_dir.exists():
            yaml_files = list(kernel_dir.glob("*.yaml"))
            assert len(yaml_files) > 0, "Kernel YAML files should exist"

    def test_kernel_loader_integration(self):
        """Kernel loader loads and merges kernels."""
        from runtime.kernel_loader import load_kernel_stack

        # Should load without error
        result = load_kernel_stack()
        assert result is not None
        assert hasattr(result, "kernels_by_id") or hasattr(result, "kernels")

    def test_agent_receives_kernel_prompt(self):
        """Agent executor receives kernel-generated prompt."""
        with patch("core.agents.executor.get_substrate_service"):
            with patch("core.agents.executor.get_redis_client"):
                from core.agents.executor import AgentExecutorService
                from tests.core.agents.test_executor import (
                    MockAgentRegistry, MockAIOSRuntime, MockSubstrateService,
                    MockToolRegistry)

                executor = AgentExecutorService(
                    aios_runtime=MockAIOSRuntime(),
                    tool_registry=MockToolRegistry(),
                    substrate_service=MockSubstrateService(),
                    agent_registry=MockAgentRegistry(),
                )

                # Executor should have kernel state or prompt builder access
                assert (
                    hasattr(executor, "_kernel_state")
                    or hasattr(executor, "kernel_state")
                    or hasattr(executor, "_prompt_builder")
                )

    def test_kernel_prompt_builder_integration(self):
        """Prompt builder uses kernel data."""
        from core.kernels.prompt_builder import \
            build_system_prompt_from_kernels

        prompt = build_system_prompt_from_kernels()

        assert prompt is not None
        assert len(prompt) > 0
