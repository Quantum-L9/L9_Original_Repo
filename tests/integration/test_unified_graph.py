"""
Integration Tests for Unified Knowledge Graph
==============================================

Tests that Tool Graph and Graph State share Agent nodes (UKG Phase 2).

Verifies:
- Single Agent node after bootstrap + tool registration
- Both responsibilities AND tool relationships on same node
- ensure_agent_exists prevents duplicates

Version: 1.0.0
Created: 2026-01-05
GMP: GMP-UKG-2 (Graph Merge)
"""

import sys
from pathlib import Path
from types import ModuleType
from unittest.mock import AsyncMock, patch

import pytest

# Ensure project root is on path
project_root = Path(__file__).parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Create mock for memory.tool_audit to satisfy import chain
if "memory.tool_audit" not in sys.modules:
    fake_tool_audit = ModuleType("memory.tool_audit")
    fake_tool_audit.log_tool_invocation = AsyncMock()
    sys.modules["memory.tool_audit"] = fake_tool_audit

from core.agents.graph_state.schema import (CREATE_AGENT_QUERY,
                                            ENSURE_AGENT_QUERY)
from core.tools.tool_graph import ToolDefinition, ToolGraph

# =============================================================================
# Test Shared Schema Exports
# =============================================================================


def test_ensure_agent_query_exported():
    """Test that ENSURE_AGENT_QUERY is available for Tool Graph."""
    from core.agents.graph_state import ENSURE_AGENT_QUERY

    assert ENSURE_AGENT_QUERY is not None
    assert "MERGE" in ENSURE_AGENT_QUERY  # Should be idempotent
    assert "agent_id" in ENSURE_AGENT_QUERY


def test_get_agent_query_exported():
    """Test that GET_AGENT_QUERY is available."""
    from core.agents.graph_state import GET_AGENT_QUERY

    assert GET_AGENT_QUERY is not None
    assert "MATCH" in GET_AGENT_QUERY


# =============================================================================
# Test Tool Graph ensure_agent_exists
# =============================================================================


@pytest.mark.asyncio
async def test_ensure_agent_exists_method():
    """Test that ToolGraph has ensure_agent_exists method."""
    assert hasattr(ToolGraph, "ensure_agent_exists")
    assert callable(ToolGraph.ensure_agent_exists)


@pytest.mark.asyncio
async def test_ensure_agent_exists_calls_shared_query():
    """Test that ensure_agent_exists uses the shared query."""
    mock_neo4j = AsyncMock()
    mock_neo4j.run_query = AsyncMock(return_value=[{"agent_id": "L", "created": False}])

    with patch.object(ToolGraph, "_get_neo4j", return_value=mock_neo4j):
        result = await ToolGraph.ensure_agent_exists("L")

        assert result is True
        assert mock_neo4j.run_query.called

        # Verify it used the ENSURE_AGENT_QUERY pattern
        query = mock_neo4j.run_query.call_args[0][0]
        assert "MERGE" in query
        assert "agent_id" in query


@pytest.mark.asyncio
async def test_ensure_agent_exists_neo4j_unavailable():
    """Test graceful handling when Neo4j unavailable."""
    with patch.object(ToolGraph, "_get_neo4j", return_value=None):
        result = await ToolGraph.ensure_agent_exists("L")
        assert result is False


# =============================================================================
# Test register_tool Uses ensure_agent_exists
# =============================================================================


@pytest.mark.asyncio
async def test_register_tool_ensures_agent_first():
    """Test that register_tool calls ensure_agent_exists for agent tools."""
    mock_neo4j = AsyncMock()
    mock_neo4j.create_entity = AsyncMock()
    mock_neo4j.create_relationship = AsyncMock()
    mock_neo4j.run_query = AsyncMock(return_value=[{"agent_id": "L", "created": False}])

    with patch.object(ToolGraph, "_get_neo4j", return_value=mock_neo4j):
        tool = ToolDefinition(
            name="test_tool",
            description="Test tool",
            agent_id="L",
        )

        result = await ToolGraph.register_tool(tool)

        assert result is True

        # Verify run_query was called (for ensure_agent_exists)
        assert mock_neo4j.run_query.called

        # Verify CAN_EXECUTE relationship created
        rel_calls = [
            c
            for c in mock_neo4j.create_relationship.call_args_list
            if c.kwargs.get("rel_type") == "CAN_EXECUTE"
        ]
        assert len(rel_calls) == 1


@pytest.mark.asyncio
async def test_register_tool_without_agent_no_ensure():
    """Test that tools without agent_id don't call ensure_agent_exists."""
    mock_neo4j = AsyncMock()
    mock_neo4j.create_entity = AsyncMock()
    mock_neo4j.create_relationship = AsyncMock()
    mock_neo4j.run_query = AsyncMock(return_value=[])

    with patch.object(ToolGraph, "_get_neo4j", return_value=mock_neo4j):
        tool = ToolDefinition(
            name="standalone_tool",
            description="No agent",
            agent_id=None,
        )

        result = await ToolGraph.register_tool(tool)

        assert result is True

        # run_query should NOT have been called (no agent to ensure)
        assert not mock_neo4j.run_query.called


# =============================================================================
# Test Single Agent Node (Integration Mock)
# =============================================================================


@pytest.mark.asyncio
async def test_unified_agent_node_scenario():
    """
    Integration scenario: bootstrap_l_graph + register_tool = single Agent node.

    Simulates:
    1. Graph State bootstraps Agent:L with responsibilities
    2. Tool Graph registers tools for Agent:L
    3. Result: ONE Agent:L node with both relationship types
    """
    # Track created nodes/relationships
    created_nodes = {}
    created_rels = []

    async def mock_create_entity(entity_type, entity_id, properties):
        key = f"{entity_type}:{entity_id}"
        if key not in created_nodes:
            created_nodes[key] = {"type": entity_type, "id": entity_id, **properties}

    async def mock_create_relationship(
        from_type, from_id, to_type, to_id, rel_type, properties=None
    ):
        created_rels.append(
            {
                "from": f"{from_type}:{from_id}",
                "to": f"{to_type}:{to_id}",
                "type": rel_type,
                "properties": properties or {},
            }
        )

    async def mock_run_query(query, params=None):
        # Simulate ENSURE_AGENT_QUERY - agent already exists
        if "MERGE" in query and "agent_id" in query:
            return [{"agent_id": params.get("agent_id"), "created": False}]
        return []

    mock_neo4j = AsyncMock()
    mock_neo4j.create_entity = mock_create_entity
    mock_neo4j.create_relationship = mock_create_relationship
    mock_neo4j.run_query = mock_run_query

    with patch.object(ToolGraph, "_get_neo4j", return_value=mock_neo4j):
        # Simulate: Graph State already created Agent:L
        await mock_create_entity("Agent", "L", {"agent_id": "L", "role": "CTO"})

        # Tool Graph registers tool
        tool = ToolDefinition(
            name="memory_read",
            description="Read memory",
            agent_id="L",
        )

        result = await ToolGraph.register_tool(tool)

        assert result is True

        # Verify: Only ONE Agent:L node
        agent_nodes = [k for k in created_nodes.keys() if k.startswith("Agent:")]
        assert len(agent_nodes) == 1
        assert "Agent:L" in agent_nodes

        # Verify: Tool was created
        assert "Tool:memory_read" in created_nodes

        # Verify: CAN_EXECUTE relationship exists
        can_execute_rels = [r for r in created_rels if r["type"] == "CAN_EXECUTE"]
        assert len(can_execute_rels) == 1
        assert can_execute_rels[0]["from"] == "Agent:L"
        assert can_execute_rels[0]["to"] == "Tool:memory_read"


# =============================================================================
# Test Query Compatibility
# =============================================================================


def test_ensure_agent_query_is_idempotent():
    """Test that ENSURE_AGENT_QUERY is safe to call multiple times."""
    assert "MERGE" in ENSURE_AGENT_QUERY  # MERGE is idempotent
    assert "ON CREATE" in ENSURE_AGENT_QUERY  # Only sets on create
    assert "ON MATCH" not in ENSURE_AGENT_QUERY or "updated_at" in ENSURE_AGENT_QUERY


def test_create_agent_query_uses_merge():
    """Test that CREATE_AGENT_QUERY also uses MERGE for idempotency."""
    assert "MERGE" in CREATE_AGENT_QUERY


# =============================================================================
# Test Relationship Types Consistency
# =============================================================================


def test_unified_relationship_type_consistency():
    """Test that Graph State and Tool Graph use same relationship type."""
    from core.agents.graph_state.schema import \
        CAN_EXECUTE as SCHEMA_CAN_EXECUTE

    assert ToolGraph.AGENT_TOOL_REL == "CAN_EXECUTE"
    assert SCHEMA_CAN_EXECUTE == "CAN_EXECUTE"
    assert ToolGraph.AGENT_TOOL_REL == SCHEMA_CAN_EXECUTE
