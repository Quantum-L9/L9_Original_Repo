"""
Evaluation Framework

Harvested from: L9-Implementation-Suite-Ready-to-Deploy.md
Purpose: Continuous evaluation, LLM-as-judge scoring, CI/CD integration.
"""

from __future__ import annotations

# ============================================================================
__dora_meta__ = {
    "component_name": "Evaluator",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2026-01-06T15:07:54Z",
    "updated_at": "2026-01-17T23:47:56Z",
    "layer": "foundation",
    "domain": "error_handling",
    "module_name": "evaluator",
    "type": "dataclass",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": [],
        "memory_layers": ["working_memory"],
        "imported_by": ["api.server"],
    },
}
# ============================================================================

import statistics
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

import structlog

if TYPE_CHECKING:
    from memory.substrate_service import MemorySubstrateService

from core.decorators import must_stay_async

logger = structlog.get_logger(__name__)


@dataclass
class EvaluationExample:
    """Single evaluation case"""

    input_text: str
    expected_output: dict[str, Any] | str | None = None
    expected_tools: list[str] | None = None
    task_type: str | None = None
    success_criteria: str | None = None


@dataclass
class EvaluationSet:
    """Collection of evaluation examples"""

    name: str
    examples: list[EvaluationExample]
    description: str = ""


@dataclass
class EvaluationResult:
    """Result of evaluation run"""

    agent_id: str
    eval_set_name: str
    timestamp: str
    version: str
    examples_run: int
    examples_passed: int
    avg_latency_ms: float
    max_latency_ms: float
    min_latency_ms: float
    p95_latency_ms: float
    tool_accuracy: float
    llm_as_judge_score: float
    error_count: int = 0

    @property
    def task_success_rate(self) -> float:
        """Returns the proportion of successfully completed tasks in the evaluation run, representing the agent's success rate."""
        return (
            self.examples_passed / self.examples_run if self.examples_run > 0 else 0.0
        )


class Evaluator:
    """Evaluation service for agent performance"""

    def __init__(
        self,
        substrate_service: MemorySubstrateService,
        llm_service: Any = None,
        agent_service: Any = None,
    ):
        """
        Initializes the Evaluator with services for agent performance assessment within the evaluation framework.
        Args:
            substrate_service: MemorySubstrateService instance managing memory and context storage.
            llm_service: Optional language model service for scoring and judgment.
            agent_service: Optional service managing agent interactions and execution.
        """
        self.substrate = substrate_service
        self.llm = llm_service
        self.agent_service = agent_service
        self.eval_sets: dict[str, EvaluationSet] = {}

    def define_eval_set(
        self,
        name: str,
        examples: list[EvaluationExample],
        description: str = "",
    ) -> None:
        """Define evaluation set"""
        self.eval_sets[name] = EvaluationSet(
            name=name,
            examples=examples,
            description=description,
        )
        logger.info(
            "Defined eval set",
            name=name,
            examples=len(examples),
        )

    @must_stay_async("callers use await")
    async def run_eval(
        self,
        agent_id: str,
        eval_set_name: str,
        version: str = "latest",
    ) -> EvaluationResult:
        """Run agent on eval set"""

        if eval_set_name not in self.eval_sets:
            raise ValueError(f"Eval set not found: {eval_set_name}")

        eval_set = self.eval_sets[eval_set_name]

        latencies = []
        passed = 0
        errors = 0
        tool_accuracy_scores = []
        llm_judge_scores = []

        logger.info(
            "Starting eval",
            agent_id=agent_id,
            eval_set=eval_set_name,
        )

        for i, example in enumerate(eval_set.examples):
            start_time = time.time()

            try:
                # Execute agent
                if self.agent_service:
                    output = await self.agent_service.execute_task(
                        agent_id=agent_id,
                        input_text=example.input_text,
                        timeout=30,
                    )
                else:
                    output = {"text": "Mock output", "tools_called": []}

                latency_ms = (time.time() - start_time) * 1000
                latencies.append(latency_ms)

                # Evaluate tool selection
                if example.expected_tools:
                    tools_used = output.get("tools_called", [])
                    tool_acc = self._compute_tool_accuracy(
                        tools_used,
                        example.expected_tools,
                    )
                    tool_accuracy_scores.append(tool_acc)

                # LLM-as-judge scoring
                judge_score = await self._judge_output(
                    example.input_text,
                    example.expected_output,
                    output,
                )
                llm_judge_scores.append(judge_score)

                if judge_score > 0.7:
                    passed += 1

                if (i + 1) % 10 == 0:
                    logger.info(
                        "Eval progress",
                        completed=i + 1,
                        total=len(eval_set.examples),
                    )

            except Exception as e:
                errors += 1
                logger.error("Eval example error", error=str(e))

        # Compute percentiles
        if latencies:
            latencies_sorted = sorted(latencies)
            p95_idx = int(len(latencies_sorted) * 0.95)
            p95_latency = latencies_sorted[min(p95_idx, len(latencies_sorted) - 1)]
        else:
            p95_latency = 0.0

        result = EvaluationResult(
            agent_id=agent_id,
            eval_set_name=eval_set_name,
            timestamp=datetime.now(UTC).isoformat(),
            version=version,
            examples_run=len(eval_set.examples),
            examples_passed=passed,
            avg_latency_ms=statistics.mean(latencies) if latencies else 0,
            max_latency_ms=max(latencies) if latencies else 0,
            min_latency_ms=min(latencies) if latencies else 0,
            p95_latency_ms=p95_latency,
            tool_accuracy=(
                statistics.mean(tool_accuracy_scores) if tool_accuracy_scores else 1.0
            ),
            llm_as_judge_score=(
                statistics.mean(llm_judge_scores) if llm_judge_scores else 0
            ),
            error_count=errors,
        )

        logger.info(
            "Eval complete",
            success_rate=f"{result.task_success_rate:.1%}",
        )
        return result

    def _compute_tool_accuracy(
        self,
        tools_used: list[str],
        expected_tools: list[str],
    ) -> float:
        """Jaccard similarity: intersection / union"""

        if not expected_tools:
            return 1.0 if not tools_used else 0.0

        intersection = len(set(tools_used) & set(expected_tools))
        union = len(set(tools_used) | set(expected_tools))

        return intersection / union if union > 0 else 0.0

    @must_stay_async("callers use await")
    async def _judge_output(
        self,
        input_text: str,
        expected: dict[str, Any],
        actual: dict[str, Any],
    ) -> float:
        """
        LLM-as-judge: Score output quality 0-1.

        Uses LLM to compare expected vs actual output and provide
        a quality score based on semantic similarity, completeness,
        and correctness.
        """
        if self.llm is None:
            # Fallback: simple heuristic if no LLM configured
            if not actual.get("text"):
                return 0.0
            if expected.get("text") and expected["text"] in str(actual.get("text", "")):
                return 1.0
            return 0.5

        judge_prompt = f"""You are an evaluation judge. Score the agent's output quality from 0.0 to 1.0.

INPUT: {input_text}

EXPECTED OUTPUT: {expected}

ACTUAL OUTPUT: {actual}

Scoring criteria:
- 1.0: Perfect match or semantically equivalent
- 0.8-0.9: Correct with minor differences
- 0.5-0.7: Partially correct
- 0.2-0.4: Some relevant content but mostly wrong
- 0.0-0.1: Completely wrong or no output

Respond with ONLY a single decimal number between 0.0 and 1.0."""

        try:
            response = await self.llm.complete(judge_prompt)
            # Parse score from response
            score_text = response.strip()
            score = float(score_text)
            return max(0.0, min(1.0, score))  # Clamp to [0, 1]

        except (ValueError, AttributeError) as e:
            logger.warning("LLM judge parse error, using fallback", error=str(e))
            return 0.5 if actual.get("text") else 0.0

    @must_stay_async("callers use await")
    async def store_eval_result(self, result: EvaluationResult) -> bool:
        """
        Store evaluation result to PostgreSQL for baseline tracking.

        Creates record in eval_results table for regression detection.
        """
        if not hasattr(self.substrate, "execute_sql"):
            logger.warning("Substrate doesn't support SQL, skipping store")
            return False

        try:
            await self.substrate.execute_sql(
                """
                INSERT INTO eval_results (
                    eval_set_name, agent_id, version, success_rate,
                    avg_latency_ms, tool_accuracy, llm_judge_score, created_at
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, NOW())
                """,
                result.eval_set_name,
                result.agent_id,
                result.version,
                result.task_success_rate,
                result.avg_latency_ms,
                result.tool_accuracy,
                result.llm_as_judge_score,
            )
            logger.info(
                "Stored eval result",
                eval_set=result.eval_set_name,
                agent=result.agent_id,
                success_rate=f"{result.task_success_rate:.1%}",
            )
            return True

        except Exception as e:
            logger.error("Failed to store eval result", error=str(e))
            return False

    @must_stay_async("callers use await")
    async def get_baseline(
        self,
        agent_id: str,
        eval_set_name: str,
        version: str = "latest",
    ) -> EvaluationResult | None:
        """
        Retrieve baseline evaluation result from PostgreSQL.

        Args:
            agent_id: Agent to get baseline for
            eval_set_name: Evaluation set name
            version: Specific version or "latest" for most recent

        Returns:
            EvaluationResult or None if no baseline exists
        """
        if not hasattr(self.substrate, "fetch_one"):
            logger.warning("Substrate doesn't support fetch, no baseline available")
            return None

        try:
            if version == "latest":
                row = await self.substrate.fetch_one(
                    """
                    SELECT eval_set_name, agent_id, version, success_rate,
                           avg_latency_ms, tool_accuracy, llm_judge_score, created_at
                    FROM eval_results
                    WHERE agent_id = $1 AND eval_set_name = $2
                    ORDER BY created_at DESC
                    LIMIT 1
                    """,
                    agent_id,
                    eval_set_name,
                )
            else:
                row = await self.substrate.fetch_one(
                    """
                    SELECT eval_set_name, agent_id, version, success_rate,
                           avg_latency_ms, tool_accuracy, llm_judge_score, created_at
                    FROM eval_results
                    WHERE agent_id = $1 AND eval_set_name = $2 AND version = $3
                    ORDER BY created_at DESC
                    LIMIT 1
                    """,
                    agent_id,
                    eval_set_name,
                    version,
                )

            if not row:
                return None

            return EvaluationResult(
                agent_id=row["agent_id"],
                eval_set_name=row["eval_set_name"],
                timestamp=str(row["created_at"]),
                version=row["version"],
                examples_run=0,  # Not stored, used for delta calculation only
                examples_passed=0,
                avg_latency_ms=row["avg_latency_ms"],
                max_latency_ms=0,
                min_latency_ms=0,
                p95_latency_ms=0,
                tool_accuracy=row["tool_accuracy"],
                llm_as_judge_score=row["llm_judge_score"],
            )

        except Exception as e:
            logger.error("Failed to get baseline", error=str(e))
            return None

    @must_stay_async("callers use await")
    async def compare_to_baseline(
        self,
        current: EvaluationResult,
        baseline_version: str = "latest",
    ) -> dict[str, float]:
        """
        Compare current results to baseline from database.

        Returns deltas for all key metrics. Positive delta = improvement,
        negative delta = regression.
        """
        baseline = await self.get_baseline(
            current.agent_id,
            current.eval_set_name,
            baseline_version,
        )

        if baseline is None:
            logger.info(
                "No baseline found, storing current as baseline",
                agent=current.agent_id,
                eval_set=current.eval_set_name,
            )
            await self.store_eval_result(current)
            return {
                "task_success_rate_delta": 0.0,
                "latency_delta_ms": 0.0,
                "tool_accuracy_delta": 0.0,
                "llm_judge_delta": 0.0,
                "is_first_baseline": True,
            }

        # Calculate deltas (positive = improvement)
        return {
            "task_success_rate_delta": current.task_success_rate
            - baseline.task_success_rate,
            "latency_delta_ms": baseline.avg_latency_ms
            - current.avg_latency_ms,  # Lower is better
            "tool_accuracy_delta": current.tool_accuracy - baseline.tool_accuracy,
            "llm_judge_delta": current.llm_as_judge_score - baseline.llm_as_judge_score,
            "baseline_version": baseline.version,
            "is_first_baseline": False,
        }


class RegressionError(Exception):
    """Raised when eval results regress beyond thresholds"""

    pass


async def ci_eval_gate(
    agent_id: str,
    eval_set_name: str,
    evaluator: Evaluator,
    thresholds: dict[str, float] | None = None,
) -> None:
    """Block PRs that regress eval scores"""

    if thresholds is None:
        thresholds = {
            "task_success_rate": -0.05,
            "latency_ms": 500,
            "tool_accuracy": -0.10,
        }

    # Run current evaluation
    current = await evaluator.run_eval(agent_id, eval_set_name, version="current")

    # Compare to baseline
    delta = await evaluator.compare_to_baseline(current)

    # Check thresholds
    if delta.get("task_success_rate_delta", 0) < thresholds["task_success_rate"]:
        raise RegressionError(
            f"Task success regression: {delta['task_success_rate_delta']:.1%}"
        )

    if delta.get("latency_delta_ms", 0) > thresholds["latency_ms"]:
        raise RegressionError(f"Latency regression: +{delta['latency_delta_ms']}ms")

    logger.info("✓ Eval passed. All deltas within thresholds.")


# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "COR-FOUN-094",
    "governance_level": "critical",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": ["core.decorators", "memory.substrate_service"],
    "tags": [
        "async",
        "dataclass",
        "error-handling",
        "foundation",
        "logging",
        "mocking",
        "testing",
    ],
    "keywords": [
        "baseline",
        "compare",
        "define",
        "eval",
        "evaluation",
        "evaluator",
        "example",
        "gate",
    ],
    "business_value": "Provides evaluator components including EvaluationExample, EvaluationSet, EvaluationResult",
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
