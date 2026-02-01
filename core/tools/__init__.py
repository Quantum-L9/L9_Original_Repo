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
# GMP-TD-WIRE: Discovery tracing/observability
from core.tools.discovery_tracing import (
    DiscoveryPhase,
    DiscoveryTrace,
    DiscoveryTracer,
)

# GMP-TD-WIRE: Discovery result types + tracer
# GMP-79: Multi-turn cache invalidation
from core.tools.dynamic_discovery import (
    DiscoveryMethod,
    DiscoveryResult,
    cache_tools,
    discover_tools_for_task,
    get_cached_tools,
    get_discovery_stats,
    get_discovery_tracer,
    invalidate_all_tool_caches,
    invalidate_tool_cache,
    is_dynamic_discovery_enabled,
)
from core.tools.prompt_caching import CacheMetrics as PromptCacheMetrics
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

# GMP-TD: Semantic Discovery (uses pgvector, NOT qdrant)
from core.tools.semantic_discovery import (
    DynamicToolDiscoveryService,
    ToolContextFormatter,
    ToolStatus,
)
from core.tools.semantic_tool_search import (
    SemanticToolSearchAdapter,
    ToolSearchOptimizer,
    ToolSearchResult,
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
    # Tool Graph
    "L9_TOOLS",
    # Registry Cache
    "CacheConfig",
    "CacheMetrics",
    "CacheStrategy",
    # Prompt Caching
    "CachingMetricsCollector",
    # Discovery Types (GMP-TD-WIRE)
    "DiscoveryMethod",
    "DiscoveryPhase",
    "DiscoveryResult",
    "DiscoveryTrace",
    "DiscoveryTracer",
    # Dynamic Discovery Service
    "DynamicToolDiscoveryService",
    # Registry Adapter
    "ExecutorToolRegistry",
    "PromptCachingStrategy",
    # Semantic Tool Search (GMP-TD-WIRE)
    "SemanticToolSearchAdapter",
    "ToolContextFormatter",
    "ToolDefinition",
    "ToolGraph",
    "ToolRegistryCache",
    "ToolSearchOptimizer",
    "ToolSearchResult",
    "ToolStatus",
    # Dynamic Discovery (GMP-78 + GMP-TD-WIRE + GMP-79)
    "cache_tools",
    "create_executor_tool_registry",
    "discover_tools_for_task",
    "find_relevant_tools",
    "find_tools_hybrid",
    "find_tools_keyword",
    "get_cached_tools",
    "get_discovery_stats",
    "get_discovery_tracer",
    "invalidate_all_tool_caches",
    "invalidate_tool_cache",
    "is_dynamic_discovery_enabled",
    "register_l9_tools",
    "sync_all_tool_embeddings",
]
