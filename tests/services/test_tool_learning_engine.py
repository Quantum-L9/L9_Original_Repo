from types import SimpleNamespace

import pytest

from services.tool_learning_engine import ToolLearningEngine


class DummyConnection:
    """Mock database connection with async methods."""

    def __init__(self, rows=None, on_execute=None):
        self.rows = rows or []
        self.calls = []
        self.on_execute = on_execute

    async def execute(self, query, *args):
        self.calls.append(("execute", query, args))
        if self.on_execute:
            await self.on_execute(query, *args)

    async def fetch(self, query, *args):
        self.calls.append(("fetch", query, args))
        return self.rows


class DummyPool:
    """Mock asyncpg pool that returns an async context manager."""

    def __init__(self, rows=None, on_execute=None):
        self.rows = rows or []
        self.calls = []
        self.on_execute = on_execute

    def acquire(self):
        """Return an async context manager (not a coroutine)."""
        return DummyAcquireContext(self.rows, self.calls, self.on_execute)


class DummyAcquireContext:
    """Async context manager returned by pool.acquire()."""

    def __init__(self, rows, calls, on_execute=None):
        self.rows = rows
        self.calls = calls
        self.on_execute = on_execute
        self.conn = None

    async def __aenter__(self):
        self.conn = DummyConnection(self.rows, self.on_execute)
        return self.conn

    async def __aexit__(self, exc_type, exc, tb):
        return False


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

    inserted = []

    async def capture_execute(query, *args):
        if "INSERT" in query.upper():
            inserted.append(args)

    pool = DummyPool(rows=rows, on_execute=capture_execute)
    substrate = SimpleNamespace(postgres_pool=pool)
    engine = ToolLearningEngine(substrate)

    await engine.daily_analysis()

    # At least one alert for degraded tool (success_rate=0.3 < threshold)
    assert any("memory_search" in str(args) for args in inserted)
