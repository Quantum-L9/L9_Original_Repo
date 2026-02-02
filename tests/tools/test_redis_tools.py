"""
Unit Tests: Redis Tools
=======================

Tests for Redis cache and queue tools.

Version: 1.0.0
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestRedisGet:
    """Tests for redis_get tool."""

    @pytest.mark.asyncio
    async def test_redis_get_existing_key(self):
        """redis_get returns value for existing key."""
        from runtime.redis_tools import redis_get

        mock_redis = MagicMock()
        mock_redis.is_available.return_value = True
        mock_redis.get = AsyncMock(return_value="test_value")

        with patch(
            "runtime.redis_client.get_redis_client", AsyncMock(return_value=mock_redis)
        ):
            result = await redis_get(key="test_key")

        assert result["status"] == "success"
        assert result["key"] == "test_key"
        assert result["value"] == "test_value"
        assert result["exists"] is True

    @pytest.mark.asyncio
    async def test_redis_get_missing_key(self):
        """redis_get returns None for missing key."""
        from runtime.redis_tools import redis_get

        mock_redis = MagicMock()
        mock_redis.is_available.return_value = True
        mock_redis.get = AsyncMock(return_value=None)

        with patch(
            "runtime.redis_client.get_redis_client", AsyncMock(return_value=mock_redis)
        ):
            result = await redis_get(key="missing_key")

        assert result["status"] == "success"
        assert result["value"] is None
        assert result["exists"] is False

    @pytest.mark.asyncio
    async def test_redis_get_unavailable(self):
        """redis_get returns error when Redis unavailable."""
        from runtime.redis_tools import redis_get

        mock_redis = MagicMock()
        mock_redis.is_available.return_value = False

        with patch(
            "runtime.redis_client.get_redis_client", AsyncMock(return_value=mock_redis)
        ):
            result = await redis_get(key="any_key")

        assert result["status"] == "error"
        assert "not available" in result["error"]


class TestRedisSet:
    """Tests for redis_set tool."""

    @pytest.mark.asyncio
    async def test_redis_set_without_ttl(self):
        """redis_set stores value without TTL."""
        from runtime.redis_tools import redis_set

        mock_redis = MagicMock()
        mock_redis.is_available.return_value = True
        mock_redis.set = AsyncMock()

        with patch(
            "runtime.redis_client.get_redis_client", AsyncMock(return_value=mock_redis)
        ):
            result = await redis_set(key="test_key", value="test_value")

        assert result["status"] == "success"
        mock_redis.set.assert_called_once_with("test_key", "test_value", ex=None)

    @pytest.mark.asyncio
    async def test_redis_set_with_ttl(self):
        """redis_set stores value with TTL."""
        from runtime.redis_tools import redis_set

        mock_redis = MagicMock()
        mock_redis.is_available.return_value = True
        mock_redis.set = AsyncMock()

        with patch(
            "runtime.redis_client.get_redis_client", AsyncMock(return_value=mock_redis)
        ):
            result = await redis_set(
                key="test_key", value="test_value", ttl_seconds=300
            )

        assert result["status"] == "success"
        assert result["ttl_seconds"] == 300
        mock_redis.set.assert_called_once_with("test_key", "test_value", ex=300)


class TestRedisEnqueueTask:
    """Tests for redis_enqueue_task tool."""

    @pytest.mark.asyncio
    async def test_redis_enqueue_task_success(self):
        """redis_enqueue_task returns task_id on success."""
        from runtime.redis_tools import redis_enqueue_task

        mock_redis = MagicMock()
        mock_redis.is_available.return_value = True
        mock_redis.enqueue_task = AsyncMock(return_value="task-uuid-123")

        with patch(
            "runtime.redis_client.get_redis_client", AsyncMock(return_value=mock_redis)
        ):
            result = await redis_enqueue_task(
                queue_name="test_queue",
                task_data={"action": "process", "item_id": 42},
                priority=5,
            )

        assert result["status"] == "success"
        assert result["task_id"] == "task-uuid-123"
        assert result["queue"] == "test_queue"


class TestRedisDequeueTask:
    """Tests for redis_dequeue_task tool."""

    @pytest.mark.asyncio
    async def test_redis_dequeue_task_with_item(self):
        """redis_dequeue_task returns task when queue has items."""
        from runtime.redis_tools import redis_dequeue_task

        mock_redis = MagicMock()
        mock_redis.is_available.return_value = True
        mock_redis.dequeue_task = AsyncMock(
            return_value={"action": "process", "item_id": 42}
        )

        with patch(
            "runtime.redis_client.get_redis_client", AsyncMock(return_value=mock_redis)
        ):
            result = await redis_dequeue_task(queue_name="test_queue")

        assert result["status"] == "success"
        assert result["task"]["action"] == "process"

    @pytest.mark.asyncio
    async def test_redis_dequeue_task_empty_queue(self):
        """redis_dequeue_task returns None for empty queue."""
        from runtime.redis_tools import redis_dequeue_task

        mock_redis = MagicMock()
        mock_redis.is_available.return_value = True
        mock_redis.dequeue_task = AsyncMock(return_value=None)

        with patch(
            "runtime.redis_client.get_redis_client", AsyncMock(return_value=mock_redis)
        ):
            result = await redis_dequeue_task(queue_name="empty_queue")

        assert result["status"] == "success"
        assert result["task"] is None
