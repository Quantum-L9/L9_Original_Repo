"""
Unit Tests – Tool Registry MCP Namespace Isolation
====================================================

Tests for MCP namespace isolation in runtime/tool_registry.py.

Covers:
- register_mcp_tool(): single registration with namespace
- register_mcp_tools_batch(): batch registration
- get_tools_by_server(): per-server tool listing
- get_mcp_tool_metadata(): metadata retrieval
- resolve_mcp_tool_name(): namespace resolution
- get_tools_by_tags(): tag-based filtering
- Collision prevention between native and MCP tools

Version: 1.0.0
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
import structlog

from core.decorators import must_stay_async

logger = structlog.get_logger(__name__)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _reset_mcp_metadata():
    """Reset MCP tool metadata dict between tests to prevent leakage."""
    from runtime.tool_registry import _mcp_tool_metadata, tool_executor_registry

    original_meta = dict(_mcp_tool_metadata)
    original_ids = set(tool_executor_registry.list_ids())
    yield
    # Restore original state
    _mcp_tool_metadata.clear()
    _mcp_tool_metadata.update(original_meta)
    for tid in set(tool_executor_registry.list_ids()) - original_ids:
        try:
            tool_executor_registry.unregister(tid)
        except Exception:
            logger.debug(
                "test_tool_registry_mcp.cleanup_unregister_failed", tool_id=tid
            )


@pytest.fixture
def dummy_executor() -> MagicMock:
    """A callable mock that stands in for an MCP tool executor."""
    return MagicMock(return_value={"status": "ok"})


# ---------------------------------------------------------------------------
# register_mcp_tool
# ---------------------------------------------------------------------------


class TestRegisterMcpTool:
    """Tests for register_mcp_tool single-tool registration."""

    def test_returns_namespaced_id(self, dummy_executor: MagicMock) -> None:
        from runtime.tool_registry import register_mcp_tool

        tool_id = register_mcp_tool(
            name="create_issue",
            server_id="github",
            executor=dummy_executor,
        )
        assert tool_id == "github__create_issue"

    def test_tool_retrievable_from_registry(self, dummy_executor: MagicMock) -> None:
        from runtime.tool_registry import register_mcp_tool, tool_executor_registry

        tool_id = register_mcp_tool(
            name="deploy",
            server_id="vercel",
            executor=dummy_executor,
        )
        assert tool_executor_registry.get(tool_id) is dummy_executor

    def test_metadata_stored(self, dummy_executor: MagicMock) -> None:
        from runtime.tool_registry import get_mcp_tool_metadata, register_mcp_tool

        register_mcp_tool(
            name="search",
            server_id="notion",
            executor=dummy_executor,
            risk_level="low",
            requires_approval=False,
            tags=["read-only"],
        )
        meta = get_mcp_tool_metadata("notion__search")
        assert meta is not None
        assert meta["server_id"] == "notion"
        assert meta["original_name"] == "search"
        assert meta["risk_level"] == "low"
        assert "read-only" in meta["tags"]

    def test_default_risk_level_is_medium(self, dummy_executor: MagicMock) -> None:
        from runtime.tool_registry import get_mcp_tool_metadata, register_mcp_tool

        register_mcp_tool(name="run", server_id="ci", executor=dummy_executor)
        meta = get_mcp_tool_metadata("ci__run")
        assert meta is not None
        assert meta["risk_level"] == "medium"

    def test_no_collision_with_native_tools(self, dummy_executor: MagicMock) -> None:
        """MCP namespace must not shadow a native tool with the same base name."""
        from runtime.tool_registry import (
            register_mcp_tool,
            register_tool,
            tool_executor_registry,
        )

        # Register a native tool first
        @register_tool(name="memory_search", category="memory")
        @must_stay_async("callers use await")
        async def memory_search(**kwargs):
            return {}

        # Register an MCP tool with same base name from different server
        register_mcp_tool(
            name="memory_search",
            server_id="external",
            executor=dummy_executor,
        )
        native = tool_executor_registry.get("memory_search")
        mcp = tool_executor_registry.get("external__memory_search")
        assert native is not mcp


# ---------------------------------------------------------------------------
# register_mcp_tools_batch
# ---------------------------------------------------------------------------


class TestRegisterMcpToolsBatch:
    """Tests for batch MCP tool registration."""

    def test_batch_registers_all(self, dummy_executor: MagicMock) -> None:
        from runtime.tool_registry import register_mcp_tools_batch

        tools = [
            {"name": "list_repos", "executor": dummy_executor},
            {"name": "create_pr", "executor": dummy_executor},
            {"name": "merge_pr", "executor": dummy_executor, "risk_level": "high"},
        ]
        ids = register_mcp_tools_batch(tools, server_id="github")
        assert len(ids) == 3
        assert "github__list_repos" in ids
        assert "github__create_pr" in ids
        assert "github__merge_pr" in ids

    def test_batch_preserves_per_tool_metadata(self, dummy_executor: MagicMock) -> None:
        from runtime.tool_registry import (
            get_mcp_tool_metadata,
            register_mcp_tools_batch,
        )

        tools = [
            {
                "name": "delete_repo",
                "executor": dummy_executor,
                "risk_level": "high",
                "requires_approval": True,
            },
            {"name": "list_repos", "executor": dummy_executor, "tags": ["read-only"]},
        ]
        register_mcp_tools_batch(tools, server_id="gh")
        high = get_mcp_tool_metadata("gh__delete_repo")
        assert high is not None
        assert high["risk_level"] == "high"
        assert high["requires_approval"] is True
        ro = get_mcp_tool_metadata("gh__list_repos")
        assert ro is not None
        assert "read-only" in ro["tags"]


# ---------------------------------------------------------------------------
# get_tools_by_server
# ---------------------------------------------------------------------------


class TestGetToolsByServer:
    """Tests for retrieving tools filtered by MCP server."""

    def test_returns_only_matching_server(self, dummy_executor: MagicMock) -> None:
        from runtime.tool_registry import (
            get_tools_by_server,
            register_mcp_tools_batch,
        )

        register_mcp_tools_batch(
            [{"name": "a", "executor": dummy_executor}], server_id="s1"
        )
        register_mcp_tools_batch(
            [{"name": "b", "executor": dummy_executor}], server_id="s2"
        )
        s1_tools = get_tools_by_server("s1")
        assert "s1__a" in s1_tools
        assert "s2__b" not in s1_tools

    def test_unknown_server_returns_empty(self) -> None:
        from runtime.tool_registry import get_tools_by_server

        assert get_tools_by_server("nonexistent_server_xyz") == {}


# ---------------------------------------------------------------------------
# resolve_mcp_tool_name
# ---------------------------------------------------------------------------


class TestResolveMcpToolName:
    """Tests for namespace resolution helper."""

    def test_resolves_registered_tool(self, dummy_executor: MagicMock) -> None:
        from runtime.tool_registry import register_mcp_tool, resolve_mcp_tool_name

        register_mcp_tool(name="deploy", server_id="fly", executor=dummy_executor)
        assert resolve_mcp_tool_name("fly", "deploy") == "fly__deploy"

    def test_returns_none_for_unknown(self) -> None:
        from runtime.tool_registry import resolve_mcp_tool_name

        assert resolve_mcp_tool_name("unknown", "missing") is None


# ---------------------------------------------------------------------------
# get_tools_by_tags
# ---------------------------------------------------------------------------


class TestGetToolsByTags:
    """Tests for tag-based tool filtering."""

    def test_filters_by_single_tag(self, dummy_executor: MagicMock) -> None:
        from runtime.tool_registry import get_tools_by_tags, register_mcp_tool

        register_mcp_tool(
            name="read_doc",
            server_id="notion",
            executor=dummy_executor,
            tags=["read-only"],
        )
        register_mcp_tool(
            name="delete_page",
            server_id="notion",
            executor=dummy_executor,
            tags=["admin-only"],
        )
        ro = get_tools_by_tags(["read-only"])
        assert "notion__read_doc" in ro
        assert "notion__delete_page" not in ro

    def test_filters_by_multiple_tags(self, dummy_executor: MagicMock) -> None:
        from runtime.tool_registry import get_tools_by_tags, register_mcp_tool

        register_mcp_tool(
            name="audit_log",
            server_id="sec",
            executor=dummy_executor,
            tags=["read-only", "compliance"],
        )
        register_mcp_tool(
            name="scan",
            server_id="sec",
            executor=dummy_executor,
            tags=["read-only"],
        )
        both = get_tools_by_tags(["read-only", "compliance"])
        assert "sec__audit_log" in both
        # scan only has read-only, not compliance
        assert "sec__scan" not in both
