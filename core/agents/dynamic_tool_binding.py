"""
L9 Core Agents - Dynamic Tool Binding Integration
==================================================

GMP-TS-BIND: Wires dynamic tool discovery into agent initialization.

This module replaces static tool binding (passing all 73 tools at init)
with deferred loading: agents get the tool_search meta-tool, then discover
task-specific tools on demand.

Key Functions:
- bind_tools_to_agent(): Decides static vs dynamic based on feature flag
- get_static_tool_bundle(): Old behavior (all tools)
- get_dynamic_tool_bundle(): New behavior (meta-tool only)

Architecture:
- Feature flag controlled: l9_dynamic_tool_discovery
- Backwards compatible: can toggle back to static binding
- Multi-turn optimization: discovered tools cached per conversation

Benefits vs Static Binding:
- 40-70% context reduction (1 meta-tool vs 73 full tool definitions)
- Task-relevant tools only
- No "tool pollution" in irrelevant contexts
- Scales to 500+ tools without context bloat

Version: 1.0.0
Created: 2026-02-12
"""

from __future__ import annotations

# ============================================================================
__dora_meta__ = {
    "component_name": "Dynamic Tool Binding Integration",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2026-02-12T18:24:00Z",
    "updated_at": "2026-02-12T18:24:00Z",
    "layer": "foundation",
    "domain": "agent_execution",
    "module_name": "dynamic_tool_binding",
    "type": "service",
    "status": "active",
    "integrates_with": {
        "api_endpoints": ["/agent/init", "/agent/execute"],
        "datasources": ["PostgreSQL", "Redis"],
        "memory_layers": ["working_memory"],
        "imported_by": [
            "core.agents.agent_instance",
            "api.agent_endpoints",
        ],
    },
}
# ============================================================================

from typing import Any

import structlog

from config.settings import get_integration_settings
from core.tools.dynamic_discovery import (
    cache_tools,
    get_cached_tools,
)

logger = structlog.get_logger(__name__)


def _get_meta_tool_definition() -> dict[str, Any]:
    """
    Get the tool_search meta-tool definition in OpenAI format.

    Returns:
        OpenAI function calling format for tool_search
    """
    return {
        "type": "function",
        "function": {
            "name": "tool_search",
            "description": (
                "Search L9's tool catalog to find tools relevant to a task. "
                "Use this when you need a tool but aren't sure which one, or when "
                "you need to discover available tools for a complex task. "
                "Returns: List of tool definitions you can then call normally."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": (
                            "Natural language description of what you need to do. "
                            "Examples: 'search memory for project X', 'commit code to git', "
                            "'run governance check', 'query world model'"
                        ),
                    },
                    "top_k": {
                        "type": "integer",
                        "description": "Maximum number of tools to return (default 5)",
                        "default": 5,
                        "minimum": 1,
                        "maximum": 20,
                    },
                },
                "required": ["query"],
            },
        },
    }


async def bind_tools_to_agent(
    agent_id: str | None = None,
    task_id: str | None = None,
    role: str | None = None,
    force_static: bool = False,
) -> list[dict[str, Any]]:
    """
    Primary entry point: bind tools to an agent (static or dynamic).

    This function implements the decision logic for whether to use
    static binding (all tools) or dynamic binding (meta-tool only).

    Args:
        agent_id: Agent identifier (for governance filtering)
        task_id: Task/conversation ID (for multi-turn caching)
        role: Agent role (for role-based tool filtering)
        force_static: Override feature flag, force static binding

    Returns:
        List of tool definitions in OpenAI format
            - Static mode: All 73+ tools
            - Dynamic mode: [tool_search] meta-tool only

    Decision Logic:
        1. If force_static=True → static binding
        2. If l9_dynamic_tool_discovery=False → static binding
        3. If task_id provided AND cached tools exist → return cached tools
        4. Else → dynamic binding (meta-tool only)
    """
    settings = get_integration_settings()

    # Decision point: static vs dynamic
    if force_static or not settings.l9_dynamic_tool_discovery:
        logger.debug(
            "tool_binding.static_mode",
            agent_id=agent_id,
            force_static=force_static,
            feature_flag=settings.l9_dynamic_tool_discovery,
        )
        return await get_static_tool_bundle(agent_id=agent_id, role=role)

    # Multi-turn optimization: check cache first
    if task_id:
        cached_tools = await get_cached_tools(task_id)
        if cached_tools:
            logger.debug(
                "tool_binding.cache_hit",
                task_id=task_id,
                tools_count=len(cached_tools),
            )
            return cached_tools

    # Dynamic mode: return meta-tool only
    logger.info(
        "tool_binding.dynamic_mode",
        agent_id=agent_id,
        task_id=task_id,
        role=role,
    )
    return await get_dynamic_tool_bundle()


async def get_static_tool_bundle(
    agent_id: str | None = None,
    role: str | None = None,
) -> list[dict[str, Any]]:
    """
    Get all tools for static binding (legacy behavior).

    This is the OLD approach: load all tool definitions into agent context.
    Used when dynamic discovery is disabled or forced.

    Args:
        agent_id: Agent identifier (for governance filtering)
        role: Agent role (for role-based filtering)

    Returns:
        List of all available tools in OpenAI format (73+ tools)
    """
    try:
        from core.tools.base_registry import get_tool_registry

        registry = get_tool_registry()

        # Get all tools (with governance filtering if agent_id provided)
        all_tools = []
        for tool_meta in registry.list_all():
            # Apply governance filtering
            if agent_id and hasattr(tool_meta, "agent_id"):
                if tool_meta.agent_id and tool_meta.agent_id != agent_id:
                    continue

            # Apply role filtering
            if role and hasattr(tool_meta, "allowed_roles"):
                if tool_meta.allowed_roles and role not in tool_meta.allowed_roles:
                    continue

            # Convert to OpenAI format
            tool_def = {
                "type": "function",
                "function": {
                    "name": tool_meta.id,
                    "description": tool_meta.description or "No description",
                    "parameters": tool_meta.input_schema
                    or {
                        "type": "object",
                        "properties": {},
                    },
                },
            }
            all_tools.append(tool_def)

        logger.info(
            "tool_binding.static_bundle_created",
            agent_id=agent_id,
            role=role,
            tools_count=len(all_tools),
        )

        return all_tools

    except Exception as e:
        logger.error(
            "tool_binding.static_bundle_failed",
            error=str(e),
            exc_info=True,
        )
        return []


async def get_dynamic_tool_bundle() -> list[dict[str, Any]]:
    """
    Get meta-tool only for dynamic binding (new behavior).

    This is the NEW approach: load only the tool_search meta-tool.
    Agent discovers other tools on-demand via tool_search(query="...").

    Returns:
        List with single tool: [tool_search]
    """
    meta_tool = _get_meta_tool_definition()

    logger.debug(
        "tool_binding.dynamic_bundle_created",
        meta_tool_name=meta_tool["function"]["name"],
    )

    return [meta_tool]


async def cache_discovered_tools(
    task_id: str,
    tools: list[dict[str, Any]],
) -> bool:
    """
    Cache discovered tools for multi-turn reuse.

    When tool_search is called, this caches the results so subsequent
    turns in the same conversation can skip discovery.

    Args:
        task_id: Task/conversation ID
        tools: Tool definitions to cache

    Returns:
        True if cached successfully
    """
    return await cache_tools(task_id, tools)


def get_binding_mode_summary() -> dict[str, Any]:
    """
    Get summary of current binding mode configuration.

    Returns:
        Dict with:
        - mode: "static" or "dynamic"
        - feature_flag: Current flag value
        - meta_tool_available: Whether tool_search is registered
    """
    settings = get_integration_settings()

    mode = "dynamic" if settings.l9_dynamic_tool_discovery else "static"

    # Check if meta-tool is registered
    meta_tool_available = False
    try:
        from runtime.tool_registry import get_tool_executors

        executors = get_tool_executors()
        meta_tool_available = "tool_search" in executors
    except Exception:
        pass

    return {
        "mode": mode,
        "feature_flag": settings.l9_dynamic_tool_discovery,
        "meta_tool_available": meta_tool_available,
        "static_bundle_size": "73+",
        "dynamic_bundle_size": "1 (meta-tool only)",
    }


__all__ = [
    "bind_tools_to_agent",
    "cache_discovered_tools",
    "get_binding_mode_summary",
    "get_dynamic_tool_bundle",
    "get_static_tool_bundle",
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
