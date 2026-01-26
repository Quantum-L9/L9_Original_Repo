"""
Tests for agents.agent_registry module.

Test suite for the agent auto-discovery system.
"""

import pytest

from agents.agent_registry import (
    agent_registry,
    build_agent_exports,
    get_agent_snapshot,
    get_agents_by_category,
    get_agents_by_role,
    get_all_agents,
    register_agent,
)

# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def clean_registry():
    """Clean the agent registry before each test."""
    # Save original state
    original_components = agent_registry._components.copy()
    original_metadata = agent_registry._metadata.copy()
    original_factories = agent_registry._factories.copy()

    # Clear registry
    agent_registry._components.clear()
    agent_registry._metadata.clear()
    agent_registry._factories.clear()

    yield agent_registry

    # Restore original state
    agent_registry._components = original_components
    agent_registry._metadata = original_metadata
    agent_registry._factories = original_factories


# =============================================================================
# Basic Registration Tests
# =============================================================================


def test_register_agent_decorator(clean_registry):
    """Test registering an agent with decorator."""

    @register_agent(role="architect", category="primary")
    class TestArchitectAgent:
        def __init__(self, config):
            self.config = config

    agents = get_all_agents()
    assert "TestArchitectAgent" in agents
    assert agents["TestArchitectAgent"] == TestArchitectAgent


def test_register_agent_with_custom_name(clean_registry):
    """Test registering an agent with custom name."""

    @register_agent(name="custom_agent", role="custom")
    class MyCustomAgent:
        pass

    agents = get_all_agents()
    assert "custom_agent" in agents
    assert agents["custom_agent"] == MyCustomAgent


def test_register_multiple_agents(clean_registry):
    """Test registering multiple agents."""

    @register_agent(role="architect")
    class ArchitectAgentA:
        pass

    @register_agent(role="coder")
    class CoderAgentA:
        pass

    @register_agent(role="qa")
    class QAAgent:
        pass

    agents = get_all_agents()
    assert len(agents) == 3
    assert "ArchitectAgentA" in agents
    assert "CoderAgentA" in agents
    assert "QAAgent" in agents


# =============================================================================
# Role Filtering Tests
# =============================================================================


def test_get_agents_by_role(clean_registry):
    """Test filtering agents by role."""

    @register_agent(role="architect")
    class ArchitectAgentA:
        pass

    @register_agent(role="architect")
    class ArchitectAgentB:
        pass

    @register_agent(role="coder")
    class CoderAgentA:
        pass

    architects = get_agents_by_role("architect")
    assert len(architects) == 2
    assert "ArchitectAgentA" in architects
    assert "ArchitectAgentB" in architects

    coders = get_agents_by_role("coder")
    assert len(coders) == 1
    assert "CoderAgentA" in coders


# =============================================================================
# Category Filtering Tests
# =============================================================================


def test_get_agents_by_category(clean_registry):
    """Test filtering agents by category."""

    @register_agent(role="architect", category="primary")
    class ArchitectAgentA:
        pass

    @register_agent(role="architect", category="secondary")
    class ArchitectAgentB:
        pass

    @register_agent(role="meta", category="reflection")
    class ReflectionAgent:
        pass

    primary_agents = get_agents_by_category("primary")
    assert len(primary_agents) == 1
    assert "ArchitectAgentA" in primary_agents

    secondary_agents = get_agents_by_category("secondary")
    assert len(secondary_agents) == 1
    assert "ArchitectAgentB" in secondary_agents


# =============================================================================
# Export Building Tests
# =============================================================================


def test_build_agent_exports(clean_registry):
    """Test building __all__ list."""

    @register_agent(role="architect")
    class ArchitectAgentA:
        pass

    @register_agent(role="coder")
    class CoderAgentA:
        pass

    exports = build_agent_exports()
    assert len(exports) == 2
    assert "ArchitectAgentA" in exports
    assert "CoderAgentA" in exports


# =============================================================================
# Snapshot Tests
# =============================================================================


def test_agent_snapshot(clean_registry):
    """Test getting agent registry snapshot."""

    @register_agent(role="architect")
    class ArchitectAgentA:
        pass

    @register_agent(role="coder")
    class CoderAgentA:
        pass

    snapshot = get_agent_snapshot()
    assert snapshot["registry_name"] == "agents"
    assert snapshot["component_count"] == 2


# =============================================================================
# Integration Tests
# =============================================================================


def test_agent_instantiation(clean_registry):
    """Test that registered agents can be instantiated."""

    @register_agent(role="test")
    class TestAgent:
        def __init__(self, name: str):
            self.name = name

        def greet(self):
            return f"Hello from {self.name}"

    agents = get_all_agents()
    agent_cls = agents["TestAgent"]

    # Instantiate and use
    instance = agent_cls("TestBot")
    assert instance.name == "TestBot"
    assert instance.greet() == "Hello from TestBot"
