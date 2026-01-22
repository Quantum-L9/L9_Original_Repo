"""
Research Graph → Tool Execution Integration Tests

Tests the flow: Research Request → Graph State → Tool Call → Result
"""

from unittest.mock import AsyncMock

import pytest

pytestmark = pytest.mark.integration


class TestResearchToolIntegration:
    """Test research graph to tool execution integration."""

    def test_tool_registry_loads(self):
        """Tool registry initializes with tools."""
        from core.tools.base_registry import ToolRegistry

        registry = ToolRegistry()
        # Should initialize without error
        assert registry is not None

    @pytest.mark.asyncio
    async def test_tool_execution_returns_result(self):
        """Tool execution returns structured result."""
        from core.tools.base_registry import (ToolMetadata, ToolRegistry,
                                              ToolType)

        registry = ToolRegistry()

        # Create a mock tool executor
        mock_tool = AsyncMock(return_value={"result": "test"})

        # Register tool with metadata
        metadata = ToolMetadata(
            id="test_tool",
            name="Test Tool",
            description="Test tool for integration",
            tool_type=ToolType.SEARCH,
            enabled=True,
        )
        registry.register(metadata, executor=mock_tool)

        # Execute tool
        result = await registry.execute_tool("test_tool", {})

        assert result is not None
        # Result may be wrapped in a response structure
        assert isinstance(result, dict)

    def test_graph_state_initialization(self):
        """Graph state initializes with required fields."""
        from services.research.graph_state import create_initial_state

        state = create_initial_state(
            query="Test query",
            thread_id="test-thread-123",
            request_id="test-request-456",
            user_id="test_user",
        )

        assert state.get("original_query") == "Test query"
        assert state.get("evidence") == []
        assert state.get("plan") == []
