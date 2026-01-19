"""
L9 Memory Substrate - Repository Layer
Version: 1.0.0

Thin repository for Postgres + pgvector database access.
Provides async functions for all memory substrate operations.
"""

import json
import structlog
from contextlib import asynccontextmanager
from contextvars import ContextVar
from datetime import datetime
from typing import Any, AsyncGenerator, Optional
from uuid import UUID, uuid4

import asyncpg


async def _init_json_codecs(conn: asyncpg.Connection) -> None:
    """Initialize connection with JSON codec for JSONB columns."""
    await conn.set_type_codec(
        'jsonb',
        encoder=json.dumps,
        decoder=json.loads,
        schema='pg_catalog'
    )
    await conn.set_type_codec(
        'json',
        encoder=json.dumps,
        decoder=json.loads,
        schema='pg_catalog'
    )

# Context variable for RLS-scoped connection (used within transactions)
_current_rls_connection: ContextVar[Optional[asyncpg.Connection]] = ContextVar(
    "_current_rls_connection", default=None
)

from core.schemas import PacketEnvelope, SemanticHit
from memory.governance_gate import (
    build_scope_project_filter,
    require_governance_context,
)
from memory.substrate_models import (
    AgentMemoryEventRow,
    GraphCheckpointRow,
    KnowledgeFactRow,
    PacketStoreRow,
    ReasoningTraceRow,
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
                init=_init_json_codecs,  # Register JSON codecs for JSONB columns
            )
            logger.info("Database connection pool initialized with JSON codecs")

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
        require_governance_context("repository.acquire")
        async with self._pool.acquire() as conn:
            yield conn

    @asynccontextmanager
    async def transaction(
        self,
        tenant_id: Optional[str] = None,
        org_id: Optional[str] = None,
        user_id: Optional[str] = None,
        role: str = "end_user",
    ) -> AsyncGenerator[asyncpg.Connection, None]:
        """
        Acquire a connection and start a transaction with RLS scope.
        
        Sets RLS session variables using SET LOCAL within the transaction,
        so the scope persists for all operations in the transaction.
        
        The connection is stored in a context variable so repository methods
        can use it instead of acquiring a new connection.
        
        Args:
            tenant_id: Optional tenant UUID for RLS isolation
            org_id: Optional organization UUID for RLS isolation
            user_id: Optional user UUID for RLS isolation
            role: User role for RLS policy enforcement
            
        Yields:
            Connection within a transaction with RLS scope set
        """
        if self._pool is None:
            raise RuntimeError("Repository not connected. Call connect() first.")
        ctx = require_governance_context("repository.transaction")
        if tenant_id and tenant_id != ctx.tenant_id:
            raise RuntimeError("tenant_id must be derived server-side")
        if org_id and org_id != ctx.org_id:
            raise RuntimeError("org_id must be derived server-side")
        if user_id and user_id != ctx.user_id:
            raise RuntimeError("user_id must be derived server-side")
        if role != ctx.role:
            raise RuntimeError("role must be derived server-side")
        
        async with self._pool.acquire() as conn:
            async with conn.transaction():
                # Set RLS scope within transaction (SET LOCAL makes it transaction-scoped)
                if ctx.tenant_id and ctx.org_id and ctx.user_id:
                    await conn.execute(
                        """SELECT l9_set_scope($1::uuid, $2::uuid, $3::uuid, $4::text)""",
                        ctx.tenant_id,
                        ctx.org_id,
                        ctx.user_id,
                        ctx.role,
                    )
                
                # Store connection in context variable for repository methods to use
                token = _current_rls_connection.set(conn)
                try:
                    yield conn
                finally:
                    # Restore previous context (or clear if None)
                    _current_rls_connection.reset(token)

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
        
        # Use RLS-scoped connection if available, otherwise acquire new one
        require_governance_context("repository.insert_packet")
        rls_conn = _current_rls_connection.get()
        if rls_conn:
            # Use existing RLS-scoped connection (within transaction)
            conn = rls_conn
            # Execute directly without context manager
            await self._insert_packet_with_connection(conn, envelope, thread_id, tags, ttl, parent_ids, metadata_dict, content_hash, session_id, scope, trace_id, importance_score)
            return envelope.packet_id
        else:
            # No RLS scope - use normal connection pool
            async with self.acquire() as conn:
                await self._insert_packet_with_connection(conn, envelope, thread_id, tags, ttl, parent_ids, metadata_dict, content_hash, session_id, scope, trace_id, importance_score)
                return envelope.packet_id
    
    async def _insert_packet_with_connection(
        self,
        conn: asyncpg.Connection,
        envelope: PacketEnvelope,
        thread_id,
        tags,
        ttl,
        parent_ids,
        metadata_dict,
        content_hash,
        session_id,
        scope,
        trace_id,
        importance_score,
    ) -> None:
        """Helper method to insert packet using provided connection."""
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

    async def get_packet(self, packet_id: UUID) -> Optional[PacketStoreRow]:
        """Retrieve a packet by ID."""
        ctx = require_governance_context("repository.get_packet")
        async with self.acquire() as conn:
            filter_clause, params, _ = build_scope_project_filter(
                ctx, param_idx=2, table_alias="packet_store"
            )
            row = await conn.fetchrow(
                f"SELECT * FROM packet_store WHERE packet_id = $1 {filter_clause}",
                packet_id,
                *params,
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
        ctx = require_governance_context("repository.search_packets_by_thread")
        async with self.acquire() as conn:
            if packet_type:
                filter_clause, params, _ = build_scope_project_filter(
                    ctx, param_idx=5, table_alias="packet_store"
                )
                rows = await conn.fetch(
                    f"""
                    SELECT * FROM packet_store 
                    WHERE thread_id = $1 AND packet_type = $2
                    {filter_clause}
                    ORDER BY timestamp ASC
                    LIMIT $3 OFFSET $4
                    """,
                    thread_id,
                    packet_type,
                    limit,
                    offset,
                    *params,
                )
            else:
                filter_clause, params, _ = build_scope_project_filter(
                    ctx, param_idx=4, table_alias="packet_store"
                )
                rows = await conn.fetch(
                    f"""
                    SELECT * FROM packet_store 
                    WHERE thread_id = $1
                    {filter_clause}
                    ORDER BY timestamp ASC
                    LIMIT $2 OFFSET $3
                    """,
                    thread_id,
                    limit,
                    offset,
                    *params,
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
        ctx = require_governance_context("repository.search_packets_by_type")
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

            filter_clause, filter_params, param_idx = build_scope_project_filter(
                ctx, param_idx=param_idx, table_alias="packet_store"
            )
            params.extend(filter_params)
            params.append(limit)

            query = f"""
                SELECT * FROM packet_store 
                WHERE {" AND ".join(conditions)}
                {filter_clause}
                ORDER BY timestamp DESC
                LIMIT ${param_idx}
            """

            rows = await conn.fetch(query, *params)
            return [self._row_to_packet_store(r) for r in rows]

    def _row_to_packet_store(self, row: Any) -> PacketStoreRow:
        """Convert a database row to PacketStoreRow (all 22 columns from migrations 0001, 0002, 0008)."""
        return PacketStoreRow(
            # Core fields (migration 0001)
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
            # Threading & lineage (migration 0002)
            thread_id=row.get("thread_id"),
            parent_ids=row.get("parent_ids") or [],
            tags=row.get("tags") or [],
            ttl=row.get("ttl"),
            # 10X Enhancements (migration 0008)
            scope=row.get("scope", "shared"),
            importance_score=row.get("importance_score", 0.5),
            access_count=row.get("access_count", 0),
            last_accessed=row.get("last_accessed"),
            confidence_updated_at=row.get("confidence_updated_at"),
            contradiction_count=row.get("contradiction_count", 0),
            chunk_count=row.get("chunk_count", 1),
            is_chunked=row.get("is_chunked", False),
            content_hash=row.get("content_hash"),
            processing_status=row.get("processing_status", "complete"),
            # Multi-tenant identity (migration 0008)
            tenant_id=row.get("tenant_id"),
            org_id=row.get("org_id"),
            user_id=row.get("user_id"),
            correlation_id=row.get("correlation_id"),
            # Tracing (migration 0008)
            session_id=row.get("session_id"),
            trace_id=row.get("trace_id"),
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
        
        # Use RLS-scoped connection if available, otherwise acquire new one
        require_governance_context("repository.insert_memory_event")
        rls_conn = _current_rls_connection.get()
        if rls_conn:
            # Use existing RLS-scoped connection (within transaction)
            await rls_conn.execute(
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
        else:
            # No RLS scope - use normal connection pool
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
        ctx = require_governance_context("repository.get_memory_events")
        async with self.acquire() as conn:
            if event_type:
                filter_clause, params, _ = build_scope_project_filter(
                    ctx, param_idx=4, table_alias="packet_store"
                )
                rows = await conn.fetch(
                    f"""
                    SELECT ame.*
                    FROM agent_memory_events ame
                    LEFT JOIN packet_store ON packet_store.packet_id = ame.packet_id
                    WHERE ame.agent_id = $1 AND ame.event_type = $2
                    {filter_clause}
                    ORDER BY timestamp DESC LIMIT $3
                    """,
                    agent_id,
                    event_type,
                    limit,
                    *params,
                )
            else:
                filter_clause, params, _ = build_scope_project_filter(
                    ctx, param_idx=3, table_alias="packet_store"
                )
                rows = await conn.fetch(
                    f"""
                    SELECT ame.*
                    FROM agent_memory_events ame
                    LEFT JOIN packet_store ON packet_store.packet_id = ame.packet_id
                    WHERE ame.agent_id = $1
                    {filter_clause}
                    ORDER BY timestamp DESC LIMIT $2
                    """,
                    agent_id,
                    limit,
                    *params,
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
        # Use RLS-scoped connection if available, otherwise acquire new one
        require_governance_context("repository.insert_reasoning_block")
        rls_conn = _current_rls_connection.get()
        if rls_conn:
            # Use existing RLS-scoped connection (within transaction)
            await self._insert_reasoning_block_with_connection(rls_conn, block)
            return block.block_id
        else:
            # No RLS scope - use normal connection pool
            async with self.acquire() as conn:
                await self._insert_reasoning_block_with_connection(conn, block)
                return block.block_id
    
    async def _insert_reasoning_block_with_connection(
        self, conn: asyncpg.Connection, block: StructuredReasoningBlock
    ) -> None:
        """Helper method to insert reasoning block using provided connection."""
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

    async def get_reasoning_traces(
        self,
        agent_id: Optional[str] = None,
        packet_id: Optional[UUID] = None,
        limit: int = 100,
    ) -> list[ReasoningTraceRow]:
        """Retrieve reasoning traces with optional filters."""
        ctx = require_governance_context("repository.get_reasoning_traces")
        async with self.acquire() as conn:
            if packet_id:
                filter_clause, params, _ = build_scope_project_filter(
                    ctx, param_idx=3, table_alias="packet_store"
                )
                rows = await conn.fetch(
                    f"""
                    SELECT rt.*
                    FROM reasoning_traces rt
                    INNER JOIN packet_store ON packet_store.packet_id = rt.packet_id
                    WHERE rt.packet_id = $1
                    {filter_clause}
                    ORDER BY rt.created_at DESC LIMIT $2
                    """,
                    packet_id,
                    limit,
                    *params,
                )
            elif agent_id:
                filter_clause, params, _ = build_scope_project_filter(
                    ctx, param_idx=3, table_alias="packet_store"
                )
                rows = await conn.fetch(
                    f"""
                    SELECT rt.*
                    FROM reasoning_traces rt
                    INNER JOIN packet_store ON packet_store.packet_id = rt.packet_id
                    WHERE rt.agent_id = $1
                    {filter_clause}
                    ORDER BY rt.created_at DESC LIMIT $2
                    """,
                    agent_id,
                    limit,
                    *params,
                )
            else:
                filter_clause, params, _ = build_scope_project_filter(
                    ctx, param_idx=2, table_alias="packet_store"
                )
                rows = await conn.fetch(
                    f"""
                    SELECT rt.*
                    FROM reasoning_traces rt
                    INNER JOIN packet_store ON packet_store.packet_id = rt.packet_id
                    WHERE TRUE
                    {filter_clause}
                    ORDER BY rt.created_at DESC LIMIT $1
                    """,
                    limit,
                    *params,
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
    # Knowledge Facts Operations (v2.1.0 - GMP-67 Unified Pipeline)
    # =========================================================================

    async def insert_knowledge_fact(
        self,
        fact_id: UUID,
        subject: str,
        predicate: str,
        object_value: Any,
        confidence: float,
        source_packet: Optional[UUID],
    ) -> KnowledgeFactRow:
        """
        Insert or update knowledge fact (idempotent via UPSERT).
        
        Uses ON CONFLICT (source_packet, subject, predicate) DO UPDATE
        to prevent duplicate facts from same packet. This ensures:
        - Same packet enriched twice = no duplicates
        - Fact updates are atomic
        
        Args:
            fact_id: UUID for the fact (used for insert)
            subject: Entity or concept being described
            predicate: Relationship or attribute type
            object_value: Value, entity, or structured data
            confidence: Extraction confidence (0.0-1.0)
            source_packet: Source packet ID (foreign key)
            
        Returns:
            KnowledgeFactRow with assigned/existing fact_id
            
        Raises:
            Exception: DB error (caller decides whether to propagate or log)
        """
        created_at = datetime.utcnow()
        
        # Serialize object_value to JSON (always required for JSONB column)
        # Even strings must be JSON-encoded (wrapped in quotes) for PostgreSQL
        object_json = json.dumps(object_value)
        
        # Use RLS-scoped connection if available, otherwise acquire new one
        require_governance_context("repository.insert_knowledge_fact")
        rls_conn = _current_rls_connection.get()
        
        if rls_conn:
            row = await self._insert_knowledge_fact_with_connection(
                rls_conn, fact_id, subject, predicate, object_json,
                confidence, source_packet, created_at
            )
        else:
            async with self.acquire() as conn:
                row = await self._insert_knowledge_fact_with_connection(
                    conn, fact_id, subject, predicate, object_json,
                    confidence, source_packet, created_at
                )
        
        return row

    async def _insert_knowledge_fact_with_connection(
        self,
        conn: asyncpg.Connection,
        fact_id: UUID,
        subject: str,
        predicate: str,
        object_json: str,
        confidence: float,
        source_packet: Optional[UUID],
        created_at: datetime,
    ) -> KnowledgeFactRow:
        """Helper to insert fact using provided connection."""
        # UPSERT: Insert or update on conflict (idempotent)
        # Note: Requires unique index on (source_packet, subject, predicate)
        row = await conn.fetchrow(
            """
            INSERT INTO knowledge_facts (
                fact_id, subject, predicate, object, confidence, source_packet, created_at
            ) VALUES ($1, $2, $3, $4::jsonb, $5, $6, $7)
            ON CONFLICT (source_packet, subject, predicate) 
            WHERE source_packet IS NOT NULL
            DO UPDATE SET 
                object = EXCLUDED.object,
                confidence = EXCLUDED.confidence
            RETURNING fact_id, subject, predicate, object, confidence, source_packet, created_at
            """,
            fact_id,
            subject,
            predicate,
            object_json,
            confidence,
            source_packet,
            created_at,
        )
        
        logger.debug(
            f"Upserted knowledge fact {row['fact_id']} "
            f"({subject} - {predicate}) for packet {source_packet}"
        )
        
        return KnowledgeFactRow(
            fact_id=row["fact_id"],
            subject=row["subject"],
            predicate=row["predicate"],
            object=json.loads(row["object"]) if isinstance(row["object"], str) else row["object"],
            confidence=row["confidence"],
            source_packet=row["source_packet"],
            created_at=row["created_at"],
        )

    async def get_knowledge_facts(
        self,
        source_packet: Optional[UUID] = None,
        subject: Optional[str] = None,
        limit: int = 100,
    ) -> list[KnowledgeFactRow]:
        """
        Retrieve knowledge facts with optional filters.
        
        Args:
            source_packet: Filter by source packet ID
            subject: Filter by subject (exact match)
            limit: Maximum results to return
            
        Returns:
            List of KnowledgeFactRow
        """
        ctx = require_governance_context("repository.get_knowledge_facts")
        async with self.acquire() as conn:
            conditions = ["deprecated = FALSE OR deprecated IS NULL"]
            params: list[Any] = []
            param_idx = 1
            
            if source_packet:
                conditions.append(f"source_packet = ${param_idx}")
                params.append(source_packet)
                param_idx += 1
            
            if subject:
                conditions.append(f"subject = ${param_idx}")
                params.append(subject)
                param_idx += 1
            
            filter_clause, filter_params, param_idx = build_scope_project_filter(
                ctx, param_idx=param_idx, table_alias="packet_store"
            )
            params.extend(filter_params)
            params.append(limit)

            query = f"""
                SELECT knowledge_facts.*
                FROM knowledge_facts
                INNER JOIN packet_store ON packet_store.packet_id = knowledge_facts.source_packet
                WHERE {" AND ".join(conditions)}
                {filter_clause}
                ORDER BY created_at DESC
                LIMIT ${param_idx}
            """
            
            rows = await conn.fetch(query, *params)
            return [
                KnowledgeFactRow(
                    fact_id=r["fact_id"],
                    subject=r["subject"],
                    predicate=r["predicate"],
                    object=json.loads(r["object"]) if isinstance(r["object"], str) else r["object"],
                    confidence=r["confidence"],
                    source_packet=r["source_packet"],
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
        require_governance_context("repository.insert_semantic_embedding")
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
        ctx = require_governance_context("repository.search_semantic_memory")
        async with self.acquire() as conn:
            vector_str = f"[{','.join(str(v) for v in query_embedding)}]"

            if agent_id:
                filter_clause, params, _ = build_scope_project_filter(
                    ctx, param_idx=4, table_alias="packet_store"
                )
                rows = await conn.fetch(
                    f"""
                    SELECT 
                        sm.embedding_id, 
                        sm.payload,
                        1 - (sm.vector <=> $1::vector) as score
                    FROM semantic_memory sm
                    INNER JOIN packet_store ON packet_store.packet_id = (sm.payload->>'packet_id')::uuid
                    WHERE sm.agent_id = $2
                    {filter_clause}
                    ORDER BY sm.vector <=> $1::vector
                    LIMIT $3
                    """,
                    vector_str,
                    agent_id,
                    top_k,
                    *params,
                )
            else:
                filter_clause, params, _ = build_scope_project_filter(
                    ctx, param_idx=3, table_alias="packet_store"
                )
                rows = await conn.fetch(
                    f"""
                    SELECT 
                        sm.embedding_id, 
                        sm.payload,
                        1 - (sm.vector <=> $1::vector) as score
                    FROM semantic_memory sm
                    INNER JOIN packet_store ON packet_store.packet_id = (sm.payload->>'packet_id')::uuid
                    WHERE TRUE
                    {filter_clause}
                    ORDER BY sm.vector <=> $1::vector
                    LIMIT $2
                    """,
                    vector_str,
                    top_k,
                    *params,
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
        reason: str = "manual",
    ) -> UUID:
        """
        Save a graph checkpoint.

        After migration 0014, supports multi-checkpoint per agent.
        Falls back to upsert if 'reason' column doesn't exist (pre-0014 schema).

        Args:
            agent_id: Agent identifier
            graph_state: State dict to persist
            reason: Checkpoint trigger reason

        Returns:
            Checkpoint UUID
        """
        checkpoint_id = uuid4()
        ctx = require_governance_context("repository.save_checkpoint")
        graph_state = {**graph_state, "project_id": ctx.project_id}
        
        # Use RLS-scoped connection if available, otherwise acquire new one
        rls_conn = _current_rls_connection.get()
        if rls_conn:
            # Use existing RLS-scoped connection (within transaction)
            await self._save_checkpoint_with_connection(rls_conn, checkpoint_id, agent_id, graph_state, reason)
            return checkpoint_id
        else:
            # No RLS scope - use normal connection pool
            async with self.acquire() as conn:
                await self._save_checkpoint_with_connection(conn, checkpoint_id, agent_id, graph_state, reason)
                return checkpoint_id
    
    async def _save_checkpoint_with_connection(
        self,
        conn: asyncpg.Connection,
        checkpoint_id: UUID,
        agent_id: str,
        graph_state: dict[str, Any],
        reason: str,
    ) -> None:
        """Helper method to save checkpoint using provided connection."""
        # Try INSERT with reason column (post-0014 schema)
        try:
            await conn.execute(
                """
                INSERT INTO graph_checkpoints (checkpoint_id, agent_id, graph_state, reason, updated_at)
                VALUES ($1, $2, $3, $4, $5)
                """,
                checkpoint_id,
                agent_id,
                json.dumps(graph_state),
                reason,
                datetime.utcnow(),
            )
        except Exception as e:
            # Fallback: pre-0014 schema without reason column (upsert)
            if "reason" in str(e).lower() or "column" in str(e).lower():
                logger.debug("Falling back to upsert (pre-0014 schema)")
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
            else:
                raise

        logger.debug(f"Saved checkpoint for agent {agent_id}", reason=reason)

    async def get_checkpoint(self, agent_id: str) -> Optional[GraphCheckpointRow]:
        """Retrieve the latest checkpoint for an agent."""
        ctx = require_governance_context("repository.get_checkpoint")
        async with self.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT * FROM graph_checkpoints
                WHERE agent_id = $1
                AND graph_state->>'project_id' = $2
                ORDER BY updated_at DESC LIMIT 1
                """,
                agent_id,
                ctx.project_id,
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

    async def list_checkpoints(
        self,
        agent_id: str,
        limit: int = 10,
    ) -> list[GraphCheckpointRow]:
        """
        List checkpoints for an agent.

        Supports both pre-0014 (single checkpoint) and post-0014 (multi-checkpoint) schemas.

        Args:
            agent_id: Agent identifier
            limit: Maximum checkpoints to return

        Returns:
            List of GraphCheckpointRow ordered by updated_at DESC
        """
        ctx = require_governance_context("repository.list_checkpoints")
        async with self.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT * FROM graph_checkpoints
                WHERE agent_id = $1
                AND graph_state->>'project_id' = $2
                ORDER BY updated_at DESC
                LIMIT $3
                """,
                agent_id,
                ctx.project_id,
                limit,
            )
            checkpoints = []
            for row in rows:
                # Parse graph_state
                graph_state = row["graph_state"]
                if isinstance(graph_state, str):
                    graph_state = json.loads(graph_state)

                # Handle optional fields (post-0014 schema)
                reason = row.get("reason") if "reason" in row.keys() else None
                checkpoint_number = row.get("checkpoint_number") if "checkpoint_number" in row.keys() else None

                checkpoints.append(
                    GraphCheckpointRow(
                        checkpoint_id=row["checkpoint_id"],
                        agent_id=row["agent_id"],
                        graph_state=graph_state,
                        updated_at=row["updated_at"],
                        reason=reason,
                        checkpoint_number=checkpoint_number,
                    )
                )
            return checkpoints

    async def delete_checkpoint(self, agent_id: str) -> bool:
        """
        Delete all checkpoints for an agent.

        Args:
            agent_id: Agent identifier

        Returns:
            True if any checkpoint was deleted, False if none found
        """
        ctx = require_governance_context("repository.delete_checkpoint")
        async with self.acquire() as conn:
            result = await conn.execute(
                """
                DELETE FROM graph_checkpoints
                WHERE agent_id = $1
                AND graph_state->>'project_id' = $2
                """,
                agent_id,
                ctx.project_id,
            )
            deleted = result.split()[-1] != "0"
            if deleted:
                logger.debug(f"Deleted checkpoints for agent {agent_id}")
            return deleted

    async def delete_old_checkpoints(
        self,
        agent_id: str,
        keep_last: int = 10,
    ) -> int:
        """
        Delete old checkpoints, keeping the most recent N.

        For retention policy: keeps most recent checkpoints, deletes older ones.

        Args:
            agent_id: Agent identifier
            keep_last: Number of recent checkpoints to keep

        Returns:
            Number of checkpoints deleted
        """
        ctx = require_governance_context("repository.delete_old_checkpoints")
        async with self.acquire() as conn:
            # Delete all checkpoints except the most recent keep_last
            result = await conn.execute(
                """
                DELETE FROM graph_checkpoints
                WHERE agent_id = $1
                AND graph_state->>'project_id' = $3
                AND checkpoint_id NOT IN (
                    SELECT checkpoint_id
                    FROM graph_checkpoints
                    WHERE agent_id = $1
                    AND graph_state->>'project_id' = $3
                    ORDER BY updated_at DESC
                    LIMIT $2
                )
                """,
                agent_id,
                keep_last,
                ctx.project_id,
            )
            # Parse "DELETE N" to get count
            deleted_count = int(result.split()[-1])
            if deleted_count > 0:
                logger.debug(
                    f"Deleted {deleted_count} old checkpoints for agent {agent_id}",
                    keep_last=keep_last,
                )
            return deleted_count

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
        require_governance_context("repository.insert_log")
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
        ctx = require_governance_context("repository.get_facts_by_subject")
        async with self.acquire() as conn:
            # If subject is empty, return all facts
            if not subject:
                if predicate:
                    filter_clause, params, _ = build_scope_project_filter(
                        ctx, param_idx=3, table_alias="packet_store"
                    )
                    rows = await conn.fetch(
                        f"""
                        SELECT knowledge_facts.*
                        FROM knowledge_facts
                        INNER JOIN packet_store ON packet_store.packet_id = knowledge_facts.source_packet
                        WHERE predicate = $1
                        {filter_clause}
                        ORDER BY created_at DESC LIMIT $2
                        """,
                        predicate,
                        limit,
                        *params,
                    )
                else:
                    filter_clause, params, _ = build_scope_project_filter(
                        ctx, param_idx=2, table_alias="packet_store"
                    )
                    rows = await conn.fetch(
                        f"""
                        SELECT knowledge_facts.*
                        FROM knowledge_facts
                        INNER JOIN packet_store ON packet_store.packet_id = knowledge_facts.source_packet
                        WHERE TRUE
                        {filter_clause}
                        ORDER BY created_at DESC LIMIT $1
                        """,
                        limit,
                        *params,
                    )
            elif predicate:
                filter_clause, params, _ = build_scope_project_filter(
                    ctx, param_idx=3, table_alias="packet_store"
                )
                rows = await conn.fetch(
                    f"""
                    SELECT knowledge_facts.*
                    FROM knowledge_facts
                    INNER JOIN packet_store ON packet_store.packet_id = knowledge_facts.source_packet
                    WHERE subject = $1 AND predicate = $2
                    {filter_clause}
                    ORDER BY created_at DESC LIMIT $3
                    """,
                    subject,
                    predicate,
                    limit,
                    *params,
                )
            else:
                filter_clause, params, _ = build_scope_project_filter(
                    ctx, param_idx=3, table_alias="packet_store"
                )
                rows = await conn.fetch(
                    f"""
                    SELECT knowledge_facts.*
                    FROM knowledge_facts
                    INNER JOIN packet_store ON packet_store.packet_id = knowledge_facts.source_packet
                    WHERE subject = $1
                    {filter_clause}
                    ORDER BY created_at DESC LIMIT $2
                    """,
                    subject,
                    limit,
                    *params,
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
        ctx = require_governance_context("repository.get_facts_by_packet")
        async with self.acquire() as conn:
            filter_clause, params, _ = build_scope_project_filter(
                ctx, param_idx=3, table_alias="packet_store"
            )
            rows = await conn.fetch(
                f"""
                SELECT knowledge_facts.*
                FROM knowledge_facts
                INNER JOIN packet_store ON packet_store.packet_id = knowledge_facts.source_packet
                WHERE source_packet = $1
                {filter_clause}
                ORDER BY created_at DESC LIMIT $2
                """,
                packet_id,
                limit,
                *params,
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
    # Spec v3.0 Required Methods - Fact Deprecation & Contradiction Tracking
    # =========================================================================

    async def deprecate_fact(
        self,
        fact_id: UUID,
        reason: str,
    ) -> bool:
        """
        Soft-deprecate a knowledge fact.

        Spec: state.contradiction_tracking.deprecate_fact

        Args:
            fact_id: UUID of fact to deprecate
            reason: Reason for deprecation

        Returns:
            True if deprecated, False if not found
        """
        require_governance_context("repository.deprecate_fact")
        async with self.acquire() as conn:
            result = await conn.execute(
                """
                UPDATE knowledge_facts
                SET deprecated = TRUE,
                    deprecated_at = NOW(),
                    deprecated_reason = $2
                WHERE fact_id = $1 AND deprecated = FALSE
                """,
                fact_id,
                reason,
            )
            # Check if any row was updated
            return "UPDATE 1" in result

    async def increment_contradiction_count(
        self,
        fact_id: UUID,
    ) -> int:
        """
        Increment contradiction count for a fact.

        Args:
            fact_id: UUID of fact

        Returns:
            New contradiction count
        """
        require_governance_context("repository.increment_contradiction_count")
        async with self.acquire() as conn:
            row = await conn.fetchrow(
                """
                UPDATE knowledge_facts
                SET contradiction_count = contradiction_count + 1
                WHERE fact_id = $1
                RETURNING contradiction_count
                """,
                fact_id,
            )
            return row["contradiction_count"] if row else 0

    async def get_active_facts(
        self,
        subject: str,
        min_confidence: float = 0.0,
    ) -> list[KnowledgeFactRow]:
        """
        Get active (non-deprecated) facts for a subject.

        Spec: state.contradiction_tracking.get_active_facts

        Args:
            subject: Subject to get facts for
            min_confidence: Minimum confidence threshold

        Returns:
            List of active KnowledgeFactRow
        """
        ctx = require_governance_context("repository.get_active_facts")
        async with self.acquire() as conn:
            filter_clause, params, _ = build_scope_project_filter(
                ctx, param_idx=3, table_alias="packet_store"
            )
            rows = await conn.fetch(
                f"""
                SELECT knowledge_facts.*
                FROM knowledge_facts
                INNER JOIN packet_store ON packet_store.packet_id = knowledge_facts.source_packet
                WHERE subject = $1 
                  AND deprecated = FALSE
                  AND confidence >= $2
                {filter_clause}
                ORDER BY confidence DESC, created_at DESC
                """,
                subject,
                min_confidence,
                *params,
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

    async def get_contradiction_count(
        self,
        fact_id: UUID,
    ) -> int:
        """
        Get contradiction count for a fact.

        Spec: state.contradiction_tracking.get_contradiction_count

        Args:
            fact_id: UUID of fact

        Returns:
            Contradiction count (0 if not found)
        """
        require_governance_context("repository.get_contradiction_count")
        async with self.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT contradiction_count FROM knowledge_facts
                WHERE fact_id = $1
                """,
                fact_id,
            )
            return row["contradiction_count"] if row else 0

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


def get_substrate_repository(database_url: Optional[str] = None) -> SubstrateRepository:
    """
    Get or create a SubstrateRepository instance.
    
    If database_url is provided, creates a new repository instance.
    If no database_url, returns the singleton (must be initialized first).
    
    This is an alias for world_model compatibility.
    """
    if database_url:
        # Create new instance (caller must manage lifecycle)
        return SubstrateRepository(database_url)
    return get_repository()


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
