"""L9 Kernel - Core Orchestration & Packet Protocol.

Bounded Context: Kernel
Domain: Central orchestration, packet envelope protocol, routing.
Owner: L (CTO)

Kernel is responsible for:
  1. PacketEnvelope protocol (immutable, validated packets)
  2. Request routing to substrates
  3. Response aggregation
  4. Cross-cutting concerns (correlation IDs, tracing)

Kernel MUST NOT directly depend on:
  - Individual substrates beyond abstract interfaces
  - Business logic (that's in bounded contexts)
  - Configuration (use control_plane.config)

Kernel defines the contract that all substrates must implement.
"""

from kernel.orchestrator import Orchestrator, OrchestratorConfig
from kernel.protocol import PacketEnvelope, PacketEnvelopeV2

__all__ = [
    "Orchestrator",
    "OrchestratorConfig",
    "PacketEnvelope",
    "PacketEnvelopeV2",
]
