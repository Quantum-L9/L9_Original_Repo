"""
L9 Runtime - MCP Tool Implementation
====================================

Tool implementation for mcp.call_tool that validates and calls MCP tools.

This tool is called by agent L to invoke MCP tools on external servers.

Version: 1.0.0
"""

from __future__ import annotations

from core.decorators import must_stay_async

# ============================================================================
__dora_meta__ = {
    "component_name": "MCP Tool Implementation",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2025-12-25T18:55:20Z",
    "updated_at": "2026-01-07T13:35:58Z",
    "layer": "operations",
    "domain": "runtime_operations",
    "module_name": "mcp_tool",
    "type": "service",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": [],
        "memory_layers": [],
        "imported_by": ["orchestration.long_plan_graph"],
    },
}
# ============================================================================

import time
from typing import Any

import structlog

from runtime.mcp_client import get_mcp_client

logger = structlog.get_logger(__name__)


@must_stay_async("callers use await")
async def mcp_call_tool(
    server_id: str,
    tool_name: str,
    arguments: dict[str, Any] | None = None,
    agent_id: str = "L",
) -> dict[str, Any]:
    """
    MCP call tool implementation.

    Validates server_id and tool_name against registry, then calls the MCP client.
    Logs tool calls via ToolGraph.log_tool_call.

    Args:
        server_id: MCP server identifier (e.g., "github", "notion", "vercel", "godaddy")
        tool_name: Tool name (e.g., "github.create_issue", "notion.create_page")
        arguments: Tool arguments dictionary
        agent_id: Agent identifier (default: "L")

    Returns:
        Dictionary with:
            - success: bool
            - result: Tool result (if successful)
            - error: Error message (if failed)
    """
    if not server_id:
        return {
            "success": False,
            "error": "server_id is required",
        }

    if not tool_name:
        return {
            "success": False,
            "error": "tool_name is required",
        }

    arguments = arguments or {}

    # Get MCP client
    mcp_client = get_mcp_client()

    # Validate server is available
    if not mcp_client.is_server_available(server_id):
        return {
            "success": False,
            "error": f"MCP server {server_id} is not configured or available",
        }

    # Validate tool is allowed
    if not mcp_client.is_tool_allowed(server_id, tool_name):
        return {
            "success": False,
            "error": f"Tool {tool_name} is not allowed for server {server_id}",
        }

    # Call tool with timing
    start_time = time.time()
    success = False
    result = None
    error = None

    try:
        result = await mcp_client.call_tool(
            server_id=server_id,
            tool_name=tool_name,
            arguments=arguments,
        )

        success = result.get("success", False)
        if not success:
            error = result.get("error", "Unknown error")

        logger.info(
            f"MCP tool call: server={server_id}, tool={tool_name}, success={success}"
        )

    except Exception as e:
        success = False
        error = str(e)
        logger.error(
            f"MCP tool call failed: server={server_id}, tool={tool_name}, error={error}",
            exc_info=True,
        )

    duration_ms = int((time.time() - start_time) * 1000)

    # Log tool call via ToolGraph
    try:
        # Use runtime import to avoid circular dependency
        import importlib

        module = importlib.import_module("core.tools.tool_graph")
        ToolGraph = module.ToolGraph

        await ToolGraph.log_tool_call(
            tool_name=tool_name,
            agent_id=agent_id,
            success=success,
            duration_ms=duration_ms,
            error=error,
        )

        # Also write to tool_audit memory segment
        try:
            from runtime.memory_helpers import memory_write

            await memory_write(
                segment="tool_audit",
                payload={
                    "tool_name": tool_name,
                    "server_id": server_id,
                    "agent_id": agent_id,
                    "success": success,
                    "duration_ms": duration_ms,
                    "error": error,
                },
                agent_id=agent_id,
            )
        except Exception as mem_err:
            logger.warning(f"Failed to write MCP tool audit to memory: {mem_err}")

    except Exception as e:
        logger.warning(f"Failed to log MCP tool call: {e}")

    # Return result
    if success:
        return {
            "success": True,
            "result": result.get("result") if result else None,
            "error": None,
        }
    return {
        "success": False,
        "result": None,
        "error": error or "Unknown error",
    }


__all__ = ["mcp_call_tool"]

# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "RUN-OPER-001",
    "governance_level": "medium",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [
        "core.tools.tool_graph",
        "runtime.mcp_client",
        "runtime.memory_helpers",
    ],
    "tags": [
        "async",
        "logging",
        "messaging",
        "operations",
        "runtime-operations",
        "service",
    ],
    "keywords": ["agent", "implementation", "mcp", "tool", "tools"],
    "business_value": "This tool is called by agent L to invoke MCP tools on external servers. Version: 1.0.0",
    "last_modified": "2026-01-07T13:35:58Z",
    "modified_by": "L9_Codegen_Engine",
    "change_summary": "Initial generation with DORA compliance",
}
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
