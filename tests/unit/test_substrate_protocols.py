"""
Unit Tests for Substrate Protocols

Tests protocol definitions and runtime_checkable behavior.

Version: 1.0.0
Created: 2026-01-24
GMP: 116 (PR #52)
"""

from typing import Any
from uuid import UUID, uuid4

import pytest

# Import protocols from relocated location (core/protocols/substrate_protocols.py)
from core.protocols.substrate_protocols import (
    DAGProtocol,
    EmbeddingProviderProtocol,
    SemanticServiceProtocol,
    SubstrateRepositoryProtocol,
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
        return {"packet_id": uuid4(), "created_at": "2026-01-24T08:00:00Z"}

    async def get_packet(self, packet_id: UUID) -> Any | None:
        return {"packet_id": packet_id, "content": "test"}

    async def search_packets_by_thread(
        self,
        thread_id: UUID,
        packet_type: str | None = None,
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
        agent_id: str | None = None,
    ) -> list[dict[str, Any]]:
        return [
            {"packet_id": uuid4(), "content": "result 1", "similarity_score": 0.95},
            {"packet_id": uuid4(), "content": "result 2", "similarity_score": 0.90},
        ]

    async def embed_and_store(
        self,
        text: str,
        payload: dict[str, Any],
        agent_id: str | None = None,
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

    embedding = await mock_provider.embed_text("test text")
    assert len(embedding) == 1536
    assert isinstance(embedding[0], float)

    embeddings = await mock_provider.embed_batch(["text 1", "text 2"])
    assert len(embeddings) == 2
    assert len(embeddings[0]) == 1536


@pytest.mark.asyncio
async def test_semantic_service_protocol_compliance():
    """Test that MockSemanticService implements SemanticServiceProtocol."""
    mock_service = MockSemanticService()

    # Check protocol compliance at runtime
    assert isinstance(mock_service, SemanticServiceProtocol)

    # Test protocol methods
    results = await mock_service.search("test query", top_k=5)
    assert len(results) > 0
    assert "similarity_score" in results[0]

    vector_id = await mock_service.embed_and_store("text", {"key": "value"})
    assert vector_id is not None


@pytest.mark.asyncio
async def test_dag_protocol_compliance():
    """Test that MockDAG implements DAGProtocol."""
    mock_dag = MockDAG()

    # Check protocol compliance at runtime
    assert isinstance(mock_dag, DAGProtocol)

    # Test protocol methods
    result = await mock_dag.run({"content": "test"})
    assert "packet_id" in result
    assert result["status"] == "processed"


# ============================================================================
# Protocol Rejection Tests
# ============================================================================


class IncompleteRepository:
    """Repository missing required methods."""

    async def connect(self) -> None:
        pass


class IncompleteEmbeddingProvider:
    """Embedding provider missing required methods."""

    @property
    def dimensions(self) -> int:
        return 1536


def test_incomplete_repository_not_protocol_compliant():
    """Test that incomplete implementation is NOT protocol compliant."""
    incomplete = IncompleteRepository()
    # Should NOT be instance of protocol (missing methods)
    assert not isinstance(incomplete, SubstrateRepositoryProtocol)


def test_incomplete_embedding_provider_not_protocol_compliant():
    """Test that incomplete embedding provider is NOT protocol compliant."""
    incomplete = IncompleteEmbeddingProvider()
    # Should NOT be instance of protocol (missing methods)
    assert not isinstance(incomplete, EmbeddingProviderProtocol)


# ============================================================================
# Dependency Injection Integration Tests
# ============================================================================


class ServiceWithRepositoryDependency:
    """Example service that depends on SubstrateRepositoryProtocol."""

    def __init__(self, repository: SubstrateRepositoryProtocol):
        self.repository = repository

    async def process(self) -> dict[str, Any]:
        await self.repository.connect()
        health = await self.repository.health_check()
        return {"status": "ok", "repo_health": health}


@pytest.mark.asyncio
async def test_dependency_injection_with_mock():
    """Test that mock can be injected as dependency."""
    mock_repo = MockSubstrateRepository()
    service = ServiceWithRepositoryDependency(repository=mock_repo)

    result = await service.process()

    assert result["status"] == "ok"
    assert result["repo_health"]["status"] == "healthy"
    assert mock_repo.connected
