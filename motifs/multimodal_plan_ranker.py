"""
Multimodal Plan Ranker — MMR-002

Rank and reroute plans based on motif coverage, kernel compliance,
and modality success. Combines tensor, symbolic, motif, and governance signals.
"""

# ============================================================================
__dora_meta__ = {
    "component_name": "Multimodal Plan Ranker",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2026-01-26T11:14:45Z",
    "updated_at": "2026-01-31T22:21:54Z",
    "layer": "operations",
    "domain": "motifs",
    "module_name": "multimodal_plan_ranker",
    "type": "dataclass",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": [],
        "memory_layers": [],
        "imported_by": [],
    },
}
# ============================================================================

from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4

import structlog

from core.decorators import must_stay_async

from .motif_feedback_graph import MotifFeedbackGraph

logger = structlog.get_logger(__name__)


@dataclass
class PlanCandidate:
    """A candidate plan to be ranked."""

    plan_id: str = field(default_factory=lambda: str(uuid4()))
    description: str = ""
    modalities: list[str] = field(default_factory=list)
    raw_scores: dict[str, float] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class RankedPlan:
    """A plan after ranking with scores and analysis."""

    plan_id: str = ""
    score: float = 0.0
    reasons: list[str] = field(default_factory=list)
    motif_coverage: float = 0.0
    governance_risk: float = 0.0
    modalities: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


class MultimodalPlanRanker:
    """
    Rank candidate plans using tensor, symbolic, motif, and governance signals.

    Combines multiple reasoning modalities to produce ranked plans with:
    - Composite scores
    - Motif coverage metrics
    - Governance risk assessment
    - Detailed reasoning explanations
    """

    def __init__(
        self,
        motif_graph: MotifFeedbackGraph | None = None,
        tensor_coordinator: Any | None = None,
        symbolic_reasoner: Any | None = None,
        compliance_checker: Any | None = None,
        anomaly_handler: Any | None = None,
        causal_reasoner: Any | None = None,
        analogical_reasoner: Any | None = None,
    ):
        """
        Initialize the multimodal plan ranker.

        Args:
            motif_graph: MotifFeedbackGraph for pattern tracking
            tensor_coordinator: Tensor reasoning coordinator
            symbolic_reasoner: Symbolic reasoning engine
            compliance_checker: Compliance checking service
            anomaly_handler: Anomaly detection handler
            causal_reasoner: Causal reasoning engine
            analogical_reasoner: Analogical reasoning engine
        """
        self.motif_graph = motif_graph or MotifFeedbackGraph()
        self.tensor_coordinator = tensor_coordinator
        self.symbolic_reasoner = symbolic_reasoner
        self.compliance_checker = compliance_checker
        self.anomaly_handler = anomaly_handler
        self.causal_reasoner = causal_reasoner
        self.analogical_reasoner = analogical_reasoner

        self.logger = logger.bind(component="MultimodalPlanRanker")
        self.logger.info("MultimodalPlanRanker initialized")

        # Weights for different scoring components
        self.weights = {
            "tensor": 0.25,
            "symbolic": 0.20,
            "motif": 0.25,
            "governance": 0.20,
            "causal": 0.05,
            "analogical": 0.05,
        }

    @must_stay_async("callers use await")
    async def rank_plans(
        self,
        packet_id: str,
        plans: list[PlanCandidate],
        context: dict[str, Any] | None = None,
    ) -> list[RankedPlan]:
        """
        Rank candidate plans using multimodal signals.

        Args:
            packet_id: ID of the packet these plans are for
            plans: List of candidate plans to rank
            context: Optional additional context

        Returns:
            List of RankedPlan objects sorted by score (highest first)
        """
        context = context or {}
        ranked_plans: list[RankedPlan] = []

        self.logger.info(
            "rank_plans.started",
            packet_id=packet_id,
            plan_count=len(plans),
        )

        for plan in plans:
            try:
                ranked = await self._rank_single_plan(packet_id, plan, context)
                ranked_plans.append(ranked)

                # Record motif event for ranking
                await self.motif_graph.record_event(
                    packet_id=packet_id,
                    motif_type="plan_ranking",
                    features={
                        "plan_id": plan.plan_id,
                        "modalities": plan.modalities,
                        "score": ranked.score,
                    },
                    outcome="ranked",
                    confidence=ranked.score,
                    source_component="MultimodalPlanRanker",
                )

            except Exception as e:
                self.logger.error(
                    "rank_plans.plan_failed",
                    plan_id=plan.plan_id,
                    error=str(e),
                )
                # Create a low-score ranked plan for failed ranking
                ranked_plans.append(
                    RankedPlan(
                        plan_id=plan.plan_id,
                        score=0.0,
                        reasons=[f"Ranking failed: {e!s}"],
                        governance_risk=1.0,
                        modalities=plan.modalities,
                    )
                )

        # Sort by score descending
        ranked_plans.sort(key=lambda p: p.score, reverse=True)

        self.logger.info(
            "rank_plans.completed",
            packet_id=packet_id,
            ranked_count=len(ranked_plans),
            top_score=ranked_plans[0].score if ranked_plans else 0.0,
        )

        return ranked_plans

    @must_stay_async("callers use await")
    async def _rank_single_plan(
        self,
        packet_id: str,
        plan: PlanCandidate,
        context: dict[str, Any],
    ) -> RankedPlan:
        """Rank a single plan candidate."""
        scores: dict[str, float] = {}
        reasons: list[str] = []

        # 1. Tensor score (from raw scores or coordinator)
        scores["tensor"] = plan.raw_scores.get("tensor", 0.5)
        if scores["tensor"] > 0.7:
            reasons.append("Strong tensor alignment")

        # 2. Symbolic score
        scores["symbolic"] = plan.raw_scores.get("symbolic", 0.5)
        if scores["symbolic"] > 0.7:
            reasons.append("Logical consistency verified")

        # 3. Motif coverage
        motif_coverage = await self._calculate_motif_coverage(packet_id, plan)
        scores["motif"] = motif_coverage
        if motif_coverage > 0.6:
            reasons.append(f"Good motif coverage ({motif_coverage:.0%})")

        # 4. Governance risk
        governance_risk = await self._assess_governance_risk(plan)
        scores["governance"] = (
            1.0 - governance_risk
        )  # Invert: lower risk = higher score
        if governance_risk < 0.3:
            reasons.append("Low governance risk")
        elif governance_risk > 0.7:
            reasons.append("⚠️ High governance risk")

        # 5. Causal score
        scores["causal"] = plan.raw_scores.get("causal", 0.5)

        # 6. Analogical score
        scores["analogical"] = plan.raw_scores.get("analogical", 0.5)

        # Calculate weighted score
        total_score = sum(scores[key] * self.weights[key] for key in self.weights)

        return RankedPlan(
            plan_id=plan.plan_id,
            score=total_score,
            reasons=reasons,
            motif_coverage=motif_coverage,
            governance_risk=governance_risk,
            modalities=plan.modalities,
            metadata={
                "component_scores": scores,
                "weights_used": self.weights,
                **plan.metadata,
            },
        )

    async def _calculate_motif_coverage(
        self,
        packet_id: str,
        plan: PlanCandidate,
    ) -> float:
        """Calculate how well the plan covers known motif patterns."""
        # Get trace for this packet
        trace = await self.motif_graph.get_trace_for_packet(packet_id)

        if not trace.events:
            return 0.5  # Neutral if no motif history

        # Calculate coverage based on successful outcomes
        successful = sum(1 for e in trace.events if e.outcome == "success")
        coverage = successful / len(trace.events) if trace.events else 0.5

        return min(1.0, coverage)

    @must_stay_async("callers use await")
    async def _assess_governance_risk(self, plan: PlanCandidate) -> float:
        """Assess governance risk of the plan."""
        risk = 0.0

        # Check for high-risk modalities
        high_risk_modalities = {"code_execution", "external_api", "data_mutation"}
        risk_modalities = set(plan.modalities) & high_risk_modalities
        risk += 0.2 * len(risk_modalities)

        # Check compliance if checker available
        if self.compliance_checker:
            try:
                # Placeholder for compliance check
                pass
            except Exception:
                risk += 0.1

        return min(1.0, risk)


__all__ = ["MultimodalPlanRanker", "PlanCandidate", "RankedPlan"]
# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "MOT-OPER-003",
    "governance_level": "medium",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": [
        "api",
        "async",
        "dataclass",
        "event-driven",
        "logging",
        "metrics",
        "motifs",
        "operations",
        "tracing",
    ],
    "keywords": [
        "candidate",
        "compliance",
        "governance",
        "kernel",
        "motif",
        "multimodal",
        "plan",
        "plans",
    ],
    "business_value": "Provides multimodal plan ranker components including PlanCandidate, RankedPlan, MultimodalPlanRanker",
    "last_modified": "2026-01-31T22:21:54Z",
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
