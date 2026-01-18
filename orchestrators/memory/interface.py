"""
L9 Memory Orchestrator - Interface
Version: 1.0.0

Manages memory substrate usage: batching, replay, garbage collection.
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
        "imported_by": [
            "api.memory.router",
            "tests.integration.test_orchestrator_memory_integration",
        ],
    },
}
# ============================================================================

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


# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "ORC-INTE-005",
    "governance_level": "high",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": ["core.decorators"],
    "tags": [
        "async",
        "batch-processing",
        "data-models",
        "enum",
        "intelligence",
        "messaging",
        "orchestration",
        "pydantic",
        "validation",
    ],
    "keywords": [
        "execute",
        "interface",
        "memory",
        "operation",
        "orchestrator",
        "substrate",
    ],
    "business_value": "Provides interface components including MemoryOperation, MemoryRequest, MemoryResponse",
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
