"""
L9 Meta Orchestrator - Interface
Version: 1.0.0

Selects best blueprint/design from multiple candidates.
Evaluates architectural proposals and chooses optimal solution.
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
        "imported_by": [],
    },
}
# ============================================================================

from typing import Protocol, List, Dict, Any, Optional
import structlog
from pydantic import BaseModel, Field
from enum import Enum
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
    content: Dict[str, Any] = Field(..., description="Blueprint content/spec")
    metadata: Dict[str, Any] = Field(
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
    scores: List[BlueprintScore] = Field(..., description="Scores per criterion")
    weighted_total: float = Field(..., description="Weighted total score")
    strengths: List[str] = Field(..., description="Key strengths")
    weaknesses: List[str] = Field(..., description="Key weaknesses")
    recommendation: str = Field(..., description="Overall recommendation")


class MetaOrchestratorRequest(BaseModel):
    """Request to meta orchestrator."""

    blueprints: List[Blueprint] = Field(..., description="Candidate blueprints")
    criteria: List[EvaluationCriteria] = Field(..., description="Evaluation criteria")
    context: Optional[Dict[str, Any]] = Field(
        default=None, description="Additional context"
    )
    min_score_threshold: float = Field(
        default=0.7, description="Minimum acceptable score"
    )


class MetaOrchestratorResponse(BaseModel):
    """Response from meta orchestrator."""

    selected_blueprint_id: str = Field(..., description="ID of selected blueprint")
    evaluations: List[BlueprintEvaluation] = Field(..., description="All evaluations")
    rationale: str = Field(..., description="Why this blueprint was selected")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Selection confidence")
    alternatives: List[str] = Field(
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
        criteria: List[EvaluationCriteria],
    ) -> Dict[str, Any]:
        """Compare two blueprints head-to-head."""
        ...

    @must_stay_async("callers use await")
    async def suggest_improvements(
        self, blueprint: Blueprint, evaluation: BlueprintEvaluation
    ) -> List[str]:
        """Suggest improvements for a blueprint based on evaluation."""
        ...

# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "ORC-INTE-009",
    "governance_level": "high",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": ["core.decorators"],
    "tags": ["async", "data-models", "enum", "intelligence", "logging", "orchestration", "pydantic", "validation"],
    "keywords": ["blueprint", "blueprints", "compare", "criteria", "evaluate", "evaluation", "improvements", "interface"],
    "business_value": "Provides interface components including BlueprintType, EvaluationCriteria, Blueprint",
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
