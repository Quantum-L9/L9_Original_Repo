import logging
from typing import Any

import anthropic

logger = logging.getLogger(__name__)


class PromptCachingStrategy:
    """
    Two-tier prompt caching strategy for tool-heavy agents

    Tier 1 (Cached): System prompt, tool discovery mechanism, instructions
    Tier 2 (Dynamic): Tool definitions, task, conversation history
    """

    def __init__(self, client: anthropic.Anthropic):
        self.client = client

    def build_cached_system_prompt(self) -> str:
        """
        Static system prompt that gets cached (one-time token cost)
        Reused across all queries in the session
        """
        return """You are L9, an autonomous agent OS architect and expert system engineer.

## Your Capabilities
You have access to a dynamic tool discovery system. When you need capabilities:
1. Identify what task you need to accomplish
2. Search available tools using semantic search
3. Load relevant tools into your context
4. Execute tools with proper parameters
5. Process results and iterate as needed

## Tool Search Mechanism
Use the tool_search() function to discover tools:
- Semantic search across 1000+ available tools
- Returns top-5 most relevant tools
- Automatic filtering for availability and permissions
- Token-efficient: only loads tools you actually need

## Task Execution Pattern
For any task:
1. Analyze requirements and identify tool gaps
2. Execute: results = tool_search(query="<describe what you need>")
3. Load tools: load_tools(tool_ids=results.top_tools)
4. Execute: use loaded tools to accomplish task
5. Iterate if new tool requirements discovered

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

    def build_dynamic_tool_context(
        self,
        discovered_tools: list[dict[str, Any]],
        task: str,
        conversation_history: list[dict[str, str]] | None = None,
    ) -> str:
        """
        Dynamic context that varies per query (NOT cached)
        Includes task-specific tools and conversation state
        """
        context_parts = []

        # Tools section
        if discovered_tools:
            context_parts.append("## Available Tools for This Task\n")
            for tool in discovered_tools:
                context_parts.append(f"\n### {tool['name']}")
                context_parts.append(f"\n{tool['description']}\n")

                if "parameters" in tool:
                    context_parts.append("Parameters:\n")
                    for param in tool["parameters"]:
                        context_parts.append(f"- {param}\n")

        # Task section
        context_parts.append(f"\n## Current Task\n{task}\n")

        # Conversation history (if multi-turn)
        if conversation_history:
            context_parts.append("\n## Conversation History\n")
            for msg in conversation_history[-5:]:  # Last 5 messages only
                context_parts.append(f"\n**{msg['role'].title()}**: {msg['content']}\n")

        return "".join(context_parts)

    def create_cached_message(
        self,
        task: str,
        discovered_tools: list[dict[str, Any]],
        conversation_history: list[dict[str, str]] | None = None,
        model: str = "claude-opus-4-20250804",
        max_tokens: int = 4096,
    ) -> dict[str, Any]:
        """
        Create message with prompt caching
        Caches system prompt, reduces cost for subsequent calls
        """

        # Tier 1: Cached system prompt (one-time cost)
        system_prompt = self.build_cached_system_prompt()

        # Tier 2: Dynamic tool context (per-query cost)
        tool_context = self.build_dynamic_tool_context(
            discovered_tools, task, conversation_history
        )

        # Build messages with caching
        messages = [{"role": "user", "content": tool_context}]

        # Create message with cache control
        response = self.client.messages.create(
            model=model,
            max_tokens=max_tokens,
            system=[
                {
                    "type": "text",
                    "text": system_prompt,
                    "cache_control": {"type": "ephemeral"},  # Cache this tier
                }
            ],
            messages=messages,
            # Tool context NOT cached (varies per query)
        )

        # Extract usage info
        usage_data = {
            "input_tokens": response.usage.input_tokens,
            "output_tokens": response.usage.output_tokens,
            "cache_creation_input_tokens": getattr(
                response.usage, "cache_creation_input_tokens", 0
            ),
            "cache_read_input_tokens": getattr(
                response.usage, "cache_read_input_tokens", 0
            ),
            "total_cost_estimate": self._estimate_cost(response.usage, model),
        }

        logger.info("Message created with caching")
        logger.info(f"  Input tokens: {usage_data['input_tokens']}")
        logger.info(f"  Cache read tokens: {usage_data['cache_read_input_tokens']}")
        logger.info(f"  Estimated cost: ${usage_data['total_cost_estimate']:.4f}")

        return {"response": response, "usage": usage_data}

    @staticmethod
    def _estimate_cost(usage, model: str) -> float:
        """Rough cost estimation based on token usage"""
        # Anthropic pricing (as of Jan 2026)
        pricing = {
            "claude-opus-4-20250804": {
                "input": 0.015 / 1000,  # $15 per 1M tokens
                "output": 0.030 / 1000,  # $30 per 1M tokens
                "cache_read": 0.003 / 1000,  # $3 per 1M cached tokens
            },
            "claude-sonnet-4-20250514": {
                "input": 0.003 / 1000,
                "output": 0.015 / 1000,
                "cache_read": 0.0003 / 1000,
            },
        }

        rates = pricing.get(model, pricing["claude-sonnet-4-20250514"])

        input_cost = usage.input_tokens * rates["input"]
        output_cost = usage.output_tokens * rates["output"]
        cache_cost = getattr(usage, "cache_read_input_tokens", 0) * rates["cache_read"]

        return input_cost + output_cost + cache_cost


class CachingMetricsCollector:
    """Track caching effectiveness and cost savings"""

    def __init__(self):
        self.metrics = {
            "total_queries": 0,
            "total_input_tokens": 0,
            "total_cache_reads": 0,
            "total_cost": 0.0,
            "cost_without_caching": 0.0,
            "cost_savings_pct": 0.0,
        }

    def record_query(self, usage: dict[str, Any]):
        """Record metrics from a single query"""
        self.metrics["total_queries"] += 1
        self.metrics["total_input_tokens"] += usage["input_tokens"]
        self.metrics["total_cache_reads"] += usage["cache_read_input_tokens"]
        self.metrics["total_cost"] += usage["total_cost_estimate"]

        # Estimate what cost would be without caching
        cost_without_cache = (
            usage["input_tokens"] * 0.003 / 1000  # All input tokens billed
            + usage["output_tokens"] * 0.015 / 1000
        )
        self.metrics["cost_without_caching"] += cost_without_cache

        # Calculate savings percentage
        if self.metrics["cost_without_caching"] > 0:
            self.metrics["cost_savings_pct"] = (
                (self.metrics["cost_without_caching"] - self.metrics["total_cost"])
                / self.metrics["cost_without_caching"]
                * 100
            )

    def get_summary(self) -> dict[str, Any]:
        """Get summary of caching metrics"""
        return {
            **self.metrics,
            "avg_cost_per_query": (
                self.metrics["total_cost"] / self.metrics["total_queries"]
                if self.metrics["total_queries"] > 0
                else 0
            ),
            "avg_cache_hit_pct": (
                self.metrics["total_cache_reads"]
                / self.metrics["total_input_tokens"]
                * 100
                if self.metrics["total_input_tokens"] > 0
                else 0
            ),
        }
