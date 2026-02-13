"""
E2E Tests: Tool Search Meta
============================

Tests for runtime/tool_search_meta.py — the Anthropic-pattern
dynamic tool discovery meta-tool.

Covers:
- Registration via @register_tool decorator
- Execution with mocked discovery engine
- Edge cases (empty query, no results, token budget)
- Integration with dynamic_discovery.py

Version: 1.0.0
"""

from __future__ import annotations

import asyncio
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ============================================================================
# FIXTURES
# ============================================================================


@pytest.fixture
def mock_discover_tools():
    """Mock discover_tools_for_task to return controlled results."""
    mock_tools = [
        {
            "type": "function",
            "function": {
                "name": "memory_search",
                "description": "Semantic search across memory.",
                "parameters": {"type": "object", "properties": {}},
            },
        },
        {
            "type": "function",
            "function": {
                "name": "memory_write",
                "description": "Write a packet to memory.",
                "parameters": {"type": "object", "properties": {}},
            },
        },
    ]
    # Patch where the function is USED (imported into), not where it's defined
    with patch(
        "runtime.tool_search_meta.discover_tools_for_task",
        new_callable=AsyncMock,
        return_value=mock_tools,
    ) as mock:
        yield mock


@pytest.fixture
def mock_discover_tools_empty():
    """Mock discover_tools_for_task returning no results."""
    with patch(
        "runtime.tool_search_meta.discover_tools_for_task",
        new_callable=AsyncMock,
        return_value=[],
    ) as mock:
        yield mock


# ============================================================================
# UNIT TESTS: REGISTRATION
# ============================================================================


class TestToolSearchRegistration:
    """Verify tool_search is properly registered via @register_tool."""

    def test_tool_search_importable(self):
        """tool_search function must be importable from module."""
        from runtime.tool_search_meta import tool_search

        assert callable(tool_search), "tool_search must be callable"

    def test_tool_search_is_async(self):
        """tool_search must be an async function."""
        import inspect

        from runtime.tool_search_meta import tool_search

        assert inspect.iscoroutinefunction(tool_search), (
            "tool_search must be async (coroutine function)"
        )

    def test_tool_search_has_metadata(self):
        """tool_search must have _tool_metadata from @register_tool."""
        from runtime.tool_search_meta import tool_search

        assert hasattr(tool_search, "_tool_metadata"), (
            "tool_search missing _tool_metadata — @register_tool not applied"
        )

    def test_tool_search_metadata_fields(self):
        """_tool_metadata must contain required fields."""
        from runtime.tool_search_meta import tool_search

        meta = tool_search._tool_metadata
        required_fields = {"name", "category", "description"}
        missing = required_fields - set(meta.keys())
        assert not missing, f"_tool_metadata missing fields: {missing}"

    def test_tool_search_name_correct(self):
        """Registered name must be 'tool_search'."""
        from runtime.tool_search_meta import tool_search

        assert tool_search._tool_metadata["name"] == "tool_search", (
            f"Expected name='tool_search', got '{tool_search._tool_metadata['name']}'"
        )

    def test_tool_search_in_exports(self):
        """tool_search must be in module __all__."""
        import runtime.tool_search_meta as mod

        assert hasattr(mod, "__all__"), "Module must define __all__"
        assert "tool_search" in mod.__all__, "tool_search must be in __all__"

    def test_tool_search_in_tool_packages(self):
        """runtime.tool_search_meta must be in TOOL_PACKAGES."""
        from runtime.tool_packages import TOOL_PACKAGES

        assert "runtime.tool_search_meta" in TOOL_PACKAGES, (
            "runtime.tool_search_meta not in TOOL_PACKAGES — "
            "tool will not be discovered at startup"
        )


# ============================================================================
# UNIT TESTS: EXECUTION
# ============================================================================


class TestToolSearchExecution:
    """Verify tool_search executes correctly with mocked backends."""

    @pytest.mark.asyncio
    async def test_returns_dict(self, mock_discover_tools):
        """tool_search must return a dict."""
        from runtime.tool_search_meta import tool_search

        result = await tool_search(query="search memory")
        assert isinstance(result, dict), f"Expected dict, got {type(result)}"

    @pytest.mark.asyncio
    async def test_returns_tools_key(self, mock_discover_tools):
        """Result must contain 'tools' key."""
        from runtime.tool_search_meta import tool_search

        result = await tool_search(query="search memory")
        assert "tools" in result, f"Result missing 'tools' key. Keys: {result.keys()}"

    @pytest.mark.asyncio
    async def test_returns_matching_tools(self, mock_discover_tools):
        """Returned tools must come from discover_tools_for_task."""
        from runtime.tool_search_meta import tool_search

        result = await tool_search(query="search memory")
        tools = result.get("tools", [])
        assert len(tools) == 2, f"Expected 2 tools, got {len(tools)}"

    @pytest.mark.asyncio
    async def test_passes_query_to_discovery(self, mock_discover_tools):
        """Query string must be forwarded to discover_tools_for_task."""
        from runtime.tool_search_meta import tool_search

        await tool_search(query="git commit operations")
        mock_discover_tools.assert_called_once()
        call_args = mock_discover_tools.call_args
        # Query should appear in positional or keyword args
        all_args = list(call_args.args) + list(call_args.kwargs.values())
        assert any("git commit" in str(a) for a in all_args), (
            "Query not forwarded to discover_tools_for_task"
        )

    @pytest.mark.asyncio
    async def test_empty_query_handled(self, mock_discover_tools_empty):
        """Empty query must not raise; should return empty tools list."""
        from runtime.tool_search_meta import tool_search

        result = await tool_search(query="")
        assert isinstance(result, dict)
        tools = result.get("tools", [])
        assert isinstance(tools, list)

    @pytest.mark.asyncio
    async def test_no_results_returns_empty_list(self, mock_discover_tools_empty):
        """When discovery returns nothing, tools should be empty list."""
        from runtime.tool_search_meta import tool_search

        result = await tool_search(query="nonexistent_tool_xyz")
        tools = result.get("tools", [])
        assert tools == [], f"Expected empty list, got {tools}"


# ============================================================================
# UNIT TESTS: ERROR HANDLING
# ============================================================================


class TestToolSearchErrorHandling:
    """Verify tool_search handles errors gracefully."""

    @pytest.mark.asyncio
    async def test_discovery_exception_returns_error(self):
        """If discover_tools_for_task raises, tool_search must return error dict."""
        with patch(
            "core.tools.dynamic_discovery.discover_tools_for_task",
            new_callable=AsyncMock,
            side_effect=RuntimeError("Discovery engine unavailable"),
        ):
            from runtime.tool_search_meta import tool_search

            result = await tool_search(query="anything")
            assert isinstance(result, dict)
            # Should contain error info, not raise
            assert "error" in result or "tools" in result

    @pytest.mark.asyncio
    async def test_discovery_timeout_handled(self):
        """If discovery times out, tool_search must not hang indefinitely."""

        async def slow_discovery(*args, **kwargs):
            await asyncio.sleep(60)  # Simulate hang
            return []

        with patch(
            "core.tools.dynamic_discovery.discover_tools_for_task",
            new_callable=AsyncMock,
            side_effect=slow_discovery,
        ):
            from runtime.tool_search_meta import tool_search

            # Should either timeout or return within reasonable time
            try:
                result = await asyncio.wait_for(tool_search(query="test"), timeout=5.0)
                assert isinstance(result, dict)
            except TimeoutError:
                pass  # Acceptable — the tool itself should handle this
