"""
Configuration management for symbolic computation module.

Loads configuration from environment variables and provides defaults.
"""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from dotenv import load_dotenv

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
        description="Enable expression caching"
    )
    cache_size: int = Field(
        default=128,
        env="SYMBOLIC_CACHE_SIZE",
        description="Maximum cache size"
    )

    # Performance settings
    default_backend: str = Field(
        default="numpy",
        env="SYMBOLIC_DEFAULT_BACKEND",
        description="Default numerical backend"
    )
    enable_metrics: bool = Field(
        default=True,
        env="SYMBOLIC_ENABLE_METRICS",
        description="Enable performance metrics"
    )

    # Code generation settings
    codegen_temp_dir: str = Field(
        default="/tmp/sympy_codegen",
        env="SYMBOLIC_CODEGEN_TEMP_DIR",
        description="Temporary directory for code generation"
    )
    default_language: str = Field(
        default="C",
        env="SYMBOLIC_DEFAULT_LANGUAGE",
        description="Default code generation language"
    )

    # Logging settings
    log_level: str = Field(
        default="INFO",
        env="SYMBOLIC_LOG_LEVEL",
        description="Logging level"
    )
    enable_structured_logging: bool = Field(
        default=True,
        env="SYMBOLIC_ENABLE_STRUCTURED_LOGGING",
        description="Enable JSON structured logging"
    )

    # Security settings
    max_expression_length: int = Field(
        default=10000,
        env="SYMBOLIC_MAX_EXPRESSION_LENGTH",
        description="Maximum expression length"
    )
    allow_dangerous_functions: bool = Field(
        default=False,
        env="SYMBOLIC_ALLOW_DANGEROUS_FUNCTIONS",
        description="Allow potentially dangerous functions"
    )



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
