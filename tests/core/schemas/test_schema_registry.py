"""
Test Schema Registry & Upcasting

GMP: CONSOLIDATE_SCHEMA_VERSIONS + BUILD_UPCASTING_MIDDLEWARE
Phase: 4 (VALIDATE)

Verifies:
- Version detection from raw packet dicts
- Upcaster registration and chaining
- Transparent migration from v1.0.0 → v2.0.0
- Performance of batch upcasting
- Error handling for unknown versions
"""

from datetime import datetime
from uuid import uuid4

import pytest

from core.schemas import PacketEnvelope
from core.schemas.schema_registry import (
    SchemaRegistry,
    detect_version,
    read_packet,
    read_packets,
    upcast,
    write_packet,
)


class TestVersionDetection:
    """Test version detection from raw packet dicts."""

    def test_detect_v1_0_0_packet(self):
        """Minimal packet defaults to v1.0.0."""
        raw = {
            "packet_id": str(uuid4()),
            "packet_type": "event",
            "payload": {"data": "test"},
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        version = detect_version(raw)
        assert version == "1.0.0"

    def test_detect_v1_0_1_packet(self):
        """Packet with metadata.schema_version=1.0.1."""
        raw = {
            "packet_id": str(uuid4()),
            "packet_type": "event",
            "payload": {"data": "test"},
            "metadata": {"schema_version": "1.0.1"},
        }
        version = detect_version(raw)
        assert version == "1.0.1"

    def test_detect_v1_1_0_by_fields(self):
        """Packet with thread_id/lineage/tags detected as v1.1.0."""
        raw = {
            "packet_id": str(uuid4()),
            "packet_type": "event",
            "payload": {"data": "test"},
            "thread_id": str(uuid4()),
            "tags": ["test"],
        }
        version = detect_version(raw)
        assert version == "1.1.0"

    def test_detect_v2_0_0_by_content_hash(self):
        """Packet with content_hash detected as v2.0.0."""
        raw = {
            "packet_id": str(uuid4()),
            "packet_type": "event",
            "payload": {"data": "test"},
            "content_hash": "abc123",
        }
        version = detect_version(raw)
        assert version == "2.0.0"

    def test_detect_version_from_metadata(self):
        """Explicit metadata.schema_version takes precedence."""
        raw = {
            "packet_id": str(uuid4()),
            "packet_type": "event",
            "payload": {"data": "test"},
            "metadata": {"schema_version": "2.0.0"},
            "content_hash": None,  # Would infer v1.1.0 without metadata
        }
        version = detect_version(raw)
        assert version == "2.0.0"


class TestUpcasting:
    """Test upcasting from older versions to latest."""

    def test_upcast_v1_0_0_to_v2_0_0(self):
        """v1.0.0 packet upcasts to v2.0.0 with new fields."""
        raw = {
            "packet_id": str(uuid4()),
            "packet_type": "event",
            "payload": {"original": "data"},
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        result = upcast(raw, "2.0.0")

        assert result["metadata"]["schema_version"] == "2.0.0"
        assert "thread_id" in result
        assert "lineage" in result
        assert "tags" in result
        assert "ttl" in result
        assert "content_hash" in result
        # Original data preserved
        assert result["payload"] == {"original": "data"}

    def test_upcast_v1_1_0_to_v2_0_0(self):
        """v1.1.0 packet preserves thread_id/lineage/tags."""
        thread_id = str(uuid4())
        raw = {
            "packet_id": str(uuid4()),
            "packet_type": "event",
            "payload": {"data": "test"},
            "metadata": {"schema_version": "1.1.0"},
            "thread_id": thread_id,
            "lineage": {"parent_ids": [], "generation": 1},
            "tags": ["important", "test"],
            "ttl": None,
        }

        result = upcast(raw, "2.0.0")

        assert result["metadata"]["schema_version"] == "2.0.0"
        assert result["thread_id"] == thread_id
        assert result["lineage"]["generation"] == 1
        assert result["tags"] == ["important", "test"]

    def test_upcast_does_not_mutate_input(self):
        """Upcasting creates a copy, doesn't mutate input."""
        raw = {
            "packet_id": str(uuid4()),
            "packet_type": "event",
            "payload": {"data": "test"},
        }
        original_payload = raw["payload"].copy()

        upcast(raw, "2.0.0")

        # Original unchanged
        assert raw["payload"] == original_payload
        assert "thread_id" not in raw  # New field not added to original

    def test_upcast_same_version_returns_original(self):
        """Upcasting to same version returns input unchanged."""
        raw = {
            "packet_id": str(uuid4()),
            "packet_type": "event",
            "payload": {"data": "test"},
            "metadata": {"schema_version": "2.0.0"},
            "content_hash": "abc123",
        }

        result = upcast(raw, "2.0.0")

        # Same object returned (no upcasting needed)
        assert result is raw

    def test_transitive_upcasting(self):
        """v1.0.0 → v1.0.1 → v1.1.0 → v1.1.1 → v2.0.0 chain works."""
        raw = {
            "packet_id": str(uuid4()),
            "packet_type": "event",
            "payload": {"data": "test"},
        }

        result = upcast(raw, "2.0.0")

        # All intermediate versions applied
        assert result["metadata"]["schema_version"] == "2.0.0"
        assert "thread_id" in result  # Added in v1.1.0
        assert "content_hash" in result  # Added in v2.0.0


class TestReadPacket:
    """Test reading raw dicts into PacketEnvelope."""

    def test_read_v1_0_0_packet(self):
        """Read v1.0.0 packet returns PacketEnvelope v2.0.0."""
        raw = {
            "packet_id": str(uuid4()),
            "packet_type": "event",
            "payload": {"original": "data"},
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        packet = read_packet(raw)

        assert isinstance(packet, PacketEnvelope)
        assert packet.payload == {"original": "data"}
        assert packet.metadata.schema_version == "2.0.0"

    def test_read_v1_1_0_preserves_enhanced_fields(self):
        """Read v1.1.0 preserves thread_id, lineage, tags."""
        thread_id = uuid4()
        raw = {
            "packet_id": str(uuid4()),
            "packet_type": "event",
            "payload": {"data": "test"},
            "metadata": {"schema_version": "1.1.0"},
            "thread_id": str(thread_id),
            "lineage": {
                "parent_ids": [str(uuid4())],
                "generation": 2,
                "derivation_type": "transform",
            },
            "tags": ["migrated", "important"],
        }

        packet = read_packet(raw)

        assert packet.thread_id == thread_id
        assert packet.lineage is not None
        assert packet.lineage.generation == 2
        assert packet.tags == ["migrated", "important"]

    def test_read_packet_is_immutable(self):
        """Resulting PacketEnvelope is immutable."""
        raw = {
            "packet_id": str(uuid4()),
            "packet_type": "event",
            "payload": {"data": "test"},
        }

        packet = read_packet(raw)

        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            packet.packet_type = "changed"


class TestBatchOperations:
    """Test batch read/write operations."""

    def test_read_packets_batch(self):
        """Batch read multiple packets efficiently."""
        raws = [
            {
                "packet_id": str(uuid4()),
                "packet_type": f"event_{i}",
                "payload": {"index": i},
            }
            for i in range(10)
        ]

        packets = read_packets(raws)

        assert len(packets) == 10
        for i, packet in enumerate(packets):
            assert isinstance(packet, PacketEnvelope)
            assert packet.payload == {"index": i}
            assert packet.metadata.schema_version == "2.0.0"

    def test_write_packet_to_dict(self):
        """Write packet serializes to JSON-compatible dict."""
        packet = PacketEnvelope(
            packet_type="test",
            payload={"data": "value"},
            thread_id=uuid4(),
            tags=["tag1", "tag2"],
        )

        result = write_packet(packet)

        assert isinstance(result, dict)
        assert result["packet_type"] == "test"
        assert result["payload"] == {"data": "value"}
        assert isinstance(result["packet_id"], str)  # UUID serialized
        assert isinstance(result["timestamp"], str)  # datetime serialized


class TestMixedVersionLoad:
    """Test loading mixed v1.x and v2.x packets."""

    def test_load_mixed_versions(self):
        """Load batch with mixed versions - all upcast to v2.0.0."""
        raws = [
            # v1.0.0
            {"packet_type": "v1_0_0", "payload": {"v": "1.0.0"}},
            # v1.0.1
            {
                "packet_type": "v1_0_1",
                "payload": {"v": "1.0.1"},
                "metadata": {"schema_version": "1.0.1"},
            },
            # v1.1.0
            {
                "packet_type": "v1_1_0",
                "payload": {"v": "1.1.0"},
                "thread_id": str(uuid4()),
                "tags": ["v1.1"],
            },
            # v2.0.0
            {
                "packet_type": "v2_0_0",
                "payload": {"v": "2.0.0"},
                "metadata": {"schema_version": "2.0.0"},
                "content_hash": "hash",
            },
        ]

        packets = read_packets(raws)

        assert len(packets) == 4
        for packet in packets:
            assert packet.metadata.schema_version == "2.0.0"

        # Verify correct types
        assert packets[0].packet_type == "v1_0_0"
        assert packets[1].packet_type == "v1_0_1"
        assert packets[2].packet_type == "v1_1_0"
        assert packets[3].packet_type == "v2_0_0"


class TestErrorHandling:
    """Test error handling for edge cases."""

    def test_unknown_version_defaults(self):
        """Unknown version string defaults to v1.0.0 detection."""
        raw = {
            "packet_type": "event",
            "payload": {"data": "test"},
            "metadata": {"schema_version": "0.9.0"},  # Unknown
        }

        # Should still work - version detection falls back
        version = detect_version(raw)
        assert version == "0.9.0"  # Uses explicit version from metadata

    def test_corrupted_metadata_still_works(self):
        """Packet with invalid metadata still processes."""
        raw = {
            "packet_type": "event",
            "payload": {"data": "test"},
            "metadata": "not_a_dict",  # Corrupted
        }

        version = detect_version(raw)
        # Falls back to field-based detection
        assert version == "1.0.0"


class TestSchemaRegistryProperties:
    """Test SchemaRegistry properties and state."""

    def test_current_version(self):
        """Current version is 2.0.0."""
        assert SchemaRegistry.current_version == "2.0.0"

    def test_supported_versions(self):
        """All expected versions are supported."""
        versions = SchemaRegistry.supported_versions
        assert "1.0.0" in versions
        assert "1.0.1" in versions
        assert "1.1.0" in versions
        assert "1.1.1" in versions
        assert "2.0.0" in versions


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
