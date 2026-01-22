"""
L9 Tests - WorldModelRepository Basic Behavior
Version: 1.0.0

Covers:
- upsert_entity uses get_pool() and fetchrow()
- delete_entity uses execute() and returns bool
- list_entities uses fetch()
"""

import pytest

pytest.skip(
    "world_model.repository not available in test environment.", allow_module_level=True
)


from world_model.repository import WorldModelRepository


class FakeConnection:
    def __init__(self):
        self.fetchrow_calls = []
        self.fetch_calls = []
        self.execute_calls = []

    async def fetchrow(self, query: str, *args):
        self.fetchrow_calls.append((query, args))
        # Minimal fake row structure: dict-like with expected keys
        return {
            "entity_id": args[0] if args else "e-1",
            "entity_type": "test",
            "attributes": {"name": "Test"},
            "confidence": 1.0,
            "updated_at": "2025-01-01T00:00:00Z",
        }

    async def fetch(self, query: str, *args):
        self.fetch_calls.append((query, args))
        return [
            {
                "entity_id": "e-1",
                "entity_type": "test",
                "attributes": {"name": "One"},
                "confidence": 0.9,
                "updated_at": "2025-01-01T00:00:00Z",
            }
        ]

    async def execute(self, query: str, *args):
        self.execute_calls.append((query, args))
        return "DELETE 1"

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False


class FakePool:
    def __init__(self):
        self.conn = FakeConnection()
        self.acquire_calls = 0

    async def acquire(self):
        self.acquire_calls += 1
        return self.conn

    async def close(self):
        pass


@pytest.mark.asyncio
class TestWorldModelRepositoryBasic:
    async def test_upsert_entity_uses_pool_and_fetchrow(self, monkeypatch):
        fake_pool = FakePool()

        async def fake_get_pool():
            return fake_pool

        monkeypatch.setattr("world_model.repository.get_pool", fake_get_pool)

        repo = WorldModelRepository()
        row = await repo.upsert_entity(
            entity_id="entity-123",
            attributes={"name": "Test"},
            entity_type="test_type",
            confidence=0.8,
        )

        assert fake_pool.acquire_calls == 1
        assert fake_pool.conn.fetchrow_calls, "fetchrow should be called"
        assert row["entity_id"] == "entity-123"

    async def test_delete_entity_returns_bool(self, monkeypatch):
        fake_pool = FakePool()

        async def fake_get_pool():
            return fake_pool

        monkeypatch.setattr("world_model.repository.get_pool", fake_get_pool)

        repo = WorldModelRepository()
        deleted = await repo.delete_entity("entity-999")

        assert isinstance(deleted, bool)
        assert deleted is True
        assert fake_pool.conn.execute_calls, "execute should be called"

    async def test_list_entities_uses_fetch(self, monkeypatch):
        fake_pool = FakePool()

        async def fake_get_pool():
            return fake_pool

        monkeypatch.setattr("world_model.repository.get_pool", fake_get_pool)

        repo = WorldModelRepository()
        rows = await repo.list_entities(limit=10)

        assert isinstance(rows, list)
        assert len(rows) == 1
        assert fake_pool.conn.fetch_calls, "fetch should be called"
