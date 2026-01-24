"""
L9 Meta Orchestrator - Implementation
Version: 1.0.0

Concrete implementation of meta orchestration logic.
"""

# ============================================================================
__dora_meta__ = {
    "component_name": "Implementation",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2025-12-09T01:02:49Z",
    "updated_at": "2026-01-17T23:47:56Z",
    "layer": "intelligence",
    "domain": "orchestration",
    "module_name": "orchestrator",
    "type": "service",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": [],
        "memory_layers": [],
        "imported_by": [],
    },
}
# ============================================================================

from typing import Any, Dict, List, Optional

import structlog

from core.decorators import must_stay_async

from .adapter import BlueprintAdapter
from .interface import (Blueprint, BlueprintEvaluation, BlueprintScore,
                        EvaluationCriteria, IMetaOrchestrator,
                        MetaOrchestratorRequest, MetaOrchestratorResponse)

logger = structlog.get_logger(__name__)


class MetaOrchestrator(IMetaOrchestrator):
    """
    Meta Orchestrator implementation.

    Evaluates multiple blueprint candidates and selects the optimal one
    based on weighted criteria.
    """

    def __init__(self, adapter: BlueprintAdapter):
        """Initialize meta orchestrator."""
        self._adapter = adapter
        logger.info("MetaOrchestrator initialized")

    async def evaluate_blueprints(
        self, request: MetaOrchestratorRequest
    ) -> MetaOrchestratorResponse:
        """Evaluate multiple blueprints and select the best one."""
        from .interface import BlueprintEvaluation

        logger.info(f"Evaluating {len(request.blueprints)} blueprints")

        evaluations: List[BlueprintEvaluation] = []
        for blueprint in request.blueprints:
            scores = await self._adapter.score_blueprint(
                blueprint, request.criteria, request.context
            )

            weighted_total = (
                sum(
                    s.score
                    * next(
                        (c.weight for c in request.criteria if c.name == s.criterion),
                        0.5,
                    )
                    for s in scores
                )
                / len(scores)
                if scores
                else 0.0
            )
            evaluation = BlueprintEvaluation(
                blueprint_id=blueprint.id,
                scores=scores,
                weighted_total=weighted_total,
                strengths=[],
                weaknesses=[],
                recommendation="Evaluation complete",
            )
            evaluations.append(evaluation)

        evaluations.sort(key=lambda e: e.weighted_total, reverse=True)

        best_evaluation = evaluations[0]
        selected_id = best_evaluation.blueprint_id

        if best_evaluation.weighted_total < request.min_score_threshold:
            logger.warning(
                f"Best blueprint score ({best_evaluation.weighted_total:.2f}) "
                f"below threshold ({request.min_score_threshold})"
            )

        rationale = self._generate_selection_rationale(best_evaluation, evaluations)
        alternatives = [
            e.blueprint_id
            for e in evaluations[1:4]
            if e.weighted_total >= request.min_score_threshold
        ]
        confidence = self._calculate_confidence(evaluations)

        response = MetaOrchestratorResponse(
            selected_blueprint_id=selected_id,
            evaluations=evaluations,
            rationale=rationale,
            confidence=confidence,
            alternatives=alternatives,
        )

        logger.info(
            f"Selected blueprint: {selected_id} (score: {best_evaluation.weighted_total:.2f})"
        )
        return response

    async def compare_blueprints(
        self,
        blueprint_a: Blueprint,
        blueprint_b: Blueprint,
        criteria: List[EvaluationCriteria],
    ) -> Dict[str, Any]:
        """Compare two blueprints head-to-head."""
        logger.info(f"Comparing {blueprint_a.id} vs {blueprint_b.id}")

        # Evaluate both blueprints
        scores_a = await self._adapter.score_blueprint(blueprint_a, criteria, None)
        scores_b = await self._adapter.score_blueprint(blueprint_b, criteria, None)

        eval_a = await self._evaluate_blueprint(blueprint_a, criteria, scores_a, None)
        eval_b = await self._evaluate_blueprint(blueprint_b, criteria, scores_b, None)

        winner = (
            blueprint_a.id
            if eval_a.weighted_total > eval_b.weighted_total
            else blueprint_b.id
        )
        margin = abs(eval_a.weighted_total - eval_b.weighted_total)

        return {
            "winner": winner,
            "margin": margin,
            "blueprint_a": {
                "id": blueprint_a.id,
                "score": eval_a.weighted_total,
                "strengths": eval_a.strengths,
                "weaknesses": eval_a.weaknesses,
            },
            "blueprint_b": {
                "id": blueprint_b.id,
                "score": eval_b.weighted_total,
                "strengths": eval_b.strengths,
                "weaknesses": eval_b.weaknesses,
            },
        }

    async def suggest_improvements(
        self, blueprint: Blueprint, evaluation: BlueprintEvaluation
    ) -> List[str]:
        """Suggest improvements based on evaluation."""
        logger.info(f"Generating improvements for {blueprint.id}")
        suggestions = await self._adapter.generate_improvements(blueprint, evaluation)
        return suggestions

    @must_stay_async("callers use await")
    async def _evaluate_blueprint(
        self,
        blueprint: Blueprint,
        criteria: List[EvaluationCriteria],
        scores: List[BlueprintScore],
        context: Optional[Dict[str, Any]] = None,
    ) -> BlueprintEvaluation:
        """Evaluate a single blueprint against all criteria."""
        logger.info(f"Evaluating blueprint: {blueprint.id}")

        total_weight = sum(c.weight for c in criteria)
        weighted_total = (
            sum(
                score.score
                * next((c.weight for c in criteria if c.name == score.criterion), 0.5)
                for score in scores
            )
            / total_weight
            if total_weight > 0
            else 0.0
        )

        strengths = [score.rationale for score in scores if score.score >= 0.8]
        weaknesses = [score.rationale for score in scores if score.score < 0.6]

        if weighted_total >= 0.8:
            recommendation = "Strongly recommended"
        elif weighted_total >= 0.6:
            recommendation = "Recommended with minor improvements"
        else:
            recommendation = "Not recommended without major improvements"

        return BlueprintEvaluation(
            blueprint_id=blueprint.id,
            scores=scores,
            weighted_total=weighted_total,
            strengths=strengths,
            weaknesses=weaknesses,
            recommendation=recommendation,
        )

    def _generate_selection_rationale(
        self, best: BlueprintEvaluation, all_evaluations: List[BlueprintEvaluation]
    ) -> str:
        """Generate rationale for why this blueprint was selected."""
        if len(all_evaluations) == 1:
            return f"Only candidate with score {best.weighted_total:.2f}"

        second_best = all_evaluations[1]
        margin = best.weighted_total - second_best.weighted_total

        rationale = (
            f"Selected with score {best.weighted_total:.2f}, "
            f"{margin:.2f} points ahead of next best candidate. "
            f"Key strengths: {', '.join(best.strengths[:3])}."
        )
        return rationale

    def _calculate_confidence(self, evaluations: List[BlueprintEvaluation]) -> float:
        """Calculate confidence in selection based on score distribution."""
        if len(evaluations) == 1:
            return evaluations[0].weighted_total

        best_score = evaluations[0].weighted_total
        second_best_score = evaluations[1].weighted_total

        gap = best_score - second_best_score
        confidence = min(1.0, best_score + (gap * 0.5))
        return confidence


# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "ORC-INTE-010",
    "governance_level": "high",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": ["core.decorators"],
    "tags": ["async", "intelligence", "logging", "orchestration", "service"],
    "keywords": [
        "blueprints",
        "compare",
        "evaluate",
        "implementation",
        "improvements",
        "meta",
        "orchestrator",
        "suggest",
    ],
    "business_value": "Implements MetaOrchestrator for orchestrator functionality",
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
