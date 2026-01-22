"""
Configuration management for symbolic computation module.

Loads configuration from environment variables and provides defaults.
"""

# ============================================================================
__dora_meta__ = {
    "component_name": "Config",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2026-01-02T15:15:57Z",
    "updated_at": "2026-01-14T15:03:00Z",
    "layer": "operations",
    "domain": "symbolic_computation",
    "module_name": "config",
    "type": "config",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": [],
        "memory_layers": [],
        "imported_by": [
            "services.symbolic_computation.api.routes",
            "services.symbolic_computation.core.cache_manager",
            "services.symbolic_computation.core.code_generator",
            "services.symbolic_computation.core.expression_evaluator",
            "services.symbolic_computation.core.metrics",
            "services.symbolic_computation.core.optimizer",
            "services.symbolic_computation.core.validator",
            "services.symbolic_computation.tools.symbolic_tool",
            "tests.services.symbolic_computation.test_expression_evaluator",
            "tests.services.symbolic_computation.test_validator",
        ],
    },
}
# ============================================================================

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
        default="/tmp/sympy_codegen",
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


# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "SER-OPER-014",
    "governance_level": "medium",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": [
        "caching",
        "config",
        "metrics",
        "operations",
        "symbolic-computation",
        "validation",
    ],
    "keywords": ["computation", "configuration", "module", "reload", "symbolic"],
    "business_value": "Implements SymbolicComputationConfig for config functionality",
    "last_modified": "2026-01-14T15:03:00Z",
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
