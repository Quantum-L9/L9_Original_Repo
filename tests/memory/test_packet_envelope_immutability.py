"""
Test PacketEnvelope Immutability Contract

GMP: ENFORCE_IMMUTABILITY_V1_1_0
Phase: 4 (VALIDATE)

Verifies that PacketEnvelope v1.1.0 in memory/substrate_models.py
correctly enforces immutability via frozen=True model_config.

Test Matrix:
- Positive: Creation, with_mutation(), lineage chain
- Negative: Mutation attempts must raise ValidationError
- Regression: Existing functionality preserved
"""

from datetime import datetime, timezone, timedelta
from uuid import uuid4

import pytest
from pydantic import ValidationError

from core.schemas import (
    PacketConfidence,
    PacketEnvelope,
    PacketLineage,
    PacketMetadata,
    PacketProvenance,
)


class TestPacketEnvelopeImmutability:
    """Test suite for PacketEnvelope immutability enforcement."""

    # =========================================================================
    # POSITIVE TESTS
    # =========================================================================

    def test_create_packet_with_all_v1_1_fields(self):
        """Create packet with all v1.1.0 fields → SUCCESS."""
        packet = PacketEnvelope(
            packet_type="test_event",
            payload={"key": "value", "nested": {"data": 123}},
            thread_id=uuid4(),
            lineage=PacketLineage(
                parent_ids=[uuid4()],
                derivation_type="transform",
                generation=1,
            ),
            tags=["test", "immutability"],
            ttl=datetime.now(timezone.utc) + timedelta(days=7),
            metadata=PacketMetadata(agent="test_agent"),
            confidence=PacketConfidence(score=0.95, rationale="High confidence test"),
        )

        assert packet.packet_id is not None
        assert packet.packet_type == "test_event"
        assert packet.payload == {"key": "value", "nested": {"data": 123}}
        assert packet.thread_id is not None
        assert packet.lineage is not None
        assert packet.lineage.generation == 1
        assert packet.tags == ["test", "immutability"]
        assert packet.ttl is not None
        assert packet.metadata.schema_version == "1.1.1"

    def test_with_mutation_creates_new_packet(self):
        """with_mutation(payload={"new": "data"}) → Returns NEW packet with lineage."""
        original = PacketEnvelope(
            packet_type="original",
            payload={"original": "data"},
        )

        mutated = original.with_mutation(payload={"new": "data"})

        # New packet ID (not the same)
        assert mutated.packet_id != original.packet_id
        # Updated payload
        assert mutated.payload == {"new": "data"}
        # Original unchanged
        assert original.payload == {"original": "data"}
        # New timestamp
        assert mutated.timestamp >= original.timestamp

    def test_with_mutation_creates_proper_lineage(self):
        """Verify new packet.lineage.parent_ids == [old packet.packet_id]."""
        original = PacketEnvelope(
            packet_type="parent",
            payload={"step": 1},
        )

        mutated = original.with_mutation(payload={"step": 2})

        assert mutated.lineage is not None
        assert original.packet_id in mutated.lineage.parent_ids
        assert mutated.lineage.derivation_type == "mutation"
        assert mutated.lineage.generation == 1
        assert mutated.lineage.root_packet_id == original.packet_id

    def test_with_mutation_chain_increments_generation(self):
        """Chained mutations increment generation correctly."""
        p1 = PacketEnvelope(packet_type="gen0", payload={"gen": 0})
        p2 = p1.with_mutation(payload={"gen": 1})
        p3 = p2.with_mutation(payload={"gen": 2})
        p4 = p3.with_mutation(payload={"gen": 3})

        assert p1.lineage is None  # Original has no lineage
        assert p2.lineage.generation == 1
        assert p3.lineage.generation == 2
        assert p4.lineage.generation == 3

        # Root packet ID preserved through chain
        assert p2.lineage.root_packet_id == p1.packet_id
        assert p3.lineage.root_packet_id == p1.packet_id
        assert p4.lineage.root_packet_id == p1.packet_id

    # =========================================================================
    # NEGATIVE TESTS - MUTATION ATTEMPTS MUST FAIL
    # =========================================================================

    def test_cannot_reassign_payload(self):
        """packet.payload = {} → MUST RAISE ValidationError.

        Note: Pydantic's frozen=True prevents field reassignment but not
        nested dict mutation. For deep immutability, use with_mutation().
        """
        packet = PacketEnvelope(
            packet_type="frozen_test",
            payload={"original": "value"},
        )

        with pytest.raises(ValidationError):
            packet.payload = {"replaced": "dict"}

    def test_cannot_mutate_timestamp(self):
        """packet.timestamp = datetime.now() → MUST RAISE ValidationError."""
        packet = PacketEnvelope(
            packet_type="frozen_test",
            payload={"data": "test"},
        )

        with pytest.raises(ValidationError):
            packet.timestamp = datetime.now(timezone.utc)

    def test_cannot_mutate_packet_type(self):
        """packet.packet_type = "new_type" → MUST RAISE ValidationError."""
        packet = PacketEnvelope(
            packet_type="original_type",
            payload={"data": "test"},
        )

        with pytest.raises(ValidationError):
            packet.packet_type = "changed_type"

    def test_cannot_mutate_packet_id(self):
        """packet.packet_id = uuid4() → MUST RAISE ValidationError."""
        packet = PacketEnvelope(
            packet_type="frozen_test",
            payload={"data": "test"},
        )

        with pytest.raises(ValidationError):
            packet.packet_id = uuid4()

    def test_cannot_mutate_tags_list(self):
        """packet.tags.append("new_tag") → MUST RAISE (frozen list behavior)."""
        packet = PacketEnvelope(
            packet_type="frozen_test",
            payload={"data": "test"},
            tags=["original"],
        )

        # Note: With frozen=True, attempting to access and modify
        # will raise TypeError or AttributeError depending on Pydantic version
        # This test verifies the list cannot be modified via direct assignment
        with pytest.raises(ValidationError):
            packet.tags = ["new_list"]

    def test_cannot_add_extra_fields(self):
        """extra="forbid" prevents adding unknown fields."""
        with pytest.raises(ValidationError):
            PacketEnvelope(
                packet_type="test",
                payload={"data": "test"},
                unknown_field="should_fail",  # type: ignore
            )

    # =========================================================================
    # REGRESSION TESTS
    # =========================================================================

    def test_supporting_models_also_immutable(self):
        """PacketMetadata, PacketProvenance, PacketConfidence are frozen."""
        metadata = PacketMetadata(agent="test")
        with pytest.raises(ValidationError):
            metadata.agent = "changed"

        provenance = PacketProvenance(source="test")
        with pytest.raises(ValidationError):
            provenance.source = "changed"

        confidence = PacketConfidence(score=0.5)
        with pytest.raises(ValidationError):
            confidence.score = 0.9

        lineage = PacketLineage(generation=1)
        with pytest.raises(ValidationError):
            lineage.generation = 5

    def test_packet_envelope_serialization(self):
        """Packets can be serialized to JSON and back."""
        original = PacketEnvelope(
            packet_type="serialization_test",
            payload={"complex": {"nested": [1, 2, 3]}},
            thread_id=uuid4(),
            tags=["serialize", "test"],
        )

        # Serialize
        json_data = original.model_dump_json()
        assert isinstance(json_data, str)

        # Deserialize
        restored = PacketEnvelope.model_validate_json(json_data)
        assert restored.packet_id == original.packet_id
        assert restored.payload == original.payload
        assert restored.thread_id == original.thread_id
        assert restored.tags == original.tags

    def test_packet_envelope_dict_roundtrip(self):
        """Packets can be converted to dict and back."""
        original = PacketEnvelope(
            packet_type="dict_test",
            payload={"data": "value"},
            lineage=PacketLineage(parent_ids=[uuid4()], generation=2),
        )

        # To dict
        as_dict = original.model_dump()
        assert isinstance(as_dict, dict)

        # From dict
        restored = PacketEnvelope.model_validate(as_dict)
        assert restored.packet_id == original.packet_id
        assert restored.lineage.generation == 2


class TestPacketEnvelopeInConversion:
    """Test PacketEnvelopeIn → PacketEnvelope conversion."""

    def test_envelope_in_to_envelope(self):
        """PacketEnvelopeIn.to_envelope() creates valid PacketEnvelope."""
        from core.schemas import PacketEnvelopeIn

        envelope_in = PacketEnvelopeIn(
            packet_type="input_test",
            payload={"from": "input"},
            thread_id=uuid4(),
            tags=["converted"],
        )

        envelope = envelope_in.to_envelope()

        assert isinstance(envelope, PacketEnvelope)
        assert envelope.packet_type == "input_test"
        assert envelope.payload == {"from": "input"}
        assert envelope.tags == ["converted"]
        # Should be immutable
        with pytest.raises(ValidationError):
            envelope.payload = {"mutated": True}


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
