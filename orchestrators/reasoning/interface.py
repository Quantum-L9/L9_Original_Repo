"""
L9 Reasoning Orchestrator - Interface
Version: 1.0.0

Controls reasoning engine modes, depth, tree/forest strategy.
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
        "imported_by": ["api.routes.reasoning"],
    },
}
# ============================================================================

from typing import Protocol, List, Optional
from pydantic import BaseModel, Field
from enum import Enum
from core.decorators import must_stay_async


class ReasoningMode(str, Enum):
    """Reasoning engine modes."""

    CHAIN_OF_THOUGHT = "chain_of_thought"
    TREE_OF_THOUGHT = "tree_of_thought"
    FOREST_OF_THOUGHT = "forest_of_thought"
    BEAM_SEARCH = "beam_search"


class ReasoningRequest(BaseModel):
    """Request to reasoning orchestrator."""

    context: str = Field(default="", description="Input context")
    mode: ReasoningMode = Field(
        default=ReasoningMode.CHAIN_OF_THOUGHT, description="Reasoning mode"
    )
    depth: int = Field(default=3, description="Reasoning depth")
    branch_factor: int = Field(default=3, description="Branch factor for tree modes")


class ReasoningResponse(BaseModel):
    """Response from reasoning orchestrator."""

    success: bool = Field(..., description="Whether operation succeeded")
    message: str = Field(..., description="Result message")
    reasoning_trace: List[str] = Field(
        default_factory=list, description="Reasoning steps"
    )
    conclusion: Optional[str] = Field(default=None, description="Final conclusion")


class IReasoningOrchestrator(Protocol):
    """Interface for Reasoning Orchestrator."""

    @must_stay_async("callers use await")
    async def execute(self, request: ReasoningRequest) -> ReasoningResponse:
        """Execute reasoning orchestration."""
        ...

# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "ORC-INTE-014",
    "governance_level": "high",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": ["core.decorators"],
    "tags": ["async", "data-models", "enum", "intelligence", "messaging", "orchestration", "pydantic", "rest-api", "tracing", "validation"],
    "keywords": ["execute", "interface", "mode", "orchestrator", "reasoning"],
    "business_value": "Provides interface components including ReasoningMode, ReasoningRequest, ReasoningResponse",
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
