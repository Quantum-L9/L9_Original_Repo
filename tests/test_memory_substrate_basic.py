"""
L9 Memory Substrate - Basic Tests
Version: 1.0.0

Minimal tests for:
- Packet model validation
- Semantic search with stub embeddings
- DAG state flow
"""

import pytest

from core.decorators import must_stay_async

pytest.skip(
    "Legacy memory substrate — memory.substrate_models not available.",
    allow_module_level=True,
)
from datetime import UTC, datetime, timezone
from uuid import uuid4

# =============================================================================
# Model Tests
# =============================================================================


class TestPacketEnvelope:
    """Tests for PacketEnvelope model."""

    def test_create_packet_with_required_fields(self):
        """Test creating a packet with only required fields."""
        from core.schemas import PacketEnvelope

        packet = PacketEnvelope(
            packet_type="event",
            payload={"test": "data"},
        )

        assert packet.packet_id is not None
        assert packet.packet_type == "event"
        assert packet.payload == {"test": "data"}
        assert packet.timestamp is not None

    def test_create_packet_with_all_fields(self):
        """Test creating a packet with all fields."""
        from core.schemas import (
            PacketConfidence,
            PacketEnvelope,
            PacketMetadata,
            PacketProvenance,
        )

        packet_id = uuid4()
        parent_id = uuid4()
        timestamp = datetime.now(UTC)

        packet = PacketEnvelope(
            packet_id=packet_id,
            packet_type="reasoning_trace",
            timestamp=timestamp,
            payload={"content": "test reasoning"},
            metadata=PacketMetadata(
                schema_version="1.0.0",
                reasoning_mode="chain_of_thought",
                agent="test_agent",
                domain="plastic_brokerage",
            ),
            provenance=PacketProvenance(
                parent_packet=parent_id,
                source="test_suite",
                tool="pytest",
            ),
            confidence=PacketConfidence(
                score=0.95,
                rationale="High confidence test case",
            ),
        )

        assert packet.packet_id == packet_id
        assert packet.timestamp == timestamp
        assert packet.metadata.agent == "test_agent"
        assert packet.provenance.parent_packet == parent_id
        assert packet.confidence.score == 0.95

    def test_packet_in_to_envelope(self):
        """Test converting PacketEnvelopeIn to PacketEnvelope."""
        from core.schemas import PacketEnvelopeIn

        packet_in = PacketEnvelopeIn(
            packet_type="memory_write",
            payload={"key": "value"},
        )

        envelope = packet_in.to_envelope()

        assert envelope.packet_id is not None
        assert envelope.packet_type == "memory_write"
        assert envelope.timestamp is not None
        assert envelope.metadata is not None


class TestStructuredReasoningBlock:
    """Tests for StructuredReasoningBlock model."""

    def test_create_reasoning_block(self):
        """Test creating a reasoning block."""
        from memory.substrate_models import StructuredReasoningBlock

        packet_id = uuid4()

        block = StructuredReasoningBlock(
            packet_id=packet_id,
            extracted_features={"type": "test"},
            inference_steps=[
                {"step": 1, "action": "analyze"},
                {"step": 2, "action": "decide"},
            ],
            reasoning_tokens=["analyze", "compare", "conclude"],
            decision_tokens=["accept"],
            confidence_scores={"overall": 0.9},
        )

        assert block.block_id is not None
        assert block.packet_id == packet_id
        assert len(block.inference_steps) == 2
        assert len(block.reasoning_tokens) == 3


class TestSemanticSearchModels:
    """Tests for semantic search models."""

    def test_search_request(self):
        """Test SemanticSearchRequest model."""
        from memory.substrate_models import SemanticSearchRequest

        request = SemanticSearchRequest(
            query="find plastic suppliers",
            top_k=5,
            agent_id="test_agent",
        )

        assert request.query == "find plastic suppliers"
        assert request.top_k == 5

    def test_search_result(self):
        """Test SemanticSearchResult model."""
        from memory.substrate_models import SemanticHit, SemanticSearchResult

        result = SemanticSearchResult(
            query="test query",
            hits=[
                SemanticHit(
                    embedding_id=uuid4(),
                    score=0.95,
                    payload={"content": "match 1"},
                ),
                SemanticHit(
                    embedding_id=uuid4(),
                    score=0.85,
                    payload={"content": "match 2"},
                ),
            ],
        )

        assert result.query == "test query"
        assert len(result.hits) == 2
        assert result.hits[0].score == 0.95


# =============================================================================
# Embedding Provider Tests
# =============================================================================


class TestStubEmbeddingProvider:
    """Tests for stub embedding provider."""

    @pytest.mark.asyncio
    async def test_embed_text(self):
        """Test stub embedding generation."""
        from memory.substrate_semantic import StubEmbeddingProvider

        provider = StubEmbeddingProvider(dimensions=1536)

        embedding = await provider.embed_text("test text")

        assert len(embedding) == 1536
        assert all(isinstance(v, float) for v in embedding)

    @pytest.mark.asyncio
    async def test_embed_deterministic(self):
        """Test that stub embeddings are deterministic."""
        from memory.substrate_semantic import StubEmbeddingProvider

        provider = StubEmbeddingProvider()

        e1 = await provider.embed_text("same text")
        e2 = await provider.embed_text("same text")

        assert e1 == e2

    @pytest.mark.asyncio
    async def test_embed_different_texts(self):
        """Test that different texts produce different embeddings."""
        from memory.substrate_semantic import StubEmbeddingProvider

        provider = StubEmbeddingProvider()

        e1 = await provider.embed_text("text one")
        e2 = await provider.embed_text("text two")

        assert e1 != e2

    @pytest.mark.asyncio
    async def test_embed_batch(self):
        """Test batch embedding."""
        from memory.substrate_semantic import StubEmbeddingProvider

        provider = StubEmbeddingProvider(dimensions=1536)

        texts = ["text 1", "text 2", "text 3"]
        embeddings = await provider.embed_batch(texts)

        assert len(embeddings) == 3
        assert all(len(e) == 1536 for e in embeddings)


# =============================================================================
# DAG Node Tests
# =============================================================================


class TestDAGNodes:
    """Tests for individual DAG nodes."""

    @pytest.mark.asyncio
    async def test_intake_node(self):
        """Test intake node validation."""
        from memory.substrate_dag import intake_node

        state = {
            "envelope": {
                "packet_type": "event",
                "payload": {"test": "data"},
            },
            "reasoning_block": None,
            "written_tables": [],
            "embedding_id": None,
            "checkpoint_id": None,
            "errors": [],
        }

        result = await intake_node(state)

        assert result["envelope"]["packet_id"] is not None
        assert result["envelope"]["timestamp"] is not None
        assert len(result["errors"]) == 0

    @pytest.mark.asyncio
    async def test_intake_node_missing_required(self):
        """Test intake node with missing required fields."""
        from memory.substrate_dag import intake_node

        state = {
            "envelope": {},
            "reasoning_block": None,
            "written_tables": [],
            "embedding_id": None,
            "checkpoint_id": None,
            "errors": [],
        }

        result = await intake_node(state)

        assert len(result["errors"]) == 2
        assert "packet_type" in result["errors"][0]

    @pytest.mark.asyncio
    async def test_reasoning_node(self):
        """Test reasoning node generates block."""
        from memory.substrate_dag import reasoning_node

        state = {
            "envelope": {
                "packet_id": str(uuid4()),
                "packet_type": "event",
                "payload": {"key": "value"},
                "timestamp": datetime.now(UTC).isoformat(),
            },
            "reasoning_block": None,
            "written_tables": [],
            "embedding_id": None,
            "checkpoint_id": None,
            "errors": [],
        }

        result = await reasoning_node(state)

        assert result["reasoning_block"] is not None
        assert result["reasoning_block"]["block_id"] is not None
        assert len(result["reasoning_block"]["inference_steps"]) == 3

    @pytest.mark.asyncio
    @must_stay_async("callers use await")
    async def test_memory_write_node_no_repo(self):
        """Test memory write node without repository marks tables."""
        from memory.substrate_dag import memory_write_node

        state = {
            "envelope": {
                "packet_id": str(uuid4()),
                "packet_type": "event",
                "payload": {"test": "data"},
                "timestamp": datetime.now(UTC).isoformat(),
                "metadata": {"agent": "test"},
            },
            "reasoning_block": {
                "block_id": str(uuid4()),
                "packet_id": str(uuid4()),
            },
            "written_tables": [],
            "embedding_id": None,
            "checkpoint_id": None,
            "errors": [],
        }

        result = await memory_write_node(state, repository=None)

        assert "packet_store" in result["written_tables"]
        assert "agent_memory_events" in result["written_tables"]


# =============================================================================
# Write Result Tests
# =============================================================================


class TestPacketWriteResult:
    """Tests for PacketWriteResult model."""

    def test_success_result(self):
        """Test successful write result."""
        from memory.substrate_models import PacketWriteResult

        result = PacketWriteResult(
            packet_id=uuid4(),
            written_tables=["packet_store", "semantic_memory"],
            status="ok",
        )

        assert result.status == "ok"
        assert result.error_message is None

    def test_error_result(self):
        """Test error write result."""
        from memory.substrate_models import PacketWriteResult

        result = PacketWriteResult(
            packet_id=uuid4(),
            written_tables=["packet_store"],
            status="error",
            error_message="Database connection failed",
        )

        assert result.status == "error"
        assert "Database" in result.error_message


# =============================================================================
# Integration-style Tests (No DB)
# =============================================================================


class TestSubstrateDAGNoDB:
    """Integration tests for DAG without database."""

    @pytest.mark.asyncio
    async def test_full_dag_flow(self):
        """Test full DAG flow without database."""
        from core.schemas import PacketEnvelope
        from memory.substrate_dag import SubstrateDAG

        dag = SubstrateDAG(repository=None, semantic_service=None)

        envelope = PacketEnvelope(
            packet_type="event",
            payload={"action": "test", "data": {"key": "value"}},
        )

        result = await dag.run(envelope)

        assert result.packet_id == envelope.packet_id
        assert result.status == "ok"
        assert "packet_store" in result.written_tables


# =============================================================================
# Factory Tests
# =============================================================================


class TestFactoryFunctions:
    """Tests for factory functions."""

    def test_create_stub_provider(self):
        """Test creating stub embedding provider."""
        from memory.substrate_semantic import create_embedding_provider

        provider = create_embedding_provider(provider_type="stub")

        assert provider.dimensions == 1536

    def test_create_openai_provider(self):
        """Test creating OpenAI provider (without making API calls)."""
        from memory.substrate_semantic import create_embedding_provider

        provider = create_embedding_provider(
            provider_type="openai",
            api_key="test_key",
        )

        assert provider.dimensions == 1536
        assert provider._model == "text-embedding-3-large"


# =============================================================================
# DB Integration Tests
# =============================================================================


class TestSubstrateDAGDBIntegration:
    """Integration tests for SubstrateDAG with real database (requires Docker)."""

    @pytest.fixture
    def db_url(self):
        """Get database URL from environment or use default Docker URL."""
        import os

        return os.environ.get(
            "DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/l9_memory"
        )

    @pytest.fixture
    async def repository(self, db_url):
        """Create a real repository connected to test database."""
        from memory.substrate_repository import SubstrateRepository

        repo = SubstrateRepository(dsn=db_url)
        try:
            await repo.initialize()
            yield repo
        except Exception:
            pytest.skip("Database not available for integration test")
        finally:
            await repo.close()

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_dag_with_db_writes_packet(self, repository):
        """Test DAG writes packet to real database."""
        import uuid

        from core.schemas import PacketEnvelope
        from memory.substrate_dag import SubstrateDAG

        # Create unique packet
        test_id = str(uuid.uuid4())
        envelope = PacketEnvelope(
            packet_type="integration_test",
            payload={"test_id": test_id, "message": "DB integration test"},
            metadata={"source": "test_substrate_dag_db_integration"},
        )

        # Run DAG with real repository
        dag = SubstrateDAG(repository=repository, semantic_service=None)
        result = await dag.run(envelope)

        # Verify result
        assert result.status == "ok"
        assert result.packet_id == envelope.packet_id
        assert "packet_store" in result.written_tables

        # Verify packet exists in database
        stored = await repository.get_packet(envelope.packet_id)
        assert stored is not None
        assert stored.packet_type == "integration_test"
        assert stored.payload["test_id"] == test_id

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_dag_with_db_creates_reasoning_trace(self, repository):
        """Test DAG creates reasoning trace in database."""
        from core.schemas import PacketEnvelope
        from memory.substrate_dag import SubstrateDAG

        envelope = PacketEnvelope(
            packet_type="reasoning_test",
            payload={"content": "Test content for reasoning extraction"},
        )

        dag = SubstrateDAG(repository=repository, semantic_service=None)
        result = await dag.run(envelope)

        assert result.status == "ok"
        assert "reasoning_traces" in result.written_tables

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_dag_with_db_extracts_insights(self, repository):
        """Test DAG extracts and stores insights from structured payload."""
        from core.schemas import PacketEnvelope
        from memory.substrate_dag import SubstrateDAG

        # Payload with extractable insights
        envelope = PacketEnvelope(
            packet_type="insight_test",
            payload={
                "insights": [
                    {"text": "Test insight 1", "confidence": 0.9},
                    {"text": "Test insight 2", "confidence": 0.8},
                ],
                "facts": [{"statement": "Test fact", "source": "test"}],
            },
        )

        dag = SubstrateDAG(repository=repository, semantic_service=None)
        result = await dag.run(envelope)

        assert result.status == "ok"
        assert "knowledge_facts" in result.written_tables

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_dag_with_db_creates_checkpoint(self, repository):
        """Test DAG creates checkpoint in database."""
        from core.schemas import PacketEnvelope
        from memory.substrate_dag import SubstrateDAG

        envelope = PacketEnvelope(
            packet_type="checkpoint_test",
            payload={"data": "checkpoint test data"},
        )

        dag = SubstrateDAG(repository=repository, semantic_service=None)
        result = await dag.run(envelope)

        assert result.status == "ok"
        assert "graph_checkpoints" in result.written_tables


# =============================================================================
# Run Tests
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
