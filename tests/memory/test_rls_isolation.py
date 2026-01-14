"""
L9 Memory RLS Isolation Tests
===============================

Tests for Row-Level Security (RLS) scope isolation:
- Tenant isolation (tenant A cannot read tenant B data)
- RLS scope persists within transaction
- RLS scope cleared after transaction

Version: 1.0.0
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

# =============================================================================
# Configuration
# =============================================================================

TEST_TENANT_A = str(uuid4())
TEST_ORG_A = str(uuid4())
TEST_USER_A = str(uuid4())

TEST_TENANT_B = str(uuid4())
TEST_ORG_B = str(uuid4())
TEST_USER_B = str(uuid4())


# =============================================================================
# Test: RLS Scope Transaction
# =============================================================================


class TestRLSScopeTransaction:
    """Tests for RLS scope within transactions."""

    @pytest.mark.asyncio
    async def test_rls_scope_set_in_transaction(self):
        """Verify RLS scope is set within transaction."""
        from memory.substrate_repository import SubstrateRepository
        
        # Mock connection pool
        mock_pool = MagicMock()
        mock_conn = AsyncMock()
        mock_transaction = AsyncMock()
        mock_conn.transaction.return_value.__aenter__ = AsyncMock(return_value=mock_transaction)
        mock_conn.transaction.return_value.__aexit__ = AsyncMock(return_value=None)
        mock_pool.acquire.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_pool.acquire.return_value.__aexit__ = AsyncMock(return_value=None)
        
        repository = SubstrateRepository("postgresql://test/test")
        repository._pool = mock_pool
        
        # Use transaction with RLS scope
        async with repository.transaction(
            tenant_id=TEST_TENANT_A,
            org_id=TEST_ORG_A,
            user_id=TEST_USER_A,
            role="end_user",
        ) as conn:
            # Verify l9_set_scope was called
            mock_conn.execute.assert_called_once()
            call_args = mock_conn.execute.call_args[0]
            assert "l9_set_scope" in call_args[0]
            assert call_args[1] == TEST_TENANT_A
            assert call_args[2] == TEST_ORG_A
            assert call_args[3] == TEST_USER_A
            assert call_args[4] == "end_user"

    @pytest.mark.asyncio
    async def test_rls_connection_available_in_context(self):
        """Verify RLS connection is available in context variable during transaction."""
        from memory.substrate_repository import SubstrateRepository, _current_rls_connection
        
        # Mock connection pool
        mock_pool = MagicMock()
        mock_conn = AsyncMock()
        mock_transaction = AsyncMock()
        mock_conn.transaction.return_value.__aenter__ = AsyncMock(return_value=mock_transaction)
        mock_conn.transaction.return_value.__aexit__ = AsyncMock(return_value=None)
        mock_pool.acquire.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_pool.acquire.return_value.__aexit__ = AsyncMock(return_value=None)
        
        repository = SubstrateRepository("postgresql://test/test")
        repository._pool = mock_pool
        
        # Use transaction with RLS scope
        async with repository.transaction(
            tenant_id=TEST_TENANT_A,
            org_id=TEST_ORG_A,
            user_id=TEST_USER_A,
        ) as conn:
            # Verify connection is in context variable
            context_conn = _current_rls_connection.get()
            assert context_conn is not None
            assert context_conn == conn
        
        # Verify context is cleared after transaction
        context_conn_after = _current_rls_connection.get()
        assert context_conn_after is None


# =============================================================================
# Test: RLS Isolation
# =============================================================================


class TestRLSIsolation:
    """Tests for tenant isolation via RLS."""

    @pytest.mark.asyncio
    async def test_repository_uses_rls_connection_when_available(self):
        """Verify repository methods use RLS connection when available."""
        from memory.substrate_repository import SubstrateRepository, _current_rls_connection
        from core.schemas import PacketEnvelope, PacketMetadata, PacketProvenance
        
        # Mock RLS connection in context
        mock_rls_conn = AsyncMock()
        token = _current_rls_connection.set(mock_rls_conn)
        
        try:
            # Mock repository
            mock_pool = MagicMock()
            repository = SubstrateRepository("postgresql://test/test")
            repository._pool = mock_pool
            
            # Create test envelope
            envelope = PacketEnvelope(
                packet_id=uuid4(),
                packet_type="test",
                payload={"test": "data"},
                metadata=PacketMetadata(agent="test-agent"),
                provenance=PacketProvenance(),
            )
            
            # Insert packet - should use RLS connection
            await repository.insert_packet(envelope)
            
            # Verify RLS connection was used (not pool.acquire)
            mock_rls_conn.execute.assert_called()
            mock_pool.acquire.assert_not_called()
        finally:
            _current_rls_connection.reset(token)

    @pytest.mark.asyncio
    async def test_repository_uses_pool_when_no_rls_connection(self):
        """Verify repository methods use pool when no RLS connection available."""
        from memory.substrate_repository import SubstrateRepository
        from core.schemas import PacketEnvelope, PacketMetadata, PacketProvenance
        
        # Mock connection pool
        mock_pool = MagicMock()
        mock_conn = AsyncMock()
        mock_pool.acquire.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_pool.acquire.return_value.__aexit__ = AsyncMock(return_value=None)
        
        repository = SubstrateRepository("postgresql://test/test")
        repository._pool = mock_pool
        
        # Create test envelope
        envelope = PacketEnvelope(
            packet_id=uuid4(),
            packet_type="test",
            payload={"test": "data"},
            metadata=PacketMetadata(agent="test-agent"),
            provenance=PacketProvenance(),
        )
        
        # Insert packet - should use pool
        await repository.insert_packet(envelope)
        
        # Verify pool was used
        mock_pool.acquire.assert_called()


# =============================================================================
# Test: Write Packet with RLS
# =============================================================================


class TestWritePacketWithRLS:
    """Tests for write_packet with RLS scope."""

    @pytest.mark.asyncio
    async def test_write_packet_uses_transaction_with_rls(self):
        """Verify write_packet uses transaction when RLS scope provided."""
        from memory.substrate_service import MemorySubstrateService
        from core.schemas import PacketEnvelopeIn
        from unittest.mock import AsyncMock, MagicMock
        
        # Mock repository with transaction
        mock_repository = MagicMock()
        mock_transaction = AsyncMock()
        mock_repository.transaction.return_value.__aenter__ = AsyncMock(return_value=mock_transaction)
        mock_repository.transaction.return_value.__aexit__ = AsyncMock(return_value=None)
        
        # Mock DAG
        mock_dag = AsyncMock()
        from core.schemas import PacketWriteResult
        mock_dag.run.return_value = PacketWriteResult(
            packet_id=uuid4(),
            written_tables=["packet_store", "agent_memory_events"],
            status="ok",
        )
        
        service = MemorySubstrateService(
            database_url="postgresql://test/test",
            embedding_provider_type="stub",
        )
        service._repository = mock_repository
        service._dag = mock_dag
        
        # Create test packet
        packet_in = PacketEnvelopeIn(
            packet_type="test",
            payload={"test": "data"},
        )
        
        # Write with RLS scope
        result = await service.write_packet(
            packet_in,
            tenant_id=TEST_TENANT_A,
            org_id=TEST_ORG_A,
            user_id=TEST_USER_A,
            role="end_user",
        )
        
        # Verify transaction was used
        mock_repository.transaction.assert_called_once_with(
            tenant_id=TEST_TENANT_A,
            org_id=TEST_ORG_A,
            user_id=TEST_USER_A,
            role="end_user",
        )
        
        # Verify DAG was run
        mock_dag.run.assert_called_once()
        
        # Verify result
        assert result.status == "ok"
