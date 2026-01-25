"""
Environment Variable Secrets Client
====================================

Simple secrets client that reads from environment variables.
Used as the default/fallback provider for local development.

Version: 1.0.0
GMP: GMP-122 AWS Secrets Manager Integration
"""

from __future__ import annotations

import os

import structlog

logger = structlog.get_logger(__name__)


# =============================================================================
# DORA Metadata
# =============================================================================
__dora_meta__ = {
    "component_name": "Environment Secrets Client",
    "module_version": "1.0.0",
    "created_by": "GMP-122",
    "created_at": "2026-01-25T00:00:00Z",
    "updated_at": "2026-01-25T00:00:00Z",
    "layer": "infrastructure",
    "domain": "secrets",
    "module_name": "env_secrets_client",
    "type": "implementation",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": ["Environment Variables"],
        "memory_layers": [],
        "imported_by": ["core.secrets"],
    },
}


# =============================================================================
# Environment Secrets Client
# =============================================================================


class EnvSecretsClient:
    """
    Secrets client that reads from environment variables.

    Simple fallback implementation for local development and testing.
    Does not support set/delete/rotate operations (env vars are read-only at runtime).
    """

    def __init__(self, prefix: str = "") -> None:
        """
        Initialize environment secrets client.

        Args:
            prefix: Optional prefix to prepend to key names (e.g., "L9_")
        """
        self._prefix = prefix
        logger.info(
            "env_secrets_client_initialized",
            prefix=prefix or "(none)",
        )

    @property
    def provider_name(self) -> str:
        """Return provider name for audit/logging."""
        return "env"

    def _build_env_key(self, key: str) -> str:
        """Build environment variable name with optional prefix."""
        return f"{self._prefix}{key}" if self._prefix else key

    def get_secret(self, key: str) -> str | None:
        """
        Get secret value from environment variable.

        Args:
            key: Secret key name

        Returns:
            Secret value or None if not set
        """
        env_key = self._build_env_key(key)
        value = os.getenv(env_key)

        if value:
            logger.debug("secret_retrieved_from_env", key=key, env_key=env_key)
        else:
            logger.debug("secret_not_found_in_env", key=key, env_key=env_key)

        return value

    def set_secret(self, key: str, value: str) -> bool:
        """
        Set secret (not supported for env vars at runtime).

        Args:
            key: Secret key name
            value: Secret value

        Returns:
            False (operation not supported)
        """
        logger.warning(
            "set_secret_not_supported",
            provider="env",
            key=key,
            reason="Environment variables are read-only at runtime",
        )
        return False

    def delete_secret(self, key: str) -> bool:
        """
        Delete secret (not supported for env vars at runtime).

        Args:
            key: Secret key name

        Returns:
            False (operation not supported)
        """
        logger.warning(
            "delete_secret_not_supported",
            provider="env",
            key=key,
            reason="Environment variables are read-only at runtime",
        )
        return False

    # -------------------------------------------------------------------------
    # Async wrappers (for protocol compatibility)
    # -------------------------------------------------------------------------

    async def get_secret_async(self, key: str) -> str | None:
        """Async wrapper for get_secret."""
        return self.get_secret(key)

    async def set_secret_async(self, key: str, value: str) -> bool:
        """Async wrapper for set_secret."""
        return self.set_secret(key, value)

    async def delete_secret_async(self, key: str) -> bool:
        """Async wrapper for delete_secret."""
        return self.delete_secret(key)

    async def rotate_secret(self, key: str) -> bool:
        """Rotation not supported for env vars."""
        logger.warning(
            "rotate_secret_not_supported",
            provider="env",
            key=key,
        )
        return False
