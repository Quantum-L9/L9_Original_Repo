"""
L9 Cursor LangGraph Configuration
Version: 1.0.0

Central configuration for Cursor-LangGraph-L9 integration.
"""

from __future__ import annotations

# ============================================================================
__dora_meta__ = {
    "component_name": "Cursor Langgraph Config",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2026-01-11T18:13:39Z",
    "updated_at": "2026-01-11T14:51:06Z",
    "layer": "foundation",
    "domain": "data_models",
    "module_name": "cursor_langgraph_config",
    "type": "schema",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": ["PostgreSQL", "Redis"],
        "memory_layers": [],
        "imported_by": ["api.server"],
    },
}
# ============================================================================

import os

from pydantic import BaseModel, Field


class CursorLangGraphConfig(BaseModel):
    """
    Configuration for Cursor-LangGraph-L9 integration.

    Loads from environment variables with sensible defaults.
    """

    # Postgres checkpoint saver
    POSTGRES_SAVER_URL: str = Field(
        default_factory=lambda: os.getenv(
            "DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/l9_memory"
        ),
        description="PostgreSQL connection string for LangGraph checkpoint saver",
    )

    # MCP API key (if needed)
    MCP_API_KEY: str | None = Field(
        default_factory=lambda: os.getenv("MCP_API_KEY"),
        description="MCP API key (optional)",
    )

    # Igor approval threshold
    IGOR_APPROVAL_THRESHOLD: float = Field(
        default=0.7,
        ge=0.0,
        le=1.0,
        description="Confidence threshold below which Igor approval is required",
    )

    # Redis configuration
    REDIS_URL: str = Field(
        default_factory=lambda: os.getenv("REDIS_URL", "redis://localhost:6379/0"),
        description="Redis connection string for caching",
    )

    # Graph cache TTLs
    GRAPH_CACHE_TTL_GOVERNANCE_SEC: int = Field(
        default=90, ge=10, description="TTL for governance queries (seconds)"
    )

    GRAPH_CACHE_TTL_DEFAULT_SEC: int = Field(
        default=450, ge=10, description="TTL for exploratory queries (seconds)"
    )

    # Schema version (computed, not configurable)
    GRAPH_CACHE_SCHEMA_VERSION: str = Field(
        default="", description="Graph cache schema version (computed at runtime)"
    )

    model_config = {"extra": "allow"}


# Singleton instance
_config: CursorLangGraphConfig | None = None


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


# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "CON-FOUN-002",
    "governance_level": "critical",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": ["memory.graph_search_cache"],
    "tags": [
        "api",
        "caching",
        "data-models",
        "foundation",
        "pydantic",
        "schema",
        "testing",
        "validation",
    ],
    "keywords": ["configuration", "cursor", "graph", "lang", "langgraph", "reset"],
    "business_value": "Implements CursorLangGraphConfig for cursor langgraph config functionality",
    "last_modified": "2026-01-11T14:51:06Z",
    "modified_by": "L9_Codegen_Engine",
    "change_summary": "Initial generation with DORA compliance",
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
