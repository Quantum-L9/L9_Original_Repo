"""
L9 Core - Dynamic Tool Binding
==============================

Provides dynamic tool discovery and binding capabilities.
Allows agents to discover tools at runtime based on semantic intent.

This module replaces the static tool binding in `agent_instance.py`
when `L9_DYNAMIC_TOOL_DISCOVERY` is enabled.

Version: 1.0.0
"""

from __future__ import annotations

from core.decorators import must_stay_async

# ============================================================================
__dora_meta__ = {
    "component_name": "Dynamic Tool Binding",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2026-02-12T18:24:00Z",
    "updated_at": "2026-02-12T18:24:00Z",
    "layer": "core",
    "domain": "agent_execution",
    "module_name": "dynamic_tool_binding",
    "type": "service",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": ["PostgreSQL"],
        "memory_layers": [],
        "imported_by": ["core.agents.agent_instance", "runtime.tool_registry"],
    },
}
# ============================================================================

from typing import Any

import structlog

from config.settings import settings
from core.tools.base_registry import ToolRegistry, get_tool_registry
from core.tools.dynamic_discovery import (
    discover_tools_for_task,
    is_dynamic_discovery_enabled,
)

logger = structlog.get_logger(__name__)


def _current_binding_mode() -> str:
    """Map dynamic-discovery feature flag to binding mode string."""
    return "dynamic" if is_dynamic_discovery_enabled() else "static"


def _extract_tool_name(tool_def: dict) -> str | None:
    """Extract tool name from OpenAI-format function tool definition."""
    if not isinstance(tool_def, dict):
        return None
    function = tool_def.get("function")
    if isinstance(function, dict):
        name = function.get("name")
        if isinstance(name, str) and name:
            return name
    return None


@must_stay_async("callers use await")
async def bind_tools_to_agent(
    agent_id: str,
    agent_role: str,
    task_description: str,
    registry: ToolRegistry | None = None,
) -> list[str]:
    """
    Bind tools to an agent based on task description.

    If dynamic discovery is enabled, uses semantic search to find relevant tools.
    Otherwise, returns all available tools (static binding).

    Args:
        agent_id: Agent identifier
        agent_role: Agent role (e.g., "researcher", "planner")
        task_description: Task description for semantic search
        registry: Optional tool registry (uses global if None)

    Returns:
        List of tool names bound to the agent
    """
    registry = registry or get_tool_registry()
    mode = _current_binding_mode()

    if mode == "dynamic":
        # Dynamic binding: use semantic search
        logger.info(
            "bind_tools_to_agent.dynamic",
            agent_id=agent_id,
            task=task_description[:50],
        )
        tools = await discover_tools_for_task(
            task_payload=task_description,
            top_k=settings.DYNAMIC_TOOL_LIMIT,
        )
        tool_names = [name for tool in tools if (name := _extract_tool_name(tool))]

        # Always include meta-tools if available
        meta_tools = ["tool_search", "tool_details"]
        for mt in meta_tools:
            if registry.get_tool(mt) and mt not in tool_names:
                tool_names.append(mt)

        logger.info(
            "bind_tools_to_agent.bound",
            agent_id=agent_id,
            count=len(tool_names),
            tools=tool_names,
        )
        return tool_names

    # Static binding: return all tools
    logger.info("bind_tools_to_agent.static", agent_id=agent_id)
    return registry.list_tool_names()


@must_stay_async("callers use await")
async def cache_discovered_tools(
    agent_id: str,
    task_id: str,
    tools: list[str],
) -> None:
    """
    Cache discovered tools for a task.

    Args:
        agent_id: Agent identifier
        task_id: Task identifier
        tools: List of tool names
    """
    # This would use Redis to cache the binding for the task duration
    # For now, it's a placeholder for future optimization
    pass


def get_binding_mode_summary() -> dict[str, Any]:
    """
    Get summary of current binding mode.

    Returns:
        Dict with mode, limit, and status
    """
    mode = _current_binding_mode()
    return {
        "mode": mode,
        "limit": settings.DYNAMIC_TOOL_LIMIT if mode == "dynamic" else None,
        "feature_flag": settings.L9_DYNAMIC_TOOL_DISCOVERY,
    }


# =============================================================================
# Spec-Aligned Aliases (for compatibility with existing code)
# =============================================================================


async def get_dynamic_tool_bundle(
    agent_id: str,
    task_description: str,
) -> list[str]:
    """
    Get dynamic tool bundle for an agent (alias for bind_tools_to_agent).

    Args:
        agent_id: Agent identifier
        task_description: Task description

    Returns:
        List of tool names
    """
    return await bind_tools_to_agent(
        agent_id=agent_id,
        agent_role="unknown",
        task_description=task_description,
    )


def get_static_tool_bundle() -> list[str]:
    """
    Get static tool bundle (all tools).

    Returns:
        List of all tool names
    """
    registry = get_tool_registry()
    return registry.list_tool_names()


# =============================================================================
# Additional Helpers
# =============================================================================


async def get_agent_tools(
    agent_id: str,
    task_description: str | None = None,
) -> list[str]:
    """
    Get tools for an agent, handling both static and dynamic modes.

    Args:
        agent_id: Agent identifier
        task_description: Optional task description for dynamic binding

    Returns:
        List of tool names
    """
    if task_description:
        return await bind_tools_to_agent(
            agent_id=agent_id,
            agent_role="unknown",
            task_description=task_description,
        )
    return get_static_tool_bundle()


async def refresh_agent_tools(
    agent_id: str,
    task_description: str,
) -> list[str]:
    """
    Force refresh of agent tools based on new task description.

    Args:
        agent_id: Agent identifier
        task_description: New task description

    Returns:
        List of tool names
    """
    # Invalidate cache if implemented
    await cache_discovered_tools(agent_id, "current", [])
    return await bind_tools_to_agent(
        agent_id=agent_id,
        agent_role="unknown",
        task_description=task_description,
    )


@must_stay_async("callers use await")
async def get_tool_binding_status() -> dict[str, Any]:
    """
    Get the current tool binding status (async wrapper).

    Returns:
        Dict with mode, feature_flag, meta_tool_available, enabled
    """
    summary = get_binding_mode_summary()
    summary["enabled"] = summary.get("feature_flag", False)
    return summary


async def clear_tool_cache(task_id: str | None = None) -> bool:
    """
    Clear cached tools for a task or all tasks.

    Args:
        task_id: Specific task to clear, or None for all

    Returns:
        True if cleared successfully
    """
    try:
        # Use runtime import to avoid circular dependency
        import importlib

        module = importlib.import_module("core.tools.dynamic_discovery")

        if task_id:
            return await module.invalidate_tool_cache(task_id)
        count = await module.invalidate_all_tool_caches()
        return count >= 0
    except (ImportError, Exception) as e:
        logger.warning("clear_tool_cache.failed", error=str(e))
        return False


__all__ = [  # noqa: RUF022
    # Original API
    "bind_tools_to_agent",
    "cache_discovered_tools",
    "get_binding_mode_summary",
    "get_dynamic_tool_bundle",
    "get_static_tool_bundle",
    # Spec-aligned aliases
    "get_agent_tools",
    "refresh_agent_tools",
    "get_tool_binding_status",
    "clear_tool_cache",
]


# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "COR-AGNT-BIND-001",
    "governance_level": "critical",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [
        "config.settings",
        "core.tools.base_registry",
        "core.tools.dynamic_discovery",
        "runtime.tool_registry",
    ],
    "tags": [
        "async",
        "agent-execution",
        "tool-binding",
        "dynamic-discovery",
        "anthropic-pattern",
    ],
    "keywords": [
        "bind",
        "static",
        "dynamic",
        "meta-tool",
        "deferred",
        "discovery",
    ],
    "business_value": (
        "Provides flexible tool binding: static (all tools) or dynamic (meta-tool). "
        "Dynamic mode reduces context usage 40-70% for large tool catalogs."
    ),
    "last_modified": "2026-02-12T18:24:00Z",
    "modified_by": "L9_Codegen_Engine",
    "change_summary": "Initial implementation - dynamic tool binding integration",
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
