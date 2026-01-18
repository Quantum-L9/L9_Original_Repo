"""
L9 WorldModel Orchestrator - Interface
Version: 1.0.0

Drives world-model lifecycle, ingest updates, schedule propagation.
"""

# ============================================================================
__dora_meta__ = {
    "component_name": "Interface",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2025-12-09T01:02:49Z",
    "updated_at": "2026-01-17T23:47:56Z",
    "layer": "intelligence",
    "domain": "data_models",
    "module_name": "interface",
    "type": "enum",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": [],
        "memory_layers": [],
        "imported_by": [],
    },
}
# ============================================================================

from typing import Protocol, List, Dict, Any, Optional
from pydantic import BaseModel, Field
from enum import Enum
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
    updates: List[Dict[str, Any]] = Field(
        default_factory=list, description="Updates to ingest"
    )
    snapshot_id: Optional[str] = Field(
        default=None, description="Snapshot ID for restore"
    )


class WorldModelResponse(BaseModel):
    """Response from world_model orchestrator."""

    success: bool = Field(..., description="Whether operation succeeded")
    message: str = Field(..., description="Result message")
    affected_entities: List[str] = Field(
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
        insights: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Update world model from extracted insights."""
        ...

# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "ORC-INTE-011",
    "governance_level": "high",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": ["core.decorators"],
    "tags": ["async", "data-models", "enum", "intelligence", "messaging", "orchestration", "pydantic", "rest-api", "scheduling", "validation"],
    "keywords": ["execute", "insights", "interface", "model", "operation", "orchestrator", "update", "world"],
    "business_value": "Provides interface components including WorldModelOperation, WorldModelRequest, WorldModelResponse",
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
