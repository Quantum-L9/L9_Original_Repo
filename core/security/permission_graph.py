"""
L9 Core Security - Permission Graph (RBAC)
============================================

Role-Based Access Control implemented as a Neo4j graph.

Graph structure:
    (User)-[:HAS]->(Role)-[:CAN]->(Permission)-[:ON]->(Resource)

Enables queries like:
- "Who can access X?"
- "What can user Y do?"
- "Show all admins"

Version: 1.0.0
"""

from __future__ import annotations

# ============================================================================
__dora_meta__ = {
    "component_name": "Permission Graph (RBAC)",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2025-12-21T00:00:34Z",
    "updated_at": "2026-01-07T13:35:57Z",
    "layer": "foundation",
    "domain": "core",
    "module_name": "permission_graph",
    "type": "service",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": ["Neo4j"],
        "memory_layers": [],
        "imported_by": ["api.server", "tests.core.security.test_permission_graph"],
    },
}
# ============================================================================

from datetime import datetime, timezone
from typing import Any

import structlog

logger = structlog.get_logger(__name__)


class PermissionGraph:
    """
    RBAC permission graph backed by Neo4j.

    Provides methods to manage users, roles, permissions, and resources.
    """

    @staticmethod
    async def _get_neo4j():
        """Get Neo4j client or None."""
        try:
            from memory.graph_client import get_neo4j_client

            return await get_neo4j_client()
        except ImportError:
            return None

    # =========================================================================
    # User Management
    # =========================================================================

    @staticmethod
    async def create_user(
        user_id: str, properties: dict[str, Any] | None = None
    ) -> bool:
        """Create a user node."""
        neo4j = await PermissionGraph._get_neo4j()
        if not neo4j:
            return False

        props = properties or {}
        props["created_at"] = datetime.now(timezone.utc).isoformat()

        result = await neo4j.create_entity("User", user_id, props)
        return result is not None

    @staticmethod
    async def get_user(user_id: str) -> dict[str, Any] | None:
        """Get user by ID."""
        neo4j = await PermissionGraph._get_neo4j()
        if not neo4j:
            return None

        return await neo4j.get_entity("User", user_id)

    # =========================================================================
    # Role Management
    # =========================================================================

    @staticmethod
    async def create_role(
        role_id: str,
        description: str | None = None,
        permissions: list[str] | None = None,
    ) -> bool:
        """
        Create a role with optional permissions.

        Args:
            role_id: Role identifier (e.g., "admin", "developer", "viewer")
            description: Human-readable description
            permissions: List of permission IDs to grant to this role
        """
        neo4j = await PermissionGraph._get_neo4j()
        if not neo4j:
            return False

        result = await neo4j.create_entity(
            "Role",
            role_id,
            {
                "name": role_id,
                "description": description or "",
                "created_at": datetime.now(timezone.utc).isoformat(),
            },
        )

        if result and permissions:
            for perm in permissions:
                await PermissionGraph.grant_permission_to_role(role_id, perm)

        return result is not None

    @staticmethod
    async def grant_permission_to_role(role_id: str, permission_id: str) -> bool:
        """Grant a permission to a role."""
        neo4j = await PermissionGraph._get_neo4j()
        if not neo4j:
            return False

        # Ensure permission exists
        await neo4j.create_entity("Permission", permission_id, {"name": permission_id})

        return await neo4j.create_relationship(
            "Role",
            role_id,
            "Permission",
            permission_id,
            "CAN",
        )

    # =========================================================================
    # User-Role Assignment
    # =========================================================================

    @staticmethod
    async def grant_role(user_id: str, role_id: str) -> bool:
        """Assign a role to a user."""
        neo4j = await PermissionGraph._get_neo4j()
        if not neo4j:
            return False

        # Ensure both exist
        await neo4j.create_entity("User", user_id, {"id": user_id})
        await neo4j.create_entity("Role", role_id, {"name": role_id})

        result = await neo4j.create_relationship(
            "User",
            user_id,
            "Role",
            role_id,
            "HAS",
            {"granted_at": datetime.now(timezone.utc).isoformat()},
        )

        if result:
            logger.info(f"Granted role '{role_id}' to user '{user_id}'")

        return result

    @staticmethod
    async def revoke_role(user_id: str, role_id: str) -> bool:
        """Revoke a role from a user."""
        neo4j = await PermissionGraph._get_neo4j()
        if not neo4j:
            return False

        try:
            await neo4j.run_query(
                """
                MATCH (u:User {id: $user_id})-[r:HAS]->(role:Role {id: $role_id})
                DELETE r
            """,
                {"user_id": user_id, "role_id": role_id},
            )

            logger.info(f"Revoked role '{role_id}' from user '{user_id}'")
            return True
        except Exception as e:
            logger.warning(f"Failed to revoke role: {e}")
            return False

    @staticmethod
    async def get_user_roles(user_id: str) -> list[str]:
        """Get all roles for a user."""
        neo4j = await PermissionGraph._get_neo4j()
        if not neo4j:
            return []

        try:
            result = await neo4j.run_query(
                """
                MATCH (u:User {id: $user_id})-[:HAS]->(r:Role)
                RETURN r.id as role_id
            """,
                {"user_id": user_id},
            )

            return [r["role_id"] for r in result] if result else []
        except Exception:
            return []

    # =========================================================================
    # Resource Management
    # =========================================================================

    @staticmethod
    async def create_resource(
        resource_id: str,
        resource_type: str,
        properties: dict[str, Any] | None = None,
    ) -> bool:
        """Create a protected resource."""
        neo4j = await PermissionGraph._get_neo4j()
        if not neo4j:
            return False

        props = properties or {}
        props["resource_type"] = resource_type
        props["created_at"] = datetime.now(timezone.utc).isoformat()

        result = await neo4j.create_entity("Resource", resource_id, props)
        return result is not None

    @staticmethod
    async def link_permission_to_resource(permission_id: str, resource_id: str) -> bool:
        """Link a permission to a resource (permission grants access to resource)."""
        neo4j = await PermissionGraph._get_neo4j()
        if not neo4j:
            return False

        return await neo4j.create_relationship(
            "Permission",
            permission_id,
            "Resource",
            resource_id,
            "ON",
        )

    # =========================================================================
    # Access Control Checks
    # =========================================================================

    @staticmethod
    async def can_access(user_id: str, resource_id: str) -> bool:
        """
        Check if user can access a resource.

        Traverses: User -> HAS -> Role -> CAN -> Permission -> ON -> Resource
        """
        neo4j = await PermissionGraph._get_neo4j()
        if not neo4j:
            return False

        try:
            result = await neo4j.run_query(
                """
                MATCH (u:User {id: $user_id})-[:HAS]->(:Role)-[:CAN]->(:Permission)-[:ON]->(r:Resource {id: $resource_id})
                RETURN count(r) > 0 as allowed
            """,
                {"user_id": user_id, "resource_id": resource_id},
            )

            return result[0]["allowed"] if result else False
        except Exception:
            return False

    @staticmethod
    async def has_permission(user_id: str, permission_id: str) -> bool:
        """
        Check if user has a specific permission.

        Traverses: User -> HAS -> Role -> CAN -> Permission
        """
        neo4j = await PermissionGraph._get_neo4j()
        if not neo4j:
            return False

        try:
            result = await neo4j.run_query(
                """
                MATCH (u:User {id: $user_id})-[:HAS]->(:Role)-[:CAN]->(p:Permission {id: $permission_id})
                RETURN count(p) > 0 as has_permission
            """,
                {"user_id": user_id, "permission_id": permission_id},
            )

            return result[0]["has_permission"] if result else False
        except Exception:
            return False

    @staticmethod
    async def get_user_permissions(user_id: str) -> list[str]:
        """Get all permissions for a user (through their roles)."""
        neo4j = await PermissionGraph._get_neo4j()
        if not neo4j:
            return []

        try:
            result = await neo4j.run_query(
                """
                MATCH (u:User {id: $user_id})-[:HAS]->(:Role)-[:CAN]->(p:Permission)
                RETURN DISTINCT p.id as permission_id
            """,
                {"user_id": user_id},
            )

            return [r["permission_id"] for r in result] if result else []
        except Exception:
            return []

    @staticmethod
    async def get_users_with_role(role_id: str) -> list[str]:
        """Get all users with a specific role."""
        neo4j = await PermissionGraph._get_neo4j()
        if not neo4j:
            return []

        try:
            result = await neo4j.run_query(
                """
                MATCH (u:User)-[:HAS]->(r:Role {id: $role_id})
                RETURN u.id as user_id
            """,
                {"role_id": role_id},
            )

            return [r["user_id"] for r in result] if result else []
        except Exception:
            return []


# =============================================================================
# Convenience Functions (module-level)
# =============================================================================


async def grant_role(user_id: str, role_id: str) -> bool:
    """Assign a role to a user."""
    return await PermissionGraph.grant_role(user_id, role_id)


async def revoke_role(user_id: str, role_id: str) -> bool:
    """Revoke a role from a user."""
    return await PermissionGraph.revoke_role(user_id, role_id)


async def grant_permission(role_id: str, permission_id: str) -> bool:
    """Grant a permission to a role."""
    return await PermissionGraph.grant_permission_to_role(role_id, permission_id)


async def can_access(user_id: str, resource_id: str) -> bool:
    """Check if user can access a resource."""
    return await PermissionGraph.can_access(user_id, resource_id)


async def get_user_permissions(user_id: str) -> list[str]:
    """Get all permissions for a user."""
    return await PermissionGraph.get_user_permissions(user_id)


__all__ = [
    "PermissionGraph",
    "can_access",
    "get_user_permissions",
    "grant_permission",
    "grant_role",
    "revoke_role",
]

# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "COR-FOUN-025",
    "governance_level": "critical",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": ["memory.graph_client"],
    "tags": ["async", "authorization", "core", "foundation", "logging", "service"],
    "keywords": [
        "(rbac)",
        "access",
        "can",
        "create",
        "grant",
        "graph",
        "link",
        "permission",
    ],
    "business_value": "Implements PermissionGraph for permission graph functionality",
    "last_modified": "2026-01-07T13:35:57Z",
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
