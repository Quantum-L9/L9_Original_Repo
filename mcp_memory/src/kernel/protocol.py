"""Kernel Protocol - PacketEnvelope and Packet Definitions.

This module defines the immutable contract for all inter-module communication.
All substrate operations must be wrapped in PacketEnvelope for tracing,
audit, and governance enforcement.

Kernel INVARIANTS (enforced by type system and tests):
  1. PacketEnvelope is immutable (frozen=True)
  2. packet_id is auto-generated, cannot be changed
  3. confidence is in [0, 1]
  4. timestamp is ISO 8601 UTC
  5. All metadata is optional but typed when present
  6. No circular references in payload
"""

# ============================================================================
__dora_meta__ = {
    "component_name": "PacketEnvelope and Packet Definitions.",
    "module_version": "1.0.0",
    "created_by": "cryptoxdog",
    "created_at": "2026-01-25T05:47:37Z",
    "updated_at": "2026-01-25T08:58:44Z",
    "layer": "integration",
    "domain": "mcp_integration",
    "module_name": "protocol",
    "type": "dataclass",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": [],
        "memory_layers": ["semantic_memory", "working_memory"],
        "imported_by": [],
    },
}
# ============================================================================

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, Optional, Union
from uuid import uuid4


@dataclass(frozen=True)
class PacketMetadata:
    """Optional metadata attached to a packet.

    Fields:
        correlation_id: Trace ID for request tracking
        trace_id: OpenTelemetry trace ID
        span_id: OpenTelemetry span ID
        user_id: User who initiated the request
        caller_id: Caller identity (L or C)
        source: Origin of the packet (l9-kernel, cursor-ide, etc.)
        tags: Optional tags for filtering and debugging
    """

    correlation_id: Optional[str] = None
    trace_id: Optional[str] = None
    span_id: Optional[str] = None
    user_id: Optional[str] = None
    caller_id: Optional[str] = None  # "L" or "C"
    source: Optional[str] = None
    tags: Optional[Dict[str, str]] = field(default_factory=dict)


@dataclass(frozen=True)
class PacketEnvelopeV2:
    """Immutable packet for all inter-module communication.

    This is the protocol contract that ALL kernel/substrate/safety operations
    must use. Immutability ensures audit integrity and prevents accidental
    state mutations during request processing.

    Invariants:
        - packet_id: Unique, auto-generated, immutable
        - packet_type: Must be one of PACKET_TYPES
        - timestamp: ISO 8601 UTC, set at creation
        - confidence: Float in [0, 1], default 1.0
        - payload: Arbitrary JSON-serializable dict
        - metadata: Optional correlation and trace info

    To modify, use .with_update() which returns new instance:
        new_packet = packet.with_update(confidence=0.8, status="processed")
    """

    # Core fields (required)
    packet_type: str  # e.g., "memory_search", "safety_check", "audit_log"
    payload: Dict[str, Any]

    # Auto-generated (immutable)
    packet_id: str = field(default_factory=lambda: str(uuid4()))
    timestamp: datetime = field(default_factory=datetime.utcnow)

    # Optional fields
    confidence: float = 1.0  # [0, 1]
    status: str = "pending"  # pending, processing, completed, failed
    error: Optional[str] = None
    metadata: Optional[PacketMetadata] = None
    result: Optional[Dict[str, Any]] = None

    def __post_init__(self):
        """Validate immutability constraints."""
        # Frozen dataclass prevents mutation, but validate confidence range
        if not (0 <= self.confidence <= 1):
            raise ValueError(f"confidence must be in [0, 1], got {self.confidence}")
        if not isinstance(self.packet_type, str) or not self.packet_type:
            raise ValueError("packet_type must be non-empty string")
        if not isinstance(self.payload, dict):
            raise ValueError("payload must be dict")

    def with_update(self, **kwargs) -> "PacketEnvelopeV2":
        """Create new packet with updated fields (preserves immutability).

        Note: packet_id and timestamp cannot be changed.

        Args:
            **kwargs: Fields to update

        Returns:
            New PacketEnvelopeV2 with updates applied

        Raises:
            ValueError: If attempting to modify packet_id or timestamp
        """
        if "packet_id" in kwargs:
            raise ValueError("packet_id cannot be modified after creation")
        if "timestamp" in kwargs:
            raise ValueError("timestamp cannot be modified after creation")

        # Use replace() from dataclasses to create new instance
        from dataclasses import replace

        return replace(self, **kwargs)


# Alias for backwards compatibility
PacketEnvelope = PacketEnvelopeV2


# Common packet types
PACKET_TYPES = {
    "memory_save": "Save memory to substrate",
    "memory_search": "Search memory semantically",
    "memory_delete": "Delete memory",
    "safety_check": "Run safety policy checks",
    "audit_log": "Audit event logging",
    "governance_check": "Governance/RLS validation",
}


def create_packet(
    packet_type: str,
    payload: Dict[str, Any],
    confidence: float = 1.0,
    metadata: Optional[PacketMetadata] = None,
) -> PacketEnvelopeV2:
    """Factory function to create and validate packet.

    Args:
        packet_type: Type of packet (see PACKET_TYPES)
        payload: Operation-specific data
        confidence: Confidence score [0, 1]
        metadata: Optional correlation/trace info

    Returns:
        New PacketEnvelopeV2

    Raises:
        ValueError: If packet_type invalid or payload not dict
    """
    if packet_type not in PACKET_TYPES:
        raise ValueError(
            f"Unknown packet_type '{packet_type}'. Valid: {list(PACKET_TYPES.keys())}"
        )

    return PacketEnvelopeV2(
        packet_type=packet_type,
        payload=payload,
        confidence=confidence,
        metadata=metadata,
    )


__all__ = [
    "PacketMetadata",
    "PacketEnvelopeV2",
    "PacketEnvelope",
    "create_packet",
    "PACKET_TYPES",
]

# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "MCP-INTE-010",
    "governance_level": "medium",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": [
        "audit-tool",
        "dataclass",
        "debugging",
        "event-driven",
        "integration",
        "mcp-integration",
        "testing",
        "tracing",
    ],
    "keywords": [
        "audit",
        "create",
        "definitions.",
        "envelope",
        "governance",
        "immutable",
        "kernel",
        "metadata",
    ],
    "business_value": "This module defines the immutable contract for all inter-module communication. All substrate operations must be wrapped in PacketEnvelope for tracing, audit, and governance enforcement. 1. PacketEnvel",
    "last_modified": "2026-01-25T08:58:44Z",
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
