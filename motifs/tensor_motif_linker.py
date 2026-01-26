"""
Tensor Motif Linker — TML-003

Bind motif metadata to tensor routing packets and responses.
Links the motif layer with the tensor coordination layer.
"""

import logging
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional
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
    tags: Dict[str, Any] = field(default_factory=dict)


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
        packet: Dict[str, Any],
        motifs: List[MotifMetadata],
    ) -> Dict[str, Any]:
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

    def extract_motifs(self, packet: Dict[str, Any]) -> List[MotifMetadata]:
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
        packet: Dict[str, Any],
        tensor_response: Dict[str, Any],
        motifs: List[MotifMetadata],
    ) -> Dict[str, Any]:
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
        from datetime import datetime

        packet["metadata"]["tensor_motif_bound_at"] = datetime.utcnow().isoformat()

        self.logger.info(
            "tensor_response.bound",
            packet_id=packet.get("packet_id", "unknown"),
            motif_count=len(motifs),
            response_keys=list(tensor_response.keys()) if tensor_response else [],
        )

        return packet

    def create_motif_from_tensor(
        self,
        tensor_result: Dict[str, Any],
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


__all__ = ["TensorMotifLinker", "MotifMetadata"]
