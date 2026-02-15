from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from memory.substrate_service import MemorySubstrateService


@pytest.mark.asyncio
async def test_search_packets_by_type_requires_active_governance_context() -> None:
    service = MemorySubstrateService.__new__(MemorySubstrateService)
    def _raise(_: str):
        raise RuntimeError("missing governance")

    service._require_rls_context = _raise

    with pytest.raises(RuntimeError, match="missing governance"):
        await service.search_packets_by_type(packet_type="reflection")


@pytest.mark.asyncio
async def test_embed_text_uses_governance_scope_for_semantic_writes() -> None:
    service = MemorySubstrateService.__new__(MemorySubstrateService)
    service._require_rls_context = lambda _: SimpleNamespace(scope="l-private")
    service._semantic_service = SimpleNamespace(embed_and_store=AsyncMock(return_value="emb-1"))

    result = await service.embed_text(
        text="hello world",
        payload={"k": "v"},
        agent_id="agent-x",
    )

    assert result == "emb-1"
    service._semantic_service.embed_and_store.assert_awaited_once_with(
        text="hello world",
        payload={"k": "v"},
        agent_id="agent-x",
        scope="l-private",
    )


@pytest.mark.asyncio
async def test_query_packets_rejects_client_supplied_tenant_override() -> None:
    service = MemorySubstrateService.__new__(MemorySubstrateService)
    service._require_rls_context = lambda _: SimpleNamespace(
        tenant_id="tenant-a",
        org_id="org-a",
        user_id="user-a",
        role="end_user",
    )

    with pytest.raises(RuntimeError, match="tenant_id must be derived server-side"):
        await service.query_packets(tenant_id="tenant-b")
