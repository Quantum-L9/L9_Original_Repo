"""
Tensor Motif Linker — TML-003

Bind motif metadata to tensor routing packets and responses.
Links the motif layer with the tensor coordination layer.
"""

# ============================================================================
__dora_meta__ = {
    "component_name": "Tensor Motif Linker",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2026-01-26T11:14:45Z",
    "updated_at": "2026-01-31T22:21:54Z",
    "layer": "operations",
    "domain": "motifs",
    "module_name": "tensor_motif_linker",
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
from datetime import UTC
from typing import Any
from uuid import uuid4

import structlog

logger = structlog.get_logger(__name__)


@dataclass
class MotifMetadata:
    """Metadata describing a motif attachment."""

    motif_id: str = field(default_factory=lambda: str(uuid4()))
    motif_type: str = ""
    confidence: float = 0.0
    source_component: str = ""
    tags: dict[str, Any] = field(default_factory=dict)


class TensorMotifLinker:
    """
    Bind motif metadata to tensor routing packets and responses.

    Provides:
    - Attachment of motif metadata to packets
    - Extraction of motifs from packets
    - Binding of tensor responses with motif context
    """

    MOTIF_METADATA_KEY = "_motif_metadata"

    def __init__(self):
        """Initialize the tensor motif linker."""
        self.logger = logger.bind(component="TensorMotifLinker")
        self.logger.info("TensorMotifLinker initialized")

    def attach_motifs(
        self,
        packet: dict[str, Any],
        motifs: list[MotifMetadata],
    ) -> dict[str, Any]:
        """
        Attach motif metadata to a packet's metadata field.

        Args:
            packet: The packet dictionary to attach motifs to
            motifs: List of MotifMetadata to attach

        Returns:
            Updated packet with motif metadata attached
        """
        if "metadata" not in packet:
            packet["metadata"] = {}

        # Serialize motifs to dict format
        motif_list = [
            {
                "motif_id": m.motif_id,
                "motif_type": m.motif_type,
                "confidence": m.confidence,
                "source_component": m.source_component,
                "tags": m.tags,
            }
            for m in motifs
        ]

        packet["metadata"][self.MOTIF_METADATA_KEY] = motif_list

        self.logger.debug(
            "motifs.attached",
            packet_id=packet.get("packet_id", "unknown"),
            motif_count=len(motifs),
        )

        return packet

    def extract_motifs(self, packet: dict[str, Any]) -> list[MotifMetadata]:
        """
        Extract motif metadata from a packet if present.

        Args:
            packet: The packet to extract motifs from

        Returns:
            List of MotifMetadata extracted from packet
        """
        metadata = packet.get("metadata", {})
        motif_data = metadata.get(self.MOTIF_METADATA_KEY, [])

        motifs = []
        for m in motif_data:
            motifs.append(
                MotifMetadata(
                    motif_id=m.get("motif_id", str(uuid4())),
                    motif_type=m.get("motif_type", ""),
                    confidence=m.get("confidence", 0.0),
                    source_component=m.get("source_component", ""),
                    tags=m.get("tags", {}),
                )
            )

        return motifs

    def bind_tensor_response(
        self,
        packet: dict[str, Any],
        tensor_response: dict[str, Any],
        motifs: list[MotifMetadata],
    ) -> dict[str, Any]:
        """
        Bind motif metadata to a tensor response and return updated packet.

        Args:
            packet: Original packet
            tensor_response: Response from tensor operations
            motifs: Motifs to bind to the response

        Returns:
            Updated packet with tensor response and motifs
        """
        # Attach motifs to packet
        packet = self.attach_motifs(packet, motifs)

        # Add tensor response to packet
        if "metadata" not in packet:
            packet["metadata"] = {}
        packet["metadata"]["tensor_response"] = tensor_response

        # Add binding timestamp
        from datetime import datetime, timezone

        packet["metadata"]["tensor_motif_bound_at"] = datetime.now(UTC).isoformat()

        self.logger.info(
            "tensor_response.bound",
            packet_id=packet.get("packet_id", "unknown"),
            motif_count=len(motifs),
            response_keys=list(tensor_response.keys()) if tensor_response else [],
        )

        return packet

    def create_motif_from_tensor(
        self,
        tensor_result: dict[str, Any],
        motif_type: str,
        source_component: str = "TensorMotifLinker",
    ) -> MotifMetadata:
        """
        Create a MotifMetadata from a tensor operation result.

        Args:
            tensor_result: Result from tensor operation
            motif_type: Type of motif to create
            source_component: Component creating this motif

        Returns:
            New MotifMetadata instance
        """
        return MotifMetadata(
            motif_type=motif_type,
            confidence=tensor_result.get("confidence", 0.5),
            source_component=source_component,
            tags={
                "tensor_operation": tensor_result.get("operation", "unknown"),
                "entity_count": len(tensor_result.get("entities", [])),
            },
        )


__all__ = ["MotifMetadata", "TensorMotifLinker"]
# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "MOT-OPER-001",
    "governance_level": "medium",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": ["dataclass", "debugging", "logging", "motifs", "operations"],
    "keywords": [
        "attach",
        "bind",
        "create",
        "extract",
        "layer",
        "linker",
        "metadata",
        "motif",
    ],
    "business_value": "Provides tensor motif linker components including MotifMetadata, TensorMotifLinker",
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
