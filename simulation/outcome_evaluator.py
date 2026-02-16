"""
L9 Simulation - Outcome Evaluator
=================================

Evaluates simulation outcomes against criteria.

Provides:
- Multi-criteria evaluation
- Weighted scoring
- Pass/fail determination
- Detailed feedback
"""

from __future__ import annotations

# ============================================================================
__dora_meta__ = {
    "component_name": "Outcome Evaluator",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2025-12-09T01:02:49Z",
    "updated_at": "2026-01-07T13:35:58Z",
    "layer": "learning",
    "domain": "data_models",
    "module_name": "outcome_evaluator",
    "type": "dataclass",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": [],
        "memory_layers": [],
        "imported_by": ["simulation.__init__"],
    },
}
# ============================================================================

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any, TYPE_CHECKING
from uuid import UUID, uuid4

import structlog


if TYPE_CHECKING:
    from simulation.simulation_engine import SimulationRun

logger = structlog.get_logger(__name__)


class CriterionType(str, Enum):
    """Types of evaluation criteria."""

    SUCCESS_RATE = "success_rate"
    PERFORMANCE = "performance"
    RESOURCE = "resource"
    RELIABILITY = "reliability"
    CUSTOM = "custom"


class EvaluationVerdict(str, Enum):
    """Evaluation verdicts."""

    PASS = "pass"  # noqa: S105 — enum value, not a credential
    CONDITIONAL_PASS = "conditional_pass"  # noqa: S105 — enum value, not a credential
    FAIL = "fail"


@dataclass
class EvaluationCriteria:
    """A single evaluation criterion."""

    name: str
    criterion_type: CriterionType
    threshold: float
    weight: float = 1.0
    comparison: str = "gte"  # gte, lte, eq, gt, lt
    description: str = ""

    def evaluate(self, value: float) -> tuple[bool, float]:
        """
        Evaluate a value against this criterion.

        Returns:
            Tuple of (passed, score)
        """
        if self.comparison == "gte":
            passed = value >= self.threshold
        elif self.comparison == "lte":
            passed = value <= self.threshold
        elif self.comparison == "gt":
            passed = value > self.threshold
        elif self.comparison == "lt":
            passed = value < self.threshold
        elif self.comparison == "eq":
            passed = abs(value - self.threshold) < 0.001
        else:
            passed = value >= self.threshold

        # Calculate score (0-1)
        if self.comparison in ("gte", "gt"):
            score = min(1.0, value / max(self.threshold, 0.001))
        elif self.comparison in ("lte", "lt"):
            if value <= self.threshold:
                score = 1.0
            else:
                score = max(
                    0.0, 1.0 - (value - self.threshold) / max(self.threshold, 0.001)
                )
        else:
            score = 1.0 if passed else 0.0

        return passed, score


@dataclass
class CriterionResult:
    """Result of evaluating a single criterion."""

    criterion: EvaluationCriteria
    value: float
    passed: bool
    score: float
    weighted_score: float
    feedback: str = ""


@dataclass
class EvaluationResult:
    """Complete evaluation result."""

    evaluation_id: UUID = field(default_factory=uuid4)
    run_id: UUID = field(default_factory=uuid4)
    verdict: EvaluationVerdict = EvaluationVerdict.FAIL
    overall_score: float = 0.0
    criterion_results: list[CriterionResult] = field(default_factory=list)
    passed_criteria: int = 0
    failed_criteria: int = 0
    recommendations: list[str] = field(default_factory=list)
    evaluated_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def to_dict(self) -> dict[str, Any]:
        return {
            "evaluation_id": str(self.evaluation_id),
            "run_id": str(self.run_id),
            "verdict": self.verdict.value,
            "overall_score": self.overall_score,
            "passed_criteria": self.passed_criteria,
            "failed_criteria": self.failed_criteria,
            "criteria_results": [
                {
                    "criterion": cr.criterion.name,
                    "value": cr.value,
                    "passed": cr.passed,
                    "score": cr.score,
                }
                for cr in self.criterion_results
            ],
            "recommendations": self.recommendations,
        }


class OutcomeEvaluator:
    """
    Evaluates simulation outcomes.

    Supports:
    - Multi-criteria evaluation
    - Weighted scoring
    - Configurable pass thresholds
    - Detailed feedback generation
    """

    def __init__(
        self,
        pass_threshold: float = 0.7,
        conditional_threshold: float = 0.5,
    ):
        """
        Initialize the evaluator.

        Args:
            pass_threshold: Score threshold for PASS
            conditional_threshold: Score threshold for CONDITIONAL_PASS
        """
        self._pass_threshold = pass_threshold
        self._conditional_threshold = conditional_threshold
        self._default_criteria = self._create_default_criteria()

        logger.info("OutcomeEvaluator initialized")

    def _create_default_criteria(self) -> list[EvaluationCriteria]:
        """Create default evaluation criteria."""
        return [
            EvaluationCriteria(
                name="Success Rate",
                criterion_type=CriterionType.SUCCESS_RATE,
                threshold=0.8,
                weight=2.0,
                comparison="gte",
                description="Percentage of steps that completed successfully",
            ),
            EvaluationCriteria(
                name="No Critical Failures",
                criterion_type=CriterionType.RELIABILITY,
                threshold=0,
                weight=3.0,
                comparison="lte",
                description="Number of critical failures",
            ),
            EvaluationCriteria(
                name="Parallelism Factor",
                criterion_type=CriterionType.PERFORMANCE,
                threshold=1.2,
                weight=0.5,
                comparison="gte",
                description="Degree of parallelism achieved",
            ),
            EvaluationCriteria(
                name="Bottleneck Count",
                criterion_type=CriterionType.PERFORMANCE,
                threshold=3,
                weight=0.5,
                comparison="lte",
                description="Number of bottlenecks identified",
            ),
        ]

    # ==========================================================================
    # Main Evaluation
    # ==========================================================================

    def evaluate(
        self,
        run: SimulationRun,
        criteria: list[EvaluationCriteria] | None = None,
    ) -> EvaluationResult:
        """
        Evaluate a simulation run.

        Args:
            run: Simulation run to evaluate
            criteria: Optional custom criteria

        Returns:
            EvaluationResult
        """
        criteria = criteria or self._default_criteria

        result = EvaluationResult(run_id=run.run_id)

        # Evaluate each criterion
        total_weight = 0.0
        weighted_sum = 0.0

        for criterion in criteria:
            value = self._extract_value(run, criterion)
            passed, score = criterion.evaluate(value)
            weighted_score = score * criterion.weight

            cr = CriterionResult(
                criterion=criterion,
                value=value,
                passed=passed,
                score=score,
                weighted_score=weighted_score,
                feedback=self._generate_feedback(criterion, value, passed),
            )

            result.criterion_results.append(cr)

            if passed:
                result.passed_criteria += 1
            else:
                result.failed_criteria += 1

            total_weight += criterion.weight
            weighted_sum += weighted_score

        # Calculate overall score
        if total_weight > 0:
            result.overall_score = weighted_sum / total_weight

        # Determine verdict
        result.verdict = self._determine_verdict(result)

        # Generate recommendations
        result.recommendations = self._generate_recommendations(result, run)

        logger.info(
            f"Evaluation complete: verdict={result.verdict.value}, "
            f"score={result.overall_score:.2f}"
        )

        return result

    def _extract_value(
        self,
        run: SimulationRun,
        criterion: EvaluationCriteria,
    ) -> float:
        """Extract the relevant value for a criterion from the run."""
        metrics = run.metrics

        if criterion.name == "Success Rate":
            if metrics.total_steps == 0:
                return 1.0
            return metrics.successful_steps / metrics.total_steps

        if criterion.name == "No Critical Failures":
            # Count critical failures
            critical = sum(
                1
                for f in run.failure_modes
                if "critical" in f.lower() or "error" in f.lower()
            )
            return float(critical)

        if criterion.name == "Parallelism Factor":
            return metrics.parallelism_factor

        if criterion.name == "Bottleneck Count":
            return float(len(metrics.bottlenecks))

        if criterion.name == "Duration":
            return float(metrics.total_duration_ms)

        # Default to simulation score
        return run.score

    def _determine_verdict(self, result: EvaluationResult) -> EvaluationVerdict:
        """Determine the evaluation verdict."""
        # Check for any critical failures
        for cr in result.criterion_results:
            if cr.criterion.weight >= 2.0 and not cr.passed:
                # High-weight criterion failed
                if result.overall_score < self._conditional_threshold:
                    return EvaluationVerdict.FAIL

        if result.overall_score >= self._pass_threshold:
            return EvaluationVerdict.PASS
        if result.overall_score >= self._conditional_threshold:
            return EvaluationVerdict.CONDITIONAL_PASS
        return EvaluationVerdict.FAIL

    def _generate_feedback(
        self,
        criterion: EvaluationCriteria,
        value: float,
        passed: bool,
    ) -> str:
        """Generate feedback for a criterion result."""
        if passed:
            return (
                f"{criterion.name}: {value:.2f} meets threshold {criterion.threshold}"
            )
        return f"{criterion.name}: {value:.2f} does not meet threshold {criterion.threshold}"

    def _generate_recommendations(
        self,
        result: EvaluationResult,
        run: SimulationRun,
    ) -> list[str]:
        """Generate recommendations based on evaluation."""
        recommendations = []

        for cr in result.criterion_results:
            if not cr.passed:
                if cr.criterion.criterion_type == CriterionType.SUCCESS_RATE:
                    recommendations.append(
                        "Improve error handling to increase success rate"
                    )
                elif cr.criterion.criterion_type == CriterionType.PERFORMANCE:
                    recommendations.append(
                        f"Address performance issue: {cr.criterion.name}"
                    )
                elif cr.criterion.criterion_type == CriterionType.RELIABILITY:
                    recommendations.append("Add retry logic and fallback mechanisms")

        # Add recommendations based on failure modes
        if run.failure_modes:
            unique_failures = set(run.failure_modes)
            if len(unique_failures) > 3:
                recommendations.append(
                    f"Address {len(unique_failures)} distinct failure modes"
                )

        return recommendations[:5]  # Limit to top 5

    # ==========================================================================
    # Batch Evaluation
    # ==========================================================================

    def evaluate_multiple(
        self,
        runs: list[SimulationRun],
        criteria: list[EvaluationCriteria] | None = None,
    ) -> list[EvaluationResult]:
        """
        Evaluate multiple simulation runs.

        Args:
            runs: List of simulation runs
            criteria: Optional custom criteria

        Returns:
            List of EvaluationResults
        """
        return [self.evaluate(run, criteria) for run in runs]

    def rank_runs(
        self,
        runs: list[SimulationRun],
        criteria: list[EvaluationCriteria] | None = None,
    ) -> list[tuple[SimulationRun, EvaluationResult]]:
        """
        Rank runs by evaluation score.

        Args:
            runs: List of runs to rank
            criteria: Optional custom criteria

        Returns:
            List of (run, result) tuples sorted by score
        """
        results = [(run, self.evaluate(run, criteria)) for run in runs]
        results.sort(key=lambda x: x[1].overall_score, reverse=True)
        return results

    # ==========================================================================
    # Criteria Management
    # ==========================================================================

    def create_criterion(
        self,
        name: str,
        criterion_type: CriterionType,
        threshold: float,
        weight: float = 1.0,
        comparison: str = "gte",
        description: str = "",
    ) -> EvaluationCriteria:
        """Create a new evaluation criterion."""
        return EvaluationCriteria(
            name=name,
            criterion_type=criterion_type,
            threshold=threshold,
            weight=weight,
            comparison=comparison,
            description=description,
        )

    def get_default_criteria(self) -> list[EvaluationCriteria]:
        """Get default evaluation criteria."""
        return self._default_criteria.copy()

    def set_thresholds(
        self,
        pass_threshold: float,
        conditional_threshold: float,
    ) -> None:
        """Update verdict thresholds."""
        self._pass_threshold = pass_threshold
        self._conditional_threshold = conditional_threshold


# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "SIM-LEAR-001",
    "governance_level": "high",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": [
        "batch-processing",
        "data-models",
        "dataclass",
        "learning",
        "logging",
        "metrics",
    ],
    "keywords": [
        "create",
        "criteria",
        "criterion",
        "default",
        "evaluate",
        "evaluation",
        "evaluator",
        "multiple",
    ],
    "business_value": "Multi-criteria evaluation Weighted scoring Pass/fail determination Detailed feedback",
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
