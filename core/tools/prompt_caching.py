"""
L9 Core Tools - Prompt Caching Strategy
========================================

GMP-TD-WIRE: Two-tier prompt caching for tool-heavy agents.

This module provides:
- PromptCachingStrategy: Build cached system prompts + dynamic tool context
- CachingMetricsCollector: Track cache hits, token savings, latency

Design:
- Tier 1 (Cached): System prompt, instructions, tool discovery mechanism
- Tier 2 (Dynamic): Tool definitions, task context, conversation history
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

import structlog

logger = structlog.get_logger(__name__)


@dataclass
class CacheMetrics:
    """Metrics for prompt caching."""

    cache_hits: int = 0
    cache_misses: int = 0
    tokens_saved: int = 0
    total_requests: int = 0
    avg_latency_ms: float = 0.0

    @property
    def hit_rate(self) -> float:
        """Cache hit rate percentage."""
        if self.total_requests == 0:
            return 0.0
        return (self.cache_hits / self.total_requests) * 100


class PromptCachingStrategy:
    """
    Two-tier prompt caching strategy for tool-heavy agents.

    Tier 1 (Cached): System prompt, tool discovery mechanism, instructions
    Tier 2 (Dynamic): Tool definitions, task, conversation history

    This reduces token cost by caching the static system prompt while
    dynamically adding task-specific tool definitions.
    """

    def __init__(self):
        self._cached_system_prompt: str | None = None
        self._system_prompt_tokens: int = 0

    def build_cached_system_prompt(self) -> str:
        """
        Static system prompt that gets cached (one-time token cost).
        Reused across all queries in the session.
        """
        if self._cached_system_prompt:
            return self._cached_system_prompt

        self._cached_system_prompt = """You are L9, an autonomous agent OS architect and expert system engineer.

## Your Capabilities
You have access to a dynamic tool discovery system. When you need capabilities:
1. Identify what task you need to accomplish
2. Search available tools using semantic search
3. Load relevant tools into your context
4. Execute tools with proper parameters
5. Process results and iterate as needed

## Tool Search Mechanism
Use the tool_search() function to discover tools:
- Semantic search across available tools using pgvector
- Returns top-k most relevant tools by similarity
- Automatic filtering for availability and permissions
- Token-efficient: only loads tools you actually need

## Task Execution Pattern
For any task:
1. Analyze requirements and identify tool gaps
2. Search: results = tool_search(query="<describe what you need>")
3. Review: examine discovered tools and their capabilities
4. Execute: use loaded tools to accomplish task
5. Iterate: discover additional tools if new requirements emerge

## Output Format
- Always explain your reasoning before tool calls
- Format tool calls clearly with parameters
- Summarize results and next steps
- Be transparent about tool limitations

## Safety & Constraints
- Only use approved tools available in catalog
- Respect permission boundaries per tool
- Log all tool invocations for audit
- Ask for clarification if task is ambiguous
"""
        # Estimate tokens (rough: 4 chars per token)
        self._system_prompt_tokens = len(self._cached_system_prompt) // 4

        logger.info(
            "prompt_caching.system_prompt_cached",
            estimated_tokens=self._system_prompt_tokens,
        )

        return self._cached_system_prompt

    def build_dynamic_tool_context(
        self,
        discovered_tools: list[dict[str, Any]],
        task: str,
        conversation_history: list[dict[str, str]] | None = None,
    ) -> str:
        """
        Dynamic context that varies per query (NOT cached).
        Includes task-specific tools and conversation state.

        Args:
            discovered_tools: Tools discovered for this task
            task: Current task description
            conversation_history: Previous messages (optional)

        Returns:
            Dynamic context string to append to cached prompt
        """
        context_parts = []

        # Tools section
        if discovered_tools:
            context_parts.append("## Available Tools for This Task\n")
            for tool in discovered_tools:
                func = tool.get("function", tool)
                name = func.get("name", "unknown")
                desc = func.get("description", "")
                context_parts.append(f"\n### {name}")
                context_parts.append(f"\n{desc}\n")

                # Parameters
                params = func.get("parameters", {})
                if params and params.get("properties"):
                    context_parts.append("**Parameters:**\n")
                    for param_name, param_spec in params.get("properties", {}).items():
                        param_type = param_spec.get("type", "any")
                        param_desc = param_spec.get("description", "")
                        context_parts.append(f"- `{param_name}` ({param_type}): {param_desc}\n")

        # Current task
        context_parts.append(f"\n## Current Task\n{task}\n")

        # Conversation history (if provided)
        if conversation_history:
            context_parts.append("\n## Conversation History\n")
            for msg in conversation_history[-5:]:  # Last 5 messages
                role = msg.get("role", "user")
                content = msg.get("content", "")[:200]  # Truncate
                context_parts.append(f"**{role}**: {content}\n")

        return "".join(context_parts)

    def build_full_prompt(
        self,
        discovered_tools: list[dict[str, Any]],
        task: str,
        conversation_history: list[dict[str, str]] | None = None,
    ) -> tuple[str, str]:
        """
        Build complete prompt with cached + dynamic parts.

        Returns:
            Tuple of (cached_system_prompt, dynamic_context)
        """
        cached = self.build_cached_system_prompt()
        dynamic = self.build_dynamic_tool_context(
            discovered_tools=discovered_tools,
            task=task,
            conversation_history=conversation_history,
        )

        return cached, dynamic

    def estimate_token_savings(
        self,
        num_requests: int,
    ) -> dict[str, int]:
        """
        Estimate token savings from caching.

        Args:
            num_requests: Number of requests in session

        Returns:
            Dict with token savings info
        """
        if num_requests <= 1:
            return {
                "cached_tokens": self._system_prompt_tokens,
                "without_caching": self._system_prompt_tokens,
                "with_caching": self._system_prompt_tokens,
                "tokens_saved": 0,
            }

        without_caching = self._system_prompt_tokens * num_requests
        with_caching = self._system_prompt_tokens  # Only counted once

        return {
            "cached_tokens": self._system_prompt_tokens,
            "without_caching": without_caching,
            "with_caching": with_caching,
            "tokens_saved": without_caching - with_caching,
        }


class CachingMetricsCollector:
    """
    Collect and report caching metrics for observability.
    """

    def __init__(self):
        self.metrics = CacheMetrics()
        self._latencies: list[float] = []

    def record_cache_hit(self, tokens_saved: int = 0) -> None:
        """Record a cache hit."""
        self.metrics.cache_hits += 1
        self.metrics.total_requests += 1
        self.metrics.tokens_saved += tokens_saved

    def record_cache_miss(self) -> None:
        """Record a cache miss."""
        self.metrics.cache_misses += 1
        self.metrics.total_requests += 1

    def record_latency(self, latency_ms: float) -> None:
        """Record request latency."""
        self._latencies.append(latency_ms)
        if self._latencies:
            self.metrics.avg_latency_ms = sum(self._latencies) / len(self._latencies)

    def get_metrics(self) -> dict[str, Any]:
        """Get all metrics as dict."""
        return {
            "cache_hits": self.metrics.cache_hits,
            "cache_misses": self.metrics.cache_misses,
            "hit_rate": self.metrics.hit_rate,
            "tokens_saved": self.metrics.tokens_saved,
            "total_requests": self.metrics.total_requests,
            "avg_latency_ms": self.metrics.avg_latency_ms,
        }

    def reset(self) -> None:
        """Reset all metrics."""
        self.metrics = CacheMetrics()
        self._latencies = []


__all__ = [
    "CacheMetrics",
    "CachingMetricsCollector",
    "PromptCachingStrategy",
]
