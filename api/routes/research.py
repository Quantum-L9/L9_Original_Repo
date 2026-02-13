"""
L9 Research Swarm API Router
Version: 1.0.0

Research swarm orchestration endpoints for concurrent research agents.
"""

# ============================================================================
__dora_meta__ = {
    "component_name": "Research",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2025-12-26T17:26:57Z",
    "updated_at": "2026-01-17T23:47:56Z",
    "layer": "operations",
    "domain": "api_gateway",
    "module_name": "research",
    "type": "router",
    "status": "active",
    "integrates_with": {
        "api_endpoints": ["GET /test", "GET /status", "POST /execute"],
        "datasources": [],
        "memory_layers": [],
        "imported_by": ["api.server"],
    },
}
# ============================================================================

from typing import Any

import structlog
from fastapi import APIRouter, Depends, Header, HTTPException, Request
from pydantic import BaseModel, Field

from api.auth import verify_api_key
from core.decorators import must_stay_async
from orchestrators.research_swarm.interface import ResearchSwarmRequest
from orchestrators.research_swarm.orchestrator import ResearchSwarmOrchestrator

logger = structlog.get_logger(__name__)

router = APIRouter()

# AUTO-REGISTRATION (Phase 2 Auto-Wiring)
from api.routes.registry import router_registry

router_registry.register(
    router=router,
    prefix="/research/swarm",
    tags=["research-swarm"],
    display_name="Research Swarm",
    dependencies=["research_swarm_orchestrator"],
)


# ============================================================================
# Dependency: Get ResearchSwarmOrchestrator from app.state
# ============================================================================


def get_research_swarm_orchestrator(request: Request) -> ResearchSwarmOrchestrator:
    """Get ResearchSwarmOrchestrator from app.state."""
    orchestrator = getattr(request.app.state, "research_swarm_orchestrator", None)
    if orchestrator is None:
        raise HTTPException(
            status_code=503,
            detail="ResearchSwarmOrchestrator not initialized. Check server logs.",
        )
    return orchestrator


# ============================================================================
# Request/Response Models (API-facing)
# ============================================================================


class ResearchExecuteRequest(BaseModel):
    """Request model for research swarm execution."""

    query: str = Field(..., description="Research query to investigate")
    agent_count: int = Field(
        default=3, ge=1, le=10, description="Number of parallel research agents"
    )
    convergence_threshold: float = Field(
        default=0.8,
        ge=0.0,
        le=1.0,
        description="Agreement threshold for consensus (0.0-1.0)",
    )


class ResearchExecuteResponse(BaseModel):
    """Response model for research swarm execution."""

    success: bool = Field(..., description="Whether operation succeeded")
    message: str = Field(default="", description="Result message")
    results: list[dict[str, Any]] = Field(
        default_factory=list, description="Individual agent results"
    )
    consensus: str | None = Field(
        default=None, description="Converged consensus if reached"
    )


# ============================================================================
# Endpoints
# ============================================================================


@router.get("/test")
@must_stay_async("FastAPI/ASGI route handler")
async def research_test(
    authorization: str = Header(None),
    _: bool = Depends(verify_api_key),
):
    """Test endpoint to verify research router is reachable."""
    return {"ok": True, "msg": "research endpoint reachable"}


@router.get("/status")
@must_stay_async("FastAPI/ASGI route handler")
async def research_status(
    authorization: str = Header(None),
    _: bool = Depends(verify_api_key),
    orchestrator: ResearchSwarmOrchestrator = Depends(get_research_swarm_orchestrator),
):
    """Get research swarm orchestrator status."""
    return {
        "status": "ready",
        "orchestrator": "ResearchSwarmOrchestrator",
        "implementation": "active",
        "note": "Research swarm orchestrator active. Spawns parallel agents and attempts consensus.",
    }


@router.post("/execute", response_model=ResearchExecuteResponse)
@must_stay_async("callers use await")
async def execute_research(
    request: ResearchExecuteRequest,
    authorization: str = Header(None),
    _: bool = Depends(verify_api_key),
    orchestrator: ResearchSwarmOrchestrator = Depends(get_research_swarm_orchestrator),
):
    """
    Execute research swarm via ResearchSwarmOrchestrator.

    Runs concurrent research agents that:
    1. Independently investigate the query
    2. Generate individual results
    3. Converge toward consensus based on threshold
    """
    try:
        logger.info(
            "Research swarm execution request",
            query_length=len(request.query),
            agent_count=request.agent_count,
            convergence_threshold=request.convergence_threshold,
        )

        # Build orchestrator request
        research_request = ResearchSwarmRequest(
            query=request.query,
            agent_count=request.agent_count,
            convergence_threshold=request.convergence_threshold,
        )

        # Execute via orchestrator
        result = await orchestrator.execute(research_request)

        logger.info(
            "Research swarm execution complete",
            success=result.success,
            results_count=len(result.results),
            has_consensus=result.consensus is not None,
        )

        return ResearchExecuteResponse(
            success=result.success,
            message=result.message,
            results=result.results,
            consensus=result.consensus,
        )
    except Exception as e:
        logger.error(f"Research swarm execution failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Research execution failed: {e!s}"
        ) from e


# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "API-OPER-015",
    "governance_level": "medium",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": ["api.auth", "core.decorators"],
    "tags": [
        "api",
        "api-gateway",
        "async",
        "auth",
        "endpoint",
        "logging",
        "messaging",
        "operations",
        "pydantic",
        "router",
    ],
    "keywords": [
        "execute",
        "orchestrator",
        "research",
        "router",
        "status",
        "swarm",
        "test",
    ],
    "business_value": "Provides research components including ResearchExecuteRequest, ResearchExecuteResponse",
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
