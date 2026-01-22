"""
L9 IR Engine - Constraint Challenger
====================================

Analyzes constraints to detect:
- False constraints (unnecessary limitations)
- Hidden constraints (undiscovered requirements)
- Implicit constraints (inferred from context)
- Better alternatives

Uses LLM reasoning to challenge and improve constraint sets.
"""

from __future__ import annotations

# ============================================================================
__dora_meta__ = {
    "component_name": "Constraint Challenger",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2025-12-09T01:02:49Z",
    "updated_at": "2026-01-07T13:35:57Z",
    "layer": "intelligence",
    "domain": "ir_compilation",
    "module_name": "constraint_challenger",
    "type": "service",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": ["OpenAI API"],
        "memory_layers": [],
        "imported_by": [
            "ir_engine.__init__",
            "orchestration.orchestrator_kernel",
            "orchestration.unified_controller",
        ],
    },
}
# ============================================================================

import json
from typing import Any, Optional
from uuid import UUID

import structlog
from openai import AsyncOpenAI

from ir_engine.ir_schema import (ConstraintNode, ConstraintType, IRGraph,
                                 IRStatus)

logger = structlog.get_logger(__name__)


CHALLENGE_PROMPT = """You are a constraint analysis expert. Review the constraints and identify issues.

For each constraint, determine:
1. Is this constraint necessary or is it a "false constraint" that limits options unnecessarily?
2. Is the constraint clearly stated (explicit) or hidden/implicit?
3. Are there better alternatives that achieve the same goal?
4. What hidden constraints might be missing?

Current intents:
{intents}

Current constraints:
{constraints}

Current actions:
{actions}

Context:
{context}

Return JSON:
{{
    "challenges": [
        {{
            "constraint_id": "...",
            "verdict": "valid|false|needs_revision",
            "reason": "...",
            "alternative": "..."
        }}
    ],
    "hidden_constraints": [
        {{
            "description": "...",
            "type": "implicit|hidden|system",
            "applies_to": ["intent description"],
            "priority": "medium"
        }}
    ],
    "recommendations": ["..."]
}}
"""


class ChallengeResult:
    """Result of constraint challenge analysis."""

    def __init__(
        self,
        challenged: list[tuple[UUID, str, Optional[str]]],
        invalidated: list[tuple[UUID, str]],
        hidden_found: list[ConstraintNode],
        recommendations: list[str],
    ):
        self.challenged = challenged  # (id, reason, alternative)
        self.invalidated = invalidated  # (id, reason)
        self.hidden_found = hidden_found
        self.recommendations = recommendations

    def to_dict(self) -> dict[str, Any]:
        return {
            "challenged_count": len(self.challenged),
            "invalidated_count": len(self.invalidated),
            "hidden_found_count": len(self.hidden_found),
            "recommendations": self.recommendations,
            "challenged": [
                {"id": str(c[0]), "reason": c[1], "alternative": c[2]}
                for c in self.challenged
            ],
            "invalidated": [
                {"id": str(i[0]), "reason": i[1]} for i in self.invalidated
            ],
        }


class ConstraintChallenger:
    """
    Challenges constraints to identify false, hidden, and improvable constraints.

    Uses LLM reasoning to analyze constraint validity and suggest improvements.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "gpt-4o",
        temperature: float = 0.4,
        auto_apply: bool = False,
    ):
        """
        Initialize the constraint challenger.

        Args:
            api_key: OpenAI API key
            model: LLM model to use
            temperature: Generation temperature
            auto_apply: If True, automatically apply challenges to graph
        """
        self._client: Optional[AsyncOpenAI] = None
        self._api_key = api_key
        self._model = model
        self._temperature = temperature
        self._auto_apply = auto_apply

        logger.info(
            f"ConstraintChallenger initialized (model={model}, auto_apply={auto_apply})"
        )

    def _ensure_client(self) -> AsyncOpenAI:
        """Ensure OpenAI client is initialized."""
        if self._client is None:
            self._client = AsyncOpenAI(api_key=self._api_key)
        return self._client

    # ==========================================================================
    # Main Challenge Flow
    # ==========================================================================

    async def challenge(
        self,
        graph: IRGraph,
        context: Optional[dict[str, Any]] = None,
    ) -> ChallengeResult:
        """
        Challenge constraints in the graph.

        Args:
            graph: IR graph to analyze
            context: Additional context for analysis

        Returns:
            ChallengeResult with findings
        """
        logger.info(f"Challenging constraints in graph {graph.graph_id}")

        # Skip if no constraints
        if not graph.constraints:
            logger.info("No constraints to challenge")
            return ChallengeResult([], [], [], [])

        # Get LLM analysis
        analysis = await self._analyze_constraints(graph, context)

        # Process challenges
        challenged: list[tuple[UUID, str, Optional[str]]] = []
        invalidated: list[tuple[UUID, str]] = []

        for challenge in analysis.get("challenges", []):
            constraint_id = self._parse_constraint_id(
                challenge.get("constraint_id", ""), graph
            )
            if not constraint_id:
                continue

            verdict = challenge.get("verdict", "valid")
            reason = challenge.get("reason", "")
            alternative = challenge.get("alternative")

            if verdict == "false":
                invalidated.append((constraint_id, reason))
                if self._auto_apply:
                    constraint = graph.get_constraint(constraint_id)
                    if constraint:
                        constraint.invalidate(reason)

            elif verdict == "needs_revision":
                challenged.append((constraint_id, reason, alternative))
                if self._auto_apply:
                    constraint = graph.get_constraint(constraint_id)
                    if constraint:
                        constraint.challenge(reason, alternative)

        # Process hidden constraints
        hidden_found: list[ConstraintNode] = []
        for hidden in analysis.get("hidden_constraints", []):
            new_constraint = ConstraintNode(
                constraint_type=self._parse_constraint_type(
                    hidden.get("type", "hidden")
                ),
                description=hidden.get("description", ""),
                priority=self._parse_priority(hidden.get("priority", "medium")),
            )
            hidden_found.append(new_constraint)

            if self._auto_apply:
                graph.add_constraint(new_constraint)

        # Update graph status
        if self._auto_apply and (challenged or invalidated or hidden_found):
            graph.set_status(IRStatus.CHALLENGED)

        result = ChallengeResult(
            challenged=challenged,
            invalidated=invalidated,
            hidden_found=hidden_found,
            recommendations=analysis.get("recommendations", []),
        )

        logger.info(
            f"Challenge complete: {len(challenged)} challenged, "
            f"{len(invalidated)} invalidated, {len(hidden_found)} hidden found"
        )

        return result

    async def _analyze_constraints(
        self,
        graph: IRGraph,
        context: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        """Use LLM to analyze constraints."""
        client = self._ensure_client()

        # Format graph data for prompt
        intents_str = "\n".join(
            [
                f"- {i.intent_type.value}: {i.description} (target: {i.target})"
                for i in graph.intents.values()
            ]
        )

        constraints_str = "\n".join(
            [
                f"- [{c.node_id}] {c.constraint_type.value}: {c.description} (status: {c.status.value})"
                for c in graph.constraints.values()
            ]
        )

        actions_str = "\n".join(
            [
                f"- {a.action_type.value}: {a.description} (target: {a.target})"
                for a in graph.actions.values()
            ]
        )

        prompt = CHALLENGE_PROMPT.format(
            intents=intents_str or "None",
            constraints=constraints_str or "None",
            actions=actions_str or "None",
            context=json.dumps(context or {}, indent=2),
        )

        try:
            response = await client.chat.completions.create(
                model=self._model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a constraint analysis expert. Return only valid JSON.",
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=self._temperature,
                response_format={"type": "json_object"},
            )

            content = response.choices[0].message.content or "{}"
            return json.loads(content)

        except Exception as e:
            logger.error(f"LLM constraint analysis failed: {e}")
            return {"challenges": [], "hidden_constraints": [], "recommendations": []}

    # ==========================================================================
    # Rule-Based Challenges
    # ==========================================================================

    def challenge_rule_based(self, graph: IRGraph) -> ChallengeResult:
        """
        Apply rule-based constraint challenges (no LLM).

        Useful for quick validation without API calls.
        """
        challenged: list[tuple[UUID, str, Optional[str]]] = []
        invalidated: list[tuple[UUID, str]] = []

        for constraint_id, constraint in graph.constraints.items():
            # Check for vague constraints
            if len(constraint.description) < 10:
                challenged.append(
                    (
                        constraint_id,
                        "Constraint description is too vague",
                        "Provide more specific requirements",
                    )
                )

            # Check for orphan constraints
            if not constraint.applies_to:
                challenged.append(
                    (
                        constraint_id,
                        "Constraint does not apply to any intent or action",
                        "Specify which intents/actions this constraint applies to",
                    )
                )

            # Check for low confidence constraints
            if constraint.confidence < 0.5:
                challenged.append(
                    (
                        constraint_id,
                        f"Low confidence constraint ({constraint.confidence:.2f})",
                        "Review and verify this constraint",
                    )
                )

            # Check for conflicting keywords
            desc_lower = constraint.description.lower()
            if "always" in desc_lower and "never" in desc_lower:
                invalidated.append(
                    (
                        constraint_id,
                        "Constraint contains conflicting terms (always + never)",
                    )
                )

        return ChallengeResult(
            challenged=challenged,
            invalidated=invalidated,
            hidden_found=[],
            recommendations=[],
        )

    # ==========================================================================
    # Utility Methods
    # ==========================================================================

    def _parse_constraint_id(self, id_str: str, graph: IRGraph) -> Optional[UUID]:
        """Parse constraint ID string to UUID."""
        try:
            return UUID(id_str)
        except (ValueError, AttributeError):
            # Try to find by partial match
            for cid in graph.constraints:
                if str(cid).startswith(id_str):
                    return cid
            return None

    def _parse_constraint_type(self, value: str) -> ConstraintType:
        """Parse constraint type string."""
        mapping = {
            "explicit": ConstraintType.EXPLICIT,
            "implicit": ConstraintType.IMPLICIT,
            "hidden": ConstraintType.HIDDEN,
            "false": ConstraintType.FALSE,
            "system": ConstraintType.SYSTEM,
        }
        return mapping.get(value.lower(), ConstraintType.HIDDEN)

    def _parse_priority(self, value: str):
        """Parse priority string."""
        from ir_engine.ir_schema import NodePriority

        mapping = {
            "critical": NodePriority.CRITICAL,
            "high": NodePriority.HIGH,
            "medium": NodePriority.MEDIUM,
            "low": NodePriority.LOW,
        }
        return mapping.get(value.lower(), NodePriority.MEDIUM)

    # ==========================================================================
    # Batch Operations
    # ==========================================================================

    async def challenge_multiple(
        self,
        graphs: list[IRGraph],
        context: Optional[dict[str, Any]] = None,
    ) -> dict[UUID, ChallengeResult]:
        """
        Challenge constraints in multiple graphs.

        Args:
            graphs: List of graphs to challenge
            context: Shared context

        Returns:
            Dict mapping graph IDs to results
        """
        results: dict[UUID, ChallengeResult] = {}

        for graph in graphs:
            result = await self.challenge(graph, context)
            results[graph.graph_id] = result

        return results


# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "IR_-INTE-006",
    "governance_level": "high",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": [
        "api",
        "async",
        "batch-processing",
        "intelligence",
        "ir-compilation",
        "llm",
        "logging",
        "messaging",
        "serialization",
        "service",
    ],
    "keywords": [
        "based",
        "challenge",
        "challenger",
        "constraint",
        "constraints",
        "multiple",
        "rule",
    ],
    "business_value": "Provides constraint challenger components including ChallengeResult, ConstraintChallenger",
    "last_modified": "2026-01-07T13:35:57Z",
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
