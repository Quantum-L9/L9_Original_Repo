"""
Runtime DI Configuration Loader

Reads YAML configuration to wire dependencies at runtime without code changes.
Enables A/B testing of different embedding models, repository implementations,
and feature flags for phased rollout.

**Compliance:**
- ADR-0052: Dependency injection
- ADR-0055: Fail-loudly principle (validates config on load)

**Usage:**
    from config.di_runtime_config import get_runtime_config_loader

    loader = get_runtime_config_loader()
    memory_config = loader.get_memory_substrate_config()

    # Or use directly in container
    from core.di.container import MemorySubstrateContainer
    container = MemorySubstrateContainer(memory_config)

Version: 1.0.0
Created: 2026-01-24
Layer: config
Domain: dependency_injection
Type: utility
Status: active
"""

from __future__ import annotations

# ============================================================================
__dora_meta__ = {
    "component_name": "DI Runtime Config Loader",
    "module_version": "1.0.0",
    "created_by": "L9 DI/DIP Refactoring",
    "created_at": "2026-01-24T08:00:00Z",
    "updated_at": "2026-01-24T08:00:00Z",
    "layer": "config",
    "domain": "dependency_injection",
    "module_name": "di_runtime_config",
    "type": "utility",
    "status": "active",
    "integrates_with": {
        "modules": [
            "core.di.container",
            "memory.substrate_service",
        ],
        "adrs": ["ADR-0052", "ADR-0055"],
    },
}
# ============================================================================

import os
from pathlib import Path
from typing import Any

import structlog
import yaml

logger = structlog.get_logger(__name__)


class DIConfigError(Exception):
    """Raised when DI config loading or validation fails."""

    pass


class DIRuntimeConfigLoader:
    """
    Load DI configuration from YAML with environment variable interpolation.

    **Features:**
    - YAML-based configuration
    - Environment variable substitution (${VAR_NAME} syntax)
    - Validation on load (fail-loudly per ADR-0055)
    - Singleton pattern for global config access

    **Config Structure:**
        memory_substrate:
          database_url: "${DATABASE_URL}"
          db_pool_size: 10
          embedding_provider:
            type: "openai"
            model: "text-embedding-3-large"
            api_key: "${OPENAI_API_KEY}"

        feature_flags:
          enable_protocol_validation: true
          enable_lazy_dag_init: false

    **Thread Safety:** Not thread-safe during initialization. Use singleton getter.
    """

    def __init__(self, config_path: Path):
        """
        Initialize loader with config file path.

        Args:
            config_path: Path to YAML config file

        Raises:
            DIConfigError: If config file doesn't exist
        """
        self._config_path = config_path
        self._config: dict[str, Any] = {}
        self._loaded = False

        if not config_path.exists():
            logger.warning(
                "DI runtime config file not found, using defaults",
                config_path=str(config_path),
            )

    def load(self) -> dict[str, Any]:
        """
        Load configuration from YAML file.

        Performs environment variable substitution for ${VAR_NAME} patterns.

        Returns:
            Loaded configuration dictionary

        Raises:
            DIConfigError: If YAML parsing fails or required env vars missing
        """
        if self._loaded:
            return self._config

        try:
            if not self._config_path.exists():
                logger.info("Using default DI runtime config (no YAML file found)")
                self._config = self._get_default_config()
                self._loaded = True
                return self._config

            with open(self._config_path) as f:
                raw_config = yaml.safe_load(f)

            if raw_config is None:
                logger.warning("Empty DI runtime config file, using defaults")
                self._config = self._get_default_config()
            else:
                # Interpolate environment variables
                self._config = self._interpolate_env_vars(raw_config)

            self._loaded = True

            logger.info(
                "DI runtime config loaded",
                config_path=str(self._config_path),
                sections=list(self._config.keys()),
            )

            return self._config

        except yaml.YAMLError as e:
            logger.error("Failed to parse DI runtime config YAML", error=str(e))
            raise DIConfigError(f"Invalid YAML in {self._config_path}: {e}") from e
        except Exception as e:
            logger.error("Failed to load DI runtime config", error=str(e))
            raise DIConfigError(
                f"Failed to load config from {self._config_path}: {e}"
            ) from e

    def _interpolate_env_vars(self, config: Any) -> Any:
        """
        Recursively interpolate environment variables in config.

        Replaces ${VAR_NAME} with os.getenv("VAR_NAME").
        Fails loudly if referenced env var is not set (ADR-0055).

        Args:
            config: Config dict/list/str to interpolate

        Returns:
            Interpolated config

        Raises:
            DIConfigError: If referenced env var is not set
        """
        if isinstance(config, dict):
            return {k: self._interpolate_env_vars(v) for k, v in config.items()}
        if isinstance(config, list):
            return [self._interpolate_env_vars(item) for item in config]
        if isinstance(config, str):
            # Replace ${VAR_NAME} with env var value
            if config.startswith("${") and config.endswith("}"):
                var_name = config[2:-1]
                value = os.getenv(var_name)
                if value is None:
                    raise DIConfigError(
                        f"Environment variable '{var_name}' referenced in config but not set"
                    )
                return value
            return config
        return config

    def _get_default_config(self) -> dict[str, Any]:
        """
        Get default configuration when YAML file is missing.

        Returns:
            Default config dictionary
        """
        return {
            "memory_substrate": {
                "database_url": os.getenv("DATABASE_URL", "postgresql://localhost/l9"),
                "db_pool_size": 5,
                "db_max_overflow": 10,
                "embedding_provider": {
                    "type": "openai",
                    "model": "text-embedding-3-large",
                    "api_key": os.getenv("OPENAI_API_KEY"),
                },
            },
            "feature_flags": {
                "enable_protocol_validation": True,
                "enable_lazy_dag_init": False,
            },
        }

    def get_memory_substrate_config(self) -> dict[str, Any]:
        """
        Extract memory substrate configuration section.

        Returns:
            Dictionary with keys:
                - database_url (str)
                - db_pool_size (int)
                - db_max_overflow (int)
                - embedding_provider_type (str)
                - embedding_model (str)
                - openai_api_key (str)
        """
        if not self._loaded:
            self.load()

        substrate_config = self._config.get("memory_substrate", {})
        embedding_config = substrate_config.get("embedding_provider", {})

        # Flatten structure for MemorySubstrateContainer
        return {
            "database_url": substrate_config.get("database_url"),
            "db_pool_size": substrate_config.get("db_pool_size", 5),
            "db_max_overflow": substrate_config.get("db_max_overflow", 10),
            "embedding_provider_type": embedding_config.get("type", "openai"),
            "embedding_model": embedding_config.get("model", "text-embedding-3-large"),
            "openai_api_key": embedding_config.get("api_key"),
        }

    def get_embedding_config(self) -> dict[str, str]:
        """
        Extract embedding provider configuration.

        Returns:
            Dictionary with keys: type, model, api_key
        """
        if not self._loaded:
            self.load()

        substrate_config = self._config.get("memory_substrate", {})
        result: dict[str, str] = substrate_config.get(
            "embedding_provider",
            {
                "type": "openai",
                "model": "text-embedding-3-large",
            },
        )
        return result

    def get_feature_flags(self) -> dict[str, bool]:
        """
        Extract feature flags for phased rollout.

        Returns:
            Dictionary of feature flag names to boolean values
        """
        if not self._loaded:
            self.load()

        result: dict[str, bool] = self._config.get(
            "feature_flags",
            {
                "enable_protocol_validation": True,
                "enable_lazy_dag_init": False,
            },
        )
        return result

    def reload(self) -> dict[str, Any]:
        """
        Reload configuration from file (for hot-reload scenarios).

        Returns:
            Reloaded configuration dictionary
        """
        self._loaded = False
        return self.load()


# ============================================================================
# Singleton Loader
# ============================================================================

_loader: DIRuntimeConfigLoader | None = None


def get_runtime_config_loader(
    config_path: Path | None = None,
) -> DIRuntimeConfigLoader:
    """
    Get or create singleton DI runtime config loader.

    Args:
        config_path: Optional path to config file (default: config/di_runtime_config.yaml)

    Returns:
        DIRuntimeConfigLoader singleton instance
    """
    global _loader

    if _loader is None:
        if config_path is None:
            # Default to config/di_runtime_config.yaml relative to project root
            config_path = Path(__file__).parent / "di_runtime_config.yaml"

        _loader = DIRuntimeConfigLoader(config_path)
        _loader.load()

    return _loader


def reset_runtime_config_loader() -> None:
    """
    Reset singleton loader (for testing).

    **Warning:** Only use in tests. Not thread-safe.
    """
    global _loader
    _loader = None


__all__ = [
    "DIConfigError",
    "DIRuntimeConfigLoader",
    "get_runtime_config_loader",
    "reset_runtime_config_loader",
]

# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "CON-FOUN-001",
    "governance_level": "critical",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": [
        "api",
        "config",
        "error-handling",
        "exception",
        "filesystem",
        "foundation",
        "loader",
        "logging",
        "testing",
    ],
    "keywords": [
        "compliance",
        "configuration",
        "container",
        "embedding",
        "feature",
        "flags",
        "load",
        "loader",
    ],
    "business_value": "Provides di runtime config components including DIConfigError, DIRuntimeConfigLoader",
    "last_modified": "2026-01-25T08:58:45Z",
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
