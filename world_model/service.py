"""
L9 World Model - Service Layer
==============================

High-level service that coordinates:
- Repository (database persistence)
- Engine (in-memory state)
- Insight integration

This service replaces in-memory storage with Postgres-backed persistence.

Specification Sources:
- WorldModelOS.yaml → service_layer
- world_model_layer.yaml → coordination

Version: 1.0.0
"""

from __future__ import annotations

import structlog
from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from world_model.repository import (
    WorldModelRepository,
    get_world_model_repository,
)

logger = structlog.get_logger(__name__)


class WorldModelService:
    """
    Service layer for World Model operations.

    Provides:
    - Database-backed entity management
    - Insight integration from memory substrate
    - Snapshot/restore with persistence
    - State version tracking

    Usage:
        service = WorldModelService()

        # Entity operations
        entity = await service.get_entity("entity-123")
        await service.upsert_entity("entity-456", {"name": "Test"})

        # Insight integration
        result = await service.update_from_insights(insights)

        # Snapshots
        snapshot = await service.create_snapshot("checkpoint-1")
        await service.restore_from_snapshot(snapshot.snapshot_id)
    """

    def __init__(self, repository: Optional[WorldModelRepository] = None):
        """
        Initialize World Model Service.

        Args:
            repository: Optional repository instance (uses singleton if not provided)
        """
        self._repository = repository or get_world_model_repository()
        self._state_version = 0
        self._pending_updates: list[dict[str, Any]] = []
        logger.info("WorldModelService initialized")

    # =========================================================================
    # Entity Operations
    # =========================================================================

    async def get_entity(
        self,
        entity_id: str,
        tenant_id: Optional[str] = None,
        org_id: Optional[str] = None,
        user_id: Optional[str] = None,
        role: str = "end_user",
    ) -> Optional[dict[str, Any]]:
        """
        Retrieve entity by ID.

        Args:
            entity_id: Unique entity identifier

        Returns:
            Entity dict if found, None otherwise
        """
        entity = await self._repository.get_entity(
            entity_id=entity_id,
            tenant_id=tenant_id,
            org_id=org_id,
            user_id=user_id,
            role=role,
        )
        if entity:
            return entity.to_dict()
        return None

    async def list_entities(
        self,
        entity_type: Optional[str] = None,
        min_confidence: Optional[float] = None,
        limit: int = 100,
        offset: int = 0,
        tenant_id: Optional[str] = None,
        org_id: Optional[str] = None,
        user_id: Optional[str] = None,
        role: str = "end_user",
    ) -> list[dict[str, Any]]:
        """
        List entities with optional filtering.

        Args:
            entity_type: Filter by entity type
            min_confidence: Minimum confidence threshold
            limit: Maximum results
            offset: Pagination offset

        Returns:
            List of entity dicts
        """
        entities = await self._repository.list_entities(
            entity_type=entity_type,
            min_confidence=min_confidence,
            limit=limit,
            offset=offset,
            tenant_id=tenant_id,
            org_id=org_id,
            user_id=user_id,
            role=role,
        )
        return [e.to_dict() for e in entities]

    async def upsert_entity(
        self,
        entity_id: str,
        attributes: dict[str, Any],
        entity_type: str = "unknown",
        confidence: float = 1.0,
        tenant_id: Optional[str] = None,
        org_id: Optional[str] = None,
        user_id: Optional[str] = None,
        role: str = "end_user",
    ) -> dict[str, Any]:
        """
        Insert or update entity.

        Args:
            entity_id: Unique entity identifier
            attributes: Entity attributes
            entity_type: Entity type classification
            confidence: Confidence score

        Returns:
            Updated entity dict
        """
        entity = await self._repository.upsert_entity(
            entity_id=entity_id,
            attributes=attributes,
            entity_type=entity_type,
            confidence=confidence,
            tenant_id=tenant_id,
            org_id=org_id,
            user_id=user_id,
            role=role,
        )
        self._state_version += 1
        return entity.to_dict()

    async def delete_entity(
        self,
        entity_id: str,
        tenant_id: Optional[str] = None,
        org_id: Optional[str] = None,
        user_id: Optional[str] = None,
        role: str = "end_user",
    ) -> bool:
        """
        Delete entity by ID.

        Args:
            entity_id: Entity to delete

        Returns:
            True if deleted
        """
        deleted = await self._repository.delete_entity(
            entity_id=entity_id,
            tenant_id=tenant_id,
            org_id=org_id,
            user_id=user_id,
            role=role,
        )
        if deleted:
            self._state_version += 1
        return deleted

    # =========================================================================
    # Insight Integration
    # =========================================================================

    async def update_from_insights(
        self,
        insights: list[dict[str, Any]],
        tenant_id: Optional[str] = None,
        org_id: Optional[str] = None,
        user_id: Optional[str] = None,
        role: str = "end_user",
    ) -> dict[str, Any]:
        """
        Update world model from extracted insights.

        This is the primary integration point with the memory substrate.
        Called by world_model_trigger_node in the memory DAG.

        Args:
            insights: List of ExtractedInsight dicts with:
                - insight_id: UUID
                - insight_type: str
                - content: str
                - entities: list[str]
                - confidence: float
                - trigger_world_model: bool
                - source_packet: UUID (optional)
                - facts: list[dict] (optional)

        Returns:
            Status dict with:
                - status: "ok" | "skipped" | "error"
                - updates_applied: int
                - entities_affected: int
                - state_version: int
        """
        logger.info(f"Processing {len(insights)} insights for world model update")

        # Filter to insights that should trigger updates
        triggering = [i for i in insights if i.get("trigger_world_model", False)]

        if not triggering:
            return {
                "status": "skipped",
                "reason": "no_triggering_insights",
                "state_version": self._state_version,
            }

        version_before = self._state_version
        affected_entities: list[str] = []
        updates_applied = 0

        try:
            for insight in triggering:
                insight_id = insight.get("insight_id")
                if isinstance(insight_id, str):
                    try:
                        insight_id = UUID(insight_id)
                    except ValueError:
                        insight_id = None

                insight_type = insight.get("insight_type", "unknown")
                entities = insight.get("entities", [])
                content = insight.get("content", "")
                confidence = insight.get("confidence", 0.7)
                source_packet = insight.get("source_packet")
                if isinstance(source_packet, str):
                    try:
                        source_packet = UUID(source_packet)
                    except ValueError:
                        source_packet = None

                # Update each referenced entity
                for entity_id in entities:
                    if not entity_id:
                        continue

                    # Build attributes from insight
                    attributes = {
                        "last_insight_type": insight_type,
                        "last_insight_content": content[:500] if content else None,
                        "last_insight_at": datetime.utcnow().isoformat(),
                    }

                    # Extract facts if present
                    facts = insight.get("facts", [])
                    for fact in facts:
                        if fact.get("subject") == entity_id:
                            pred = fact.get("predicate", "")
                            obj = fact.get("object")
                            if pred and obj is not None:
                                attributes[pred] = obj

                    # Upsert entity
                    await self._repository.upsert_entity(
                        entity_id=entity_id,
                        attributes=attributes,
                        entity_type=insight_type,
                        confidence=confidence,
                        tenant_id=tenant_id,
                        org_id=org_id,
                        user_id=user_id,
                        role=role,
                    )
                    affected_entities.append(entity_id)

                # Record update in audit log
                await self._repository.record_update(
                    insight_id=insight_id,
                    insight_type=insight_type,
                    entities=entities,
                    content={"content": content, "facts": insight.get("facts", [])},
                    confidence=confidence,
                    source_packet=source_packet,
                    state_version_before=version_before,
                    state_version_after=self._state_version + 1,
                    tenant_id=tenant_id,
                    org_id=org_id,
                    user_id=user_id,
                    role=role,
                )

                updates_applied += 1

            self._state_version += 1

            logger.info(
                f"World model updated: {updates_applied} updates, "
                f"{len(set(affected_entities))} entities affected"
            )

            return {
                "status": "ok",
                "updates_applied": updates_applied,
                "entities_affected": len(set(affected_entities)),
                "affected_entity_ids": list(set(affected_entities)),
                "state_version": self._state_version,
            }

        except Exception as e:
            logger.error(f"Error updating world model from insights: {e}")
            return {
                "status": "error",
                "error": str(e),
                "state_version": self._state_version,
            }

    # =========================================================================
    # Snapshot Operations
    # =========================================================================

    async def create_snapshot(
        self,
        description: Optional[str] = None,
        created_by: str = "system",
        tenant_id: Optional[str] = None,
        org_id: Optional[str] = None,
        user_id: Optional[str] = None,
        role: str = "end_user",
    ) -> dict[str, Any]:
        """
        Create a snapshot of current world model state.

        Args:
            description: Optional description
            created_by: Creator identifier

        Returns:
            Snapshot dict with snapshot_id
        """
        # Get all entities
        entities = await self._repository.list_entities(
            limit=10000,
            tenant_id=tenant_id,
            org_id=org_id,
            user_id=user_id,
            role=role,
        )
        entity_count = len(entities)

        # Serialize state
        snapshot_data = {
            "entities": [e.to_dict() for e in entities],
            "state_version": self._state_version,
            "created_at": datetime.utcnow().isoformat(),
        }

        # Save to database
        snapshot = await self._repository.save_snapshot(
            snapshot=snapshot_data,
            state_version=self._state_version,
            entity_count=entity_count,
            relation_count=0,  # Relations not yet implemented
            description=description,
            created_by=created_by,
            tenant_id=tenant_id,
            org_id=org_id,
            user_id=user_id,
            role=role,
        )

        logger.info(f"Created snapshot: {snapshot.snapshot_id}")

        return snapshot.to_dict()

    async def restore_from_snapshot(
        self,
        snapshot_id: UUID,
        tenant_id: Optional[str] = None,
        org_id: Optional[str] = None,
        user_id: Optional[str] = None,
        role: str = "end_user",
    ) -> dict[str, Any]:
        """
        Restore world model state from a snapshot.

        WARNING: This replaces all current entities!

        Args:
            snapshot_id: Snapshot UUID to restore from

        Returns:
            Restore result dict
        """
        snapshot = await self._repository.load_snapshot(
            snapshot_id=snapshot_id,
            tenant_id=tenant_id,
            org_id=org_id,
            user_id=user_id,
            role=role,
        )

        if not snapshot:
            return {
                "status": "error",
                "error": f"Snapshot {snapshot_id} not found",
            }

        try:
            snapshot_data = snapshot.snapshot
            entities = snapshot_data.get("entities", [])

            # Restore each entity
            restored_count = 0
            for entity_data in entities:
                await self._repository.upsert_entity(
                    entity_id=entity_data["entity_id"],
                    attributes=entity_data.get("attributes", {}),
                    entity_type=entity_data.get("entity_type", "unknown"),
                    confidence=entity_data.get("confidence", 1.0),
                    tenant_id=tenant_id,
                    org_id=org_id,
                    user_id=user_id,
                    role=role,
                )
                restored_count += 1

            self._state_version = snapshot_data.get("state_version", 0)

            logger.info(
                f"Restored from snapshot {snapshot_id}: "
                f"{restored_count} entities, version {self._state_version}"
            )

            return {
                "status": "ok",
                "snapshot_id": str(snapshot_id),
                "entities_restored": restored_count,
                "state_version": self._state_version,
            }

        except Exception as e:
            logger.error(f"Error restoring from snapshot: {e}")
            return {
                "status": "error",
                "error": str(e),
            }

    async def get_latest_snapshot(
        self,
        tenant_id: Optional[str] = None,
        org_id: Optional[str] = None,
        user_id: Optional[str] = None,
        role: str = "end_user",
    ) -> Optional[dict[str, Any]]:
        """
        Get the most recent snapshot.

        Returns:
            Snapshot dict if any exist
        """
        snapshot = await self._repository.get_latest_snapshot(
            tenant_id=tenant_id,
            org_id=org_id,
            user_id=user_id,
            role=role,
        )
        if snapshot:
            return snapshot.to_dict()
        return None

    async def list_snapshots(
        self,
        limit: int = 20,
        tenant_id: Optional[str] = None,
        org_id: Optional[str] = None,
        user_id: Optional[str] = None,
        role: str = "end_user",
    ) -> list[dict[str, Any]]:
        """
        List recent snapshots.

        Args:
            limit: Maximum results

        Returns:
            List of snapshot dicts (newest first)
        """
        snapshots = await self._repository.list_snapshots(
            limit=limit,
            tenant_id=tenant_id,
            org_id=org_id,
            user_id=user_id,
            role=role,
        )
        return [s.to_dict() for s in snapshots]

    # =========================================================================
    # State Version
    # =========================================================================

    async def get_state_version(
        self,
        tenant_id: Optional[str] = None,
        org_id: Optional[str] = None,
        user_id: Optional[str] = None,
        role: str = "end_user",
    ) -> int:
        """
        Get current state version.

        Returns:
            Current state version
        """
        # Sync with database version
        db_version = await self._repository.get_state_version(
            tenant_id=tenant_id,
            org_id=org_id,
            user_id=user_id,
            role=role,
        )
        self._state_version = max(self._state_version, db_version)
        return self._state_version

    async def get_entity_count(
        self,
        tenant_id: Optional[str] = None,
        org_id: Optional[str] = None,
        user_id: Optional[str] = None,
        role: str = "end_user",
    ) -> int:
        """
        Get total entity count.

        Returns:
            Number of entities
        """
        return await self._repository.get_entity_count(
            tenant_id=tenant_id,
            org_id=org_id,
            user_id=user_id,
            role=role,
        )

    # =========================================================================
    # Update History
    # =========================================================================

    async def list_updates(
        self,
        insight_type: Optional[str] = None,
        min_confidence: Optional[float] = None,
        since: Optional[datetime] = None,
        limit: int = 100,
        tenant_id: Optional[str] = None,
        org_id: Optional[str] = None,
        user_id: Optional[str] = None,
        role: str = "end_user",
    ) -> list[dict[str, Any]]:
        """
        List recent updates to the world model.

        Args:
            insight_type: Filter by insight type
            min_confidence: Minimum confidence
            since: Updates after this timestamp
            limit: Maximum results

        Returns:
            List of update dicts
        """
        updates = await self._repository.list_updates(
            insight_type=insight_type,
            min_confidence=min_confidence,
            since=since,
            limit=limit,
            tenant_id=tenant_id,
            org_id=org_id,
            user_id=user_id,
            role=role,
        )
        return [u.to_dict() for u in updates]


# =============================================================================
# Singleton Access
# =============================================================================

_service: Optional[WorldModelService] = None


def get_world_model_service() -> WorldModelService:
    """Get or create singleton service."""
    global _service
    if _service is None:
        _service = WorldModelService()
    return _service


async def close_world_model_service():
    """Close service and cleanup."""
    global _service
    if _service is not None:
        from world_model.repository import close_pool

        await close_pool()
        _service = None
        logger.info("WorldModelService closed")
