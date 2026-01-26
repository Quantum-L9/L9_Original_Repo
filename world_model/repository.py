"""
L9 World Model - Repository
===========================

Database integration layer for world model persistence.
Uses asyncpg for async Postgres operations.

Specification Sources:
- WorldModelOS.yaml → persistence
- world_model_layer.yaml → data_layer

Tables:
- world_model_entities: Entity storage
- world_model_updates: Update audit log
- world_model_snapshots: Point-in-time snapshots

Version: 1.0.0
"""

from __future__ import annotations

from core.singleton_auto_registry import register_singleton

# ============================================================================
__dora_meta__ = {
    "component_name": "Repository",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2025-12-09T01:02:49Z",
    "updated_at": "2026-01-17T23:47:57Z",
    "layer": "learning",
    "domain": "world_model",
    "module_name": "repository",
    "type": "service",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": ["PostgreSQL"],
        "memory_layers": [],
        "imported_by": [
            "core.singleton_registry",
            "tests.integration.test_world_model_repository_integration",
            "tests.world_model.test_wm_scope",
            "tests.world_model.test_world_model_repository_basic",
            "world_model.__init__",
            "world_model.service",
        ],
    },
}
# ============================================================================

import json
import os
from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

import asyncpg
import structlog

logger = structlog.get_logger(__name__)


async def _init_json_codecs(conn: asyncpg.Connection) -> None:
    """Initialize connection with JSON codec for JSONB columns."""
    await conn.set_type_codec(
        "jsonb", encoder=json.dumps, decoder=json.loads, schema="pg_catalog"
    )
    await conn.set_type_codec(
        "json", encoder=json.dumps, decoder=json.loads, schema="pg_catalog"
    )


# =============================================================================
# Database Configuration
# =============================================================================

# Get database URL from environment - use service DNS for Docker
# Default uses 'l9-postgres' service name from docker-compose.yml
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    os.getenv(
        "MEMORY_DSN", "postgresql://postgres:postgres@l9-postgres:5432/l9_memory"
    ),
)


# =============================================================================
# Connection Pool Management
# =============================================================================

_pool = None


async def get_pool():
    """Get or create connection pool."""
    global _pool
    if _pool is None:
        _pool = await asyncpg.create_pool(
            DATABASE_URL,
            min_size=2,
            max_size=10,
            init=_init_json_codecs,  # Register JSON codecs for JSONB columns
        )
        logger.info("World Model DB pool initialized with JSON codecs")
    return _pool


async def close_pool():
    """Close connection pool."""
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None
        logger.info("World Model DB pool closed")


# =============================================================================
# Entity Data Types
# =============================================================================


class WorldModelEntityRow:
    """Row data from world_model_entities table."""

    def __init__(
        self,
        entity_id: str,
        entity_type: str,
        attributes: dict[str, Any],
        confidence: float,
        created_at: datetime,
        updated_at: datetime,
        version: int,
    ):
        self.entity_id = entity_id
        self.entity_type = entity_type
        self.attributes = attributes
        self.confidence = confidence
        self.created_at = created_at
        self.updated_at = updated_at
        self.version = version

    def to_dict(self) -> dict[str, Any]:
        return {
            "entity_id": self.entity_id,
            "entity_type": self.entity_type,
            "attributes": self.attributes,
            "confidence": self.confidence,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "version": self.version,
        }

    @classmethod
    def from_row(cls, row) -> WorldModelEntityRow:
        attributes = row["attributes"]
        if isinstance(attributes, str):
            attributes = json.loads(attributes)
        return cls(
            entity_id=row["entity_id"],
            entity_type=row["entity_type"],
            attributes=attributes,
            confidence=row["confidence"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            version=row["version"],
        )


class WorldModelUpdateRow:
    """Row data from world_model_updates table."""

    def __init__(
        self,
        update_id: UUID,
        insight_id: UUID | None,
        insight_type: str | None,
        entities: list[str],
        content: dict[str, Any],
        confidence: float,
        applied_at: datetime,
        source_packet: UUID | None = None,
        state_version_before: int | None = None,
        state_version_after: int | None = None,
    ):
        self.update_id = update_id
        self.insight_id = insight_id
        self.insight_type = insight_type
        self.entities = entities
        self.content = content
        self.confidence = confidence
        self.applied_at = applied_at
        self.source_packet = source_packet
        self.state_version_before = state_version_before
        self.state_version_after = state_version_after

    def to_dict(self) -> dict[str, Any]:
        return {
            "update_id": str(self.update_id),
            "insight_id": str(self.insight_id) if self.insight_id else None,
            "insight_type": self.insight_type,
            "entities": self.entities,
            "content": self.content,
            "confidence": self.confidence,
            "applied_at": self.applied_at.isoformat() if self.applied_at else None,
            "source_packet": str(self.source_packet) if self.source_packet else None,
            "state_version_before": self.state_version_before,
            "state_version_after": self.state_version_after,
        }


class WorldModelSnapshotRow:
    """Row data from world_model_snapshots table."""

    def __init__(
        self,
        snapshot_id: UUID,
        snapshot: dict[str, Any],
        state_version: int,
        entity_count: int,
        relation_count: int,
        created_at: datetime,
        description: str | None = None,
        created_by: str = "system",
    ):
        self.snapshot_id = snapshot_id
        self.snapshot = snapshot
        self.state_version = state_version
        self.entity_count = entity_count
        self.relation_count = relation_count
        self.created_at = created_at
        self.description = description
        self.created_by = created_by

    def to_dict(self) -> dict[str, Any]:
        return {
            "snapshot_id": str(self.snapshot_id),
            "snapshot": self.snapshot,
            "state_version": self.state_version,
            "entity_count": self.entity_count,
            "relation_count": self.relation_count,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "description": self.description,
            "created_by": self.created_by,
        }


# =============================================================================
# World Model Repository
# =============================================================================


class WorldModelRepository:
    """
    Database repository for World Model persistence.

    Provides async CRUD operations for:
    - Entities
    - Updates (audit log)
    - Snapshots

    Usage:
        repo = WorldModelRepository()
        entity = await repo.get_entity("entity-123")
        await repo.upsert_entity("entity-456", {"name": "Test"}, confidence=0.9)
    """

    def __init__(self):
        """Initialize repository."""
        logger.info("WorldModelRepository initialized")

    @staticmethod
    def _ensure_scope(
        tenant_id: str | None,
        org_id: str | None,
        user_id: str | None,
    ) -> None:
        if not tenant_id or not org_id or not user_id:
            raise RuntimeError(
                "RLS scope required for WorldModelRepository "
                "(tenant_id, org_id, user_id)."
            )

    async def set_session_scope(
        self,
        conn: asyncpg.Connection,
        tenant_id: str,
        org_id: str,
        user_id: str,
        role: str = "end_user",
    ) -> None:
        """Set PostgreSQL session variables for RLS (Row-Level Security)."""
        await conn.execute(
            """SELECT l9_set_scope($1::uuid, $2::uuid, $3::uuid, $4::text)""",
            tenant_id,
            org_id,
            user_id,
            role,
        )

    # =========================================================================
    # Entity Operations
    # =========================================================================

    async def get_entity(
        self,
        entity_id: str,
        tenant_id: str | None = None,
        org_id: str | None = None,
        user_id: str | None = None,
        role: str = "end_user",
    ) -> WorldModelEntityRow | None:
        """
        Retrieve entity by ID.

        Args:
            entity_id: Unique entity identifier

        Returns:
            WorldModelEntityRow if found, None otherwise
        """
        self._ensure_scope(tenant_id, org_id, user_id)
        pool = await get_pool()
        async with pool.acquire() as conn:
            await self.set_session_scope(conn, tenant_id, org_id, user_id, role)
            row = await conn.fetchrow(
                """
                SELECT entity_id, entity_type, attributes, confidence,
                       created_at, updated_at, version
                FROM world_model_entities
                WHERE entity_id = $1
                """,
                entity_id,
            )
            if row:
                return WorldModelEntityRow.from_row(row)
            return None

    async def list_entities(
        self,
        entity_type: str | None = None,
        min_confidence: float | None = None,
        limit: int = 100,
        offset: int = 0,
        tenant_id: str | None = None,
        org_id: str | None = None,
        user_id: str | None = None,
        role: str = "end_user",
    ) -> list[WorldModelEntityRow]:
        """
        List entities with optional filtering.

        Args:
            entity_type: Filter by entity type
            min_confidence: Minimum confidence threshold
            limit: Maximum results
            offset: Pagination offset

        Returns:
            List of matching entities
        """
        self._ensure_scope(tenant_id, org_id, user_id)
        pool = await get_pool()
        async with pool.acquire() as conn:
            await self.set_session_scope(conn, tenant_id, org_id, user_id, role)
            conditions = []
            params = []
            param_idx = 1

            if entity_type:
                conditions.append(f"entity_type = ${param_idx}")
                params.append(entity_type)
                param_idx += 1

            if min_confidence is not None:
                conditions.append(f"confidence >= ${param_idx}")
                params.append(min_confidence)
                param_idx += 1

            where_clause = ""
            if conditions:
                where_clause = "WHERE " + " AND ".join(conditions)

            params.extend([limit, offset])

            query = f"""
                SELECT entity_id, entity_type, attributes, confidence,
                       created_at, updated_at, version
                FROM world_model_entities
                {where_clause}
                ORDER BY updated_at DESC
                LIMIT ${param_idx} OFFSET ${param_idx + 1}
            """

            rows = await conn.fetch(query, *params)
            return [WorldModelEntityRow.from_row(row) for row in rows]

    async def upsert_entity(
        self,
        entity_id: str,
        attributes: dict[str, Any],
        entity_type: str = "unknown",
        confidence: float = 1.0,
        tenant_id: str | None = None,
        org_id: str | None = None,
        user_id: str | None = None,
        role: str = "end_user",
    ) -> WorldModelEntityRow:
        """
        Insert or update entity.

        Uses UPSERT pattern for atomic insert/update.

        Args:
            entity_id: Unique entity identifier
            attributes: Entity attributes (merged on update)
            entity_type: Entity type classification
            confidence: Confidence score (0.0-1.0)

        Returns:
            Updated/inserted entity
        """
        self._ensure_scope(tenant_id, org_id, user_id)
        pool = await get_pool()
        async with pool.acquire() as conn:
            await self.set_session_scope(conn, tenant_id, org_id, user_id, role)
            row = await conn.fetchrow(
                """
                INSERT INTO world_model_entities
                    (entity_id, entity_type, attributes, confidence, created_at, updated_at, version)
                VALUES ($1, $2, $3, $4, now(), now(), 1)
                ON CONFLICT (entity_id) DO UPDATE SET
                    attributes = world_model_entities.attributes || $3,
                    confidence = GREATEST(world_model_entities.confidence, $4),
                    updated_at = now(),
                    version = world_model_entities.version + 1
                RETURNING entity_id, entity_type, attributes, confidence,
                          created_at, updated_at, version
                """,
                entity_id,
                entity_type,
                json.dumps(attributes),
                confidence,
            )
            logger.debug(f"Upserted entity: {entity_id}")
            return WorldModelEntityRow.from_row(row)

    async def delete_entity(
        self,
        entity_id: str,
        tenant_id: str | None = None,
        org_id: str | None = None,
        user_id: str | None = None,
        role: str = "end_user",
    ) -> bool:
        """
        Delete entity by ID.

        Args:
            entity_id: Entity to delete

        Returns:
            True if deleted, False if not found
        """
        self._ensure_scope(tenant_id, org_id, user_id)
        pool = await get_pool()
        async with pool.acquire() as conn:
            await self.set_session_scope(conn, tenant_id, org_id, user_id, role)
            result = await conn.execute(
                "DELETE FROM world_model_entities WHERE entity_id = $1", entity_id
            )
            deleted = result == "DELETE 1"
            if deleted:
                logger.debug(f"Deleted entity: {entity_id}")
            return deleted

    async def get_entity_count(
        self,
        tenant_id: str | None = None,
        org_id: str | None = None,
        user_id: str | None = None,
        role: str = "end_user",
    ) -> int:
        """Get total entity count."""
        self._ensure_scope(tenant_id, org_id, user_id)
        pool = await get_pool()
        async with pool.acquire() as conn:
            await self.set_session_scope(conn, tenant_id, org_id, user_id, role)
            row = await conn.fetchrow(
                "SELECT COUNT(*) as count FROM world_model_entities"
            )
            return row["count"] if row else 0

    # =========================================================================
    # Update Operations (Audit Log)
    # =========================================================================

    async def record_update(
        self,
        insight_id: UUID | None,
        insight_type: str | None,
        entities: list[str],
        content: dict[str, Any],
        confidence: float,
        source_packet: UUID | None = None,
        state_version_before: int | None = None,
        state_version_after: int | None = None,
        tenant_id: str | None = None,
        org_id: str | None = None,
        user_id: str | None = None,
        role: str = "end_user",
    ) -> WorldModelUpdateRow:
        """
        Record an update to the world model audit log.

        Args:
            insight_id: Source insight ID
            insight_type: Type of insight
            entities: List of affected entity IDs
            content: Update content/payload
            confidence: Update confidence
            source_packet: Source packet ID (if any)
            state_version_before: Version before update
            state_version_after: Version after update

        Returns:
            Created update record
        """
        self._ensure_scope(tenant_id, org_id, user_id)
        update_id = uuid4()
        pool = await get_pool()
        async with pool.acquire() as conn:
            await self.set_session_scope(conn, tenant_id, org_id, user_id, role)
            await conn.execute(
                """
                INSERT INTO world_model_updates
                    (update_id, insight_id, insight_type, entities, content,
                     confidence, applied_at, source_packet,
                     state_version_before, state_version_after)
                VALUES ($1, $2, $3, $4, $5, $6, now(), $7, $8, $9)
                """,
                update_id,
                insight_id,
                insight_type,
                json.dumps(entities),
                json.dumps(content),
                confidence,
                source_packet,
                state_version_before,
                state_version_after,
            )
            logger.debug(f"Recorded update: {update_id}")

            return WorldModelUpdateRow(
                update_id=update_id,
                insight_id=insight_id,
                insight_type=insight_type,
                entities=entities,
                content=content,
                confidence=confidence,
                applied_at=datetime.utcnow(),
                source_packet=source_packet,
                state_version_before=state_version_before,
                state_version_after=state_version_after,
            )

    async def list_updates(
        self,
        insight_type: str | None = None,
        min_confidence: float | None = None,
        since: datetime | None = None,
        limit: int = 100,
        tenant_id: str | None = None,
        org_id: str | None = None,
        user_id: str | None = None,
        role: str = "end_user",
    ) -> list[WorldModelUpdateRow]:
        """
        List update records with filtering.

        Args:
            insight_type: Filter by insight type
            min_confidence: Minimum confidence
            since: Updates after this timestamp
            limit: Maximum results

        Returns:
            List of update records
        """
        self._ensure_scope(tenant_id, org_id, user_id)
        pool = await get_pool()
        async with pool.acquire() as conn:
            await self.set_session_scope(conn, tenant_id, org_id, user_id, role)
            conditions = []
            params = []
            param_idx = 1

            if insight_type:
                conditions.append(f"insight_type = ${param_idx}")
                params.append(insight_type)
                param_idx += 1

            if min_confidence is not None:
                conditions.append(f"confidence >= ${param_idx}")
                params.append(min_confidence)
                param_idx += 1

            if since:
                conditions.append(f"applied_at >= ${param_idx}")
                params.append(since)
                param_idx += 1

            where_clause = ""
            if conditions:
                where_clause = "WHERE " + " AND ".join(conditions)

            params.append(limit)

            query = f"""
                SELECT update_id, insight_id, insight_type, entities, content,
                       confidence, applied_at, source_packet,
                       state_version_before, state_version_after
                FROM world_model_updates
                {where_clause}
                ORDER BY applied_at DESC
                LIMIT ${param_idx}
            """

            rows = await conn.fetch(query, *params)
            results = []
            for row in rows:
                entities = row["entities"]
                if isinstance(entities, str):
                    entities = json.loads(entities)
                content = row["content"]
                if isinstance(content, str):
                    content = json.loads(content)
                results.append(
                    WorldModelUpdateRow(
                        update_id=row["update_id"],
                        insight_id=row["insight_id"],
                        insight_type=row["insight_type"],
                        entities=entities,
                        content=content,
                        confidence=row["confidence"],
                        applied_at=row["applied_at"],
                        source_packet=row["source_packet"],
                        state_version_before=row["state_version_before"],
                        state_version_after=row["state_version_after"],
                    )
                )
            return results

    # =========================================================================
    # Snapshot Operations
    # =========================================================================

    async def save_snapshot(
        self,
        snapshot: dict[str, Any],
        state_version: int,
        entity_count: int = 0,
        relation_count: int = 0,
        description: str | None = None,
        created_by: str = "system",
        tenant_id: str | None = None,
        org_id: str | None = None,
        user_id: str | None = None,
        role: str = "end_user",
    ) -> WorldModelSnapshotRow:
        """
        Save a world model snapshot.

        Args:
            snapshot: Full state serialization
            state_version: Current state version
            entity_count: Number of entities
            relation_count: Number of relations
            description: Optional description
            created_by: Creator identifier

        Returns:
            Created snapshot record
        """
        self._ensure_scope(tenant_id, org_id, user_id)
        snapshot_id = uuid4()
        pool = await get_pool()
        async with pool.acquire() as conn:
            await self.set_session_scope(conn, tenant_id, org_id, user_id, role)
            await conn.execute(
                """
                INSERT INTO world_model_snapshots
                    (snapshot_id, snapshot, state_version, entity_count,
                     relation_count, created_at, description, created_by)
                VALUES ($1, $2, $3, $4, $5, now(), $6, $7)
                """,
                snapshot_id,
                json.dumps(snapshot),
                state_version,
                entity_count,
                relation_count,
                description,
                created_by,
            )
            logger.info(f"Saved snapshot: {snapshot_id} (version {state_version})")

            return WorldModelSnapshotRow(
                snapshot_id=snapshot_id,
                snapshot=snapshot,
                state_version=state_version,
                entity_count=entity_count,
                relation_count=relation_count,
                created_at=datetime.utcnow(),
                description=description,
                created_by=created_by,
            )

    async def load_snapshot(
        self,
        snapshot_id: UUID,
        tenant_id: str | None = None,
        org_id: str | None = None,
        user_id: str | None = None,
        role: str = "end_user",
    ) -> WorldModelSnapshotRow | None:
        """
        Load a snapshot by ID.

        Args:
            snapshot_id: Snapshot UUID

        Returns:
            Snapshot if found, None otherwise
        """
        self._ensure_scope(tenant_id, org_id, user_id)
        pool = await get_pool()
        async with pool.acquire() as conn:
            await self.set_session_scope(conn, tenant_id, org_id, user_id, role)
            row = await conn.fetchrow(
                """
                SELECT snapshot_id, snapshot, state_version, entity_count,
                       relation_count, created_at, description, created_by
                FROM world_model_snapshots
                WHERE snapshot_id = $1
                """,
                snapshot_id,
            )
            if row:
                snapshot = row["snapshot"]
                if isinstance(snapshot, str):
                    snapshot = json.loads(snapshot)
                return WorldModelSnapshotRow(
                    snapshot_id=row["snapshot_id"],
                    snapshot=snapshot,
                    state_version=row["state_version"],
                    entity_count=row["entity_count"],
                    relation_count=row["relation_count"],
                    created_at=row["created_at"],
                    description=row["description"],
                    created_by=row["created_by"],
                )
            return None

    async def get_latest_snapshot(
        self,
        tenant_id: str | None = None,
        org_id: str | None = None,
        user_id: str | None = None,
        role: str = "end_user",
    ) -> WorldModelSnapshotRow | None:
        """
        Get the most recent snapshot.

        Returns:
            Latest snapshot if any exist
        """
        self._ensure_scope(tenant_id, org_id, user_id)
        pool = await get_pool()
        async with pool.acquire() as conn:
            await self.set_session_scope(conn, tenant_id, org_id, user_id, role)
            row = await conn.fetchrow("""
                SELECT snapshot_id, snapshot, state_version, entity_count,
                       relation_count, created_at, description, created_by
                FROM world_model_snapshots
                ORDER BY created_at DESC
                LIMIT 1
                """)
            if row:
                snapshot = row["snapshot"]
                if isinstance(snapshot, str):
                    snapshot = json.loads(snapshot)
                return WorldModelSnapshotRow(
                    snapshot_id=row["snapshot_id"],
                    snapshot=snapshot,
                    state_version=row["state_version"],
                    entity_count=row["entity_count"],
                    relation_count=row["relation_count"],
                    created_at=row["created_at"],
                    description=row["description"],
                    created_by=row["created_by"],
                )
            return None

    async def list_snapshots(
        self,
        limit: int = 20,
        tenant_id: str | None = None,
        org_id: str | None = None,
        user_id: str | None = None,
        role: str = "end_user",
    ) -> list[WorldModelSnapshotRow]:
        """
        List recent snapshots.

        Args:
            limit: Maximum results

        Returns:
            List of snapshots (newest first)
        """
        self._ensure_scope(tenant_id, org_id, user_id)
        pool = await get_pool()
        async with pool.acquire() as conn:
            await self.set_session_scope(conn, tenant_id, org_id, user_id, role)
            rows = await conn.fetch(
                """
                SELECT snapshot_id, snapshot, state_version, entity_count,
                       relation_count, created_at, description, created_by
                FROM world_model_snapshots
                ORDER BY created_at DESC
                LIMIT $1
                """,
                limit,
            )
            results = []
            for row in rows:
                snapshot = row["snapshot"]
                if isinstance(snapshot, str):
                    snapshot = json.loads(snapshot)
                results.append(
                    WorldModelSnapshotRow(
                        snapshot_id=row["snapshot_id"],
                        snapshot=snapshot,
                        state_version=row["state_version"],
                        entity_count=row["entity_count"],
                        relation_count=row["relation_count"],
                        created_at=row["created_at"],
                        description=row["description"],
                        created_by=row["created_by"],
                    )
                )
            return results

    # =========================================================================
    # State Version Management
    # =========================================================================

    async def get_state_version(
        self,
        tenant_id: str | None = None,
        org_id: str | None = None,
        user_id: str | None = None,
        role: str = "end_user",
    ) -> int:
        """
        Get current state version (highest version from any entity).

        Returns:
            Current state version
        """
        self._ensure_scope(tenant_id, org_id, user_id)
        pool = await get_pool()
        async with pool.acquire() as conn:
            await self.set_session_scope(conn, tenant_id, org_id, user_id, role)
            row = await conn.fetchrow("""
                SELECT COALESCE(MAX(version), 0) as max_version
                FROM world_model_entities
                """)
            return row["max_version"] if row else 0


# =============================================================================
# Singleton Access
# =============================================================================

_repository: WorldModelRepository | None = None


@register_singleton(
    name="world_model_repository",
    lifecycle="lazy",
    description="World model data repository",
)
def get_world_model_repository() -> WorldModelRepository:
    """Get or create singleton repository."""
    global _repository
    if _repository is None:
        _repository = WorldModelRepository()
    return _repository


# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "WOR-LEAR-014",
    "governance_level": "high",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": [
        "async",
        "audit-tool",
        "data-access",
        "debugging",
        "learning",
        "logging",
        "postgres",
        "serialization",
        "service",
        "testing",
    ],
    "keywords": [
        "audit",
        "close",
        "count",
        "delete",
        "entities",
        "entity",
        "latest",
        "load",
    ],
    "business_value": "Provides repository components including WorldModelEntityRow, WorldModelUpdateRow, WorldModelSnapshotRow",
    "last_modified": "2026-01-17T23:47:57Z",
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
