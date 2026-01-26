"""
Tests for schema validation and constraints.

Memory.yaml v1.0.1 note:
- payload is arbitrary JSON and NOT variant-typed
- No kind discriminator in this version
- Validation focuses on required fields and data types
"""

from uuid import uuid4

import pytest

from core.schemas.packet_envelope import (
    PacketEnvelope,
    PacketEnvelopeIn,
    PacketMetadata,
    SemanticSearchRequest,
)
from core.schemas.research_factory_models import ParsedObject, ValidationStatus


class TestPacketTypeValidation:
    """Test packet_type field validation."""

    def test_packet_type_required(self):
        """Verify packet_type is required."""
        with pytest.raises(Exception):
            PacketEnvelope(payload={"data": "test"})

    def test_packet_type_min_length(self):
        """Verify packet_type has minimum length."""
        with pytest.raises(Exception):
            PacketEnvelope(packet_type="", payload={"data": "test"})

    def test_valid_packet_types(self):
        """Verify various valid packet types."""
        types = ["event", "message", "reasoning_trace", "tool_call", "tool_result"]

        for ptype in types:
            envelope = PacketEnvelope(packet_type=ptype, payload={"data": "test"})
            assert envelope.packet_type == ptype


class TestPayloadValidation:
    """Test payload field validation."""

    def test_payload_is_dict(self):
        """Verify payload accepts dictionary."""
        envelope = PacketEnvelope(
            packet_type="event", payload={"key": "value", "nested": {"a": 1}}
        )

        assert envelope.payload["key"] == "value"
        assert envelope.payload["nested"]["a"] == 1

    def test_payload_accepts_any_structure(self):
        """Verify payload is arbitrary JSON (v1.0.1 contract)."""
        # Simple
        envelope = PacketEnvelope(packet_type="event", payload={"simple": "data"})
        assert envelope.payload["simple"] == "data"

        # Complex nested
        envelope = PacketEnvelope(
            packet_type="event",
            payload={
                "level1": {"level2": {"level3": ["a", "b", "c"]}},
                "numbers": [1, 2, 3],
                "mixed": {"string": "test", "number": 42, "bool": True},
            },
        )
        assert envelope.payload["level1"]["level2"]["level3"] == ["a", "b", "c"]

    def test_payload_empty_dict_allowed(self):
        """Verify empty payload dict is allowed."""
        envelope = PacketEnvelope(packet_type="event", payload={})
        assert envelope.payload == {}


class TestValidationStatusEnum:
    """Test ValidationStatus enum in ParsedObject."""

    def test_all_validation_statuses(self):
        """Verify all ValidationStatus values are valid."""
        for status in ValidationStatus:
            obj = ParsedObject(
                batch_id=uuid4(),
                extracted_data={"test": "data"},
                validation_status=status,
                confidence=0.5,
            )
            assert obj.validation_status == status

    def test_validation_status_values(self):
        """Verify ValidationStatus enum values."""
        assert ValidationStatus.VALID.value == "valid"
        assert ValidationStatus.INVALID.value == "invalid"
        assert ValidationStatus.PARTIAL.value == "partial"
        assert ValidationStatus.PENDING.value == "pending"


class TestMetadataExtras:
    """Test metadata accepts extra fields."""

    def test_metadata_extra_fields(self):
        """Verify metadata allows extra fields (extra='allow')."""
        metadata = PacketMetadata(
            schema_version="1.0.1", agent="test", domain="test_domain"
        )

        # These should be accessible
        assert metadata.schema_version == "1.0.1"
        assert metadata.agent == "test"


class TestSemanticSearchValidation:
    """Test SemanticSearchRequest validation."""

    def test_query_min_length(self):
        """Verify query has minimum length."""
        with pytest.raises(Exception):
            SemanticSearchRequest(query="", top_k=5)

    def test_top_k_bounds(self):
        """Verify top_k bounds (1-100)."""
        # Valid min
        req = SemanticSearchRequest(query="test", top_k=1)
        assert req.top_k == 1

        # Valid max
        req = SemanticSearchRequest(query="test", top_k=100)
        assert req.top_k == 100

        # Invalid below min
        with pytest.raises(Exception):
            SemanticSearchRequest(query="test", top_k=0)

        # Invalid above max
        with pytest.raises(Exception):
            SemanticSearchRequest(query="test", top_k=101)


class TestPacketEnvelopeInValidation:
    """Test PacketEnvelopeIn input validation."""

    def test_packet_type_required(self):
        """Verify packet_type is required on input."""
        with pytest.raises(Exception):
            PacketEnvelopeIn(payload={"data": "test"})

    def test_payload_required(self):
        """Verify payload is required on input."""
        with pytest.raises(Exception):
            PacketEnvelopeIn(packet_type="event")

    def test_optional_fields_truly_optional(self):
        """Verify optional fields can be omitted."""
        input_packet = PacketEnvelopeIn(packet_type="event", payload={"data": "test"})

        assert input_packet.metadata is None
        assert input_packet.provenance is None
        assert input_packet.confidence is None
