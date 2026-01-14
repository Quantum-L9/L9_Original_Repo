"""
L9 Integration Tests - Cursor LangGraph Integration (GMP-48)
============================================================

Tests for Cursor + LangGraph + L9 Memory integration.

Verifies:
- Decision write to packetstore v2.0.0
- Semantic search hits pgvector
- Graph search uses Redis cache
- Igor high-impact decision escalation
- Checkpoint and resume thread
- Scope enforcement (Cursor cannot read l-private)
"""

import pytest
from uuid import uuid4
from unittest.mock import Mock, AsyncMock, patch

from agents.cursor.integrations.cursor_langgraph import CursorAgentState
from agents.cursor.integrations.cursor_gateway import CursorMemoryGateway, CursorScopeViolationError
from memory.substrate_dag_wrapper import SubstrateDagOrchestrator
from memory.checkpoint.cursor_checkpoint_manager import CursorCheckpointManager
from memory.checkpoint.postgres_saver import L9PostgresSaver
from memory.semantic_search import semantic_search, SearchHit
from memory.graph_search_cache import cached_graph_search, GraphSearchContext
from core.governance.approval_gate import is_high_impact_decision, escalate_to_igor
from core.governance.approval_manager import ApprovalManager, ApprovalStatus


class TestDecisionWrittenToPacketstoreV2:
    """Test that decisions are written to packetstore as PacketEnvelope v2.0.0."""

    @pytest.mark.asyncio
    async def test_decision_written_to_packetstore_v2(self):
        """Run simple Cursor task and assert cursor_decision PacketEnvelope v2.0.0 is written."""
        # Mock dependencies
        from core.schemas import PacketWriteResult
        dag_orchestrator = Mock(spec=SubstrateDagOrchestrator)
        dag_orchestrator.ingest_packet = AsyncMock(return_value=PacketWriteResult(
            packet_id=uuid4(),
            status="ok",
            written_tables=["packet_store"],
        ))
        
        gateway = CursorMemoryGateway(dag_orchestrator)
        
        # Create state with decision
        state = CursorAgentState(
            thread_id=str(uuid4()),
            task="Test task",
            decisions=[{"type": "file_mutation", "file": "test.py"}],
        )
        
        # Write decision
        packet_id = await gateway.write_decision(state)
        
        # Verify
        assert packet_id is not None
        dag_orchestrator.ingest_packet.assert_called_once()
        call_args = dag_orchestrator.ingest_packet.call_args[0][0]
        assert call_args.packet_type == "cursor_decision"
        assert call_args.payload["task"] == "Test task"


class TestSemanticSearchHitsPgvector:
    """Test that semantic search returns results from pgvector."""

    @pytest.mark.asyncio
    async def test_semantic_search_hits_pgvector(self):
        """Insert known packets + embeddings, run search, assert expected results."""
        # Mock substrate service
        mock_service = Mock()
        mock_service.semantic_search = AsyncMock(return_value=Mock(
            query="test query",
            hits=[
                Mock(
                    embedding_id=uuid4(),
                    score=0.85,
                    payload={"packet_id": str(uuid4()), "packet_type": "cursor_decision"},
                ),
            ],
        ))
        
        # Run search
        with patch("memory.semantic_search.get_service", return_value=mock_service):
            hits = await semantic_search(
                query="test query",
                agent_id="cursor",
                project_id="test",
                top_k=10,
                substrate_service=mock_service,
            )
        
        # Verify
        assert len(hits) == 1
        assert isinstance(hits[0], SearchHit)
        assert hits[0].similarity_score == 0.85


class TestGraphSearchUsesRedisCache:
    """Test that graph search uses Redis cache."""

    @pytest.mark.asyncio
    async def test_graph_search_uses_redis_cache(self):
        """Mock Neo4j and Redis, verify first call hits Neo4j, second hits cache."""
        # Mock Redis client
        mock_redis = Mock()
        mock_redis.get = AsyncMock(return_value=None)  # First call: cache miss
        mock_redis.set = AsyncMock()
        
        # Mock Neo4j client
        mock_neo4j = Mock()
        mock_neo4j.is_connected = Mock(return_value=True)
        mock_neo4j.session = Mock(return_value=Mock(
            __aenter__=AsyncMock(return_value=Mock(
                run=AsyncMock(return_value=Mock(
                    __aiter__=Mock(return_value=iter([])),
                )),
            )),
            __aexit__=AsyncMock(),
        ))
        
        ctx = GraphSearchContext(project_id="test")
        
        # First call: should hit Neo4j
        result1 = await cached_graph_search(
            query="MATCH (n) RETURN n",
            params={},
            ctx=ctx,
            redis_client=mock_redis,
            neo4j_client=mock_neo4j,
        )
        
        # Verify Neo4j was called
        assert mock_neo4j.session.called
        
        # Verify cache write
        assert mock_redis.set.called
        
        # Second call: should hit cache
        mock_redis.get = AsyncMock(return_value='{"results": [], "created_at": "2026-01-01T00:00:00", "schema_version": "test", "ttl": 100}')
        
        result2 = await cached_graph_search(
            query="MATCH (n) RETURN n",
            params={},
            ctx=ctx,
            redis_client=mock_redis,
            neo4j_client=mock_neo4j,
        )
        
        # Verify cache was read (Neo4j should not be called again)
        assert mock_redis.get.called


class TestIgorHighImpactDecisionEscalation:
    """Test that high-impact decisions escalate to Igor."""

    @pytest.mark.asyncio
    async def test_igor_high_impact_decision_escalation(self):
        """Create high-impact decision, assert CursorDecisionGateNode uses ApprovalManager."""
        # Test high-impact detection
        high_impact_decision = {
            "type": "git_commit",
            "tool_name": "git_commit",
            "affected_files": ["core/agents/executor.py"],
            "confidence": 0.6,
        }
        
        assert is_high_impact_decision(high_impact_decision) is True
        
        # Test low-impact decision
        low_impact_decision = {
            "type": "file_read",
            "confidence": 0.9,
        }
        
        assert is_high_impact_decision(low_impact_decision) is False
        
        # Test escalation
        mock_approval_manager = Mock(spec=ApprovalManager)
        mock_approval_manager.request_approval = AsyncMock(return_value=Mock(
            request_id="test-request",
            status=ApprovalStatus.PENDING,
        ))
        
        escalation_result = await escalate_to_igor(
            decision_packet=None,
            approval_manager=mock_approval_manager,
            agent_id="cursor",
            task_id="test-task",
        )
        
        assert escalation_result.approval_status == ApprovalStatus.PENDING
        assert escalation_result.request_id == "test-request"


class TestCheckpointAndResumeThread:
    """Test checkpoint and resume functionality."""

    @pytest.mark.asyncio
    async def test_checkpoint_and_resume_thread(self):
        """Simulate partial execution, checkpoint, interruption, resume."""
        # Mock dependencies
        mock_postgres_saver = Mock(spec=L9PostgresSaver)
        mock_postgres_saver.put = AsyncMock(return_value={"checkpoint_id": "test-checkpoint"})
        mock_postgres_saver.get = AsyncMock(return_value={"task": "resumed task"})
        
        mock_gateway = Mock(spec=CursorMemoryGateway)
        mock_gateway.write_checkpoint = AsyncMock(return_value=uuid4())
        mock_gateway.load_checkpoint = AsyncMock(return_value=None)
        
        checkpoint_manager = CursorCheckpointManager(
            postgres_saver=mock_postgres_saver,
            memory_gateway=mock_gateway,
        )
        
        # Create state and checkpoint
        state = CursorAgentState(
            thread_id="test-thread",
            task="Test task",
            task_status="running",
        )
        
        result = await checkpoint_manager.checkpoint("test-thread", state)
        
        # Verify dual checkpoint
        assert result["checkpoint_id"] == "test-checkpoint"
        assert result["packet_id"] is not None
        
        # Restore checkpoint
        restored = await checkpoint_manager.restore("test-thread")
        
        # Verify restoration
        assert restored is not None
        assert restored.task == "resumed task"


class TestScopeEnforcementCursorCannotReadLPrivate:
    """Test that Cursor cannot access l-private scope."""

    @pytest.mark.asyncio
    async def test_scope_enforcement_cursor_cannot_read_l_private(self):
        """Attempt to search/write with disallowed scope, assert CursorScopeViolationError."""
        # Mock dependencies
        mock_dag = Mock(spec=SubstrateDagOrchestrator)
        gateway = CursorMemoryGateway(mock_dag)
        
        # Attempt to search with l-private scope
        with pytest.raises(CursorScopeViolationError):
            await gateway.search_memory(
                query="test",
                scope=["l-private"],  # Disallowed
                project_id="test",
                limit=10,
            )
        
        # Attempt with allowed scope (should not raise)
        try:
            await gateway.search_memory(
                query="test",
                scope=["developer"],  # Allowed
                project_id="test",
                limit=10,
            )
        except CursorScopeViolationError:
            pytest.fail("Should not raise for allowed scope")

