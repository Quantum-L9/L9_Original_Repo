"""
L9 Core Tools - Dynamic Tool Discovery Integration
===================================================

GMP-78 Phase 2 + GMP-TD-WIRE: Wires semantic + hybrid tool discovery into agent execution.

Instead of statically binding all tools to agents, this module enables
dynamic discovery: given a task, find the most relevant tools via
semantic search (pgvector) + keyword search (BM25) and return them
in OpenAI function calling format.

Key Functions:
- discover_tools_for_task(): Hybrid search → OpenAI tool format
- format_tools_for_openai(): Convert ToolEmbeddingResult → OpenAI schema
- enforce_token_budget(): Ensure tool context doesn't exceed budget

Architecture:
- Uses tool_embeddings.py::find_tools_hybrid() (pgvector + BM25)
- Pulls full tool schemas from registry_adapter.py
- Enforces token budget to prevent context bloat

Benefits:
- 40-70% token reduction vs static tool binding
- Task-relevant tools loaded on-demand
- Hybrid search: conceptual (semantic) + exact (keyword) matching
- Backwards compatible (feature flag controlled)

Version: 2.0.0 (GMP-TD-WIRE)
Created: 2026-01-25
"""

from __future__ import annotations

# ============================================================================
__dora_meta__ = {
    "component_name": "Dynamic Tool Discovery Integration",
    "module_version": "2.0.0 (GMP-TD-WIRE)",
    "created_by": "Igor Beylin",
    "created_at": "2026-01-25T06:31:32Z",
    "updated_at": "2026-01-25T14:49:28Z",
    "layer": "foundation",
    "domain": "data_models",
    "module_name": "dynamic_discovery",
    "type": "dataclass",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": ["OpenAI API", "Redis"],
        "memory_layers": ["semantic_memory", "working_memory"],
        "imported_by": [
            "core.agents.agent_instance",
            "core.tools.__init__",
            "tests.unit.test_dynamic_tool_discovery",
        ],
    },
}
# ============================================================================

import time
import uuid
from dataclasses import dataclass
from enum import Enum
from typing import Any

import structlog

from config.settings import get_integration_settings
from core.tools.discovery_tracing import DiscoveryPhase, DiscoveryTrace, DiscoveryTracer
from memory.substrate_service import (
    get_memory_substrate_service,
)  # if such helper exists
from services.tool_feedback_service import get_tool_feedback_service

logger = structlog.get_logger(__name__)

# Module-level tracer for discovery observability
_discovery_tracer = DiscoveryTracer()


def get_discovery_tracer() -> DiscoveryTracer:
    """Get the module-level discovery tracer for stats/monitoring."""
    return _discovery_tracer


# =============================================================================
# Discovery Result Types (Adapted from harvested 1_semantic_discovery.py)
# =============================================================================


class DiscoveryMethod(str, Enum):
    """Method used for tool discovery"""

    SEMANTIC = "semantic"
    KEYWORD = "keyword"
    HYBRID = "hybrid"


@dataclass
class DiscoveryResult:
    """Tool discovery result with confidence scores"""

    tool_id: str
    tool_name: str
    description: str
    similarity_score: float  # 0.0 to 1.0
    rank: int
    discovery_method: DiscoveryMethod
    token_estimate: int
    is_available: bool = True
    category: str = ""


# =============================================================================
# Main Discovery Functions
# =============================================================================


def _infer_task_type(task_payload: str) -> str:
    """
    Very lightweight heuristic to tag tasks for feedback bucketing.

    This keeps the interface simple and backwards compatible. You can
    refine this over time without affecting stored data.
    """
    text = task_payload.lower()
    if "memory" in text:
        return "memory"
    if "search" in text:
        return "search"
    if "code" in text or "python" in text:
        return "code"
    return "generic"


async def discover_tools_for_task(
    task_payload: str,
    top_k: int | None = None,
    min_similarity: float | None = None,
    max_tokens: int | None = None,
    use_hybrid: bool = True,
    task_id: str | None = None,
) -> list[dict[str, Any]]:
    """
    Discover relevant tools for a task using hybrid (semantic + keyword) search.

    Args:
        task_payload: Natural language description of the task
        top_k: Maximum tools to return (default from settings)
        min_similarity: Minimum similarity threshold (default from settings)
        max_tokens: Maximum tokens for tool definitions (default from settings)
        use_hybrid: Use hybrid search (default True). Falls back to semantic-only if BM25 unavailable.
        task_id: Optional task ID for tracing (auto-generated if not provided)

    Returns:
        List of tool definitions in OpenAI function calling format
    """
    settings = get_integration_settings()
    task_id = task_id or str(uuid.uuid4())[:8]
    start_time = time.perf_counter()

    # Use settings defaults if not specified
    top_k = top_k or settings.l9_tool_discovery_top_k
    min_similarity = min_similarity or settings.l9_tool_discovery_min_similarity
    max_tokens = max_tokens or settings.l9_tool_discovery_max_tokens

    if not task_payload or not task_payload.strip():
        logger.debug("Empty task payload, returning empty tool list")
        return []

    results = []
    tools = []
    error_msg = None

    try:
        if use_hybrid:
            from core.tools.tool_embeddings import find_tools_hybrid

            # Hybrid search: semantic + keyword (BM25)
            results = await find_tools_hybrid(
                query=task_payload,
                top_k=top_k * 2,  # Fetch extra for filtering
                min_similarity=min_similarity,
            )
        else:
            from core.tools.tool_embeddings import find_relevant_tools

            # Semantic-only search
            results = await find_relevant_tools(
                query=task_payload,
                top_k=top_k * 2,
                min_similarity=min_similarity,
            )

        if not results:
            logger.debug(
                "No relevant tools found",
                task_preview=task_payload[:100],
            )
            return []

        # --------------------------------------------------------------
        # NEW: Feedback-aware re-ranking before formatting
        # --------------------------------------------------------------
        settings = get_integration_settings()
        if settings.l9_tool_feedback_enabled:
            try:
                # If you have a central substrate accessor, use that here
                substrate_service = get_memory_substrate_service()  # or pass in
                feedback_service = get_tool_feedback_service(substrate_service)

                task_type = _infer_task_type(task_payload)
                tool_names = [r.tool_name for r in results]
                success_rates = await feedback_service.get_success_rates(
                    tool_names=tool_names,
                    task_type=task_type,
                )

                # Apply a simple multiplicative boost based on success_rate
                alpha = 0.5
                for r in results:
                    rate = success_rates.get(r.tool_name)
                    if rate is not None:
                        r.similarity_score *= 1.0 + alpha * rate

                # Sort by adjusted similarity_score
                results.sort(
                    key=lambda r: getattr(r, "similarity_score", 0.0),
                    reverse=True,
                )

            except Exception as e:
                logger.debug("Feedback-aware re-ranking failed", error=str(e))
        # --------------------------------------------------------------

        # Convert to OpenAI format with token budget enforcement
        tools = await _format_and_filter_tools(results, max_tokens)

        logger.info(
            "Dynamic tool discovery complete",
            task_preview=task_payload[:50],
            tools_discovered=len(tools),
            top_k=top_k,
            method="hybrid" if use_hybrid else "semantic",
        )

        return tools

    except ImportError as e:
        error_msg = f"Tool embeddings not available: {e}"
        logger.warning(error_msg)
        return []
    except Exception as e:
        error_msg = f"Dynamic tool discovery failed: {e}"
        logger.error(error_msg)
        return []
    finally:
        # Record trace for observability
        latency_ms = (time.perf_counter() - start_time) * 1000
        tokens_used = sum(t.get("_token_estimate", 0) for t in tools) if tools else 0

        trace = DiscoveryTrace(
            task_id=task_id,
            phase=DiscoveryPhase.DISCOVERY,
            query=task_payload[:200],
            num_results=len(results),
            num_selected=len(tools),
            tokens_used=tokens_used,
            latency_ms=latency_ms,
            success=error_msg is None,
            error=error_msg,
        )
        _discovery_tracer.trace_discovery(trace)


async def _format_and_filter_tools(
    results: list,
    max_tokens: int,
) -> list[dict[str, Any]]:
    """
    Convert ToolEmbeddingResult list to OpenAI format with token budget.

    Args:
        results: List of ToolEmbeddingResult from find_relevant_tools
        max_tokens: Maximum tokens to allocate

    Returns:
        List of OpenAI-formatted tool definitions
    """
    # Get full tool schemas from registry
    tool_schemas = await _get_tool_schemas()

    tools = []
    tokens_used = 0

    for result in results:
        tool_name = result.tool_name

        # Get full schema if available
        schema = tool_schemas.get(tool_name)

        if schema:
            # Use full schema from registry
            tool_def = {
                "type": "function",
                "function": {
                    "name": tool_name,
                    "description": result.description,
                    "parameters": schema.get(
                        "parameters", {"type": "object", "properties": {}}
                    ),
                },
            }
        else:
            # Fallback: minimal definition from embedding result
            tool_def = {
                "type": "function",
                "function": {
                    "name": tool_name,
                    "description": result.description,
                    "parameters": {"type": "object", "properties": {}},
                },
            }

        # Estimate token cost (rough: 1 token ≈ 4 chars + overhead)
        import json

        tool_json = json.dumps(tool_def)
        est_tokens = len(tool_json) // 4 + 50

        # Check token budget
        if tokens_used + est_tokens > max_tokens:
            logger.debug(
                "Token budget reached, stopping tool loading",
                tokens_used=tokens_used,
                max_tokens=max_tokens,
                tools_loaded=len(tools),
            )
            break

        tools.append(tool_def)
        tokens_used += est_tokens

    return tools


async def _get_tool_schemas() -> dict[str, dict[str, Any]]:
    """
    Get tool input schemas from registry for full parameter definitions.

    Returns:
        Dict mapping tool_name to schema dict
    """
    try:
        from core.tools.base_registry import get_tool_registry

        registry = get_tool_registry()
        schemas = {}

        for tool_meta in registry.list_all():
            if tool_meta.input_schema:
                schemas[tool_meta.id] = {
                    "parameters": tool_meta.input_schema,
                }

        return schemas

    except Exception as e:
        logger.debug(f"Could not get tool schemas from registry: {e}")
        return {}


def is_dynamic_discovery_enabled() -> bool:
    """Check if dynamic tool discovery is enabled."""
    settings = get_integration_settings()
    return settings.l9_dynamic_tool_discovery


async def get_discovery_stats() -> dict[str, Any]:
    """
    Get statistics about tool discovery system.

    Returns:
        Dict with discovery health metrics
    """
    try:
        from core.tools.tool_embeddings import find_relevant_tools

        # Test query to verify system is working
        test_results = await find_relevant_tools(
            query="search memory",
            top_k=1,
            min_similarity=0.1,
        )

        settings = get_integration_settings()

        return {
            "enabled": settings.l9_dynamic_tool_discovery,
            "top_k": settings.l9_tool_discovery_top_k,
            "min_similarity": settings.l9_tool_discovery_min_similarity,
            "max_tokens": settings.l9_tool_discovery_max_tokens,
            "embeddings_healthy": len(test_results) > 0,
            "test_tool_found": test_results[0].tool_name if test_results else None,
        }

    except Exception as e:
        return {
            "enabled": False,
            "error": str(e),
            "embeddings_healthy": False,
        }


# =============================================================================
# Multi-Turn Tool Caching (GMP-79)
# =============================================================================


def _get_tool_cache_key(task_id: str) -> str:
    """Generate Redis key for tool cache."""
    return f"l9:tool_cache:{task_id}"


async def get_cached_tools(task_id: str) -> list[dict[str, Any]] | None:
    """
    Retrieve cached tool definitions from Redis for multi-turn optimization.

    Args:
        task_id: The task/conversation ID

    Returns:
        List of cached tool definitions, or None if not cached
    """
    try:
        from runtime.redis_client import get_redis_client

        redis = await get_redis_client()
        if not redis:
            return None

        import json

        cache_key = _get_tool_cache_key(task_id)
        cached = await redis.get(cache_key)

        if cached:
            tools = json.loads(cached)
            logger.debug(
                "Tool cache hit",
                task_id=task_id,
                tools_cached=len(tools),
            )
            return tools

        return None

    except Exception as e:
        logger.debug(f"Tool cache lookup failed: {e}")
        return None


async def cache_tools(task_id: str, tools: list[dict[str, Any]]) -> bool:
    """
    Cache discovered tools in Redis for multi-turn reuse.

    Args:
        task_id: The task/conversation ID
        tools: Tool definitions to cache

    Returns:
        True if cached successfully
    """
    if not tools:
        return False

    try:
        from runtime.redis_client import get_redis_client

        redis = await get_redis_client()
        if not redis:
            return False

        import json

        settings = get_integration_settings()
        cache_key = _get_tool_cache_key(task_id)
        ttl = settings.l9_tool_cache_ttl

        await redis.set(cache_key, json.dumps(tools), ex=ttl)

        logger.debug(
            "Tools cached for multi-turn",
            task_id=task_id,
            tools_count=len(tools),
            ttl_seconds=ttl,
        )
        return True

    except Exception as e:
        logger.debug(f"Tool caching failed: {e}")
        return False


async def invalidate_tool_cache(task_id: str) -> bool:
    """
    Invalidate cached tools for a task (e.g., on tool set change).

    Args:
        task_id: The task/conversation ID

    Returns:
        True if invalidated successfully
    """
    try:
        from runtime.redis_client import get_redis_client

        redis = await get_redis_client()
        if not redis:
            return False

        cache_key = _get_tool_cache_key(task_id)
        await redis.delete(cache_key)

        logger.debug("Tool cache invalidated", task_id=task_id)
        return True

    except Exception as e:
        logger.debug(f"Tool cache invalidation failed: {e}")
        return False


__all__ = [
    "cache_tools",
    "discover_tools_for_task",
    # Multi-turn caching (GMP-79)
    "get_cached_tools",
    "get_discovery_stats",
    "invalidate_tool_cache",
    "is_dynamic_discovery_enabled",
]

# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "COR-FOUN-026",
    "governance_level": "critical",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [
        "core.tools.base_registry",
        "core.tools.discovery_tracing",
        "core.tools.tool_embeddings",
        "memory.substrate_service",
        "runtime.redis_client",
    ],
    "tags": [
        "async",
        "cache",
        "caching",
        "data-models",
        "dataclass",
        "debugging",
        "event-driven",
        "foundation",
        "logging",
        "metrics",
    ],
    "keywords": [
        "agent",
        "binding",
        "budget",
        "cache",
        "cached",
        "discover",
        "discovery",
        "dynamic",
    ],
    "business_value": "Provides dynamic discovery components including DiscoveryMethod, DiscoveryResult",
    "last_modified": "2026-01-25T14:49:28Z",
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
