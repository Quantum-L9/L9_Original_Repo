"""
Unit Tests: MCP Tools
=====================

Tests for MCP protocol tools.

Version: 1.0.0
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestMcpListServers:
    """Tests for mcp_list_servers tool."""

    @pytest.mark.asyncio
    async def test_mcp_list_servers_success(self):
        """mcp_list_servers returns configured servers."""
        from runtime.mcp_tools import mcp_list_servers

        mock_client = MagicMock()
        mock_client._servers = {
            "github": {"enabled": True, "type": "stdio"},
            "notion": {"enabled": False, "type": "http"},
        }
        mock_client.get_allowed_tools = MagicMock(
            return_value=["create_issue", "search"]
        )

        with patch("runtime.mcp_tools.get_mcp_client", return_value=mock_client):
            result = await mcp_list_servers()

        assert result["status"] == "success"
        assert result["count"] == 2
        assert any(s["server_id"] == "github" for s in result["servers"])

    @pytest.mark.asyncio
    async def test_mcp_list_servers_error(self):
        """mcp_list_servers returns error on failure."""
        from runtime.mcp_tools import mcp_list_servers

        with patch(
            "runtime.mcp_tools.get_mcp_client", side_effect=Exception("Client error")
        ):
            result = await mcp_list_servers()

        assert result["status"] == "error"
        assert "error" in result


class TestMcpListTools:
    """Tests for mcp_list_tools tool."""

    @pytest.mark.asyncio
    async def test_mcp_list_tools_available_server(self):
        """mcp_list_tools returns tools for available server."""
        from runtime.mcp_tools import mcp_list_tools

        mock_tool = MagicMock()
        mock_tool.to_dict.return_value = {
            "name": "create_issue",
            "description": "Create GitHub issue",
        }

        mock_client = MagicMock()
        mock_client.is_server_available.return_value = True
        mock_client.list_tools = AsyncMock(return_value=[mock_tool])

        with patch("runtime.mcp_tools.get_mcp_client", return_value=mock_client):
            result = await mcp_list_tools(server_id="github")

        assert result["status"] == "success"
        assert result["server_id"] == "github"
        assert result["count"] == 1

    @pytest.mark.asyncio
    async def test_mcp_list_tools_unavailable_server(self):
        """mcp_list_tools returns error for unavailable server."""
        from runtime.mcp_tools import mcp_list_tools

        mock_client = MagicMock()
        mock_client.is_server_available.return_value = False

        with patch("runtime.mcp_tools.get_mcp_client", return_value=mock_client):
            result = await mcp_list_tools(server_id="nonexistent")

        assert result["status"] == "error"
        assert "not configured" in result["error"]


class TestMcpCallTool:
    """Tests for mcp_call_tool tool."""

    @pytest.mark.asyncio
    async def test_mcp_call_tool_success(self):
        """mcp_call_tool returns result on success."""
        from runtime.mcp_tools import mcp_call_tool

        mock_client = MagicMock()
        mock_client.call_tool = AsyncMock(
            return_value={
                "success": True,
                "result": {"issue_id": 123, "url": "https://..."},
            }
        )

        with patch("runtime.mcp_tools.get_mcp_client", return_value=mock_client):
            result = await mcp_call_tool(
                server_id="github",
                tool_name="create_issue",
                arguments={"owner": "org", "repo": "repo", "title": "Bug"},
            )

        assert result["status"] == "success"
        assert result["tool_name"] == "create_issue"
        assert result["result"]["issue_id"] == 123

    @pytest.mark.asyncio
    async def test_mcp_call_tool_failure(self):
        """mcp_call_tool returns error on tool failure."""
        from runtime.mcp_tools import mcp_call_tool

        mock_client = MagicMock()
        mock_client.call_tool = AsyncMock(
            return_value={"success": False, "error": "Permission denied"}
        )

        with patch("runtime.mcp_tools.get_mcp_client", return_value=mock_client):
            result = await mcp_call_tool(
                server_id="github",
                tool_name="delete_repo",
                arguments={"owner": "org", "repo": "repo"},
            )

        assert result["status"] == "error"
        assert "Permission denied" in result["error"]

    @pytest.mark.asyncio
    async def test_mcp_call_tool_default_empty_arguments(self):
        """mcp_call_tool handles None arguments."""
        from runtime.mcp_tools import mcp_call_tool

        mock_client = MagicMock()
        mock_client.call_tool = AsyncMock(return_value={"success": True, "result": {}})

        with patch("runtime.mcp_tools.get_mcp_client", return_value=mock_client):
            result = await mcp_call_tool(
                server_id="test",
                tool_name="no_args_tool",
                arguments=None,
            )

        assert result["status"] == "success"
        mock_client.call_tool.assert_called_with("test", "no_args_tool", {})
