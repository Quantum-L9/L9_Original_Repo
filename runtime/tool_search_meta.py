"""
L9 Runtime - Tool Search Meta-Tool (Anthropic Pattern)
========================================================

GMP-TS-META: Implements Anthropic's "Tool Search Tool" pattern for dynamic
tool discovery at agent runtime.

Instead of binding all 73+ tools to every agent request, this meta-tool
enables Claude to discover only the tools it needs by calling `tool_search`
with a natural language query.

Architecture:
- Agents get ONE meta-tool: tool_search(query: str)
- Meta-tool calls discover_tools_for_task() under the hood
- Returns discovered tools in OpenAI function format
- Agent then calls the discovered tools normally

This mirrors Anthropic's recommended approach for large tool catalogs:
https://docs.anthropic.com/en/docs/build-with-claude/tool-use/deferred-tool-loading

Version: 1.0.0
Created: 2026-02-12
"""

from __future__ import annotations

# ============================================================================
__dora_meta__ = {
    "component_name": "Tool Search Meta-Tool",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2026-02-12T18:24:00Z",
    "updated_at": "2026-02-12T18:24:00Z",
    "layer": "runtime",
    "domain": "tool_registry",
    "module_name": "tool_search_meta",
    "type": "tool",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": ["PostgreSQL", "Redis"],
        "memory_layers": ["semantic_memory"],
        "imported_by": [
            "core.agents.dynamic_tool_binding",
            "runtime.tool_packages",
        ],
    },
}
# ============================================================================

from typing import Any

import structlog

from core.decorators import must_stay_async, register_tool
from core.tools.dynamic_discovery import discover_tools_for_task

logger = structlog.get_logger(__name__)


@register_tool(
    name="tool_search",
    category="meta",
    priority=10,
    description=(
        "Search L9's tool catalog to find tools relevant to a task. "
        "Use this when you need a tool but aren't sure which one, or when "
        "you need to discover available tools for a complex task. "
        "Returns: List of tool definitions you can then call normally."
    ),
)
@must_stay_async("uses semantic search + database")
async def tool_search(
    query: str,
    top_k: int = 5,
    **kwargs: Any,
) -> dict[str, Any]:
    """
    Meta-tool for dynamic tool discovery (Anthropic pattern).

    This is the ONLY tool that agents need to discover other tools.
    Instead of loading 73+ tools into context, agents call this meta-tool
    with a natural language query describing what they need.

    Args:
        query: Natural language description of what you need to do.
               Examples:
               - "search memory for information about project X"
               - "commit code changes to git"
               - "run a governance check"
               - "query the world model"
        top_k: Maximum number of tools to return (default 5)

    Returns:
        Dict with:
        - tools: List of tool definitions in OpenAI format
        - count: Number of tools found
        - query: The search query used
        - method: Discovery method (hybrid/semantic/keyword)

    Example:
        >>> result = await tool_search("search memory for recent events")
        >>> print(result["tools"])
        [
            {
                "type": "function",
                "function": {
                    "name": "memory_search",
                    "description": "Semantic search across memory...",
                    "parameters": {...}
                }
            }
        ]

    Constraints:
        - Query must be descriptive (not just tool name)
        - Returns tools you have permission to use
        - Token budget enforced (won't exceed context limits)
        - Cached for multi-turn conversations
    """
    if not query or not query.strip():
        return {
            "tools": [],
            "count": 0,
            "query": query,
            "error": "Query cannot be empty",
        }

    try:
        # Use dynamic discovery (hybrid semantic + keyword search)
        tools = await discover_tools_for_task(
            task_payload=query,
            top_k=top_k,
            use_hybrid=True,  # Anthropic recommends BM25 + semantic
        )

        logger.info(
            "tool_search.meta_tool_called",
            query_preview=query[:50],
            tools_found=len(tools),
            top_k=top_k,
        )

        return {
            "tools": tools,
            "count": len(tools),
            "query": query,
            "method": "hybrid",
        }

    except Exception as e:
        logger.error(
            "tool_search.meta_tool_failed",
            query=query[:100],
            error=str(e),
            exc_info=True,
        )
        return {
            "tools": [],
            "count": 0,
            "query": query,
            "error": str(e),
        }


__all__ = [
    "tool_search",
]

# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "RUN-TOOL-SRCH-001",
    "governance_level": "critical",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [
        "core.decorators",
        "core.tools.dynamic_discovery",
    ],
    "tags": [
        "async",
        "meta-tool",
        "tool-discovery",
        "anthropic-pattern",
        "runtime",
    ],
    "keywords": [
        "tool_search",
        "meta",
        "discovery",
        "deferred",
        "anthropic",
        "claude",
    ],
    "business_value": (
        "Implements Anthropic's Tool Search pattern for deferred tool loading. "
        "Reduces context bloat from 73+ tools to 1 meta-tool + 3-5 discovered tools per task."
    ),
    "last_modified": "2026-02-12T18:24:00Z",
    "modified_by": "L9_Codegen_Engine",
    "change_summary": "Initial implementation - Anthropic Tool Search meta-tool",
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
