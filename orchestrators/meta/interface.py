"""
L9 Meta Orchestrator - Interface
Version: 1.0.0

Selects best blueprint/design from multiple candidates.
Evaluates architectural proposals and chooses optimal solution.
"""


from enum import Enum
from typing import Any, Protocol

import structlog
from pydantic import BaseModel, Field

from core.decorators import must_stay_async

logger = structlog.get_logger(__name__)


class BlueprintType(str, Enum):
    """Types of blueprints that can be evaluated."""

    ARCHITECTURE = "architecture"
    WORKFLOW = "workflow"
    SCHEMA = "schema"
    PROMPT = "prompt"
    INTEGRATION = "integration"


class EvaluationCriteria(BaseModel):
    """Criteria for evaluating blueprints."""

    name: str = Field(..., description="Criterion name")
    weight: float = Field(..., ge=0.0, le=1.0, description="Weight (0-1)")
    description: str = Field(..., description="What this criterion measures")


class Blueprint(BaseModel):
    """A candidate blueprint/design."""

    id: str = Field(..., description="Unique blueprint ID")
    type: BlueprintType = Field(..., description="Blueprint type")
    name: str = Field(..., description="Blueprint name")
    description: str = Field(..., description="Blueprint description")
    content: dict[str, Any] = Field(..., description="Blueprint content/spec")
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Additional metadata"
    )


class BlueprintScore(BaseModel):
    """Score for a single criterion."""

    criterion: str = Field(..., description="Criterion name")
    score: float = Field(..., ge=0.0, le=1.0, description="Score (0-1)")
    rationale: str = Field(..., description="Why this score")


class BlueprintEvaluation(BaseModel):
    """Complete evaluation of a blueprint."""

    blueprint_id: str = Field(..., description="Blueprint being evaluated")
    scores: list[BlueprintScore] = Field(..., description="Scores per criterion")
    weighted_total: float = Field(..., description="Weighted total score")
    strengths: list[str] = Field(..., description="Key strengths")
    weaknesses: list[str] = Field(..., description="Key weaknesses")
    recommendation: str = Field(..., description="Overall recommendation")


class MetaOrchestratorRequest(BaseModel):
    """Request to meta orchestrator."""

    blueprints: list[Blueprint] = Field(..., description="Candidate blueprints")
    criteria: list[EvaluationCriteria] = Field(..., description="Evaluation criteria")
    context: dict[str, Any] | None = Field(
        default=None, description="Additional context"
    )
    min_score_threshold: float = Field(
        default=0.7, description="Minimum acceptable score"
    )


class MetaOrchestratorResponse(BaseModel):
    """Response from meta orchestrator."""

    selected_blueprint_id: str = Field(..., description="ID of selected blueprint")
    evaluations: list[BlueprintEvaluation] = Field(..., description="All evaluations")
    rationale: str = Field(..., description="Why this blueprint was selected")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Selection confidence")
    alternatives: list[str] = Field(
        default_factory=list, description="Alternative blueprint IDs"
    )


class IMetaOrchestrator(Protocol):
    """Interface for Meta Orchestrator."""

    @must_stay_async("callers use await")
    async def evaluate_blueprints(
        self, request: MetaOrchestratorRequest
    ) -> MetaOrchestratorResponse:
        """Evaluate multiple blueprints and select the best one."""
        ...

    @must_stay_async("callers use await")
    async def compare_blueprints(
        self,
        blueprint_a: Blueprint,
        blueprint_b: Blueprint,
        criteria: list[EvaluationCriteria],
    ) -> dict[str, Any]:
        """Compare two blueprints head-to-head."""
        ...

    @must_stay_async("callers use await")
    async def suggest_improvements(
        self, blueprint: Blueprint, evaluation: BlueprintEvaluation
    ) -> list[str]:
        """Suggest improvements for a blueprint based on evaluation."""
        ...


# Runtime execution trace - updated automatically on every execution
