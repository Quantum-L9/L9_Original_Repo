"""
Motif Feedback Graph — MFG-001

Track motif activations, decisions, and outcomes in a traceable graph structure.
Provides audit trail for reasoning patterns across domain packets.
"""

# ============================================================================
__dora_meta__ = {
    "component_name": "Motif Feedback Graph",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2026-01-26T11:14:45Z",
    "updated_at": "2026-01-31T22:21:54Z",
    "layer": "operations",
    "domain": "motifs",
    "module_name": "motif_feedback_graph",
    "type": "dataclass",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": [],
        "memory_layers": [],
        "imported_by": [],
    },
}
# ============================================================================

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

import structlog

logger = structlog.get_logger(__name__)


@dataclass
class MotifEvent:
    """A single motif activation event."""

    event_id: str = field(default_factory=lambda: str(uuid4()))
    packet_id: str = ""
    source_component: str = ""
    motif_type: str = ""
    features: dict[str, Any] = field(default_factory=dict)
    outcome: str = ""
    confidence: float = 0.0
    governance_flags: dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now(UTC).isoformat())


@dataclass
class MotifTrace:
    """Complete trace of motif events for a packet."""

    packet_id: str = ""
    events: list[MotifEvent] = field(default_factory=list)
    edges: list[dict[str, str]] = field(
        default_factory=list
    )  # {"from": id, "to": id, "relation": str}


class MotifFeedbackGraph:
    """
    Track motif activations, decisions, and outcomes in a traceable graph.

    Provides:
    - Event recording for motif activations
    - Transition tracking between events
    - Trace retrieval for audit
    - Aggregated statistics
    """

    def __init__(self):
        """Initialize the motif feedback graph."""
        self._events: dict[str, MotifEvent] = {}
        self._traces: dict[str, MotifTrace] = {}
        self._transitions: list[dict[str, str]] = []
        self.logger = logger.bind(component="MotifFeedbackGraph")
        self.logger.info("MotifFeedbackGraph initialized")

    async def record_event(
        self,
        packet_id: str,
        motif_type: str,
        features: dict[str, Any],
        outcome: str,
        confidence: float,
        source_component: str = "unknown",
        governance_flags: dict[str, Any] | None = None,
    ) -> MotifEvent:
        """
        Record a new motif event derived from a processed packet.

        Args:
            packet_id: ID of the packet that triggered this motif
            motif_type: Type of motif pattern detected
            features: Feature dict extracted for this motif
            outcome: Result of the motif activation
            confidence: Confidence score [0.0, 1.0]
            source_component: Component that generated this event
            governance_flags: Optional governance metadata

        Returns:
            The recorded MotifEvent
        """
        event = MotifEvent(
            packet_id=packet_id,
            source_component=source_component,
            motif_type=motif_type,
            features=features,
            outcome=outcome,
            confidence=confidence,
            governance_flags=governance_flags or {},
        )

        self._events[event.event_id] = event

        # Add to packet trace
        if packet_id not in self._traces:
            self._traces[packet_id] = MotifTrace(packet_id=packet_id)
        self._traces[packet_id].events.append(event)

        self.logger.info(
            "motif_event.recorded",
            event_id=event.event_id,
            packet_id=packet_id,
            motif_type=motif_type,
            confidence=confidence,
        )

        return event

    async def record_transition(
        self,
        from_event_id: str,
        to_event_id: str,
        relation: str,
    ) -> None:
        """
        Record a directed transition between two motif events.

        Args:
            from_event_id: Source event ID
            to_event_id: Target event ID
            relation: Type of relationship (e.g., "caused_by", "follows", "triggers")
        """
        transition = {
            "from": from_event_id,
            "to": to_event_id,
            "relation": relation,
        }
        self._transitions.append(transition)

        # Add edge to relevant traces
        from_event = self._events.get(from_event_id)
        if from_event and from_event.packet_id in self._traces:
            self._traces[from_event.packet_id].edges.append(transition)

        self.logger.debug(
            "motif_transition.recorded",
            from_event=from_event_id,
            to_event=to_event_id,
            relation=relation,
        )

    async def get_trace_for_packet(self, packet_id: str) -> MotifTrace:
        """
        Return the motif trace for a given packet ID.

        Args:
            packet_id: The packet to retrieve trace for

        Returns:
            MotifTrace containing all events and transitions
        """
        return self._traces.get(packet_id, MotifTrace(packet_id=packet_id))

    async def get_statistics(self) -> dict[str, Any]:
        """
        Aggregate statistics over motif events and transitions.

        Returns:
            Dictionary with aggregated metrics
        """
        motif_type_counts: dict[str, int] = {}
        outcome_counts: dict[str, int] = {}
        total_confidence = 0.0

        for event in self._events.values():
            motif_type_counts[event.motif_type] = (
                motif_type_counts.get(event.motif_type, 0) + 1
            )
            outcome_counts[event.outcome] = outcome_counts.get(event.outcome, 0) + 1
            total_confidence += event.confidence

        event_count = len(self._events)

        return {
            "total_events": event_count,
            "total_traces": len(self._traces),
            "total_transitions": len(self._transitions),
            "motif_type_distribution": motif_type_counts,
            "outcome_distribution": outcome_counts,
            "average_confidence": total_confidence / event_count
            if event_count > 0
            else 0.0,
        }

    def get_event(self, event_id: str) -> MotifEvent | None:
        """Get a specific event by ID."""
        return self._events.get(event_id)

    def __len__(self) -> int:
        """Return total number of events."""
        return len(self._events)


__all__ = ["MotifEvent", "MotifFeedbackGraph", "MotifTrace"]
# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "MOT-OPER-004",
    "governance_level": "medium",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": [
        "async",
        "audit-tool",
        "dataclass",
        "debugging",
        "event-driven",
        "logging",
        "metrics",
        "motifs",
        "operations",
        "tracing",
    ],
    "keywords": [
        "audit",
        "event",
        "feedback",
        "graph",
        "motif",
        "packet",
        "record",
        "statistics",
    ],
    "business_value": "Provides audit trail for reasoning patterns across domain packets.",
    "last_modified": "2026-01-31T22:21:54Z",
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
