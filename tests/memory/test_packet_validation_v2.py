"""
Test PacketValidator v2 - Validation against packet_envelope_v2 schema.

GMP: GMP-62 Packet Validation V2 Schema Alignment
Phase: 4 (VALIDATE)

Tests for:
- Typed PacketValidationError with field, value, error_code
- Malformed provenance fields (derive_type, source_timestamp)
- Confidence outside [0, 1]
- Async context compatibility (pure function, no I/O)
"""

from datetime import datetime, timedelta

import pytest

from core.schemas import (
    PacketEnvelopeIn,
    DeriveType,
    VALID_DERIVE_TYPES,
)
from memory.validators.packet_validator import (
    PacketValidator,
    PacketValidationError,
)


class TestPacketValidationErrorTyped:
    """Test the typed PacketValidationError exception."""

    def test_error_has_field_attribute(self):
        """PacketValidationError includes field path."""
        err = PacketValidationError(
            "Test error",
            field="confidence.score",
            value=1.5,
            error_code="TEST_ERROR",
        )
        assert err.field == "confidence.score"
        assert err.value == 1.5
        assert err.error_code == "TEST_ERROR"
        assert str(err) == "Test error"

    def test_error_backwards_compatible(self):
        """Error can be raised with just message (backwards compat)."""
        err = PacketValidationError("Simple error")
        assert err.field is None
        assert err.value is None
        assert err.error_code is None
        assert str(err) == "Simple error"


class TestConfidenceValidation:
    """Test confidence score validation."""

    def test_confidence_below_zero_rejected(self):
        """Confidence score < 0.0 raises PacketValidationError."""
        packet = PacketEnvelopeIn(
            packet_type="event",
            payload={"test": "data"},
            confidence={"score": -0.5},
        )
        with pytest.raises(PacketValidationError) as exc_info:
            PacketValidator.validate(packet)

        assert exc_info.value.field == "confidence.score"
        assert exc_info.value.value == -0.5
        assert exc_info.value.error_code == "CONFIDENCE_OUT_OF_RANGE"

    def test_confidence_above_one_rejected(self):
        """Confidence score > 1.0 raises PacketValidationError."""
        packet = PacketEnvelopeIn(
            packet_type="event",
            payload={"test": "data"},
            confidence={"score": 1.5},
        )
        with pytest.raises(PacketValidationError) as exc_info:
            PacketValidator.validate(packet)

        assert exc_info.value.field == "confidence.score"
        assert exc_info.value.error_code == "CONFIDENCE_OUT_OF_RANGE"

    def test_valid_confidence_accepted(self):
        """Confidence score in [0.0, 1.0] passes validation."""
        for score in [0.0, 0.5, 1.0]:
            packet = PacketEnvelopeIn(
                packet_type="event",
                payload={"test": "data"},
                confidence={"score": score},
            )
            # Should not raise
            PacketValidator.validate(packet)

    def test_confidence_none_accepted(self):
        """No confidence field is valid."""
        packet = PacketEnvelopeIn(
            packet_type="event",
            payload={"test": "data"},
        )
        # Should not raise
        PacketValidator.validate(packet)


class TestProvenanceValidation:
    """Test provenance field validation (v2.0.0 fields)."""

    def test_valid_derive_type_accepted(self):
        """Valid derive_type values pass validation."""
        for derive_type in ["direct", "inferred", "synthesized"]:
            packet = PacketEnvelopeIn(
                packet_type="event",
                payload={"test": "data"},
                provenance={"derive_type": derive_type},
            )
            # Should not raise
            PacketValidator.validate(packet)

    def test_invalid_derive_type_rejected(self):
        """derive_type not in valid set raises PacketValidationError."""
        packet = PacketEnvelopeIn(
            packet_type="event",
            payload={"test": "data"},
            provenance={"derive_type": "invalid_type"},
        )
        with pytest.raises(PacketValidationError) as exc_info:
            PacketValidator.validate(packet)

        assert exc_info.value.field == "provenance.derive_type"
        assert exc_info.value.value == "invalid_type"
        assert exc_info.value.error_code == "INVALID_DERIVE_TYPE"

    def test_source_timestamp_in_past_accepted(self):
        """source_timestamp in the past is valid."""
        past_time = datetime.utcnow() - timedelta(hours=1)
        packet = PacketEnvelopeIn(
            packet_type="event",
            payload={"test": "data"},
            provenance={"source_timestamp": past_time.isoformat()},
        )
        # Should not raise
        PacketValidator.validate(packet)

    def test_source_timestamp_in_future_rejected(self):
        """source_timestamp in the future raises PacketValidationError."""
        future_time = datetime.utcnow() + timedelta(hours=1)
        packet = PacketEnvelopeIn(
            packet_type="event",
            payload={"test": "data"},
            provenance={"source_timestamp": future_time.isoformat()},
        )
        with pytest.raises(PacketValidationError) as exc_info:
            PacketValidator.validate(packet)

        assert exc_info.value.field == "provenance.source_timestamp"
        assert exc_info.value.error_code == "FUTURE_SOURCE_TIMESTAMP"

    def test_no_provenance_accepted(self):
        """No provenance field is valid (optional)."""
        packet = PacketEnvelopeIn(
            packet_type="event",
            payload={"test": "data"},
        )
        # Should not raise
        PacketValidator.validate(packet)

    def test_empty_provenance_accepted(self):
        """Empty provenance dict is valid."""
        packet = PacketEnvelopeIn(
            packet_type="event",
            payload={"test": "data"},
            provenance={},
        )
        # Should not raise
        PacketValidator.validate(packet)

    def test_derive_type_none_treated_as_direct(self):
        """derive_type=None is valid (interpreted as 'direct')."""
        packet = PacketEnvelopeIn(
            packet_type="event",
            payload={"test": "data"},
            provenance={"derive_type": None},
        )
        # Should not raise
        PacketValidator.validate(packet)


class TestTTLValidation:
    """Test TTL validation."""

    def test_ttl_in_future_accepted(self):
        """TTL in the future is valid."""
        future_ttl = datetime.utcnow() + timedelta(days=7)
        packet = PacketEnvelopeIn(
            packet_type="event",
            payload={"test": "data"},
            ttl=future_ttl,
        )
        # Should not raise
        PacketValidator.validate(packet)

    def test_ttl_in_past_rejected(self):
        """TTL in the past raises PacketValidationError."""
        past_ttl = datetime.utcnow() - timedelta(hours=1)
        packet = PacketEnvelopeIn(
            packet_type="event",
            payload={"test": "data"},
            ttl=past_ttl,
        )
        with pytest.raises(PacketValidationError) as exc_info:
            PacketValidator.validate(packet)

        assert exc_info.value.field == "ttl"
        assert exc_info.value.error_code == "TTL_IN_PAST"


class TestPacketTypeValidation:
    """Test packet_type validation."""

    def test_core_packet_type_accepted(self):
        """Core packet types pass validation."""
        for packet_type in ["event", "memory_write", "reasoning_trace"]:
            packet = PacketEnvelopeIn(
                packet_type=packet_type,
                payload={"test": "data"},
            )
            # Should not raise
            PacketValidator.validate(packet)

    def test_unknown_packet_type_warns_in_non_strict(self):
        """Unknown packet_type logs warning but passes in non-strict mode."""
        packet = PacketEnvelopeIn(
            packet_type="unknown_custom_type",
            payload={"test": "data"},
        )
        # Should not raise (warns only)
        PacketValidator.validate(packet, strict=False)

    def test_unknown_packet_type_rejected_in_strict(self):
        """Unknown packet_type raises in strict mode."""
        packet = PacketEnvelopeIn(
            packet_type="unknown_custom_type",
            payload={"test": "data"},
        )
        with pytest.raises(PacketValidationError) as exc_info:
            PacketValidator.validate(packet, strict=True)

        assert exc_info.value.field == "packet_type"
        assert exc_info.value.error_code == "INVALID_PACKET_TYPE"


# =============================================================================
# Async Context Tests
# =============================================================================


@pytest.mark.asyncio
async def test_validator_callable_from_async_context():
    """Validator can be called from async functions without blocking."""
    packet = PacketEnvelopeIn(
        packet_type="event",
        payload={"async": "test"},
    )

    # Simulate async context
    PacketValidator.validate(packet)  # Should work fine (pure function)
    assert True  # Reached without error


@pytest.mark.asyncio
async def test_validation_error_propagates_in_async():
    """PacketValidationError propagates correctly in async context."""
    packet = PacketEnvelopeIn(
        packet_type="event",
        payload={"test": "data"},
        confidence={"score": 99.0},  # Invalid
    )

    with pytest.raises(PacketValidationError) as exc_info:
        PacketValidator.validate(packet)

    assert exc_info.value.error_code == "CONFIDENCE_OUT_OF_RANGE"


@pytest.mark.asyncio
async def test_provenance_validation_in_async():
    """Provenance validation works in async context."""
    packet = PacketEnvelopeIn(
        packet_type="event",
        payload={"test": "data"},
        provenance={"derive_type": "bad_value"},
    )

    with pytest.raises(PacketValidationError) as exc_info:
        PacketValidator.validate(packet)

    assert exc_info.value.error_code == "INVALID_DERIVE_TYPE"


# =============================================================================
# DeriveType Enum Tests
# =============================================================================


class TestDeriveTypeEnum:
    """Test DeriveType enum values."""

    def test_derive_type_values(self):
        """DeriveType enum has expected values."""
        assert DeriveType.DIRECT.value == "direct"
        assert DeriveType.INFERRED.value == "inferred"
        assert DeriveType.SYNTHESIZED.value == "synthesized"

    def test_valid_derive_types_set(self):
        """VALID_DERIVE_TYPES contains all enum values."""
        assert "direct" in VALID_DERIVE_TYPES
        assert "inferred" in VALID_DERIVE_TYPES
        assert "synthesized" in VALID_DERIVE_TYPES
        assert len(VALID_DERIVE_TYPES) == 3


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
