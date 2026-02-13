"""
L9 Runtime - Tool Call Wrapper
===============================

Wrapper to ensure all tool calls are logged via ToolGraph.log_tool_call.

This ensures consistent audit logging for:
- Internal tools
- MCP tools
- Mac Agent tools
- GMP tools

Version: 1.0.0
"""

from __future__ import annotations

# ============================================================================
__dora_meta__ = {
    "component_name": "Tool Call Wrapper",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2025-12-25T18:55:20Z",
    "updated_at": "2026-01-07T13:35:58Z",
    "layer": "operations",
    "domain": "runtime_operations",
    "module_name": "tool_call_wrapper",
    "type": "adapter",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": [],
        "memory_layers": [],
        "imported_by": ["runtime.long_plan_tool"],
    },
}
# ============================================================================

import time
from collections.abc import Callable, Coroutine
from functools import wraps
from typing import Any

import structlog

logger = structlog.get_logger(__name__)


async def tool_call_wrapper(
    tool_name: str,
    tool_func: Callable[..., Coroutine[Any, Any, Any]],
    agent_id: str = "L",
    *args: Any,
    **kwargs: Any,
) -> Any:
    """
    Wrap a tool call to ensure it's logged via ToolGraph.log_tool_call.

    Args:
        tool_name: Name of the tool being called
        tool_func: Async function to execute
        agent_id: Agent identifier (default: "L")
        *args: Positional arguments for tool_func
        **kwargs: Keyword arguments for tool_func

    Returns:
        Result from tool_func

    Usage:
        result = await tool_call_wrapper(
            "gmp_run",
            gmp_run_tool,
            agent_id="L",
            gmp_markdown=markdown,
            repo_root=repo,
        )
    """
    start_time = time.time()
    success = False
    error = None
    result = None

    try:
        # Execute the tool
        result = await tool_func(*args, **kwargs)

        # Determine success from result
        if isinstance(result, dict):
            success = result.get("success", True)  # Default to True if no success field
            error = result.get("error")
        else:
            success = True  # Assume success if not a dict

        logger.debug(f"Tool call {tool_name} completed: success={success}")

    except Exception as e:
        success = False
        error = str(e)
        logger.error(f"Tool call {tool_name} failed: {error}", exc_info=True)
        raise

    finally:
        # Log the tool call
        duration_ms = int((time.time() - start_time) * 1000)

        try:
            from core.tools.tool_graph import ToolGraph

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
                        "agent_id": agent_id,
                        "success": success,
                        "duration_ms": duration_ms,
                        "error": error,
                        "timestamp": time.time(),
                    },
                    agent_id=agent_id,
                )
            except Exception as mem_err:
                logger.warning(f"Failed to write tool audit to memory: {mem_err}")

        except Exception as log_err:
            logger.warning(f"Failed to log tool call: {log_err}")

        # Record observability metrics (Enhancement from GMP MCP-Tools)
        _record_tool_execution_metric(
            tool_name=tool_name,
            agent_id=agent_id,
            duration_ms=duration_ms,
            status="success" if success else "error",
            error_type=type(error).__name__
            if error and not isinstance(error, str)
            else None,
        )

    return result


def wrap_tool_function(
    tool_name: str,
    agent_id: str = "L",
) -> Callable:
    """
    Decorator to wrap a tool function with automatic logging.

    Args:
        tool_name: Name of the tool
        agent_id: Agent identifier (default: "L")

    Usage:
        @wrap_tool_function("gmp_run", agent_id="L")
        async def gmp_run_tool(...):
            ...
    """

    def decorator(func: Callable[..., Coroutine[Any, Any, Any]]) -> Callable:
        """
        Performs a decorator that wraps tool functions to ensure all calls are logged via ToolGraph.log_tool_call for consistent audit logging.

        Args:
            func: The asynchronous tool function to be decorated for logging.

        Returns:
            A wrapped asynchronous function that logs each call before execution.
        """

        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            """
            Performs asynchronous logging of tool calls to ensure consistent audit records within the ToolCallWrapper context.

            Args:
                *args: Positional arguments to pass to the wrapped tool function.
                **kwargs: Keyword arguments to pass to the wrapped tool function.
                tool_name: Name identifier for the tool being invoked.
                tool_func: The actual tool function to execute.
                agent_id: Identifier for the agent initiating the call.

            Returns:
                The result of the tool function execution, wrapped with logging.
            """
            return await tool_call_wrapper(
                tool_name=tool_name,
                tool_func=func,
                agent_id=agent_id,
                *args,
                **kwargs,
            )

        return wrapper

    return decorator


__all__ = [
    "tool_call_wrapper",
    "wrap_tool_function",
]

# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "RUN-OPER-001",
    "governance_level": "medium",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": ["core.tools.tool_graph", "runtime.memory_helpers"],
    "tags": [
        "adapter",
        "async",
        "audit-tool",
        "debugging",
        "logging",
        "operations",
        "runtime-operations",
    ],
    "keywords": [
        "agent",
        "audit",
        "decorator",
        "function",
        "gmp",
        "tool",
        "tools",
        "wrap",
    ],
    "business_value": "Internal tools MCP tools Mac Agent tools GMP tools Version: 1.0.0",
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
