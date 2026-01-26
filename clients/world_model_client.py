"""
L9 World Model Client SDK
=========================

Internal async HTTP client for L9 components to interact with
the World Model API.

Usage:
    from clients.world_model_client import get_world_model_client

    client = get_world_model_client()

    # Get entity
    entity = await client.get_entity("entity-123")

    # List entities
    entities = await client.list_entities(entity_type="user", limit=50)

    # Submit insights
    result = await client.send_insights_for_update([
        {"insight_type": "conclusion", "content": "...", "entities": ["user-1"]}
    ])

    # Create snapshot
    snapshot = await client.snapshot(description="manual backup")

    # Close when done
    await client.close()

Version: 1.0.0
"""

from __future__ import annotations

# ============================================================================
__dora_meta__ = {
    "component_name": "World Model Client",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2025-12-09T01:02:49Z",
    "updated_at": "2026-01-17T23:47:56Z",
    "layer": "integration",
    "domain": "data_models",
    "module_name": "world_model_client",
    "type": "schema",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": ["HTTP API"],
        "memory_layers": [],
        "imported_by": [
            "clients.world_model_client",
            "core.singleton_registry",
            "runtime.l_tools",
        ],
    },
}
# ============================================================================

import os
from typing import Any

import httpx
import structlog
from pydantic import BaseModel

from core.decorators import must_stay_async

logger = structlog.get_logger(__name__)

# =============================================================================
# Configuration
# =============================================================================

DEFAULT_BASE_URL = "http://l9-api:8000"
DEFAULT_TIMEOUT = 30.0

# =============================================================================
# Response Models
# =============================================================================


class EntityData(BaseModel):
    """Entity data from API."""

    entity_id: str
    entity_type: str
    attributes: dict[str, Any]
    confidence: float
    created_at: str | None = None
    updated_at: str | None = None
    version: int = 1


class StateVersion(BaseModel):
    """State version data."""

    state_version: int
    entity_count: int


class SnapshotData(BaseModel):
    """Snapshot data from API."""

    snapshot_id: str
    state_version: int
    entity_count: int
    created_at: str
    description: str | None = None


class RestoreResult(BaseModel):
    """Restore operation result."""

    status: str
    snapshot_id: str
    entities_restored: int
    state_version: int


class InsightsResult(BaseModel):
    """Insights submission result."""

    status: str
    updates_applied: int = 0
    entities_affected: int = 0
    state_version: int = 0


class UpdateRecord(BaseModel):
    """Update record from API."""

    update_id: str
    insight_id: str | None = None
    insight_type: str | None = None
    entities: list[str]
    confidence: float
    applied_at: str


# =============================================================================
# World Model Client
# =============================================================================


class WorldModelClient:
    """
    Async HTTP client for L9 World Model API.

    Uses httpx for async HTTP operations.
    """

    def __init__(
        self,
        base_url: str | None = None,
        timeout: float = DEFAULT_TIMEOUT,
    ):
        """
        Initialize World Model client.

        Args:
            base_url: API base URL (default from env or http://l9-api:8000)
            timeout: Request timeout in seconds
        """
        self.base_url = base_url or os.getenv("L9_API_BASE_URL", DEFAULT_BASE_URL)
        self.timeout = timeout
        self._client: httpx.AsyncClient | None = None
        logger.info(f"WorldModelClient initialized: {self.base_url}")

    @must_stay_async("callers use await")
    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=self.timeout,
                headers={"Content-Type": "application/json"},
            )
        return self._client

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client is not None and not self._client.is_closed:
            await self._client.aclose()
            self._client = None
            logger.debug("WorldModelClient closed")

    @must_stay_async("async context manager protocol")
    async def __aenter__(self) -> WorldModelClient:
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        await self.close()

    # =========================================================================
    # Health Check
    # =========================================================================

    async def health_check(self) -> dict[str, Any]:
        """
        Check World Model API health.

        Returns:
            Health status dict
        """
        client = await self._get_client()
        try:
            response = await client.get("/world-model/health")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.warning(f"World model health check failed: {e}")
            return {"status": "error", "error": str(e)}

    # =========================================================================
    # Entity Operations
    # =========================================================================

    async def get_entity(self, entity_id: str) -> EntityData | None:
        """
        Get entity by ID.

        Args:
            entity_id: Entity identifier

        Returns:
            EntityData if found, None otherwise
        """
        client = await self._get_client()
        logger.debug(f"Getting entity: {entity_id}")

        try:
            response = await client.get(f"/world-model/entities/{entity_id}")
            if response.status_code == 404:
                return None
            response.raise_for_status()
            return EntityData.model_validate(response.json())
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return None
            raise

    async def list_entities(
        self,
        entity_type: str | None = None,
        min_confidence: float | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[EntityData]:
        """
        List entities with optional filtering.

        Args:
            entity_type: Filter by type
            min_confidence: Minimum confidence
            limit: Maximum results
            offset: Pagination offset

        Returns:
            List of entities
        """
        client = await self._get_client()
        logger.debug(f"Listing entities: type={entity_type}, limit={limit}")

        params = {"limit": limit, "offset": offset}
        if entity_type:
            params["entity_type"] = entity_type
        if min_confidence is not None:
            params["min_confidence"] = min_confidence

        response = await client.get("/world-model/entities", params=params)
        response.raise_for_status()

        data = response.json()
        return [EntityData.model_validate(e) for e in data.get("entities", [])]

    # =========================================================================
    # State Version
    # =========================================================================

    async def get_state_version(self) -> StateVersion:
        """
        Get current state version.

        Returns:
            State version and entity count
        """
        client = await self._get_client()
        response = await client.get("/world-model/state-version")
        response.raise_for_status()
        return StateVersion.model_validate(response.json())

    # =========================================================================
    # Snapshot Operations
    # =========================================================================

    async def snapshot(
        self,
        description: str | None = None,
        created_by: str = "client",
    ) -> SnapshotData:
        """
        Create a snapshot of current state.

        Args:
            description: Optional description
            created_by: Creator identifier

        Returns:
            Created snapshot data
        """
        client = await self._get_client()
        logger.info("Creating world model snapshot")

        response = await client.post(
            "/world-model/snapshot",
            json={
                "description": description,
                "created_by": created_by,
            },
        )
        response.raise_for_status()

        result = SnapshotData.model_validate(response.json())
        logger.info(f"Snapshot created: {result.snapshot_id}")
        return result

    async def restore(self, snapshot_id: str) -> RestoreResult:
        """
        Restore from a snapshot.

        WARNING: This replaces all current entities!

        Args:
            snapshot_id: Snapshot UUID to restore from

        Returns:
            Restore result
        """
        client = await self._get_client()
        logger.info(f"Restoring from snapshot: {snapshot_id}")

        response = await client.post(
            "/world-model/restore",
            json={"snapshot_id": snapshot_id},
        )
        response.raise_for_status()

        result = RestoreResult.model_validate(response.json())
        logger.info(f"Restored: {result.entities_restored} entities")
        return result

    async def list_snapshots(self, limit: int = 20) -> list[dict[str, Any]]:
        """
        List recent snapshots.

        Args:
            limit: Maximum results

        Returns:
            List of snapshot records
        """
        client = await self._get_client()
        response = await client.get(
            "/world-model/snapshots",
            params={"limit": limit},
        )
        response.raise_for_status()
        return response.json().get("snapshots", [])

    # =========================================================================
    # Insight Integration
    # =========================================================================

    async def send_insights_for_update(
        self,
        insights: list[dict[str, Any]],
    ) -> InsightsResult:
        """
        Submit insights for world model update.

        Args:
            insights: List of insight dicts with:
                - insight_type: str
                - content: str
                - entities: list[str]
                - confidence: float (optional)
                - trigger_world_model: bool (optional, default True)

        Returns:
            Update result
        """
        client = await self._get_client()
        logger.debug(f"Submitting {len(insights)} insights for update")

        # Ensure required fields
        normalized = []
        for i in insights:
            insight = {
                "insight_type": i.get("insight_type", "unknown"),
                "content": i.get("content", ""),
                "entities": i.get("entities", []),
                "confidence": i.get("confidence", 0.7),
                "trigger_world_model": i.get("trigger_world_model", True),
            }
            if "insight_id" in i:
                insight["insight_id"] = i["insight_id"]
            if "source_packet" in i:
                insight["source_packet"] = i["source_packet"]
            if "facts" in i:
                insight["facts"] = i["facts"]
            normalized.append(insight)

        response = await client.post(
            "/world-model/insights",
            json={"insights": normalized},
        )
        response.raise_for_status()

        result = InsightsResult.model_validate(response.json())
        logger.info(
            f"Insights processed: {result.updates_applied} updates, "
            f"{result.entities_affected} entities"
        )
        return result

    # =========================================================================
    # Updates History
    # =========================================================================

    async def list_updates(
        self,
        insight_type: str | None = None,
        min_confidence: float | None = None,
        limit: int = 100,
    ) -> list[UpdateRecord]:
        """
        List recent world model updates.

        Args:
            insight_type: Filter by type
            min_confidence: Minimum confidence
            limit: Maximum results

        Returns:
            List of update records
        """
        client = await self._get_client()

        params = {"limit": limit}
        if insight_type:
            params["insight_type"] = insight_type
        if min_confidence is not None:
            params["min_confidence"] = min_confidence

        response = await client.get("/world-model/updates", params=params)
        response.raise_for_status()

        data = response.json()
        return [UpdateRecord.model_validate(u) for u in data.get("updates", [])]


# =============================================================================
# Singleton / Factory
# =============================================================================

_client: WorldModelClient | None = None


def get_world_model_client() -> WorldModelClient:
    """Get or create singleton client."""
    global _client
    if _client is None:
        _client = WorldModelClient()
    return _client


async def close_world_model_client() -> None:
    """Close singleton client."""
    global _client
    if _client is not None:
        await _client.close()
        _client = None


# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "CLI-INTE-002",
    "governance_level": "medium",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": ["core.decorators"],
    "tags": [
        "api",
        "async",
        "client",
        "data-models",
        "debugging",
        "http-client",
        "integration",
        "logging",
        "pydantic",
        "rest-api",
    ],
    "keywords": [
        "await",
        "check",
        "client",
        "close",
        "entities",
        "entity",
        "health",
        "insights",
    ],
    "business_value": "the World Model API. from clients.world_model_client import get_world_model_client client = get_worl",
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
