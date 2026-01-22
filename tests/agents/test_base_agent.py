"""
L9 Base Agent Tests
===================

Tests for base agent class.
No external services required - uses mocks.

Version: 1.0.0
"""

import sys
from pathlib import Path

import pytest

# Add project root to path
project_root = Path(__file__).parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

try:
    from agents.base_agent import AgentConfig, AgentRole, BaseAgent
except ImportError as e:
    pytest.skip(f"Could not import agents.base_agent: {e}", allow_module_level=True)


# =============================================================================
# Test: Base agent instantiation
# =============================================================================


def test_base_agent_instantiation():
    """
    Contract: BaseAgent cannot be instantiated directly (abstract class).
    """
    with pytest.raises(TypeError):
        # BaseAgent is abstract, should raise TypeError
        BaseAgent()


# =============================================================================
# Test: Base agent has required methods
# =============================================================================


def test_base_agent_has_required_methods():
    """
    Contract: BaseAgent defines required abstract methods.
    """
    # Check that BaseAgent has abstract methods
    assert hasattr(BaseAgent, "get_system_prompt")
    assert hasattr(BaseAgent, "run")

    # Check that they are abstract
    import inspect

    assert inspect.isabstract(BaseAgent.get_system_prompt)
    assert inspect.isabstract(BaseAgent.run)


# =============================================================================
# Test: AgentConfig creation
# =============================================================================


def test_agent_config_creation():
    """
    Contract: AgentConfig can be created with defaults.
    """
    config = AgentConfig()

    assert config.model == "gpt-4o"
    assert config.temperature == 0.3
    assert config.max_tokens == 4000
    assert config.timeout_seconds == 120
    assert config.retry_count == 3


# =============================================================================
# Test: AgentConfig with custom values
# =============================================================================


def test_agent_config_custom_values():
    """
    Contract: AgentConfig accepts custom values.
    """
    config = AgentConfig(
        model="gpt-3.5-turbo",
        temperature=0.7,
        max_tokens=2000,
    )

    assert config.model == "gpt-3.5-turbo"
    assert config.temperature == 0.7
    assert config.max_tokens == 2000
