"""
L9 Memory - Packet Validator
Version: 1.0.0

Centralized validation for PacketEnvelopeIn before it hits the DAG.
This is where we enforce business-level constraints above Pydantic's typing.
"""

from __future__ import annotations

from typing import Iterable

from pydantic import ValidationError

from memory.substrate_models import PacketEnvelopeIn
from memory.audit_utils import detect_injection_markers, detect_pii_types


ALLOWED_PACKET_TYPES: set[str] = {
    "event",
    "memory_write",
    "reasoning_trace",
    "tool_call",
    "tool_result",
    "message",
}


class PacketValidationError(Exception):
    """Raised when a packet fails custom validation."""


class PacketValidator:
    """Static helpers for validating PacketEnvelopeIn instances."""

    @staticmethod
    def validate(packet_in: PacketEnvelopeIn) -> None:
        """
        Perform custom validation:
        - Pydantic structural validation
        - packet_type sanity check
        """
        # This will re-run Pydantic's field-level checks
        try:
            PacketEnvelopeIn.model_validate(packet_in.model_dump())
        except ValidationError as exc:
            raise PacketValidationError(f"Structural validation failed: {exc}") from exc

        if packet_in.packet_type not in ALLOWED_PACKET_TYPES:
            raise PacketValidationError(
                f"packet_type '{packet_in.packet_type}' not in {sorted(ALLOWED_PACKET_TYPES)}"
            )

    @staticmethod
    def scan_security(packet_in: PacketEnvelopeIn) -> dict[str, list[str]]:
        """
        Scan packet payload for PII and injection markers.

        Returns:
            Dict with detected pii_types and injection_markers.
        """
        pii_types = list(detect_pii_types(packet_in.payload))
        injection_markers = list(detect_injection_markers(packet_in.payload))
        return {
            "pii_types": pii_types,
            "injection_markers": injection_markers,
        }

    @staticmethod
    def allowed_types() -> Iterable[str]:
        return sorted(ALLOWED_PACKET_TYPES)
