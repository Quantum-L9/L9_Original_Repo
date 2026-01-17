"""
L9 Research Department - Tool Wrappers
Version: 2.0.0

Concrete tool implementations for research.
Uses production Perplexity client with best practices codified.
"""

import structlog
from abc import ABC, abstractmethod
from typing import Any, Optional

import httpx
from core.decorators import must_stay_async

from services.research.tools.perplexity_client import (
    PerplexityClient,
    get_perplexity_client,
)

log = structlog.get_logger(__name__)


class BaseTool(ABC):
    """Base class for all tools."""

    @abstractmethod
    @must_stay_async("callers use await")
    async def execute(self, args: dict[str, Any]) -> Any:
        """
        Execute the tool.

        Args:
            args: Tool arguments

        Returns:
            Tool result
        """
        pass


class PerplexityTool(BaseTool):
    """
    Perplexity AI search tool.

    Uses production PerplexityClient with best practices codified:
    - Correct model selection (sonar, sonar-pro, sonar-deep-research)
    - API parameters for search control (not prompt-based)
    - Structured request validation
    - Proper rate limit awareness

    Requires PERPLEXITY_API_KEY environment variable.
    """

    def __init__(self):
        """Initialize Perplexity tool."""
        self._client: Optional[PerplexityClient] = None

    async def execute(self, args: dict[str, Any]) -> dict[str, Any]:
        """
        Execute Perplexity search.

        Args:
            args: {
                "query": str - The search query (required)
                "mode": str - "quick", "research", "analyze", "deep" (default: "research")
                "domains": list[str] - Domain filter (optional)
            }

        Returns:
            {"result": str, "sources": list, "model": str, "cost": float}
        """
        query = args.get("query", "")
        if not query:
            return {
                "result": "No query provided",
                "sources": [],
                "error": "missing_query",
            }

        mode = args.get("mode", "research")
        domains = args.get("domains", [])

        client = get_perplexity_client()
        if not client:
            log.warning("perplexity_not_configured", fallback="mock")
            return {
                "result": f"[Mock] Research results for: {query}",
                "sources": ["mock://source1", "mock://source2"],
                "model": "mock",
                "cost": 0.0,
            }

        try:
            async with client:
                # Route to appropriate method based on mode
                if mode == "quick":
                    response = await client.quick_search(query)
                elif mode == "analyze":
                    response = await client.analyze(query)
                elif mode == "deep":
                    response = await client.deep_research(query)
                else:  # default: research
                    response = await client.research(
                        query, domains=domains if domains else None
                    )

                if response.success:
                    return {
                        "result": response.content,
                        "sources": response.citations,
                        "model": response.model,
                        "tokens": response.tokens_used,
                        "cost": response.cost,
                    }
                else:
                    return {
                        "result": f"Search failed: {response.error}",
                        "sources": [],
                        "model": response.model,
                        "error": response.error,
                    }

        except Exception as e:
            log.error("perplexity_tool_error", error=str(e))
            return {
                "result": f"Search failed: {str(e)}",
                "sources": [],
                "error": str(e),
            }


class HTTPTool(BaseTool):
    """
    Generic HTTP request tool.

    Makes HTTP requests to external APIs.
    """

    async def execute(self, args: dict[str, Any]) -> dict[str, Any]:
        """
        Execute HTTP request.

        Args:
            args: {
                "url": str,
                "method": str (default "GET"),
                "headers": dict (optional),
                "body": dict (optional),
            }

        Returns:
            {"status": int, "body": str/dict}
        """
        url = args.get("url", "")
        method = args.get("method", "GET").upper()
        headers = args.get("headers", {})
        body = args.get("body")

        if not url:
            return {"status": 400, "body": "No URL provided"}

        try:
            async with httpx.AsyncClient() as client:
                response = await client.request(
                    method=method,
                    url=url,
                    headers=headers,
                    json=body if body else None,
                    timeout=30.0,
                )

                # Try to parse JSON
                try:
                    body_data = response.json()
                except Exception:
                    body_data = response.text

                return {
                    "status": response.status_code,
                    "body": body_data,
                }

        except Exception as e:
            log.error("http_request_failed", error=str(e))
            return {
                "status": 500,
                "body": str(e),
                "error": str(e),
            }


class MockSearchTool(BaseTool):
    """
    Mock search tool for testing.

    Returns deterministic mock results without API calls.
    """

    @must_stay_async("callers use await")
    async def execute(self, args: dict[str, Any]) -> dict[str, Any]:
        """
        Execute mock search.

        Args:
            args: {"query": str}

        Returns:
            Mock search results
        """
        query = args.get("query", "unknown query")

        # Generate deterministic mock results
        mock_results = {
            "result": (
                f"Mock research findings for '{query}':\n\n"
                f"1. Key Finding: This is a mock result for testing purposes.\n"
                f"2. Supporting Evidence: The query '{query}' was processed by the mock search tool.\n"
                f"3. Conclusion: Mock search provides deterministic results for testing.\n"
            ),
            "sources": [
                "https://mock.example.com/result1",
                "https://mock.example.com/result2",
                "https://mock.example.com/result3",
            ],
            "confidence": 0.9,
            "is_mock": True,
        }

        log.debug("mock_search_executed", query_preview=query[:50])
        return mock_results
