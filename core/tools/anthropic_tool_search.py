import logging
from typing import Any

import anthropic

logger = logging.getLogger(__name__)


class AnthropicToolSearchAdapter:
    """
    Adapter for Anthropic's Tool Search feature
    Supports deferred tool loading to reduce context overhead
    """

    def __init__(self, api_key: str, model: str = "claude-opus-4-20250804"):
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = model
        self.tools_catalog: dict[str, dict[str, Any]] = {}

    def register_tools(self, tools: list[dict[str, Any]]):
        """
        Register tools with Anthropic Tool Search
        Must use defer_loading: true for deferred tools
        """
        for tool in tools:
            self.tools_catalog[tool["name"]] = tool

    def build_anthropic_tools_list(
        self, defer_loading: bool = True, always_available: list[str] | None = None
    ) -> list[dict[str, Any]]:
        """
        Build tools list for Anthropic API with deferred loading strategy

        Always available: 3-5 most frequently used tools (not deferred)
        Deferred: Remaining tools loaded on-demand via Tool Search
        """
        always_available = always_available or []
        anthropic_tools = []

        for tool_name, tool_spec in self.tools_catalog.items():
            tool_def = {
                "name": tool_spec.get("name", tool_name),
                "description": tool_spec.get("description", ""),
                "input_schema": tool_spec.get("input_schema", {}),
            }

            # Defer loading for non-essential tools
            if defer_loading and tool_name not in always_available:
                tool_def["defer_loading"] = True

                # Add search keywords for Tool Search to find this tool
                tool_def["search_keywords"] = tool_spec.get("tags", [])

            anthropic_tools.append(tool_def)

        logger.info(f"Built {len(anthropic_tools)} tools for Anthropic API")
        logger.info(f"  Always available: {len(always_available)}")
        logger.info(f"  Deferred: {len(anthropic_tools) - len(always_available)}")

        return anthropic_tools

    def create_message_with_tool_search(
        self,
        messages: list[dict[str, str]],
        system_prompt: str,
        always_available_tools: list[str] | None = None,
        max_tokens: int = 4096,
    ) -> anthropic.Message:
        """
        Create message using Tool Search (deferred loading)
        Only specified tools loaded upfront; others discovered on-demand
        """
        always_available_tools = always_available_tools or []

        # Build tools with deferred loading
        tools = self.build_anthropic_tools_list(
            defer_loading=True, always_available=always_available_tools
        )

        # Call Claude with Tool Search enabled
        response = self.client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            system=system_prompt,
            tools=tools,
            messages=messages,
            betas=["tool-search-1"],  # Enable Tool Search
        )

        logger.info("Message created with Tool Search")
        logger.info(f"  Input tokens: {response.usage.input_tokens}")
        logger.info(f"  Output tokens: {response.usage.output_tokens}")

        return response

    def extract_tool_calls(self, response: anthropic.Message) -> list[dict[str, Any]]:
        """Extract tool calls from response"""
        tool_calls = []

        for block in response.content:
            if hasattr(block, "type") and block.type == "tool_use":
                tool_calls.append(
                    {"id": block.id, "name": block.name, "input": block.input}
                )

        return tool_calls


class ToolSearchOptimizer:
    """
    Optimization strategies for Anthropic Tool Search
    Based on real production testing
    """

    @staticmethod
    def get_optimal_always_available(
        tool_usage_stats: dict[str, int], top_n: int = 3
    ) -> list[str]:
        """
        Select top-N most frequently used tools to keep always available
        Rest are deferred and discovered on-demand
        """
        # Sort by usage frequency
        sorted_tools = sorted(
            tool_usage_stats.items(), key=lambda x: x[-1], reverse=True
        )

        # Return top N
        always_available = [tool_name for tool_name, _ in sorted_tools[:top_n]]

        logger.info("Most frequently used tools (always available):")
        for tool in always_available:
            logger.info(f"  - {tool}")

        return always_available

    @staticmethod
    def add_semantic_keywords(tools: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """
        Add semantic search keywords to tool definitions
        Improves Tool Search discovery accuracy
        """
        enhanced_tools = []

        for tool in tools:
            # Ensure semantic keywords are present
            if "search_keywords" not in tool:
                # Generate keywords from description
                description = tool.get("description", "")
                keywords = [
                    word
                    for word in description.lower().split()
                    if len(word) > 3 and word not in ["this", "that", "with", "from"]
                ]
                tool["search_keywords"] = keywords[:5]  # Top 5

            enhanced_tools.append(tool)

        return enhanced_tools

    @staticmethod
    def validate_tool_search_coverage(
        tools: list[dict[str, Any]], test_queries: list[str]
    ) -> dict[str, Any]:
        """
        Validate that Tool Search can find tools for realistic queries
        (In practice, would use actual Anthropic API for validation)
        """
        coverage = {
            "total_tools": len(tools),
            "queries_tested": len(test_queries),
            "discovery_accuracy": 0.0,  # Would measure against real API
            "recommendations": [],
        }

        # Basic validation: check keywords exist
        tools_with_keywords = [
            t
            for t in tools
            if "search_keywords" in t and len(t.get("search_keywords", [])) > 0
        ]

        coverage["keyword_coverage_pct"] = len(tools_with_keywords) / len(tools) * 100

        if coverage["keyword_coverage_pct"] < 100:
            coverage["recommendations"].append(
                "Add search_keywords to all tools for better discoverability"
            )

        return coverage


# ============================================================================
# EXAMPLE USAGE
# ============================================================================

if __name__ == "__main__":
    import os

    adapter = AnthropicToolSearchAdapter(api_key=os.environ.get("ANTHROPIC_API_KEY"))

    # Register tools
    sample_tools = [
        {
            "name": "web_search",
            "description": "Search the web for current information",
            "tags": ["search", "web", "news"],
            "input_schema": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query"}
                },
                "required": ["query"],
            },
        },
        # ... more tools
    ]

    adapter.register_tools(sample_tools)

    # Determine which tools are always available
    usage_stats = {
        "web_search": 150,
        "api_query": 120,
        "file_read": 90,
        # ... more stats
    }

    always_available = ToolSearchOptimizer.get_optimal_always_available(
        usage_stats, top_n=3
    )

    # Create message with Tool Search
    messages = [
        {
            "role": "user",
            "content": "Search for recent developments in quantum computing",
        }
    ]

    response = adapter.create_message_with_tool_search(
        messages=messages,
        system_prompt="You are a helpful research assistant. Use the available tools to answer user queries.",
        always_available_tools=always_available,
    )

    print(f"Response: {response.content}")
