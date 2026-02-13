"""
Introspection Tools Re-export Shim.

This module provides a stable import path for tool introspection functions.
The actual implementations live in runtime.l_tools, but this shim
allows imports from core.tools.introspection_tools for API consistency.

Usage:
    from core.tools.introspection_tools import tools_get_catalog

Version: 1.0.0
"""

from __future__ import annotations

# ============================================================================
__dora_meta__ = {
    "component_name": "Introspection Tools Re-export Shim",
    "module_version": "1.0.0",
    "created_by": "L9 System",
    "created_at": "2026-02-12T00:00:00Z",
    "updated_at": "2026-02-12T00:00:00Z",
    "layer": "core",
    "domain": "tools",
    "module_name": "introspection_tools",
    "type": "shim",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": [],
        "memory_layers": ["runtime.l_tools"],
        "imported_by": [],
    },
}
# ============================================================================

# Re-export introspection tools from runtime.l_tools
from runtime.l_tools import (
    tools_detect_circular_deps,
    tools_get_api_dependents,
    tools_get_blast_radius,
    tools_get_by_type,
    tools_get_catalog,
    tools_get_dependencies,
    tools_get_for_role,
    tools_get_metadata,
    tools_get_schema,
    tools_list_all,
    tools_list_enabled,
)

__all__ = [
    "tools_detect_circular_deps",
    "tools_get_api_dependents",
    "tools_get_blast_radius",
    "tools_get_by_type",
    "tools_get_catalog",
    "tools_get_dependencies",
    "tools_get_for_role",
    "tools_get_metadata",
    "tools_get_schema",
    "tools_list_all",
    "tools_list_enabled",
]
