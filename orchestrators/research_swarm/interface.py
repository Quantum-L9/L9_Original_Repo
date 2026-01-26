"""
L9 ResearchSwarm Orchestrator - Interface
Version: 1.0.0

Runs concurrent research agents, analyst pass, dreamers, convergence.
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
    "type": "schema",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": [],
        "memory_layers": [],
        "imported_by": ["api.routes.research"],
    },
}
# ============================================================================

from typing import Any, Protocol

from pydantic import BaseModel, Field

from core.decorators import must_stay_async


class ResearchSwarmRequest(BaseModel):
    """Request to research_swarm orchestrator."""

    query: str = Field(default="", description="Research query")
    agent_count: int = Field(default=3, description="Number of parallel agents")
    convergence_threshold: float = Field(default=0.8, description="Agreement threshold")


class ResearchSwarmResponse(BaseModel):
    """Response from research_swarm orchestrator."""

    success: bool = Field(..., description="Whether operation succeeded")
    message: str = Field(..., description="Result message")
    results: list[dict[str, Any]] = Field(
        default_factory=list, description="Agent results"
    )
    consensus: str | None = Field(default=None, description="Converged consensus")


class IResearchSwarmOrchestrator(Protocol):
    """Interface for ResearchSwarm Orchestrator."""

    @must_stay_async("callers use await")
    async def execute(self, request: ResearchSwarmRequest) -> ResearchSwarmResponse:
        """Execute research_swarm orchestration."""
        ...


# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "ORC-INTE-018",
    "governance_level": "high",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": ["core.decorators"],
    "tags": [
        "async",
        "data-models",
        "intelligence",
        "messaging",
        "orchestration",
        "pydantic",
        "schema",
        "validation",
    ],
    "keywords": ["execute", "interface", "orchestrator", "research", "swarm"],
    "business_value": "Provides interface components including ResearchSwarmRequest, ResearchSwarmResponse, IResearchSwarmOrchestrator",
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
