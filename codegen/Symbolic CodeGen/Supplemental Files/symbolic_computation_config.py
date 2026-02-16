"""
Configuration management for symbolic computation module.

Loads configuration from environment variables and provides defaults.
"""

# ============================================================================
__dora_meta__ = {
    "component_name": "Symbolic Computation Config",
    "module_version": "1.0.0",
    "created_by": "L9_Codegen_Engine",
    "created_at": "2026-01-01T13:15:14Z",
    "updated_at": "2026-01-15T15:48:34Z",
    "layer": "operations",
    "domain": "current_work",
    "module_name": "symbolic_computation_config",
    "type": "schema",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": [],
        "memory_layers": [],
        "imported_by": [],
    },
}
# ============================================================================

import os
from typing import Optional
from pydantic import BaseSettings, Field
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class SymbolicComputationConfig(BaseSettings):
    """Configuration settings for symbolic computation."""

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

    class Config:
        """Pydantic configuration."""
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


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
    "component_id": "CUR-OPER-030",
    "governance_level": "medium",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": ["caching", "current-work", "metrics", "operations", "schema", "validation"],
    "keywords": ["computation", "configuration", "module", "reload", "symbolic"],
    "business_value": "Provides symbolic computation config components including SymbolicComputationConfig, Config",
    "last_modified": "2026-01-15T15:48:34Z",
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
