# ADR 0047: Memory Facade Decomposition

## Status

Proposed

## Pattern

Decompose `MemorySubstrateService` (a ~2,000 line god class) into a **facade** over 5+ mini-services. Each mini-service handles one cluster of memory operations.

## Context

L9's `MemorySubstrateService` handles too many concerns:

- Packet CRUD
- Semantic search / embeddings
- Reasoning trace storage
- Checkpoint management
- Knowledge/insight storage

This violates SRP and makes the class difficult to test, maintain, and extend.

**Source:** Perplexity Refactor Analysis (2026-01-20)

## Files

### New Directory Structure

```
memory/
├── __init__.py
├── substrate_service.py        # Facade (simplified)
├── services/
│   ├── __init__.py
│   ├── packet_service.py       # Packet CRUD
│   ├── semantic_search_service.py  # Embeddings, k-NN
│   ├── reasoning_trace_service.py  # Trace storage/replay
│   ├── checkpoint_service.py   # Snapshots, restores
│   └── knowledge_service.py    # Facts, insights, sagas
└── ... (existing files)
```

### Files to Create

- `memory/services/__init__.py`
- `memory/services/packet_service.py`
- `memory/services/semantic_search_service.py`
- `memory/services/reasoning_trace_service.py`
- `memory/services/checkpoint_service.py`
- `memory/services/knowledge_service.py`

### Files to Modify

- `memory/substrate_service.py` - Convert to facade

## Import Block

```python
from dataclasses import dataclass

from memory.services import (
    PacketService,
    SemanticSearchService,
    ReasoningTraceService,
    CheckpointService,
    KnowledgeService,
)
```

## Minimal Implementation

```python
# memory/substrate_service.py (refactored to facade)
"""Memory substrate facade over mini-services."""

from dataclasses import dataclass
from typing import Optional

from memory.services.packet_service import PacketService
from memory.services.semantic_search_service import SemanticSearchService
from memory.services.reasoning_trace_service import ReasoningTraceService
from memory.services.checkpoint_service import CheckpointService
from memory.services.knowledge_service import KnowledgeService


@dataclass
class MemorySubstrateService:
    """
    Facade over memory mini-services.

    Provides unified interface while delegating to
    specialized services for each concern.

    Services:
    - packets: Packet CRUD operations
    - search: Semantic search and embeddings
    - traces: Reasoning trace storage/replay
    - checkpoints: Snapshot and restore
    - knowledge: Facts, insights, sagas
    """

    packets: PacketService
    search: SemanticSearchService
    traces: ReasoningTraceService
    checkpoints: CheckpointService
    knowledge: KnowledgeService

    # Convenience methods delegate to services

    async def ingest_packet(self, packet):
        """Ingest packet (delegates to packets service)."""
        return await self.packets.ingest(packet)

    async def query_packets(self, query, limit=10):
        """Query packets (delegates to packets service)."""
        return await self.packets.query(query, limit)

    async def semantic_search(self, query, k=10):
        """Semantic search (delegates to search service)."""
        return await self.search.search(query, k)

    async def store_trace(self, trace):
        """Store reasoning trace (delegates to traces service)."""
        return await self.traces.store(trace)

    async def create_checkpoint(self, state):
        """Create checkpoint (delegates to checkpoints service)."""
        return await self.checkpoints.create(state)

    async def restore_checkpoint(self, checkpoint_id):
        """Restore checkpoint (delegates to checkpoints service)."""
        return await self.checkpoints.restore(checkpoint_id)

    async def store_insight(self, insight):
        """Store insight (delegates to knowledge service)."""
        return await self.knowledge.store_insight(insight)


def create_memory_substrate_service(
    postgres_client,
    neo4j_client,
    redis_client,
    embedder,
) -> MemorySubstrateService:
    """Factory for creating fully-wired MemorySubstrateService."""

    return MemorySubstrateService(
        packets=PacketService(postgres_client),
        search=SemanticSearchService(postgres_client, embedder),
        traces=ReasoningTraceService(postgres_client, neo4j_client),
        checkpoints=CheckpointService(postgres_client, neo4j_client),
        knowledge=KnowledgeService(postgres_client, neo4j_client),
    )
```

```python
# memory/services/packet_service.py
"""Packet CRUD operations."""

import logging
from typing import List, Optional
from uuid import UUID

logger = logging.getLogger(__name__)


class PacketService:
    """
    Handles packet CRUD operations.

    Responsibilities:
    - Ingest new packets
    - Query packets by criteria
    - Update packet metadata
    - Delete/archive packets
    """

    def __init__(self, postgres_client):
        self._db = postgres_client

    async def ingest(self, packet) -> UUID:
        """Ingest a new packet."""
        result = await self._db.execute(
            """
            INSERT INTO packets (id, kind, author, content, metadata, created_at)
            VALUES ($1, $2, $3, $4, $5, NOW())
            RETURNING id
            """,
            packet.id,
            packet.kind,
            packet.author,
            packet.content,
            packet.metadata,
        )
        logger.debug(f"Ingested packet: {packet.id}")
        return result["id"]

    async def query(
        self,
        query: str,
        limit: int = 10,
        kind: Optional[str] = None,
    ) -> List:
        """Query packets by text search."""
        sql = """
            SELECT * FROM packets
            WHERE content_tsv @@ plainto_tsquery($1)
        """
        if kind:
            sql += f" AND kind = '{kind}'"
        sql += f" LIMIT {limit}"

        return await self._db.fetch(sql, query)

    async def get(self, packet_id: UUID):
        """Get packet by ID."""
        return await self._db.fetchrow(
            "SELECT * FROM packets WHERE id = $1",
            packet_id,
        )

    async def update_metadata(self, packet_id: UUID, metadata: dict):
        """Update packet metadata."""
        await self._db.execute(
            "UPDATE packets SET metadata = metadata || $2 WHERE id = $1",
            packet_id,
            metadata,
        )
```

```python
# memory/services/semantic_search_service.py
"""Semantic search and embedding operations."""

import logging
from typing import List

logger = logging.getLogger(__name__)


class SemanticSearchService:
    """
    Handles semantic search via embeddings.

    Responsibilities:
    - Generate embeddings for content
    - k-NN search over embedding space
    - Similarity scoring
    """

    def __init__(self, postgres_client, embedder):
        self._db = postgres_client
        self._embedder = embedder

    async def search(
        self,
        query: str,
        k: int = 10,
        min_similarity: float = 0.7,
    ) -> List:
        """Semantic search using embeddings."""

        # Generate query embedding
        query_embedding = await self._embedder.embed(query)

        # k-NN search
        results = await self._db.fetch(
            """
            SELECT *, 1 - (embedding <=> $1) AS similarity
            FROM packets
            WHERE 1 - (embedding <=> $1) > $2
            ORDER BY embedding <=> $1
            LIMIT $3
            """,
            query_embedding,
            min_similarity,
            k,
        )

        logger.debug(f"Semantic search found {len(results)} results")
        return results

    async def embed_and_store(self, packet_id, content: str):
        """Generate embedding and store for packet."""
        embedding = await self._embedder.embed(content)

        await self._db.execute(
            "UPDATE packets SET embedding = $2 WHERE id = $1",
            packet_id,
            embedding,
        )
```

```python
# memory/services/checkpoint_service.py
"""Checkpoint management for crash recovery."""

import logging
from typing import Optional, Tuple
from uuid import UUID, uuid4

logger = logging.getLogger(__name__)


class CheckpointService:
    """
    Handles checkpoint creation and restoration.

    Responsibilities:
    - Create state snapshots
    - Restore from checkpoints
    - Manage checkpoint lifecycle
    """

    def __init__(self, postgres_client, neo4j_client):
        self._db = postgres_client
        self._graph = neo4j_client

    async def create(self, state: dict) -> UUID:
        """Create a checkpoint from current state."""
        checkpoint_id = uuid4()

        # Store in PostgreSQL
        await self._db.execute(
            """
            INSERT INTO checkpoints (id, state, created_at)
            VALUES ($1, $2, NOW())
            """,
            checkpoint_id,
            state,
        )

        # Create graph node
        await self._graph.execute(
            """
            CREATE (cp:Checkpoint {id: $id, created_at: datetime()})
            """,
            {"id": str(checkpoint_id)},
        )

        logger.info(f"Created checkpoint: {checkpoint_id}")
        return checkpoint_id

    async def restore(self, checkpoint_id: UUID) -> Optional[dict]:
        """Restore state from checkpoint."""
        result = await self._db.fetchrow(
            "SELECT state FROM checkpoints WHERE id = $1",
            checkpoint_id,
        )

        if result:
            logger.info(f"Restored checkpoint: {checkpoint_id}")
            return result["state"]

        logger.warning(f"Checkpoint not found: {checkpoint_id}")
        return None
```

## Usage Example

```python
# Creating the facade with mini-services
from memory.substrate_service import create_memory_substrate_service

substrate = create_memory_substrate_service(
    postgres_client=postgres,
    neo4j_client=neo4j,
    redis_client=redis,
    embedder=embedder,
)

# Use via facade (backwards compatible)
await substrate.ingest_packet(packet)
results = await substrate.semantic_search("query")
checkpoint_id = await substrate.create_checkpoint(state)

# Or access mini-services directly for specialized operations
await substrate.packets.update_metadata(packet_id, {"tag": "important"})
await substrate.search.embed_and_store(packet_id, content)
await substrate.checkpoints.restore(checkpoint_id)
```

## Anti-Pattern Example

```python
# ❌ WRONG — God class with everything
class MemorySubstrateService:
    def __init__(self, ...):
        # 2000 lines of initialization and methods
        pass

    async def ingest_packet(self, ...): ...      # 100 lines
    async def query_packets(self, ...): ...      # 80 lines
    async def semantic_search(self, ...): ...    # 150 lines
    async def store_trace(self, ...): ...        # 100 lines
    async def create_checkpoint(self, ...): ...  # 120 lines
    async def restore_checkpoint(self, ...): ... # 100 lines
    async def store_insight(self, ...): ...      # 80 lines
    # ... 50 more methods ...

# ✅ CORRECT — Facade over mini-services
@dataclass
class MemorySubstrateService:
    packets: PacketService           # ~250 lines
    search: SemanticSearchService    # ~250 lines
    traces: ReasoningTraceService    # ~250 lines
    checkpoints: CheckpointService   # ~250 lines
    knowledge: KnowledgeService      # ~250 lines
```

## Rules

1. `MemorySubstrateService` MUST be a facade (dataclass with services)
2. Each mini-service MUST be ≤ 300 lines
3. Mini-services MUST NOT depend on each other
4. Facade methods MUST delegate to appropriate service
5. Each mini-service MUST have its own tests
6. Services MUST be in `memory/services/` directory
7. Factory function MUST handle wiring

## AI Guidance

**DO:**

- Create one service per concern cluster
- Keep services under 300 lines each
- Use facade for backwards compatibility
- Test services in isolation

**DO NOT:**

- Put cross-cutting logic in facade
- Make services depend on each other
- Skip the facade — direct service access loses unified interface
- Mix responsibilities within a service

## Related ADRs

- [ADR-0012: Memory DAG Pipeline](./0012-memory-dag-pipeline.md) - Pipeline using memory services
- [ADR-0022: Registry Pattern](./0022-registry-pattern.md) - Service registry
- [ADR-0036: Schema Organization Pattern](./0036-schema-organization-pattern.md) - Memory schemas
