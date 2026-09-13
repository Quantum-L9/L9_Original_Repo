"""
L9 WorldModel Orchestrator - Interface
Version: 1.0.0

Drives world-model lifecycle, ingest updates, schedule propagation.
"""


from enum import Enum
from typing import Any, Protocol

from pydantic import BaseModel, Field

from core.decorators import must_stay_async


class WorldModelOperation(str, Enum):
    """World model operation types."""

    INGEST = "ingest"
    PROPAGATE = "propagate"
    SNAPSHOT = "snapshot"
    RESTORE = "restore"


class WorldModelRequest(BaseModel):
    """Request to world_model orchestrator."""

    operation: WorldModelOperation = Field(
        default=WorldModelOperation.INGEST, description="Operation type"
    )
    updates: list[dict[str, Any]] = Field(
        default_factory=list, description="Updates to ingest"
    )
    snapshot_id: str | None = Field(default=None, description="Snapshot ID for restore")


class WorldModelResponse(BaseModel):
    """Response from world_model orchestrator."""

    success: bool = Field(..., description="Whether operation succeeded")
    message: str = Field(..., description="Result message")
    affected_entities: list[str] = Field(
        default_factory=list, description="Affected entity IDs"
    )
    state_version: int = Field(default=0, description="Current state version")


class IWorldModelOrchestrator(Protocol):
    """Interface for WorldModel Orchestrator."""

    @must_stay_async("callers use await")
    async def execute(self, request: WorldModelRequest) -> WorldModelResponse:
        """Execute world_model orchestration."""
        ...

    @must_stay_async("callers use await")
    async def update_from_insights(
        self,
        insights: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Update world model from extracted insights."""
        ...


# Runtime execution trace - updated automatically on every execution
