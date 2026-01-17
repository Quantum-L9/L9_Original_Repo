"""
L9 Memory Orchestrator - Interface
Version: 1.0.0

Manages memory substrate usage: batching, replay, garbage collection.
"""

from typing import Protocol, List, Dict, Any
from pydantic import BaseModel, Field
from enum import Enum
from core.decorators import must_stay_async


class MemoryOperation(str, Enum):
    """Memory operation types."""

    BATCH_WRITE = "batch_write"
    REPLAY = "replay"
    GC = "garbage_collection"
    COMPACT = "compact"


class MemoryRequest(BaseModel):
    """Request to memory orchestrator."""

    operation: MemoryOperation = Field(
        default=MemoryOperation.BATCH_WRITE, description="Operation type"
    )
    packets: List[Dict[str, Any]] = Field(
        default_factory=list, description="Packets to process"
    )
    gc_threshold_days: int = Field(default=30, description="GC threshold in days")

    # Multi-tenant RLS context (required for all operations)
    tenant_id: str = Field(..., description="Tenant UUID for RLS isolation")
    org_id: str = Field(..., description="Organization UUID for RLS isolation")
    user_id: str = Field(..., description="User UUID for RLS isolation")
    role: str = Field(
        default="end_user",
        description="User role: platform_admin, tenant_admin, org_admin, end_user",
    )


class MemoryResponse(BaseModel):
    """Response from memory orchestrator."""

    success: bool = Field(..., description="Whether operation succeeded")
    message: str = Field(..., description="Result message")
    processed_count: int = Field(default=0, description="Number of items processed")
    errors: List[str] = Field(
        default_factory=list, description="Any errors encountered"
    )


class IMemoryOrchestrator(Protocol):
    """Interface for Memory Orchestrator."""

    @must_stay_async("callers use await")
    async def execute(self, request: MemoryRequest) -> MemoryResponse:
        """Execute memory orchestration."""
        ...
