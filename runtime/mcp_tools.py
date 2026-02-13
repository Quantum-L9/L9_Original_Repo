"""
MCP (Model Context Protocol) Tools
==================================

Tools for interacting with MCP servers - listing, calling, and managing.
Migrated from runtime/l_tools.py for domain separation (GMP-123).

This module contains 7 MCP-related tools:
- Discovery: mcp_list_servers, mcp_list_tools, mcp_discover_and_register
- Execution: mcp_call_tool
- Control: mcp_start_server, mcp_stop_server, mcp_stop_all_servers

Version: 1.0.0
"""

from __future__ import annotations

from core.decorators import must_stay_async

# ============================================================================
__dora_meta__ = {
    "component_name": "MCP Tools",
    "module_version": "1.0.0",
    "created_by": "GMP-123",
    "created_at": "2026-01-24T00:00:00Z",
    "updated_at": "2026-01-24T00:00:00Z",
    "layer": "runtime",
    "domain": "tools",
    "module_name": "mcp_tools",
    "type": "tools",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": ["MCP Servers"],
        "memory_layers": [],
        "imported_by": ["runtime.tool_packages"],
    },
}
# ============================================================================

from typing import Any

import structlog

from runtime.tool_registry import register_tool

logger = structlog.get_logger(__name__)


# =============================================================================
# MCP DISCOVERY TOOLS
# =============================================================================


@register_tool(
    category="mcp", priority=10, description="List all configured MCP servers"
)
@must_stay_async("callers use await")
async def mcp_list_servers(**kwargs: Any) -> dict[str, Any]:
    """
    List all configured MCP servers.

    Returns:
        Dict with list of server IDs and their status
    """
    try:
        from runtime.mcp_client import get_mcp_client

        client = get_mcp_client()

        servers = []
        for server_id, config in client._servers.items():
            servers.append(
                {
                    "server_id": server_id,
                    "enabled": config.get("enabled", False),
                    "type": config.get("type", "stdio"),
                    "allowed_tools": client.get_allowed_tools(server_id),
                }
            )

        logger.info(f"MCP list servers: {len(servers)} configured")

        return {
            "status": "success",
            "servers": servers,
            "count": len(servers),
        }
    except Exception as e:
        logger.error(f"MCP list servers failed: {e}")
        return {"error": str(e), "status": "error"}


@register_tool(
    category="mcp", priority=10, description="List available tools from an MCP server"
)
@must_stay_async("callers use await")
async def mcp_list_tools(
    server_id: str,
    **kwargs: Any,
) -> dict[str, Any]:
    """
    List available tools from an MCP server.

    Dynamically queries the server for its tool catalog.

    Args:
        server_id: MCP server identifier (e.g., "github", "notion", "filesystem")

    Returns:
        Dict with list of tools and their schemas
    """
    try:
        from runtime.mcp_client import get_mcp_client

        client = get_mcp_client()

        if not client.is_server_available(server_id):
            return {
                "status": "error",
                "error": f"MCP server '{server_id}' is not configured or available",
                "tools": [],
            }

        tools = await client.list_tools(server_id)

        logger.info(f"MCP list tools: server={server_id} tools={len(tools)}")

        return {
            "status": "success",
            "server_id": server_id,
            "tools": [t.to_dict() for t in tools],
            "count": len(tools),
        }
    except Exception as e:
        logger.error(f"MCP list tools failed: {e}")
        return {"error": str(e), "status": "error"}


@register_tool(
    category="mcp", priority=10, description="Discover MCP tools and register in Neo4j"
)
@must_stay_async("callers use await")
async def mcp_discover_and_register(**kwargs: Any) -> dict[str, Any]:
    """
    Discover all MCP tools from all servers and register them in Neo4j.

    This is called at startup to populate the tool graph with all available
    MCP tools, enabling L to see what's available without hardcoding.

    Returns:
        Dict with registration results
    """
    try:
        # Use runtime import to avoid circular dependency
        import importlib

        module = importlib.import_module("core.tools.tool_graph")
        ToolDefinition = module.ToolDefinition
        ToolGraph = module.ToolGraph
        from runtime.mcp_client import get_mcp_client

        client = get_mcp_client()

        total_registered = 0
        results = {}

        for server_id, config in client._servers.items():
            if not config.get("enabled", False):
                continue

            try:
                tools = await client.list_tools(server_id)
                server_registered = 0

                for tool in tools:
                    # Build full tool name: server_tool (OpenAI-compatible, no dots)
                    full_name = f"{server_id}_{tool.name}"

                    # Determine risk level based on tool type
                    risk_level = "low"
                    requires_igor = False
                    is_destructive = False

                    # High-risk tools
                    if any(
                        x in tool.name.lower()
                        for x in ["merge", "delete", "deploy", "update_dns"]
                    ):
                        risk_level = "high"
                        requires_igor = True
                        is_destructive = True
                    # Medium-risk tools
                    elif any(
                        x in tool.name.lower()
                        for x in ["create", "update", "write", "push"]
                    ):
                        risk_level = "medium"
                        is_destructive = True

                    tool_def = ToolDefinition(
                        name=full_name,
                        description=tool.description
                        or f"{tool.name} via {server_id} MCP",
                        category="mcp",
                        scope="external",
                        risk_level=risk_level,
                        requires_igor_approval=requires_igor,
                        is_destructive=is_destructive,
                        external_apis=[server_id.title(), "MCP"],
                        agent_id="L",
                    )

                    if await ToolGraph.register_tool(tool_def):
                        server_registered += 1
                        total_registered += 1

                results[server_id] = {
                    "discovered": len(tools),
                    "registered": server_registered,
                }
                logger.info(
                    "MCP discover: %s -> %d/%d registered",
                    server_id,
                    server_registered,
                    len(tools),
                )

            except Exception as e:
                results[server_id] = {"error": str(e)}
                logger.warning(f"MCP discover failed for {server_id}: {e}")

        logger.info(
            "MCP auto-discovery complete: %d tools across %d servers",
            total_registered,
            len(results),
        )

        return {
            "status": "success",
            "total_registered": total_registered,
            "servers": results,
        }
    except Exception as e:
        logger.error(f"MCP discover and register failed: {e}")
        return {"error": str(e), "status": "error"}


# =============================================================================
# MCP EXECUTION TOOLS
# =============================================================================


@register_tool(category="mcp", priority=10, description="Call a tool on an MCP server")
@must_stay_async("callers use await")
async def mcp_call_tool(
    server_id: str,
    tool_name: str,
    arguments: dict[str, Any] | None = None,
    **kwargs: Any,
) -> dict[str, Any]:
    """
    Call a tool on an MCP server.

    This is the unified MCP tool caller. Use mcp_list_servers and mcp_list_tools
    to discover available servers and tools.

    Args:
        server_id: MCP server identifier (e.g., "github", "notion", "filesystem")
        tool_name: Tool name (e.g., "create_issue", "search", "read_file")
        arguments: Tool arguments dictionary

    Returns:
        Dict with tool call result

    Examples:
        # Create GitHub issue
        mcp_call_tool(server_id="github", tool_name="create_issue", arguments={
            "owner": "org", "repo": "repo", "title": "Bug", "body": "Details..."
        })

        # Search Notion
        mcp_call_tool(server_id="notion", tool_name="search", arguments={
            "query": "project notes"
        })

        # Read local file
        mcp_call_tool(server_id="filesystem", tool_name="read_file", arguments={
            "path": str(Path.home() / "Projects/L9/README.md")
        })
    """
    if arguments is None:
        arguments = {}

    try:
        from runtime.mcp_client import get_mcp_client

        client = get_mcp_client()
        result = await client.call_tool(server_id, tool_name, arguments)

        logger.info(
            "MCP call: server=%s tool=%s success=%s",
            server_id,
            tool_name,
            result.get("success"),
        )

        if result.get("success"):
            return {
                "status": "success",
                "server_id": server_id,
                "tool_name": tool_name,
                "result": result.get("result"),
            }
        return {
            "status": "error",
            "server_id": server_id,
            "tool_name": tool_name,
            "error": result.get("error", "Unknown error"),
        }
    except Exception as e:
        logger.error(f"MCP call failed: {e}")
        return {"error": str(e), "status": "error"}


# =============================================================================
# MCP SERVER CONTROL TOOLS
# =============================================================================


@register_tool(category="mcp", priority=10, description="Start an MCP server process")
@must_stay_async("callers use await")
async def mcp_start_server(
    server_id: str,
    **kwargs: Any,
) -> dict[str, Any]:
    """
    Start an MCP server process.

    Args:
        server_id: ID of the MCP server to start

    Returns:
        Dict with start result
    """
    try:
        from runtime.mcp_client import get_mcp_client

        client = get_mcp_client()

        if server_id not in client._servers:
            return {"error": f"Unknown server: {server_id}", "status": "error"}

        server = client._servers[server_id]
        await server.get("instance", server).start()

        logger.info(f"MCP server started: {server_id}")
        return {
            "status": "success",
            "server_id": server_id,
            "message": f"Server {server_id} started",
        }
    except Exception as e:
        logger.error(f"MCP start server failed: {e}")
        return {"error": str(e), "status": "error"}


@register_tool(category="mcp", priority=10, description="Stop an MCP server process")
@must_stay_async("callers use await")
async def mcp_stop_server(
    server_id: str,
    **kwargs: Any,
) -> dict[str, Any]:
    """
    Stop an MCP server process.

    Args:
        server_id: ID of the MCP server to stop

    Returns:
        Dict with stop result
    """
    try:
        from runtime.mcp_client import get_mcp_client

        client = get_mcp_client()

        if server_id not in client._servers:
            return {"error": f"Unknown server: {server_id}", "status": "error"}

        server = client._servers[server_id]
        await server.get("instance", server).stop()

        logger.info(f"MCP server stopped: {server_id}")
        return {
            "status": "success",
            "server_id": server_id,
            "message": f"Server {server_id} stopped",
        }
    except Exception as e:
        logger.error(f"MCP stop server failed: {e}")
        return {"error": str(e), "status": "error"}


@register_tool(category="mcp", priority=10, description="Stop all running MCP servers")
async def mcp_stop_all_servers(**kwargs: Any) -> dict[str, Any]:
    """
    Stop all running MCP server processes.

    Returns:
        Dict with stop results for each server
    """
    try:
        from runtime.mcp_client import get_mcp_client

        client = get_mcp_client()
        await client.stop_all_servers()

        logger.info("All MCP servers stopped")
        return {
            "status": "success",
            "message": "All MCP servers stopped",
        }
    except Exception as e:
        logger.error(f"MCP stop all servers failed: {e}")
        return {"error": str(e), "status": "error"}


# =============================================================================
# DORA FOOTER META - AUTO-GENERATED
# =============================================================================
__dora_footer__ = {
    "component_id": "RUN-MCP-TOOLS-001",
    "governance_level": "standard",
    "security_reviewed": False,
    "performance_tested": False,
    "last_audit": "2026-01-24T00:00:00Z",
}
# =============================================================================
# ============================================================================
# L9 DORA BLOCK - AUTO-UPDATED - DO NOT EDIT
# Runtime execution trace - updated automatically on every execution
# ============================================================================
__l9_trace__ = {
    "trace_id": "",
    "task": "",
    "timestamp": "",
    "patterns_used": [],
    "graph": {"nodes": [], "edges": []},
    "inputs": {},
    "outputs": {},
    "metrics": {"confidence": "", "errors_detected": [], "stability_score": ""},
}
# ============================================================================
# END L9 DORA BLOCK
# ============================================================================
