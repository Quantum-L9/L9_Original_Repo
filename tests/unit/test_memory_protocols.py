"""
Unit Tests for Memory Protocols

Tests protocol definitions and runtime_checkable behavior.

Version: 1.0.0
Created: 2026-01-22
"""

import pytest
from typing import Any, Optional
from uuid import UUID, uuid4

# Import protocols
from core.abstractions.memory_protocols import (
    SubstrateRepositoryProtocol,
    EmbeddingProviderProtocol,
    SemanticServiceProtocol,
    DAGProtocol,
)


# ============================================================================
# Mock Implementations for Testing
# ============================================================================


class MockSubstrateRepository:
    """Mock implementation of SubstrateRepositoryProtocol."""

    def __init__(self):
        self.connected = False

    async def connect(self) -> None:
        self.connected = True

    async def disconnect(self) -> None:
        self.connected = False

    async def health_check(self) -> dict[str, Any]:
        return {"status": "healthy", "latency_ms": 5.0, "pool_size": 10}

    async def write_packet(self, envelope: Any) -> Any:
        return {"packet_id": uuid4(), "created_at": "2026-01-22T20:00:00Z"}

    async def get_packet(self, packet_id: UUID) -> Optional[Any]:
        return {"packet_id": packet_id, "content": "test"}

    async def search_packets_by_thread(
        self,
        thread_id: UUID,
        packet_type: Optional[str] = None,
        limit: int = 50,
    ) -> list[Any]:
        return [{"packet_id": uuid4(), "content": "test"}]

    async def acquire(self) -> Any:
        return self

    async def transaction(
        self,
        tenant_id: str,
        org_id: str,
        user_id: str,
        role: str,
    ) -> Any:
        return self


class MockEmbeddingProvider:
    """Mock implementation of EmbeddingProviderProtocol."""

    @property
    def dimensions(self) -> int:
        return 1536

    async def embed_text(self, text: str) -> list[float]:
        return [0.1] * 1536

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        return [[0.1] * 1536 for _ in texts]


class MockSemanticService:
    """Mock implementation of SemanticServiceProtocol."""

    async def search(
        self,
        query: str,
        top_k: int = 10,
        agent_id: Optional[str] = None,
    ) -> list[dict[str, Any]]:
        return [
            {"packet_id": uuid4(), "content": "result 1", "similarity_score": 0.95},
            {"packet_id": uuid4(), "content": "result 2", "similarity_score": 0.90},
        ]

    async def embed_and_store(
        self,
        text: str,
        payload: dict[str, Any],
        agent_id: Optional[str] = None,
    ) -> str:
        return str(uuid4())


class MockDAG:
    """Mock implementation of DAGProtocol."""

    async def run(self, envelope: Any) -> Any:
        return {"packet_id": uuid4(), "status": "processed"}


# ============================================================================
# Protocol Compliance Tests
# ============================================================================


@pytest.mark.asyncio
async def test_substrate_repository_protocol_compliance():
    """Test that MockSubstrateRepository implements SubstrateRepositoryProtocol."""
    mock_repo = MockSubstrateRepository()

    # Check protocol compliance at runtime
    assert isinstance(mock_repo, SubstrateRepositoryProtocol)

    # Test protocol methods
    await mock_repo.connect()
    assert mock_repo.connected

    health = await mock_repo.health_check()
    assert health["status"] == "healthy"

    result = await mock_repo.write_packet({"content": "test"})
    assert "packet_id" in result

    packet = await mock_repo.get_packet(uuid4())
    assert packet is not None

    packets = await mock_repo.search_packets_by_thread(uuid4())
    assert len(packets) > 0

    await mock_repo.disconnect()
    assert not mock_repo.connected


@pytest.mark.asyncio
async def test_embedding_provider_protocol_compliance():
    """Test that MockEmbeddingProvider implements EmbeddingProviderProtocol."""
    mock_provider = MockEmbeddingProvider()

    # Check protocol compliance at runtime
    assert isinstance(mock_provider, EmbeddingProviderProtocol)

    # Test protocol methods
    assert mock_provider.dimensions == 1536

    embedding = await mock_provider.embed_text("test")
    assert len(embedding) == 1536

    batch_embeddings = await mock_provider.embed_batch(["test1", "test2"])
    assert len(batch_embeddings) == 2
    assert all(len(emb) == 1536 for emb in batch_embeddings)


@pytest.mark.asyncio
async def test_semantic_service_protocol_compliance():
    """Test that MockSemanticService implements SemanticServiceProtocol."""
    mock_service = MockSemanticService()

    # Check protocol compliance at runtime
    assert isinstance(mock_service, SemanticServiceProtocol)

    # Test protocol methods
    results = await mock_service.search("test query", top_k=5)
    assert len(results) > 0
    assert all("similarity_score" in r for r in results)

    vector_id = await mock_service.embed_and_store("test", {"key": "value"})
    assert vector_id is not None


@pytest.mark.asyncio
async def test_dag_protocol_compliance():
    """Test that MockDAG implements DAGProtocol."""
    mock_dag = MockDAG()

    # Check protocol compliance at runtime
    assert isinstance(mock_dag, DAGProtocol)

    # Test protocol methods
    result = await mock_dag.run({"content": "test"})
    assert result["status"] == "processed"


# ============================================================================
# Protocol Rejection Tests
# ============================================================================


def test_protocol_rejects_non_compliant_class():
    """Test that protocol rejects classes that don't implement required methods."""

    class IncompleteRepository:
        """Missing required methods."""

        async def connect(self) -> None:
            pass

    incomplete = IncompleteRepository()

    # Should NOT be instance of protocol (missing methods)
    assert not isinstance(incomplete, SubstrateRepositoryProtocol)


def test_protocol_rejects_wrong_signature():
    """Test that protocol rejects classes with wrong method signatures."""

    class WrongSignatureRepository:
        """Has connect() but wrong signature."""

        def connect(
            self, wrong_param: str
        ) -> None:  # Wrong signature (not async, extra param)
            pass

    wrong_sig = WrongSignatureRepository()

    # Should NOT be instance of protocol (wrong signature)
    assert not isinstance(wrong_sig, SubstrateRepositoryProtocol)


# ============================================================================
# Integration Test: Protocol-Based Dependency Injection
# ============================================================================


@pytest.mark.asyncio
async def test_protocol_based_dependency_injection():
    """Test that protocols enable dependency injection."""

    class ServiceUsingProtocols:
        """Service that depends on protocols, not concrete classes."""

        def __init__(
            self,
            repository: SubstrateRepositoryProtocol,
            embedding_provider: EmbeddingProviderProtocol,
        ):
            self.repository = repository
            self.embedding_provider = embedding_provider

        async def process_text(self, text: str) -> dict[str, Any]:
            """Process text using injected dependencies."""
            embedding = await self.embedding_provider.embed_text(text)
            result = await self.repository.write_packet(
                {
                    "content": text,
                    "embedding": embedding,
                }
            )
            return result

    # Inject mock implementations
    service = ServiceUsingProtocols(
        repository=MockSubstrateRepository(),
        embedding_provider=MockEmbeddingProvider(),
    )

    # Service works with mocks (dependency inversion!)
    await service.repository.connect()
    result = await service.process_text("test content")

    assert "packet_id" in result
    await service.repository.disconnect()


# ============================================================================
# DORA FOOTER
# ============================================================================
# tags: ["protocols", "testing", "unit-tests"]
# keywords: ["dag", "embedding", "memory", "protocol", "repository", "semantic"]
# last_modified: "2026-01-22T20:00:00Z"
# ============================================================================
