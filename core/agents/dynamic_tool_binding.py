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

from core.decorators import must_stay_async

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

from core.tools import dynamic_discovery as _discovery
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


@must_stay_async("callers use await")
async def bind_tools_to_agent(
    agent_id: str | None = None,
    task_id: str | None = None,
    role: str | None = None,
    force_static: bool = False,
    task_description: str | None = None,
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
    # Decision point: static vs dynamic
    if force_static or not _discovery.is_dynamic_discovery_enabled():
        logger.debug(
            "tool_binding.static_mode",
            agent_id=agent_id,
            force_static=force_static,
            feature_flag=_discovery.is_dynamic_discovery_enabled(),
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


@must_stay_async("callers use await")
async def get_static_tool_bundle(
    agent_id: str | None = None,
    role: str | None = None,
) -> list[dict[str, Any]]:
    """
    Get tools for static binding — the fallback when dynamic discovery is off or broken.

    Pulls from the runtime tool_executor_registry (actual @register_tool functions).
    If the registry is empty or fails, falls back to a hardcoded top-20 tool
    definition list so agents always have something to work with.

    Args:
        agent_id: Agent identifier (for governance filtering)
        role: Agent role (for role-based filtering)

    Returns:
        List of tool definitions in OpenAI format
    """
    all_tools: list[dict[str, Any]] = []

    # --- Source 1: runtime tool_executor_registry (@register_tool functions) ---
    try:
        from runtime.tool_registry import get_tool_executors

        executors = get_tool_executors()
        for tool_name, func in executors.items():
            meta = getattr(func, "_tool_metadata", {})
            desc = meta.get("description", "")
            if not desc and hasattr(func, "__doc__") and func.__doc__:
                desc = func.__doc__.strip().split("\n")[0]

            tool_def = {
                "type": "function",
                "function": {
                    "name": tool_name,
                    "description": desc or f"{tool_name} tool",
                    "parameters": {"type": "object", "properties": {}},
                },
            }
            all_tools.append(tool_def)

    except Exception as e:
        logger.warning(
            "tool_binding.registry_read_failed",
            error=str(e),
        )

    # --- Source 2: hardcoded top-20 fallback (always available, no DB needed) ---
    # These are the highest-priority tools that agents need most often.
    # They act as a safety net when the registry hasn't loaded yet.
    seen = {t["function"]["name"] for t in all_tools}
    for fallback in _STATIC_FALLBACK_TOOLS:
        if fallback["function"]["name"] not in seen:
            all_tools.append(fallback)

    logger.info(
        "tool_binding.static_bundle_created",
        agent_id=agent_id,
        role=role,
        tools_count=len(all_tools),
        from_registry=len(seen),
        from_fallback=len(all_tools) - len(seen),
    )

    return all_tools


# =============================================================================
# HARDCODED TOP-20 FALLBACK TOOLS
# =============================================================================
# These definitions are always available even when DB/Redis/registry are down.
# Selected by priority: memory ops > communication > research > execution.
# Each has a real executor in the codebase (l_tools.py or @register_tool).
# =============================================================================

_STATIC_FALLBACK_TOOLS: list[dict[str, Any]] = [
    # --- Memory (highest priority — core agent capability) ---
    {
        "type": "function",
        "function": {
            "name": "memory_search",
            "description": (
                "Search L9 memory with embeddings. Use for structured data retrieval, "
                "keyword search, and text similarity."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query text"},
                    "limit": {
                        "type": "integer",
                        "description": "Max results (default 10)",
                        "default": 10,
                    },
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "memory_write",
            "description": "Write a packet to L9 memory substrate.",
            "parameters": {
                "type": "object",
                "properties": {
                    "content": {"type": "string", "description": "Content to store"},
                    "kind": {
                        "type": "string",
                        "description": "Packet kind (REASONING, DECISION, MEMORY, LESSON)",
                    },
                    "tags": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Tags for categorization",
                    },
                },
                "required": ["content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "memory_get_packet",
            "description": "Get a specific packet by ID from memory substrate.",
            "parameters": {
                "type": "object",
                "properties": {
                    "packet_id": {
                        "type": "string",
                        "description": "UUID of the packet",
                    },
                },
                "required": ["packet_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "memory_query_packets",
            "description": "Query packets with complex filters (kind, date range, tags).",
            "parameters": {
                "type": "object",
                "properties": {
                    "kind": {"type": "string", "description": "Filter by packet kind"},
                    "limit": {
                        "type": "integer",
                        "description": "Max results",
                        "default": 20,
                    },
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "memory_hybrid_search",
            "description": "Hybrid search combining semantic embeddings + keyword matching.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query"},
                    "top_k": {
                        "type": "integer",
                        "description": "Max results",
                        "default": 10,
                    },
                },
                "required": ["query"],
            },
        },
    },
    # --- Communication (Slack — primary user interaction) ---
    {
        "type": "function",
        "function": {
            "name": "slack_send",
            "description": "Send a message to a Slack channel or DM. Supports threading via thread_ts.",
            "parameters": {
                "type": "object",
                "properties": {
                    "channel": {"type": "string", "description": "Channel ID or name"},
                    "text": {"type": "string", "description": "Message text"},
                    "thread_ts": {
                        "type": "string",
                        "description": "Thread timestamp for replies",
                    },
                },
                "required": ["channel", "text"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "slack_file_upload",
            "description": "Upload a file to a Slack channel or thread.",
            "parameters": {
                "type": "object",
                "properties": {
                    "channel": {"type": "string", "description": "Channel ID"},
                    "file_path": {"type": "string", "description": "Path to file"},
                    "title": {"type": "string", "description": "File title"},
                },
                "required": ["channel", "file_path"],
            },
        },
    },
    # --- MCP Integration (dynamic tool access) ---
    {
        "type": "function",
        "function": {
            "name": "mcp_call_tool",
            "description": "Call any tool on any MCP server (GitHub, Notion, Filesystem, etc.).",
            "parameters": {
                "type": "object",
                "properties": {
                    "server_name": {"type": "string", "description": "MCP server name"},
                    "tool_name": {"type": "string", "description": "Tool to call"},
                    "arguments": {"type": "object", "description": "Tool arguments"},
                },
                "required": ["server_name", "tool_name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "mcp_list_tools",
            "description": "List available tools from an MCP server (dynamic discovery).",
            "parameters": {
                "type": "object",
                "properties": {
                    "server_name": {"type": "string", "description": "MCP server name"},
                },
                "required": ["server_name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "mcp_list_servers",
            "description": "List all configured MCP servers and their status.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    # --- Research (knowledge acquisition) ---
    {
        "type": "function",
        "function": {
            "name": "run_research_query",
            "description": "Run a research query using the research agent pipeline.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Research question"},
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "research_agent_synthesize",
            "description": "Synthesize research findings into a coherent summary.",
            "parameters": {
                "type": "object",
                "properties": {
                    "findings": {
                        "type": "string",
                        "description": "Raw findings to synthesize",
                    },
                },
                "required": ["findings"],
            },
        },
    },
    # --- AI / LLM ---
    {
        "type": "function",
        "function": {
            "name": "llm_chat",
            "description": "Chat with OpenAI models for reasoning, analysis, or generation.",
            "parameters": {
                "type": "object",
                "properties": {
                    "prompt": {"type": "string", "description": "User prompt"},
                    "model": {
                        "type": "string",
                        "description": "Model name (default gpt-4o)",
                        "default": "gpt-4o",
                    },
                    "system": {"type": "string", "description": "System prompt"},
                },
                "required": ["prompt"],
            },
        },
    },
    # --- Knowledge Graph ---
    {
        "type": "function",
        "function": {
            "name": "world_model_query",
            "description": "Query the world model knowledge graph for entities and relationships.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Natural language query",
                    },
                },
                "required": ["query"],
            },
        },
    },
    # --- Reflection / Self-improvement ---
    {
        "type": "function",
        "function": {
            "name": "reflection_agent_reflect",
            "description": "Execute reflection on execution history to improve future performance.",
            "parameters": {
                "type": "object",
                "properties": {
                    "execution_history": {
                        "type": "string",
                        "description": "History to reflect on",
                    },
                },
                "required": ["execution_history"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "reflection_agent_analyze_failure",
            "description": "Deep root cause analysis of a failure.",
            "parameters": {
                "type": "object",
                "properties": {
                    "failure_description": {
                        "type": "string",
                        "description": "What failed",
                    },
                    "context": {"type": "string", "description": "Surrounding context"},
                },
                "required": ["failure_description"],
            },
        },
    },
    # --- Redis (task queue + cache — runtime infrastructure) ---
    {
        "type": "function",
        "function": {
            "name": "redis_get",
            "description": "Get a value from Redis cache.",
            "parameters": {
                "type": "object",
                "properties": {
                    "key": {"type": "string", "description": "Redis key"},
                },
                "required": ["key"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "redis_set",
            "description": "Set a value in Redis cache.",
            "parameters": {
                "type": "object",
                "properties": {
                    "key": {"type": "string", "description": "Redis key"},
                    "value": {"type": "string", "description": "Value to store"},
                    "ttl": {"type": "integer", "description": "TTL in seconds"},
                },
                "required": ["key", "value"],
            },
        },
    },
    # --- Execution (high-risk, approval-gated) ---
    {
        "type": "function",
        "function": {
            "name": "git_commit",
            "description": "Commit changes to git repository. Requires Igor approval.",
            "parameters": {
                "type": "object",
                "properties": {
                    "message": {"type": "string", "description": "Commit message"},
                    "files": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Files to commit",
                    },
                },
                "required": ["message"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "tool_search",
            "description": (
                "Search L9's tool catalog to find tools relevant to a task. "
                "Use when you need a tool but aren't sure which one."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "What you need to do"},
                    "top_k": {
                        "type": "integer",
                        "description": "Max tools to return",
                        "default": 5,
                    },
                },
                "required": ["query"],
            },
        },
    },
]


@must_stay_async("callers use await")
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
    enabled = _discovery.is_dynamic_discovery_enabled()

    mode = "dynamic" if enabled else "static"

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
        "feature_flag": enabled,
        "meta_tool_available": meta_tool_available,
        "static_bundle_size": "73+",
        "dynamic_bundle_size": "1 (meta-tool only)",
    }


# ============================================================================
# SPEC-ALIGNED ALIASES (expected by test_dynamic_tool_binding.py)
# These map the test-spec API to the implementation functions above.
# ============================================================================


async def get_agent_tools(
    agent_id: str | None = None,
    task_id: str | None = None,
) -> list[dict[str, Any]]:
    """
    Get the tools currently bound to an agent.

    Alias for bind_tools_to_agent — returns whatever the current
    binding mode provides (static bundle or dynamic meta-tool).

    Args:
        agent_id: Agent identifier
        task_id: Task/conversation ID (for cache lookup)

    Returns:
        List of tool definitions in OpenAI format
    """
    return await bind_tools_to_agent(agent_id=agent_id, task_id=task_id)


async def refresh_agent_tools(
    agent_id: str | None = None,
    task_id: str | None = None,
) -> list[dict[str, Any]]:
    """
    Force-refresh the tools bound to an agent (bypass cache).

    Args:
        agent_id: Agent identifier
        task_id: Task/conversation ID

    Returns:
        Fresh list of tool definitions
    """
    # Clear cache for this task, then re-bind
    if task_id:
        from core.tools.dynamic_discovery import invalidate_tool_cache

        await invalidate_tool_cache(task_id)

    return await bind_tools_to_agent(agent_id=agent_id, task_id=task_id)


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
        from core.tools.dynamic_discovery import (
            invalidate_all_tool_caches,
            invalidate_tool_cache,
        )

        if task_id:
            return await invalidate_tool_cache(task_id)
        count = await invalidate_all_tool_caches()
        return count >= 0
    except (ImportError, Exception) as e:
        logger.warning("clear_tool_cache.failed", error=str(e))
        return False


__all__ = [
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
