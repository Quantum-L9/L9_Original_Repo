"""
L9 Memory - Packet Serializer
Version: 1.0.0

Utility helpers to convert PacketEnvelope <-> dict/JSON safe structures.

Centralizes how we flatten packets for logging, external APIs, and tests.
"""

from __future__ import annotations

# ============================================================================
__dora_meta__ = {
    "component_name": "Packet Serializer",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2025-12-09T01:02:49Z",
    "updated_at": "2026-01-14T13:21:36Z",
    "layer": "learning",
    "domain": "memory_substrate",
    "module_name": "packet_serializer",
    "type": "utility",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": [],
        "memory_layers": ["working_memory"],
        "imported_by": ["tests.memory.test_packet_envelope"],
    },
}
# ============================================================================

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

# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "MEM-LEAR-001",
    "governance_level": "critical",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": ["core.schemas"],
    "tags": ["api", "learning", "memory-substrate", "serialization", "testing", "utility"],
    "keywords": ["envelope", "json", "memory", "packet", "serializer"],
    "business_value": "Utility module for packet serializer",
    "last_modified": "2026-01-14T13:21:36Z",
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
