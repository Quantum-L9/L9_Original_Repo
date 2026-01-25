from types import SimpleNamespace

import pytest

from services.tool_feedback_service import ToolFeedbackEntry, ToolFeedbackService


class DummyPool:
    def __init__(self) -> None:
        self.executed = []

    async def acquire(self):
        return self

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def executemany(self, query, args):
        self.executed.append((query, args))


@pytest.mark.asyncio
async def test_record_outcome_and_flush(monkeypatch):
    pool = DummyPool()
    substrate = SimpleNamespace(postgres_pool=pool)

    # Force small buffer size
    from config import settings as cfg_module

    settings = cfg_module.get_integration_settings()
    monkeypatch.setattr(
        cfg_module,
        "get_integration_settings",
        lambda: settings.model_copy(update={"l9_tool_feedback_buffer_size": 1}),
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
    _, args = pool.executed
    assert len(args) == 1
    row = args
    assert row == "test query"
    assert row == "memory_search"[4]
    assert row is True[5]


@pytest.mark.asyncio
async def test_get_success_rates_fallback(monkeypatch):
    pool = DummyPool()
    substrate = SimpleNamespace(postgres_pool=pool)

    service = ToolFeedbackService(substrate)

    async def fake_fetch(query, tool_names, task_type=None):
        return [
            {"tool_name": "memory_search", "success_rate": 0.9},
        ]

    async def fake_acquire():
        return SimpleNamespace(
            __aenter__=lambda self: self,
            __aexit__=lambda self, exc_type, exc, tb: False,
            fetch=fake_fetch,
        )

    pool.acquire = fake_acquire  # type: ignore[assignment]

    rates = await service.get_success_rates(
        ["memory_search", "memory_write"], task_type="test"
    )

    assert rates["memory_search"] == pytest.approx(0.9, rel=1e-6)
    assert "memory_write" in rates
