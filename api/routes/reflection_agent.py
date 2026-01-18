"""
L9 Reflection Agent API Router
==============================

API endpoints for the ReflectionAgent:
- /reflect: Execute reflection on execution history
- /analyze-failure: Deep failure root cause analysis
- /compare: Compare two approaches
- /extract-patterns: Extract patterns from examples
- /generate-improvements: Generate improvement plans
- /lessons-learned: Get accumulated lessons

Version: 1.0.0
GMP: wire_reflection_agent_yaml
"""

from __future__ import annotations

# ============================================================================
__dora_meta__ = {
    "component_name": "Reflection Agent",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2026-01-16T12:13:08Z",
    "updated_at": "2026-01-17T23:47:56Z",
    "layer": "operations",
    "domain": "api_gateway",
    "module_name": "reflection_agent",
    "type": "router",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [
            "GET /status",
            "POST /reflect",
            "POST /analyze-failure",
            "POST /compare",
            "POST /extract-patterns",
            "POST /generate-improvements",
            "GET /lessons-learned",
            "DELETE /lessons-learned",
        ],
        "datasources": [],
        "memory_layers": [],
        "imported_by": ["api.server"],
    },
}
# ============================================================================

from typing import Any, Optional

import structlog
from fastapi import APIRouter, Depends, Header, HTTPException, Request
from pydantic import BaseModel, Field

from api.auth import verify_api_key
from core.decorators import must_stay_async

logger = structlog.get_logger(__name__)

router = APIRouter()


# ============================================================================
# Dependency: Get ReflectionAgent from app.state
# ============================================================================


def get_reflection_agent(request: Request):
    """Get ReflectionAgent from app.state."""
    agent = getattr(request.app.state, "reflection_agent", None)
    if agent is None:
        raise HTTPException(
            status_code=503,
            detail="ReflectionAgent not initialized. Check server logs.",
        )
    return agent


# ============================================================================
# Request/Response Models
# ============================================================================


class ReflectRequest(BaseModel):
    """Request model for reflection task."""

    history: list[dict[str, Any]] = Field(
        ..., min_length=1, description="Execution history to reflect on"
    )
    focus: str = Field(
        default="general", description="Focus area (general, failures, patterns)"
    )
    goals: Optional[list[str]] = Field(
        default=None, description="Goals to evaluate against"
    )


class ReflectResponse(BaseModel):
    """Response model for reflection result."""

    success: bool = Field(..., description="Whether operation succeeded")
    analysis: Optional[dict[str, Any]] = Field(
        default=None, description="Analysis of successes, failures, patterns"
    )
    insights: list[dict[str, Any]] = Field(
        default_factory=list, description="Key insights with confidence"
    )
    lessons_learned: list[dict[str, Any]] = Field(
        default_factory=list, description="Lessons learned with priority"
    )
    improvements: list[dict[str, Any]] = Field(
        default_factory=list, description="Proposed improvements"
    )
    knowledge_updates: list[dict[str, Any]] = Field(
        default_factory=list, description="Knowledge base updates"
    )
    meta_observations: list[str] = Field(
        default_factory=list, description="Meta-level observations"
    )
    summary: str = Field(default="", description="Summary of reflection")
    error: Optional[str] = Field(default=None, description="Error message if failed")


class AnalyzeFailureRequest(BaseModel):
    """Request model for failure analysis."""

    failure_context: dict[str, Any] = Field(..., description="Context of the failure")
    error: str = Field(..., min_length=1, description="Error message")
    stack_trace: Optional[str] = Field(default=None, description="Optional stack trace")


class AnalyzeFailureResponse(BaseModel):
    """Response model for failure analysis."""

    success: bool = Field(..., description="Whether operation succeeded")
    root_cause_analysis: Optional[dict[str, Any]] = Field(
        default=None, description="Root cause analysis"
    )
    similar_past_failures: list[str] = Field(
        default_factory=list, description="Similar past failures"
    )
    prevention_strategies: list[dict[str, Any]] = Field(
        default_factory=list, description="Prevention strategies"
    )
    recovery_actions: list[str] = Field(
        default_factory=list, description="Immediate recovery actions"
    )
    detection_improvements: list[str] = Field(
        default_factory=list, description="How to detect earlier"
    )
    systemic_changes: list[str] = Field(
        default_factory=list, description="Broader systemic changes"
    )
    lessons: list[str] = Field(default_factory=list, description="Key lessons")
    error: Optional[str] = Field(default=None, description="Error message if failed")


class CompareApproachesRequest(BaseModel):
    """Request model for approach comparison."""

    approach_a: dict[str, Any] = Field(..., description="First approach")
    approach_b: dict[str, Any] = Field(..., description="Second approach")
    criteria: list[str] = Field(..., min_length=1, description="Comparison criteria")


class CompareApproachesResponse(BaseModel):
    """Response model for approach comparison."""

    success: bool = Field(..., description="Whether operation succeeded")
    comparison: list[dict[str, Any]] = Field(
        default_factory=list, description="Per-criterion comparison"
    )
    overall_scores: Optional[dict[str, float]] = Field(
        default=None, description="Overall scores for each approach"
    )
    recommendation: str = Field(
        default="", description="Recommendation: A, B, or hybrid"
    )
    hybrid_suggestion: str = Field(default="", description="Hybrid approach suggestion")
    key_differentiators: list[str] = Field(
        default_factory=list, description="Key differentiators"
    )
    context_dependencies: list[str] = Field(
        default_factory=list, description="When each is better"
    )
    reasoning: str = Field(default="", description="Reasoning behind recommendation")
    error: Optional[str] = Field(default=None, description="Error message if failed")


class ExtractPatternsRequest(BaseModel):
    """Request model for pattern extraction."""

    examples: list[dict[str, Any]] = Field(
        ..., min_length=2, description="Examples to analyze"
    )


class ExtractPatternsResponse(BaseModel):
    """Response model for pattern extraction."""

    success: bool = Field(..., description="Whether operation succeeded")
    patterns: list[dict[str, Any]] = Field(
        default_factory=list, description="Extracted patterns"
    )
    anti_patterns: list[dict[str, Any]] = Field(
        default_factory=list, description="Anti-patterns to avoid"
    )
    correlations: list[str] = Field(
        default_factory=list, description="Pattern correlations"
    )
    outliers: list[str] = Field(
        default_factory=list, description="Examples that don't fit patterns"
    )
    generalizations: list[str] = Field(
        default_factory=list, description="Broader rules derived"
    )
    confidence: float = Field(default=0.0, description="Confidence in patterns")
    error: Optional[str] = Field(default=None, description="Error message if failed")


class GenerateImprovementsRequest(BaseModel):
    """Request model for improvement generation."""

    current_performance: dict[str, Any] = Field(
        ..., description="Current performance metrics"
    )
    goals: list[str] = Field(..., min_length=1, description="Improvement goals")


class GenerateImprovementsResponse(BaseModel):
    """Response model for improvement generation."""

    success: bool = Field(..., description="Whether operation succeeded")
    gap_analysis: Optional[dict[str, Any]] = Field(
        default=None, description="Current vs goal gap analysis"
    )
    improvement_plan: list[dict[str, Any]] = Field(
        default_factory=list, description="Prioritized improvement plan"
    )
    quick_wins: list[str] = Field(
        default_factory=list, description="Low effort, high impact"
    )
    strategic_changes: list[str] = Field(
        default_factory=list, description="High effort, high impact"
    )
    risks: list[str] = Field(default_factory=list, description="Potential risks")
    measurement_plan: str = Field(default="", description="How to track progress")
    error: Optional[str] = Field(default=None, description="Error message if failed")


class LessonsLearnedResponse(BaseModel):
    """Response model for lessons learned."""

    success: bool = Field(..., description="Whether operation succeeded")
    lessons: list[dict[str, Any]] = Field(
        default_factory=list, description="Accumulated lessons"
    )
    count: int = Field(default=0, description="Number of lessons")


# ============================================================================
# Endpoints
# ============================================================================


@router.get("/status")
@must_stay_async("FastAPI/ASGI route handler")
async def reflection_agent_status(
    authorization: str = Header(None),
    _: bool = Depends(verify_api_key),
    agent=Depends(get_reflection_agent),
):
    """Get ReflectionAgent status and capabilities."""
    return {
        "status": "ready",
        "agent_id": agent.agent_id,
        "agent_name": agent.agent_name,
        "capabilities": [
            "reflect (analyze execution history)",
            "analyze_failure (deep root cause analysis)",
            "compare_approaches (score and recommend)",
            "extract_patterns (identify patterns)",
            "generate_improvements (gap analysis + plan)",
        ],
        "lessons_accumulated": len(agent.get_lessons_learned()),
    }


@router.post("/reflect", response_model=ReflectResponse)
async def reflect(
    request: ReflectRequest,
    authorization: str = Header(None),
    _: bool = Depends(verify_api_key),
    agent=Depends(get_reflection_agent),
):
    """
    Execute reflection on execution history.

    Analyzes successes, failures, and patterns to derive
    lessons and propose improvements.
    """
    try:
        logger.info(
            "reflection_agent.reflect",
            focus=request.focus,
            history_size=len(request.history),
        )

        task = {
            "history": request.history,
            "focus": request.focus,
            "goals": request.goals or [],
        }
        response = await agent.run(task)

        if response.success and response.structured_output:
            output = response.structured_output
            return ReflectResponse(
                success=True,
                analysis=output.get("analysis"),
                insights=output.get("insights", []),
                lessons_learned=output.get("lessons_learned", []),
                improvements=output.get("improvements", []),
                knowledge_updates=output.get("knowledge_updates", []),
                meta_observations=output.get("meta_observations", []),
                summary=output.get("summary", ""),
            )
        else:
            return ReflectResponse(
                success=False,
                error=response.content or "Reflection failed",
            )
    except Exception as e:
        logger.error("reflection_agent.reflect failed", error=str(e), exc_info=True)
        return ReflectResponse(success=False, error=str(e))


@router.post("/analyze-failure", response_model=AnalyzeFailureResponse)
async def analyze_failure(
    request: AnalyzeFailureRequest,
    authorization: str = Header(None),
    _: bool = Depends(verify_api_key),
    agent=Depends(get_reflection_agent),
):
    """
    Deep failure root cause analysis.

    Identifies immediate cause, root cause, chain of events,
    prevention strategies, and recovery actions.
    """
    try:
        logger.info(
            "reflection_agent.analyze_failure",
            error=request.error[:100],
            has_stack_trace=request.stack_trace is not None,
        )

        result = await agent.analyze_failure(
            failure_context=request.failure_context,
            error=request.error,
            stack_trace=request.stack_trace,
        )

        if result:
            return AnalyzeFailureResponse(
                success=True,
                root_cause_analysis=result.get("root_cause_analysis"),
                similar_past_failures=result.get("similar_past_failures", []),
                prevention_strategies=result.get("prevention_strategies", []),
                recovery_actions=result.get("recovery_actions", []),
                detection_improvements=result.get("detection_improvements", []),
                systemic_changes=result.get("systemic_changes", []),
                lessons=result.get("lessons", []),
            )
        else:
            return AnalyzeFailureResponse(
                success=False,
                error="Failure analysis returned empty result",
            )
    except Exception as e:
        logger.error(
            "reflection_agent.analyze_failure failed", error=str(e), exc_info=True
        )
        return AnalyzeFailureResponse(success=False, error=str(e))


@router.post("/compare", response_model=CompareApproachesResponse)
async def compare_approaches(
    request: CompareApproachesRequest,
    authorization: str = Header(None),
    _: bool = Depends(verify_api_key),
    agent=Depends(get_reflection_agent),
):
    """
    Compare two approaches with scoring.

    Evaluates each approach against criteria and provides
    recommendation with reasoning.
    """
    try:
        logger.info(
            "reflection_agent.compare_approaches",
            criteria_count=len(request.criteria),
        )

        result = await agent.compare_approaches(
            approach_a=request.approach_a,
            approach_b=request.approach_b,
            criteria=request.criteria,
        )

        if result:
            return CompareApproachesResponse(
                success=True,
                comparison=result.get("comparison", []),
                overall_scores=result.get("overall_scores"),
                recommendation=result.get("recommendation", ""),
                hybrid_suggestion=result.get("hybrid_suggestion", ""),
                key_differentiators=result.get("key_differentiators", []),
                context_dependencies=result.get("context_dependencies", []),
                reasoning=result.get("reasoning", ""),
            )
        else:
            return CompareApproachesResponse(
                success=False,
                error="Comparison returned empty result",
            )
    except Exception as e:
        logger.error(
            "reflection_agent.compare_approaches failed", error=str(e), exc_info=True
        )
        return CompareApproachesResponse(success=False, error=str(e))


@router.post("/extract-patterns", response_model=ExtractPatternsResponse)
async def extract_patterns(
    request: ExtractPatternsRequest,
    authorization: str = Header(None),
    _: bool = Depends(verify_api_key),
    agent=Depends(get_reflection_agent),
):
    """
    Extract patterns from examples.

    Identifies recurring patterns, anti-patterns, correlations,
    and generalizable rules.
    """
    try:
        logger.info(
            "reflection_agent.extract_patterns",
            examples_count=len(request.examples),
        )

        result = await agent.extract_patterns(examples=request.examples)

        if result:
            return ExtractPatternsResponse(
                success=True,
                patterns=result.get("patterns", []),
                anti_patterns=result.get("anti_patterns", []),
                correlations=result.get("correlations", []),
                outliers=result.get("outliers", []),
                generalizations=result.get("generalizations", []),
                confidence=result.get("confidence", 0.0),
            )
        else:
            return ExtractPatternsResponse(
                success=False,
                error="Pattern extraction returned empty result",
            )
    except Exception as e:
        logger.error(
            "reflection_agent.extract_patterns failed", error=str(e), exc_info=True
        )
        return ExtractPatternsResponse(success=False, error=str(e))


@router.post("/generate-improvements", response_model=GenerateImprovementsResponse)
async def generate_improvements(
    request: GenerateImprovementsRequest,
    authorization: str = Header(None),
    _: bool = Depends(verify_api_key),
    agent=Depends(get_reflection_agent),
):
    """
    Generate improvement plan from current performance.

    Performs gap analysis and generates prioritized
    improvement plan with quick wins and strategic changes.
    """
    try:
        logger.info(
            "reflection_agent.generate_improvements",
            goals_count=len(request.goals),
        )

        result = await agent.generate_improvements(
            current_performance=request.current_performance,
            goals=request.goals,
        )

        if result:
            return GenerateImprovementsResponse(
                success=True,
                gap_analysis=result.get("gap_analysis"),
                improvement_plan=result.get("improvement_plan", []),
                quick_wins=result.get("quick_wins", []),
                strategic_changes=result.get("strategic_changes", []),
                risks=result.get("risks", []),
                measurement_plan=result.get("measurement_plan", ""),
            )
        else:
            return GenerateImprovementsResponse(
                success=False,
                error="Improvement generation returned empty result",
            )
    except Exception as e:
        logger.error(
            "reflection_agent.generate_improvements failed", error=str(e), exc_info=True
        )
        return GenerateImprovementsResponse(success=False, error=str(e))


@router.get("/lessons-learned", response_model=LessonsLearnedResponse)
@must_stay_async("FastAPI/ASGI route handler")
async def get_lessons_learned(
    authorization: str = Header(None),
    _: bool = Depends(verify_api_key),
    agent=Depends(get_reflection_agent),
):
    """Get accumulated lessons learned from reflection sessions."""
    try:
        lessons = agent.get_lessons_learned()
        return LessonsLearnedResponse(
            success=True,
            lessons=lessons,
            count=len(lessons),
        )
    except Exception as e:
        logger.error(
            "reflection_agent.get_lessons_learned failed", error=str(e), exc_info=True
        )
        return LessonsLearnedResponse(success=False, error=str(e))


@router.delete("/lessons-learned")
@must_stay_async("FastAPI/ASGI route handler")
async def clear_lessons_learned(
    authorization: str = Header(None),
    _: bool = Depends(verify_api_key),
    agent=Depends(get_reflection_agent),
):
    """Clear accumulated lessons learned."""
    try:
        agent.clear_lessons()
        logger.info("reflection_agent.lessons_cleared")
        return {"success": True, "message": "Lessons cleared"}
    except Exception as e:
        logger.error(
            "reflection_agent.clear_lessons failed", error=str(e), exc_info=True
        )
        return {"success": False, "error": str(e)}


# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "API-OPER-017",
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
        "event-driven",
        "logging",
        "messaging",
        "metrics",
        "operations",
    ],
    "keywords": [
        "agent",
        "analysis",
        "analyze",
        "approaches",
        "clear",
        "compare",
        "extract",
        "failure",
    ],
    "business_value": "/reflect: Execute reflection on execution history /analyze-failure: Deep failure root cause analysis /compare: Compare two approaches /extract-patterns: Extract patterns from examples /generate-improv",
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
