"""
Domain Bridge — Canonical Ingress Layer (ADR-0092).

This package contains the single ingress gateway for all state-mutating
operations in L9.  External actors interact with the DomainGuardAdapter
(future); the adapter forwards validated PacketEnvelopes to the
DomainBridgeGateway, which enforces governance and dispatches to handlers.
"""

from __future__ import annotations

# ============================================================================
__dora_meta__ = {
    "component_name": "DomainBridge",
    "module_version": "1.0.0",
    "created_by": "L-CTO Agent",
    "created_at": "2026-02-19T14:00:00Z",
    "updated_at": "2026-02-19T14:00:00Z",
    "layer": "operations",
    "domain": "domain_bridge",
    "module_name": "__init__",
    "type": "package",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": [],
        "memory_layers": [],
        "imported_by": ["api.server"],
    },
}
# ============================================================================

from .gateway import DomainBridgeGateway

__all__ = [
    "DomainBridgeGateway",
]
