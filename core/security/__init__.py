"""
L9 Core Security Module
========================

Provides security primitives including:
- Permission Graph (RBAC via Neo4j)
- Access control utilities

Version: 1.0.0
"""

from .path_safety import (
    PathSafetyError,
    resolve_base_dir,
    safe_resolve_path,
    safe_resolve_path_async,
    validate_filename,
)
from .permission_graph import (
    PermissionGraph,
    can_access,
    get_user_permissions,
    grant_permission,
    grant_role,
    revoke_role,
)

__all__ = [
    "PathSafetyError",
    "PermissionGraph",
    "can_access",
    "get_user_permissions",
    "grant_permission",
    "grant_role",
    "resolve_base_dir",
    "revoke_role",
    "safe_resolve_path",
    "safe_resolve_path_async",
    "validate_filename",
]
