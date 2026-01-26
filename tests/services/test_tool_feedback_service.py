from types import SimpleNamespace

import pytest

from services.tool_feedback_service import ToolFeedbackEntry, ToolFeedbackService


class DummyConnection:
    """Mock database connection."""

    def __init__(self, executed_list):
        self.executed = executed_list

    async def executemany(self, query, args):
        self.executed.append((query, args))


class DummyAcquireContext:
    """Async context manager returned by pool.acquire()."""

    def __init__(self, executed_list):
        self.executed = executed_list

    async def __aenter__(self):
        return DummyConnection(self.executed)

    async def __aexit__(self, exc_type, exc, tb):
        return False


class DummyPool:
    """Mock asyncpg pool."""

    def __init__(self) -> None:
        self.executed = []

    def acquire(self):
        """Return an async context manager (not a coroutine)."""
        return DummyAcquireContext(self.executed)


@pytest.mark.asyncio
async def test_record_outcome_and_flush(monkeypatch):
    pool = DummyPool()
    substrate = SimpleNamespace(postgres_pool=pool)

    # Force small buffer size by patching the settings function in the service module
    from config.settings import get_integration_settings

    current_settings = get_integration_settings()
    monkeypatch.setattr(
        "services.tool_feedback_service.get_integration_settings",
        lambda: current_settings.model_copy(update={"l9_tool_feedback_buffer_size": 1}),
    )

    service = ToolFeedbackService(substrate)

    entry = ToolFeedbackEntry(
        task_query="test query",
        task_embedding=[0.1] * 1536,
        task_type="test",
        session_id="sess",
        tool_name="memory_search",
        success=True,
        execution_time_ms=10.0,
        error_type=None,
        agent_id="L",
        confidence_score=0.8,
        discovery_rank=1,
        request_id="req-1",
    )

    await service.record_outcome(entry)

    assert len(pool.executed) == 1
    _, args = pool.executed[0]
    assert len(args) == 1
    row = args[0]
    assert row[0] == "test query"  # task_query
    assert row[4] == "memory_search"  # tool_name
    assert row[5] is True  # success


class AsyncContextManager:
    """Async context manager for mocking pool.acquire()."""

    def __init__(self, fetch_fn):
        self.fetch_fn = fetch_fn

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def fetch(self, query, *args, **kwargs):
        return await self.fetch_fn(query, *args, **kwargs)


@pytest.mark.asyncio
async def test_get_success_rates_fallback(monkeypatch):
    pool = DummyPool()
    substrate = SimpleNamespace(postgres_pool=pool)

    service = ToolFeedbackService(substrate)

    async def fake_fetch(query, *args, **kwargs):
        return [
            {"tool_name": "memory_search", "success_rate": 0.9},
        ]

    def fake_acquire():
        return AsyncContextManager(fake_fetch)

    pool.acquire = fake_acquire  # type: ignore[assignment]

    rates = await service.get_success_rates(
        ["memory_search", "memory_write"], task_type="test"
    )

    assert rates["memory_search"] == pytest.approx(0.9, rel=1e-6)
    assert "memory_write" in rates
