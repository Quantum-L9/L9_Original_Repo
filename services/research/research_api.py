"""
L9 Research Factory - Research API
Version: 1.0.0

FastAPI router for the /research endpoint.
"""

# ============================================================================
__dora_meta__ = {
    "component_name": "Research API",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2025-12-09T01:02:49Z",
    "updated_at": "2026-01-07T13:35:58Z",
    "layer": "operations",
    "domain": "api_gateway",
    "module_name": "research_api",
    "type": "router",
    "status": "active",
    "integrates_with": {
        "api_endpoints": ["GET /status/{thread_id}", "POST /resume/{thread_id}"],
        "datasources": [],
        "memory_layers": [],
        "imported_by": ["api.server", "services.research.__init__"],
    },
}
# ============================================================================

from uuid import uuid4

import structlog
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from api.routes.registry import router_registry
from services.research.graph_runtime import ResearchGraphRuntime, get_runtime

logger = structlog.get_logger(__name__)

# Create router
router = APIRouter(prefix="/research", tags=["research"])

# Auto-register with RouterRegistry
router_registry.register(
    router=router,
    prefix="",  # Router already has prefix="/research"
    tags=["research"],
    module_id="research_factory",
    display_name="Research Factory API",
)


# =============================================================================
# Request/Response Models
# =============================================================================


class ResearchRequest(BaseModel):
    """Request model for research endpoint."""

    query: str = Field(..., min_length=1, max_length=5000, description="Research query")
    user_id: str = Field(default="anonymous", description="User identifier")
    thread_id: str | None = Field(None, description="Optional thread ID for tracking")

    class Config:
        """
        Represents configuration settings for the research API, including JSON schema customization.

        Args:
            json_schema_extra: Dictionary containing example data for API schema validation.
        """

        json_schema_extra = {
            "example": {
                "query": "What are the latest advances in plastic recycling technology?",
                "user_id": "user_123",
                "thread_id": None,
            }
        }


class ResearchResponse(BaseModel):
    """Response model for research endpoint."""

    thread_id: str = Field(..., description="Thread ID for this research")
    query: str = Field(..., description="Original query")
    refined_goal: str = Field(default="", description="Refined research goal")
    summary: str = Field(default="", description="Research summary")
    sources: list[str] = Field(default_factory=list, description="Sources cited")
    evidence_count: int = Field(default=0, description="Number of evidence pieces")
    quality_score: float = Field(
        default=0.0, ge=0.0, le=1.0, description="Quality score"
    )
    feedback: str = Field(default="", description="Critic feedback")
    timestamp: str = Field(default="", description="Completion timestamp")
    error: str | None = Field(None, description="Error message if failed")

    class Config:
        """
        Config class for specifying JSON schema customization in the research API.
        Args:
            json_schema_extra: Dictionary containing additional schema details, such as example payloads.
        """

        json_schema_extra = {
            "example": {
                "thread_id": "abc123",
                "query": "What are the latest advances in plastic recycling technology?",
                "refined_goal": "Research latest advances in plastic recycling technology",
                "summary": "Recent advances include chemical recycling...",
                "sources": ["https://example.com/source1"],
                "evidence_count": 3,
                "quality_score": 0.85,
                "feedback": "Good quality research with comprehensive sources",
                "timestamp": "2024-01-15T10:30:00Z",
                "error": None,
            }
        }


class ResearchStatusResponse(BaseModel):
    """Response model for research status endpoint."""

    thread_id: str
    query: str
    refined_goal: str
    steps_completed: int
    total_steps: int
    evidence_count: int
    critic_score: float
    retry_count: int
    has_output: bool


# =============================================================================
# Dependencies
# =============================================================================


def get_research_runtime() -> ResearchGraphRuntime:
    """Dependency to get the research runtime."""
    runtime = get_runtime()
    if not runtime._initialized:
        raise HTTPException(status_code=503, detail="Research service not initialized")
    return runtime


# =============================================================================
# Endpoints
# =============================================================================


@router.post(
    "",
    response_model=ResearchResponse,
    summary="Execute research query",
    description="Submit a research query for multi-agent processing",
)
async def research(
    request: ResearchRequest,
    runtime: ResearchGraphRuntime = Depends(get_research_runtime),  # noqa: B008 — FastAPI dependency injection
) -> ResearchResponse:
    """
    Execute a research query.

    The query is processed by a multi-agent pipeline:
    1. Planner: Decomposes query into research steps
    2. Researcher: Gathers evidence using tools
    3. Merger: Synthesizes findings
    4. Critic: Evaluates quality (may trigger retry)
    5. Finalizer: Packages output

    Results are persisted to the Memory Substrate.
    """
    logger.info(f"Research request: query={request.query[:50]}...")

    try:
        result = await runtime.execute(
            query=request.query,
            user_id=request.user_id,
            thread_id=request.thread_id,
        )

        # Handle error in result
        if result.get("error"):
            return ResearchResponse(
                thread_id=result.get("thread_id", str(uuid4())),
                query=request.query,
                error=result["error"],
            )

        return ResearchResponse(
            thread_id=result.get("thread_id", ""),
            query=result.get("query", request.query),
            refined_goal=result.get("refined_goal", ""),
            summary=result.get("summary", ""),
            sources=result.get("sources", []),
            evidence_count=result.get("evidence_count", 0),
            quality_score=result.get("quality_score", 0.0),
            feedback=result.get("feedback", ""),
            timestamp=result.get("timestamp", ""),
        )

    except Exception as e:
        logger.error(f"Research failed: {e}")
        raise HTTPException(
            status_code=500, detail=f"Research execution failed: {e!s}"
        ) from e


@router.get(
    "/status/{thread_id}",
    response_model=ResearchStatusResponse,
    summary="Get research status",
    description="Get the status of a research thread",
)
async def get_research_status(
    thread_id: str,
    runtime: ResearchGraphRuntime = Depends(get_research_runtime),  # noqa: B008 — FastAPI dependency injection
) -> ResearchStatusResponse:
    """
    Get status of a research thread.

    Returns current progress and state of the research.
    """
    status = await runtime.get_status(thread_id)

    if not status:
        raise HTTPException(
            status_code=404, detail=f"Research thread not found: {thread_id}"
        )

    return ResearchStatusResponse(**status)


@router.post(
    "/resume/{thread_id}",
    response_model=ResearchResponse,
    summary="Resume research from checkpoint",
    description="Resume a previously interrupted research thread",
)
async def resume_research(
    thread_id: str,
    runtime: ResearchGraphRuntime = Depends(get_research_runtime),  # noqa: B008 — FastAPI dependency injection
) -> ResearchResponse:
    """
    Resume research from a checkpoint.

    Loads the last saved state and continues execution.
    """
    logger.info(f"Resuming research: thread={thread_id}")

    try:
        result = await runtime.resume(thread_id)

        if result is None:
            raise HTTPException(
                status_code=404, detail=f"No checkpoint found for thread: {thread_id}"
            )

        return ResearchResponse(
            thread_id=result.get("thread_id", thread_id),
            query=result.get("query", ""),
            refined_goal=result.get("refined_goal", ""),
            summary=result.get("summary", ""),
            sources=result.get("sources", []),
            evidence_count=result.get("evidence_count", 0),
            quality_score=result.get("quality_score", 0.0),
            feedback=result.get("feedback", ""),
            timestamp=result.get("timestamp", ""),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Resume failed: {e}")
        raise HTTPException(status_code=500, detail=f"Resume failed: {e!s}") from e


# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "SER-OPER-004",
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
        "messaging",
        "operations",
        "pydantic",
        "router",
        "testing",
    ],
    "keywords": ["api", "research", "resume", "router", "runtime", "status"],
    "business_value": "Provides research api components including ResearchRequest, ResearchResponse, ResearchStatusResponse",
    "last_modified": "2026-01-07T13:35:58Z",
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
