"""
L9 Research Agent API Router
=============================

API endpoints for the unified ResearchAgent:
- /synthesize: Fast multi-perspective synthesis (~10 min)
- /discover: Deep 5-stage research pipeline (hours)
- /generate-spec: Module-Spec-v2.4 YAML generation (~1 min)
- /research-to-code: End-to-end pipeline

Version: 1.0.0
GMP: wire_research_agent_yaml
"""

from __future__ import annotations

# ============================================================================
__dora_meta__ = {
    "component_name": "Research Agent",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2026-01-16T12:13:08Z",
    "updated_at": "2026-01-17T23:47:56Z",
    "layer": "operations",
    "domain": "api_gateway",
    "module_name": "research_agent",
    "type": "router",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [
            "GET /status",
            "POST /synthesize",
            "POST /discover",
            "POST /generate-spec",
            "POST /research-to-code",
        ],
        "datasources": ["Perplexity API"],
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

logger = structlog.get_logger(__name__)

router = APIRouter()

# AUTO-REGISTRATION (Phase 2 Auto-Wiring)
from api.routes.registry import router_registry

router_registry.register(
    router=router,
    prefix="/research/agent",
    tags=["research-agent"],
    display_name="Research Agent",
    dependencies=["research_agent"],
)


# ============================================================================
# Dependency: Get ResearchAgent from app.state
# ============================================================================


def get_research_agent(request: Request):
    """Get ResearchAgent from app.state."""
    agent = getattr(request.app.state, "research_agent", None)
    if agent is None:
        raise HTTPException(
            status_code=503,
            detail="ResearchAgent not initialized. Check PERPLEXITY_API_KEY env var and server logs.",
        )
    return agent


# ============================================================================
# Request/Response Models
# ============================================================================


class SynthesizeRequest(BaseModel):
    """Request model for fast synthesis."""

    topic: str = Field(..., min_length=3, description="Research topic to synthesize")
    context: dict[str, Any] | None = Field(
        default=None, description="Optional additional context"
    )


class SynthesizeResponse(BaseModel):
    """Response model for synthesis result."""

    success: bool = Field(..., description="Whether operation succeeded")
    timestamp: str = Field(..., description="Completion timestamp")
    total_variations: int = Field(..., description="Number of prompt variations used")
    consensus_patterns: dict[str, Any] = Field(
        default_factory=dict, description="Patterns agreed across variations"
    )
    unique_insights: list[str] = Field(
        default_factory=list, description="Novel insights unique to fewer variations"
    )
    recommended_architecture: dict[str, Any] = Field(
        default_factory=dict, description="Recommended architecture"
    )
    implementation_roadmap: list[str] = Field(
        default_factory=list, description="Implementation phases"
    )
    confidence_scores: dict[str, float] = Field(
        default_factory=dict, description="Confidence by category"
    )
    error: str | None = Field(default=None, description="Error message if failed")


class DiscoverRequest(BaseModel):
    """Request model for deep research."""

    topic: str = Field(..., min_length=3, description="Research topic")
    domain: str = Field(default="general", description="Research domain")
    stages: list[str] | None = Field(
        default=None,
        description="Stages to run: landscape, deep_dive, comparative, gaps, hypotheses",
    )


class DiscoverResponse(BaseModel):
    """Response model for discovery result."""

    success: bool = Field(..., description="Whether operation succeeded")
    topic: str = Field(..., description="Research topic")
    domain: str = Field(..., description="Research domain")
    stages_completed: list[str] = Field(
        default_factory=list, description="Stages completed"
    )
    total_sources: int = Field(default=0, description="Total sources analyzed")
    summary: str = Field(default="", description="Research summary")
    hypotheses_count: int = Field(
        default=0, description="Number of hypotheses generated"
    )
    gaps_count: int = Field(default=0, description="Number of gaps identified")
    error: str | None = Field(default=None, description="Error message if failed")


class GenerateSpecRequest(BaseModel):
    """Request model for spec generation."""

    topic: str = Field(..., min_length=3, description="Module topic")
    description: str | None = Field(default=None, description="Module description")
    run_synthesis_first: bool = Field(
        default=True,
        description="Whether to run synthesis before generating spec",
    )


class GenerateSpecResponse(BaseModel):
    """Response model for spec generation."""

    success: bool = Field(..., description="Whether operation succeeded")
    module_id: str = Field(default="", description="Generated module ID")
    output_path: str = Field(default="", description="Path to generated YAML")
    is_valid: bool = Field(default=False, description="Whether spec passed validation")
    validation_errors: list[str] = Field(
        default_factory=list, description="Validation errors"
    )
    error: str | None = Field(default=None, description="Error message if failed")


class ResearchToCodeRequest(BaseModel):
    """Request model for end-to-end pipeline."""

    topic: str = Field(..., min_length=3, description="Research topic")
    mode: str = Field(
        default="fast",
        description="Mode: fast (synthesis only), deep (full discovery), full (both)",
    )
    domain: str = Field(default="general", description="Research domain")


class ResearchToCodeResponse(BaseModel):
    """Response model for end-to-end pipeline."""

    success: bool = Field(..., description="Whether operation succeeded")
    topic: str = Field(..., description="Research topic")
    mode: str = Field(..., description="Mode used")
    has_discovery: bool = Field(default=False, description="Whether discovery ran")
    has_synthesis: bool = Field(default=False, description="Whether synthesis ran")
    has_spec: bool = Field(default=False, description="Whether spec was generated")
    spec_path: str | None = Field(default=None, description="Path to spec if generated")
    error: str | None = Field(default=None, description="Error message if failed")


# ============================================================================
# Endpoints
# ============================================================================


@router.get("/status")
@must_stay_async("FastAPI/ASGI route handler")
async def research_agent_status(
    authorization: str = Header(None),
    _: bool = Depends(verify_api_key),
    agent=Depends(get_research_agent),  # noqa: B008 — FastAPI dependency injection
):
    """Get ResearchAgent status and capabilities."""
    return {
        "status": "ready",
        "agent_id": agent.agent_id,
        "capabilities": [
            "synthesize (fast multi-perspective, ~10 min)",
            "discover (deep 5-stage research, hours)",
            "generate_spec (Module-Spec-v2.4 YAML, ~1 min)",
            "research_to_code (end-to-end pipeline)",
        ],
        "prompt_variations": len(agent.prompt_variations),
        "perplexity_model_fast": "sonar-reasoning",
        "perplexity_model_deep": "sonar-reasoning",
    }


@router.post("/synthesize", response_model=SynthesizeResponse)
async def synthesize(
    request: SynthesizeRequest,
    authorization: str = Header(None),
    _: bool = Depends(verify_api_key),
    agent=Depends(get_research_agent),  # noqa: B008 — FastAPI dependency injection
):
    """
    Fast multi-perspective synthesis (~10 min).

    Runs 5 parallel prompt variations and synthesizes consensus:
    - v1_pragmatic: Implementation-first engineering
    - v2_research: Theory-first academic
    - v3_systems: DevOps/systems integration
    - v4_agents: Autonomous agent integration
    - v5_multimodal: Cross-modality specifics
    """
    try:
        logger.info("research_agent.synthesize", topic=request.topic)

        result = await agent.synthesize(
            topic=request.topic,
            context=request.context,
        )

        return SynthesizeResponse(
            success=True,
            timestamp=result.timestamp,
            total_variations=result.total_variations,
            consensus_patterns=result.consensus_patterns,
            unique_insights=result.unique_insights,
            recommended_architecture=result.recommended_architecture,
            implementation_roadmap=result.implementation_roadmap,
            confidence_scores=result.confidence_scores,
        )
    except Exception as e:
        logger.error("research_agent.synthesize failed", error=str(e), exc_info=True)
        return SynthesizeResponse(
            success=False,
            timestamp="",
            total_variations=0,
            consensus_patterns={},
            unique_insights=[],
            recommended_architecture={},
            implementation_roadmap=[],
            confidence_scores={},
            error=str(e),
        )


@router.post("/discover", response_model=DiscoverResponse)
@must_stay_async("callers use await")
async def discover(
    request: DiscoverRequest,
    authorization: str = Header(None),
    _: bool = Depends(verify_api_key),
    agent=Depends(get_research_agent),  # noqa: B008 — FastAPI dependency injection
):
    """
    Deep 5-stage academic research pipeline (15-25 hours).

    Stages:
    1. landscape: Map research landscape (3-5 hours)
    2. deep_dive: Vertical deep-dives on themes (4-6 hours)
    3. comparative: Compare leading approaches (3-5 hours)
    4. gaps: Identify research gaps (3-4 hours)
    5. hypotheses: Generate testable hypotheses (2-3 hours)
    """
    try:
        logger.info(
            "research_agent.discover",
            topic=request.topic,
            domain=request.domain,
            stages=request.stages,
        )

        result = await agent.discover(
            topic=request.topic,
            domain=request.domain,
            stages=request.stages,
        )

        return DiscoverResponse(
            success=True,
            topic=result.topic,
            domain=result.domain,
            stages_completed=result.stages_completed,
            total_sources=result.total_sources,
            summary=result.summary,
            hypotheses_count=len(result.hypotheses),
            gaps_count=len(result.gaps),
        )
    except Exception as e:
        logger.error("research_agent.discover failed", error=str(e), exc_info=True)
        return DiscoverResponse(
            success=False,
            topic=request.topic,
            domain=request.domain,
            stages_completed=[],
            total_sources=0,
            summary="",
            hypotheses_count=0,
            gaps_count=0,
            error=str(e),
        )


@router.post("/generate-spec", response_model=GenerateSpecResponse)
@must_stay_async("callers use await")
async def generate_spec(
    request: GenerateSpecRequest,
    authorization: str = Header(None),
    _: bool = Depends(verify_api_key),
    agent=Depends(get_research_agent),  # noqa: B008 — FastAPI dependency injection
):
    """
    Generate Module-Spec-v2.4 YAML (~1 min).

    If run_synthesis_first=True (default), runs synthesis first
    to inform the spec generation with research insights.
    """
    try:
        logger.info(
            "research_agent.generate_spec",
            topic=request.topic,
            run_synthesis_first=request.run_synthesis_first,
        )

        synthesis = None
        if request.run_synthesis_first:
            synthesis = await agent.synthesize(topic=request.topic)

        result = await agent.generate_spec(
            synthesis=synthesis,
            topic=request.topic,
            description=request.description,
        )

        return GenerateSpecResponse(
            success=True,
            module_id=result.module_id,
            output_path=str(result.output_path),
            is_valid=result.is_valid,
            validation_errors=result.validation_errors,
        )
    except Exception as e:
        logger.error("research_agent.generate_spec failed", error=str(e), exc_info=True)
        return GenerateSpecResponse(
            success=False,
            module_id="",
            output_path="",
            is_valid=False,
            validation_errors=[],
            error=str(e),
        )


@router.post("/research-to-code", response_model=ResearchToCodeResponse)
@must_stay_async("callers use await")
async def research_to_code(
    request: ResearchToCodeRequest,
    authorization: str = Header(None),
    _: bool = Depends(verify_api_key),
    agent=Depends(get_research_agent),  # noqa: B008 — FastAPI dependency injection
):
    """
    End-to-end research-to-code pipeline.

    Modes:
    - fast: Synthesis only (~10 min)
    - deep: Full discovery + synthesis (hours)
    - full: Both discovery and synthesis (longest)
    """
    try:
        logger.info(
            "research_agent.research_to_code",
            topic=request.topic,
            mode=request.mode,
            domain=request.domain,
        )

        result = await agent.research_to_code(
            topic=request.topic,
            mode=request.mode,
            domain=request.domain,
        )

        return ResearchToCodeResponse(
            success=True,
            topic=result["topic"],
            mode=result["mode"],
            has_discovery="discovery" in result,
            has_synthesis="synthesis" in result,
            has_spec="spec" in result,
            spec_path=result.get("spec", {}).get("output_path"),
        )
    except Exception as e:
        logger.error(
            "research_agent.research_to_code failed", error=str(e), exc_info=True
        )
        return ResearchToCodeResponse(
            success=False,
            topic=request.topic,
            mode=request.mode,
            has_discovery=False,
            has_synthesis=False,
            has_spec=False,
            error=str(e),
        )


# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "API-OPER-022",
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
        "agent",
        "discover",
        "generate",
        "module",
        "pipeline",
        "research",
        "router",
        "spec",
    ],
    "business_value": "/synthesize: Fast multi-perspective synthesis (~10 min) /discover: Deep 5-stage research pipeline (hours) /generate-spec: Module-Spec-v2.4 YAML generation (~1 min) /research-to-code: End-to-end pipeli",
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
