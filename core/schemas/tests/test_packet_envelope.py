"""
Tests for PacketEnvelope schema (Memory.yaml v1.0.1).

Validates:
- Immutability (frozen=True)
- Required fields (packet_type, payload, timestamp)
- Optional fields (metadata, provenance, confidence)
- PacketEnvelopeIn conversion
- Semantic search models
"""

from datetime import datetime
from uuid import uuid4

import pytest

from core.schemas.packet_envelope import (
    PacketConfidence,
    PacketEnvelope,
    PacketEnvelopeIn,
    PacketMetadata,
    PacketProvenance,
    PacketWriteResult,
    SemanticHit,
    SemanticSearchRequest,
    SemanticSearchResult,
)


class TestPacketEnvelopeImmutability:
    """Test that PacketEnvelope is immutable (frozen)."""

    def test_cannot_modify_packet_id(self):
        """Verify packet_id cannot be changed after creation."""
        envelope = PacketEnvelope(packet_type="event", payload={"message": "Hello"})

        with pytest.raises(Exception):  # ValidationError or AttributeError
            envelope.packet_id = uuid4()

    def test_cannot_modify_payload(self):
        """Verify payload cannot be changed after creation."""
        envelope = PacketEnvelope(packet_type="event", payload={"message": "Hello"})

        with pytest.raises(Exception):
            envelope.payload = {"message": "Modified"}

    def test_with_update_creates_new_packet(self):
        """Verify with_update creates a new packet with lineage."""
        original = PacketEnvelope(packet_type="event", payload={"message": "Original"})

        updated = original.with_update(payload={"message": "Updated"})

        assert updated.packet_id != original.packet_id
        assert updated.provenance is not None
        assert updated.provenance.parent_packet == original.packet_id
        assert updated.payload["message"] == "Updated"


class TestPacketEnvelopeRequired:
    """Test required fields."""

    def test_packet_type_required(self):
        """Verify packet_type is required."""
        with pytest.raises(Exception):
            PacketEnvelope(payload={"data": "test"})

    def test_payload_required(self):
        """Verify payload is required."""
        with pytest.raises(Exception):
            PacketEnvelope(packet_type="event")

    def test_timestamp_auto_generated(self):
        """Verify timestamp is auto-generated."""
        envelope = PacketEnvelope(packet_type="event", payload={"data": "test"})

        assert envelope.timestamp is not None
        assert isinstance(envelope.timestamp, datetime)

    def test_packet_id_auto_generated(self):
        """Verify packet_id is auto-generated."""
        envelope = PacketEnvelope(packet_type="event", payload={"data": "test"})

        assert envelope.packet_id is not None


class TestPacketEnvelopeOptional:
    """Test optional fields."""

    def test_metadata_optional(self):
        """Verify metadata is optional."""
        envelope = PacketEnvelope(packet_type="event", payload={"data": "test"})

        assert envelope.metadata is None

    def test_metadata_with_values(self):
        """Verify metadata can be set."""
        metadata = PacketMetadata(
            schema_version="1.0.1", agent="test_agent", domain="test_domain"
        )

        envelope = PacketEnvelope(
            packet_type="event", payload={"data": "test"}, metadata=metadata
        )

        assert envelope.metadata.agent == "test_agent"

    def test_provenance_optional(self):
        """Verify provenance is optional."""
        envelope = PacketEnvelope(packet_type="event", payload={"data": "test"})

        assert envelope.provenance is None

    def test_provenance_with_parent(self):
        """Verify provenance can link to parent."""
        parent_id = uuid4()
        provenance = PacketProvenance(
            parent_packet=parent_id, source_agent="test_agent"
        )

        envelope = PacketEnvelope(
            packet_type="event", payload={"data": "test"}, provenance=provenance
        )

        assert envelope.provenance.parent_packet == parent_id

    def test_confidence_optional(self):
        """Verify confidence is optional."""
        envelope = PacketEnvelope(packet_type="event", payload={"data": "test"})

        assert envelope.confidence is None

    def test_confidence_with_values(self):
        """Verify confidence can be set."""
        confidence = PacketConfidence(
            score=0.95, rationale="High confidence based on source"
        )

        envelope = PacketEnvelope(
            packet_type="event", payload={"data": "test"}, confidence=confidence
        )

        assert envelope.confidence.score == 0.95


class TestPacketEnvelopeIn:
    """Test PacketEnvelopeIn input model."""

    def test_to_envelope_basic(self):
        """Verify basic conversion to PacketEnvelope."""
        input_packet = PacketEnvelopeIn(
            packet_type="message", payload={"text": "Hello world"}
        )

        envelope = input_packet.to_envelope()

        assert envelope.packet_type == "message"
        assert envelope.payload["text"] == "Hello world"
        assert envelope.packet_id is not None
        assert envelope.timestamp is not None

    def test_to_envelope_with_all_fields(self):
        """Verify conversion with all optional fields."""
        input_packet = PacketEnvelopeIn(
            packet_type="event",
            payload={"data": "test"},
            metadata={"agent": "test_agent"},
            provenance={"source_agent": "origin"},
            confidence={"score": 0.8},
        )

        envelope = input_packet.to_envelope()

        assert envelope.metadata.agent == "test_agent"
        assert envelope.provenance.source_agent == "origin"
        assert envelope.confidence.score == 0.8


class TestPacketWriteResult:
    """Test PacketWriteResult model."""

    def test_success_result(self):
        """Verify success result creation."""
        result = PacketWriteResult(
            status="ok",
            packet_id=uuid4(),
            written_tables=["packet_store", "semantic_memory"],
        )

        assert result.status == "ok"
        assert len(result.written_tables) == 2

    def test_error_result(self):
        """Verify error result creation."""
        result = PacketWriteResult(
            status="error",
            packet_id=uuid4(),
            written_tables=[],
            error_message="Database connection failed",
        )

        assert result.status == "error"
        assert result.error_message is not None


class TestSemanticSearch:
    """Test semantic search models."""

    def test_search_request(self):
        """Verify search request creation."""
        request = SemanticSearchRequest(query="find suppliers", top_k=5)

        assert request.query == "find suppliers"
        assert request.top_k == 5

    def test_search_request_with_agent_filter(self):
        """Verify search request with agent filter."""
        request = SemanticSearchRequest(
            query="find suppliers", top_k=10, agent_id="agent_123"
        )

        assert request.agent_id == "agent_123"

    def test_semantic_hit(self):
        """Verify semantic hit creation."""
        hit = SemanticHit(
            embedding_id=uuid4(), score=0.95, payload={"document": "test content"}
        )

        assert hit.score == 0.95

    def test_search_result(self):
        """Verify search result creation."""
        hits = [
            SemanticHit(embedding_id=uuid4(), score=0.9, payload={"doc": "1"}),
            SemanticHit(embedding_id=uuid4(), score=0.8, payload={"doc": "2"}),
        ]

        result = SemanticSearchResult(query="test query", hits=hits)

        assert result.query == "test query"
        assert len(result.hits) == 2


class TestConfidenceValidation:
    """Test confidence score validation."""

    def test_confidence_valid_range(self):
        """Verify valid confidence scores."""
        conf = PacketConfidence(score=0.0)
        assert conf.score == 0.0

        conf = PacketConfidence(score=1.0)
        assert conf.score == 1.0

        conf = PacketConfidence(score=0.5)
        assert conf.score == 0.5

    def test_confidence_below_zero(self):
        """Verify confidence below 0 is rejected."""
        with pytest.raises(ValueError):
            PacketConfidence(score=-0.1)

    def test_confidence_above_one(self):
        """Verify confidence above 1 is rejected."""
        with pytest.raises(ValueError):
            PacketConfidence(score=1.1)
