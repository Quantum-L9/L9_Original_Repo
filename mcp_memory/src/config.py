"""
Configuration for L9 MCP Memory Server.
Environment-based settings with HNSW and memory compounding support.
"""

# ============================================================================
__dora_meta__ = {
    "component_name": "Config",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2026-01-11T18:13:39Z",
    "updated_at": "2026-01-17T23:47:56Z",
    "layer": "integration",
    "domain": "mcp_integration",
    "module_name": "config",
    "type": "schema",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": ["OpenAI API", "Redis"],
        "memory_layers": ["semantic_memory", "working_memory"],
        "imported_by": ["tests.memory.test_governance_invariants"],
    },
}
# ============================================================================

import structlog
from pydantic_settings import BaseSettings

logger = structlog.get_logger(__name__)


class Settings(BaseSettings):
    # Server Configuration
    # Single source of truth for MCP server host/port/env
    # UNIFIED ARCHITECTURE: MCP endpoints live inside l9-api (port 8000)
    # Public URL: https://l9.quantumaipartners.com or https://157.180.73.53:9001
    # Port 8000 = l9-api Docker container (unified - handles all traffic)
    # Port 9001 = Alternate HTTPS front door (IP-based), routes to 8000
    # NOTE: Port 9002 is DEPRECATED and never deployed - do not use
    MCP_HOST: str = "127.0.0.1"  # Default: localhost only (Caddy reverse proxy)
    MCP_PORT: int = (
        8000  # Default: 8000 (unified l9-api) - NOTE: Not used when running in Docker
    )
    MCP_ENV: str = "production"  # Default: production
    LOG_LEVEL: str = "INFO"

    # OpenAI Configuration
    OPENAI_API_KEY: str
    # CRITICAL: Write AND search MUST use the SAME embedding model
    # text-embedding-3-large produces better semantic search results
    # Both substrate_service (write) and embeddings.py (search) use this setting
    OPENAI_EMBED_MODEL: str = "text-embedding-3-large"
    OPENAI_EMBED_DIM: int = 1536

    # Database Configuration
    MEMORY_DSN: str

    # Memory Lifecycle
    MEMORY_SHORT_TERM_HOURS: int = 24
    MEMORY_MEDIUM_TERM_HOURS: int = 168
    MEMORY_CLEANUP_INTERVAL_MINUTES: int = 720
    MEMORY_SHORT_RETENTION_DAYS: int = 14
    MEMORY_MEDIUM_RETENTION_DAYS: int = 30

    # Vector Search Configuration
    VECTOR_SEARCH_THRESHOLD: float = 0.7
    VECTOR_SEARCH_TOP_K: int = 10

    # Vector Index Configuration (HNSW)
    VECTOR_INDEX_TYPE: str = "hnsw"
    HNSW_M: int = 16
    HNSW_EF_CONSTRUCTION: int = 64
    HNSW_EF_SEARCH: int = 40

    # Memory Compounding Configuration
    COMPOUNDING_ENABLED: bool = True
    COMPOUNDING_SIMILARITY_THRESHOLD: float = 0.92
    COMPOUNDING_MIN_COUNT: int = 3

    # Importance Decay Configuration
    DECAY_ENABLED: bool = True
    DECAY_RATE_PER_DAY: float = 0.01
    ACCESS_BOOST_PER_HIT: float = 0.05

    # Authentication - Dual API Keys for L and C
    # See: mcp_memory/memory-setup-instructions.md for governance spec
    # Primary keys (required):
    # - MCP_API_KEY_L: L-CTO kernel (full read/write/delete)
    # - MCP_API_KEY_C: Cursor IDE (read all, write/delete own only)
    # Legacy fallbacks (optional, for backward compatibility):
    # - MCP_API_KEY: Shared fallback (maps to L if MCP_API_KEY_L not set)
    # - MCPL9MEMORYKEY: Legacy alias (same as MCP_API_KEY)
    # - MCP_API_KEYL: Legacy alias for MCP_API_KEY_L
    # - MCP_API_KEYC: Legacy alias for MCP_API_KEY_C
    MCP_API_KEY_L: str = ""  # L-CTO API key (required, but allow empty for validation)
    MCP_API_KEY_C: str = (
        ""  # Cursor IDE API key (required, but allow empty for validation)
    )

    # Legacy fallback keys (optional)
    MCP_API_KEY: str = ""  # Shared fallback (legacy)
    MCPL9MEMORYKEY: str = ""  # Legacy alias (same as MCP_API_KEY)
    MCP_API_KEYL: str = ""  # Legacy alias for MCP_API_KEY_L
    MCP_API_KEYC: str = ""  # Legacy alias for MCP_API_KEY_C

    # Shared User Identity (L and C operate in same semantic space)
    # Separation is enforced via metadata.creator and caller identity
    # See: memory-setup-instructions.md → userid_strategy
    L_CTO_USER_ID: str = "l9-shared"  # Shared userid for L + Cursor collaboration

    # Project isolation (server-derived, not client-supplied)
    MCP_PROJECT_ID: str = "l9"

    # Redis (optional)
    REDIS_ENABLED: bool = False
    REDIS_HOST: str = "127.0.0.1"
    REDIS_PORT: int = 6379

    # Project isolation (server-derived, not client-supplied)
    MCP_PROJECT_ID: str = "l9"

    # ==========================================================================
    # Governance Hardening Feature Flags
    # See: Memory Governance Hardening Plan v2.0
    # ==========================================================================
    # Master switch for governance hardening
    # - False: Legacy mode (unauthenticated REST routes allowed)
    # - True: All routes require authentication (SECURE DEFAULT)
    # NOTE: Defaults to True (fail-closed). Set GOVERNANCE_HARDENING_ENABLED=false
    #       in .env to disable during development/testing.
    GOVERNANCE_HARDENING_ENABLED: bool = True

    # Enforcement mode (only applies when GOVERNANCE_HARDENING_ENABLED=True)
    # - "log_only": Log violations but allow requests through (for monitoring)
    # - "enforce": Reject requests that violate governance rules
    GOVERNANCE_ENFORCEMENT_MODE: str = "log_only"

    # Audit logging configuration
    AUDIT_FALLBACK_PATH: str = "/var/log/l9/audit.jsonl"
    AUDIT_CIRCUIT_BREAKER_THRESHOLD: int = 3
    AUDIT_CIRCUIT_BREAKER_TIMEOUT: int = 60

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()


def get_api_key_l() -> str:
    """Get L-CTO API key with legacy fallback support.

    Priority:
    1. MCP_API_KEY_L (primary)
    2. MCP_API_KEYL (legacy alias)
    3. MCP_API_KEY (shared fallback)
    4. MCPL9MEMORYKEY (legacy alias)
    """
    if settings.MCP_API_KEY_L:
        return settings.MCP_API_KEY_L
    if settings.MCP_API_KEYL:
        return settings.MCP_API_KEYL
    if settings.MCP_API_KEY:
        return settings.MCP_API_KEY
    if settings.MCPL9MEMORYKEY:
        return settings.MCPL9MEMORYKEY
    return ""


def get_api_key_c() -> str:
    """Get Cursor API key with legacy fallback support.

    Priority:
    1. MCP_API_KEY_C (primary)
    2. MCP_API_KEYC (legacy alias)
    3. MCP_API_KEY (shared fallback)
    4. MCPL9MEMORYKEY (legacy alias)
    """
    if settings.MCP_API_KEY_C:
        return settings.MCP_API_KEY_C
    if settings.MCP_API_KEYC:
        return settings.MCP_API_KEYC
    if settings.MCP_API_KEY:
        return settings.MCP_API_KEY
    if settings.MCPL9MEMORYKEY:
        return settings.MCPL9MEMORYKEY
    return ""


def validate_api_keys() -> None:
    """Validate that at least one API key is configured. Fail fast with clear error."""
    api_key_l = get_api_key_l()
    api_key_c = get_api_key_c()

    if not api_key_l and not api_key_c:
        raise ValueError(
            "MCP_API_KEY_L or MCP_API_KEY_C must be set. "
            "Legacy fallbacks (MCP_API_KEY, MCPL9MEMORYKEY) are optional but at least one key is required."
        )

    if not api_key_l:
        import warnings

        warnings.warn(
            "MCP_API_KEY_L not set. L-CTO operations will fail. "
            "Set MCP_API_KEY_L or use legacy MCP_API_KEYL/MCP_API_KEY/MCPL9MEMORYKEY.",
            UserWarning,
            stacklevel=2,
        )

    if not api_key_c:
        import warnings

        warnings.warn(
            "MCP_API_KEY_C not set. Cursor operations will fail. "
            "Set MCP_API_KEY_C or use legacy MCP_API_KEYC/MCP_API_KEY/MCPL9MEMORYKEY.",
            UserWarning,
            stacklevel=2,
        )


# Validate on module load (warn but don't exit - allow app to start)
try:
    validate_api_keys()
except ValueError as e:
    logger.warning("MCP server API keys not configured", error=str(e))
    # Don't exit - allow app to start, MCP features will be disabled

# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "MCP-INTE-001",
    "governance_level": "medium",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": [
        "api",
        "auth",
        "integration",
        "logging",
        "mcp-integration",
        "monitoring",
        "rest-api",
        "schema",
        "testing",
        "validation",
    ],
    "keywords": ["api", "memory", "validate"],
    "business_value": "Provides config components including Settings, Config",
    "last_modified": "2026-01-17T23:47:56Z",
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
