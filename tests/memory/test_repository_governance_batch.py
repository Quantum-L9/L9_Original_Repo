from __future__ import annotations

from contextlib import asynccontextmanager
from types import SimpleNamespace
from uuid import uuid4

import pytest

from memory.governance_gate import governance_context
from memory.substrate_repository import SubstrateRepository


@pytest.mark.asyncio
async def test_get_packets_batch_requires_governance_context() -> None:
    repo = SubstrateRepository("postgresql://unused")
    with pytest.raises(RuntimeError, match="Governance context required"):
        await repo.get_packets_batch([uuid4()])


@pytest.mark.asyncio
async def test_get_packets_batch_applies_scope_project_filter(gov_ctx) -> None:
    repo = SubstrateRepository("postgresql://unused")

    class DummyConn:
        def __init__(self) -> None:
            self.fetch_calls = []

        async def fetch(self, query, *params):
            self.fetch_calls.append((query, params))
            return []

    conn = DummyConn()

    @asynccontextmanager
    async def _acquire():
        yield conn

    repo.acquire = _acquire  # type: ignore[method-assign]

    packet_id = uuid4()
    async with governance_context(gov_ctx):
        result = await repo.get_packets_batch([packet_id])

    assert result == {}
    assert len(conn.fetch_calls) == 1
    query, params = conn.fetch_calls[0]
    assert "scope = ANY" in query
    assert "project_id" in query
    assert params[0] == [packet_id]
    assert params[1] == ["developer"]
    assert params[2] == "l9"
