"""
Memory Ingestion Tests
======================

Tests for memory packet ingestion and retrieval.
"""

import pytest


@pytest.mark.asyncio
async def test_ingestion_roundtrip(memory_adapter):
    """
    Contract: Ingested packets can be retrieved by packet_id.
    """
    packet = await memory_adapter.ingest({"content": "hello"})
    out = await memory_adapter.retrieve(packet["packet_id"])
    assert out["content"] == "hello", f"Expected 'hello', got {out.get('content')}"


@pytest.mark.asyncio
async def test_ingestion_assigns_packet_id(memory_adapter):
    """
    Contract: Ingestion assigns a unique packet_id to each packet.
    """
    packet = await memory_adapter.ingest({"content": "test"})

    assert "packet_id" in packet, "Packet should have packet_id field"
    assert packet["packet_id"] is not None, (
        f"packet_id should not be None, got {packet.get('packet_id')}"
    )


@pytest.mark.asyncio
async def test_ingestion_assigns_timestamp(memory_adapter):
    """
    Contract: Ingestion assigns a timestamp to each packet.
    """
    packet = await memory_adapter.ingest({"content": "test"})

    assert "timestamp" in packet


@pytest.mark.asyncio
async def test_ingest_multiple_packets(memory_adapter):
    """
    Contract: Multiple packets can be ingested and each receives a unique packet_id.
    """
    packets = []

    for i in range(10):
        packet = await memory_adapter.ingest({"content": f"message {i}"})
        packets.append(packet)

    # All should have unique IDs
    ids = [p["packet_id"] for p in packets]
    assert len(set(ids)) == 10, f"Expected 10 unique packet IDs, got {len(set(ids))}"


@pytest.mark.asyncio
async def test_retrieve_nonexistent(memory_adapter):
    """
    Contract: Retrieving non-existent packet_id returns None.
    """
    result = await memory_adapter.retrieve("nonexistent-id")
    assert result is None, f"Expected None for nonexistent packet, got {result}"


@pytest.mark.asyncio
async def test_ingest_with_metadata(memory_adapter):
    """
    Contract: Packets with metadata preserve metadata on retrieval.
    """
    packet = await memory_adapter.ingest(
        {
            "content": "test",
            "metadata": {"source": "test", "priority": "high"},
        }
    )

    retrieved = await memory_adapter.retrieve(packet["packet_id"])
    assert retrieved["metadata"]["source"] == "test"


@pytest.mark.asyncio
async def test_ingest_preserves_data(memory_adapter):
    """
    Contract: All ingested data including nested structures is preserved on retrieval.
    """
    original = {
        "content": "test content",
        "tags": ["tag1", "tag2"],
        "nested": {"key": "value"},
    }

    packet = await memory_adapter.ingest(original)
    retrieved = await memory_adapter.retrieve(packet["packet_id"])

    assert retrieved["content"] == original["content"]
    assert retrieved["tags"] == original["tags"]
    assert retrieved["nested"] == original["nested"]


@pytest.mark.asyncio
async def test_ingest_empty_payload(memory_adapter):
    """
    Contract: Empty payload is handled gracefully.
    """
    packet = await memory_adapter.ingest({})

    assert "packet_id" in packet
    retrieved = await memory_adapter.retrieve(packet["packet_id"])
    assert retrieved is not None


@pytest.mark.asyncio
async def test_ingest_oversized_payload(memory_adapter):
    """
    Contract: Oversized payload triggers appropriate handling.
    """
    # Create a large payload (simulate oversized)
    large_content = "x" * (10 * 1024 * 1024)  # 10MB

    packet = await memory_adapter.ingest({"content": large_content})

    assert "packet_id" in packet
    retrieved = await memory_adapter.retrieve(packet["packet_id"])
    assert retrieved is not None
    assert len(retrieved["content"]) == len(large_content)


@pytest.mark.asyncio
async def test_ingest_null_fields(memory_adapter):
    """
    Contract: Null fields in payload handled correctly.
    """
    packet = await memory_adapter.ingest(
        {
            "content": "test",
            "optional_field": None,
            "nested": {"key": None},
        }
    )

    retrieved = await memory_adapter.retrieve(packet["packet_id"])
    assert retrieved["content"] == "test"
    assert retrieved["optional_field"] is None
    assert retrieved["nested"]["key"] is None
