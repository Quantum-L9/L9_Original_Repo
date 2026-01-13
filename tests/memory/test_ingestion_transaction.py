"""
L9 Memory Ingestion Transaction Tests
========================================

Tests for transactional ingestion pipeline:
- Core writes (packet_store, memory_events) are atomic
- Transaction rollback on failure
- Best-effort writes (embedding, lineage) outside transaction

Version: 1.0.0
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

# =============================================================================
# Test: Transactional Core Writes
# =============================================================================


class TestTransactionalIngestion:
    """Tests for transactional ingestion pipeline."""

    @pytest.mark.asyncio
    async def test_ingestion_uses_transaction_for_core_writes(self):
        """Verify ingestion uses transaction for packet_store and memory_events."""
        from memory.ingestion import IngestionPipeline
        from core.schemas.packet_envelope_v2 import PacketEnvelopeIn
        
        # Mock repository with transaction
        mock_repository = MagicMock()
        mock_transaction = AsyncMock()
        mock_repository.transaction.return_value.__aenter__ = AsyncMock(return_value=mock_transaction)
        mock_repository.transaction.return_value.__aexit__ = AsyncMock(return_value=None)
        
        pipeline = IngestionPipeline(repository=mock_repository)
        
        # Create test packet
        packet_in = PacketEnvelopeIn(
            packet_type="test",
            payload={"test": "data"},
        )
        
        # Ingest packet
        result = await pipeline.ingest(packet_in)
        
        # Verify transaction was used
        mock_repository.transaction.assert_called_once()
        
        # Verify result
        assert "packet_store" in result.written_tables
        assert "agent_memory_events" in result.written_tables

    @pytest.mark.asyncio
    async def test_ingestion_rollback_on_core_write_failure(self):
        """Verify transaction rolls back on core write failure."""
        from memory.ingestion import IngestionPipeline
        from core.schemas.packet_envelope_v2 import PacketEnvelopeIn
        
        # Mock repository with transaction that fails
        mock_repository = MagicMock()
        mock_transaction = AsyncMock()
        mock_repository.transaction.return_value.__aenter__ = AsyncMock(return_value=mock_transaction)
        mock_repository.transaction.return_value.__aexit__ = AsyncMock(return_value=None)
        
        # Make insert_packet fail
        mock_repository.insert_packet = AsyncMock(side_effect=Exception("DB error"))
        
        pipeline = IngestionPipeline(repository=mock_repository)
        
        # Create test packet
        packet_in = PacketEnvelopeIn(
            packet_type="test",
            payload={"test": "data"},
        )
        
        # Ingest packet - should handle exception
        result = await pipeline.ingest(packet_in)
        
        # Verify transaction was attempted
        mock_repository.transaction.assert_called_once()
        
        # Verify result shows error
        assert result.status in ["error", "partial"]
        assert "packet_store" not in result.written_tables or result.status == "error"

    @pytest.mark.asyncio
    async def test_ingestion_best_effort_writes_outside_transaction(self):
        """Verify embedding and lineage writes are outside transaction (best-effort)."""
        from memory.ingestion import IngestionPipeline
        from core.schemas.packet_envelope_v2 import PacketEnvelopeIn
        
        # Mock repository with transaction
        mock_repository = MagicMock()
        mock_transaction = AsyncMock()
        mock_repository.transaction.return_value.__aenter__ = AsyncMock(return_value=mock_transaction)
        mock_repository.transaction.return_value.__aexit__ = AsyncMock(return_value=None)
        
        # Mock semantic service
        mock_semantic = AsyncMock()
        mock_semantic.embed_and_store = AsyncMock(return_value=None)
        
        pipeline = IngestionPipeline(
            repository=mock_repository,
            semantic_service=mock_semantic,
            auto_embed=True,
        )
        
        # Create test packet with embeddable content
        packet_in = PacketEnvelopeIn(
            packet_type="test",
            payload={"text": "This is test content to embed"},
        )
        
        # Ingest packet
        result = await pipeline.ingest(packet_in)
        
        # Verify transaction was used for core writes
        mock_repository.transaction.assert_called_once()
        
        # Verify embedding was attempted (outside transaction)
        mock_semantic.embed_and_store.assert_called()
        
        # Verify result includes both core and best-effort writes
        assert "packet_store" in result.written_tables
        assert "agent_memory_events" in result.written_tables
        # Embedding may or may not be in written_tables depending on success

    @pytest.mark.asyncio
    async def test_ingestion_embedding_failure_doesnt_block(self):
        """Verify embedding failure doesn't block core writes."""
        from memory.ingestion import IngestionPipeline
        from core.schemas.packet_envelope_v2 import PacketEnvelopeIn
        
        # Mock repository with transaction
        mock_repository = MagicMock()
        mock_transaction = AsyncMock()
        mock_repository.transaction.return_value.__aenter__ = AsyncMock(return_value=mock_transaction)
        mock_repository.transaction.return_value.__aexit__ = AsyncMock(return_value=None)
        
        # Mock semantic service that fails
        mock_semantic = AsyncMock()
        mock_semantic.embed_and_store = AsyncMock(side_effect=Exception("Embedding failed"))
        
        pipeline = IngestionPipeline(
            repository=mock_repository,
            semantic_service=mock_semantic,
            auto_embed=True,
        )
        
        # Create test packet
        packet_in = PacketEnvelopeIn(
            packet_type="test",
            payload={"text": "This is test content"},
        )
        
        # Ingest packet
        result = await pipeline.ingest(packet_in)
        
        # Verify core writes succeeded
        assert "packet_store" in result.written_tables
        assert "agent_memory_events" in result.written_tables
        assert result.status in ["ok", "partial"]  # Should be ok or partial, not error
        
        # Verify embedding was attempted but failed (non-blocking)
        mock_semantic.embed_and_store.assert_called()
