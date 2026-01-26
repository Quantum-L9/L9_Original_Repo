"""
L9 PacketEnvelope Infrastructure Package
=========================================

Core infrastructure capabilities for PacketEnvelope:

- Observability (OpenTelemetry, Jaeger, Prometheus)
- Standardization (CloudEvents v1.0)
- Scalability (Batch ingestion, CQRS, Event Sourcing)
- Governance (TTL enforcement, GDPR, Compliance)

Usage:
    from core.packet_envelope import PacketEnvelopeUpgradeEngine

    engine = PacketEnvelopeUpgradeEngine()
    await engine.activate_all_phases()
"""

from core.packet_envelope.integration import (
    PacketEnvelopeAdapter,
    PacketEnvelopeUpgradeEngine,
    PacketEnvelopeUpgradePhase,
    UpgradeState,
    validate_deployment,
)

__all__ = [
    "PacketEnvelopeAdapter",
    "PacketEnvelopeUpgradeEngine",
    "PacketEnvelopeUpgradePhase",
    "UpgradeState",
    "validate_deployment",
]
