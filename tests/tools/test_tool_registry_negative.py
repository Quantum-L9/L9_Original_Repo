"""
L9 Tool Registry — Negative-Path & Filter Exclusion Tests
==========================================================

Regression tests for Bug 1: get_tools_by_tags() returned ALL tools
instead of filtering by requested tags (governance bypass).

Root cause: Second loop iterated every non-MCP tool without checking
tag membership. These tests assert EXCLUSION, not just inclusion.

Reference: L9 Bug Postmortem — 5 Root Causes (2026-02-12)

Author: L9 Engineering
Created: 2026-02-12
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

# ============================================================================
__dora_meta__ = {
    "component_name": "Tool Registry Negative Tests",
    "module_version": "1.0.0",
    "created_by": "L9 Engineering",
    "created_at": "2026-02-12T03:41:00Z",
    "updated_at": "2026-02-12T03:41:00Z",
    "layer": "testing",
    "domain": "tool_registry",
    "module_name": "test_tool_registry_negative",
    "type": "test",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": [],
        "memory_layers": [],
        "imported_by": [],
    },
}
# ============================================================================


@pytest.fixture(autouse=True)
def _clean_registry():
    """Reset the global tool_executor_registry between tests."""
    from runtime.tool_registry import _mcp_tool_metadata, tool_executor_registry

    # Backup
    original_tools = dict(tool_executor_registry._components)
    original_metadata = dict(tool_executor_registry._metadata)
    original_mcp = dict(_mcp_tool_metadata)

    # Clear
    tool_executor_registry._components.clear()
    tool_executor_registry._metadata.clear()
    _mcp_tool_metadata.clear()

    yield

    # Restore
    tool_executor_registry._components.clear()
    tool_executor_registry._metadata.clear()
    _mcp_tool_metadata.clear()

    tool_executor_registry._components.update(original_tools)
    tool_executor_registry._metadata.update(original_metadata)
    _mcp_tool_metadata.update(original_mcp)


# ---------------------------------------------------------------------------
# Bug 1 regression: tag-based filtering must EXCLUDE non-matching tools
# ---------------------------------------------------------------------------


class TestGetToolsByTagsExclusion:
    """Assert that get_tools_by_tags returns ONLY tools matching the tag set."""

    def _register_dummy(self, name: str, tags: list[str]):
        from runtime.tool_registry import tool_executor_registry

        func = MagicMock()
        func.__name__ = name

        tool_executor_registry.register_instance(
            component_id=name, component=func, tags=tags, priority=0
        )

    def test_excludes_tools_with_non_matching_tags(self):
        """Tools without the requested tag must NOT appear in results."""
        from runtime.tool_registry import get_tools_by_tags

        self._register_dummy("memory_write", tags=["memory"])
        self._register_dummy("governance_check", tags=["governance"])

        result = get_tools_by_tags(["memory"])

        assert "memory_write" in result
        assert "governance_check" not in result, (
            "get_tools_by_tags(['memory']) must NOT return 'governance_check'"
        )

    def test_result_count_matches_expected(self):
        """Result set size must equal the number of tools that match the tag."""
        from runtime.tool_registry import get_tools_by_tags

        self._register_dummy("tool_a", tags=["memory"])
        self._register_dummy("tool_b", tags=["memory"])
        self._register_dummy("tool_c", tags=["governance"])
        self._register_dummy("tool_d", tags=["search"])

        result = get_tools_by_tags(["memory"])
        assert len(result) == 2, f"Expected 2 tools tagged 'memory', got {len(result)}"

    def test_empty_tag_set_returns_empty(self):
        """Requesting tools for an empty tag list must return no tools."""
        from runtime.tool_registry import get_tools_by_tags

        self._register_dummy("tool_a", tags=["memory"])

        result = get_tools_by_tags([])
        assert len(result) == 0, "Empty tag request must yield empty result"

    def test_nonexistent_tag_returns_empty(self):
        """A tag not present on any tool must return an empty result set."""
        from runtime.tool_registry import get_tools_by_tags

        self._register_dummy("tool_a", tags=["memory"])

        result = get_tools_by_tags(["nonexistent_tag"])
        assert len(result) == 0, "Nonexistent tag must yield empty result"

    def test_multi_tag_intersection(self):
        """When multiple tags are requested, only tools matching ALL tags appear."""
        from runtime.tool_registry import get_tools_by_tags

        self._register_dummy("tool_full", tags=["memory", "governance"])
        self._register_dummy("tool_partial", tags=["memory"])
        self._register_dummy("tool_other", tags=["governance"])

        result = get_tools_by_tags(["memory", "governance"])

        assert "tool_full" in result
        assert "tool_partial" not in result, (
            "tool_partial only has 'memory' tag, must be excluded from multi-tag query"
        )
        assert "tool_other" not in result, (
            "tool_other only has 'governance' tag, must be excluded"
        )

    def test_does_not_return_mcp_tools_when_not_requested(self):
        """MCP-registered tools must not leak into non-MCP tag queries."""
        from runtime.tool_registry import get_tools_by_tags, register_mcp_tool

        self._register_dummy("native_tool", tags=["memory"])

        # Register MCP tool
        register_mcp_tool(
            name="mcp_tool",
            server_id="test_server",
            executor=MagicMock(),
            tags=["mcp", "external"],
        )

        result = get_tools_by_tags(["memory"])

        assert "native_tool" in result
        # MCP tool ID is namespaced: test_server__mcp_tool
        mcp_id = "test_server__mcp_tool"
        assert mcp_id not in result, "MCP tools must not appear in native tag queries"
