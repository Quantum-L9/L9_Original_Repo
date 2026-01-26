"""
L9 Research Department - Tools Module
Version: 2.0.0

In-memory tool registry and wrappers for research tools.
Includes production Perplexity client with best practices codified.
"""

from core.tools.base_registry import (
    ToolMetadata,
    ToolRegistry,
    ToolType,
    get_tool_registry,
)
from services.research.tools.perplexity_client import (
    PerplexityClient,
    PerplexityModel,
    PerplexityRequest,
    PerplexityResponse,
    SearchContextSize,
    get_perplexity_client,
)
from services.research.tools.tool_resolver import ToolResolver, get_tool_resolver
from services.research.tools.tool_wrappers import (
    BaseTool,
    HTTPTool,
    MockSearchTool,
    PerplexityTool,
)

__all__ = [
    # Wrappers
    "BaseTool",
    "HTTPTool",
    "MockSearchTool",
    # Perplexity Client (production)
    "PerplexityClient",
    "PerplexityModel",
    "PerplexityRequest",
    "PerplexityResponse",
    "PerplexityTool",
    "SearchContextSize",
    "ToolMetadata",
    "ToolRegistry",
    # Resolver
    "ToolResolver",
    # Registry
    "ToolType",
    "get_perplexity_client",
    "get_tool_registry",
    "get_tool_resolver",
]
