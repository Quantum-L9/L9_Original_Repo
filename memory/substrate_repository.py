"""
L9 Memory Substrate - Repository Layer
Version: 1.0.0

Thin repository for Postgres + pgvector database access.
Provides async functions for all memory substrate operations.
"""

import json
import structlog
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any, AsyncGenerator, Optional
from uuid import UUID, uuid4

import asyncpg

from memory.substrate_models import (
    AgentMemoryEventRow,
    GraphCheckpointRow,
    KnowledgeFactRow,
    PacketEnvelope,
    PacketStoreRow,
    ReasoningTraceRow,
    SemanticHit,
    StructuredReasoningBlock,
)

logger = structlog.get_logger(__name__)


class SubstrateRepository:
    """
    Repository for memory substrate database operations.

    Uses asyncpg for async Postgres access with pgvector support.
    """

    def __init__(self, database_url: str, pool_size: int = 5, max_overflow: int = 10):
        """
        Initialize repository with database URL.

        Args:
            database_url: Postgres DSN (postgresql://user:pass@host:port/db)
            pool_size: Connection pool minimum size
            max_overflow: Connection pool maximum size
        """
        self._database_url = database_url
        self._pool_size = pool_size
        self._max_overflow = max_overflow
        self._pool: Optional[asyncpg.Pool] = None

    async def connect(self) -> None:
        """Initialize connection pool."""
        if self._pool is None:
            self._pool = await asyncpg.create_pool(
                self._database_url,
                min_size=self._pool_size,
                max_size=self._pool_size + self._max_overflow,
            )
            logger.info("Database connection pool initialized")

    async def disconnect(self) -> None:
        """Close connection pool."""
        if self._pool:
            await self._pool.close()
            self._pool = None
            logger.info("Database connection pool closed")

    @asynccontextmanager
    async def acquire(self) -> AsyncGenerator[asyncpg.Connection, None]:
        """Acquire a connection from the pool."""
        if self._pool is None:
            raise RuntimeError("Repository not connected. Call connect() first.")
        async with self._pool.acquire() as conn:
            yield conn

    # =========================================================================
    # Packet Store Operations
    # =========================================================================

    async def insert_packet(self, envelope: PacketEnvelope) -> UUID:
        """
        Insert a PacketEnvelope into packet_store.

        Returns:
            The packet_id of the inserted record.
        """
        # Extract fields from envelope for dedicated columns (v2.0 support)
        thread_id = envelope.thread_id
        tags = envelope.tags if envelope.tags else []
        ttl = envelope.ttl
        # Extract parent_ids from lineage (DAG support)
        parent_ids = envelope.lineage.parent_ids if envelope.lineage else []
        # Extra fields may be in metadata dict (extra="allow" in PacketMetadata)
        metadata_dict = envelope.metadata.model_dump() if envelope.metadata else {}
        content_hash = metadata_dict.get("content_hash")
        session_id = metadata_dict.get("session_id")
        scope = metadata_dict.get("scope", "shared")
        trace_id = metadata_dict.get("trace_id")
        # importance_score: prefer metadata, fallback to confidence.score
        importance_score = metadata_dict.get("importance")
        if importance_score is None and envelope.confidence:
            importance_score = envelope.confidence.score
        
        async with self.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO packet_store (
                    packet_id, packet_type, envelope, timestamp, routing, provenance,
                    thread_id, parent_ids, tags, ttl, content_hash, session_id, scope,
                    trace_id, importance_score
                )
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15)
                ON CONFLICT (packet_id) DO UPDATE SET
                    envelope = EXCLUDED.envelope,
                    timestamp = EXCLUDED.timestamp,
                    thread_id = COALESCE(EXCLUDED.thread_id, packet_store.thread_id),
                    parent_ids = COALESCE(EXCLUDED.parent_ids, packet_store.parent_ids),
                    tags = COALESCE(EXCLUDED.tags, packet_store.tags),
                    ttl = COALESCE(EXCLUDED.ttl, packet_store.ttl),
                    content_hash = COALESCE(EXCLUDED.content_hash, packet_store.content_hash),
                    session_id = COALESCE(EXCLUDED.session_id, packet_store.session_id),
                    scope = COALESCE(EXCLUDED.scope, packet_store.scope),
                    trace_id = COALESCE(EXCLUDED.trace_id, packet_store.trace_id),
                    importance_score = COALESCE(EXCLUDED.importance_score, packet_store.importance_score)
                """,
                envelope.packet_id,
                envelope.packet_type,
                json.dumps(envelope.model_dump(mode="json")),
                envelope.timestamp,
                json.dumps(
                    {"agent": envelope.metadata.agent if envelope.metadata else None}
                ),
                json.dumps(
                    envelope.provenance.model_dump(mode="json")
                    if envelope.provenance
                    else None
                ),
                thread_id,
                parent_ids,
                tags,
                ttl,
                content_hash,
                session_id,
                scope,
                trace_id,
                importance_score,
            )
            logger.debug(f"Inserted packet {envelope.packet_id} with thread_id={thread_id}, parent_ids={parent_ids}, importance={importance_score}")
            return envelope.packet_id

    async def get_packet(self, packet_id: UUID) -> Optional[PacketStoreRow]:
        """Retrieve a packet by ID."""
        async with self.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM packet_store WHERE packet_id = $1", packet_id
            )
            if row:
                return self._row_to_packet_store(row)
            return None

    async def search_packets_by_thread(
        self,
        thread_id: UUID,
        packet_type: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[PacketStoreRow]:
        """
        Search for packets by thread ID.

        Args:
            thread_id: Thread UUID to search for
            packet_type: Optional filter by packet type
            limit: Maximum packets to return
            offset: Offset for pagination

        Returns:
            List of PacketStoreRow sorted by timestamp ascending
        """
        async with self.acquire() as conn:
            if packet_type:
                rows = await conn.fetch(
                    """
                    SELECT * FROM packet_store 
                    WHERE thread_id = $1 AND packet_type = $2
                    ORDER BY timestamp ASC
                    LIMIT $3 OFFSET $4
                    """,
                    thread_id,
                    packet_type,
                    limit,
                    offset,
                )
            else:
                rows = await conn.fetch(
                    """
                    SELECT * FROM packet_store 
                    WHERE thread_id = $1
                    ORDER BY timestamp ASC
                    LIMIT $2 OFFSET $3
                    """,
                    thread_id,
                    limit,
                    offset,
                )
            return [self._row_to_packet_store(r) for r in rows]

    async def search_packets_by_type(
        self,
        packet_type: str,
        agent_id: Optional[str] = None,
        limit: int = 100,
        since: Optional[datetime] = None,
    ) -> list[PacketStoreRow]:
        """
        Search for packets by type.

        Args:
            packet_type: Packet type to search for
            agent_id: Optional filter by agent
            limit: Maximum packets to return
            since: Optional filter by timestamp

        Returns:
            List of PacketStoreRow sorted by timestamp descending
        """
        async with self.acquire() as conn:
            conditions = ["packet_type = $1"]
            params: list[Any] = [packet_type]
            param_idx = 2

            if agent_id:
                conditions.append(f"routing->>'agent' = ${param_idx}")
                params.append(agent_id)
                param_idx += 1

            if since:
                conditions.append(f"timestamp > ${param_idx}")
                params.append(since)
                param_idx += 1

            params.append(limit)

            query = f"""
                SELECT * FROM packet_store 
                WHERE {" AND ".join(conditions)}
                ORDER BY timestamp DESC
                LIMIT ${param_idx}
            """

            rows = await conn.fetch(query, *params)
            return [self._row_to_packet_store(r) for r in rows]

    def _row_to_packet_store(self, row: Any) -> PacketStoreRow:
        """Convert a database row to PacketStoreRow."""
        return PacketStoreRow(
            packet_id=row["packet_id"],
            packet_type=row["packet_type"],
            envelope=json.loads(row["envelope"])
            if isinstance(row["envelope"], str)
            else row["envelope"],
            timestamp=row["timestamp"],
            routing=json.loads(row["routing"])
            if row["routing"] and isinstance(row["routing"], str)
            else row["routing"],
            provenance=json.loads(row["provenance"])
            if row["provenance"] and isinstance(row["provenance"], str)
            else row["provenance"],
            thread_id=row.get("thread_id"),
            parent_ids=row.get("parent_ids") or [],
            tags=row.get("tags") or [],
            ttl=row.get("ttl"),
        )

    # =========================================================================
    # Agent Memory Events Operations
    # =========================================================================

    async def insert_memory_event(
        self,
        agent_id: str,
        event_type: str,
        content: dict[str, Any],
        packet_id: Optional[UUID] = None,
        timestamp: Optional[datetime] = None,
    ) -> UUID:
        """Insert a memory event."""
        event_id = uuid4()
        async with self.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO agent_memory_events (event_id, agent_id, timestamp, packet_id, event_type, content)
                VALUES ($1, $2, $3, $4, $5, $6)
                """,
                event_id,
                agent_id,
                timestamp or datetime.utcnow(),
                packet_id,
                event_type,
                json.dumps(content),
            )
            logger.debug(f"Inserted memory event {event_id} for agent {agent_id}")
            return event_id

    async def get_memory_events(
        self,
        agent_id: str,
        event_type: Optional[str] = None,
        limit: int = 100,
    ) -> list[AgentMemoryEventRow]:
        """Retrieve memory events for an agent."""
        async with self.acquire() as conn:
            if event_type:
                rows = await conn.fetch(
                    """
                    SELECT * FROM agent_memory_events 
                    WHERE agent_id = $1 AND event_type = $2
                    ORDER BY timestamp DESC LIMIT $3
                    """,
                    agent_id,
                    event_type,
                    limit,
                )
            else:
                rows = await conn.fetch(
                    """
                    SELECT * FROM agent_memory_events 
                    WHERE agent_id = $1
                    ORDER BY timestamp DESC LIMIT $2
                    """,
                    agent_id,
                    limit,
                )
            return [
                AgentMemoryEventRow(
                    event_id=r["event_id"],
                    agent_id=r["agent_id"],
                    timestamp=r["timestamp"],
                    packet_id=r["packet_id"],
                    event_type=r["event_type"],
                    content=json.loads(r["content"])
                    if isinstance(r["content"], str)
                    else r["content"],
                )
                for r in rows
            ]

    # =========================================================================
    # Reasoning Traces Operations
    # =========================================================================

    async def insert_reasoning_block(self, block: StructuredReasoningBlock) -> UUID:
        """Insert a reasoning block into reasoning_traces."""
        async with self.acquire() as conn:
            # Extract agent_id from block metadata or use default
            agent_id = "unknown"
            if hasattr(block, "agent_id"):
                agent_id = block.agent_id

            await conn.execute(
                """
                INSERT INTO reasoning_traces (
                    trace_id, agent_id, packet_id, steps, extracted_features,
                    inference_steps, reasoning_tokens, decision_tokens, 
                    confidence_scores, created_at
                )
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
                """,
                block.block_id,
                agent_id,
                block.packet_id,
                json.dumps({"steps": block.inference_steps}),
                json.dumps(block.extracted_features),
                json.dumps(block.inference_steps),
                json.dumps(block.reasoning_tokens),
                json.dumps(block.decision_tokens),
                json.dumps(block.confidence_scores),
                block.timestamp,
            )
            logger.debug(f"Inserted reasoning block {block.block_id}")
            return block.block_id

    async def get_reasoning_traces(
        self,
        agent_id: Optional[str] = None,
        packet_id: Optional[UUID] = None,
        limit: int = 100,
    ) -> list[ReasoningTraceRow]:
        """Retrieve reasoning traces with optional filters."""
        async with self.acquire() as conn:
            if packet_id:
                rows = await conn.fetch(
                    "SELECT * FROM reasoning_traces WHERE packet_id = $1 ORDER BY created_at DESC LIMIT $2",
                    packet_id,
                    limit,
                )
            elif agent_id:
                rows = await conn.fetch(
                    "SELECT * FROM reasoning_traces WHERE agent_id = $1 ORDER BY created_at DESC LIMIT $2",
                    agent_id,
                    limit,
                )
            else:
                rows = await conn.fetch(
                    "SELECT * FROM reasoning_traces ORDER BY created_at DESC LIMIT $1",
                    limit,
                )
            return [
                ReasoningTraceRow(
                    trace_id=r["trace_id"],
                    agent_id=r["agent_id"],
                    packet_id=r["packet_id"],
                    steps=json.loads(r["steps"])
                    if r["steps"] and isinstance(r["steps"], str)
                    else r["steps"],
                    extracted_features=json.loads(r["extracted_features"])
                    if r["extracted_features"]
                    and isinstance(r["extracted_features"], str)
                    else r["extracted_features"],
                    inference_steps=json.loads(r["inference_steps"])
                    if r["inference_steps"] and isinstance(r["inference_steps"], str)
                    else r["inference_steps"],
                    reasoning_tokens=json.loads(r["reasoning_tokens"])
                    if r["reasoning_tokens"] and isinstance(r["reasoning_tokens"], str)
                    else r["reasoning_tokens"],
                    decision_tokens=json.loads(r["decision_tokens"])
                    if r["decision_tokens"] and isinstance(r["decision_tokens"], str)
                    else r["decision_tokens"],
                    confidence_scores=json.loads(r["confidence_scores"])
                    if r["confidence_scores"]
                    and isinstance(r["confidence_scores"], str)
                    else r["confidence_scores"],
                    created_at=r["created_at"],
                )
                for r in rows
            ]

    # =========================================================================
    # Semantic Memory Operations (pgvector)
    # =========================================================================

    async def insert_semantic_embedding(
        self,
        vector: list[float],
        payload: dict[str, Any],
        agent_id: Optional[str] = None,
    ) -> UUID:
        """
        Insert a semantic embedding into semantic_memory.

        Args:
            vector: Embedding vector (1536 dimensions for text-embedding-3-large)
            payload: JSON payload associated with this embedding
            agent_id: Optional agent identifier

        Returns:
            embedding_id of the inserted record
        """
        embedding_id = uuid4()
        async with self.acquire() as conn:
            # pgvector expects vector as string format '[x,y,z,...]'
            vector_str = f"[{','.join(str(v) for v in vector)}]"
            await conn.execute(
                """
                INSERT INTO semantic_memory (embedding_id, agent_id, vector, payload, created_at)
                VALUES ($1, $2, $3::vector, $4, $5)
                """,
                embedding_id,
                agent_id,
                vector_str,
                json.dumps(payload),
                datetime.utcnow(),
            )
            logger.debug(f"Inserted semantic embedding {embedding_id}")
            return embedding_id

    async def search_semantic_memory(
        self,
        query_embedding: list[float],
        top_k: int = 10,
        agent_id: Optional[str] = None,
    ) -> list[SemanticHit]:
        """
        Search semantic memory using cosine similarity.

        Args:
            query_embedding: Query vector
            top_k: Number of results to return
            agent_id: Optional filter by agent

        Returns:
            List of SemanticHit with embedding_id, score, payload
        """
        async with self.acquire() as conn:
            vector_str = f"[{','.join(str(v) for v in query_embedding)}]"

            if agent_id:
                rows = await conn.fetch(
                    """
                    SELECT 
                        embedding_id, 
                        payload,
                        1 - (vector <=> $1::vector) as score
                    FROM semantic_memory
                    WHERE agent_id = $2
                    ORDER BY vector <=> $1::vector
                    LIMIT $3
                    """,
                    vector_str,
                    agent_id,
                    top_k,
                )
            else:
                rows = await conn.fetch(
                    """
                    SELECT 
                        embedding_id, 
                        payload,
                        1 - (vector <=> $1::vector) as score
                    FROM semantic_memory
                    ORDER BY vector <=> $1::vector
                    LIMIT $2
                    """,
                    vector_str,
                    top_k,
                )

            return [
                SemanticHit(
                    embedding_id=r["embedding_id"],
                    score=float(r["score"]),
                    payload=json.loads(r["payload"])
                    if isinstance(r["payload"], str)
                    else r["payload"],
                )
                for r in rows
            ]

    # =========================================================================
    # Graph Checkpoint Operations
    # =========================================================================

    async def save_checkpoint(
        self,
        agent_id: str,
        graph_state: dict[str, Any],
    ) -> UUID:
        """Save or update a graph checkpoint."""
        checkpoint_id = uuid4()
        async with self.acquire() as conn:
            # Upsert based on agent_id
            await conn.execute(
                """
                INSERT INTO graph_checkpoints (checkpoint_id, agent_id, graph_state, updated_at)
                VALUES ($1, $2, $3, $4)
                ON CONFLICT (agent_id) 
                DO UPDATE SET 
                    graph_state = EXCLUDED.graph_state,
                    updated_at = EXCLUDED.updated_at
                """,
                checkpoint_id,
                agent_id,
                json.dumps(graph_state),
                datetime.utcnow(),
            )
            logger.debug(f"Saved checkpoint for agent {agent_id}")
            return checkpoint_id

    async def get_checkpoint(self, agent_id: str) -> Optional[GraphCheckpointRow]:
        """Retrieve the latest checkpoint for an agent."""
        async with self.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM graph_checkpoints WHERE agent_id = $1 ORDER BY updated_at DESC LIMIT 1",
                agent_id,
            )
            if row:
                return GraphCheckpointRow(
                    checkpoint_id=row["checkpoint_id"],
                    agent_id=row["agent_id"],
                    graph_state=json.loads(row["graph_state"])
                    if isinstance(row["graph_state"], str)
                    else row["graph_state"],
                    updated_at=row["updated_at"],
                )
            return None

    # =========================================================================
    # Agent Log Operations
    # =========================================================================

    async def insert_log(
        self,
        agent_id: str,
        level: str,
        message: str,
        metadata: Optional[dict[str, Any]] = None,
    ) -> UUID:
        """Insert a log entry."""
        log_id = uuid4()
        async with self.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO agent_log (log_id, timestamp, agent_id, level, message, metadata)
                VALUES ($1, $2, $3, $4, $5, $6)
                """,
                log_id,
                datetime.utcnow(),
                agent_id,
                level.upper(),
                message,
                json.dumps(metadata) if metadata else None,
            )
            return log_id

    # =========================================================================
    # Knowledge Facts Operations (v1.1.0+)
    # =========================================================================

    async def insert_knowledge_fact(
        self,
        subject: str,
        predicate: str,
        object_value: Any,
        confidence: Optional[float] = None,
        source_packet: Optional[UUID] = None,
        fact_id: Optional[str] = None,
    ) -> UUID:
        """
        Insert a knowledge fact into knowledge_facts table.

        Args:
            subject: Entity or concept being described
            predicate: Relationship or attribute type
            object_value: Value, entity, or structured data
            confidence: Extraction confidence (0.0-1.0)
            source_packet: UUID of originating packet
            fact_id: Optional pre-generated fact_id

        Returns:
            fact_id of inserted record
        """
        fid = UUID(fact_id) if fact_id else uuid4()
        async with self.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO knowledge_facts (fact_id, subject, predicate, object, confidence, source_packet, created_at)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
                ON CONFLICT (fact_id) DO UPDATE SET
                    object = EXCLUDED.object,
                    confidence = EXCLUDED.confidence
                """,
                fid,
                subject,
                predicate,
                json.dumps(object_value),
                confidence or 0.8,
                UUID(source_packet)
                if isinstance(source_packet, str)
                else source_packet,
                datetime.utcnow(),
            )
            logger.debug(f"Inserted knowledge fact {fid}: {subject} - {predicate}")
            return fid

    async def get_facts_by_subject(
        self,
        subject: str,
        predicate: Optional[str] = None,
        limit: int = 100,
    ) -> list[KnowledgeFactRow]:
        """
        Retrieve knowledge facts by subject.

        Args:
            subject: Subject to search for (empty string returns all facts)
            predicate: Optional predicate filter
            limit: Maximum facts to return

        Returns:
            List of KnowledgeFactRow
        """
        async with self.acquire() as conn:
            # If subject is empty, return all facts
            if not subject:
                if predicate:
                    rows = await conn.fetch(
                        """
                        SELECT * FROM knowledge_facts 
                        WHERE predicate = $1
                        ORDER BY created_at DESC LIMIT $2
                        """,
                        predicate,
                        limit,
                    )
                else:
                    rows = await conn.fetch(
                        """
                        SELECT * FROM knowledge_facts 
                        ORDER BY created_at DESC LIMIT $1
                        """,
                        limit,
                    )
            elif predicate:
                rows = await conn.fetch(
                    """
                    SELECT * FROM knowledge_facts 
                    WHERE subject = $1 AND predicate = $2
                    ORDER BY created_at DESC LIMIT $3
                    """,
                    subject,
                    predicate,
                    limit,
                )
            else:
                rows = await conn.fetch(
                    """
                    SELECT * FROM knowledge_facts 
                    WHERE subject = $1
                    ORDER BY created_at DESC LIMIT $2
                    """,
                    subject,
                    limit,
                )
            return [
                KnowledgeFactRow(
                    fact_id=r["fact_id"],
                    subject=r["subject"],
                    predicate=r["predicate"],
                    object=json.loads(r["object"])
                    if isinstance(r["object"], str)
                    else r["object"],
                    confidence=r["confidence"],
                    source_packet=r["source_packet"],
                    created_at=r["created_at"],
                )
                for r in rows
            ]

    async def get_facts_by_packet(
        self,
        packet_id: UUID,
        limit: int = 100,
    ) -> list[KnowledgeFactRow]:
        """
        Retrieve knowledge facts by source packet.

        Args:
            packet_id: Source packet UUID
            limit: Maximum facts to return

        Returns:
            List of KnowledgeFactRow
        """
        async with self.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT * FROM knowledge_facts 
                WHERE source_packet = $1
                ORDER BY created_at DESC LIMIT $2
                """,
                packet_id,
                limit,
            )
            return [
                KnowledgeFactRow(
                    fact_id=r["fact_id"],
                    subject=r["subject"],
                    predicate=r["predicate"],
                    object=json.loads(r["object"])
                    if isinstance(r["object"], str)
                    else r["object"],
                    confidence=r["confidence"],
                    source_packet=r["source_packet"],
                    created_at=r["created_at"],
                )
                for r in rows
            ]

    # =========================================================================
    # Health Check
    # =========================================================================

    async def health_check(self) -> dict[str, Any]:
        """Check database connectivity and return status."""
        try:
            async with self.acquire() as conn:
                result = await conn.fetchval("SELECT 1")
                return {
                    "status": "healthy",
                    "database": "connected",
                    "pool_size": self._pool.get_size() if self._pool else 0,
                }
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {
                "status": "unhealthy",
                "database": "disconnected",
                "error": str(e),
            }


# Singleton instance
_repository: Optional[SubstrateRepository] = None


def get_repository() -> SubstrateRepository:
    """Get repository singleton (must be initialized first)."""
    if _repository is None:
        raise RuntimeError("Repository not initialized. Call init_repository() first.")
    return _repository


async def init_repository(database_url: str, **kwargs) -> SubstrateRepository:
    """Initialize the repository singleton."""
    global _repository
    _repository = SubstrateRepository(database_url, **kwargs)
    await _repository.connect()
    return _repository


async def close_repository() -> None:
    """Close the repository connection."""
    global _repository
    if _repository:
        await _repository.disconnect()
        _repository = None
