"""
Tests for Graph-Backed Agent State
==================================

Unit tests for the graph_state package:
- schema.py: Cypher queries
- bootstrap_l_graph.py: Graph initialization
- agent_graph_loader.py: State loading
- graph_hydrator.py: State hydration

Version: 1.0.0
Created: 2026-01-05
"""

import pytest
from unittest.mock import AsyncMock, MagicMock


# =============================================================================
# Test Schema Constants
# =============================================================================

def test_schema_constants():
    """Test that schema constants are defined correctly."""
    from core.agents.graph_state.schema import (
        AGENT_LABEL,
        RESPONSIBILITY_LABEL,
        DIRECTIVE_LABEL,
        SOP_LABEL,
        TOOL_LABEL,
        HAS_RESPONSIBILITY,
        HAS_DIRECTIVE,
        HAS_SOP,
        CAN_EXECUTE,
        REPORTS_TO,
        COLLABORATES_WITH,
    )
    
    assert AGENT_LABEL == "Agent"
    assert RESPONSIBILITY_LABEL == "Responsibility"
    assert DIRECTIVE_LABEL == "Directive"
    assert SOP_LABEL == "SOP"
    assert TOOL_LABEL == "Tool"
    
    assert HAS_RESPONSIBILITY == "HAS_RESPONSIBILITY"
    assert HAS_DIRECTIVE == "HAS_DIRECTIVE"
    assert HAS_SOP == "HAS_SOP"
    assert CAN_EXECUTE == "CAN_EXECUTE"
    assert REPORTS_TO == "REPORTS_TO"
    assert COLLABORATES_WITH == "COLLABORATES_WITH"


def test_load_agent_state_query_structure():
    """Test that LOAD_AGENT_STATE_QUERY has expected structure."""
    from core.agents.graph_state.schema import LOAD_AGENT_STATE_QUERY
    
    # Should match on agent_id
    assert "$agent_id" in LOAD_AGENT_STATE_QUERY
    
    # Should query all relationship types
    assert "HAS_RESPONSIBILITY" in LOAD_AGENT_STATE_QUERY
    assert "HAS_DIRECTIVE" in LOAD_AGENT_STATE_QUERY
    assert "HAS_SOP" in LOAD_AGENT_STATE_QUERY
    assert "CAN_EXECUTE" in LOAD_AGENT_STATE_QUERY
    assert "REPORTS_TO" in LOAD_AGENT_STATE_QUERY
    assert "COLLABORATES_WITH" in LOAD_AGENT_STATE_QUERY
    
    # Should collect related nodes
    assert "collect(DISTINCT" in LOAD_AGENT_STATE_QUERY


# =============================================================================
# Test Bootstrap Configuration
# =============================================================================

def test_l_agent_config():
    """Test L agent configuration is complete."""
    from core.agents.graph_state.bootstrap_l_graph import L_AGENT_CONFIG
    
    assert L_AGENT_CONFIG["agent_id"] == "L"
    assert L_AGENT_CONFIG["designation"] == "Chief Technology Officer"
    assert "authority_level" in L_AGENT_CONFIG


def test_l_responsibilities():
    """Test L has required responsibilities."""
    from core.agents.graph_state.bootstrap_l_graph import L_RESPONSIBILITIES
    
    assert len(L_RESPONSIBILITIES) >= 3
    
    titles = [r["title"] for r in L_RESPONSIBILITIES]
    assert "Architecture Design" in titles
    assert "Code Quality" in titles


def test_l_directives():
    """Test L has critical directives."""
    from core.agents.graph_state.bootstrap_l_graph import L_DIRECTIVES
    
    assert len(L_DIRECTIVES) >= 3
    
    # Should have at least one CRITICAL directive
    critical = [d for d in L_DIRECTIVES if d["severity"] == "CRITICAL"]
    assert len(critical) >= 2
    
    # Igor authority directive must exist
    igor_directive = [d for d in L_DIRECTIVES if "Igor" in d["text"]]
    assert len(igor_directive) >= 1


def test_l_sops():
    """Test L has standard SOPs."""
    from core.agents.graph_state.bootstrap_l_graph import L_SOPS
    
    assert len(L_SOPS) >= 2
    
    names = [s["name"] for s in L_SOPS]
    assert "code_deployment" in names
    
    # Each SOP should have steps
    for sop in L_SOPS:
        assert len(sop["steps"]) >= 3


def test_l_tools():
    """Test L has tools with approval requirements."""
    from core.agents.graph_state.bootstrap_l_graph import L_TOOLS
    
    assert len(L_TOOLS) >= 4
    
    # Shell and git should require approval
    shell = next((t for t in L_TOOLS if t["name"] == "shell"), None)
    assert shell is not None
    assert shell["requires_approval"] is True
    assert shell["risk_level"] == "HIGH"
    
    git = next((t for t in L_TOOLS if t["name"] == "git_commit"), None)
    assert git is not None
    assert git["requires_approval"] is True


# =============================================================================
# Test AgentGraphState Dataclass
# =============================================================================

def test_agent_graph_state():
    """Test AgentGraphState dataclass."""
    from core.agents.graph_state.agent_graph_loader import (
        AgentGraphState,
        AgentResponsibility,
        AgentDirective,
        AgentTool,
    )
    
    state = AgentGraphState(
        agent_id="L",
        designation="CTO",
        role="Architect",
        mission="Build L9",
        authority_level="CTO",
        responsibilities=[
            AgentResponsibility("Arch", "Design", 0),
        ],
        directives=[
            AgentDirective("Respect Igor", "governance", "CRITICAL"),
            AgentDirective("Log everything", "observability", "HIGH"),
        ],
        tools=[
            AgentTool("shell", "HIGH", True, "igor"),
            AgentTool("memory_search", "LOW", False),
        ],
    )
    
    assert state.agent_id == "L"
    
    # Test helper methods
    critical = state.get_critical_directives()
    assert len(critical) == 1
    assert critical[0].text == "Respect Igor"
    
    high_risk = state.get_high_risk_tools()
    assert len(high_risk) == 1
    assert high_risk[0].name == "shell"


# =============================================================================
# Test AgentGraphLoader
# =============================================================================

@pytest.mark.asyncio
async def test_agent_graph_loader_cache():
    """Test AgentGraphLoader caching behavior."""
    from core.agents.graph_state.agent_graph_loader import AgentGraphLoader
    
    mock_driver = MagicMock()
    loader = AgentGraphLoader(mock_driver)
    
    # Cache should be empty
    assert len(loader._cache) == 0
    
    # Invalidate should not error on empty cache
    loader.invalidate_cache("L")
    loader.invalidate_cache()  # Clear all


@pytest.mark.asyncio
async def test_agent_graph_loader_exists_check():
    """Test AgentGraphLoader.exists()."""
    from core.agents.graph_state.agent_graph_loader import AgentGraphLoader
    
    # Mock Neo4j driver and session
    mock_result = AsyncMock()
    mock_result.single = AsyncMock(return_value={"exists": True})
    
    mock_session = AsyncMock()
    mock_session.run = AsyncMock(return_value=mock_result)
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=None)
    
    mock_driver = MagicMock()
    mock_driver.session = MagicMock(return_value=mock_session)
    
    loader = AgentGraphLoader(mock_driver)
    
    exists = await loader.exists("L")
    assert exists is True


# =============================================================================
# Test GraphHydrator
# =============================================================================

def test_hydrated_agent_context():
    """Test HydratedAgentContext structure."""
    from core.agents.graph_state.graph_hydrator import HydratedAgentContext
    
    context = HydratedAgentContext(
        agent_id="L",
        designation="CTO",
        role="Architect",
        mission="Build L9",
        authority_level="CTO",
        responsibilities=["Architecture: Design systems"],
        critical_directives=["Respect Igor"],
        all_directives=[{"text": "Respect Igor", "severity": "CRITICAL"}],
        sops={"deploy": ["step1", "step2"]},
        available_tools=["shell", "memory_search"],
        tools_requiring_approval=["shell"],
        system_prompt="",
        safety_constraints=[],
        supervisor_id="igor",
    )
    
    # Test system prompt generation
    prompt = context.to_system_prompt_context()
    
    assert "Chief Technology Officer" not in prompt  # Uses designation
    assert "CTO" in prompt
    assert "Architecture: Design systems" in prompt
    assert "Respect Igor" in prompt
    assert "shell [REQUIRES APPROVAL]" in prompt
    assert "igor" in prompt


@pytest.mark.asyncio
async def test_graph_hydrator_tool_approval_check():
    """Test GraphHydrator.check_tool_approval()."""
    from core.agents.graph_state.graph_hydrator import GraphHydrator
    from core.agents.graph_state.agent_graph_loader import (
        AgentGraphState,
        AgentTool,
    )
    
    # Mock the loader
    mock_driver = MagicMock()
    hydrator = GraphHydrator(mock_driver)
    
    # Mock cached state
    mock_state = AgentGraphState(
        agent_id="L",
        designation="CTO",
        role="Architect",
        mission="Build",
        authority_level="CTO",
        tools=[
            AgentTool("shell", "HIGH", True, "igor"),
            AgentTool("memory_search", "LOW", False, None),
        ],
    )
    hydrator.loader._cache["L"] = mock_state
    
    # Check shell (requires approval)
    requires, source = await hydrator.check_tool_approval("L", "shell")
    assert requires is True
    assert source == "igor"
    
    # Check memory_search (no approval)
    requires, source = await hydrator.check_tool_approval("L", "memory_search")
    assert requires is False
    
    # Check unknown tool (default to approval required)
    requires, source = await hydrator.check_tool_approval("L", "unknown_tool")
    assert requires is True
    assert source == "igor"


# =============================================================================
# Test Module Imports
# =============================================================================

def test_package_exports():
    """Test that __init__.py exports expected symbols."""
    from core.agents.graph_state import (
        AgentGraphLoader,
        GraphHydrator,
        bootstrap_l_graph,
        AGENT_LABEL,
    )
    
    assert AgentGraphLoader is not None
    assert GraphHydrator is not None
    assert callable(bootstrap_l_graph)
    assert AGENT_LABEL == "Agent"

