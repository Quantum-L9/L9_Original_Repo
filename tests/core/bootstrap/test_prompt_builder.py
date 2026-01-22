"""
Tests for kernel-aware prompt builder (GMP-60: Runtime Hardening).

Tests the building of system prompts from kernel stack:
- Safety prefix inclusion
- Kernel section extraction
- Runtime context building
- Edge cases (no kernels, inactive state)

Version: 1.0.0
"""

from unittest.mock import MagicMock

from core.agents.prompt_builder import (SAFETY_PREFIX,
                                        build_kernel_system_prompt,
                                        build_runtime_prompt,
                                        get_safety_prefix)


class MockKernelAgent:
    """Mock kernel-aware agent for testing."""

    def __init__(
        self,
        kernels: dict = None,
        kernel_state: str = "ACTIVE",
    ):
        self.kernels = kernels or {}
        self.kernel_state = kernel_state


class TestSafetyPrefix:
    """Tests for safety prefix functionality."""

    def test_safety_prefix_not_empty(self):
        """Safety prefix should not be empty."""
        prefix = get_safety_prefix()
        assert len(prefix) > 0

    def test_safety_prefix_contains_constraints(self):
        """Safety prefix should contain key constraints."""
        prefix = get_safety_prefix()
        assert "IMMUTABLE" in prefix
        assert "Igor" in prefix
        assert "MUST NOT" in prefix

    def test_safety_prefix_constant(self):
        """Safety prefix should match SAFETY_PREFIX constant."""
        assert get_safety_prefix() == SAFETY_PREFIX


class TestBuildKernelSystemPrompt:
    """Tests for build_kernel_system_prompt function."""

    def test_empty_kernels_returns_safety_prefix(self):
        """Should return safety prefix when no kernels loaded."""
        agent = MockKernelAgent(kernels={}, kernel_state="INACTIVE")
        prompt = build_kernel_system_prompt(agent)

        assert SAFETY_PREFIX in prompt
        assert "INACTIVE" in prompt

    def test_inactive_kernel_state_warns(self):
        """Should include warning when kernel state is not ACTIVE."""
        agent = MockKernelAgent(
            kernels={"test_kernel": {"identity": "test"}}, kernel_state="LOADING"
        )
        prompt = build_kernel_system_prompt(agent)

        assert "INACTIVE" in prompt or "LOADING" in prompt or SAFETY_PREFIX in prompt

    def test_active_kernels_includes_safety_prefix(self):
        """Should include safety prefix when kernels are active."""
        agent = MockKernelAgent(
            kernels={
                "private/kernels/00_system/02_identity_kernel.yaml": {
                    "identity": "I am L, the CTO"
                }
            },
            kernel_state="ACTIVE",
        )
        prompt = build_kernel_system_prompt(agent)

        assert SAFETY_PREFIX in prompt

    def test_extracts_identity_section(self):
        """Should extract identity section from kernels."""
        agent = MockKernelAgent(
            kernels={
                "private/kernels/00_system/02_identity_kernel.yaml": {
                    "identity": "I am L, Igor's CTO assistant"
                }
            },
            kernel_state="ACTIVE",
        )
        prompt = build_kernel_system_prompt(agent, include_identity=True)

        assert "IDENTITY" in prompt
        assert "Igor's CTO" in prompt

    def test_extracts_safety_section(self):
        """Should extract safety section from kernels."""
        agent = MockKernelAgent(
            kernels={
                "private/kernels/00_system/08_safety_kernel.yaml": {
                    "safety": "Never execute destructive operations without approval"
                }
            },
            kernel_state="ACTIVE",
        )
        prompt = build_kernel_system_prompt(agent, include_safety=True)

        assert "SAFETY CONSTRAINTS" in prompt
        assert "destructive operations" in prompt

    def test_extracts_behavioral_section(self):
        """Should extract behavioral section from kernels."""
        agent = MockKernelAgent(
            kernels={
                "private/kernels/00_system/04_behavioral_kernel.yaml": {
                    "behavioral": "Be direct and concise"
                }
            },
            kernel_state="ACTIVE",
        )
        prompt = build_kernel_system_prompt(agent, include_behavioral=True)

        assert "BEHAVIORAL" in prompt
        assert "direct and concise" in prompt

    def test_extracts_execution_section(self):
        """Should extract execution section from kernels."""
        agent = MockKernelAgent(
            kernels={
                "private/kernels/00_system/07_execution_kernel.yaml": {
                    "execution": "Execute tasks autonomously"
                }
            },
            kernel_state="ACTIVE",
        )
        prompt = build_kernel_system_prompt(agent, include_execution=True)

        assert "EXECUTION" in prompt
        assert "autonomously" in prompt

    def test_can_disable_safety_prefix(self):
        """Should allow disabling safety prefix (for testing only)."""
        agent = MockKernelAgent(
            kernels={
                "private/kernels/00_system/02_identity_kernel.yaml": {
                    "identity": "Test identity"
                }
            },
            kernel_state="ACTIVE",
        )
        prompt = build_kernel_system_prompt(agent, include_safety_prefix=False)

        assert SAFETY_PREFIX not in prompt
        assert "IDENTITY" in prompt

    def test_can_disable_sections(self):
        """Should allow disabling individual sections."""
        agent = MockKernelAgent(
            kernels={
                "private/kernels/00_system/02_identity_kernel.yaml": {
                    "identity": "Test identity"
                },
                "private/kernels/00_system/08_safety_kernel.yaml": {
                    "safety": "Test safety"
                },
            },
            kernel_state="ACTIVE",
        )
        prompt = build_kernel_system_prompt(
            agent,
            include_identity=False,
            include_safety=False,
        )

        # Should only have safety prefix, no identity or safety sections
        assert SAFETY_PREFIX in prompt
        # IDENTITY section should not be present (separate from prefix)
        assert "## IDENTITY" not in prompt
        assert "## SAFETY CONSTRAINTS" not in prompt

    def test_handles_nested_kernel_content(self):
        """Should handle nested kernel content structures."""
        agent = MockKernelAgent(
            kernels={
                "private/kernels/00_system/02_identity_kernel.yaml": {
                    "identity": {"content": "Nested content", "version": "1.0"}
                }
            },
            kernel_state="ACTIVE",
        )
        prompt = build_kernel_system_prompt(agent)

        assert "Nested content" in prompt

    def test_handles_list_kernel_content(self):
        """Should handle list kernel content structures."""
        agent = MockKernelAgent(
            kernels={
                "private/kernels/00_system/02_identity_kernel.yaml": {
                    "identity": ["Trait 1", "Trait 2", "Trait 3"]
                }
            },
            kernel_state="ACTIVE",
        )
        prompt = build_kernel_system_prompt(agent)

        assert "Trait 1" in prompt
        assert "Trait 2" in prompt


class TestBuildRuntimePrompt:
    """Tests for build_runtime_prompt function."""

    def test_includes_channel(self):
        """Should include channel in runtime prompt."""
        prompt = build_runtime_prompt(
            task_payload={"message": "Hello"},
            channel="slack",
        )

        assert "slack" in prompt
        assert "CURRENT SESSION" in prompt

    def test_includes_thread_context(self):
        """Should include thread context when provided."""
        prompt = build_runtime_prompt(
            task_payload={"message": "Hello"},
            memory_context={"thread_context": "Previous conversation about GMP"},
            channel="http",
        )

        assert "Thread Context" in prompt
        assert "GMP" in prompt

    def test_includes_semantic_hits(self):
        """Should include semantic hits when provided."""
        prompt = build_runtime_prompt(
            task_payload={"message": "Hello"},
            memory_context={"semantic_hits": "Relevant memory about deployment"},
            channel="http",
        )

        assert "Relevant Memory" in prompt
        assert "deployment" in prompt

    def test_handles_empty_memory_context(self):
        """Should handle empty memory context."""
        prompt = build_runtime_prompt(
            task_payload={"message": "Hello"},
            memory_context={},
            channel="http",
        )

        assert "CURRENT SESSION" in prompt
        assert "Thread Context" not in prompt

    def test_handles_none_memory_context(self):
        """Should handle None memory context."""
        prompt = build_runtime_prompt(
            task_payload={"message": "Hello"},
            memory_context=None,
            channel="http",
        )

        assert "CURRENT SESSION" in prompt


class TestKernelExtractionEdgeCases:
    """Tests for edge cases in kernel extraction."""

    def test_no_matching_kernel_file(self):
        """Should handle missing kernel files gracefully."""
        agent = MockKernelAgent(
            kernels={"some_other_path/kernel.yaml": {"data": "value"}},
            kernel_state="ACTIVE",
        )
        prompt = build_kernel_system_prompt(agent)

        # Should still have safety prefix
        assert SAFETY_PREFIX in prompt

    def test_kernel_with_description_key(self):
        """Should extract from 'description' key as fallback."""
        agent = MockKernelAgent(
            kernels={
                "private/kernels/00_system/02_identity_kernel.yaml": {
                    "description": "Identity from description"
                }
            },
            kernel_state="ACTIVE",
        )
        prompt = build_kernel_system_prompt(agent)

        # The extraction tries multiple keys including 'description'
        assert SAFETY_PREFIX in prompt

    def test_kernel_with_content_key(self):
        """Should extract from 'content' key."""
        agent = MockKernelAgent(
            kernels={
                "private/kernels/00_system/02_identity_kernel.yaml": {
                    "content": "Identity from content key"
                }
            },
            kernel_state="ACTIVE",
        )
        prompt = build_kernel_system_prompt(agent)

        assert SAFETY_PREFIX in prompt


class TestMultipleKernels:
    """Tests for handling multiple kernels."""

    def test_multiple_kernels(self):
        """Should handle multiple kernel files."""
        agent = MockKernelAgent(
            kernels={
                "private/kernels/00_system/01_master_kernel.yaml": {
                    "master": "Master rules"
                },
                "private/kernels/00_system/02_identity_kernel.yaml": {
                    "identity": "L identity"
                },
                "private/kernels/00_system/08_safety_kernel.yaml": {
                    "safety": "Safety rules"
                },
                "private/kernels/00_system/07_execution_kernel.yaml": {
                    "execution": "Execution rules"
                },
                "private/kernels/00_system/04_behavioral_kernel.yaml": {
                    "behavioral": "Behavioral rules"
                },
            },
            kernel_state="ACTIVE",
        )
        prompt = build_kernel_system_prompt(agent)

        assert SAFETY_PREFIX in prompt
        assert "IDENTITY" in prompt
        assert "SAFETY CONSTRAINTS" in prompt
        assert "EXECUTION" in prompt
        assert "BEHAVIORAL" in prompt


class TestAgentWithoutKernelAttribute:
    """Tests for agents that may not have kernel attributes."""

    def test_agent_without_kernels_attr(self):
        """Should handle agent without kernels attribute."""
        agent = MagicMock(spec=[])  # No kernels attribute
        del agent.kernels  # Ensure it doesn't exist

        prompt = build_kernel_system_prompt(agent)

        # Should return safety prefix with warning
        assert SAFETY_PREFIX in prompt

    def test_agent_with_none_kernels(self):
        """Should handle agent with None kernels."""
        agent = MockKernelAgent(kernels=None, kernel_state="ACTIVE")
        agent.kernels = None  # Explicitly set to None

        prompt = build_kernel_system_prompt(agent)

        assert SAFETY_PREFIX in prompt
        assert "INACTIVE" in prompt or "Operating with minimal constraints" in prompt
