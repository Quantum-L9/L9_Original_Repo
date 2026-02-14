"""Tests for E1 — PipelineRouter wiring through WorkingMemoryAdapter.

Harvested from: current_work/02-14-2026/memory upgrade/test_pipeline_router_wiring.py
Adapted to match actual L9 APIs (WorkingMemoryAdapter.__init__ takes substrate,
semantic_recall_for_intent takes keyword args, PipelineRouter.query takes str).

Covers: feature flag ON → PipelineRouter.query() called,
        feature flag OFF → original substrate.semantic_search path.
"""

from __future__ import annotations

import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from memory.working_memory_adapter import WorkingMemoryAdapter


# ------------------------------------------------------------------
# E1: WorkingMemoryAdapter → PipelineRouter wiring
# ------------------------------------------------------------------
class TestWorkingMemoryAdapterPipelineWiring:
    """Feature flag controls delegation to PipelineRouter."""

    @pytest.fixture
    def mock_substrate(self) -> MagicMock:
        """Mock MemorySubstrateService with semantic_search."""
        substrate = MagicMock()
        # Mock semantic_search to return a result with .hits
        hit = MagicMock()
        hit.payload = {"content": "original result"}
        hit.embedding_id = "emb-001"
        hit.score = 0.9
        search_result = MagicMock()
        search_result.hits = [hit]
        substrate.semantic_search = AsyncMock(return_value=search_result)
        return substrate

    @pytest.fixture
    def adapter(self, mock_substrate: MagicMock) -> WorkingMemoryAdapter:
        return WorkingMemoryAdapter(substrate=mock_substrate)

    @pytest.mark.asyncio
    async def test_flag_off_uses_original_path(
        self,
        adapter: WorkingMemoryAdapter,
        mock_substrate: MagicMock,
    ) -> None:
        """Flag OFF → substrate.semantic_search called directly."""
        with patch.dict(os.environ, {"ENABLE_PIPELINE_ROUTER": "false"}):
            result = await adapter.semantic_recall_for_intent(
                agent_id="agent-001",
                query="test intent",
            )
        mock_substrate.semantic_search.assert_awaited_once()
        assert len(result) == 1
        assert result[0]["score"] == 0.9

    @pytest.mark.asyncio
    async def test_flag_off_is_default(
        self,
        adapter: WorkingMemoryAdapter,
        mock_substrate: MagicMock,
    ) -> None:
        """No env var set → default is OFF, original path used."""
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("ENABLE_PIPELINE_ROUTER", None)
            result = await adapter.semantic_recall_for_intent(
                agent_id="agent-001",
                query="test intent",
            )
        mock_substrate.semantic_search.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_flag_on_delegates_to_pipeline_method(
        self,
        adapter: WorkingMemoryAdapter,
        mock_substrate: MagicMock,
    ) -> None:
        """Flag ON → _semantic_recall_via_pipeline method called."""
        mock_pipeline_result = [
            {"content": "routed result", "score": 0.95, "source": "pipeline_router"},
        ]
        with (
            patch.dict(os.environ, {"ENABLE_PIPELINE_ROUTER": "true"}),
            patch.object(
                adapter,
                "_semantic_recall_via_pipeline",
                new_callable=AsyncMock,
                return_value=mock_pipeline_result,
            ) as mock_pipeline,
        ):
            result = await adapter.semantic_recall_for_intent(
                agent_id="agent-001",
                query="test intent",
            )
        mock_pipeline.assert_awaited_once_with(
            agent_id="agent-001",
            query="test intent",
            top_k=8,
        )
        assert result == mock_pipeline_result

    @pytest.mark.asyncio
    async def test_pipeline_method_exists(
        self,
        adapter: WorkingMemoryAdapter,
    ) -> None:
        """Verify _semantic_recall_via_pipeline method exists on adapter."""
        assert hasattr(adapter, "_semantic_recall_via_pipeline")
        assert callable(adapter._semantic_recall_via_pipeline)

    @pytest.mark.asyncio
    async def test_original_path_normalizes_hits(
        self,
        adapter: WorkingMemoryAdapter,
        mock_substrate: MagicMock,
    ) -> None:
        """Original path normalizes hits into plain dicts with embedding_id + score."""
        with patch.dict(os.environ, {"ENABLE_PIPELINE_ROUTER": "false"}):
            result = await adapter.semantic_recall_for_intent(
                agent_id="agent-001",
                query="test",
            )
        assert "embedding_id" in result[0]
        assert "score" in result[0]
        assert result[0]["embedding_id"] == "emb-001"
