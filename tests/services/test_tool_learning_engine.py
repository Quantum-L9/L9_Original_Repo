from types import SimpleNamespace

import pytest

from services.tool_learning_engine import ToolLearningEngine


class DummyPool:
    def __init__(self, rows=None) -> None:
        self.rows = rows or []
        self.calls = []

    async def acquire(self):
        return self

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def execute(self, query):
        self.calls.append(("execute", query))

    async def fetch(self, query):
        self.calls.append(("fetch", query))
        return self.rows


@pytest.mark.asyncio
async def test_daily_analysis_with_no_snapshots(monkeypatch):
    pool = DummyPool(rows=[])
    substrate = SimpleNamespace(postgres_pool=pool)

    engine = ToolLearningEngine(substrate)

    await engine.daily_analysis()


@pytest.mark.asyncio
async def test_daily_analysis_creates_alerts(monkeypatch):
    rows = [
        {
            "tool_name": "memory_search",
            "task_type": "test",
            "success_rate": 0.3,
            "avg_latency_ms": 100.0,
            "total_executions": 20,
        },
        {
            "tool_name": "world_model_query",
            "task_type": "test",
            "success_rate": 0.95,
            "avg_latency_ms": 50.0,
            "total_executions": 50,
        },
    ]

    pool = DummyPool(rows=rows)
    inserted = []

    async def fake_execute_insert(query, *args):
        inserted.append(args)

    async def fake_acquire():
        return SimpleNamespace(
            __aenter__=lambda self: self,
            __aexit__=lambda self, exc_type, exc, tb: False,
            execute=fake_execute_insert,
            fetch=pool.fetch,
        )

    pool.acquire = fake_acquire  # type: ignore[assignment]

    substrate = SimpleNamespace(postgres_pool=pool)
    engine = ToolLearningEngine(substrate)

    await engine.daily_analysis()

    # At least one alert for degraded tool
    assert any("memory_search" in args for args in inserted)
