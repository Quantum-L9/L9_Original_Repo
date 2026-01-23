"""
L9 Memory Protocols - Core Abstractions
========================================

Frontier-grade protocol definitions for memory subsystem following Dependency Inversion Principle.

**Top Frontier AI Lab Quality** - Production-ready abstractions for memory operations.

Features:
- ✅ Protocol-based abstractions for all memory operations
- ✅ Type-safe interfaces with comprehensive type hints
- ✅ Enables dependency injection and testing
- ✅ Supports multiple storage backends (Redis, Neo4j, PostgreSQL, pgvector)
- ✅ Hot-swappable implementations

Protocols:
- CacheClient: Key-value cache operations (Redis)
- GraphClient: Graph database operations (Neo4j)
- VectorStore: Vector similarity search operations (pgvector)
- MemoryRepository: High-level memory CRUD operations
- IngestionPipeline: Memory ingestion and processing
- RetrievalStrategy: Memory retrieval and ranking

Version: 1.0.0
GMP: di-dip-phase1-abstractions
Author: Top Frontier AI Lab
"""

from __future__ import annotations

# ============================================================================
__dora_meta__ = {
    "component_name": "Memory Protocols",
    "module_version": "1.0.0",
    "created_by": "L9 DI/DIP Upgrade",
    "created_at": "2026-01-20T12:00:00Z",
    "updated_at": "2026-01-20T12:00:00Z",
    "layer": "foundation",
    "domain": "abstractions",
    "module_name": "memory_protocols",
    "type": "protocol",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": ["Redis", "Neo4j", "PostgreSQL"],
        "memory_layers": ["semantic_memory", "working_memory", "episodic_memory"],
        "imported_by": [
            "memory.substrate_service",
            "memory.ingestion_pipeline",
            "core.di.container",
            "tests.unit.test_memory_protocols",
        ],
    },
}
# ============================================================================

from typing import Any, Dict, List, Optional, Protocol, runtime_checkable


@runtime_checkable
class CacheClient(Protocol):
    """
    Protocol for key-value cache operations.

    Implementations must provide Redis-compatible cache operations
    with TTL support and atomic operations.

    Example implementations:
    - RedisClient: Production Redis client
    - MemoryCacheClient: In-memory cache for testing
    - DistributedCacheClient: Multi-node cache cluster
    """

    async def get(self, key: str) -> Optional[str]:
        """
        Get value by key.

        Args:
            key: Cache key

        Returns:
            Value as string or None if not found
        """
        ...

    async def set(self, key: str, value: str, ttl: Optional[int] = None) -> bool:
        """
        Set key-value pair with optional TTL.

        Args:
            key: Cache key
            value: Value to store
            ttl: Time-to-live in seconds (None = no expiration)

        Returns:
            True if successful
        """
        ...

    async def delete(self, key: str) -> bool:
        """
        Delete key from cache.

        Args:
            key: Cache key

        Returns:
            True if key existed and was deleted
        """
        ...

    async def exists(self, key: str) -> bool:
        """
        Check if key exists.

        Args:
            key: Cache key

        Returns:
            True if key exists
        """
        ...

    async def expire(self, key: str, ttl: int) -> bool:
        """
        Set expiration on existing key.

        Args:
            key: Cache key
            ttl: Time-to-live in seconds

        Returns:
            True if expiration was set
        """
        ...

    async def close(self) -> None:
        """Close cache client connection."""
        ...


@runtime_checkable
class GraphClient(Protocol):
    """
    Protocol for graph database operations.

    Implementations must provide Neo4j-compatible graph operations
    for nodes, relationships, and Cypher queries.

    Example implementations:
    - Neo4jClient: Production Neo4j client
    - MemoryGraphClient: In-memory graph for testing
    - RemoteGraphClient: Remote graph database
    """

    async def execute_query(
        self, query: str, parameters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Execute Cypher query.

        Args:
            query: Cypher query string
            parameters: Query parameters

        Returns:
            List of result records as dictionaries
        """
        ...

    async def create_node(self, labels: List[str], properties: Dict[str, Any]) -> str:
        """
        Create a node with labels and properties.

        Args:
            labels: Node labels
            properties: Node properties

        Returns:
            Node ID
        """
        ...

    async def create_relationship(
        self,
        from_node_id: str,
        to_node_id: str,
        rel_type: str,
        properties: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Create relationship between nodes.

        Args:
            from_node_id: Source node ID
            to_node_id: Target node ID
            rel_type: Relationship type
            properties: Relationship properties

        Returns:
            Relationship ID
        """
        ...

    async def get_node(self, node_id: str) -> Optional[Dict[str, Any]]:
        """
        Get node by ID.

        Args:
            node_id: Node ID

        Returns:
            Node properties or None if not found
        """
        ...

    async def close(self) -> None:
        """Close graph client connection."""
        ...


@runtime_checkable
class VectorStore(Protocol):
    """
    Protocol for vector similarity search operations.

    Implementations must provide pgvector-compatible operations
    for embedding storage and similarity search.

    Example implementations:
    - PgVectorStore: PostgreSQL + pgvector
    - ChromaVectorStore: Chroma vector database
    - MockVectorStore: In-memory vectors for testing
    """

    async def upsert_embedding(
        self,
        id: str,
        embedding: List[float],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Insert or update embedding with metadata.

        Args:
            id: Unique embedding ID
            embedding: Vector embedding
            metadata: Optional metadata
        """
        ...

    async def search_similar(
        self, query_embedding: List[float], top_k: int = 10, threshold: float = 0.7
    ) -> List[Dict[str, Any]]:
        """
        Search for similar embeddings.

        Args:
            query_embedding: Query vector
            top_k: Number of results to return
            threshold: Minimum similarity threshold

        Returns:
            List of results with id, score, and metadata
        """
        ...

    async def delete_embedding(self, id: str) -> bool:
        """
        Delete embedding by ID.

        Args:
            id: Embedding ID

        Returns:
            True if deleted
        """
        ...

    async def close(self) -> None:
        """Close vector store connection."""
        ...


@runtime_checkable
class MemoryRepository(Protocol):
    """
    Protocol for high-level memory CRUD operations.

    Implementations must provide unified interface for memory
    storage across multiple backends.

    Example implementations:
    - SubstrateMemoryRepository: Multi-backend repository
    - InMemoryRepository: Testing repository
    - ReadOnlyRepository: Read-only memory access
    """

    async def store_memory(
        self,
        content: str,
        memory_type: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Store a memory.

        Args:
            content: Memory content
            memory_type: Type of memory (semantic, episodic, working)
            metadata: Optional metadata

        Returns:
            Memory ID
        """
        ...

    async def retrieve_memory(self, memory_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve memory by ID.

        Args:
            memory_id: Memory ID

        Returns:
            Memory data or None if not found
        """
        ...

    async def search_memories(
        self,
        query: str,
        memory_type: Optional[str] = None,
        top_k: int = 10,
    ) -> List[Dict[str, Any]]:
        """
        Search memories by query.

        Args:
            query: Search query
            memory_type: Optional memory type filter
            top_k: Number of results

        Returns:
            List of matching memories
        """
        ...

    async def delete_memory(self, memory_id: str) -> bool:
        """
        Delete memory by ID.

        Args:
            memory_id: Memory ID

        Returns:
            True if deleted
        """
        ...


@runtime_checkable
class IngestionPipeline(Protocol):
    """
    Protocol for memory ingestion and processing.

    Implementations must handle memory ingestion workflow including
    validation, enrichment, embedding, and storage.

    Example implementations:
    - StandardIngestionPipeline: Default pipeline
    - EnrichedIngestionPipeline: With additional enrichment
    - StreamingIngestionPipeline: Real-time streaming ingestion
    """

    async def ingest(
        self, content: str, metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Ingest content into memory system.

        Args:
            content: Content to ingest
            metadata: Optional metadata

        Returns:
            Memory ID
        """
        ...

    async def batch_ingest(self, items: List[Dict[str, Any]]) -> List[str]:
        """
        Ingest multiple items in batch.

        Args:
            items: List of items with content and metadata

        Returns:
            List of memory IDs
        """
        ...

    def validate_content(self, content: str) -> bool:
        """
        Validate content before ingestion.

        Args:
            content: Content to validate

        Returns:
            True if valid
        """
        ...


@runtime_checkable
class RetrievalStrategy(Protocol):
    """
    Protocol for memory retrieval and ranking.

    Implementations must provide retrieval strategies with
    ranking and filtering capabilities.

    Example implementations:
    - SemanticRetrievalStrategy: Embedding-based retrieval
    - HybridRetrievalStrategy: Combined semantic + keyword
    - CachedRetrievalStrategy: With caching layer
    """

    async def retrieve(
        self,
        query: str,
        top_k: int = 10,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Retrieve memories for query.

        Args:
            query: Search query
            top_k: Number of results
            filters: Optional filters

        Returns:
            Ranked list of memories
        """
        ...

    def rank_results(
        self, results: List[Dict[str, Any]], query: str
    ) -> List[Dict[str, Any]]:
        """
        Re-rank retrieval results.

        Args:
            results: Initial results
            query: Original query

        Returns:
            Re-ranked results
        """
        ...

    def get_strategy_name(self) -> str:
        """
        Get strategy name.

        Returns:
            Strategy identifier
        """
        ...


__all__ = [
    "CacheClient",
    "GraphClient",
    "VectorStore",
    "MemoryRepository",
    "IngestionPipeline",
    "RetrievalStrategy",
]
