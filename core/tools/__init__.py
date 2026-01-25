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
# GMP-TD: Advanced Tool Discovery (Harvested 2026-01-25)
from core.tools.anthropic_tool_search import (
    AnthropicToolSearchAdapter,
    ToolSearchOptimizer,
)

# GMP-TD-WIRE: Discovery tracing/observability
from core.tools.discovery_tracing import (
    DiscoveryPhase,
    DiscoveryTrace,
    DiscoveryTracer,
)

# GMP-TD-WIRE: Discovery result types + tracer
from core.tools.dynamic_discovery import (
    DiscoveryMethod,
    DiscoveryResult,
    cache_tools,
    discover_tools_for_task,
    get_cached_tools,
    get_discovery_stats,
    get_discovery_tracer,
    invalidate_tool_cache,
    is_dynamic_discovery_enabled,
)
from core.tools.prompt_caching import (
    CachingMetricsCollector,
    PromptCachingStrategy,
)
from core.tools.registry_adapter import (
    ExecutorToolRegistry,
    create_executor_tool_registry,
)

# GMP-124: Tool Registry Cache
from core.tools.registry_cache import (
    CacheConfig,
    CacheMetrics,
    CacheStrategy,
    ToolRegistryCache,
)
from core.tools.semantic_discovery import (
    DynamicToolDiscoveryService,
    ToolContextFormatter,
    ToolStatus,
)

# GMP-78 Phase 1: Tool Embeddings (Foundation)
# GMP-TD-WIRE: Added hybrid search (semantic + BM25)
from core.tools.tool_embeddings import (
    find_relevant_tools,
    find_tools_hybrid,
    find_tools_keyword,
    sync_all_tool_embeddings,
)
from core.tools.tool_graph import L9_TOOLS, ToolDefinition, ToolGraph, register_l9_tools

__all__ = [
    # Registry Cache
    "CacheConfig",
    "CacheMetrics",
    "CacheStrategy",
    "ToolRegistryCache",
    # Registry Adapter
    "ExecutorToolRegistry",
    "create_executor_tool_registry",
    # Tool Graph
    "L9_TOOLS",
    "ToolDefinition",
    "ToolGraph",
    "register_l9_tools",
    # Dynamic Discovery (GMP-78 + GMP-TD-WIRE)
    "cache_tools",
    "discover_tools_for_task",
    "find_relevant_tools",
    "find_tools_hybrid",
    "find_tools_keyword",
    "get_cached_tools",
    "get_discovery_stats",
    "invalidate_tool_cache",
    "is_dynamic_discovery_enabled",
    "sync_all_tool_embeddings",
    # Discovery Types (GMP-TD-WIRE)
    "DiscoveryMethod",
    "DiscoveryPhase",
    "DiscoveryResult",
    "DiscoveryTrace",
    "DiscoveryTracer",
    "get_discovery_tracer",
    # Advanced Tool Discovery (GMP-TD Harvested)
    "AnthropicToolSearchAdapter",
    "CachingMetricsCollector",
    "DynamicToolDiscoveryService",
    "PromptCachingStrategy",
    "ToolContextFormatter",
    "ToolSearchOptimizer",
    "ToolStatus",
]
