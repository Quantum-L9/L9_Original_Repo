"""
L9 Core Tools - Semantic Discovery Service
===========================================

GMP-TD-WIRE: Production-grade tool discovery using L9's pgvector backend.

This module provides:
- DynamicToolDiscoveryService: Semantic + keyword hybrid search for tools
- ToolContextFormatter: Format discovered tools for LLM prompts
- ToolStatus: Tool availability states

Note: Uses pgvector (via tool_embeddings.py), NOT qdrant.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any

import structlog

logger = structlog.get_logger(__name__)


class ToolStatus(Enum):
    """Tool availability states"""

    AVAILABLE = "available"
    AUTH_REQUIRED = "auth_required"
    UNAVAILABLE = "unavailable"
    DEPRECATED = "deprecated"


@dataclass
class ToolDefinition:
    """Complete tool specification for discovery."""

    id: str
    name: str
    description: str
    category: str
    tags: list[str]
    parameters: dict[str, Any]
    status: ToolStatus = ToolStatus.AVAILABLE
    examples: list[dict[str, str]] | None = None
    performance: dict[str, Any] | None = None
    requirements: dict[str, Any] | None = None

    def to_embedding_text(self) -> str:
        """Construct optimal text for vector embedding."""
        parts = [
            self.description,
            f"Category: {self.category}",
            f"Tags: {', '.join(self.tags)}",
            f"Parameters: {', '.join(self.parameters.keys())}",
        ]

        if self.examples:
            example = self.examples[0] if self.examples else {}
            parts.append(f"Example: {example.get('description', '')}")

        return "\n".join(parts)


class DynamicToolDiscoveryService:
    """
    Production-grade tool discovery using L9's pgvector backend.

    Features:
    - Semantic search (pgvector cosine similarity)
    - Keyword search (PostgreSQL BM25 full-text)
    - Hybrid fusion (weighted combination)
    - Token budget management
    - Availability checking

    Note: This wraps tool_embeddings.py functions for a service interface.
    """

    def __init__(
        self,
        tool_budget_tokens: int = 2000,
        confidence_threshold: float = 0.30,
        top_k_results: int = 5,
        semantic_weight: float = 0.6,
        keyword_weight: float = 0.4,
    ):
        """
        Initialize discovery service.

        Args:
            tool_budget_tokens: Maximum tokens for tool definitions in context
            confidence_threshold: Minimum similarity score to include tool
            top_k_results: Maximum number of tools to return
            semantic_weight: Weight for semantic search (0-1)
            keyword_weight: Weight for keyword search (0-1)
        """
        self.tool_budget_tokens = tool_budget_tokens
        self.confidence_threshold = confidence_threshold
        self.top_k_results = top_k_results
        self.semantic_weight = semantic_weight
        self.keyword_weight = keyword_weight

        # Tool cache
        self._tool_cache: dict[str, ToolDefinition] = {}

        logger.info(
            "discovery_service.initialized",
            budget_tokens=tool_budget_tokens,
            threshold=confidence_threshold,
            top_k=top_k_results,
        )

    def register_tool(self, tool: ToolDefinition) -> None:
        """Register a tool for discovery."""
        self._tool_cache[tool.id] = tool
        logger.debug("discovery_service.tool_registered", tool_id=tool.id)

    def register_tools(self, tools: list[ToolDefinition]) -> int:
        """Register multiple tools for discovery."""
        for tool in tools:
            self._tool_cache[tool.id] = tool
        logger.info("discovery_service.tools_registered", count=len(tools))
        return len(tools)

    async def discover_tools(
        self,
        query: str,
        top_k: int | None = None,
        use_hybrid: bool = True,
    ) -> list[dict[str, Any]]:
        """
        Discover relevant tools for a query.

        Args:
            query: Natural language query describing needed functionality
            top_k: Override default top_k_results
            use_hybrid: Use hybrid search (semantic + keyword)

        Returns:
            List of tool definitions in OpenAI format
        """
        top_k = top_k or self.top_k_results

        try:
            if use_hybrid:
                from core.tools.tool_embeddings import find_tools_hybrid

                results = await find_tools_hybrid(
                    query=query,
                    top_k=top_k,
                    semantic_weight=self.semantic_weight,
                    keyword_weight=self.keyword_weight,
                    min_similarity=self.confidence_threshold,
                )
            else:
                from core.tools.tool_embeddings import find_relevant_tools

                results = await find_relevant_tools(
                    query=query,
                    top_k=top_k,
                    min_similarity=self.confidence_threshold,
                )

            # Convert to OpenAI format
            tools = []
            for r in results:
                tools.append({
                    "type": "function",
                    "function": {
                        "name": r.tool_name,
                        "description": r.description,
                        "parameters": r.metadata.get("parameters", {}),
                    },
                })

            logger.info(
                "discovery_service.tools_discovered",
                query_preview=query[:50],
                count=len(tools),
                method="hybrid" if use_hybrid else "semantic",
            )

            return tools

        except Exception as e:
            logger.error("discovery_service.discover_failed", error=str(e))
            raise

    async def discover_tools_with_budget(
        self,
        query: str,
        max_tokens: int | None = None,
    ) -> list[dict[str, Any]]:
        """
        Discover tools respecting token budget.

        Args:
            query: Search query
            max_tokens: Override default budget

        Returns:
            Tools that fit within token budget
        """
        max_tokens = max_tokens or self.tool_budget_tokens
        tools = await self.discover_tools(query, top_k=self.top_k_results * 2)

        # Enforce token budget
        selected_tools = []
        total_tokens = 0

        for tool in tools:
            # Estimate tokens (rough: 4 chars per token)
            tool_tokens = len(str(tool)) // 4
            if total_tokens + tool_tokens <= max_tokens:
                selected_tools.append(tool)
                total_tokens += tool_tokens
            else:
                break

        logger.debug(
            "discovery_service.budget_enforced",
            total_tokens=total_tokens,
            max_tokens=max_tokens,
            tools_selected=len(selected_tools),
        )

        return selected_tools


class ToolContextFormatter:
    """Format discovered tools into LLM-ready prompt sections."""

    @staticmethod
    def format_tools_for_prompt(
        tools: list[ToolDefinition],
        max_chars: int = 8000,
    ) -> str:
        """
        Format tools into optimized prompt text.

        Args:
            tools: List of ToolDefinition objects
            max_chars: Maximum characters for output

        Returns:
            Formatted prompt string
        """
        prompt_parts = ["# Available Tools\n"]

        for tool in tools:
            # Tool header
            prompt_parts.append(f"\n## {tool.name}\n")
            prompt_parts.append(f"**Category**: {tool.category}\n")
            prompt_parts.append(f"**Description**: {tool.description}\n")

            # Parameters
            if tool.parameters:
                prompt_parts.append("\n**Parameters**:\n")
                for param_name, param_spec in tool.parameters.items():
                    param_type = param_spec.get("type", "any") if isinstance(param_spec, dict) else "any"
                    prompt_parts.append(f"- `{param_name}`: {param_type}")
                    if isinstance(param_spec, dict) and param_spec.get("description"):
                        prompt_parts.append(f" - {param_spec['description']}")
                    prompt_parts.append("\n")

            # Example usage
            if tool.examples:
                prompt_parts.append("\n**Example**:\n")
                example = tool.examples[0] if tool.examples else {}
                call = example.get("call", "") if isinstance(example, dict) else ""
                prompt_parts.append(f"```\n{call}\n```\n")

        # Enforce max chars
        full_prompt = "".join(prompt_parts)
        if len(full_prompt) > max_chars:
            full_prompt = full_prompt[:max_chars] + "\n... (truncated)"

        return full_prompt

    @staticmethod
    def format_openai_tools(tools: list[dict[str, Any]]) -> str:
        """
        Format OpenAI-style tool definitions for prompt.

        Args:
            tools: List of tools in OpenAI format

        Returns:
            Formatted string
        """
        lines = ["# Available Tools\n"]

        for tool in tools:
            func = tool.get("function", {})
            name = func.get("name", "unknown")
            desc = func.get("description", "")
            lines.append(f"\n## {name}\n{desc}\n")

        return "".join(lines)


__all__ = [
    "DynamicToolDiscoveryService",
    "ToolContextFormatter",
    "ToolDefinition",
    "ToolStatus",
]
