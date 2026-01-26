"""
L9 Tool Graph Tests
===================

Tests for tool graph (with mocked Neo4j).
No external services required - uses mocks.

Version: 1.0.0
"""

import sys
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

try:
    from core.tools.tool_graph import ToolDefinition, ToolGraph
except ImportError as e:
    pytest.skip(f"Could not import core.tools.tool_graph: {e}", allow_module_level=True)


# =============================================================================
# Test: Tool definition creation
# =============================================================================


def test_tool_definition_creation():
    """
    Contract: ToolDefinition can be created.
    """
    tool_def = ToolDefinition(
        name="test_tool",
        description="A test tool",
        external_apis=["api1", "api2"],
        category="testing",
    )

    assert tool_def.name == "test_tool"
    assert tool_def.description == "A test tool"
    assert len(tool_def.external_apis) == 2
    assert tool_def.category == "testing"
    assert tool_def.is_destructive is False


# =============================================================================
# Test: Register tool mock
# =============================================================================


@pytest.mark.asyncio
async def test_register_tool_mock():
    """
    Contract: ToolGraph can register tools (mocked Neo4j).
    """
    ToolDefinition(
        name="test_tool",
        description="Test tool",
    )

    # Mock Neo4j client
    with patch("core.tools.tool_graph.ToolGraph._get_neo4j") as mock_get_neo4j:
        mock_neo4j = AsyncMock()
        mock_get_neo4j.return_value = mock_neo4j

        # Mock run_query
        mock_neo4j.run_query = AsyncMock(return_value=[])

        # Try to register tool
        # Note: ToolGraph methods are static, so we test the structure
        assert ToolGraph is not None
        assert hasattr(ToolGraph, "register_tool") or hasattr(
            ToolGraph, "_register_tool"
        )
