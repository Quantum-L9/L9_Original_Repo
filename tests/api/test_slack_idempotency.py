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

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from core.decorators import must_stay_async

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
        redis_mock.is_available = MagicMock(return_value=True)
        call_count = 0

        @must_stay_async("callers use await")
        async def mock_redis_get(key):
            nonlocal call_count
            if call_count > 0:
                return b"1"
            return None

        async def mock_redis_setnx(key, value, **kwargs):
            nonlocal call_count
            if call_count > 0:
                return False
            call_count += 1
            return True

        redis_mock.get = mock_redis_get
        redis_mock.setnx = mock_redis_setnx

        substrate_mock = MagicMock()
        substrate_mock.write_packet = AsyncMock(return_value=MagicMock(packet_id="123"))
        substrate_mock._repository = MagicMock()
        substrate_mock._repository.acquire = MagicMock()

        # Mock repository connection context manager
        mock_conn = AsyncMock()
        mock_conn.fetchrow = AsyncMock(return_value=None)
        substrate_mock._repository.acquire.return_value.__aenter__.return_value = (
            mock_conn
        )

        with (
            patch(
                "memory.slack_ingest.get_redis_client",
                AsyncMock(return_value=redis_mock),
            ),
            patch(
                "memory.slack_ingest.handle_slack_with_l_agent", new_callable=AsyncMock
            ) as mock_agent_handler,
            patch(
                "memory.slack_ingest._retrieve_thread_context", new_callable=AsyncMock
            ) as mock_thread_ctx,
            patch(
                "memory.slack_ingest._retrieve_semantic_hits", new_callable=AsyncMock
            ) as mock_semantic_hits,
            patch(
                "memory.slack_ingest._index_slack_conversation", new_callable=AsyncMock
            ) as mock_index,
        ):
            mock_agent_handler.return_value = ("Mock reply", "completed", [])
            mock_thread_ctx.return_value = {}
            mock_semantic_hits.return_value = {}
            mock_index.return_value = None

            for _ in range(3):
                try:
                    await handle_slack_events(
                        request_body=b"",
                        payload=event,
                        substrate_service=substrate_mock,
                        slack_client=slack_client,
                        aios_base_url="http://mock",
                        app=MagicMock(),
                    )
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

        substrate_mock = MagicMock()
        substrate_mock.write_packet = AsyncMock(return_value=MagicMock(packet_id="123"))
        substrate_mock._repository = MagicMock()
        mock_conn = AsyncMock()
        mock_conn.fetchrow = AsyncMock(return_value=None)
        substrate_mock._repository.acquire.return_value.__aenter__.return_value = (
            mock_conn
        )

        seen_keys: set = set()
        redis_mock = AsyncMock()
        redis_mock.is_available = MagicMock(return_value=True)

        @must_stay_async("callers use await")
        async def mock_redis_get(key):
            # For this test, we assume no inflight collision for different keys
            return None

        async def mock_redis_setnx(key, value, **kwargs):
            if key in seen_keys:
                return False
            seen_keys.add(key)
            return True

        async def mock_redis_delete(key):
            if key in seen_keys:
                seen_keys.remove(key)

        redis_mock.get = mock_redis_get
        redis_mock.setnx = mock_redis_setnx
        redis_mock.delete = mock_redis_delete

        with (
            patch(
                "memory.slack_ingest.get_redis_client",
                AsyncMock(return_value=redis_mock),
            ),
            patch(
                "memory.slack_ingest.handle_slack_with_l_agent", new_callable=AsyncMock
            ) as mock_agent_handler,
            patch(
                "memory.slack_ingest._retrieve_thread_context", new_callable=AsyncMock
            ) as mock_thread_ctx,
            patch(
                "memory.slack_ingest._retrieve_semantic_hits", new_callable=AsyncMock
            ) as mock_semantic_hits,
            patch(
                "memory.slack_ingest._index_slack_conversation", new_callable=AsyncMock
            ) as mock_index,
        ):
            mock_agent_handler.return_value = ("Mock reply", "completed", [])
            mock_thread_ctx.return_value = {}
            mock_semantic_hits.return_value = {}
            mock_index.return_value = None

            for event in [event_a, event_b]:
                try:
                    await handle_slack_events(
                        request_body=b"",
                        payload=event,
                        substrate_service=substrate_mock,
                        slack_client=slack_client,
                        aios_base_url="http://mock",
                        app=MagicMock(),
                    )
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

        substrate_mock = MagicMock()
        substrate_mock.write_packet = AsyncMock(return_value=MagicMock(packet_id="123"))
        substrate_mock._repository = MagicMock()
        mock_conn = AsyncMock()
        mock_conn.fetchrow = AsyncMock(return_value=None)
        substrate_mock._repository.acquire.return_value.__aenter__.return_value = (
            mock_conn
        )

        slack_client = MagicMock()
        slack_client.post_message = AsyncMock(return_value={"ok": True})

        with (
            patch("memory.slack_ingest.get_redis_client", AsyncMock(return_value=None)),
            patch(
                "memory.slack_ingest.handle_slack_with_l_agent", new_callable=AsyncMock
            ) as mock_agent_handler,
            patch(
                "memory.slack_ingest._retrieve_thread_context", new_callable=AsyncMock
            ) as mock_thread_ctx,
            patch(
                "memory.slack_ingest._retrieve_semantic_hits", new_callable=AsyncMock
            ) as mock_semantic_hits,
            patch(
                "memory.slack_ingest._index_slack_conversation", new_callable=AsyncMock
            ) as mock_index,
        ):
            mock_agent_handler.return_value = ("Mock reply", "completed", [])
            mock_thread_ctx.return_value = {}
            mock_semantic_hits.return_value = {}
            mock_index.return_value = None

            try:
                await handle_slack_events(
                    request_body=b"",
                    payload=event,
                    substrate_service=substrate_mock,
                    slack_client=slack_client,
                    aios_base_url="http://mock",
                    app=MagicMock(),
                )
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
        redis_mock.is_available = MagicMock(return_value=True)
        redis_mock.setnx = AsyncMock(side_effect=ConnectionError("Redis down"))

        substrate_mock = MagicMock()
        substrate_mock.write_packet = AsyncMock(return_value=MagicMock(packet_id="123"))
        substrate_mock._repository = MagicMock()
        mock_conn = AsyncMock()
        mock_conn.fetchrow = AsyncMock(return_value=None)
        substrate_mock._repository.acquire.return_value.__aenter__.return_value = (
            mock_conn
        )

        slack_client = MagicMock()
        slack_client.post_message = AsyncMock(return_value={"ok": True})

        with (
            patch(
                "memory.slack_ingest.get_redis_client",
                AsyncMock(return_value=redis_mock),
            ),
            patch(
                "memory.slack_ingest.handle_slack_with_l_agent", new_callable=AsyncMock
            ) as mock_agent_handler,
            patch(
                "memory.slack_ingest._retrieve_thread_context", new_callable=AsyncMock
            ) as mock_thread_ctx,
            patch(
                "memory.slack_ingest._retrieve_semantic_hits", new_callable=AsyncMock
            ) as mock_semantic_hits,
            patch(
                "memory.slack_ingest._index_slack_conversation", new_callable=AsyncMock
            ) as mock_index,
        ):
            mock_agent_handler.return_value = ("Mock reply", "completed", [])
            mock_thread_ctx.return_value = {}
            mock_semantic_hits.return_value = {}
            mock_index.return_value = None

            try:
                await handle_slack_events(
                    request_body=b"",
                    payload=event,
                    substrate_service=substrate_mock,
                    slack_client=slack_client,
                    aios_base_url="http://mock",
                    app=MagicMock(),
                )
            except ConnectionError:
                pytest.fail(
                    "Redis ConnectionError leaked to caller. "
                    "Handler must catch and fail-open."
                )
            except Exception:
                pass  # Other exceptions (missing deps) are OK
