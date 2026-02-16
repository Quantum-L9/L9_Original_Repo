"""
L9 Custom Exceptions Package.

Provides domain-specific exception classes for better error classification,
monitoring, and handling across the L9 system.

GMP-115: Enterprise-grade exception hierarchy for security, governance,
and operational error handling.
"""

from __future__ import annotations

# ============================================================================
__dora_meta__ = {
    "component_name": "Exceptions Package",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2026-02-16T18:00:00Z",
    "updated_at": "2026-02-16T18:00:00Z",
    "layer": "foundation",
    "domain": "core",
    "module_name": "exceptions",
    "type": "package",
    "status": "active",
}
# ============================================================================

from core.exceptions.security import (
    InvalidOperationError,
    InvalidSortColumnError,
    InvalidTableError,
    SQLSecurityError,
)

__all__ = [
    "InvalidOperationError",
    "InvalidSortColumnError",
    "InvalidTableError",
    "SQLSecurityError",
]

# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "CORE-FOUND-EXC",
    "governance_level": "low",
    "compliance_required": False,
    "audit_trail": False,
    "dependencies": [],
    "tags": ["core", "exceptions", "foundation"],
    "keywords": ["exception", "error", "security"],
    "last_modified": "2026-02-16T18:00:00Z",
}
# ============================================================================
