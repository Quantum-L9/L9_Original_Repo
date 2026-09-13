"""
Domain Bridge — Canonical Ingress Layer (ADR-0092).

This package is the single ingress for state-mutating writes. External
actors reach DomainBridgeGateway; archived MemoryBridge adapters stay in
_archived/ and are not re-exported.
"""

from __future__ import annotations


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
