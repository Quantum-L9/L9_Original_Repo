"""
L9 Memory Substrate - Configuration Settings
Version: 1.0.0

Pydantic settings for environment variables and configuration.
"""


from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings


class MemorySubstrateSettings(BaseSettings):
    """
    Configuration for the Memory Substrate module.

    Environment variables:
    - DATABASE_URL: Postgres DSN with pgvector extension enabled (required)
    - EMBEDDING_MODEL: Embedding model name (optional, default: text-embedding-3-large)
    - OPENAI_API_KEY: Required for embedding generation
    """

    # Database
    # Note: Required at runtime via DATABASE_URL env var
    database_url: str | None = Field(
        default=None,
        alias="DATABASE_URL",
        description="Postgres DSN with pgvector extension enabled",
    )

    # Embedding configuration
    embedding_model: str = Field(
        default="text-embedding-3-large",
        alias="EMBEDDING_MODEL",
        description="Embedding model name",
    )
    embedding_dimensions: int = Field(
        default=1536, description="Embedding vector dimensions (must match model)"
    )

    # OpenAI API (for embeddings)
    openai_api_key: str | None = Field(
        default=None,
        alias="OPENAI_API_KEY",
        description="OpenAI API key for embedding generation",
    )

    # API configuration
    api_host: str = Field(default="0.0.0.0", alias="API_HOST")  # noqa: S104 — intentional for container binding
    api_port: int = Field(default=8080, alias="API_PORT")
    api_prefix: str = Field(default="/api/v1/memory", alias="API_PREFIX")

    # Substrate namespace
    namespace: str = Field(
        default="plasticos",
        alias="SUBSTRATE_NAMESPACE",
        description="Namespace for memory isolation",
    )

    # Performance tuning
    db_pool_size: int = Field(default=5, alias="DB_POOL_SIZE")
    db_max_overflow: int = Field(default=10, alias="DB_MAX_OVERFLOW")

    # Sync configuration
    sync_interval_minutes: int = Field(
        default=10,
        alias="SYNC_INTERVAL_MINUTES",
        description="Interval for background sync to external systems",
    )

    # DAG Enrichment settings (v2.1.0 - GMP-67 unified pipeline)
    enable_dag_enrichment: bool = Field(
        default=False,
        alias="ENABLE_DAG_ENRICHMENT",
        description="Enable SubstrateDAG enrichment after core writes (default: False for safety rollout)",
    )
    dag_enrichment_timeout_seconds: float = Field(
        default=30.0,
        alias="DAG_ENRICHMENT_TIMEOUT",
        description="Max time for DAG enrichment before timeout (enrichment failure, core write preserved)",
    )

    class Config:
        """
        Config class manages environment variable settings for the Memory Substrate, ensuring proper configuration loading.

        Args:
            env_file: Path to the environment file, defaulting to ".env".
            env_file_encoding: Encoding for the environment file, default "utf-8".
            case_sensitive: Whether environment variable names are case-sensitive, default False.
            extra: How to handle unknown environment variables, default "ignore".

        Returns:
            A pydantic BaseSettings subclass instance with loaded configuration.
        """

        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        extra = "ignore"


@lru_cache(maxsize=1)
def get_settings() -> MemorySubstrateSettings:
    """Get or create settings singleton. CACHED."""
    return MemorySubstrateSettings()


def reset_settings() -> None:
    """Reset settings (useful for testing)."""
    get_settings.cache_clear()


# Runtime execution trace - updated automatically on every execution
