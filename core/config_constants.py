"""Centralized configuration constants for L9 Secure AI OS.

Single source of truth for configuration defaults, whitelists, and enums.
All modules MUST import from here instead of hardcoding values.

Created as part of Bug Knowledge Package (BUG-001 through BUG-004 post-mortem).
See ADR-0098 for rationale and enforcement.

Usage:
    from core.config_constants import DEFAULT_PROJECT_ID, DEFAULT_CALLER_SCOPE
    from core.config_constants import ALLOWED_SCOPES_L, ALLOWED_SCOPES_CURSOR
"""

from __future__ import annotations

import os
from typing import Literal

# ============================================================================
__dora_meta__ = {
    "component_name": "Config Constants",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2026-02-13T00:00:00Z",
    "updated_at": "2026-02-13T00:00:00Z",
    "layer": "core",
    "domain": "configuration",
    "module_name": "config_constants",
    "type": "constants",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": [],
        "memory_layers": [],
        "imported_by": [
            "mcp_memory.src.main",
            "mcp_memory.src.mcp_server",
            "mcp_memory.src.routes.memory_unified",
        ],
    },
}
# ============================================================================


# =============================================================================
# Project Defaults
# =============================================================================


def get_default_project_id() -> str:
    """Get the default project ID from environment or fallback.

    On C1: L9_PROJECT_ID=l9-c1
    Locally: defaults to l9-default
    """
    return os.getenv("L9_PROJECT_ID", "l9-default")


DEFAULT_PROJECT_ID_FALLBACK: str = "l9-default"
"""Hardcoded fallback when env var is not set. Use get_default_project_id() in runtime code."""


# =============================================================================
# Caller Scopes (Governance)
# =============================================================================

CallerScope = Literal["developer", "global", "agent", "cursor", "l-private"]
"""All valid caller scope values in the L9 system."""

DEFAULT_CALLER_SCOPE: CallerScope = "cursor"
"""Default scope for Cursor callers (ADR-0005 RLS design)."""

DEFAULT_MEMORY_SCOPE: str = "developer"
"""Default memory scope from L9_MEMORY_SCOPE env var fallback."""

DEFAULT_SEARCH_SCOPES: list[str] = ["developer", "global"]
"""Default scopes for search operations when no scopes are explicitly requested."""


# =============================================================================
# Allowed Scopes Per Caller Identity
# =============================================================================

ALLOWED_SCOPES_L: list[str] = ["developer", "global", "l-private", "cursor"]
"""Scopes accessible to L-CTO agent (includes l-private)."""

ALLOWED_SCOPES_CURSOR: list[str] = ["cursor", "developer", "global"]
"""Scopes accessible to Cursor agent (excludes l-private)."""


# =============================================================================
# Memory Scopes (RLS)
# =============================================================================

MemoryScope = Literal["shared", "private", "developer", "global", "agent", "cursor"]
"""All valid memory scope values for RLS policy enforcement."""

RLS_VISIBLE_SCOPES: frozenset[str] = frozenset(
    ["shared", "developer", "global", "agent", "cursor"]
)
"""Scopes visible through RLS policies (excludes private, l-private)."""

MCP_WRITE_SCOPES: list[str] = ["developer", "l-private", "global", "cursor"]
"""Valid scope values for MCP save_memory tool schema (JSON schema enum)."""

MCP_SEARCH_SCOPES: list[str] = ["developer", "l-private", "global", "cursor"]
"""Valid scope values for MCP search_memory tool schema (JSON schema enum)."""


# =============================================================================
# Helper Functions
# =============================================================================


def get_allowed_scopes_for_caller(caller_id: str) -> list[str]:
    """Return the allowed scopes for a given caller identity.

    Args:
        caller_id: The caller identifier ("L" for L-CTO, "C" for Cursor, etc.)

    Returns:
        List of allowed scope strings for the caller.
    """
    if caller_id == "L":
        return ALLOWED_SCOPES_L.copy()
    return ALLOWED_SCOPES_CURSOR.copy()


def get_default_scope_for_caller(caller_id: str) -> str:
    """Return the default scope for a given caller identity.

    Args:
        caller_id: The caller identifier ("L" for L-CTO, "C" for Cursor, etc.)

    Returns:
        Default scope string for the caller.
    """
    if caller_id == "L":
        return os.getenv("L9_MEMORY_SCOPE", DEFAULT_MEMORY_SCOPE)
    return DEFAULT_CALLER_SCOPE


# =============================================================================
__dora_footer__ = {
    "governance_level": "high",
    "compliance_required": True,
}
# =============================================================================
