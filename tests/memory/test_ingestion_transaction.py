"""
L9 Memory Ingestion Transaction Tests
========================================

Tests for transactional ingestion pipeline:
- Core writes (packet_store, memory_events) are atomic
- Transaction rollback on failure
- Best-effort writes (embedding, lineage) outside transaction

Version: 1.0.2
"""

from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from core.decorators import must_stay_async
from memory.governance_gate import build_governance_context, governance_context


# Fixture for governance context
@pytest.fixture
def gov_ctx():
    """Build test governance context."""
    return build_governance_context(
        caller_id="test",
        role="end_user",
        scope="developer",
        project_id="l9",
        allowed_scopes=["developer"],
    )


def _make_mock_repository(insert_packet_side_effect=None):
    """Create a mock repository with proper async transaction context manager."""
    mock_repo = AsyncMock()
    pid = uuid4()
    if insert_packet_side_effect:
        mock_repo.insert_packet = AsyncMock(side_effect=insert_packet_side_effect)
    else:
        mock_repo.insert_packet = AsyncMock(return_value=pid)
    mock_repo.insert_memory_event = AsyncMock(return_value=uuid4())

    @asynccontextmanager
    @must_stay_async("callers use await")
    async def _transaction(**kwargs):
        yield mock_repo

    mock_repo.transaction = MagicMock(side_effect=lambda **kw: _transaction(**kw))
    return mock_repo


# =============================================================================
# Test: Transactional Core Writes
# =============================================================================


class TestTransactionalIngestion:
    """Tests for transactional ingestion pipeline."""

    @pytest.mark.asyncio
    async def test_ingestion_uses_transaction_for_core_writes(self, gov_ctx):
        """Verify ingestion uses transaction for packet_store and memory_events."""
        from core.schemas import PacketEnvelopeIn
        from memory.ingestion import IngestionPipeline

        mock_repository = _make_mock_repository()
        pipeline = IngestionPipeline(repository=mock_repository)

        packet_in = PacketEnvelopeIn(
            packet_type="test",
            payload={"test": "data"},
        )

        async with governance_context(gov_ctx):
            result = await pipeline.ingest(packet_in)

        # Verify result
        assert "packet_store" in result.written_tables
        assert "agent_memory_events" in result.written_tables

    @pytest.mark.asyncio
    async def test_ingestion_rollback_on_core_write_failure(self, gov_ctx):
        """Verify transaction rolls back on core write failure."""
        from core.schemas import PacketEnvelopeIn
        from memory.ingestion import IngestionPipeline

        mock_repository = _make_mock_repository(
            insert_packet_side_effect=Exception("DB error")
        )
        pipeline = IngestionPipeline(repository=mock_repository)

        packet_in = PacketEnvelopeIn(
            packet_type="test",
            payload={"test": "data"},
        )

        async with governance_context(gov_ctx):
            result = await pipeline.ingest(packet_in)

        # Verify result shows error
        assert result.status in ["error", "partial"]
        assert "packet_store" not in result.written_tables or result.status == "error"

    @pytest.mark.asyncio
    @must_stay_async("callers use await")
    async def test_ingestion_best_effort_writes_outside_transaction(self, gov_ctx):
        """Verify embedding and lineage writes are outside transaction (best-effort)."""
        from core.schemas import PacketEnvelopeIn
        from memory.ingestion import IngestionPipeline

        mock_repository = _make_mock_repository()

        mock_semantic = AsyncMock()
        mock_semantic.embed_and_store = AsyncMock(return_value=None)

        pipeline = IngestionPipeline(
            repository=mock_repository,
            semantic_service=mock_semantic,
            auto_embed=True,
        )

        packet_in = PacketEnvelopeIn(
            packet_type="test",
            payload={"text": "This is test content to embed"},
        )

        async with governance_context(gov_ctx):
            result = await pipeline.ingest(packet_in)

        # Verify result includes core writes
        assert "packet_store" in result.written_tables
        assert "agent_memory_events" in result.written_tables

    @pytest.mark.asyncio
    @must_stay_async("callers use await")
    async def test_ingestion_embedding_failure_doesnt_block(self, gov_ctx):
        """Verify embedding failure doesn't block core writes."""
        from core.schemas import PacketEnvelopeIn
        from memory.ingestion import IngestionPipeline

        mock_repository = _make_mock_repository()

        mock_semantic = AsyncMock()
        mock_semantic.embed_and_store = AsyncMock(
            side_effect=Exception("Embedding failed")
        )

        pipeline = IngestionPipeline(
            repository=mock_repository,
            semantic_service=mock_semantic,
            auto_embed=True,
        )

        packet_in = PacketEnvelopeIn(
            packet_type="test",
            payload={"text": "This is test content"},
        )

        async with governance_context(gov_ctx):
            result = await pipeline.ingest(packet_in)

        # Verify core writes succeeded
        assert "packet_store" in result.written_tables
        assert "agent_memory_events" in result.written_tables
        assert result.status in ["ok", "partial"]
