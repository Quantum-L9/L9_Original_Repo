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
    """Reset the AutoRegistry singleton between tests."""
    from core.auto_registry import AutoRegistry

    registry = AutoRegistry()
    original = dict(registry._tools) if hasattr(registry, "_tools") else {}
    yield
    if hasattr(registry, "_tools"):
        registry._tools.clear()
        registry._tools.update(original)


# ---------------------------------------------------------------------------
# Bug 1 regression: tag-based filtering must EXCLUDE non-matching tools
# ---------------------------------------------------------------------------


class TestGetToolsByTagsExclusion:
    """Assert that get_tools_by_tags returns ONLY tools matching the tag set."""

    def test_excludes_tools_with_non_matching_tags(self):
        """Tools without the requested tag must NOT appear in results."""
        from core.auto_registry import AutoRegistry

        registry = AutoRegistry()
        registry.register("memory_write", tags=["memory"])
        registry.register("governance_check", tags=["governance"])

        result = registry.get_tools_by_tags(["memory"])
        result_names = {t.name if hasattr(t, "name") else t for t in result}

        assert "governance_check" not in result_names, (
            "get_tools_by_tags(['memory']) must NOT return 'governance_check'"
        )

    def test_result_count_matches_expected(self):
        """Result set size must equal the number of tools that match the tag."""
        from core.auto_registry import AutoRegistry

        registry = AutoRegistry()
        registry.register("tool_a", tags=["memory"])
        registry.register("tool_b", tags=["memory"])
        registry.register("tool_c", tags=["governance"])
        registry.register("tool_d", tags=["search"])

        result = registry.get_tools_by_tags(["memory"])
        assert len(result) == 2, f"Expected 2 tools tagged 'memory', got {len(result)}"

    def test_empty_tag_set_returns_empty(self):
        """Requesting tools for an empty tag list must return no tools."""
        from core.auto_registry import AutoRegistry

        registry = AutoRegistry()
        registry.register("tool_a", tags=["memory"])

        result = registry.get_tools_by_tags([])
        assert len(result) == 0, "Empty tag request must yield empty result"

    def test_nonexistent_tag_returns_empty(self):
        """A tag not present on any tool must return an empty result set."""
        from core.auto_registry import AutoRegistry

        registry = AutoRegistry()
        registry.register("tool_a", tags=["memory"])

        result = registry.get_tools_by_tags(["nonexistent_tag"])
        assert len(result) == 0, "Nonexistent tag must yield empty result"

    def test_multi_tag_intersection(self):
        """When multiple tags are requested, only tools matching ALL tags appear."""
        from core.auto_registry import AutoRegistry

        registry = AutoRegistry()
        registry.register("tool_full", tags=["memory", "governance"])
        registry.register("tool_partial", tags=["memory"])
        registry.register("tool_other", tags=["governance"])

        result = registry.get_tools_by_tags(["memory", "governance"])
        result_names = {t.name if hasattr(t, "name") else t for t in result}

        assert "tool_partial" not in result_names, (
            "tool_partial only has 'memory' tag, must be excluded from multi-tag query"
        )
        assert "tool_other" not in result_names, (
            "tool_other only has 'governance' tag, must be excluded"
        )

    def test_does_not_return_mcp_tools_when_not_requested(self):
        """MCP-registered tools must not leak into non-MCP tag queries."""
        from core.auto_registry import AutoRegistry

        registry = AutoRegistry()
        registry.register("native_tool", tags=["memory"])
        if hasattr(registry, "register_mcp_tool"):
            registry.register_mcp_tool("mcp_tool", tags=["mcp", "external"])

        result = registry.get_tools_by_tags(["memory"])
        result_names = {t.name if hasattr(t, "name") else t for t in result}

        assert "mcp_tool" not in result_names, (
            "MCP tools must not appear in native tag queries"
        )
