"""
Test Content Hash Integrity (SHA-256)

GMP: ADD_CONTENT_HASH_INTEGRITY
Phase: 4 (VALIDATE)

Verifies:
- Content hash computation is deterministic
- Hash covers payload, metadata, timestamp
- Tamper detection works correctly
- Upcasted packets get content hash computed
- Hash verification API works
"""

import hashlib
import json
from datetime import datetime
from uuid import uuid4

import pytest

from core.schemas import (
    PacketEnvelope,
    PacketMetadata,
)
from core.schemas.schema_registry import upcast


class TestContentHashComputation:
    """Test content hash computation."""

    def test_compute_content_hash_deterministic(self):
        """Same packet produces same hash every time."""
        packet = PacketEnvelope(
            packet_type="test",
            payload={"key": "value", "nested": {"a": 1}},
            timestamp=datetime(2024, 1, 1, 12, 0, 0),
        )

        hash1 = packet.compute_content_hash()
        hash2 = packet.compute_content_hash()

        assert hash1 == hash2
        assert len(hash1) == 64  # SHA-256 hex length

    def test_different_payloads_different_hashes(self):
        """Different payloads produce different hashes."""
        timestamp = datetime(2024, 1, 1, 12, 0, 0)
        
        packet1 = PacketEnvelope(
            packet_type="test",
            payload={"data": "value1"},
            timestamp=timestamp,
        )
        packet2 = PacketEnvelope(
            packet_type="test",
            payload={"data": "value2"},
            timestamp=timestamp,
        )

        hash1 = packet1.compute_content_hash()
        hash2 = packet2.compute_content_hash()

        assert hash1 != hash2

    def test_different_metadata_different_hashes(self):
        """Different metadata produces different hashes."""
        timestamp = datetime(2024, 1, 1, 12, 0, 0)
        payload = {"data": "value"}
        
        packet1 = PacketEnvelope(
            packet_type="test",
            payload=payload,
            timestamp=timestamp,
            metadata=PacketMetadata(agent="agent1"),
        )
        packet2 = PacketEnvelope(
            packet_type="test",
            payload=payload,
            timestamp=timestamp,
            metadata=PacketMetadata(agent="agent2"),
        )

        hash1 = packet1.compute_content_hash()
        hash2 = packet2.compute_content_hash()

        assert hash1 != hash2

    def test_different_timestamps_different_hashes(self):
        """Different timestamps produce different hashes."""
        payload = {"data": "value"}
        
        packet1 = PacketEnvelope(
            packet_type="test",
            payload=payload,
            timestamp=datetime(2024, 1, 1, 12, 0, 0),
        )
        packet2 = PacketEnvelope(
            packet_type="test",
            payload=payload,
            timestamp=datetime(2024, 1, 1, 12, 0, 1),  # 1 second later
        )

        hash1 = packet1.compute_content_hash()
        hash2 = packet2.compute_content_hash()

        assert hash1 != hash2


class TestWithContentHash:
    """Test with_content_hash() method."""

    def test_with_content_hash_sets_field(self):
        """with_content_hash() creates new packet with hash set."""
        packet = PacketEnvelope(
            packet_type="test",
            payload={"data": "value"},
        )

        assert packet.content_hash is None

        hashed = packet.with_content_hash()

        assert hashed.content_hash is not None
        assert len(hashed.content_hash) == 64

    def test_with_content_hash_preserves_original(self):
        """with_content_hash() doesn't modify original (immutability)."""
        packet = PacketEnvelope(
            packet_type="test",
            payload={"data": "value"},
        )

        hashed = packet.with_content_hash()

        # Original unchanged
        assert packet.content_hash is None
        # New packet has hash
        assert hashed.content_hash is not None

    def test_with_content_hash_hash_matches_computed(self):
        """with_content_hash() hash matches compute_content_hash()."""
        packet = PacketEnvelope(
            packet_type="test",
            payload={"data": "value"},
            timestamp=datetime(2024, 1, 1, 12, 0, 0),
        )

        hashed = packet.with_content_hash()

        # The stored hash should match what we compute manually
        # Note: The hashed packet has a different packet_id, but
        # hash is based on payload/metadata/timestamp which are preserved
        expected_hash = packet.compute_content_hash()
        assert hashed.content_hash == expected_hash


class TestVerifyIntegrity:
    """Test integrity verification."""

    def test_verify_integrity_valid_packet(self):
        """Valid packet with correct hash passes verification."""
        packet = PacketEnvelope(
            packet_type="test",
            payload={"data": "value"},
            timestamp=datetime(2024, 1, 1, 12, 0, 0),
        )

        hashed = packet.with_content_hash()

        assert hashed.verify_integrity() is True

    def test_verify_integrity_no_hash_returns_false(self):
        """Packet without content_hash fails verification."""
        packet = PacketEnvelope(
            packet_type="test",
            payload={"data": "value"},
        )

        assert packet.content_hash is None
        assert packet.verify_integrity() is False

    def test_verify_integrity_wrong_hash_returns_false(self):
        """Packet with incorrect hash fails verification."""
        packet = PacketEnvelope(
            packet_type="test",
            payload={"data": "value"},
            content_hash="wrong_hash_value",
        )

        assert packet.verify_integrity() is False


class TestUpcastingWithContentHash:
    """Test that upcasting adds content hash."""

    def test_upcast_v1_0_0_adds_content_hash(self):
        """Upcasting from v1.0.0 to v2.0.0 computes content hash."""
        raw = {
            "packet_id": str(uuid4()),
            "packet_type": "event",
            "payload": {"data": "test"},
            "timestamp": datetime.utcnow().isoformat(),
        }

        result = upcast(raw, "2.0.0")

        assert "content_hash" in result
        assert result["content_hash"] is not None
        assert len(result["content_hash"]) == 64

    def test_upcast_content_hash_is_valid(self):
        """Upcasted content hash can be verified."""
        raw = {
            "packet_type": "event",
            "payload": {"data": "test"},
            "timestamp": datetime(2024, 1, 1, 12, 0, 0).isoformat(),
        }

        result = upcast(raw, "2.0.0")

        # Verify by recomputing
        content = {
            "payload": result["payload"],
            "metadata": result["metadata"],
            "timestamp": result["timestamp"],
        }
        content_bytes = json.dumps(content, sort_keys=True, default=str).encode("utf-8")
        expected_hash = hashlib.sha256(content_bytes).hexdigest()

        assert result["content_hash"] == expected_hash


class TestHashAlgorithmProperties:
    """Test properties of the hashing algorithm."""

    def test_hash_is_sha256(self):
        """Content hash uses SHA-256."""
        packet = PacketEnvelope(
            packet_type="test",
            payload={"data": "value"},
        )

        content_hash = packet.compute_content_hash()

        # SHA-256 produces 64 hex characters (256 bits = 32 bytes = 64 hex)
        assert len(content_hash) == 64
        # All characters should be valid hex
        assert all(c in "0123456789abcdef" for c in content_hash)

    def test_hash_is_collision_resistant(self):
        """Different similar payloads produce different hashes (no collisions)."""
        hashes = set()
        timestamp = datetime(2024, 1, 1, 12, 0, 0)

        for i in range(100):
            packet = PacketEnvelope(
                packet_type="test",
                payload={"index": i},
                timestamp=timestamp,
            )
            h = packet.compute_content_hash()
            hashes.add(h)

        # All 100 hashes should be unique
        assert len(hashes) == 100


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

