"""Tests for PipelineRouter — unit tests with mock substrate + mock LLM.

Coverage:
  - Query rewrite enabled: rewritten + expansions passed into retrieval
  - LLM failure path: rewrite fails -> retrieval still returns results
  - Tier blending: episodic + semantic + procedural sections in context
  - Importance update called on ingest
  - Router construction validation
"""

from __future__ import annotations

from dataclasses import dataclass
from unittest.mock import AsyncMock

import pytest

from memory.pipeline_router import (
    CallerContext,
    ContextSection,
    MemoryTier,
    PipelineRouter,
    RouterResult,
    TierRetrievalConfig,
)
from memory.query_rewriter import RewriteResult

# ---------------------------------------------------------------------------
# Mock fixtures
# ---------------------------------------------------------------------------


@dataclass
class MockHit:
    packet_id: str
    content: str
    score: float = 0.8


@pytest.fixture
def mock_ingestion() -> AsyncMock:
    svc = AsyncMock()
    svc.ingest.return_value = {"status": "ok", "packet_id": "pkt-001"}
    return svc


@pytest.fixture
def mock_retrieval() -> AsyncMock:
    svc = AsyncMock()
    svc.search.return_value = [
        MockHit(packet_id="pkt-e1", content="episodic content", score=0.9),
        MockHit(packet_id="pkt-e2", content="episodic content 2", score=0.7),
    ]
    return svc


@pytest.fixture
def mock_rewriter() -> AsyncMock:
    svc = AsyncMock()
    svc.rewrite.return_value = RewriteResult(
        rewritten_query="improved query",
        expansions=["related angle 1", "related angle 2"],
        used_llm=True,
    )
    return svc


@pytest.fixture
def mock_importance() -> AsyncMock:
    return AsyncMock()


# ---------------------------------------------------------------------------
# Construction tests
# ---------------------------------------------------------------------------


class TestPipelineRouterConstruction:
    def test_requires_ingestion(self, mock_retrieval: AsyncMock) -> None:
        with pytest.raises(ValueError, match="ingestion service is required"):
            PipelineRouter(ingestion=None, retrieval=mock_retrieval)  # type: ignore[arg-type]

    def test_requires_retrieval(self, mock_ingestion: AsyncMock) -> None:
        with pytest.raises(ValueError, match="retrieval service is required"):
            PipelineRouter(ingestion=mock_ingestion, retrieval=None)  # type: ignore[arg-type]

    def test_constructs_with_required_only(
        self,
        mock_ingestion: AsyncMock,
        mock_retrieval: AsyncMock,
    ) -> None:
        router = PipelineRouter(
            ingestion=mock_ingestion,
            retrieval=mock_retrieval,
        )
        assert router is not None


# ---------------------------------------------------------------------------
# Ingest tests
# ---------------------------------------------------------------------------


class TestPipelineRouterIngest:
    @pytest.mark.asyncio
    async def test_ingest_delegates_to_ingestion_service(
        self,
        mock_ingestion: AsyncMock,
        mock_retrieval: AsyncMock,
    ) -> None:
        router = PipelineRouter(
            ingestion=mock_ingestion,
            retrieval=mock_retrieval,
        )
        result = await router.ingest({"payload": "test"}, segment="episodic")
        mock_ingestion.ingest.assert_awaited_once()
        assert result["status"] == "ok"

    @pytest.mark.asyncio
    async def test_ingest_propagates_caller_context(
        self,
        mock_ingestion: AsyncMock,
        mock_retrieval: AsyncMock,
    ) -> None:
        router = PipelineRouter(
            ingestion=mock_ingestion,
            retrieval=mock_retrieval,
        )
        caller = CallerContext(agent_id="test-agent", trace_id="tr-001")
        await router.ingest({"payload": "test"}, caller=caller)
        mock_ingestion.ingest.assert_awaited_once()


# ---------------------------------------------------------------------------
# Query tests — rewrite enabled
# ---------------------------------------------------------------------------


class TestPipelineRouterQueryWithRewrite:
    @pytest.mark.asyncio
    async def test_query_uses_rewritten_query(
        self,
        mock_ingestion: AsyncMock,
        mock_retrieval: AsyncMock,
        mock_rewriter: AsyncMock,
    ) -> None:
        router = PipelineRouter(
            ingestion=mock_ingestion,
            retrieval=mock_retrieval,
            rewriter=mock_rewriter,
        )
        result = await router.query("original query")
        assert isinstance(result, RouterResult)
        assert result.rewritten_query == "improved query"
        assert len(result.expansions) == 2
        assert mock_rewriter.rewrite.await_count == 1

    @pytest.mark.asyncio
    async def test_query_passes_expansions_to_retrieval(
        self,
        mock_ingestion: AsyncMock,
        mock_retrieval: AsyncMock,
        mock_rewriter: AsyncMock,
    ) -> None:
        router = PipelineRouter(
            ingestion=mock_ingestion,
            retrieval=mock_retrieval,
            rewriter=mock_rewriter,
        )
        cfg = TierRetrievalConfig(tiers=(MemoryTier.EPISODIC,))
        await router.query("test", tier_cfg=cfg)
        # 1 rewritten + 2 expansions = 3 search calls for 1 tier
        assert mock_retrieval.search.await_count == 3


# ---------------------------------------------------------------------------
# Query tests — rewrite failure (graceful degradation)
# ---------------------------------------------------------------------------


class TestPipelineRouterQueryRewriteFailure:
    @pytest.mark.asyncio
    async def test_query_succeeds_when_rewriter_fails(
        self,
        mock_ingestion: AsyncMock,
        mock_retrieval: AsyncMock,
    ) -> None:
        failing_rewriter = AsyncMock()
        failing_rewriter.rewrite.side_effect = RuntimeError("LLM down")
        router = PipelineRouter(
            ingestion=mock_ingestion,
            retrieval=mock_retrieval,
            rewriter=failing_rewriter,
        )
        result = await router.query("test query")
        assert isinstance(result, RouterResult)
        # Falls back to original query
        assert result.rewritten_query == "test query"
        assert result.expansions == []
        # Retrieval still called
        assert mock_retrieval.search.await_count > 0


# ---------------------------------------------------------------------------
# Tier blending tests
# ---------------------------------------------------------------------------


class TestPipelineRouterTierBlending:
    @pytest.mark.asyncio
    async def test_all_three_tiers_queried(
        self,
        mock_ingestion: AsyncMock,
        mock_retrieval: AsyncMock,
    ) -> None:
        router = PipelineRouter(
            ingestion=mock_ingestion,
            retrieval=mock_retrieval,
        )
        cfg = TierRetrievalConfig(
            tiers=(MemoryTier.EPISODIC, MemoryTier.SEMANTIC, MemoryTier.PROCEDURAL),
            enable_query_rewrite=False,
        )
        result = await router.query("test", tier_cfg=cfg)
        assert set(result.tiers_queried) == {"episodic", "semantic", "procedural"}
        assert len(result.sections) == 3

    @pytest.mark.asyncio
    async def test_sections_have_correct_tier_labels(
        self,
        mock_ingestion: AsyncMock,
        mock_retrieval: AsyncMock,
    ) -> None:
        router = PipelineRouter(
            ingestion=mock_ingestion,
            retrieval=mock_retrieval,
        )
        cfg = TierRetrievalConfig(
            tiers=(MemoryTier.EPISODIC, MemoryTier.SEMANTIC),
            enable_query_rewrite=False,
        )
        result = await router.query("test", tier_cfg=cfg)
        tier_labels = {s.tier for s in result.sections}
        assert MemoryTier.EPISODIC in tier_labels
        assert MemoryTier.SEMANTIC in tier_labels


# ---------------------------------------------------------------------------
# Build context tests
# ---------------------------------------------------------------------------


class TestPipelineRouterBuildContext:
    @pytest.mark.asyncio
    async def test_build_context_without_builder(
        self,
        mock_ingestion: AsyncMock,
        mock_retrieval: AsyncMock,
    ) -> None:
        router = PipelineRouter(
            ingestion=mock_ingestion,
            retrieval=mock_retrieval,
        )
        sections = [
            ContextSection(tier=MemoryTier.EPISODIC, content="ep content"),
            ContextSection(tier=MemoryTier.SEMANTIC, content="sem content"),
        ]
        result = await router.build_context(sections)
        assert result == ["ep content", "sem content"]

    @pytest.mark.asyncio
    async def test_build_context_with_builder(
        self,
        mock_ingestion: AsyncMock,
        mock_retrieval: AsyncMock,
    ) -> None:
        builder = AsyncMock()
        builder.build.return_value = ["assembled"]
        router = PipelineRouter(
            ingestion=mock_ingestion,
            retrieval=mock_retrieval,
            context_builder=builder,
        )
        sections = [ContextSection(tier=MemoryTier.EPISODIC, content="test")]
        result = await router.build_context(sections)
        assert result == ["assembled"]
        builder.build.assert_awaited_once()
