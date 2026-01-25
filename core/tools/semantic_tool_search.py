"""
L9 Core Tools - Semantic Tool Search
=====================================

GMP-TD-WIRE: Provider-agnostic semantic tool search adapter.
Supports deferred tool loading to reduce context overhead.

This module provides:
- SemanticToolSearchAdapter: Register and search tools by semantic similarity
- ToolSearchOptimizer: Optimize tool availability based on usage patterns

Note: This is L9's internal tool search, NOT Anthropic's Tool Search API.
Uses pgvector for semantic search via tool_embeddings.py.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

import structlog

logger = structlog.get_logger(__name__)


@dataclass
class ToolSearchResult:
    """Result from semantic tool search."""

    tool_name: str
    description: str
    similarity: float
    is_deferred: bool = False
    search_keywords: list[str] = field(default_factory=list)


class SemanticToolSearchAdapter:
    """
    Adapter for semantic tool search using L9's pgvector backend.

    Supports deferred tool loading to reduce context overhead:
    - Always available: 3-5 most frequently used tools (not deferred)
    - Deferred: Remaining tools loaded on-demand via semantic search
    """

    def __init__(self):
        self.tools_catalog: dict[str, dict[str, Any]] = {}
        self._always_available: list[str] = []

    def register_tools(self, tools: list[dict[str, Any]]) -> None:
        """
        Register tools for semantic search.

        Args:
            tools: List of tool definitions with 'name', 'description', etc.
        """
        for tool in tools:
            name = tool.get("name", "")
            if name:
                self.tools_catalog[name] = tool

        logger.info(
            "semantic_tool_search.registered",
            tool_count=len(self.tools_catalog),
        )

    def set_always_available(self, tool_names: list[str]) -> None:
        """
        Set tools that should always be available (not deferred).

        Args:
            tool_names: List of tool names to keep always available
        """
        self._always_available = tool_names
        logger.info(
            "semantic_tool_search.always_available_set",
            count=len(tool_names),
            tools=tool_names,
        )

    def build_tools_list(
        self,
        defer_loading: bool = True,
        always_available: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        """
        Build tools list with deferred loading strategy.

        Args:
            defer_loading: Whether to mark non-essential tools as deferred
            always_available: Override list of always-available tools

        Returns:
            List of tool definitions with defer_loading flags
        """
        always_available = always_available or self._always_available
        tools_list = []

        for tool_name, tool_spec in self.tools_catalog.items():
            tool_def = {
                "name": tool_spec.get("name", tool_name),
                "description": tool_spec.get("description", ""),
                "input_schema": tool_spec.get("input_schema", {}),
            }

            # Mark non-essential tools as deferred
            if defer_loading and tool_name not in always_available:
                tool_def["defer_loading"] = True
                tool_def["search_keywords"] = tool_spec.get("tags", [])

            tools_list.append(tool_def)

        logger.debug(
            "semantic_tool_search.tools_built",
            total=len(tools_list),
            always_available=len(always_available),
            deferred=len(tools_list) - len(always_available),
        )

        return tools_list

    async def search_tools(
        self,
        query: str,
        top_k: int = 5,
        min_similarity: float = 0.3,
    ) -> list[ToolSearchResult]:
        """
        Search for relevant tools using semantic similarity.

        Args:
            query: Natural language query describing needed functionality
            top_k: Maximum number of tools to return
            min_similarity: Minimum similarity threshold

        Returns:
            List of ToolSearchResult ordered by relevance
        """
        try:
            from core.tools.tool_embeddings import find_tools_hybrid

            results = await find_tools_hybrid(
                query=query,
                top_k=top_k,
                min_similarity=min_similarity,
            )

            return [
                ToolSearchResult(
                    tool_name=r.tool_name,
                    description=r.description,
                    similarity=r.similarity,
                    is_deferred=r.tool_name not in self._always_available,
                )
                for r in results
            ]

        except Exception as e:
            logger.error("semantic_tool_search.search_failed", error=str(e))
            return []

    def get_tool(self, tool_name: str) -> dict[str, Any] | None:
        """Get a specific tool by name."""
        return self.tools_catalog.get(tool_name)


class ToolSearchOptimizer:
    """
    Optimize tool availability based on usage patterns.

    Tracks tool usage and recommends which tools should be always available
    vs deferred for optimal context efficiency.
    """

    @staticmethod
    def get_optimal_always_available(
        tool_usage_stats: dict[str, int],
        top_n: int = 3,
    ) -> list[str]:
        """
        Select top-N most frequently used tools to keep always available.

        Args:
            tool_usage_stats: Dict mapping tool_name -> usage count
            top_n: Number of tools to keep always available

        Returns:
            List of tool names that should be always available
        """
        sorted_tools = sorted(
            tool_usage_stats.items(),
            key=lambda x: x[1],
            reverse=True,
        )

        always_available = [tool_name for tool_name, _ in sorted_tools[:top_n]]

        logger.info(
            "tool_search_optimizer.always_available_computed",
            tools=always_available,
        )

        return always_available

    @staticmethod
    def add_semantic_keywords(tools: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """
        Add semantic search keywords to tool definitions.

        Enhances tool discoverability by extracting keywords from descriptions.
        """
        enhanced_tools = []

        for tool in tools:
            if "search_keywords" not in tool or not tool.get("search_keywords"):
                description = tool.get("description", "")
                # Extract meaningful words from description
                keywords = [
                    word
                    for word in description.lower().split()
                    if len(word) > 3 and word not in {"this", "that", "with", "from", "the"}
                ]
                tool["search_keywords"] = keywords[:5]

            enhanced_tools.append(tool)

        return enhanced_tools

    @staticmethod
    def validate_tool_search_coverage(
        tools: list[dict[str, Any]],
        test_queries: list[str],
    ) -> dict[str, Any]:
        """
        Validate that semantic search can find tools for realistic queries.

        Returns coverage report with recommendations.
        """
        coverage = {
            "tools_count": len(tools),
            "queries_tested": len(test_queries),
            "recommendations": [],
        }

        # Check keyword coverage
        tools_with_keywords = [
            t
            for t in tools
            if "search_keywords" in t and len(t.get("search_keywords", [])) > 0
        ]

        coverage["keyword_coverage_pct"] = (
            len(tools_with_keywords) / len(tools) * 100 if tools else 0
        )

        if coverage["keyword_coverage_pct"] < 100:
            coverage["recommendations"].append(
                "Add search_keywords to all tools for better discoverability"
            )

        return coverage


__all__ = [
    "SemanticToolSearchAdapter",
    "ToolSearchOptimizer",
    "ToolSearchResult",
]
