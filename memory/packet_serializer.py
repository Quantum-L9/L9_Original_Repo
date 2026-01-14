"""
L9 Memory - Packet Serializer
Version: 1.0.0

Utility helpers to convert PacketEnvelope <-> dict/JSON safe structures.

Centralizes how we flatten packets for logging, external APIs, and tests.
"""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Dict

from core.schemas import PacketEnvelope, PacketEnvelopeIn


def envelope_to_dict(envelope: PacketEnvelope) -> Dict[str, Any]:
    """
    Convert a PacketEnvelope to a JSON-serializable dict.

    Uses Pydantic's model_dump but normalizes datetimes and UUIDs to strings.
    """
    data = envelope.model_dump(mode="json")
    # Ensure timestamp is ISO string for consistency
    ts = data.get("timestamp")
    if isinstance(ts, datetime):
        data["timestamp"] = ts.isoformat()
    return data


def envelope_from_dict(data: Dict[str, Any]) -> PacketEnvelope:
    """
    Construct a PacketEnvelope from a dict that likely came from JSON.
    """
    return PacketEnvelope.model_validate(data)


def packet_in_from_dict(data: Dict[str, Any]) -> PacketEnvelopeIn:
    """
    Construct a PacketEnvelopeIn from a dict.

    Useful for tests and external adapters that receive JSON payloads.
    """
    return PacketEnvelopeIn.model_validate(data)


def envelope_to_json(envelope: PacketEnvelope) -> str:
    """Dump a PacketEnvelope to a JSON string."""
    return json.dumps(envelope_to_dict(envelope), separators=(",", ":"))


def envelope_from_json(payload: str) -> PacketEnvelope:
    """Load a PacketEnvelope from a JSON string."""
    return envelope_from_dict(json.loads(payload))
