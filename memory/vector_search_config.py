"""
Vector Search Configuration

Provides runtime configuration for optimized vector search performance.

Author: L9 Platform Team
Date: 2026-01-17
"""

# ============================================================================
__dora_meta__ = {
    "component_name": "Vector Search Config",
    "module_version": "1.0.0",
    "created_by": "cryptoxdog",
    "created_at": "2026-01-23T15:07:20Z",
    "updated_at": "2026-01-24T13:02:52Z",
    "layer": "learning",
    "domain": "memory_substrate",
    "module_name": "vector_search_config",
    "type": "service",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": ["PostgreSQL"],
        "memory_layers": [],
        "imported_by": [
            "memory.substrate_repository",
            "tests.memory.test_query_cache_and_vector",
        ],
    },
}
# ============================================================================


import structlog

logger = structlog.get_logger(__name__)


class VectorSearchConfig:
    """
    Configuration for HNSW vector search optimization.

    HNSW (Hierarchical Navigable Small World) parameters:
    - ef_search: Size of dynamic candidate list during search
                 Higher = better recall, slower search
                 Default: 40, Range: 1-1000

    Recommended values:
    - Fast search (lower recall): ef_search = 20
    - Balanced (recommended): ef_search = 40
    - High recall: ef_search = 100

    Usage:
        config = VectorSearchConfig(ef_search=40)
        await config.apply(conn)
    """

    def __init__(
        self,
        ef_search: int = 40,
        enable_seqscan: bool = False,
    ):
        """
        Initialize vector search configuration.

        Args:
            ef_search: HNSW ef_search parameter (1-1000)
            enable_seqscan: Whether to allow sequential scans (usually False)
        """
        if not 1 <= ef_search <= 1000:
            raise ValueError(f"ef_search must be between 1 and 1000, got {ef_search}")

        self.ef_search = ef_search
        self.enable_seqscan = enable_seqscan

        logger.info(
            "vector_search_config_initialized",
            ef_search=ef_search,
            enable_seqscan=enable_seqscan,
        )

    async def apply(self, conn) -> None:
        """
        Apply configuration to database connection.

        Args:
            conn: asyncpg connection
        """
        # Set HNSW ef_search parameter
        await conn.execute(f"SET hnsw.ef_search = {self.ef_search}")

        # Disable sequential scans to force index usage
        if not self.enable_seqscan:
            await conn.execute("SET enable_seqscan = off")

        logger.debug(
            "vector_search_config_applied",
            ef_search=self.ef_search,
            enable_seqscan=self.enable_seqscan,
        )

    @classmethod
    def fast(cls) -> "VectorSearchConfig":
        """Fast search configuration (lower recall)."""
        return cls(ef_search=20)

    @classmethod
    def balanced(cls) -> "VectorSearchConfig":
        """Balanced configuration (recommended)."""
        return cls(ef_search=40)

    @classmethod
    def high_recall(cls) -> "VectorSearchConfig":
        """High recall configuration (slower)."""
        return cls(ef_search=100)


# Global configuration instance
_global_config: VectorSearchConfig | None = None


def get_vector_config() -> VectorSearchConfig:
    """Get or create global vector search configuration."""
    global _global_config
    if _global_config is None:
        _global_config = VectorSearchConfig.balanced()
    return _global_config


def set_vector_config(config: VectorSearchConfig) -> None:
    """Set global vector search configuration."""
    global _global_config
    _global_config = config
    logger.info("global_vector_config_updated", ef_search=config.ef_search)


# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "MEM-LEAR-042",
    "governance_level": "critical",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": [
        "async",
        "debugging",
        "learning",
        "logging",
        "memory-substrate",
        "service",
    ],
    "keywords": [
        "apply",
        "balanced",
        "configuration",
        "fast",
        "high",
        "recall",
        "search",
        "vector",
    ],
    "business_value": "Provides runtime configuration for optimized vector search performance. Author: L9 Platform Team Date: 2026-01-17",
    "last_modified": "2026-01-24T13:02:52Z",
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
