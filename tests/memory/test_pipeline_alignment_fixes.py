from contextlib import asynccontextmanager
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from fastapi import HTTPException


from memory.governance_gate import build_governance_context, governance_context
from memory.hybrid_rag import HybridRAGPipeline
from memory.saga_patterns import _vector_search_step
from memory.saga import SagaContext
from memory.substrate_repository import SubstrateRepository
from memory.substrate_semantic import EMBEDDING_DIMENSIONS, SemanticService


def _ctx():
    return build_governance_context(
        caller_id="L",
        role="platform_admin",
        scope="developer",
        project_id="l9",
        allowed_scopes=["developer", "global"],
        tenant_id="11111111-1111-1111-1111-111111111111",
        org_id="22222222-2222-2222-2222-222222222222",
        user_id="33333333-3333-3333-3333-333333333333",
    )


@pytest.mark.asyncio
async def test_semantic_service_requires_explicit_provider():
    with pytest.raises(RuntimeError, match="Embedding provider required"):
        SemanticService(repository=MagicMock())


@pytest.mark.asyncio
async def test_insert_semantic_embedding_includes_scope_and_tenant_fields():
    repo = SubstrateRepository("postgresql://unused")
    conn = AsyncMock()

    async with governance_context(_ctx()):
        await repo._insert_semantic_embedding_with_connection(
            conn=conn,
            embedding_id=uuid4(),
            vector=[0.1] * EMBEDDING_DIMENSIONS,
            payload={"packet_id": "abc"},
            agent_id="agent-1",
            scope="developer",
        )

    args = conn.execute.await_args.args
    assert "tenant_id" in args[0]
    assert args[4]["_project_id"] == "l9"
    assert args[7] == "11111111-1111-1111-1111-111111111111"


@pytest.mark.asyncio
async def test_search_semantic_memory_applies_project_and_scope_filters():
    repo = SubstrateRepository("postgresql://unused")
    conn = AsyncMock()
    conn.fetch = AsyncMock(return_value=[])

    @asynccontextmanager
    async def _acquire():
        yield conn

    repo.acquire = _acquire

    async with governance_context(_ctx()):
        await repo.search_semantic_memory(
            query_embedding=[0.2] * EMBEDDING_DIMENSIONS,
            top_k=5,
            agent_id=None,
        )

    sql = conn.fetch.await_args.args[0]
    assert "payload->>'_project_id'" in sql
    assert "scope = ANY" in sql


@pytest.mark.asyncio
async def test_hybrid_rag_uses_semantic_search_signature_and_filters_similarity():
    semantic = MagicMock()
    semantic.search = AsyncMock(
        return_value=[
            {"packet_id": str(uuid4()), "content": "a", "score": 0.9},
            {"packet_id": str(uuid4()), "content": "b", "score": 0.2},
        ]
    )
    neo4j = MagicMock()
    neo4j.is_available.return_value = False

    pipeline = HybridRAGPipeline(semantic, neo4j)
    hits = await pipeline._vector_search("query", limit=5, min_similarity=0.5)

    semantic.search.assert_awaited_once_with(query="query", top_k=5)
    assert len(hits) == 1


@pytest.mark.asyncio
async def test_vector_search_step_uses_top_k_signature():
    semantic = MagicMock()
    semantic.search = AsyncMock(return_value=[])

    context = SagaContext(saga_id=uuid4(), input_data={"query": "test", "limit": 7, "min_similarity": 0.1})
    await _vector_search_step(context, semantic=semantic)

    semantic.search.assert_awaited_once_with(query="test", top_k=7)


@pytest.mark.asyncio
async def test_hybrid_rag_vector_search_raises_on_semantic_failure():
    semantic = MagicMock()
    semantic.search = AsyncMock(side_effect=RuntimeError("boom"))
    neo4j = MagicMock()
    neo4j.is_available.return_value = False

    pipeline = HybridRAGPipeline(semantic, neo4j)

    with pytest.raises(RuntimeError, match="boom"):
        await pipeline._vector_search("query", limit=5, min_similarity=0.0)


@pytest.mark.asyncio
async def test_repository_search_semantic_memory_fails_closed_without_governance_context():
    repo = SubstrateRepository("postgresql://unused")

    with pytest.raises(RuntimeError, match="Governance context required"):
        await repo.search_semantic_memory(
            query_embedding=[0.2] * EMBEDDING_DIMENSIONS,
            top_k=5,
            agent_id=None,
        )


@pytest.mark.asyncio
async def test_mcp_search_handler_enforces_tenant_project_scope_predicates(monkeypatch):
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[2] / "mcp_memory"))
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("MEMORY_DSN", "postgresql://test:test@localhost:5432/test")
    from src.routes import memory_unified

    captured = {}

    async def _mock_embed_text(_query):
        return [0.1] * EMBEDDING_DIMENSIONS

    async def _mock_fetch_all(sql, *params):
        captured["sql"] = sql
        captured["params"] = params
        return []

    monkeypatch.setattr(memory_unified, "embed_text", _mock_embed_text)
    monkeypatch.setattr(memory_unified, "fetch_all", _mock_fetch_all)

    async with governance_context(_ctx()):
        result = await memory_unified.search_memory_handler(
            user_id="u",
            query="find memory",
            scopes=["developer"],
            top_k=3,
            threshold=0.1,
            project_id="l9",
        )

    assert result["total_results"] == 0
    assert "payload->>'_project_id'" in captured["sql"]
    assert "sm.tenant_id =" in captured["sql"]
    assert "IS NULL OR sm.tenant_id" not in captured["sql"]
    assert "developer" in captured["params"]
    assert "l9" in captured["params"]


@pytest.mark.asyncio
async def test_mcp_search_handler_blocks_cross_project_request(monkeypatch):
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[2] / "mcp_memory"))
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("MEMORY_DSN", "postgresql://test:test@localhost:5432/test")
    from src.routes import memory_unified

    async def _mock_embed_text(_query):
        return [0.1] * EMBEDDING_DIMENSIONS

    monkeypatch.setattr(memory_unified, "embed_text", _mock_embed_text)

    async with governance_context(_ctx()):
        with pytest.raises(HTTPException, match="project_id must be derived"):

            await memory_unified.search_memory_handler(
                user_id="u",
                query="find memory",
                scopes=["developer"],
                project_id="other-project",
            )


def test_migration_contains_semantic_scope_project_index():
    migration_sql = (Path(__file__).resolve().parents[2] / "migrations" / "0030_semantic_memory_scope_project_index.sql").read_text()

    assert "CREATE INDEX IF NOT EXISTS idx_semantic_scope_project_tenant_org_user_created" in migration_sql
    assert "payload->>'_project_id'" in migration_sql


@pytest.mark.asyncio
async def test_mcp_search_handler_legacy_null_tenant_gate(monkeypatch):
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[2] / "mcp_memory"))
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("MEMORY_DSN", "postgresql://test:test@localhost:5432/test")
    monkeypatch.setenv("L9_ALLOW_LEGACY_NULL_SCOPE_ROWS", "true")
    from src.routes import memory_unified

    captured = {}

    async def _mock_embed_text(_query):
        return [0.1] * EMBEDDING_DIMENSIONS

    async def _mock_fetch_all(sql, *params):
        captured["sql"] = sql
        return []

    monkeypatch.setattr(memory_unified, "embed_text", _mock_embed_text)
    monkeypatch.setattr(memory_unified, "fetch_all", _mock_fetch_all)

    async with governance_context(_ctx()):
        await memory_unified.search_memory_handler(
            user_id="u",
            query="find memory",
            scopes=["developer"],
            top_k=3,
            threshold=0.1,
            project_id="l9",
        )

    assert "(sm.tenant_id IS NULL OR sm.tenant_id" in captured["sql"]
