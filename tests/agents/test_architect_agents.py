"""
L9 Architect Agents Tests
=========================

Tests for architect agent implementations.
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
    from agents.architect_agent_a import ArchitectAgentA
    from agents.architect_agent_b import ArchitectAgentB
    from agents.base_agent import AgentConfig
except ImportError as e:
    pytest.skip(f"Could not import architect agents: {e}", allow_module_level=True)


# =============================================================================
# Test: ArchitectAgentA instantiation
# =============================================================================


def test_architect_agent_a_instantiation():
    """
    Contract: ArchitectAgentA can be instantiated.
    """
    agent = ArchitectAgentA()
    assert agent is not None
    assert agent.agent_name == "architect_agent_a"


# =============================================================================
# Test: ArchitectAgentB instantiation
# =============================================================================


def test_architect_agent_b_instantiation():
    """
    Contract: ArchitectAgentB can be instantiated.
    """
    agent = ArchitectAgentB()
    assert agent is not None
    assert agent.agent_name == "architect_agent_b"


# =============================================================================
# Test: Architect agents have system prompts
# =============================================================================


def test_architect_agents_have_system_prompts():
    """
    Contract: Architect agents implement get_system_prompt.
    """
    agent_a = ArchitectAgentA()
    agent_b = ArchitectAgentB()

    prompt_a = agent_a.get_system_prompt()
    prompt_b = agent_b.get_system_prompt()

    assert isinstance(prompt_a, str)
    assert len(prompt_a) > 0
    assert isinstance(prompt_b, str)
    assert len(prompt_b) > 0
