"""
Memory Substrate Protocol Definitions

Defines abstract interfaces for DI/DIP compliance per ADR-0026 and ADR-0052.
Enables dependency injection with runtime type checking and alternate implementations.

These protocols complement the higher-level memory protocols in memory_protocols.py:
- memory_protocols.py: CacheClient, GraphClient, VectorStore, MemoryRepository, etc.
- substrate_protocols.py: SubstrateRepositoryProtocol, EmbeddingProviderProtocol, etc.

Version: 1.0.0
Created: 2026-01-24
Layer: core
Domain: protocols
Type: protocol
Status: active
"""

from __future__ import annotations

# ============================================================================
__dora_meta__ = {
    "component_name": "Substrate Protocols",
    "module_version": "1.0.0",
    "created_by": "L9 DI/DIP Refactoring",
    "created_at": "2026-01-24T08:00:00Z",
    "updated_at": "2026-01-24T08:00:00Z",
    "layer": "core",
    "domain": "protocols",
    "module_name": "substrate_protocols",
    "type": "protocol",
    "status": "active",
    "integrates_with": {
        "modules": [
            "memory.substrate_service",
            "memory.substrate_repository",
            "memory.substrate_semantic",
            "memory.substrate_dag",
            "core.di.container",
        ],
        "adrs": ["ADR-0026", "ADR-0052"],
    },
}
# ============================================================================

from typing import Any, Protocol, runtime_checkable
from uuid import UUID


@runtime_checkable
class SubstrateRepositoryProtocol(Protocol):
    """
    Protocol for substrate repository layer.

    Defines the contract for PostgreSQL + pgvector memory substrate operations.
    Implementations must provide connection management, packet CRUD, and search.

    **Compliance:**
    - ADR-0026: Protocol-based abstractions
    - ADR-0052: Dependency injection

    **Implementations:**
    - memory.substrate_repository.SubstrateRepository (production)
    - tests.mocks.MockSubstrateRepository (testing)
    """

    async def connect(self) -> None:
        """Establish database connection pool."""
        ...

    async def disconnect(self) -> None:
        """Close database connection pool gracefully."""
        ...

    async def health_check(self) -> dict[str, Any]:
        """
        Check repository health status.

        Returns:
            dict with keys: status (str), latency_ms (float), pool_size (int)
        """
        ...

    async def write_packet(self, envelope: Any) -> Any:
        """
        Write packet envelope to substrate.

        Args:
            envelope: PacketEnvelopeIn with content + metadata

        Returns:
            PacketWriteResult with packet_id + timestamps
        """
        ...

    async def get_packet(self, packet_id: UUID) -> Any | None:
        """
        Retrieve packet by ID.

        Args:
            packet_id: UUID of packet

        Returns:
            PacketEnvelope or None if not found
        """
        ...

    async def search_packets_by_thread(
        self,
        thread_id: UUID,
        packet_type: str | None = None,
        limit: int = 50,
    ) -> list[Any]:
        """
        Search packets by thread ID with optional type filter.

        Args:
            thread_id: Thread UUID
            packet_type: Optional packet type filter
            limit: Maximum results

        Returns:
            List of PacketEnvelope objects
        """
        ...

    async def acquire(self) -> Any:
        """
        Acquire database connection from pool.

        Returns:
            AsyncContextManager yielding connection
        """
        ...

    async def transaction(
        self,
        tenant_id: str,
        org_id: str,
        user_id: str,
        role: str,
    ) -> Any:
        """
        Create transaction context with tenant isolation.

        Args:
            tenant_id: Tenant identifier
            org_id: Organization identifier
            user_id: User identifier
            role: User role for RBAC

        Returns:
            AsyncContextManager yielding transaction
        """
        ...


@runtime_checkable
class EmbeddingProviderProtocol(Protocol):
    """
    Protocol for embedding providers.

    Defines the contract for text embedding generation.
    Supports both OpenAI and custom embedding models.

    **Compliance:**
    - ADR-0026: Protocol-based abstractions

    **Implementations:**
    - memory.substrate_semantic.OpenAIEmbeddingProvider (production)
    - memory.substrate_semantic.StubEmbeddingProvider (testing)
    """

    @property
    def dimensions(self) -> int:
        """
        Embedding vector dimensionality.

        Returns:
            int (e.g., 1536 for text-embedding-3-large)
        """
        ...

    async def embed_text(self, text: str) -> list[float]:
        """
        Generate embedding for single text.

        Args:
            text: Input text string

        Returns:
            Embedding vector (list of floats)
        """
        ...

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """
        Generate embeddings for batch of texts.

        Args:
            texts: List of input text strings

        Returns:
            List of embedding vectors
        """
        ...


@runtime_checkable
class SemanticServiceProtocol(Protocol):
    """
    Protocol for semantic search service.

    Defines the contract for vector similarity search operations.
    Combines embedding generation with pgvector search.

    **Compliance:**
    - ADR-0026: Protocol-based abstractions

    **Implementations:**
    - memory.substrate_semantic.SemanticService (production)
    """

    async def search(
        self,
        query: str,
        top_k: int = 10,
        agent_id: str | None = None,
    ) -> list[dict[str, Any]]:
        """
        Semantic search for similar packets.

        Args:
            query: Search query text
            top_k: Maximum results
            agent_id: Optional agent filter

        Returns:
            List of dicts with keys: packet_id, content, similarity_score
        """
        ...

    async def embed_and_store(
        self,
        text: str,
        payload: dict[str, Any],
        agent_id: str | None = None,
    ) -> str:
        """
        Generate embedding and store in vector index.

        Args:
            text: Text to embed
            payload: Metadata payload
            agent_id: Optional agent identifier

        Returns:
            Stored vector ID
        """
        ...


@runtime_checkable
class DAGProtocol(Protocol):
    """
    Protocol for substrate DAG processing.

    Defines the contract for packet processing pipeline.
    Orchestrates validation, enrichment, storage, and indexing.

    **Compliance:**
    - ADR-0026: Protocol-based abstractions

    **Implementations:**
    - memory.substrate_dag.SubstrateDAG (production)
    """

    async def run(self, envelope: Any) -> Any:
        """
        Execute DAG pipeline for packet.

        Pipeline stages:
        1. Validation (schema + governance)
        2. Enrichment (embeddings + metadata)
        3. Storage (PostgreSQL write)
        4. Indexing (vector index update)

        Args:
            envelope: PacketEnvelopeIn to process

        Returns:
            PacketWriteResult with processing metadata
        """
        ...


__all__ = [
    "DAGProtocol",
    "EmbeddingProviderProtocol",
    "SemanticServiceProtocol",
    "SubstrateRepositoryProtocol",
]
