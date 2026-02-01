"""
Evaluation API Routes

Provides endpoints for running agent evaluations, viewing results,
and managing evaluation sets.

Version: 1.0.0
GMP: GMP-WIRE-VC-EQ
"""

from __future__ import annotations

from typing import Any

import structlog
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/eval", tags=["evaluation"])

# AUTO-REGISTRATION (ARCH-01 Migration)
from api.routes.registry import router_registry

router_registry.register(
    router=router,
    prefix="/eval",
    tags=["evaluation"],
    display_name="Agent Evaluation",
    dependencies=["evaluator"],  # Depends on the evaluator service
)


# =============================================================================
# REQUEST/RESPONSE MODELS
# =============================================================================


class RunEvalRequest(BaseModel):
    """Request to run an evaluation"""

    agent_id: str = "L"
    eval_set_name: str
    version: str = "latest"


class EvalResultResponse(BaseModel):
    """Evaluation result response"""

    agent_id: str
    eval_set_name: str
    version: str
    task_success_rate: float
    avg_latency_ms: float
    tool_accuracy: float
    llm_as_judge_score: float
    examples_run: int
    examples_passed: int
    error_count: int


class EvalSetInfo(BaseModel):
    """Information about an evaluation set"""

    name: str
    description: str
    example_count: int


class CompareBaselineResponse(BaseModel):
    """Baseline comparison response"""

    task_success_rate_delta: float
    latency_delta_ms: float
    tool_accuracy_delta: float
    llm_judge_delta: float | None = None
    is_first_baseline: bool = False
    baseline_version: str | None = None


# =============================================================================
# ENDPOINTS
# =============================================================================


@router.get("/sets", response_model=list[EvalSetInfo])
async def list_eval_sets(request: Request) -> list[EvalSetInfo]:
    """
    List all available evaluation sets.

    Returns:
        List of evaluation set info including name, description, and example count.
    """
    evaluator = getattr(request.app.state, "evaluator", None)
    if evaluator is None:
        raise HTTPException(
            status_code=503,
            detail="Evaluator not available",
        )

    return [
        EvalSetInfo(
            name=name,
            description=eval_set.description,
            example_count=len(eval_set.examples),
        )
        for name, eval_set in evaluator.eval_sets.items()
    ]


@router.post("/run", response_model=EvalResultResponse)
async def run_evaluation(
    request: Request,
    body: RunEvalRequest,
) -> EvalResultResponse:
    """
    Run an evaluation set against an agent.

    This executes all examples in the evaluation set and returns
    aggregate metrics including success rate, latency, and LLM-as-judge scores.

    Args:
        body: Request containing agent_id, eval_set_name, and version

    Returns:
        EvalResultResponse with all evaluation metrics
    """
    evaluator = getattr(request.app.state, "evaluator", None)
    if evaluator is None:
        raise HTTPException(
            status_code=503,
            detail="Evaluator not available",
        )

    if body.eval_set_name not in evaluator.eval_sets:
        raise HTTPException(
            status_code=404,
            detail=f"Eval set not found: {body.eval_set_name}. "
            f"Available: {list(evaluator.eval_sets.keys())}",
        )

    try:
        logger.info(
            "Starting evaluation",
            agent_id=body.agent_id,
            eval_set=body.eval_set_name,
            version=body.version,
        )

        result = await evaluator.run_eval(
            agent_id=body.agent_id,
            eval_set_name=body.eval_set_name,
            version=body.version,
        )

        return EvalResultResponse(
            agent_id=result.agent_id,
            eval_set_name=result.eval_set_name,
            version=result.version,
            task_success_rate=result.task_success_rate,
            avg_latency_ms=result.avg_latency_ms,
            tool_accuracy=result.tool_accuracy,
            llm_as_judge_score=result.llm_as_judge_score,
            examples_run=result.examples_run,
            examples_passed=result.examples_passed,
            error_count=result.error_count,
        )

    except Exception as e:
        logger.error("Evaluation failed", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Evaluation failed: {e!s}",
        ) from e


@router.post("/compare", response_model=CompareBaselineResponse)
async def compare_to_baseline(
    request: Request,
    body: RunEvalRequest,
) -> CompareBaselineResponse:
    """
    Run evaluation and compare results to baseline.

    This runs the evaluation and then compares the results against
    the stored baseline for regression detection.

    Args:
        body: Request containing agent_id, eval_set_name, and version

    Returns:
        CompareBaselineResponse with delta metrics
    """
    evaluator = getattr(request.app.state, "evaluator", None)
    if evaluator is None:
        raise HTTPException(
            status_code=503,
            detail="Evaluator not available",
        )

    if body.eval_set_name not in evaluator.eval_sets:
        raise HTTPException(
            status_code=404,
            detail=f"Eval set not found: {body.eval_set_name}",
        )

    try:
        # Run current evaluation
        result = await evaluator.run_eval(
            agent_id=body.agent_id,
            eval_set_name=body.eval_set_name,
            version=body.version,
        )

        # Compare to baseline
        delta = await evaluator.compare_to_baseline(result)

        return CompareBaselineResponse(
            task_success_rate_delta=delta.get("task_success_rate_delta", 0.0),
            latency_delta_ms=delta.get("latency_delta_ms", 0.0),
            tool_accuracy_delta=delta.get("tool_accuracy_delta", 0.0),
            llm_judge_delta=delta.get("llm_judge_delta"),
            is_first_baseline=delta.get("is_first_baseline", False),
            baseline_version=delta.get("baseline_version"),
        )

    except Exception as e:
        logger.error("Baseline comparison failed", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Baseline comparison failed: {e!s}",
        ) from e


@router.get("/health")
async def eval_health(request: Request) -> dict[str, Any]:
    """
    Check evaluator health status.

    Returns:
        Health status including available eval sets and LLM availability.
    """
    evaluator = getattr(request.app.state, "evaluator", None)

    return {
        "status": "healthy" if evaluator is not None else "unavailable",
        "eval_sets_loaded": len(evaluator.eval_sets) if evaluator else 0,
        "llm_available": evaluator.llm is not None if evaluator else False,
        "eval_sets": list(evaluator.eval_sets.keys()) if evaluator else [],
    }
