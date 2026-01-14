"""
Tests for Agent Self-Modify Tool
================================

Unit tests for the AgentSelfModifyTool that allows agents
to modify their own graph state within governance constraints.

Version: 1.0.0
Created: 2026-01-05
"""

import sys
from pathlib import Path

# Add project root to path for direct module imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

import pytest
from unittest.mock import AsyncMock, MagicMock

# Import directly to avoid core.tools.__init__.py chain
import importlib.util
_spec = importlib.util.spec_from_file_location(
    "agent_self_modify",
    Path(__file__).parent.parent.parent.parent / "core" / "tools" / "agent_self_modify.py"
)
_agent_self_modify = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_agent_self_modify)

AgentSelfModifyTool = _agent_self_modify.AgentSelfModifyTool
AGENT_SELF_MODIFY_TOOL_DEFINITIONS = _agent_self_modify.AGENT_SELF_MODIFY_TOOL_DEFINITIONS
create_self_modify_tool = _agent_self_modify.create_self_modify_tool


# =============================================================================
# Test Tool Definitions
# =============================================================================

def test_tool_definitions_exist():
    """Test that tool definitions are exported."""
    assert len(AGENT_SELF_MODIFY_TOOL_DEFINITIONS) == 3
    
    tool_ids = [t["tool_id"] for t in AGENT_SELF_MODIFY_TOOL_DEFINITIONS]
    assert "agent_add_directive" in tool_ids
    assert "agent_update_responsibility" in tool_ids
    assert "agent_add_sop_step" in tool_ids


def test_tool_definitions_structure():
    """Test that each tool definition has required fields."""
    required_fields = [
        "tool_id",
        "name",
        "description",
        "category",
        "scope",
        "risk_level",
        "requires_igor_approval",
        "is_destructive",
    ]
    
    for tool_def in AGENT_SELF_MODIFY_TOOL_DEFINITIONS:
        for field in required_fields:
            assert field in tool_def, f"Missing {field} in {tool_def['name']}"


def test_add_directive_requires_approval():
    """Test that add_directive tool requires Igor approval."""
    add_directive = next(
        t for t in AGENT_SELF_MODIFY_TOOL_DEFINITIONS
        if t["tool_id"] == "agent_add_directive"
    )
    
    assert add_directive["requires_igor_approval"] is True
    assert add_directive["risk_level"] == "medium"


def test_low_risk_tools_no_approval():
    """Test that low-risk tools don't require approval."""
    for tool_def in AGENT_SELF_MODIFY_TOOL_DEFINITIONS:
        if tool_def["risk_level"] == "low":
            assert tool_def["requires_igor_approval"] is False


# =============================================================================
# Test AgentSelfModifyTool Governance
# =============================================================================

@pytest.mark.asyncio
async def test_add_directive_blocks_high_without_approval():
    """Test that HIGH severity directives are blocked without Igor approval."""
    mock_driver = MagicMock()
    tool = AgentSelfModifyTool(mock_driver)
    
    result = await tool.add_directive(
        agent_id="L",
        text="Test directive",
        context="test",
        severity="HIGH",
        igor_approved=False,
    )
    
    assert result["success"] is False
    assert "Igor approval" in result["error"]
    assert result["requires_action"] == "request_igor_approval"


@pytest.mark.asyncio
async def test_add_directive_blocks_critical_without_approval():
    """Test that CRITICAL severity directives are blocked without approval."""
    
    mock_driver = MagicMock()
    tool = AgentSelfModifyTool(mock_driver)
    
    result = await tool.add_directive(
        agent_id="L",
        text="Critical test",
        context="safety",
        severity="CRITICAL",
        igor_approved=False,
    )
    
    assert result["success"] is False
    assert "CRITICAL" in result["error"]


@pytest.mark.asyncio
async def test_add_directive_allows_low_without_approval():
    """Test that LOW severity directives work without approval."""
    
    # Mock Neo4j session and result
    mock_record = {"directive_id": "test-uuid", "text": "Low risk"}
    mock_result = AsyncMock()
    mock_result.single = AsyncMock(return_value=mock_record)
    
    mock_session = AsyncMock()
    mock_session.run = AsyncMock(return_value=mock_result)
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=None)
    
    mock_driver = MagicMock()
    mock_driver.session = MagicMock(return_value=mock_session)
    
    tool = AgentSelfModifyTool(mock_driver)
    
    result = await tool.add_directive(
        agent_id="L",
        text="Low risk directive",
        context="test",
        severity="LOW",
        igor_approved=False,
    )
    
    assert result["success"] is True
    assert result["directive"] == "Low risk directive"


@pytest.mark.asyncio
async def test_add_directive_allows_high_with_approval():
    """Test that HIGH severity directives work with Igor approval."""
    
    # Mock Neo4j
    mock_record = {"directive_id": "test-uuid", "text": "High risk"}
    mock_result = AsyncMock()
    mock_result.single = AsyncMock(return_value=mock_record)
    
    mock_session = AsyncMock()
    mock_session.run = AsyncMock(return_value=mock_result)
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=None)
    
    mock_driver = MagicMock()
    mock_driver.session = MagicMock(return_value=mock_session)
    
    tool = AgentSelfModifyTool(mock_driver)
    
    result = await tool.add_directive(
        agent_id="L",
        text="High risk directive",
        context="architecture",
        severity="HIGH",
        igor_approved=True,  # Igor approved
    )
    
    assert result["success"] is True


# =============================================================================
# Test Update Responsibility
# =============================================================================

@pytest.mark.asyncio
async def test_update_responsibility_success():
    """Test successful responsibility update."""
    
    mock_record = {"title": "Architecture Design", "description": "Updated"}
    mock_result = AsyncMock()
    mock_result.single = AsyncMock(return_value=mock_record)
    
    mock_session = AsyncMock()
    mock_session.run = AsyncMock(return_value=mock_result)
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=None)
    
    mock_driver = MagicMock()
    mock_driver.session = MagicMock(return_value=mock_session)
    
    tool = AgentSelfModifyTool(mock_driver)
    
    result = await tool.update_responsibility(
        agent_id="L",
        responsibility_title="Architecture Design",
        new_description="Updated description",
    )
    
    assert result["success"] is True
    assert result["responsibility"] == "Architecture Design"


@pytest.mark.asyncio
async def test_update_responsibility_not_found():
    """Test handling of non-existent responsibility."""
    
    mock_result = AsyncMock()
    mock_result.single = AsyncMock(return_value=None)
    
    mock_session = AsyncMock()
    mock_session.run = AsyncMock(return_value=mock_result)
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=None)
    
    mock_driver = MagicMock()
    mock_driver.session = MagicMock(return_value=mock_session)
    
    tool = AgentSelfModifyTool(mock_driver)
    
    result = await tool.update_responsibility(
        agent_id="L",
        responsibility_title="Non-Existent",
        new_description="Won't work",
    )
    
    assert result["success"] is False
    assert "not found" in result["error"]


# =============================================================================
# Test Add SOP Step
# =============================================================================

@pytest.mark.asyncio
async def test_add_sop_step_success():
    """Test successful SOP step addition."""
    
    mock_record = {"name": "code_deployment", "step_count": 8}
    mock_result = AsyncMock()
    mock_result.single = AsyncMock(return_value=mock_record)
    
    mock_session = AsyncMock()
    mock_session.run = AsyncMock(return_value=mock_result)
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=None)
    
    mock_driver = MagicMock()
    mock_driver.session = MagicMock(return_value=mock_session)
    
    tool = AgentSelfModifyTool(mock_driver)
    
    result = await tool.add_sop_step(
        agent_id="L",
        sop_name="code_deployment",
        step="Verify monitoring dashboards",
    )
    
    assert result["success"] is True
    assert result["sop"] == "code_deployment"
    assert result["total_steps"] == 8


@pytest.mark.asyncio
async def test_add_sop_step_not_found():
    """Test handling of non-existent SOP."""
    
    mock_result = AsyncMock()
    mock_result.single = AsyncMock(return_value=None)
    
    mock_session = AsyncMock()
    mock_session.run = AsyncMock(return_value=mock_result)
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=None)
    
    mock_driver = MagicMock()
    mock_driver.session = MagicMock(return_value=mock_session)
    
    tool = AgentSelfModifyTool(mock_driver)
    
    result = await tool.add_sop_step(
        agent_id="L",
        sop_name="nonexistent_sop",
        step="Won't work",
    )
    
    assert result["success"] is False
    assert "SOP not found" in result["error"]


# =============================================================================
# Test Factory Function
# =============================================================================

def test_factory_function():
    """Test create_self_modify_tool factory."""
    mock_driver = MagicMock()
    tool = create_self_modify_tool(mock_driver)
    
    assert isinstance(tool, AgentSelfModifyTool)
    assert tool.neo4j is mock_driver


def test_factory_with_substrate():
    """Test factory with substrate service."""
    mock_driver = MagicMock()
    mock_substrate = MagicMock()
    
    tool = create_self_modify_tool(
        neo4j_driver=mock_driver,
        substrate_service=mock_substrate,
    )
    
    assert tool.substrate is mock_substrate

