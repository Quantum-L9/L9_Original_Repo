"""
L9 Secrets Protocols - Core Abstractions
=========================================

Frontier-grade protocol definitions for secrets management following Dependency Inversion Principle.

**Top Frontier AI Lab Quality** - Production-ready abstractions for secrets operations.

Features:
- ✅ Protocol-based abstractions for secrets management
- ✅ Type-safe interfaces with comprehensive type hints
- ✅ Enables dependency injection and testing
- ✅ Supports multiple secrets backends (Vault, AWS Secrets Manager, Environment)
- ✅ Hot-swappable implementations

Protocols:
- SecretsClient: Secrets retrieval and management operations

Version: 1.0.0
GMP: security-remediation-phase1
Author: Top Frontier AI Lab
ADR: readme/adr/0038-secrets-management-protocol.md
"""

from __future__ import annotations

# ============================================================================
__dora_meta__ = {
    "component_name": "Secrets Protocols",
    "module_version": "1.0.0",
    "created_by": "L9 Security Remediation",
    "created_at": "2026-01-20T18:00:00Z",
    "updated_at": "2026-01-20T18:00:00Z",
    "layer": "foundation",
    "domain": "abstractions",
    "module_name": "secrets_protocols",
    "type": "protocol",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": ["HashiCorp Vault", "AWS Secrets Manager", "Environment Variables"],
        "memory_layers": [],
        "imported_by": [
            "memory.graph_client",
            "memory.redis_client",
            "core.di.container",
            "tests.unit.test_secrets_protocols",
        ],
    },
}
# ============================================================================

from typing import Optional, Protocol, runtime_checkable

import structlog

logger = structlog.get_logger(__name__)


@runtime_checkable
class SecretsClient(Protocol):
    """
    Protocol for secrets management operations.

    Implementations must provide secure secrets retrieval from various backends
    with caching and rotation support.

    Example implementations:
    - VaultSecretsClient: HashiCorp Vault integration
    - AWSSecretsClient: AWS Secrets Manager integration
    - EnvSecretsClient: Environment variable fallback for local development
    """

    async def get_secret(self, key: str) -> Optional[str]:
        """
        Get secret value by key.

        Args:
            key: Secret key (e.g., "NEO4J_PASSWORD")

        Returns:
            Secret value as string or None if not found

        Raises:
            SecretsError: If secrets backend is unavailable
        """
        ...

    async def set_secret(self, key: str, value: str) -> bool:
        """
        Set secret value (if supported by backend).

        Args:
            key: Secret key
            value: Secret value

        Returns:
            True if successful

        Raises:
            SecretsError: If operation fails or is not supported
        """
        ...

    async def delete_secret(self, key: str) -> bool:
        """
        Delete secret (if supported by backend).

        Args:
            key: Secret key

        Returns:
            True if successful

        Raises:
            SecretsError: If operation fails or is not supported
        """
        ...

    async def rotate_secret(self, key: str) -> bool:
        """
        Trigger secret rotation (if supported by backend).

        Args:
            key: Secret key

        Returns:
            True if rotation initiated successfully

        Raises:
            SecretsError: If operation fails or is not supported
        """
        ...


class SecretsError(Exception):
    """Base exception for secrets operations."""

    pass
