"""
Memory Tools Re-export Shim.

This module provides a stable import path for memory-related tools.
The actual implementations live in runtime.l_tools, but this shim
allows imports from memory.tools for API consistency.

Usage:
    from memory.tools import memory_search, memory_write

Version: 1.0.0
"""

from __future__ import annotations

# ============================================================================
__dora_meta__ = {
    "component_name": "Memory Tools Re-export Shim",
    "module_version": "1.0.0",
    "created_by": "L9 System",
    "created_at": "2026-02-12T00:00:00Z",
    "updated_at": "2026-02-12T00:00:00Z",
    "layer": "memory",
    "domain": "memory_tools",
    "module_name": "tools",
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

# Re-export memory tools from runtime.l_tools
from runtime.l_tools import (
    memory_get_packet,
    memory_health_check,
    memory_search,
    memory_search_by_thread,
    memory_search_by_type,
    memory_write,
    memory_write_insight,
)

__all__ = [
    "memory_get_packet",
    "memory_health_check",
    "memory_search",
    "memory_search_by_thread",
    "memory_search_by_type",
    "memory_write",
    "memory_write_insight",
]
