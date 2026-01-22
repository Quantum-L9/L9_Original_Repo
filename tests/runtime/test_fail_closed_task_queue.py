"""
L9 Runtime - Fail-Closed Task Queue Tests
==========================================

Tests for fail-closed enforcement in TaskQueue.

These tests verify that:
1. TaskQueue rejects in-memory mode
2. Operations fail when Redis is unavailable
3. No silent fallbacks occur

GMP-95: PR #11 Fail-Closed Enforcement Tests
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestTaskQueueFailClosed:
    """Tests for TaskQueue fail-closed behavior."""

    def test_task_queue_rejects_in_memory_mode(self):
        """TaskQueue raises RuntimeError when use_redis=False."""
        from runtime.task_queue import TaskQueue

        with pytest.raises(RuntimeError, match="TaskQueue requires Redis"):
            TaskQueue(use_redis=False)

    def test_task_queue_raises_without_redis_client(self):
        """TaskQueue raises RuntimeError when Redis client import fails."""
        with patch("runtime.task_queue._has_redis_client", False):
            # Need to reload to pick up the patched value
            from runtime import task_queue

            # Temporarily set the module-level flag
            original = task_queue._has_redis_client
            task_queue._has_redis_client = False

            try:
                with pytest.raises(
                    RuntimeError, match="TaskQueue requires Redis client"
                ):
                    task_queue.TaskQueue()
            finally:
                task_queue._has_redis_client = original

    @pytest.mark.asyncio
    async def test_ensure_redis_raises_when_unavailable(self):
        """_ensure_redis raises RuntimeError when Redis is not available."""
        from runtime.task_queue import TaskQueue

        # Create TaskQueue with mocked Redis client import
        with patch("runtime.task_queue._has_redis_client", True):
            queue = TaskQueue()

            # Mock get_redis_client to return None (unavailable)
            with patch(
                "runtime.task_queue.get_redis_client", new_callable=AsyncMock
            ) as mock_get:
                mock_get.return_value = None

                with pytest.raises(RuntimeError, match="Redis unavailable"):
                    await queue._ensure_redis()

    @pytest.mark.asyncio
    async def test_ensure_redis_raises_when_client_not_available(self):
        """_ensure_redis raises RuntimeError when Redis client reports not available."""
        from runtime.task_queue import TaskQueue

        with patch("runtime.task_queue._has_redis_client", True):
            queue = TaskQueue()

            # Mock Redis client that reports not available
            mock_client = MagicMock()
            mock_client.is_available.return_value = False

            with patch(
                "runtime.task_queue.get_redis_client", new_callable=AsyncMock
            ) as mock_get:
                mock_get.return_value = mock_client

                with pytest.raises(RuntimeError, match="Redis unavailable"):
                    await queue._ensure_redis()

    @pytest.mark.asyncio
    async def test_peek_raises_unsupported(self):
        """TaskQueue.peek raises RuntimeError as unsupported for Redis."""
        from runtime.task_queue import TaskQueue

        with patch("runtime.task_queue._has_redis_client", True):
            queue = TaskQueue()

            # Mock _ensure_redis to succeed
            queue._redis_available = True
            queue._redis_client = MagicMock()
            queue._redis_client.is_available.return_value = True

            with patch.object(queue, "_ensure_redis", new_callable=AsyncMock):
                with pytest.raises(RuntimeError, match="peek is not supported"):
                    await queue.peek()

    @pytest.mark.asyncio
    async def test_enqueue_raises_on_redis_failure(self):
        """enqueue raises RuntimeError when Redis enqueue fails."""
        from runtime.task_queue import TaskQueue

        with patch("runtime.task_queue._has_redis_client", True):
            queue = TaskQueue()

            # Mock Redis client that fails on enqueue
            mock_client = MagicMock()
            mock_client.is_available.return_value = True
            mock_client.enqueue_task = AsyncMock(
                side_effect=Exception("Connection refused")
            )

            queue._redis_client = mock_client
            queue._redis_available = True

            with patch.object(queue, "_ensure_redis", new_callable=AsyncMock):
                with pytest.raises(RuntimeError, match="Redis enqueue failed"):
                    await queue.enqueue(
                        name="test_task",
                        payload={"test": "data"},
                        handler="default",
                    )

    @pytest.mark.asyncio
    async def test_dequeue_raises_on_redis_failure(self):
        """dequeue raises RuntimeError when Redis dequeue fails."""
        from runtime.task_queue import TaskQueue

        with patch("runtime.task_queue._has_redis_client", True):
            queue = TaskQueue()

            # Mock Redis client that fails on dequeue
            mock_client = MagicMock()
            mock_client.is_available.return_value = True
            mock_client.dequeue_task = AsyncMock(
                side_effect=Exception("Connection refused")
            )

            queue._redis_client = mock_client
            queue._redis_available = True

            with patch.object(queue, "_ensure_redis", new_callable=AsyncMock):
                with pytest.raises(RuntimeError, match="Redis dequeue failed"):
                    await queue.dequeue()

    @pytest.mark.asyncio
    async def test_size_raises_on_redis_failure(self):
        """size raises RuntimeError when Redis queue_size fails."""
        from runtime.task_queue import TaskQueue

        with patch("runtime.task_queue._has_redis_client", True):
            queue = TaskQueue()

            # Mock Redis client that fails on queue_size
            mock_client = MagicMock()
            mock_client.is_available.return_value = True
            mock_client.queue_size = AsyncMock(
                side_effect=Exception("Connection refused")
            )

            queue._redis_client = mock_client
            queue._redis_available = True

            with patch.object(queue, "_ensure_redis", new_callable=AsyncMock):
                with pytest.raises(RuntimeError, match="Redis queue size failed"):
                    await queue.size()
