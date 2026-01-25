"""
L9 Core Tools - Tool Management
===============================

Provides tool registration, selection, and dispatch for the agent executor.

Components:
- registry_adapter: Adapter that wraps existing tool registry for executor use
- tool_graph: Neo4j-backed tool dependency tracking
- tool_embeddings: pgvector-based semantic tool search (GMP-78 Phase 1)
- dynamic_discovery: Semantic tool discovery for agents (GMP-78 Phase 2)
- governance: Tool governance and approval (future)

Version: 2.0.0 (GMP-78 Dynamic Tool Discovery)

Breaking Changes (v2.0.0):
- Dynamic tool discovery is now DEFAULT behavior
- Static tool binding emits DeprecationWarning
- Set L9_DYNAMIC_TOOL_DISCOVERY=false to revert (temporary)
"""

# GMP-78 Phase 2: Dynamic Tool Discovery (PREFERRED)
# GMP-79: Multi-Turn Tool Caching (Redis)
from core.tools.dynamic_discovery import (
    cache_tools,
    discover_tools_for_task,
    get_cached_tools,
    get_discovery_stats,
    invalidate_tool_cache,
    is_dynamic_discovery_enabled,
)
from core.tools.registry_adapter import (
    ExecutorToolRegistry,
    create_executor_tool_registry,
)

# GMP-78 Phase 1: Tool Embeddings (Foundation)
from core.tools.tool_embeddings import (
    find_relevant_tools,
    sync_all_tool_embeddings,
)
from core.tools.tool_graph import L9_TOOLS, ToolDefinition, ToolGraph, register_l9_tools

__all__ = [
    # Registry (used by executor)
    "ExecutorToolRegistry",
    "create_executor_tool_registry",
    # Tool Graph (Neo4j dependency tracking)
    "ToolDefinition",
    "ToolGraph",
    "L9_TOOLS",  # DEPRECATED: Use discover_tools_for_task() instead
    "register_l9_tools",
    # Dynamic Discovery (PREFERRED - GMP-78 Phase 2)
    "discover_tools_for_task",
    "is_dynamic_discovery_enabled",
    "get_discovery_stats",
    # Multi-Turn Caching (GMP-79)
    "get_cached_tools",
    "cache_tools",
    "invalidate_tool_cache",
    # Tool Embeddings (Foundation - GMP-78 Phase 1)
    "sync_all_tool_embeddings",
    "find_relevant_tools",
]
