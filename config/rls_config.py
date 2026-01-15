"""
L9 RLS (Row-Level Security) Configuration
==========================================

Deterministic UUID generation for multi-tenant isolation.
Uses uuid5 with DNS namespace to generate consistent UUIDs from string identifiers.

GMP-80: RLS Full Instantiation

Design:
- L and C share the SAME tenant_id/org_id (preserving collaboration)
- UUIDs are deterministic (same input = same UUID across restarts)
- Environment variables can override defaults for different deployments
"""

from __future__ import annotations

import uuid
from functools import lru_cache

import structlog
from pydantic_settings import BaseSettings

logger = structlog.get_logger(__name__)

# Namespace for deterministic UUID generation (DNS namespace is standard)
RLS_UUID_NAMESPACE = uuid.NAMESPACE_DNS


def generate_deterministic_uuid(identifier: str) -> str:
    """
    Generate a deterministic UUID from a string identifier.

    Uses uuid5 with DNS namespace to ensure:
    - Same identifier always produces same UUID
    - UUIDs are valid PostgreSQL UUIDs
    - Reproducible across restarts and deployments

    Args:
        identifier: String identifier (e.g., "l9", "quantumai", "l9-shared")

    Returns:
        UUID string (e.g., "550e8400-e29b-41d4-a716-446655440000")
    """
    return str(uuid.uuid5(RLS_UUID_NAMESPACE, identifier))


class RLSConfig(BaseSettings):
    """
    RLS Configuration with deterministic UUID generation.

    Environment variables (all optional, defaults provided):
    - RLS_TENANT_ID: Tenant identifier (default: "l9")
    - RLS_ORG_ID: Organization identifier (default: "quantumai")
    - RLS_USER_ID: Shared user identifier (default: "l9-shared")

    The identifiers are converted to UUIDs using uuid5 for PostgreSQL compatibility.
    """

    # String identifiers (for human readability in .env)
    rls_tenant_id: str = "l9"
    rls_org_id: str = "quantumai"
    rls_user_id: str = "l9-shared"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"

    @property
    def tenant_uuid(self) -> str:
        """Get tenant UUID from identifier."""
        return generate_deterministic_uuid(self.rls_tenant_id)

    @property
    def org_uuid(self) -> str:
        """Get organization UUID from identifier."""
        return generate_deterministic_uuid(self.rls_org_id)

    @property
    def user_uuid(self) -> str:
        """Get user UUID from identifier."""
        return generate_deterministic_uuid(self.rls_user_id)


@lru_cache(maxsize=1)
def get_rls_config() -> RLSConfig:
    """Get or create RLS config singleton. CACHED."""
    config = RLSConfig()
    logger.info(
        "RLS config loaded",
        tenant_id=config.rls_tenant_id,
        tenant_uuid=config.tenant_uuid,
        org_id=config.rls_org_id,
        org_uuid=config.org_uuid,
        user_id=config.rls_user_id,
        user_uuid=config.user_uuid,
    )
    return config


def get_rls_uuids() -> tuple[str, str, str]:
    """
    Get RLS UUIDs for PostgreSQL RLS session variables.

    Returns:
        Tuple of (tenant_uuid, org_uuid, user_uuid)
    """
    config = get_rls_config()
    return config.tenant_uuid, config.org_uuid, config.user_uuid


# Pre-computed UUIDs for common identifiers (for reference/testing)
# These are deterministic and will always be the same:
#   uuid5(NAMESPACE_DNS, "l9") = "a1b2c3d4-..."  (actual value depends on namespace)
#   uuid5(NAMESPACE_DNS, "quantumai") = "e5f6g7h8-..."
#   uuid5(NAMESPACE_DNS, "l9-shared") = "i9j0k1l2-..."
