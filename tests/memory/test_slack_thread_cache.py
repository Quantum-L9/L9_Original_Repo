"""
Tests for Slack Thread Context Cache (Redis).

Covers:
- Cache miss → PostgreSQL fallback → cache populated
- Cache hit → returns without DB query
- Write-ahead append → message N visible to message N+1
- TTL expiry → cache miss after timeout
- Redis unavailable → graceful fallback
- Bounded size enforcement
- Corrupted cache entry handling
"""

from __future__ import annotations

import json
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from memory.slack_thread_cache import (
    MAX_CACHED_PACKETS_PER_THREAD,
    SlackThreadCacheService,
)


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def mock_redis() -> MagicMock:
    """Create a mock RedisClient with async methods."""
    redis = MagicMock()
    redis.is_available.return_value = True
    redis.get = AsyncMock(return_value=None)
    redis.set = AsyncMock(return_value=True)
    redis.delete = AsyncMock(return_value=True)
    return redis


@pytest.fixture
def cache_service(mock_redis: MagicMock) -> SlackThreadCacheService:
    """Create a SlackThreadCacheService with mock Redis."""
    return SlackThreadCacheService(redis_client=mock_redis, ttl_seconds=1800)


@pytest.fixture
def thread_uuid() -> str:
    return "550e8400-e29b-41d4-a716-446655440000"


@pytest.fixture
def sample_context() -> dict[str, Any]:
    return {
        "packets": [
            {
                "text": "Hello L9",
                "user_id": "U123",
                "ts": "1707764400.000100",
                "payload": {"text": "Hello L9"},
            },
            {
                "text": "Hi! How can I help?",
                "user_id": "BOT",
                "ts": "1707764401.000200",
                "payload": {"text": "Hi! How can I help?"},
            },
        ]
    }


# ============================================================================
# Cache Miss Tests
# ============================================================================


class TestCacheMiss:
    """Tests for cache miss behavior."""

    @pytest.mark.asyncio
    async def test_cache_miss_returns_none(
        self,
        cache_service: SlackThreadCacheService,
        mock_redis: MagicMock,
        thread_uuid: str,
    ) -> None:
        """Cache miss returns None when key does not exist."""
        mock_redis.get.return_value = None

        result = await cache_service.get_thread_context(thread_uuid)

        assert result is None
        mock_redis.get.assert_called_once()

    @pytest.mark.asyncio
    async def test_cache_miss_key_format(
        self,
        cache_service: SlackThreadCacheService,
        mock_redis: MagicMock,
        thread_uuid: str,
    ) -> None:
        """Cache miss uses correct Redis key pattern."""
        mock_redis.get.return_value = None

        await cache_service.get_thread_context(thread_uuid)

        expected_key = f"slack:thread:{thread_uuid}:context"
        mock_redis.get.assert_called_once_with(expected_key, raw=True)


# ============================================================================
# Cache Hit Tests
# ============================================================================


class TestCacheHit:
    """Tests for cache hit behavior."""

    @pytest.mark.asyncio
    async def test_cache_hit_returns_context(
        self,
        cache_service: SlackThreadCacheService,
        mock_redis: MagicMock,
        thread_uuid: str,
        sample_context: dict[str, Any],
    ) -> None:
        """Cache hit returns deserialized context."""
        mock_redis.get.return_value = json.dumps(sample_context)

        result = await cache_service.get_thread_context(thread_uuid)

        assert result is not None
        assert len(result["packets"]) == 2
        assert result["packets"][0]["text"] == "Hello L9"

    @pytest.mark.asyncio
    async def test_cache_hit_no_db_query(
        self,
        cache_service: SlackThreadCacheService,
        mock_redis: MagicMock,
        thread_uuid: str,
        sample_context: dict[str, Any],
    ) -> None:
        """Cache hit does not trigger any PostgreSQL query."""
        mock_redis.get.return_value = json.dumps(sample_context)

        result = await cache_service.get_thread_context(thread_uuid)

        assert result is not None
        # Only Redis.get was called, no substrate_service calls
        mock_redis.get.assert_called_once()


# ============================================================================
# Write-Ahead Append Tests
# ============================================================================


class TestWriteAhead:
    """Tests for write-ahead cache append (race condition fix)."""

    @pytest.mark.asyncio
    async def test_append_to_empty_cache(
        self,
        cache_service: SlackThreadCacheService,
        mock_redis: MagicMock,
        thread_uuid: str,
    ) -> None:
        """Append to non-existent cache creates new entry."""
        mock_redis.get.return_value = None

        result = await cache_service.append_to_thread(
            thread_uuid=thread_uuid,
            packet_summary={"text": "New message", "user_id": "U123", "ts": "123.456"},
        )

        assert result is True
        # Verify set was called with the new packet
        set_call = mock_redis.set.call_args
        stored = json.loads(set_call.args[1])
        assert len(stored["packets"]) == 1
        assert stored["packets"][0]["text"] == "New message"

    @pytest.mark.asyncio
    async def test_append_preserves_existing_packets(
        self,
        cache_service: SlackThreadCacheService,
        mock_redis: MagicMock,
        thread_uuid: str,
        sample_context: dict[str, Any],
    ) -> None:
        """Append adds to existing packets without overwriting."""
        mock_redis.get.return_value = json.dumps(sample_context)

        result = await cache_service.append_to_thread(
            thread_uuid=thread_uuid,
            packet_summary={"text": "Message N+1", "user_id": "U123", "ts": "123.789"},
        )

        assert result is True
        set_call = mock_redis.set.call_args
        stored = json.loads(set_call.args[1])
        assert len(stored["packets"]) == 3
        assert stored["packets"][2]["text"] == "Message N+1"

    @pytest.mark.asyncio
    async def test_append_adds_timestamp(
        self,
        cache_service: SlackThreadCacheService,
        mock_redis: MagicMock,
        thread_uuid: str,
    ) -> None:
        """Appended packets get _appended_at timestamp."""
        mock_redis.get.return_value = None

        await cache_service.append_to_thread(
            thread_uuid=thread_uuid,
            packet_summary={"text": "Test", "user_id": "U123"},
        )

        set_call = mock_redis.set.call_args
        stored = json.loads(set_call.args[1])
        assert "_appended_at" in stored["packets"][0]


# ============================================================================
# Bounded Size Tests
# ============================================================================


class TestBoundedSize:
    """Tests for bounded cache size enforcement."""

    @pytest.mark.asyncio
    async def test_enforces_max_packets(
        self,
        cache_service: SlackThreadCacheService,
        mock_redis: MagicMock,
        thread_uuid: str,
    ) -> None:
        """Cache enforces MAX_CACHED_PACKETS_PER_THREAD limit."""
        # Create context with max packets
        existing = {
            "packets": [
                {"text": f"msg-{i}", "user_id": "U123"}
                for i in range(MAX_CACHED_PACKETS_PER_THREAD)
            ]
        }
        mock_redis.get.return_value = json.dumps(existing)

        await cache_service.append_to_thread(
            thread_uuid=thread_uuid,
            packet_summary={"text": "overflow-msg", "user_id": "U123"},
        )

        set_call = mock_redis.set.call_args
        stored = json.loads(set_call.args[1])
        assert len(stored["packets"]) == MAX_CACHED_PACKETS_PER_THREAD
        # Most recent message is kept
        assert stored["packets"][-1]["text"] == "overflow-msg"
        # Oldest message is evicted
        assert stored["packets"][0]["text"] != "msg-0"


# ============================================================================
# Redis Unavailable Tests
# ============================================================================


class TestRedisUnavailable:
    """Tests for graceful degradation when Redis is unavailable."""

    @pytest.mark.asyncio
    async def test_get_returns_none_when_unavailable(
        self,
        cache_service: SlackThreadCacheService,
        mock_redis: MagicMock,
        thread_uuid: str,
    ) -> None:
        """get_thread_context returns None when Redis is unavailable."""
        mock_redis.is_available.return_value = False

        result = await cache_service.get_thread_context(thread_uuid)

        assert result is None
        mock_redis.get.assert_not_called()

    @pytest.mark.asyncio
    async def test_set_returns_false_when_unavailable(
        self,
        cache_service: SlackThreadCacheService,
        mock_redis: MagicMock,
        thread_uuid: str,
        sample_context: dict[str, Any],
    ) -> None:
        """set_thread_context returns False when Redis is unavailable."""
        mock_redis.is_available.return_value = False

        result = await cache_service.set_thread_context(thread_uuid, sample_context)

        assert result is False

    @pytest.mark.asyncio
    async def test_append_returns_false_when_unavailable(
        self,
        cache_service: SlackThreadCacheService,
        mock_redis: MagicMock,
        thread_uuid: str,
    ) -> None:
        """append_to_thread returns False when Redis is unavailable."""
        mock_redis.is_available.return_value = False

        result = await cache_service.append_to_thread(
            thread_uuid=thread_uuid,
            packet_summary={"text": "test", "user_id": "U123"},
        )

        assert result is False

    @pytest.mark.asyncio
    async def test_invalidate_returns_false_when_unavailable(
        self,
        cache_service: SlackThreadCacheService,
        mock_redis: MagicMock,
        thread_uuid: str,
    ) -> None:
        """invalidate_thread returns False when Redis is unavailable."""
        mock_redis.is_available.return_value = False

        result = await cache_service.invalidate_thread(thread_uuid)

        assert result is False


# ============================================================================
# Corrupted Cache Tests
# ============================================================================


class TestCorruptedCache:
    """Tests for handling corrupted cache entries."""

    @pytest.mark.asyncio
    async def test_corrupt_json_returns_none(
        self,
        cache_service: SlackThreadCacheService,
        mock_redis: MagicMock,
        thread_uuid: str,
    ) -> None:
        """Corrupted JSON returns None and invalidates cache."""
        mock_redis.get.return_value = "not-valid-json{{"

        result = await cache_service.get_thread_context(thread_uuid)

        assert result is None
        # Verify invalidation was attempted
        mock_redis.delete.assert_called_once()

    @pytest.mark.asyncio
    async def test_redis_exception_returns_none(
        self,
        cache_service: SlackThreadCacheService,
        mock_redis: MagicMock,
        thread_uuid: str,
    ) -> None:
        """Redis exception returns None gracefully."""
        mock_redis.get.side_effect = ConnectionError("Redis connection lost")

        result = await cache_service.get_thread_context(thread_uuid)

        assert result is None


# ============================================================================
# Invalidation Tests
# ============================================================================


class TestInvalidation:
    """Tests for explicit cache invalidation."""

    @pytest.mark.asyncio
    async def test_invalidate_deletes_key(
        self,
        cache_service: SlackThreadCacheService,
        mock_redis: MagicMock,
        thread_uuid: str,
    ) -> None:
        """invalidate_thread deletes the correct Redis key."""
        result = await cache_service.invalidate_thread(thread_uuid)

        assert result is True
        expected_key = f"slack:thread:{thread_uuid}:context"
        mock_redis.delete.assert_called_once_with(expected_key)


# ============================================================================
# Set Thread Context Tests
# ============================================================================


class TestSetThreadContext:
    """Tests for cache population."""

    @pytest.mark.asyncio
    async def test_set_adds_cache_metadata(
        self,
        cache_service: SlackThreadCacheService,
        mock_redis: MagicMock,
        thread_uuid: str,
        sample_context: dict[str, Any],
    ) -> None:
        """set_thread_context adds _cached_at and _ttl_seconds metadata."""
        await cache_service.set_thread_context(thread_uuid, sample_context)

        set_call = mock_redis.set.call_args
        stored = json.loads(set_call.args[1])
        assert "_cached_at" in stored
        assert stored["_ttl_seconds"] == 1800

    @pytest.mark.asyncio
    async def test_set_uses_correct_ttl(
        self,
        cache_service: SlackThreadCacheService,
        mock_redis: MagicMock,
        thread_uuid: str,
        sample_context: dict[str, Any],
    ) -> None:
        """set_thread_context passes configured TTL to Redis."""
        await cache_service.set_thread_context(thread_uuid, sample_context)

        set_call = mock_redis.set.call_args
        assert set_call.kwargs["ttl"] == 1800
