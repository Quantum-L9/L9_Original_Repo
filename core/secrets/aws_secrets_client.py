"""
AWS Secrets Manager Client
==========================

Production-grade AWS Secrets Manager client with caching and env fallback.
Implements SecretsClient protocol for L9 secrets management.

Features:
- Boto3-based AWS Secrets Manager integration
- In-memory caching with configurable TTL (default 3600s / 1 hour)
- Graceful fallback to env vars in non-production
- Clear error mapping to SecretsError
- Support for secret naming convention: l9/<key>
- Structured logging (key names only, never values)

Version: 1.0.0
GMP: GMP-122 AWS Secrets Manager Integration
"""

from __future__ import annotations

import os
from datetime import datetime, timedelta
from typing import Any

import structlog

from core.protocols.secrets_protocols import SecretsError

logger = structlog.get_logger(__name__)


# =============================================================================
# DORA Metadata
# =============================================================================
__dora_meta__ = {
    "component_name": "AWS Secrets Manager Client",
    "module_version": "1.0.0",
    "created_by": "GMP-122",
    "created_at": "2026-01-25T00:00:00Z",
    "updated_at": "2026-01-25T00:00:00Z",
    "layer": "infrastructure",
    "domain": "secrets",
    "module_name": "aws_secrets_client",
    "type": "implementation",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": ["AWS Secrets Manager", "Environment Variables"],
        "memory_layers": [],
        "imported_by": ["core.secrets"],
    },
}


# =============================================================================
# AWS Secrets Manager Client
# =============================================================================


class AwsSecretsClient:
    """
    AWS Secrets Manager client with caching and env fallback.

    Provides production-grade secret retrieval from AWS with in-memory caching,
    graceful fallback to env vars, and integration with L9 governance.
    """

    def __init__(
        self,
        region: str = "us-east-1",
        prefix: str = "l9",
        cache_ttl_seconds: int = 3600,
        fallback_to_env: bool = False,
    ) -> None:
        """
        Initialize AWS Secrets Manager client.

        Args:
            region: AWS region (default: us-east-1)
            prefix: Secret name prefix convention (default: l9)
            cache_ttl_seconds: Cache TTL in seconds (default: 3600)
            fallback_to_env: Fall back to env vars if secret not in AWS (default: False)
        """
        self._region = region
        self._prefix = prefix
        self._cache_ttl_seconds = cache_ttl_seconds
        self._fallback_to_env = fallback_to_env
        self._cache: dict[str, tuple[str, datetime]] = {}
        self._client: Any = None
        self._available = False
        self._boto3: Any = None
        self._BotoCoreError: Any = Exception
        self._NoCredentialsError: Any = Exception

        try:
            import boto3
            from botocore.exceptions import BotoCoreError, NoCredentialsError

            self._boto3 = boto3
            self._BotoCoreError = BotoCoreError
            self._NoCredentialsError = NoCredentialsError

            self._client = boto3.client("secretsmanager", region_name=region)
            self._available = True
            logger.info(
                "aws_secrets_client_initialized",
                region=region,
                prefix=prefix,
                cache_ttl=cache_ttl_seconds,
                fallback_to_env=fallback_to_env,
            )
        except ImportError:
            logger.warning("boto3_not_installed", fallback_to_env=fallback_to_env)
            if not fallback_to_env:
                raise SecretsError(
                    "boto3 not installed and fallback to env disabled"
                ) from None
        except Exception as e:
            logger.warning(
                "aws_secrets_client_init_failed",
                error=str(e),
                fallback_to_env=fallback_to_env,
            )
            if not fallback_to_env:
                raise SecretsError(
                    f"AWS Secrets Manager unavailable and fallback disabled: {e}"
                ) from e

    @property
    def provider_name(self) -> str:
        """Return provider name for audit/logging."""
        return "aws"

    def _build_secret_name(self, key: str) -> str:
        """Build full secret name with prefix."""
        return f"{self._prefix}/{key}" if self._prefix else key

    def _is_cache_valid(self, cached_at: datetime) -> bool:
        """Check if cached secret is still valid."""
        ttl = timedelta(seconds=self._cache_ttl_seconds)
        return datetime.utcnow() - cached_at < ttl

    def get_secret(self, key: str) -> str | None:
        """
        Retrieve secret from AWS Secrets Manager or cache.

        Args:
            key: Secret key name (without prefix)

        Returns:
            Secret value or None if not found

        Raises:
            SecretsError: If secret retrieval fails and fallback disabled
        """
        if not self._available and not self._fallback_to_env:
            raise SecretsError("AWS Secrets Manager not available")

        # Check cache first
        if key in self._cache:
            value, cached_at = self._cache[key]
            if self._is_cache_valid(cached_at):
                logger.debug("secret_from_cache", key=key)
                return value
            # Cache expired, remove it
            del self._cache[key]

        # Try AWS if available
        if self._available and self._client:
            try:
                secret_name = self._build_secret_name(key)
                response = self._client.get_secret_value(SecretId=secret_name)

                if "SecretString" in response:
                    value = response["SecretString"]
                    # Cache the value
                    self._cache[key] = (value, datetime.utcnow())
                    logger.info(
                        "secret_retrieved_from_aws",
                        key=key,
                        secret_name=secret_name,
                    )
                    return value
                logger.warning("secret_no_string_value", key=key)
                return None

            except self._client.exceptions.ResourceNotFoundException:
                logger.info("secret_not_found_in_aws", key=key)
                if not self._fallback_to_env:
                    raise SecretsError(f"Secret not found: {key}") from None

            except (self._BotoCoreError, self._NoCredentialsError) as e:
                logger.error("aws_api_error", key=key, error=str(e))
                if not self._fallback_to_env:
                    raise SecretsError(f"Failed to retrieve secret {key}: {e}") from e

            except Exception as e:
                logger.error("unexpected_secret_error", key=key, error=str(e))
                if not self._fallback_to_env:
                    raise SecretsError(f"Unexpected error: {e}") from e

        # Fallback to env var
        if self._fallback_to_env:
            env_value = os.getenv(key)
            if env_value:
                logger.info("secret_from_env_fallback", key=key)
                # Cache the env value too
                self._cache[key] = (env_value, datetime.utcnow())
                return env_value

        logger.warning("secret_not_found", key=key)
        return None

    def set_secret(self, key: str, value: str) -> bool:
        """
        Create or update secret in AWS Secrets Manager.

        Args:
            key: Secret key name
            value: Secret value

        Returns:
            True if successful

        Raises:
            SecretsError: If operation fails
        """
        if not self._available or not self._client:
            raise SecretsError("AWS Secrets Manager not available")

        try:
            secret_name = self._build_secret_name(key)
            self._client.put_secret_value(
                SecretId=secret_name,
                SecretString=value,
            )
            # Update cache
            self._cache[key] = (value, datetime.utcnow())
            logger.info("secret_updated_in_aws", key=key)
            return True

        except Exception as e:
            logger.error("secret_set_failed", key=key, error=str(e))
            raise SecretsError(f"Failed to set secret {key}: {e}") from e

    def delete_secret(self, key: str) -> bool:
        """
        Delete secret from AWS Secrets Manager.

        Args:
            key: Secret key name

        Returns:
            True if successful, False if not found

        Raises:
            SecretsError: If operation fails
        """
        if not self._available or not self._client:
            raise SecretsError("AWS Secrets Manager not available")

        try:
            secret_name = self._build_secret_name(key)
            self._client.delete_secret(
                SecretId=secret_name,
                ForceDeleteWithoutRecovery=True,
            )
            # Invalidate cache
            if key in self._cache:
                del self._cache[key]
            logger.info("secret_deleted_from_aws", key=key)
            return True

        except self._client.exceptions.ResourceNotFoundException:
            logger.warning("secret_not_found_for_deletion", key=key)
            return False

        except Exception as e:
            logger.error("secret_delete_failed", key=key, error=str(e))
            raise SecretsError(f"Failed to delete secret {key}: {e}") from e

    def invalidate_cache(self, key: str | None = None) -> None:
        """
        Invalidate cached secrets.

        Args:
            key: Specific key to invalidate, or None to clear all
        """
        if key:
            if key in self._cache:
                del self._cache[key]
                logger.debug("cache_invalidated", key=key)
        else:
            self._cache.clear()
            logger.debug("cache_cleared")

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
        """
        Trigger secret rotation in AWS Secrets Manager.

        Args:
            key: Secret key name

        Returns:
            True if rotation initiated successfully
        """
        if not self._available or not self._client:
            raise SecretsError("AWS Secrets Manager not available")

        try:
            secret_name = self._build_secret_name(key)
            self._client.rotate_secret(SecretId=secret_name)
            # Invalidate cache since value will change
            self.invalidate_cache(key)
            logger.info("secret_rotation_initiated", key=key)
            return True

        except Exception as e:
            logger.error("secret_rotation_failed", key=key, error=str(e))
            raise SecretsError(f"Failed to rotate secret {key}: {e}") from e


# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "COR-FOUN-042",
    "governance_level": "critical",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": ["core.protocols.secrets_protocols"],
    "tags": [
        "api",
        "async",
        "caching",
        "client",
        "core",
        "debugging",
        "foundation",
        "logging",
        "security",
        "service",
    ],
    "keywords": [
        "async",
        "aws",
        "cache",
        "caching",
        "client",
        "delete",
        "fallback",
        "integration",
    ],
    "business_value": "Implements SecretsClient protocol for L9 secrets management. Boto3-based AWS Secrets Manager integration In-memory caching with configurable TTL (default 3600s / 1 hour) Graceful fallback to env vars ",
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
