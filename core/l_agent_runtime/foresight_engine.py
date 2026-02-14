"""
L9 L Agent Runtime - Foresight Engine
======================================
Implements the Foresight Engine pattern for anticipatory agent behavior.

The foresight loop:
Observe → Predict → Decide → Act → Reflect → Improve

Enables agents to:
- Generate candidate actions from context
- Simulate outcomes before acting
- Score confidence for each prediction
- Execute only if confidence >= threshold

Observe cycle (periodic Observe):
- Periodic Observe stage: gather context (optional checklist file, e.g. OBSERVE_CHECKLIST.md).
- Decision framing: "What is the single highest-leverage task that has the
  highest ROI and biggest impact saving the most time for my user?"
- run_observe_cycle() returns either a ForesightDecision or FORESIGHT_OK ack.

Version: 1.0.0
Author: Manus AI
Created: 2025-12-20
"""

from __future__ import annotations

import os

# ============================================================================
__dora_meta__ = {
    "component_name": "Foresight Engine",
    "module_version": "1.1.0",
    "created_by": "Igor Beylin",
    "created_at": "2026-01-25T17:47:23Z",
    "updated_at": "2026-01-31T22:21:48Z",
    "layer": "foundation",
    "domain": "data_models",
    "module_name": "foresight_engine",
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

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC
from enum import Enum
from pathlib import Path

import structlog

logger = structlog.get_logger(__name__)

# Decision prompt for observe cycle / highest-leverage mode. Drives candidate
# generation and selection toward ROI and time-saved for the user.
HIGHEST_LEVERAGE_QUESTION = (
    "What is the single highest-leverage task I can perform next that will "
    "have the highest ROI and biggest impact saving the most time for my user?"
)


class DecisionMode(Enum):
    """Decision modes for the foresight engine."""

    EXECUTE = "execute"  # Execute if confidence >= threshold
    PROPOSE = "propose"  # Always propose, never execute
    ESCALATE = "escalate"  # Escalate for human review


@dataclass
class CandidateAction:
    """A candidate action with predicted outcome."""

    action: dict
    confidence: float
    expected_outcome: str
    reasoning: str
    novelty_factor: float = 0.5
    alignment_score: float = 0.5
    risk_level: float = 0.0
    # Observe cycle / leverage: higher = better ROI, more time saved for user
    leverage_score: float = 0.0
    estimated_time_saved_minutes: float | None = None
    roi_estimate: float | None = None


# Ack sent when observe cycle finds nothing above threshold (suppress delivery).
FORESIGHT_OK = "FORESIGHT_OK"


@dataclass
class ForesightCycleResult:
    """Result of a periodic Observe cycle (Observe → Decide → Act or ack)."""

    ack: str | None = None  # FORESIGHT_OK when nothing meets the bar
    decision: ForesightDecision | None = None  # set when something to do


@dataclass
class ForesightDecision:
    """Result of foresight decision-making."""

    mode: DecisionMode
    action: dict | None
    confidence: float
    candidates: list[CandidateAction]
    reason: str


def _sort_candidates_by_leverage_then_confidence(
    evaluated: list[CandidateAction],
) -> list[CandidateAction]:
    """Sort by leverage_score desc, then confidence desc. Used in observe cycle / ROI mode."""
    return sorted(
        evaluated,
        key=lambda x: (
            -(x.leverage_score if x.leverage_score else 0),
            -(x.confidence),
        ),
    )


class ForesightEngine:
    """Implements the Foresight Engine pattern."""

    def __init__(
        self,
        state_manager,
        memory_manager,
        action_registry,
        candidate_generator: Callable | None = None,
        outcome_simulator: Callable | None = None,
    ):
        """
        Initialize foresight engine.

        Args:
            state_manager: Agent state manager
            memory_manager: Memory substrate
            action_registry: Action registry for execution
            candidate_generator: Optional custom candidate generator
            outcome_simulator: Optional custom outcome simulator
        """
        self.state = state_manager
        self.memory = memory_manager
        self.registry = action_registry
        self._candidate_generator = candidate_generator
        self._outcome_simulator = outcome_simulator

    @property
    def confidence_threshold(self) -> float:
        """Get current confidence threshold from state."""
        return self.state.confidence_threshold

    def observe(
        self,
        context_source: dict | None = None,
        observe_checklist_path: str | None = None,
        use_leverage_question: bool = True,
    ) -> dict:
        """
        Observe stage: gather context for the foresight loop (periodic Observe).

        Optionally reads a checklist file (e.g. OBSERVE_CHECKLIST.md) and
        injects the highest-leverage decision question so candidate generation
        can focus on ROI and time-saved for the user.

        Args:
            context_source: Initial context (workspace, inbox, calendar, etc.)
            observe_checklist_path: Path to checklist file (e.g. "OBSERVE_CHECKLIST.md")
            use_leverage_question: If True, set context["foresight_question"]

        Returns:
            Enriched context dict for generate_candidates / decide_and_act
        """
        from datetime import datetime

        ctx = dict(context_source or {})
        ctx.setdefault("observe_timestamp", datetime.now(UTC).isoformat())
        ctx.setdefault("mode", "observe_cycle")

        if observe_checklist_path:
            path = Path(observe_checklist_path)
            if path.exists():
                try:
                    ctx["checklist_content"] = path.read_text()
                    ctx["checklist_path"] = str(path)
                except OSError as e:
                    logger.warning(
                        "foresight_observe_checklist_read_failed",
                        path=observe_checklist_path,
                        error=str(e),
                    )
            else:
                ctx["checklist_content"] = ""
                ctx["checklist_path"] = str(path)

        if use_leverage_question:
            ctx["foresight_question"] = HIGHEST_LEVERAGE_QUESTION

        return ctx

    def run_observe_cycle(
        self,
        context_source: dict | None = None,
        observe_checklist_path: str | None = None,
        min_leverage_to_act: float = 0.0,
        min_confidence_to_act: float | None = None,
    ) -> ForesightCycleResult:
        """
        Run one periodic Observe cycle: Observe → (Predict → Decide) → Act or ack.

        Triggers the Observe stage (with optional checklist file), then runs
        decide_and_act with the highest-leverage question. If no candidates
        or best candidate is below thresholds, returns FORESIGHT_OK so the
        caller can suppress delivery.

        Args:
            context_source: Input for observe()
            observe_checklist_path: e.g. "OBSERVE_CHECKLIST.md"
            min_leverage_to_act: Only execute/propose if best leverage >= this
            min_confidence_to_act: Override confidence threshold for this run

        Returns:
            ForesightCycleResult with either decision or ack=FORESIGHT_OK
        """
        context = self.observe(
            context_source=context_source,
            observe_checklist_path=observe_checklist_path,
            use_leverage_question=True,
        )
        decision = self.decide_and_act(context)

        if decision.mode == DecisionMode.ESCALATE and not decision.candidates:
            return ForesightCycleResult(ack=FORESIGHT_OK)

        best = decision.candidates[0] if decision.candidates else None
        if not best:
            return ForesightCycleResult(ack=FORESIGHT_OK)

        threshold = (
            min_confidence_to_act
            if min_confidence_to_act is not None
            else self.confidence_threshold
        )
        if best.confidence < threshold:
            return ForesightCycleResult(ack=FORESIGHT_OK)
        if min_leverage_to_act > 0 and (best.leverage_score or 0) < min_leverage_to_act:
            return ForesightCycleResult(ack=FORESIGHT_OK)

        return ForesightCycleResult(decision=decision)

    def decide_and_act(self, context: dict) -> ForesightDecision:
        """
        Main foresight loop: Observe → Predict → Decide → Act.

        Args:
            context: Current context and state

        Returns:
            ForesightDecision object
        """
        # Step 1: Generate candidate actions
        candidates = self.generate_candidates(context)

        if not candidates:
            return ForesightDecision(
                mode=DecisionMode.ESCALATE,
                action=None,
                confidence=0.0,
                candidates=[],
                reason="no_candidates_generated",
            )

        # Step 2: Evaluate and score each candidate
        evaluated = self.evaluate_candidates(context, candidates)

        # Step 3: Select best candidate
        best = evaluated[0] if evaluated else None

        if not best:
            return ForesightDecision(
                mode=DecisionMode.ESCALATE,
                action=None,
                confidence=0.0,
                candidates=evaluated,
                reason="no_viable_candidates",
            )

        # Step 4: Check confidence threshold (C-CONF-001)
        if best.confidence >= self.confidence_threshold:
            # Execute autonomously
            self.execute_action(best.action, best.confidence)
            return ForesightDecision(
                mode=DecisionMode.EXECUTE,
                action=best.action,
                confidence=best.confidence,
                candidates=evaluated,
                reason="confidence_above_threshold",
            )
        # Propose for approval
        return ForesightDecision(
            mode=DecisionMode.PROPOSE,
            action=best.action,
            confidence=best.confidence,
            candidates=evaluated,
            reason=f"confidence_below_threshold ({best.confidence:.2f} < {self.confidence_threshold})",
        )

    def generate_candidates(self, context: dict) -> list[dict]:
        """
        Generate candidate actions from context.

        Args:
            context: Current context

        Returns:
            List of candidate actions
        """
        if self._candidate_generator:
            return self._candidate_generator(context)

        # Default: empty list (override with custom generator)
        logger.warning("No candidate generator configured")
        return []

    def evaluate_candidates(
        self, context: dict, candidates: list[dict]
    ) -> list[CandidateAction]:
        """
        Evaluate and score each candidate.

        Args:
            context: Current context
            candidates: List of candidate actions

        Returns:
            List of CandidateAction objects, sorted by confidence (descending)
        """
        # DTB: Enrich context with causal chain analysis (feature-flagged)
        causal_factors: list[str] = []
        if os.getenv("L9_ENABLE_DTB", "false").lower() == "true":
            try:
                import asyncio

                from domain_tensor_bridge.causal_reasoner import CausalReasoner

                reasoner = CausalReasoner()
                causal_ctx = {
                    "causal_factors": [
                        c.get("action_type", c.get("name", str(c))) for c in candidates
                    ],
                }
                # Run the async causal logic in a sync context
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # Already inside an event loop — schedule as task
                    import concurrent.futures

                    with concurrent.futures.ThreadPoolExecutor() as pool:
                        result = pool.submit(
                            asyncio.run, reasoner.apply_causal_logic(causal_ctx)
                        ).result(timeout=5)
                else:
                    result = asyncio.run(reasoner.apply_causal_logic(causal_ctx))
                causal_factors = result.intervention_points
                logger.info(
                    "foresight.dtb.causal_analysis",
                    chain_length=len(result.causal_chain),
                    interventions=causal_factors,
                    confidence=result.causal_confidence,
                )
            except ImportError:
                pass  # DTB not installed
            except Exception as e:
                logger.debug("foresight.dtb.causal_failed", error=str(e))

        evaluated = []

        for action in candidates:
            # Simulate outcome and calculate confidence
            confidence = self.simulate_action(context, action)

            # DTB: Boost confidence for actions identified as causal intervention points.
            # Boost scales with the action's importance_score (from ImportanceManager)
            # rather than a flat 10%.  Range: 5% (low importance) to 25% (high importance).
            action_name = action.get("action_type", action.get("name", ""))
            if causal_factors and action_name in causal_factors:
                importance = action.get(
                    "importance_score", action.get("leverage_score", 0.5)
                )
                boost_pct = 0.05 + 0.20 * importance  # 5%-25% based on importance
                confidence = min(1.0, confidence * (1.0 + boost_pct))

            # Create candidate action object (include leverage/ROI when present)
            candidate = CandidateAction(
                action=action,
                confidence=confidence,
                expected_outcome=action.get("expected_outcome", "unknown"),
                reasoning=action.get("reasoning", ""),
                novelty_factor=action.get("novelty_factor", 0.5),
                alignment_score=action.get("alignment_score", 0.5),
                risk_level=action.get("risk_level", 0.0),
                leverage_score=action.get("leverage_score", 0.0),
                estimated_time_saved_minutes=action.get("estimated_time_saved_minutes"),
                roi_estimate=action.get("roi_estimate"),
            )
            evaluated.append(candidate)

        # Sort: in leverage mode use leverage then confidence; else confidence only
        if any(c.leverage_score for c in evaluated):
            return _sort_candidates_by_leverage_then_confidence(evaluated)
        evaluated.sort(key=lambda x: x.confidence, reverse=True)
        return evaluated

    def simulate_action(self, context: dict, action: dict) -> float:
        """
        Simulate action outcome and calculate confidence.

        Args:
            context: Current context
            action: Action to simulate

        Returns:
            Confidence score (0.0-1.0)
        """
        if self._outcome_simulator:
            return self._outcome_simulator(context, action)

        # Default: return action's confidence or 0.5
        return action.get("confidence", 0.5)

    def execute_action(self, action: dict, confidence: float) -> dict:
        """
        Execute action and record expectation for reflection.

        Args:
            action: Action to execute
            confidence: Confidence score

        Returns:
            Execution result
        """
        # Record expectation BEFORE executing (P-REFLECT-001)
        expectation = {
            "outcome": action.get("expected_outcome", "success"),
            "confidence": confidence,
            "reasoning": action.get("reasoning", ""),
        }

        # Execute via registry
        result = self.registry.execute(action)

        # Record for reflection
        self.state.record_action_outcome(
            {
                "action": action,
                "expectation": expectation,
                "actual_outcome": result.result
                if result.success
                else {"error": result.error},
                "confidence_score": confidence,
                "success": result.success,
                "timestamp": self._get_timestamp(),
            }
        )

        return {
            "success": result.success,
            "result": result.result,
            "error": result.error,
        }

    def _get_timestamp(self) -> str:
        """Get current timestamp."""
        from datetime import datetime

        return datetime.now(UTC).isoformat()


# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "COR-FOUN-220",
    "governance_level": "critical",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": ["auth", "data-models", "dataclass", "engine", "foundation", "logging"],
    "keywords": [
        "act",
        "action",
        "agent",
        "candidate",
        "candidates",
        "confidence",
        "decide",
        "decision",
        "leverage",
        "observe_cycle",
        "observe",
        "ROI",
    ],
    "business_value": "Implements the Foresight Engine pattern for anticipatory agent behavior. Observe cycle: periodic Observe (optional checklist), highest-leverage decision framing, FORESIGHT_OK ack.",
    "last_modified": "2026-01-31T22:21:48Z",
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
