"""
L9 Secrets Client Factory
=========================

Provides factory function for creating SecretsClient implementations
based on configuration, supporting env-based and AWS Secrets Manager backends.

Configuration via environment variables:
- L9_SECRETS_PROVIDER: "env" | "aws" (default: "env")
- AWS_REGION: AWS region (default: "us-east-1")
- AWS_SECRETS_PREFIX: Secret name prefix (default: "l9")
- AWS_SECRETS_CACHE_TTL: Cache TTL in seconds (default: 3600)
- AWS_SECRETS_FALLBACK_TO_ENV: Fallback to env vars (default: "true" in non-prod)

Version: 1.0.0
GMP: GMP-122 AWS Secrets Manager Integration
"""

from __future__ import annotations

import os
from typing import Optional, Union

import structlog

# Import directly to avoid circular imports
from core.protocols.secrets_protocols import SecretsError
from core.secrets.aws_secrets_client import AwsSecretsClient
from core.secrets.env_secrets_client import EnvSecretsClient

logger = structlog.get_logger(__name__)


# =============================================================================
# DORA Metadata
# =============================================================================
__dora_meta__ = {
    "component_name": "Secrets Factory",
    "module_version": "1.0.0",
    "created_by": "GMP-122",
    "created_at": "2026-01-25T00:00:00Z",
    "updated_at": "2026-01-25T00:00:00Z",
    "layer": "infrastructure",
    "domain": "secrets",
    "module_name": "secrets",
    "type": "factory",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": ["AWS Secrets Manager", "Environment Variables"],
        "memory_layers": [],
        "imported_by": ["config.settings", "api.server"],
    },
}


# =============================================================================
# Type Alias
# =============================================================================

SecretsClientType = Union[EnvSecretsClient, AwsSecretsClient]


# =============================================================================
# Global Singleton
# =============================================================================

_secrets_client: SecretsClientType | None = None


# =============================================================================
# Factory Function
# =============================================================================


def get_secrets_client() -> SecretsClientType:
    """
    Get or create the secrets client singleton.

    Configuration via environment variables:
    - L9_SECRETS_PROVIDER: "env" | "aws" (default: "env")
    - AWS_REGION: AWS region (default: "us-east-1")
    - AWS_SECRETS_PREFIX: Secret name prefix (default: "l9")
    - AWS_SECRETS_CACHE_TTL: Cache TTL in seconds (default: 3600)
    - AWS_SECRETS_FALLBACK_TO_ENV: Fallback to env vars (default: "true" in non-prod)

    Returns:
        SecretsClient instance (env-based or AWS-based)

    Raises:
        SecretsError: If initialization fails and no fallback available
    """
    global _secrets_client

    if _secrets_client is not None:
        return _secrets_client

    provider = os.getenv("L9_SECRETS_PROVIDER", "env").lower()

    if provider == "aws":
        region = os.getenv("AWS_REGION", "us-east-1")
        prefix = os.getenv("AWS_SECRETS_PREFIX", "l9")
        cache_ttl = int(os.getenv("AWS_SECRETS_CACHE_TTL", "3600"))

        # Default fallback to True in non-prod, False in prod
        is_prod = os.getenv("ENVIRONMENT", "dev").lower() == "prod"
        fallback_default = "false" if is_prod else "true"
        fallback_str = os.getenv("AWS_SECRETS_FALLBACK_TO_ENV", fallback_default)
        fallback = fallback_str.lower() in ("true", "1", "yes")

        logger.info(
            "initializing_aws_secrets_client",
            region=region,
            prefix=prefix,
            cache_ttl=cache_ttl,
            fallback_to_env=fallback,
            environment="prod" if is_prod else "non-prod",
        )

        _secrets_client = AwsSecretsClient(
            region=region,
            prefix=prefix,
            cache_ttl_seconds=cache_ttl,
            fallback_to_env=fallback,
        )
    else:
        # Default to env-based client
        prefix = os.getenv("ENV_SECRETS_PREFIX", "")
        logger.info(
            "initializing_env_secrets_client",
            prefix=prefix or "(none)",
        )
        _secrets_client = EnvSecretsClient(prefix=prefix)

    return _secrets_client


def reset_secrets_client() -> None:
    """
    Reset singleton for testing.

    Clears the cached secrets client instance, allowing
    reinitialization with different configuration.
    """
    global _secrets_client
    _secrets_client = None
    logger.debug("secrets_client_reset")


# =============================================================================
# Convenience Functions
# =============================================================================


def get_secret(key: str) -> str | None:
    """
    Convenience function to get a secret value.

    Args:
        key: Secret key name

    Returns:
        Secret value or None if not found
    """
    return get_secrets_client().get_secret(key)


def get_secret_or_env(key: str, default: str | None = None) -> str | None:
    """
    Get secret from configured provider, with explicit env fallback.

    Useful for migration: tries secrets provider first, then env var.

    Args:
        key: Secret key name
        default: Default value if not found anywhere

    Returns:
        Secret value from provider, env var, or default
    """
    value = get_secrets_client().get_secret(key)
    if value is not None:
        return value

    # Explicit env fallback
    env_value = os.getenv(key)
    if env_value is not None:
        return env_value

    return default


# =============================================================================
# Exports
# =============================================================================

__all__ = [
    # Factory
    "get_secrets_client",
    "reset_secrets_client",
    # Convenience
    "get_secret",
    "get_secret_or_env",
    # Implementations
    "EnvSecretsClient",
    "AwsSecretsClient",
    # Types
    "SecretsClientType",
    # Errors
    "SecretsError",
]
