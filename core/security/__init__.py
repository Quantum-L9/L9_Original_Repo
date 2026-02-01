"""
L9 Core Security Module
========================

Provides security primitives including:
- Permission Graph (RBAC via Neo4j)
- Access control utilities

Version: 1.0.0
"""

# ============================================================================
__dora_meta__ = {
    "component_name": "  Init  ",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2025-12-21T00:00:34Z",
    "updated_at": "2026-01-31T22:21:46Z",
    "layer": "foundation",
    "domain": "core",
    "module_name": "__init__",
    "type": "utility",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": ["Neo4j"],
        "memory_layers": [],
        "imported_by": [],
    },
}
# ============================================================================

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
# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "COR-FOUN-056",
    "governance_level": "critical",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": ["authorization", "core", "foundation", "utility"],
    "keywords": ["module", "security"],
    "business_value": "Permission Graph (RBAC via Neo4j) Access control utilities Version: 1.0.0",
    "last_modified": "2026-01-31T22:21:46Z",
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
