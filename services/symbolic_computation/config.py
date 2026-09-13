"""
Configuration management for symbolic computation module.

Loads configuration from environment variables and provides defaults.
"""


from dotenv import load_dotenv
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# Load environment variables
load_dotenv()


class SymbolicComputationConfig(BaseSettings):
    """Configuration settings for symbolic computation."""

    model_config = SettingsConfigDict(
        extra="ignore",  # Allow extra env vars
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Cache settings
    cache_enabled: bool = Field(
        default=True,
        env="SYMBOLIC_CACHE_ENABLED",
        description="Enable expression caching",
    )
    cache_size: int = Field(
        default=128, env="SYMBOLIC_CACHE_SIZE", description="Maximum cache size"
    )

    # Performance settings
    default_backend: str = Field(
        default="numpy",
        env="SYMBOLIC_DEFAULT_BACKEND",
        description="Default numerical backend",
    )
    enable_metrics: bool = Field(
        default=True,
        env="SYMBOLIC_ENABLE_METRICS",
        description="Enable performance metrics",
    )

    # Code generation settings
    codegen_temp_dir: str = Field(
        default="/tmp/sympy_codegen",  # noqa: S108 — intentional temp path for codegen
        env="SYMBOLIC_CODEGEN_TEMP_DIR",
        description="Temporary directory for code generation",
    )
    default_language: str = Field(
        default="C",
        env="SYMBOLIC_DEFAULT_LANGUAGE",
        description="Default code generation language",
    )

    # Logging settings
    log_level: str = Field(
        default="INFO", env="SYMBOLIC_LOG_LEVEL", description="Logging level"
    )
    enable_structured_logging: bool = Field(
        default=True,
        env="SYMBOLIC_ENABLE_STRUCTURED_LOGGING",
        description="Enable JSON structured logging",
    )

    # Security settings
    max_expression_length: int = Field(
        default=10000,
        env="SYMBOLIC_MAX_EXPRESSION_LENGTH",
        description="Maximum expression length",
    )
    allow_dangerous_functions: bool = Field(
        default=False,
        env="SYMBOLIC_ALLOW_DANGEROUS_FUNCTIONS",
        description="Allow potentially dangerous functions",
    )
    dangerous_functions: list[str] = Field(
        default_factory=list,
        env="SYMBOLIC_DANGEROUS_FUNCTIONS",
        description="List of dangerous functions to block",
    )
    redis_cache_ttl: int = Field(
        default=3600,
        env="SYMBOLIC_REDIS_CACHE_TTL",
        description="Redis cache TTL in seconds",
    )
    keyspace: str = Field(
        default="symbolic",
        env="SYMBOLIC_KEYSPACE",
        description="Redis keyspace prefix",
    )

    def get_redis_key(self, expr_hash: str, backend: str) -> str:
        """Get Redis key for expression result."""
        return f"{self.keyspace}:{expr_hash}:{backend}"

    def get_compiled_key(self, expr_hash: str) -> str:
        """Get Redis key for compiled function."""
        return f"{self.keyspace}:compiled:{expr_hash}"


# Global configuration instance
config = SymbolicComputationConfig()


def get_config() -> SymbolicComputationConfig:
    """
    Get configuration instance.

    Returns:
        Configuration object
    """
    return config


def reload_config():
    """Reload configuration from environment."""
    global config
    config = SymbolicComputationConfig()


# Runtime execution trace - updated automatically on every execution
