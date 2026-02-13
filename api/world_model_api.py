"""
L9 World Model API
==================

FastAPI routes for World Model operations.

Endpoints:
- GET /world-model/entities/{entity_id} - Get entity by ID
- GET /world-model/entities - List entities with filtering
- GET /world-model/state-version - Get current state version
- POST /world-model/snapshot - Create a snapshot
- POST /world-model/restore - Restore from snapshot
- GET /world-model/updates - List recent updates
- POST /world-model/insights - Submit insights for update

Version: 1.0.0
"""

from __future__ import annotations

from core.decorators import must_stay_async

# ============================================================================
__dora_meta__ = {
    "component_name": "World Model Api",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2025-12-09T01:02:49Z",
    "updated_at": "2026-01-07T13:35:57Z",
    "layer": "operations",
    "domain": "api_gateway",
    "module_name": "world_model_api",
    "type": "router",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [
            "GET /health",
            "GET /entities/{entity_id}",
            "GET /entities",
            "GET /state-version",
            "POST /snapshot",
            "POST /restore",
            "GET /snapshots",
            "POST /insights",
            "GET /updates",
        ],
        "datasources": [],
        "memory_layers": [],
        "imported_by": ["api.server"],
    },
}
# ============================================================================

from typing import Any
from uuid import UUID

import structlog
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from api.routes.registry import router_registry

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/world-model", tags=["world-model"])

# Auto-register with RouterRegistry
router_registry.register(
    router=router,
    prefix="",  # Router already has prefix="/world-model"
    tags=["world-model"],
    module_id="world_model_api",
    display_name="World Model API",
    dependencies=["world_model_service"],
)


# =============================================================================
# Request/Response Models
# =============================================================================


class EntityResponse(BaseModel):
    """Entity data response."""

    entity_id: str
    entity_type: str
    attributes: dict[str, Any]
    confidence: float
    created_at: str | None = None
    updated_at: str | None = None
    version: int = 1


class EntityListResponse(BaseModel):
    """List of entities response."""

    entities: list[EntityResponse]
    total: int
    limit: int
    offset: int


class StateVersionResponse(BaseModel):
    """State version response."""

    state_version: int
    entity_count: int


class SnapshotRequest(BaseModel):
    """Create snapshot request."""

    description: str | None = Field(None, description="Optional description")
    created_by: str = Field(default="api", description="Creator identifier")


class SnapshotResponse(BaseModel):
    """Snapshot response."""

    snapshot_id: str
    state_version: int
    entity_count: int
    created_at: str
    description: str | None = None


class RestoreRequest(BaseModel):
    """Restore from snapshot request."""

    snapshot_id: str = Field(..., description="Snapshot UUID to restore from")


class RestoreResponse(BaseModel):
    """Restore result response."""

    status: str
    snapshot_id: str
    entities_restored: int
    state_version: int


class InsightInput(BaseModel):
    """Single insight for world model update."""

    insight_id: str | None = None
    insight_type: str = Field(
        ..., description="Type: pattern, conclusion, recommendation"
    )
    content: str = Field(..., description="Insight content")
    entities: list[str] = Field(default_factory=list, description="Referenced entities")
    confidence: float = Field(default=0.7, ge=0.0, le=1.0)
    trigger_world_model: bool = Field(default=True)
    source_packet: str | None = None
    facts: list[dict[str, Any]] = Field(default_factory=list)


class InsightsRequest(BaseModel):
    """Submit insights for update request."""

    insights: list[InsightInput] = Field(..., min_length=1)


class InsightsResponse(BaseModel):
    """Insights processing result."""

    status: str
    updates_applied: int = 0
    entities_affected: int = 0
    state_version: int = 0


class UpdateRecord(BaseModel):
    """Single update record."""

    update_id: str
    insight_id: str | None = None
    insight_type: str | None = None
    entities: list[str]
    confidence: float
    applied_at: str


class UpdatesListResponse(BaseModel):
    """List of updates response."""

    updates: list[UpdateRecord]
    total: int


# =============================================================================
# Service Dependency
# =============================================================================


def _get_service():
    """Get WorldModelService instance."""
    from world_model.service import get_world_model_service

    return get_world_model_service()


# =============================================================================
# Endpoints
# =============================================================================


@router.get("/health")
async def world_model_health():
    """Health check for world model API."""
    try:
        service = _get_service()
        version = await service.get_state_version()
        count = await service.get_entity_count()
        return {
            "status": "healthy",
            "state_version": version,
            "entity_count": count,
        }
    except Exception as e:
        logger.error(f"World model health check failed: {e}")
        return {
            "status": "degraded",
            "error": str(e),
        }


@router.get("/entities/{entity_id}", response_model=EntityResponse)
async def get_entity(entity_id: str):
    """
    Get entity by ID.

    Args:
        entity_id: Unique entity identifier

    Returns:
        Entity data

    Raises:
        404: Entity not found
    """
    service = _get_service()
    entity = await service.get_entity(entity_id)

    if entity is None:
        raise HTTPException(status_code=404, detail=f"Entity {entity_id} not found")

    return EntityResponse(**entity)


@router.get("/entities", response_model=EntityListResponse)
@must_stay_async("callers use await")
async def list_entities(
    entity_type: str | None = Query(None, description="Filter by entity type"),
    min_confidence: float | None = Query(
        None, ge=0.0, le=1.0, description="Minimum confidence"
    ),
    limit: int = Query(100, ge=1, le=1000, description="Maximum results"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
):
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
    service = _get_service()
    entities = await service.list_entities(
        entity_type=entity_type,
        min_confidence=min_confidence,
        limit=limit,
        offset=offset,
    )

    return EntityListResponse(
        entities=[EntityResponse(**e) for e in entities],
        total=len(entities),
        limit=limit,
        offset=offset,
    )


@router.get("/state-version", response_model=StateVersionResponse)
async def get_state_version():
    """
    Get current world model state version.

    Returns:
        Current state version and entity count
    """
    service = _get_service()
    version = await service.get_state_version()
    count = await service.get_entity_count()

    return StateVersionResponse(
        state_version=version,
        entity_count=count,
    )


@router.post("/snapshot", response_model=SnapshotResponse)
async def create_snapshot(request: SnapshotRequest):
    """
    Create a snapshot of current world model state.

    Args:
        request: Snapshot creation parameters

    Returns:
        Created snapshot info
    """
    service = _get_service()

    try:
        snapshot = await service.create_snapshot(
            description=request.description,
            created_by=request.created_by,
        )

        return SnapshotResponse(
            snapshot_id=snapshot["snapshot_id"],
            state_version=snapshot["state_version"],
            entity_count=snapshot["entity_count"],
            created_at=snapshot["created_at"],
            description=snapshot.get("description"),
        )
    except Exception as e:
        logger.error(f"Failed to create snapshot: {e}")
        raise HTTPException(status_code=500, detail=f"Snapshot failed: {e!s}") from e


@router.post("/restore", response_model=RestoreResponse)
@must_stay_async("callers use await")
async def restore_from_snapshot(request: RestoreRequest):
    """
    Restore world model state from a snapshot.

    WARNING: This replaces all current entities!

    Args:
        request: Restore parameters with snapshot_id

    Returns:
        Restore result
    """
    service = _get_service()

    try:
        snapshot_uuid = UUID(request.snapshot_id)
    except ValueError:
        raise HTTPException(
            status_code=400, detail="Invalid snapshot_id format"
        ) from None

    result = await service.restore_from_snapshot(snapshot_uuid)

    if result.get("status") == "error":
        raise HTTPException(
            status_code=404, detail=result.get("error", "Restore failed")
        )

    return RestoreResponse(
        status=result["status"],
        snapshot_id=request.snapshot_id,
        entities_restored=result.get("entities_restored", 0),
        state_version=result.get("state_version", 0),
    )


@router.get("/snapshots")
async def list_snapshots(
    limit: int = Query(20, ge=1, le=100, description="Maximum results"),
):
    """
    List recent snapshots.

    Args:
        limit: Maximum results

    Returns:
        List of snapshots
    """
    service = _get_service()
    snapshots = await service.list_snapshots(limit=limit)

    return {
        "snapshots": snapshots,
        "total": len(snapshots),
    }


@router.post("/insights", response_model=InsightsResponse)
async def submit_insights(request: InsightsRequest):
    """
    Submit insights for world model update.

    This is the primary integration point with the memory substrate.

    Args:
        request: List of insights to process

    Returns:
        Update result with affected entities
    """
    service = _get_service()

    # Convert to dict format expected by service
    insights = [i.model_dump() for i in request.insights]

    result = await service.update_from_insights(insights)

    return InsightsResponse(
        status=result.get("status", "error"),
        updates_applied=result.get("updates_applied", 0),
        entities_affected=result.get("entities_affected", 0),
        state_version=result.get("state_version", 0),
    )


@router.get("/updates", response_model=UpdatesListResponse)
async def list_updates(
    insight_type: str | None = Query(None, description="Filter by insight type"),
    min_confidence: float | None = Query(None, ge=0.0, le=1.0),
    limit: int = Query(100, ge=1, le=1000),
):
    """
    List recent world model updates.

    Args:
        insight_type: Filter by insight type
        min_confidence: Minimum confidence
        limit: Maximum results

    Returns:
        List of update records
    """
    service = _get_service()
    updates = await service.list_updates(
        insight_type=insight_type,
        min_confidence=min_confidence,
        limit=limit,
    )

    records = []
    for u in updates:
        records.append(
            UpdateRecord(
                update_id=u["update_id"],
                insight_id=u.get("insight_id"),
                insight_type=u.get("insight_type"),
                entities=u.get("entities", []),
                confidence=u.get("confidence", 0.0),
                applied_at=u.get("applied_at", ""),
            )
        )

    return UpdatesListResponse(
        updates=records,
        total=len(records),
    )


# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "API-OPER-003",
    "governance_level": "medium",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": [
        "api",
        "api-gateway",
        "async",
        "endpoint",
        "logging",
        "operations",
        "pydantic",
        "rest-api",
        "router",
        "validation",
    ],
    "keywords": [
        "api",
        "create",
        "entities",
        "entity",
        "health",
        "insight",
        "insights",
        "model",
    ],
    "business_value": "Provides world model api components including EntityResponse, EntityListResponse, StateVersionResponse",
    "last_modified": "2026-01-07T13:35:57Z",
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
