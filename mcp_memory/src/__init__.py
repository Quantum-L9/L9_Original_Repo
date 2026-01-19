"""
L9 MCP Memory Server.

Semantic memory service for Cursor IDE integration.
Provides MCP (Model Context Protocol) tools for saving, querying,
and managing context memories via OpenAI embeddings + pgvector.

Created: 2025-12-27
Modified: 2026-01-01
Author: L9 Team
"""

try:
    # Relative import (when imported as mcp_memory.src)
    from .rate_limiter import RateLimiter
except ImportError:
    # Absolute import (when running inside mcp_memory directory)
    from src.rate_limiter import RateLimiter

__version__ = "1.0.0"

__all__ = ["RateLimiter"]
