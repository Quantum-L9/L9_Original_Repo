"""
Tests for Tool Graph Unified Relationships
==========================================

Tests for the unified CAN_EXECUTE relationship type introduced in UKG Phase 1.
Verifies that:
- New tools use CAN_EXECUTE relationship
- Legacy HAS_TOOL queries still work (backward compat)
- Both relationship types are handled in queries

Version: 1.0.0
Created: 2026-01-05
GMP: GMP-UKG-1 (Schema Unification)
"""

import sys
from pathlib import Path
from types import ModuleType
from unittest.mock import AsyncMock, patch

import pytest

from core.decorators import must_stay_async

# Ensure project root is on path FIRST
project_root = Path(__file__).parent.parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Create a fake memory.tool_audit module to satisfy the import chain
# This prevents ModuleNotFoundError when core.tools.__init__.py loads
if "memory.tool_audit" not in sys.modules:
    fake_tool_audit = ModuleType("memory.tool_audit")
    fake_tool_audit.log_tool_invocation = AsyncMock()
    sys.modules["memory.tool_audit"] = fake_tool_audit

# Now import from the package - the fake module will be used
from core.tools.tool_graph import (
    L9_TOOLS,
    L_INTERNAL_TOOLS,
    ToolDefinition,
    ToolGraph,
    create_tool_definition,
    register_l9_tools,
    register_l_tools,
    register_tool_with_metadata,
)

# =============================================================================
# Test Relationship Constants
# =============================================================================


def test_unified_relationship_constant():
    """Test that unified relationship constant is defined."""
    assert hasattr(ToolGraph, "AGENT_TOOL_REL")
    assert ToolGraph.AGENT_TOOL_REL == "CAN_EXECUTE"


def test_legacy_relationship_constant():
    """Test that legacy relationship constant is defined for backward compat."""
    assert hasattr(ToolGraph, "LEGACY_AGENT_TOOL_REL")
    assert ToolGraph.LEGACY_AGENT_TOOL_REL == "HAS_TOOL"


# =============================================================================
# Test Tool Registration Uses Unified Relationship
# =============================================================================


@pytest.mark.asyncio
async def test_register_tool_uses_can_execute():
    """Test that register_tool creates CAN_EXECUTE relationship."""

    # Mock Neo4j client
    mock_neo4j = AsyncMock()
    mock_neo4j.create_entity = AsyncMock()
    mock_neo4j.create_relationship = AsyncMock()

    with patch.object(ToolGraph, "_get_neo4j", return_value=mock_neo4j):
        tool = ToolDefinition(
            name="test_tool",
            description="Test tool",
            agent_id="L",
        )

        result = await ToolGraph.register_tool(tool)

        assert result is True

        # Verify CAN_EXECUTE relationship was created
        relationship_calls = [
            call
            for call in mock_neo4j.create_relationship.call_args_list
            if call.kwargs.get("rel_type") == "CAN_EXECUTE"
        ]

        assert len(relationship_calls) == 1
        call = relationship_calls[0]
        assert call.kwargs["from_type"] == "Agent"
        assert call.kwargs["from_id"] == "L"
        assert call.kwargs["to_type"] == "Tool"
        assert call.kwargs["to_id"] == "test_tool"


@pytest.mark.asyncio
async def test_register_tool_without_agent_no_relationship():
    """Test that tools without agent_id don't create agent relationship."""

    mock_neo4j = AsyncMock()
    mock_neo4j.create_entity = AsyncMock()
    mock_neo4j.create_relationship = AsyncMock()

    with patch.object(ToolGraph, "_get_neo4j", return_value=mock_neo4j):
        tool = ToolDefinition(
            name="standalone_tool",
            description="Tool without agent",
            agent_id=None,  # No agent
        )

        result = await ToolGraph.register_tool(tool)

        assert result is True

        # Should not create any CAN_EXECUTE relationships
        relationship_calls = [
            call
            for call in mock_neo4j.create_relationship.call_args_list
            if call.kwargs.get("rel_type") == "CAN_EXECUTE"
        ]

        assert len(relationship_calls) == 0


# =============================================================================
# Test Catalog Query Handles Both Relationship Types
# =============================================================================


@pytest.mark.asyncio
async def test_get_l_tool_catalog_query_format():
    """Test that catalog query handles both CAN_EXECUTE and HAS_TOOL."""

    mock_neo4j = AsyncMock()
    mock_neo4j.run_query = AsyncMock(
        return_value=[
            {"t": {"name": "tool1", "category": "test"}},
            {"t": {"name": "tool2", "category": "test"}},
        ]
    )

    with patch.object(ToolGraph, "_get_neo4j", return_value=mock_neo4j):
        await ToolGraph.get_l_tool_catalog()

        # Verify query was called
        assert mock_neo4j.run_query.called

        # Get the query string
        query = mock_neo4j.run_query.call_args[0][0]

        # Should include both relationship types for backward compat
        assert "CAN_EXECUTE" in query
        assert "HAS_TOOL" in query

        # Should use DISTINCT to avoid duplicates
        assert "DISTINCT" in query


@pytest.mark.asyncio
@must_stay_async("callers use await")
async def test_get_l_tool_catalog_returns_tools():
    """Test that catalog returns properly formatted tool list."""

    mock_neo4j = AsyncMock()
    mock_neo4j.run_query = AsyncMock(
        return_value=[
            {
                "t": {
                    "name": "memory_read",
                    "description": "Read memory",
                    "category": "memory",
                    "scope": "internal",
                    "risk_level": "low",
                    "requires_igor_approval": False,
                }
            },
        ]
    )

    with patch.object(ToolGraph, "_get_neo4j", return_value=mock_neo4j):
        catalog = await ToolGraph.get_l_tool_catalog()

        assert len(catalog) == 1
        tool = catalog[0]

        assert tool["name"] == "memory_read"
        assert tool["category"] == "memory"
        assert tool["risk_level"] == "low"
        assert tool["requires_igor_approval"] is False


# =============================================================================
# Test ToolDefinition
# =============================================================================


def test_tool_definition_defaults():
    """Test ToolDefinition default values."""

    tool = ToolDefinition(name="test")

    assert tool.name == "test"
    assert tool.description == ""
    assert tool.category == "general"
    assert tool.scope == "internal"
    assert tool.risk_level == "low"
    assert tool.is_destructive is False
    assert tool.requires_confirmation is False
    assert tool.requires_igor_approval is False
    assert tool.agent_id is None
    assert tool.external_apis == []
    assert tool.internal_dependencies == []


def test_tool_definition_with_agent():
    """Test ToolDefinition with agent_id."""

    tool = ToolDefinition(
        name="agent_tool",
        description="Tool for L",
        agent_id="L",
        risk_level="high",
        requires_igor_approval=True,
    )

    assert tool.agent_id == "L"
    assert tool.risk_level == "high"
    assert tool.requires_igor_approval is True


# =============================================================================
# Test Helper Functions
# =============================================================================


def test_create_tool_definition():
    """Test create_tool_definition helper."""

    tool = create_tool_definition(
        name="helper_test",
        description="Test tool",
        category="test",
        risk_level="medium",
        agent_id="L",
    )

    assert tool.name == "helper_test"
    assert tool.description == "Test tool"
    assert tool.category == "test"
    assert tool.risk_level == "medium"
    assert tool.agent_id == "L"


@pytest.mark.asyncio
async def test_register_tool_with_metadata():
    """Test register_tool_with_metadata helper."""

    mock_neo4j = AsyncMock()
    mock_neo4j.create_entity = AsyncMock()
    mock_neo4j.create_relationship = AsyncMock()

    with patch.object(ToolGraph, "_get_neo4j", return_value=mock_neo4j):
        result = await register_tool_with_metadata(
            name="metadata_test",
            description="Test with metadata",
            category="test",
            agent_id="L",
        )

        assert result is True


# =============================================================================
# Test L9 Tool Definitions
# =============================================================================


def test_l9_tools_defined():
    """Test that L9_TOOLS are defined."""

    assert len(L9_TOOLS) >= 5

    tool_names = [t.name for t in L9_TOOLS]
    assert "web_search" in tool_names
    assert "memory_write" in tool_names


def test_l_internal_tools_defined():
    """Test that L_INTERNAL_TOOLS are defined with agent_id."""

    assert len(L_INTERNAL_TOOLS) >= 5

    # All L internal tools should have agent_id="L"
    for tool in L_INTERNAL_TOOLS:
        assert tool.agent_id == "L", f"Tool {tool.name} missing agent_id"


def test_high_risk_tools_require_approval():
    """Test that high-risk tools require Igor approval."""

    high_risk = [t for t in L_INTERNAL_TOOLS if t.risk_level == "high"]

    assert len(high_risk) >= 3  # gmp_run, git_commit, mac_agent_exec_task, etc.

    for tool in high_risk:
        assert tool.requires_igor_approval is True, (
            f"High-risk tool {tool.name} should require Igor approval"
        )


# =============================================================================
# Test Neo4j Unavailable Fallback
# =============================================================================


@pytest.mark.asyncio
async def test_register_tool_neo4j_unavailable():
    """Test graceful handling when Neo4j is unavailable."""

    with patch.object(ToolGraph, "_get_neo4j", return_value=None):
        tool = ToolDefinition(name="no_neo4j", agent_id="L")
        result = await ToolGraph.register_tool(tool)

        assert result is False


@pytest.mark.asyncio
async def test_get_catalog_neo4j_unavailable():
    """Test catalog returns empty when Neo4j unavailable."""

    with patch.object(ToolGraph, "_get_neo4j", return_value=None):
        catalog = await ToolGraph.get_l_tool_catalog()

        assert catalog == []


# =============================================================================
# Test Exports
# =============================================================================


def test_module_exports():
    """Test that module exports expected symbols."""
    # Already imported at module level
    assert ToolDefinition is not None
    assert ToolGraph is not None
    assert callable(create_tool_definition)
    assert callable(register_tool_with_metadata)
    assert isinstance(L9_TOOLS, list)
    assert callable(register_l9_tools)
    assert isinstance(L_INTERNAL_TOOLS, list)
    assert callable(register_l_tools)
