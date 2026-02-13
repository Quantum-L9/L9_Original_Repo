"""
L9 Memory RLS Isolation Tests
===============================

Tests for Row-Level Security (RLS) scope isolation:
- Tenant isolation (tenant A cannot read tenant B data)
- RLS scope persists within transaction
- RLS scope cleared after transaction

Version: 1.0.0
"""

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

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
        from contextlib import asynccontextmanager

        from memory.substrate_repository import SubstrateRepository

        # Mock connection pool with proper async context managers
        mock_pool = MagicMock()
        mock_conn = AsyncMock()

        # Create an actual async context manager for transaction()
        @asynccontextmanager
        async def mock_transaction_cm():
            yield mock_conn

        mock_conn.transaction = MagicMock(
            return_value=mock_transaction_cm().__aenter__()
        )
        # Make transaction return an async context manager
        mock_conn.transaction = lambda: mock_transaction_cm()

        # Create async context manager for pool.acquire()
        @asynccontextmanager
        async def mock_acquire_cm():
            yield mock_conn

        mock_pool.acquire = lambda: mock_acquire_cm()

        repository = SubstrateRepository("postgresql://test/test")
        repository._pool = mock_pool

        # Use transaction with RLS scope
        async with repository.transaction(
            tenant_id=TEST_TENANT_A,
            org_id=TEST_ORG_A,
            user_id=TEST_USER_A,
            role="end_user",
        ):
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
        from contextlib import asynccontextmanager

        from memory.substrate_repository import (
            SubstrateRepository,
            _current_rls_connection,
        )

        # Mock connection pool with proper async context managers
        mock_pool = MagicMock()
        mock_conn = AsyncMock()

        # Create an actual async context manager for transaction()
        @asynccontextmanager
        async def mock_transaction_cm():
            yield mock_conn

        mock_conn.transaction = lambda: mock_transaction_cm()

        # Create async context manager for pool.acquire()
        @asynccontextmanager
        async def mock_acquire_cm():
            yield mock_conn

        mock_pool.acquire = lambda: mock_acquire_cm()

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
        from core.schemas import PacketEnvelope, PacketMetadata, PacketProvenance
        from memory.substrate_repository import (
            SubstrateRepository,
            _current_rls_connection,
        )

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
        from contextlib import asynccontextmanager

        from core.schemas import PacketEnvelope, PacketMetadata, PacketProvenance
        from memory.substrate_repository import SubstrateRepository

        # Mock connection pool with proper async context manager
        mock_pool = MagicMock()
        mock_conn = AsyncMock()

        @asynccontextmanager
        async def _mock_acquire():
            yield mock_conn

        mock_pool.acquire = MagicMock(return_value=_mock_acquire())

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
        from contextlib import asynccontextmanager
        from unittest.mock import AsyncMock, MagicMock

        from core.schemas import PacketEnvelopeIn
        from memory.governance_gate import build_governance_context, governance_context
        from memory.substrate_service import MemorySubstrateService

        # Mock repository with proper async context managers
        mock_repository = MagicMock()
        mock_transaction = AsyncMock()
        mock_conn = AsyncMock()

        @asynccontextmanager
        async def _mock_transaction_cm(**kwargs):
            yield mock_transaction

        @asynccontextmanager
        async def _mock_acquire():
            yield mock_conn

        mock_repository.transaction = MagicMock(
            side_effect=lambda **kw: _mock_transaction_cm(**kw)
        )
        mock_repository.acquire = MagicMock(return_value=_mock_acquire())

        # Mock DAG
        mock_dag = AsyncMock()
        from core.schemas import PacketWriteResult

        mock_dag.run.return_value = PacketWriteResult(
            packet_id=uuid4(),
            written_tables=["packet_store", "agent_memory_events"],
            status="ok",
        )

        # Create mock embedding provider (required since GMP-96: fail-closed enforcement)
        mock_embedding_provider = MagicMock()
        mock_embedding_provider.dimensions = 1536
        mock_embedding_provider.embed_text = AsyncMock(return_value=[0.1] * 1536)
        mock_embedding_provider.embed_batch = AsyncMock(return_value=[[0.1] * 1536])

        # Create service with mock repository and mock embedding provider
        service = MemorySubstrateService(
            repository=mock_repository,
            embedding_provider=mock_embedding_provider,
        )
        service._dag = mock_dag

        # Create test packet
        packet_in = PacketEnvelopeIn(
            packet_type="test",
            payload={"test": "data"},
        )

        # Set up governance context (required since GMP-70)
        gov_ctx = build_governance_context(
            caller_id="test",
            role="end_user",
            scope="developer",
            project_id="l9",
            allowed_scopes=["developer"],
            tenant_id=TEST_TENANT_A,
            org_id=TEST_ORG_A,
            user_id=TEST_USER_A,
        )

        # Write with RLS scope
        async with governance_context(gov_ctx):
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
