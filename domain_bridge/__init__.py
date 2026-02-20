"""
Domain Bridge — Canonical Ingress Layer (ADR-0092).

This package is the single ingress for state-mutating writes. External
actors reach DomainBridgeGateway; archived MemoryBridge adapters stay in
_archived/ and are not re-exported.
"""

from __future__ import annotations

# ============================================================================
__dora_meta__ = {
    "component_name": "DomainBridge",
    "module_version": "1.0.0",
    "created_by": "L-CTO Agent",
    "created_at": "2026-02-19T14:00:00Z",
    "updated_at": "2026-08-30T00:00:00Z",
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

from .agent_controller import AgentController, process_packet
from .decision_synthesizer import DecisionSynthesizer
from .gateway import DomainBridgeGateway
from .governance_bridge import GovernanceBridge
from .packet_router import PacketRouter
from .reasoning_engine import ReasoningEngine

__version__ = "6.0.0"

__all__ = [
    "AgentController",
    "DecisionSynthesizer",
    "DomainBridgeGateway",
    "GovernanceBridge",
    "PacketRouter",
    "ReasoningEngine",
    "__version__",
    "process_packet",
]
