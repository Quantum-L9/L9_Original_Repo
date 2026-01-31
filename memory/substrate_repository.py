"""
L9 Memory Substrate - Repository Layer
Version: 1.0.0

Thin repository for Postgres + pgvector database access.
Provides async functions for all memory substrate operations.
"""

from __future__ import annotations

# ============================================================================
__dora_meta__ = {
    "component_name": "Repository Layer",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2025-12-09T01:02:49Z",
    "updated_at": "2026-01-17T23:47:56Z",
    "layer": "learning",
    "domain": "memory_substrate",
    "module_name": "substrate_repository",
    "type": "service",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": ["PostgreSQL"],
        "memory_layers": ["episodic_memory", "semantic_memory", "working_memory"],
        "imported_by": [
            "core.integration.tool_pattern_extractor",
            "core.singleton_registry",
            "core.tools.tool_embeddings",
            "memory.__init__",
            "memory.agent_persistence",
            "memory.checkpoint.postgres_saver",
            "memory.consolidation",
            "memory.index_syncer",
            "memory.reasoning_replay",
            "memory.retention_engine",
        ],
    },
}
# ============================================================================

import json
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from contextvars import ContextVar
from datetime import UTC, datetime, timezone
from typing import Any
from uuid import UUID, uuid4

import asyncpg
import structlog

from core.singleton_auto_registry import register_singleton, register_singleton_closer
from memory.vector_search_config import get_vector_config


async def _init_json_codecs(conn: asyncpg.Connection) -> None:
    """Initialize connection with JSON codec for JSONB columns."""
    await conn.set_type_codec(
        "jsonb", encoder=json.dumps, decoder=json.loads, schema="pg_catalog"
    )
    await conn.set_type_codec(
        "json", encoder=json.dumps, decoder=json.loads, schema="pg_catalog"
    )


# Context variable for RLS-scoped connection (used within transactions)
_current_rls_connection: ContextVar[asyncpg.Connection | None] = ContextVar(
    "_current_rls_connection", default=None
)

from core.schemas import PacketEnvelope, SemanticHit
from memory.governance_gate import (
    build_scope_project_filter,
    require_governance_context,
)
from memory.substrate_models import (
    AgentMemoryEventRow,
    EpisodicEventRow,
    GraphCheckpointRow,
    KnowledgeFactRow,
    PacketStoreRow,
    ReasoningTraceRow,
    SemanticFactRow,
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
        self._pool: asyncpg.Pool | None = None

    async def connect(self) -> None:
        """Initialize connection pool with lazy initialization and timeouts."""
        if self._pool is None:
            # GMP-MEM-FIX: Use min_size=0 for lazy pool (no connections at startup)
            # This prevents hanging when multiple services start simultaneously
            self._pool = await asyncpg.create_pool(
                self._database_url,
                min_size=0,  # Lazy: create connections on-demand, not at startup
                max_size=self._pool_size + self._max_overflow,
                init=_init_json_codecs,  # Register JSON codecs for JSONB columns
                timeout=30,  # Connection acquisition timeout (seconds)
                command_timeout=60,  # Query execution timeout (seconds)
            )
            logger.info(
                "Database connection pool initialized",
                min_size=0,
                max_size=self._pool_size + self._max_overflow,
            )

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

    @asynccontextmanager
    async def transaction(
        self,
        tenant_id: str | None = None,
        org_id: str | None = None,
        user_id: str | None = None,
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

        async with self._pool.acquire() as conn, conn.transaction():
            # Set RLS scope within transaction (SET LOCAL makes it transaction-scoped)
            if tenant_id and org_id and user_id:
                await conn.execute(
                    """SELECT l9_set_scope($1::uuid, $2::uuid, $3::uuid, $4::text)""",
                    tenant_id,
                    org_id,
                    user_id,
                    role,
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
        rls_conn = _current_rls_connection.get()
        if rls_conn:
            # Use existing RLS-scoped connection (within transaction)
            conn = rls_conn
            # Execute directly without context manager
            await self._insert_packet_with_connection(
                conn,
                envelope,
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
            )
            return envelope.packet_id
        # No RLS scope - use normal connection pool
        async with self.acquire() as conn:
            await self._insert_packet_with_connection(
                conn,
                envelope,
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
            )
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
        """Helper method to insert packet using provided connection."""
        # GMP-C1-GOVERNANCE: Pass dict directly to asyncpg.
        # The JSONB codec (line 57) will serialize it. DO NOT json.dumps() here
        # as that causes double-serialization and breaks JSON path constraints.
        envelope_dict = envelope.model_dump(mode="json")
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
            envelope_dict,  # Pass dict, asyncpg codec handles serialization
            envelope.timestamp,
            # routing and provenance are also JSONB - pass dicts, not json.dumps()
            {"agent": envelope.metadata.agent if envelope.metadata else None},
            (
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
        logger.debug(
            f"Inserted packet {envelope.packet_id} with thread_id={thread_id}, parent_ids={parent_ids}, importance={importance_score}"
        )

    async def get_packet(self, packet_id: UUID) -> PacketStoreRow | None:
        """Retrieve a packet by ID."""
        # GMP-70: Governance scope filtering
        ctx = require_governance_context("repository.get_packet")
        filter_clause, filter_params, _ = build_scope_project_filter(
            ctx, param_idx=2, table_alias="packet_store"
        )

        async with self.acquire() as conn:
            row = await conn.fetchrow(
                f"SELECT * FROM packet_store WHERE packet_id = $1 {filter_clause}",
                packet_id,
                *filter_params,
            )
            if row:
                return self._row_to_packet_store(row)
            return None

    async def check_packet_exists(self, packet_id: UUID) -> bool:
        """
        Check if a packet with the given ID already exists.

        Used for duplicate detection in the ingestion pipeline.
        This is a lightweight existence check without RLS filtering
        since deduplication is global (same packet_id = same packet).

        Args:
            packet_id: The packet UUID to check

        Returns:
            True if packet exists, False otherwise
        """
        async with self.acquire() as conn:
            result = await conn.fetchval(
                "SELECT EXISTS(SELECT 1 FROM packet_store WHERE packet_id = $1)",
                packet_id,
            )
            return bool(result)

    async def search_packets_by_thread(
        self,
        thread_id: UUID,
        packet_type: str | None = None,
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
        # GMP-70: Governance scope filtering
        ctx = require_governance_context("repository.search_packets_by_thread")

        async with self.acquire() as conn:
            if packet_type:
                filter_clause, filter_params, _ = build_scope_project_filter(
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
                    *filter_params,
                )
            else:
                filter_clause, filter_params, _ = build_scope_project_filter(
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
                    *filter_params,
                )
            return [self._row_to_packet_store(r) for r in rows]

    async def search_packets_by_type(
        self,
        packet_type: str,
        agent_id: str | None = None,
        limit: int = 100,
        since: datetime | None = None,
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
        # GMP-70: Governance scope filtering
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

            # Add governance scope filter
            _filter_clause, filter_params, param_idx = build_scope_project_filter(
                ctx, param_idx=param_idx, table_alias="packet_store"
            )
            # Strip leading "AND " from filter_clause since we're building conditions list
            conditions.append(f"scope = ANY(${param_idx - 2})")
            conditions.append(f"envelope->'metadata'->>'project_id' = ${param_idx - 1}")
            params.extend(filter_params)

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
        """Convert a database row to PacketStoreRow (all 22 columns from migrations 0001, 0002, 0008)."""
        return PacketStoreRow(
            # Core fields (migration 0001)
            packet_id=row["packet_id"],
            packet_type=row["packet_type"],
            envelope=(
                json.loads(row["envelope"])
                if isinstance(row["envelope"], str)
                else row["envelope"]
            ),
            timestamp=row["timestamp"],
            routing=(
                json.loads(row["routing"])
                if row["routing"] and isinstance(row["routing"], str)
                else row["routing"]
            ),
            provenance=(
                json.loads(row["provenance"])
                if row["provenance"] and isinstance(row["provenance"], str)
                else row["provenance"]
            ),
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
        packet_id: UUID | None = None,
        timestamp: datetime | None = None,
    ) -> UUID:
        """Insert a memory event."""
        event_id = uuid4()

        # Use RLS-scoped connection if available, otherwise acquire new one
        rls_conn = _current_rls_connection.get()
        if rls_conn:
            # Use existing RLS-scoped connection (within transaction)
            # GMP-JSONB-GOV-FIX: Pass dict directly - asyncpg JSONB codec handles serialization
            await rls_conn.execute(
                """
                INSERT INTO agent_memory_events (event_id, agent_id, timestamp, packet_id, event_type, content)
                VALUES ($1, $2, $3, $4, $5, $6)
                """,
                event_id,
                agent_id,
                timestamp or datetime.now(UTC),
                packet_id,
                event_type,
                content,  # Dict, not json.dumps() - asyncpg codec serializes JSONB
            )
            logger.debug(f"Inserted memory event {event_id} for agent {agent_id}")
            return event_id
        # No RLS scope - use normal connection pool
        # GMP-JSONB-GOV-FIX: Pass dict directly - asyncpg JSONB codec handles serialization
        async with self.acquire() as conn:
            await conn.execute(
                """
                    INSERT INTO agent_memory_events (event_id, agent_id, timestamp, packet_id, event_type, content)
                    VALUES ($1, $2, $3, $4, $5, $6)
                    """,
                event_id,
                agent_id,
                timestamp or datetime.now(UTC),
                packet_id,
                event_type,
                content,  # Dict, not json.dumps() - asyncpg codec serializes JSONB
            )
            logger.debug(f"Inserted memory event {event_id} for agent {agent_id}")
            return event_id

    async def get_memory_events(
        self,
        agent_id: str,
        event_type: str | None = None,
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
                    content=(
                        json.loads(r["content"])
                        if isinstance(r["content"], str)
                        else r["content"]
                    ),
                )
                for r in rows
            ]

    # =========================================================================
    # Reasoning Traces Operations
    # =========================================================================

    async def insert_reasoning_block(self, block: StructuredReasoningBlock) -> UUID:
        """Insert a reasoning block into reasoning_traces."""
        # Use RLS-scoped connection if available, otherwise acquire new one
        rls_conn = _current_rls_connection.get()
        if rls_conn:
            # Use existing RLS-scoped connection (within transaction)
            await self._insert_reasoning_block_with_connection(rls_conn, block)
            return block.block_id
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

        # GMP-JSONB-GOV-FIX: Pass dicts directly - asyncpg JSONB codec handles serialization
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
            {"steps": block.inference_steps},  # Dict, not json.dumps()
            block.extracted_features,  # Dict, not json.dumps()
            block.inference_steps,  # Dict/list, not json.dumps()
            block.reasoning_tokens,  # Dict/list, not json.dumps()
            block.decision_tokens,  # Dict/list, not json.dumps()
            block.confidence_scores,  # Dict/list, not json.dumps()
            block.timestamp,
        )
        logger.debug(f"Inserted reasoning block {block.block_id}")

    async def get_reasoning_traces(
        self,
        agent_id: str | None = None,
        packet_id: UUID | None = None,
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
                    steps=(
                        json.loads(r["steps"])
                        if r["steps"] and isinstance(r["steps"], str)
                        else r["steps"]
                    ),
                    extracted_features=(
                        json.loads(r["extracted_features"])
                        if r["extracted_features"]
                        and isinstance(r["extracted_features"], str)
                        else r["extracted_features"]
                    ),
                    inference_steps=(
                        json.loads(r["inference_steps"])
                        if r["inference_steps"]
                        and isinstance(r["inference_steps"], str)
                        else r["inference_steps"]
                    ),
                    reasoning_tokens=(
                        json.loads(r["reasoning_tokens"])
                        if r["reasoning_tokens"]
                        and isinstance(r["reasoning_tokens"], str)
                        else r["reasoning_tokens"]
                    ),
                    decision_tokens=(
                        json.loads(r["decision_tokens"])
                        if r["decision_tokens"]
                        and isinstance(r["decision_tokens"], str)
                        else r["decision_tokens"]
                    ),
                    confidence_scores=(
                        json.loads(r["confidence_scores"])
                        if r["confidence_scores"]
                        and isinstance(r["confidence_scores"], str)
                        else r["confidence_scores"]
                    ),
                    created_at=r["created_at"],
                )
                for r in rows
            ]

    # =========================================================================
    # Knowledge Facts Operations (v2.1.0 - GMP-67 Unified Pipeline)
    # =========================================================================

    async def insert_knowledge_fact(
        self,
        subject: str,
        predicate: str,
        object_value: Any,
        confidence: float,
        source_packet: UUID | None,
        fact_id: UUID | None = None,
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
        # Generate fact_id if not provided
        if fact_id is None:
            fact_id = uuid4()

        created_at = datetime.now(UTC)

        # Serialize object_value to JSON (always required for JSONB column)
        # Even strings must be JSON-encoded (wrapped in quotes) for PostgreSQL
        object_json = json.dumps(object_value)

        # Use RLS-scoped connection if available, otherwise acquire new one
        rls_conn = _current_rls_connection.get()

        if rls_conn:
            row = await self._insert_knowledge_fact_with_connection(
                rls_conn,
                fact_id,
                subject,
                predicate,
                object_json,
                confidence,
                source_packet,
                created_at,
            )
        else:
            async with self.acquire() as conn:
                row = await self._insert_knowledge_fact_with_connection(
                    conn,
                    fact_id,
                    subject,
                    predicate,
                    object_json,
                    confidence,
                    source_packet,
                    created_at,
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
        source_packet: UUID | None,
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
            object=(
                json.loads(row["object"])
                if isinstance(row["object"], str)
                else row["object"]
            ),
            confidence=row["confidence"],
            source_packet=row["source_packet"],
            created_at=row["created_at"],
        )

    async def get_knowledge_facts(
        self,
        source_packet: UUID | None = None,
        subject: str | None = None,
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

            params.append(limit)

            query = f"""
                SELECT * FROM knowledge_facts
                WHERE {" AND ".join(conditions)}
                ORDER BY created_at DESC
                LIMIT ${param_idx}
            """

            rows = await conn.fetch(query, *params)
            return [
                KnowledgeFactRow(
                    fact_id=r["fact_id"],
                    subject=r["subject"],
                    predicate=r["predicate"],
                    object=(
                        json.loads(r["object"])
                        if isinstance(r["object"], str)
                        else r["object"]
                    ),
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
        agent_id: str | None = None,
        scope: str = "shared",  # RLS scope: 'developer', 'global', 'shared', 'l-private'
    ) -> UUID:
        """
        Insert a semantic embedding into semantic_memory.

        Args:
            vector: Embedding vector (1536 dimensions for text-embedding-3-large)
            payload: JSON payload associated with this embedding
            agent_id: Optional agent identifier
            scope: RLS scope for row-level security (default: 'shared')

        Returns:
            embedding_id of the inserted record
        """
        embedding_id = uuid4()
        rls_conn = _current_rls_connection.get()
        if rls_conn:
            await self._insert_semantic_embedding_with_connection(
                rls_conn, embedding_id, vector, payload, agent_id, scope
            )
            return embedding_id

        async with self.acquire() as conn:
            await self._insert_semantic_embedding_with_connection(
                conn, embedding_id, vector, payload, agent_id, scope
            )
            return embedding_id

    async def _insert_semantic_embedding_with_connection(
        self,
        conn: asyncpg.Connection,
        embedding_id: UUID,
        vector: list[float],
        payload: dict[str, Any],
        agent_id: str | None,
        scope: str = "shared",
    ) -> None:
        """Helper to insert semantic embedding using provided connection."""
        vector_str = f"[{','.join(str(v) for v in vector)}]"
        await conn.execute(
            """
            INSERT INTO semantic_memory (embedding_id, agent_id, vector, payload, created_at, scope)
            VALUES ($1, $2, $3::vector, $4, $5, $6)
            """,
            embedding_id,
            agent_id,
            vector_str,
            payload,  # asyncpg handles dict -> jsonb automatically (don't double-encode)
            datetime.now(UTC),
            scope,
        )
        logger.debug(f"Inserted semantic embedding {embedding_id} with scope={scope}")

    async def search_semantic_memory(
        self,
        query_embedding: list[float],
        top_k: int = 10,
        agent_id: str | None = None,
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
            # Apply vector search optimization
            config = get_vector_config()
            await config.apply(conn)

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
                    payload=(
                        json.loads(r["payload"])
                        if isinstance(r["payload"], str)
                        else r["payload"]
                    ),
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

        # Use RLS-scoped connection if available, otherwise acquire new one
        rls_conn = _current_rls_connection.get()
        if rls_conn:
            # Use existing RLS-scoped connection (within transaction)
            await self._save_checkpoint_with_connection(
                rls_conn, checkpoint_id, agent_id, graph_state, reason
            )
            return checkpoint_id
        # No RLS scope - use normal connection pool
        async with self.acquire() as conn:
            await self._save_checkpoint_with_connection(
                conn, checkpoint_id, agent_id, graph_state, reason
            )
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
                datetime.now(UTC),
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
                    datetime.now(UTC),
                )
            else:
                raise

        logger.debug(f"Saved checkpoint for agent {agent_id}", reason=reason)

    async def get_checkpoint(self, agent_id: str) -> GraphCheckpointRow | None:
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
                    graph_state=(
                        json.loads(row["graph_state"])
                        if isinstance(row["graph_state"], str)
                        else row["graph_state"]
                    ),
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
        async with self.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT * FROM graph_checkpoints
                WHERE agent_id = $1
                ORDER BY updated_at DESC
                LIMIT $2
                """,
                agent_id,
                limit,
            )
            checkpoints = []
            for row in rows:
                # Parse graph_state
                graph_state = row["graph_state"]
                if isinstance(graph_state, str):
                    graph_state = json.loads(graph_state)

                # Handle optional fields (post-0014 schema)
                reason = row.get("reason") if "reason" in row else None
                checkpoint_number = (
                    row.get("checkpoint_number") if "checkpoint_number" in row else None
                )

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
        async with self.acquire() as conn:
            result = await conn.execute(
                "DELETE FROM graph_checkpoints WHERE agent_id = $1",
                agent_id,
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
        async with self.acquire() as conn:
            # Delete all checkpoints except the most recent keep_last
            result = await conn.execute(
                """
                DELETE FROM graph_checkpoints
                WHERE agent_id = $1
                AND checkpoint_id NOT IN (
                    SELECT checkpoint_id
                    FROM graph_checkpoints
                    WHERE agent_id = $1
                    ORDER BY updated_at DESC
                    LIMIT $2
                )
                """,
                agent_id,
                keep_last,
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
        metadata: dict[str, Any] | None = None,
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
                datetime.now(UTC),
                agent_id,
                level.upper(),
                message,
                json.dumps(metadata) if metadata else None,
            )
            return log_id

    async def get_facts_by_subject(
        self,
        subject: str,
        predicate: str | None = None,
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
                    object=(
                        json.loads(r["object"])
                        if isinstance(r["object"], str)
                        else r["object"]
                    ),
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
                    object=(
                        json.loads(r["object"])
                        if isinstance(r["object"], str)
                        else r["object"]
                    ),
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
        async with self.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT * FROM knowledge_facts
                WHERE subject = $1
                  AND deprecated = FALSE
                  AND confidence >= $2
                ORDER BY confidence DESC, created_at DESC
                """,
                subject,
                min_confidence,
            )
            return [
                KnowledgeFactRow(
                    fact_id=r["fact_id"],
                    subject=r["subject"],
                    predicate=r["predicate"],
                    object=(
                        json.loads(r["object"])
                        if isinstance(r["object"], str)
                        else r["object"]
                    ),
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
    # Semantic Facts Operations (Migration 0018 - Memory Spec v3.1)
    # =========================================================================

    async def insert_semantic_fact(
        self,
        fact_text: str,
        triplet: dict[str, Any] | None = None,
        embedding: list[float] | None = None,
        importance: float = 0.5,
        tags: list[str] | None = None,
        tier: str = "general",
        source: str | None = None,
        source_packet_id: UUID | None = None,
        confidence: float = 0.8,
        agent_id: str | None = None,
        tenant_id: UUID | None = None,
        org_id: UUID | None = None,
        user_id: UUID | None = None,
    ) -> UUID:
        """
        Insert a semantic fact into the semantic_facts table.

        Part of frontier-grade dual semantic+episodic memory architecture.

        Args:
            fact_text: Human-readable fact statement
            triplet: SPO triplet {"subject": "...", "predicate": "...", "object": "..."}
            embedding: Vector embedding (1536 dimensions, truncated from text-embedding-3-large)
            importance: Importance score 0.0-1.0
            tags: Categorization tags
            tier: Memory tier (identity, project, session, general)
            source: Origin (user_stated, inferred, extracted)
            source_packet_id: Originating packet UUID
            confidence: Extraction/inference confidence
            agent_id: Agent that created this fact
            tenant_id, org_id, user_id: Multi-tenant ownership

        Returns:
            UUID of the inserted fact
        """

        fact_id = uuid4()

        # Use defaults for multi-tenant IDs if not provided
        _tenant_id = tenant_id or UUID("00000000-0000-0000-0000-000000000000")
        _org_id = org_id or UUID("00000000-0000-0000-0000-000000000000")
        _user_id = user_id or UUID("00000000-0000-0000-0000-000000000000")

        async with self.acquire() as conn:
            if embedding:
                # With embedding
                await conn.execute(
                    """
                    INSERT INTO semantic_facts (
                        fact_id, tenant_id, org_id, user_id, agent_id,
                        fact_text, triplet, embedding, importance, tags,
                        tier, source, source_packet_id, confidence
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8::vector, $9, $10, $11, $12, $13, $14)
                    """,
                    fact_id,
                    _tenant_id,
                    _org_id,
                    _user_id,
                    agent_id,
                    fact_text,
                    json.dumps(triplet or {}),
                    f"[{','.join(str(x) for x in embedding)}]",
                    importance,
                    tags or [],
                    tier,
                    source,
                    source_packet_id,
                    confidence,
                )
            else:
                # Without embedding
                await conn.execute(
                    """
                    INSERT INTO semantic_facts (
                        fact_id, tenant_id, org_id, user_id, agent_id,
                        fact_text, triplet, importance, tags,
                        tier, source, source_packet_id, confidence
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13)
                    """,
                    fact_id,
                    _tenant_id,
                    _org_id,
                    _user_id,
                    agent_id,
                    fact_text,
                    json.dumps(triplet or {}),
                    importance,
                    tags or [],
                    tier,
                    source,
                    source_packet_id,
                    confidence,
                )

        logger.debug(f"Inserted semantic fact {fact_id}: {fact_text[:50]}...")
        return fact_id

    async def get_semantic_facts_by_subject(
        self,
        subject: str,
        tier: str | None = None,
        limit: int = 50,
    ) -> list:
        """
        Retrieve semantic facts by subject from triplet.

        Args:
            subject: Subject to search for in triplet.subject
            tier: Optional tier filter (identity, project, session, general)
            limit: Maximum facts to return

        Returns:
            List of SemanticFactRow objects
        """

        async with self.acquire() as conn:
            if tier:
                rows = await conn.fetch(
                    """
                    SELECT * FROM semantic_facts
                    WHERE triplet->>'subject' = $1 AND tier = $2
                    ORDER BY importance DESC, created_at DESC
                    LIMIT $3
                    """,
                    subject,
                    tier,
                    limit,
                )
            else:
                rows = await conn.fetch(
                    """
                    SELECT * FROM semantic_facts
                    WHERE triplet->>'subject' = $1
                    ORDER BY importance DESC, created_at DESC
                    LIMIT $2
                    """,
                    subject,
                    limit,
                )

        return [
            SemanticFactRow(
                fact_id=r["fact_id"],
                tenant_id=r["tenant_id"],
                org_id=r["org_id"],
                user_id=r["user_id"],
                agent_id=r.get("agent_id"),
                fact_text=r["fact_text"],
                triplet=(
                    r["triplet"]
                    if isinstance(r["triplet"], dict)
                    else json.loads(r["triplet"] or "{}")
                ),
                importance=r["importance"],
                access_count=r["access_count"],
                last_accessed=r.get("last_accessed"),
                tags=r.get("tags") or [],
                tier=r.get("tier", "general"),
                source=r.get("source"),
                source_packet_id=r.get("source_packet_id"),
                confidence=r.get("confidence", 0.8),
                validated_at=r.get("validated_at"),
                validated_by=r.get("validated_by"),
                created_at=r["created_at"],
                updated_at=r["updated_at"],
            )
            for r in rows
        ]

    async def get_semantic_facts_by_tier(
        self,
        tier: str,
        limit: int = 100,
    ) -> list:
        """
        Retrieve semantic facts by memory tier.

        Args:
            tier: Memory tier (identity, project, session, general)
            limit: Maximum facts to return

        Returns:
            List of SemanticFactRow objects
        """

        async with self.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT * FROM semantic_facts
                WHERE tier = $1
                ORDER BY importance DESC, created_at DESC
                LIMIT $2
                """,
                tier,
                limit,
            )

        return [
            SemanticFactRow(
                fact_id=r["fact_id"],
                tenant_id=r["tenant_id"],
                org_id=r["org_id"],
                user_id=r["user_id"],
                agent_id=r.get("agent_id"),
                fact_text=r["fact_text"],
                triplet=(
                    r["triplet"]
                    if isinstance(r["triplet"], dict)
                    else json.loads(r["triplet"] or "{}")
                ),
                importance=r["importance"],
                access_count=r["access_count"],
                last_accessed=r.get("last_accessed"),
                tags=r.get("tags") or [],
                tier=r.get("tier", "general"),
                source=r.get("source"),
                source_packet_id=r.get("source_packet_id"),
                confidence=r.get("confidence", 0.8),
                validated_at=r.get("validated_at"),
                validated_by=r.get("validated_by"),
                created_at=r["created_at"],
                updated_at=r["updated_at"],
            )
            for r in rows
        ]

    async def update_fact_importance(
        self,
        fact_id: UUID,
        new_importance: float,
        touch_access: bool = True,
    ) -> bool:
        """
        Update importance score for a semantic fact.

        Used by active memory management to elevate frequently-used facts.

        Args:
            fact_id: UUID of fact to update
            new_importance: New importance value (0.0-1.0)
            touch_access: If True, also update last_accessed and access_count

        Returns:
            True if fact was found and updated
        """
        async with self.acquire() as conn:
            if touch_access:
                result = await conn.execute(
                    """
                    UPDATE semantic_facts
                    SET importance = $2,
                        access_count = access_count + 1,
                        last_accessed = NOW()
                    WHERE fact_id = $1
                    """,
                    fact_id,
                    new_importance,
                )
            else:
                result = await conn.execute(
                    """
                    UPDATE semantic_facts
                    SET importance = $2
                    WHERE fact_id = $1
                    """,
                    fact_id,
                    new_importance,
                )

        updated = result.split()[-1] != "0"
        if updated:
            logger.debug(f"Updated fact {fact_id} importance to {new_importance}")
        return updated

    # =========================================================================
    # Episodic Events Operations (Migration 0019 - Memory Spec v3.1)
    # =========================================================================

    async def insert_episodic_event(
        self,
        observation: str,
        event_timestamp: datetime,
        event_type: str = "general",
        entities: list[str] | None = None,
        context: dict[str, Any] | None = None,
        outcome: str | None = None,
        severity: float = 0.5,
        source_packet_id: UUID | None = None,
        parent_event_id: UUID | None = None,
        session_id: UUID | None = None,
        agent_id: str | None = None,
        tenant_id: UUID | None = None,
        org_id: UUID | None = None,
        user_id: UUID | None = None,
    ) -> UUID:
        """
        Insert an episodic event into the episodic_events table.

        Part of frontier-grade dual semantic+episodic memory architecture.

        Args:
            observation: Human-readable description of what happened
            event_timestamp: When the event occurred (CRITICAL for temporal queries)
            event_type: Type categorization
            entities: Entities involved in the event
            context: Additional context as JSONB
            outcome: What was the result
            severity: Event importance 0.0-1.0
            source_packet_id: Originating packet UUID
            parent_event_id: Parent event for event chains
            session_id: Session grouping
            agent_id: Agent that observed this event
            tenant_id, org_id, user_id: Multi-tenant ownership

        Returns:
            UUID of the inserted event
        """

        event_id = uuid4()

        # Use defaults for multi-tenant IDs if not provided
        _tenant_id = tenant_id or UUID("00000000-0000-0000-0000-000000000000")
        _org_id = org_id or UUID("00000000-0000-0000-0000-000000000000")
        _user_id = user_id or UUID("00000000-0000-0000-0000-000000000000")

        async with self.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO episodic_events (
                    event_id, tenant_id, org_id, user_id, agent_id,
                    observation, event_type, event_timestamp,
                    entities, context, outcome, severity,
                    source_packet_id, parent_event_id, session_id
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15)
                """,
                event_id,
                _tenant_id,
                _org_id,
                _user_id,
                agent_id,
                observation,
                event_type,
                event_timestamp,
                entities or [],
                json.dumps(context or {}),
                outcome,
                severity,
                source_packet_id,
                parent_event_id,
                session_id,
            )

        logger.debug(f"Inserted episodic event {event_id}: {observation[:50]}...")
        return event_id

    async def get_events_by_time_range(
        self,
        start_time: datetime,
        end_time: datetime,
        entities: list[str] | None = None,
        event_type: str | None = None,
        limit: int = 100,
    ) -> list:
        """
        Retrieve episodic events within a time range.

        Primary query pattern for episodic memory - "What happened between X and Y?"

        Args:
            start_time: Start of time range
            end_time: End of time range
            entities: Optional filter by entities involved
            event_type: Optional filter by event type
            limit: Maximum events to return

        Returns:
            List of EpisodicEventRow objects ordered by timestamp DESC
        """

        async with self.acquire() as conn:
            if entities and event_type:
                rows = await conn.fetch(
                    """
                    SELECT * FROM episodic_events
                    WHERE event_timestamp BETWEEN $1 AND $2
                    AND entities && $3
                    AND event_type = $4
                    ORDER BY event_timestamp DESC
                    LIMIT $5
                    """,
                    start_time,
                    end_time,
                    entities,
                    event_type,
                    limit,
                )
            elif entities:
                rows = await conn.fetch(
                    """
                    SELECT * FROM episodic_events
                    WHERE event_timestamp BETWEEN $1 AND $2
                    AND entities && $3
                    ORDER BY event_timestamp DESC
                    LIMIT $4
                    """,
                    start_time,
                    end_time,
                    entities,
                    limit,
                )
            elif event_type:
                rows = await conn.fetch(
                    """
                    SELECT * FROM episodic_events
                    WHERE event_timestamp BETWEEN $1 AND $2
                    AND event_type = $3
                    ORDER BY event_timestamp DESC
                    LIMIT $4
                    """,
                    start_time,
                    end_time,
                    event_type,
                    limit,
                )
            else:
                rows = await conn.fetch(
                    """
                    SELECT * FROM episodic_events
                    WHERE event_timestamp BETWEEN $1 AND $2
                    ORDER BY event_timestamp DESC
                    LIMIT $3
                    """,
                    start_time,
                    end_time,
                    limit,
                )

        return [
            EpisodicEventRow(
                event_id=r["event_id"],
                tenant_id=r["tenant_id"],
                org_id=r["org_id"],
                user_id=r["user_id"],
                agent_id=r.get("agent_id"),
                observation=r["observation"],
                event_type=r.get("event_type", "general"),
                event_timestamp=r["event_timestamp"],
                duration_seconds=r.get("duration_seconds"),
                entities=r.get("entities") or [],
                context=(
                    r["context"]
                    if isinstance(r["context"], dict)
                    else json.loads(r["context"] or "{}")
                ),
                outcome=r.get("outcome"),
                severity=r.get("severity", 0.5),
                impact_score=r.get("impact_score", 0.5),
                source_packet_id=r.get("source_packet_id"),
                parent_event_id=r.get("parent_event_id"),
                session_id=r.get("session_id"),
                thread_id=r.get("thread_id"),
                decay_factor=r.get("decay_factor", 1.0),
                last_recalled=r.get("last_recalled"),
                recall_count=r.get("recall_count", 0),
                created_at=r["created_at"],
                updated_at=r["updated_at"],
            )
            for r in rows
        ]

    async def link_event_to_facts(
        self,
        event_id: UUID,
        fact_ids: list[UUID],
        relationship_type: str = "involves",
        strength: float = 1.0,
    ) -> int:
        """
        Create links between an episodic event and semantic facts.

        Part of frontier-grade fact-episode linking pattern.

        Args:
            event_id: UUID of the episodic event
            fact_ids: List of semantic fact UUIDs to link
            relationship_type: Type of relationship (involves, confirms, contradicts, updates)
            strength: Link strength 0.0-1.0

        Returns:
            Number of links created
        """
        if not fact_ids:
            return 0

        # Batch insert using executemany for better performance
        async with self.acquire() as conn:
            # Prepare batch data
            batch_data = [
                (
                    uuid4(),  # link_id
                    event_id,
                    fact_id,
                    relationship_type,
                    strength,
                )
                for fact_id in fact_ids
            ]

            try:
                # Batch insert with ON CONFLICT
                await conn.executemany(
                    """
                    INSERT INTO episodic_semantic_links (
                        link_id, event_id, fact_id, relationship_type, strength
                    ) VALUES ($1, $2, $3, $4, $5)
                    ON CONFLICT (event_id, fact_id) DO UPDATE
                    SET relationship_type = EXCLUDED.relationship_type,
                        strength = EXCLUDED.strength
                    """,
                    batch_data,
                )
                links_created = len(fact_ids)
            except Exception as e:
                logger.warning(f"Failed to link event {event_id} to facts: {e}")
                links_created = 0

        logger.debug(f"Linked event {event_id} to {links_created} facts")
        return links_created

    async def get_events_for_fact(
        self,
        fact_id: UUID,
        limit: int = 50,
    ) -> list:
        """
        Find all episodic events linked to a semantic fact.

        Enables queries like "When was this fact observed/used?"

        Args:
            fact_id: UUID of the semantic fact
            limit: Maximum events to return

        Returns:
            List of EpisodicEventRow objects ordered by timestamp DESC
        """

        async with self.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT e.* FROM episodic_events e
                INNER JOIN episodic_semantic_links l ON l.event_id = e.event_id
                WHERE l.fact_id = $1
                ORDER BY e.event_timestamp DESC
                LIMIT $2
                """,
                fact_id,
                limit,
            )

        return [
            EpisodicEventRow(
                event_id=r["event_id"],
                tenant_id=r["tenant_id"],
                org_id=r["org_id"],
                user_id=r["user_id"],
                agent_id=r.get("agent_id"),
                observation=r["observation"],
                event_type=r.get("event_type", "general"),
                event_timestamp=r["event_timestamp"],
                duration_seconds=r.get("duration_seconds"),
                entities=r.get("entities") or [],
                context=(
                    r["context"]
                    if isinstance(r["context"], dict)
                    else json.loads(r["context"] or "{}")
                ),
                outcome=r.get("outcome"),
                severity=r.get("severity", 0.5),
                impact_score=r.get("impact_score", 0.5),
                source_packet_id=r.get("source_packet_id"),
                parent_event_id=r.get("parent_event_id"),
                session_id=r.get("session_id"),
                thread_id=r.get("thread_id"),
                decay_factor=r.get("decay_factor", 1.0),
                last_recalled=r.get("last_recalled"),
                recall_count=r.get("recall_count", 0),
                created_at=r["created_at"],
                updated_at=r["updated_at"],
            )
            for r in rows
        ]

    async def get_facts_for_event(
        self,
        event_id: UUID,
    ) -> list:
        """
        Find all semantic facts linked to an episodic event.

        Enables queries like "What facts are relevant to this event?"

        Args:
            event_id: UUID of the episodic event

        Returns:
            List of SemanticFactRow objects
        """

        async with self.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT f.* FROM semantic_facts f
                INNER JOIN episodic_semantic_links l ON l.fact_id = f.fact_id
                WHERE l.event_id = $1
                ORDER BY l.strength DESC, f.importance DESC
                """,
                event_id,
            )

        return [
            SemanticFactRow(
                fact_id=r["fact_id"],
                tenant_id=r["tenant_id"],
                org_id=r["org_id"],
                user_id=r["user_id"],
                agent_id=r.get("agent_id"),
                fact_text=r["fact_text"],
                triplet=(
                    r["triplet"]
                    if isinstance(r["triplet"], dict)
                    else json.loads(r["triplet"] or "{}")
                ),
                importance=r["importance"],
                access_count=r["access_count"],
                last_accessed=r.get("last_accessed"),
                tags=r.get("tags") or [],
                tier=r.get("tier", "general"),
                source=r.get("source"),
                source_packet_id=r.get("source_packet_id"),
                confidence=r.get("confidence", 0.8),
                validated_at=r.get("validated_at"),
                validated_by=r.get("validated_by"),
                created_at=r["created_at"],
                updated_at=r["updated_at"],
            )
            for r in rows
        ]

    # =========================================================================
    # Time-Travel Queries (Migration 0022)
    # =========================================================================

    async def get_facts_as_of(
        self,
        point_in_time: datetime,
        tier: str | None = None,
        limit: int = 100,
    ) -> list:
        """
        Time-travel query: Get facts that were valid at a specific point in time.

        This enables "what did we know at time T?" queries for debugging,
        audit trails, and temporal reasoning.

        Args:
            point_in_time: The moment to query (e.g., datetime(2025, 6, 15))
            tier: Optional filter by memory tier
            limit: Maximum results

        Returns:
            List of SemanticFactRow objects that were valid at point_in_time
        """
        logger.debug(f"Time-travel query: facts as of {point_in_time}, tier={tier}")

        async with self.acquire() as conn:
            if tier:
                rows = await conn.fetch(
                    """
                    SELECT * FROM semantic_facts
                    WHERE (valid_from IS NULL OR valid_from <= $1)
                    AND (valid_to IS NULL OR valid_to > $1)
                    AND tier = $2
                    ORDER BY importance DESC, created_at DESC
                    LIMIT $3
                    """,
                    point_in_time,
                    tier,
                    limit,
                )
            else:
                rows = await conn.fetch(
                    """
                    SELECT * FROM semantic_facts
                    WHERE (valid_from IS NULL OR valid_from <= $1)
                    AND (valid_to IS NULL OR valid_to > $1)
                    ORDER BY importance DESC, created_at DESC
                    LIMIT $2
                    """,
                    point_in_time,
                    limit,
                )

        return [self._row_to_semantic_fact(r) for r in rows]

    async def get_fact_history(
        self,
        fact_text: str,
        tenant_id: UUID | None = None,
    ) -> list:
        """
        Get the version history of a fact (all versions, including superseded).

        Useful for debugging how knowledge evolved over time.

        Args:
            fact_text: The fact text to search for (fuzzy match)
            tenant_id: Optional tenant filter

        Returns:
            List of SemanticFactRow versions ordered by valid_from DESC
        """
        logger.debug(f"Fact history query: {fact_text[:50]}...")

        async with self.acquire() as conn:
            if tenant_id:
                rows = await conn.fetch(
                    """
                    SELECT * FROM semantic_facts
                    WHERE fact_text ILIKE $1
                    AND tenant_id = $2
                    ORDER BY COALESCE(valid_from, created_at) DESC
                    """,
                    f"%{fact_text}%",
                    tenant_id,
                )
            else:
                rows = await conn.fetch(
                    """
                    SELECT * FROM semantic_facts
                    WHERE fact_text ILIKE $1
                    ORDER BY COALESCE(valid_from, created_at) DESC
                    """,
                    f"%{fact_text}%",
                )

        return [self._row_to_semantic_fact(r) for r in rows]

    async def supersede_fact(
        self,
        old_fact_id: UUID,
        new_fact_text: str,
        reason: str | None = None,
    ) -> UUID:
        """
        Mark a fact as superseded and create a new version.

        This maintains the version chain for time-travel queries.

        Args:
            old_fact_id: The fact being superseded
            new_fact_text: The replacement fact text
            reason: Optional reason for supersession

        Returns:
            UUID of the new fact
        """
        now = datetime.now(UTC)

        async with self.acquire() as conn, conn.transaction():
            # Get the old fact
            old_row = await conn.fetchrow(
                "SELECT * FROM semantic_facts WHERE fact_id = $1",
                old_fact_id,
            )

            if not old_row:
                raise ValueError(f"Fact {old_fact_id} not found")

            # Create new fact (inheriting properties from old)
            new_fact_id = uuid4()
            await conn.execute(
                """
                    INSERT INTO semantic_facts (
                        fact_id, tenant_id, org_id, user_id, agent_id,
                        fact_text, triplet, importance, tags, tier,
                        source, confidence, valid_from, embedding
                    )
                    SELECT
                        $1, tenant_id, org_id, user_id, agent_id,
                        $2, triplet, importance, tags, tier,
                        'supersession', confidence, $3, embedding
                    FROM semantic_facts
                    WHERE fact_id = $4
                    """,
                new_fact_id,
                new_fact_text,
                now,
                old_fact_id,
            )

            # Mark old fact as superseded
            await conn.execute(
                """
                    UPDATE semantic_facts
                    SET valid_to = $1, superseded_by = $2
                    WHERE fact_id = $3
                    """,
                now,
                new_fact_id,
                old_fact_id,
            )

            logger.info(
                f"Fact {old_fact_id} superseded by {new_fact_id}",
                reason=reason,
            )
            return new_fact_id

    # =========================================================================
    # Health Check
    # =========================================================================

    async def health_check(self) -> dict[str, Any]:
        """Check database connectivity and return status."""
        try:
            async with self.acquire() as conn:
                await conn.fetchval("SELECT 1")
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
_repository: SubstrateRepository | None = None


@register_singleton(
    name="memory_substrate_repository",
    lifecycle="startup",
    description="PostgreSQL connection pool for memory substrate",
)
def get_repository() -> SubstrateRepository:
    """Get repository singleton (must be initialized first)."""
    if _repository is None:
        raise RuntimeError("Repository not initialized. Call init_repository() first.")
    return _repository


def get_substrate_repository(database_url: str | None = None) -> SubstrateRepository:
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


@register_singleton_closer("memory_substrate_repository")
async def close_repository() -> None:
    """Close the repository connection."""
    global _repository
    if _repository:
        await _repository.disconnect()
        _repository = None


# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "MEM-LEAR-037",
    "governance_level": "critical",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [
        "core.schemas",
        "memory.governance_gate",
        "memory.substrate_models",
    ],
    "tags": [
        "async",
        "data-access",
        "debugging",
        "event-driven",
        "learning",
        "logging",
        "memory-substrate",
        "messaging",
        "migration",
        "postgres",
    ],
    "keywords": [
        "acquire",
        "active",
        "block",
        "check",
        "checkpoint",
        "checkpoints",
        "close",
        "connect",
    ],
    "business_value": "Provides async functions for all memory substrate operations.",
    "last_modified": "2026-01-17T23:47:56Z",
    "modified_by": "L9_Codegen_Engine",
    "change_summary": "Initial generation with DORA compliance",
}
# ============================================================================
# L9 DORA BLOCK - AUTO-UPDATED - DO NOT EDIT
# Runtime execution trace - updated automatically on every execution
# ============================================================================
__l9_trace__ = {
    "trace_id": "",
    "task": "",
    "timestamp": "",
    "patterns_used": [],
    "graph": {"nodes": [], "edges": []},
    "inputs": {},
    "outputs": {},
    "metrics": {"confidence": "", "errors_detected": [], "stability_score": ""},
}
# ============================================================================
# END L9 DORA BLOCK
# ============================================================================
