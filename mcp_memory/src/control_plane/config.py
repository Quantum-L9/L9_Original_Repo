"""Unified Configuration Interface.

All configuration must flow through this module.
No other module reads from environment or YAML directly.

Configuration precedence:
  1. Environment variables (highest priority)
  2. .env file
  3. YAML config files
  4. Defaults (lowest priority)
"""

from dataclasses import dataclass
from typing import Optional
from functools import lru_cache
import os
from dotenv import load_dotenv


@dataclass(frozen=True)
class Settings:
    """Global configuration for L9 Memory System.
    
    This is the SINGLE SOURCE OF TRUTH for all settings.
    Access via get_settings() singleton.
    """
    
    # Service Configuration
    MCP_HOST: str = "0.0.0.0"
    MCP_PORT: int = 8000
    MCP_ENV: str = "production"
    LOG_LEVEL: str = "INFO"
    
    # Database
    MEMORY_DSN: Optional[str] = None
    DB_POOL_SIZE: int = 20
    DB_TIMEOUT: int = 30
    
    # Embeddings
    OPENAI_EMBED_MODEL: str = "text-embedding-3-small"
    OPENAI_API_KEY: Optional[str] = None
    EMBEDDING_PROVIDER: str = "openai"
    
    # API Keys
    API_KEY_L: Optional[str] = None
    API_KEY_C: Optional[str] = None
    MCP_API_KEY: Optional[str] = None  # Legacy
    MCPL9MEMORYKEY: Optional[str] = None  # Legacy
    
    # Governance
    GOVERNANCE_HARDENING_ENABLED: bool = True
    GOVERNANCE_ENFORCEMENT_MODE: str = "strict"  # strict, moderate, permissive
    L_CTO_USER_ID: str = "L_CTO_DEFAULT"
    
    # Audit
    AUDIT_FALLBACK_PATH: str = "/tmp/l9_audit_fallback.jsonl"
    AUDIT_CIRCUIT_BREAKER_THRESHOLD: int = 3
    AUDIT_CIRCUIT_BREAKER_TIMEOUT: int = 60
    
    # Feature Flags (all default to False)
    FEATURE_EXPERIMENTAL_TEMPORAL: bool = False
    FEATURE_GRAPH_RELATIONSHIPS: bool = False
    FEATURE_PROACTIVE_RECALL: bool = False
    
    @classmethod
    def from_env(cls) -> "Settings":
        """Load settings from environment."""
        load_dotenv()
        
        return cls(
            MCP_HOST=os.getenv("MCP_HOST", "0.0.0.0"),
            MCP_PORT=int(os.getenv("MCP_PORT", "8000")),
            MCP_ENV=os.getenv("MCP_ENV", "production"),
            LOG_LEVEL=os.getenv("LOG_LEVEL", "INFO"),
            MEMORY_DSN=os.getenv("MEMORY_DSN"),
            DB_POOL_SIZE=int(os.getenv("DB_POOL_SIZE", "20")),
            DB_TIMEOUT=int(os.getenv("DB_TIMEOUT", "30")),
            OPENAI_EMBED_MODEL=os.getenv(
                "OPENAI_EMBED_MODEL",
                "text-embedding-3-small"
            ),
            OPENAI_API_KEY=os.getenv("OPENAI_API_KEY"),
            EMBEDDING_PROVIDER=os.getenv("EMBEDDING_PROVIDER", "openai"),
            API_KEY_L=os.getenv("API_KEY_L"),
            API_KEY_C=os.getenv("API_KEY_C"),
            MCP_API_KEY=os.getenv("MCP_API_KEY"),
            MCPL9MEMORYKEY=os.getenv("MCPL9MEMORYKEY"),
            GOVERNANCE_HARDENING_ENABLED=(
                os.getenv("GOVERNANCE_HARDENING_ENABLED", "true").lower() == "true"
            ),
            GOVERNANCE_ENFORCEMENT_MODE=os.getenv(
                "GOVERNANCE_ENFORCEMENT_MODE",
                "strict"
            ),
            L_CTO_USER_ID=os.getenv("L_CTO_USER_ID", "L_CTO_DEFAULT"),
            AUDIT_FALLBACK_PATH=os.getenv(
                "AUDIT_FALLBACK_PATH",
                "/tmp/l9_audit_fallback.jsonl"
            ),
            AUDIT_CIRCUIT_BREAKER_THRESHOLD=int(
                os.getenv("AUDIT_CIRCUIT_BREAKER_THRESHOLD", "3")
            ),
            AUDIT_CIRCUIT_BREAKER_TIMEOUT=int(
                os.getenv("AUDIT_CIRCUIT_BREAKER_TIMEOUT", "60")
            ),
            FEATURE_EXPERIMENTAL_TEMPORAL=(
                os.getenv("FEATURE_EXPERIMENTAL_TEMPORAL", "false").lower() == "true"
            ),
            FEATURE_GRAPH_RELATIONSHIPS=(
                os.getenv("FEATURE_GRAPH_RELATIONSHIPS", "false").lower() == "true"
            ),
            FEATURE_PROACTIVE_RECALL=(
                os.getenv("FEATURE_PROACTIVE_RECALL", "false").lower() == "true"
            ),
        )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Get settings singleton.
    
    SINGLETON: Only loads once per process.
    Changes to environment after first call are ignored.
    
    Returns:
        Global Settings instance
    """
    return Settings.from_env()


def reset_settings() -> None:
    """Reset settings cache (for testing only)."""
    get_settings.cache_clear()


__all__ = [
    "Settings",
    "get_settings",
    "reset_settings",
]
