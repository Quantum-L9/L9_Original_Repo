"""
L9 Reasoning API Router
Version: 1.0.0

Reasoning orchestration endpoints for chain/tree/forest-of-thought reasoning.
"""

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from pydantic import BaseModel, Field
from api.auth import verify_api_key
from typing import List, Optional
import structlog

from orchestrators.reasoning.interface import (
    ReasoningRequest,
    ReasoningMode,
)
from orchestrators.reasoning.orchestrator import ReasoningOrchestrator
from core.decorators import must_stay_async

logger = structlog.get_logger(__name__)

router = APIRouter()


# ============================================================================
# Dependency: Get ReasoningOrchestrator from app.state
# ============================================================================


def get_reasoning_orchestrator(request: Request) -> ReasoningOrchestrator:
    """Get ReasoningOrchestrator from app.state."""
    orchestrator = getattr(request.app.state, "reasoning_orchestrator", None)
    if orchestrator is None:
        raise HTTPException(
            status_code=503,
            detail="ReasoningOrchestrator not initialized. Check server logs.",
        )
    return orchestrator


# ============================================================================
# Request/Response Models (API-facing)
# ============================================================================


class ReasoningExecuteRequest(BaseModel):
    """Request model for reasoning execution."""

    context: str = Field(..., description="Input context to reason about")
    mode: str = Field(
        default="chain_of_thought",
        description="Reasoning mode: chain_of_thought, tree_of_thought, forest_of_thought, beam_search",
    )
    depth: int = Field(default=3, ge=1, le=10, description="Reasoning depth (1-10)")
    branch_factor: int = Field(
        default=3, ge=1, le=10, description="Branch factor for tree modes"
    )


class ReasoningExecuteResponse(BaseModel):
    """Response model for reasoning execution."""

    success: bool = Field(..., description="Whether operation succeeded")
    message: str = Field(default="", description="Result message")
    reasoning_trace: List[str] = Field(
        default_factory=list, description="Reasoning steps"
    )
    conclusion: Optional[str] = Field(default=None, description="Final conclusion")


# ============================================================================
# Endpoints
# ============================================================================


@router.get("/test")
@must_stay_async("FastAPI/ASGI route handler")
async def reasoning_test(
    authorization: str = Header(None),
    _: bool = Depends(verify_api_key),
):
    """Test endpoint to verify reasoning router is reachable."""
    return {"ok": True, "msg": "reasoning endpoint reachable"}


@router.get("/modes")
@must_stay_async("FastAPI/ASGI route handler")
async def get_reasoning_modes(
    authorization: str = Header(None),
    _: bool = Depends(verify_api_key),
):
    """Get available reasoning modes."""
    return {
        "modes": [
            {
                "id": "chain_of_thought",
                "name": "Chain of Thought",
                "description": "Sequential step-by-step reasoning with accumulating context",
            },
            {
                "id": "tree_of_thought",
                "name": "Tree of Thought",
                "description": "Branching exploration with evaluation and pruning",
            },
            {
                "id": "forest_of_thought",
                "name": "Forest of Thought",
                "description": "Multiple independent trees with ensemble conclusion",
            },
            {
                "id": "beam_search",
                "name": "Beam Search",
                "description": "Maintains top-k candidates at each reasoning step",
            },
        ]
    }


@router.post("/execute", response_model=ReasoningExecuteResponse)
async def execute_reasoning(
    request: ReasoningExecuteRequest,
    authorization: str = Header(None),
    _: bool = Depends(verify_api_key),
    orchestrator: ReasoningOrchestrator = Depends(get_reasoning_orchestrator),
):
    """
    Execute reasoning via ReasoningOrchestrator.

    Supports multiple reasoning modes:
    - chain_of_thought: Sequential step-by-step reasoning
    - tree_of_thought: Branching exploration
    - forest_of_thought: Ensemble of independent reasoning trees
    - beam_search: Top-k candidate tracking
    """
    try:
        # Validate and convert mode
        try:
            mode = ReasoningMode(request.mode)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid reasoning mode: {request.mode}. "
                f"Valid modes: chain_of_thought, tree_of_thought, forest_of_thought, beam_search",
            )

        logger.info(
            "Reasoning execution request",
            mode=mode.value,
            depth=request.depth,
            branch_factor=request.branch_factor,
            context_length=len(request.context),
        )

        # Build orchestrator request
        reasoning_request = ReasoningRequest(
            context=request.context,
            mode=mode,
            depth=request.depth,
            branch_factor=request.branch_factor,
        )

        # Execute via orchestrator
        result = await orchestrator.execute(reasoning_request)

        logger.info(
            "Reasoning execution complete",
            mode=mode.value,
            success=result.success,
            trace_length=len(result.reasoning_trace),
        )

        return ReasoningExecuteResponse(
            success=result.success,
            message=result.message,
            reasoning_trace=result.reasoning_trace,
            conclusion=result.conclusion,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Reasoning execution failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Reasoning execution failed: {str(e)}"
        )
