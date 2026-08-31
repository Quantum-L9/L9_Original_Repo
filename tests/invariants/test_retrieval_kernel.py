"""
Invariant tests for L9RetrievalKernel (ADR-0092).

Tests:
  1. retrieve() returns empty list when no backends configured
  2. retrieve() returns working memory hits when backend available
  3. retrieve() gracefully handles timeout on each tier
  4. retrieve() gracefully handles exceptions on each tier
  5. retrieve() combines results from multiple tiers
"""

from __future__ import annotations

import asyncio
from typing import Any
from unittest.mock import AsyncMock

import pytest

from memory.retrieval_kernel import L9RetrievalKernel, RetrievalHit

# =============================================================================
# Fake Backends
# =============================================================================


class FakeWorkingMemory:
    """Fake working memory backend."""

    def __init__(self, *, intent: str = "test intent") -> None:
        self._intent = intent

    async def hydrate(self, repo_id: str, branch: str) -> Any:
        class Snapshot:
            intent = self._intent

        return Snapshot()


class FakeSemanticSearch:
    """Fake semantic search backend."""

    async def search_packets(
        self, query: str, top_k: int = 5, **kwargs: Any
    ) -> list[dict[str, Any]]:
        return [
            {"payload": f"semantic result for: {query}", "score": 0.9, "metadata": {}},
        ]


class FakeGraphContext:
    """Fake graph context backend."""

    async def query_history(
        self, session_id: str, limit: int = 10
    ) -> list[dict[str, Any]]:
        return [
            {"content": f"graph result for session: {session_id}"},
        ]


class SlowBackend:
    """Backend that always times out."""

    async def hydrate(self, repo_id: str, branch: str) -> Any:
        await asyncio.sleep(10)

    async def search_packets(
        self, query: str, top_k: int = 5, **kwargs: Any
    ) -> list[Any]:
        await asyncio.sleep(10)

    async def query_history(self, session_id: str, limit: int = 10) -> list[Any]:
        await asyncio.sleep(10)


class ErrorBackend:
    """Backend that always raises."""

    async def hydrate(self, repo_id: str, branch: str) -> Any:
        raise RuntimeError("hydrate failed")

    async def search_packets(
        self, query: str, top_k: int = 5, **kwargs: Any
    ) -> list[Any]:
        raise RuntimeError("search failed")

    async def query_history(self, session_id: str, limit: int = 10) -> list[Any]:
        raise RuntimeError("query failed")


# =============================================================================
# Tests
# =============================================================================


class TestL9RetrievalKernel:
    """Invariant tests for L9RetrievalKernel."""

    @pytest.mark.asyncio
    async def test_empty_when_no_backends(self) -> None:
        """No backends → empty result list."""
        kernel = L9RetrievalKernel()
        hits = await kernel.retrieve(agent_id="test-agent", query="test query")
        assert hits == []

    @pytest.mark.asyncio
    async def test_working_memory_tier(self) -> None:
        """Working memory backend returns hits."""
        kernel = L9RetrievalKernel(
            working_memory=FakeWorkingMemory(intent="find the DAG spec"),
        )
        hits = await kernel.retrieve(agent_id="test-agent", query="DAG spec")
        assert len(hits) == 1
        assert hits[0].source_tier == "working_memory"
        assert "find the DAG spec" in hits[0].content

    @pytest.mark.asyncio
    async def test_semantic_tier(self) -> None:
        """Semantic backend returns hits."""
        kernel = L9RetrievalKernel(
            semantic=FakeSemanticSearch(),
        )
        hits = await kernel.retrieve(agent_id="test-agent", query="DAG spec")
        assert len(hits) == 1
        assert hits[0].source_tier == "semantic"

    @pytest.mark.asyncio
    async def test_graph_tier(self) -> None:
        """Graph backend returns hits when thread_id provided."""
        kernel = L9RetrievalKernel(
            graph=FakeGraphContext(),
        )
        hits = await kernel.retrieve(
            agent_id="test-agent",
            thread_id="session-123",
            query="test query",
        )
        assert len(hits) == 1
        assert hits[0].source_tier == "graph"

    @pytest.mark.asyncio
    async def test_graph_tier_skipped_without_thread_id(self) -> None:
        """Graph backend is skipped when no thread_id."""
        kernel = L9RetrievalKernel(
            graph=FakeGraphContext(),
        )
        hits = await kernel.retrieve(agent_id="test-agent", query="test query")
        assert hits == []

    @pytest.mark.asyncio
    async def test_multi_tier_combination(self) -> None:
        """All three tiers combine results."""
        kernel = L9RetrievalKernel(
            working_memory=FakeWorkingMemory(),
            semantic=FakeSemanticSearch(),
            graph=FakeGraphContext(),
        )
        hits = await kernel.retrieve(
            agent_id="test-agent",
            thread_id="session-123",
            query="test query",
        )
        tiers = {h.source_tier for h in hits}
        assert "working_memory" in tiers
        assert "semantic" in tiers
        assert "graph" in tiers

    @pytest.mark.asyncio
    async def test_timeout_graceful_degradation(self) -> None:
        """Timeout on a tier returns empty, does not raise."""
        kernel = L9RetrievalKernel(
            working_memory=SlowBackend(),  # type: ignore[arg-type]
            semantic=FakeSemanticSearch(),
            wm_timeout=0.01,
        )
        hits = await kernel.retrieve(agent_id="test-agent", query="test query")
        # Should still get semantic results despite WM timeout
        assert len(hits) >= 1
        assert all(h.source_tier == "semantic" for h in hits)

    @pytest.mark.asyncio
    async def test_exception_graceful_degradation(self) -> None:
        """Exception on a tier returns empty, does not raise."""
        kernel = L9RetrievalKernel(
            working_memory=ErrorBackend(),  # type: ignore[arg-type]
            semantic=FakeSemanticSearch(),
        )
        hits = await kernel.retrieve(agent_id="test-agent", query="test query")
        assert len(hits) >= 1
        assert all(h.source_tier == "semantic" for h in hits)
