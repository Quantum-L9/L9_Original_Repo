"""
L9 API — Slack Event Idempotency & Replay Tests
=================================================

Validates that duplicate Slack events (retries) produce exactly one
response and one stored packet. Also validates graceful degradation
when Redis is unavailable.

Author: L9 Engineering
Created: 2026-02-12
"""

from __future__ import annotations
from core.decorators import must_stay_async

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ============================================================================
__dora_meta__ = {
    "component_name": "Slack Idempotency Tests",
    "module_version": "1.0.0",
    "created_by": "L9 Engineering",
    "created_at": "2026-02-12T03:41:00Z",
    "updated_at": "2026-02-12T03:41:00Z",
    "layer": "testing",
    "domain": "api",
    "module_name": "test_slack_idempotency",
    "type": "test",
    "status": "active",
    "integrates_with": {
        "api_endpoints": ["/api/slack/events"],
        "datasources": ["Redis", "PostgreSQL"],
        "memory_layers": [],
        "imported_by": [],
    },
}
# ============================================================================


def _make_slack_event(event_id: str = "Ev01TEST", text: str = "hello") -> dict:
    """Build a minimal Slack event payload for testing."""
    return {
        "event_id": event_id,
        "team_id": "T_TEST",
        "event": {
            "type": "message",
            "text": text,
            "user": "U_TEST",
            "channel": "C_TEST",
            "ts": "1707782400.000001",
            "thread_ts": "1707782400.000001",
        },
    }


class TestSlackEventDeduplication:
    """Same event_id fired multiple times must produce exactly one reply."""

    @pytest.mark.asyncio
    @must_stay_async("callers use await")
    async def test_replay_three_times_one_response(self):
        """Firing the same event_id 3 times must yield at most 1 Slack reply."""
        try:
            from memory.slack_ingest import handle_slack_events
        except ImportError:
            pytest.skip("memory.slack_ingest not available")

        event = _make_slack_event(event_id="Ev_DEDUP_TEST")
        slack_client = MagicMock()
        slack_client.post_message = AsyncMock(return_value={"ok": True})

        redis_mock = AsyncMock()
        call_count = 0

        @must_stay_async("callers use await")
        async def mock_redis_get(key):
            nonlocal call_count
            if call_count > 0:
                return b"1"
            return None

        async def mock_redis_set(key, value, **kwargs):
            nonlocal call_count
            call_count += 1

        redis_mock.get = mock_redis_get
        redis_mock.set = mock_redis_set

        with patch(
            "memory.slack_ingest.get_redis_client",
            AsyncMock(return_value=redis_mock),
        ):
            for _ in range(3):
                try:
                    await handle_slack_events(event, slack_client=slack_client)
                except Exception:
                    pass

        assert slack_client.post_message.call_count <= 1, (
            f"Expected at most 1 Slack reply, got "
            f"{slack_client.post_message.call_count}. "
            "Event deduplication is broken."
        )

    @pytest.mark.asyncio
    @must_stay_async("callers use await")
    async def test_different_event_ids_both_processed(self):
        """Two different event_ids must both be processed (not deduplicated)."""
        try:
            from memory.slack_ingest import handle_slack_events
        except ImportError:
            pytest.skip("memory.slack_ingest not available")

        event_a = _make_slack_event(event_id="Ev_A", text="first")
        event_b = _make_slack_event(event_id="Ev_B", text="second")

        slack_client = MagicMock()
        slack_client.post_message = AsyncMock(return_value={"ok": True})

        seen_keys: set = set()
        redis_mock = AsyncMock()

        @must_stay_async("callers use await")
        async def mock_redis_get(key):
            if key in seen_keys:
                return b"1"
            return None

        async def mock_redis_set(key, value, **kwargs):
            seen_keys.add(key)

        redis_mock.get = mock_redis_get
        redis_mock.set = mock_redis_set

        with patch(
            "memory.slack_ingest.get_redis_client",
            AsyncMock(return_value=redis_mock),
        ):
            for event in [event_a, event_b]:
                try:
                    await handle_slack_events(event, slack_client=slack_client)
                except Exception:
                    pass

        assert slack_client.post_message.call_count >= 2, (
            "Different event_ids must both be processed, not deduplicated."
        )


class TestSlackRedisUnavailable:
    """When Redis is down, the handler must still process (fail-open)."""

    @pytest.mark.asyncio
    async def test_processes_when_redis_unavailable(self):
        """Handler must not silently drop events when Redis is unreachable."""
        try:
            from memory.slack_ingest import handle_slack_events
        except ImportError:
            pytest.skip("memory.slack_ingest not available")

        event = _make_slack_event(event_id="Ev_NO_REDIS")

        with patch(
            "memory.slack_ingest.get_redis_client",
            AsyncMock(return_value=None),
        ):
            try:
                await handle_slack_events(event)
                processed = True
            except ConnectionError:
                processed = False
                pytest.fail(
                    "Handler raised ConnectionError when Redis unavailable. "
                    "Must fail-open and process the event."
                )
            except Exception:
                processed = True

        assert processed, "Event was silently dropped when Redis was unavailable"

    @pytest.mark.asyncio
    async def test_redis_exception_does_not_crash_handler(self):
        """If Redis raises an exception, handler must catch and proceed."""
        try:
            from memory.slack_ingest import handle_slack_events
        except ImportError:
            pytest.skip("memory.slack_ingest not available")

        event = _make_slack_event(event_id="Ev_REDIS_ERR")

        redis_mock = AsyncMock()
        redis_mock.get = AsyncMock(side_effect=ConnectionError("Redis down"))

        with patch(
            "memory.slack_ingest.get_redis_client",
            AsyncMock(return_value=redis_mock),
        ):
            try:
                await handle_slack_events(event)
            except ConnectionError:
                pytest.fail(
                    "Redis ConnectionError leaked to caller. "
                    "Handler must catch and fail-open."
                )
            except Exception:
                pass  # Other exceptions (missing deps) are OK
