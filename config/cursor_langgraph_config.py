"""
L9 Cursor LangGraph Configuration
Version: 1.0.0

Central configuration for Cursor-LangGraph-L9 integration.
"""

from __future__ import annotations

import os
from typing import Optional
from pydantic import BaseModel, Field


class CursorLangGraphConfig(BaseModel):
    """
    Configuration for Cursor-LangGraph-L9 integration.
    
    Loads from environment variables with sensible defaults.
    """
    
    # Postgres checkpoint saver
    POSTGRES_SAVER_URL: str = Field(
        default_factory=lambda: os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/l9_memory"),
        description="PostgreSQL connection string for LangGraph checkpoint saver"
    )
    
    # MCP API key (if needed)
    MCP_API_KEY: Optional[str] = Field(
        default_factory=lambda: os.getenv("MCP_API_KEY"),
        description="MCP API key (optional)"
    )
    
    # Igor approval threshold
    IGOR_APPROVAL_THRESHOLD: float = Field(
        default=0.7,
        ge=0.0,
        le=1.0,
        description="Confidence threshold below which Igor approval is required"
    )
    
    # Redis configuration
    REDIS_URL: str = Field(
        default_factory=lambda: os.getenv("REDIS_URL", "redis://localhost:6379/0"),
        description="Redis connection string for caching"
    )
    
    # Graph cache TTLs
    GRAPH_CACHE_TTL_GOVERNANCE_SEC: int = Field(
        default=90,
        ge=10,
        description="TTL for governance queries (seconds)"
    )
    
    GRAPH_CACHE_TTL_DEFAULT_SEC: int = Field(
        default=450,
        ge=10,
        description="TTL for exploratory queries (seconds)"
    )
    
    # Schema version (computed, not configurable)
    GRAPH_CACHE_SCHEMA_VERSION: str = Field(
        default="",
        description="Graph cache schema version (computed at runtime)"
    )
    
    model_config = {"extra": "allow"}


# Singleton instance
_config: Optional[CursorLangGraphConfig] = None


def get_cursor_langgraph_config() -> CursorLangGraphConfig:
    """Get singleton CursorLangGraphConfig instance."""
    global _config
    if _config is None:
        _config = CursorLangGraphConfig()
        # Compute schema version at initialization
        try:
            from memory.graph_search_cache import GRAPH_CACHE_SCHEMA_VERSION
            _config.GRAPH_CACHE_SCHEMA_VERSION = GRAPH_CACHE_SCHEMA_VERSION
        except ImportError:
            _config.GRAPH_CACHE_SCHEMA_VERSION = "unknown"
    return _config


def reset_cursor_langgraph_config() -> None:
    """Reset singleton (for testing)."""
    global _config
    _config = None

