"""
Tests for substrate-backed idempotency in agent executor.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
import json
import hashlib

from core.agents.idempotency_store import IdempotencyStore
from core.schemas.packet_envelope import PacketEnvelope, PacketProvenance


@pytest.fixture
def mock_substrate():
    """Mock substrate service with Redis."""
    substrate = MagicMock()
    redis = AsyncMock()
    substrate.get_redis_client = AsyncMock(return_value=redis)
    return substrate, redis


@pytest.fixture
def sample_packet():
    """Create sample packet for testing."""
    return PacketEnvelope(
        packet_type="task.execute",
        payload={"action": "process", "value": 42},
        provenance=PacketProvenance(source_agent="agent-1"),
    )


@pytest.mark.asyncio
async def test_idempotency_check_not_executed(mock_substrate, sample_packet):
    """Test idempotency check for task that hasn't been executed."""
    substrate, redis = mock_substrate
    redis.exists = AsyncMock(return_value=False)

    store = IdempotencyStore(substrate)
    result = await store.check_executed(sample_packet)

    assert result is False
    redis.exists.assert_called_once()


@pytest.mark.asyncio
async def test_idempotency_check_already_executed(mock_substrate, sample_packet):
    """Test idempotency check for previously executed task."""
    substrate, redis = mock_substrate
    redis.exists = AsyncMock(return_value=True)

    store = IdempotencyStore(substrate)
    result = await store.check_executed(sample_packet)

    assert result is True
    redis.exists.assert_called_once()


@pytest.mark.asyncio
async def test_idempotency_mark_executed(mock_substrate, sample_packet):
    """Test marking task as executed."""
    substrate, redis = mock_substrate
    redis.setex = AsyncMock()

    store = IdempotencyStore(substrate)
    result = {"timestamp": "2026-01-29T12:00:00Z", "status": "success"}

    await store.mark_executed(sample_packet, result)

    redis.setex.assert_called_once()
    call_args = redis.setex.call_args
    assert call_args[0][0].startswith("l9:idempotency:")
    assert call_args[0][1] == store.ttl

    # Verify stored data contains execution info
    stored_data = json.loads(call_args[0][2])
    assert stored_data["status"] == "success"
    assert "packet_id" in stored_data  # UUID string


@pytest.mark.asyncio
async def test_idempotency_get_execution_record(mock_substrate, sample_packet):
    """Test retrieving execution record."""
    substrate, redis = mock_substrate

    record = {
        "executed_at": "2026-01-29T12:00:00Z",
        "status": "success",
        "packet_id": "test-123",
    }
    redis.get = AsyncMock(return_value=json.dumps(record))

    store = IdempotencyStore(substrate)
    result = await store.get_execution_record(sample_packet)

    assert result == record
    redis.get.assert_called_once()


@pytest.mark.asyncio
async def test_idempotency_key_computation(mock_substrate, sample_packet):
    """Test deterministic idempotency key generation."""
    substrate, _ = mock_substrate

    store = IdempotencyStore(substrate)
    key1 = store._compute_key(sample_packet)
    key2 = store._compute_key(sample_packet)

    # Same packet should produce same key
    assert key1 == key2

    # Key should be prefixed and contain hash
    assert key1.startswith("l9:idempotency:")
    assert len(key1) > len("l9:idempotency:")


@pytest.mark.asyncio
async def test_idempotency_different_packets_different_keys(
    mock_substrate, sample_packet
):
    """Test that different packets produce different keys."""
    substrate, _ = mock_substrate

    packet2 = PacketEnvelope(
        packet_type="task.execute",
        payload={"action": "process", "value": 99},  # Different payload
        provenance=PacketProvenance(source_agent="agent-1"),
    )

    store = IdempotencyStore(substrate)
    key1 = store._compute_key(sample_packet)
    key2 = store._compute_key(packet2)

    assert key1 != key2


@pytest.mark.asyncio
async def test_idempotency_graceful_degradation(mock_substrate, sample_packet):
    """Test graceful degradation when Redis fails."""
    substrate, redis = mock_substrate
    redis.exists = AsyncMock(side_effect=Exception("Redis connection failed"))

    store = IdempotencyStore(substrate)

    # Should return False (not executed) on error to be safe
    result = await store.check_executed(sample_packet)
    assert result is False
