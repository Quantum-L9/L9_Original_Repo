"""
L9 IR Engine - Deliberation Cell
================================

2-agent collaboration cell for IR refinement.

Implements a produce-critique-revise loop:
1. Agent A produces initial IR or revision
2. Agent B critiques and suggests improvements
3. Iterate until convergence or max rounds
"""

from __future__ import annotations

# ============================================================================
__dora_meta__ = {
    "component_name": "Deliberation Cell",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2025-12-09T01:02:49Z",
    "updated_at": "2026-01-07T13:35:57Z",
    "layer": "intelligence",
    "domain": "ir_compilation",
    "module_name": "deliberation_cell",
    "type": "dataclass",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": ["OpenAI API"],
        "memory_layers": ["semantic_memory"],
        "imported_by": ["ir_engine.__init__", "orchestration.unified_controller"],
    },
}
# ============================================================================

import json
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

import structlog
from openai import AsyncOpenAI

from ir_engine.ir_schema import (
    ActionNode,
    ActionType,
    ConstraintNode,
    ConstraintType,
    IntentNode,
    IntentType,
    IRGraph,
    IRStatus,
    NodePriority,
)
from ir_engine.ir_validator import IRValidator
from ir_engine.semantic_compiler import SemanticCompiler

logger = structlog.get_logger(__name__)


@dataclass
class DeliberationRound:
    """Record of a single deliberation round."""

    round_number: int
    producer_output: dict[str, Any]
    critique: dict[str, Any]
    revisions_made: list[str]
    consensus_reached: bool
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class DeliberationResult:
    """Result of deliberation process."""

    session_id: UUID
    final_graph: IRGraph
    rounds: list[DeliberationRound]
    consensus_reached: bool
    total_rounds: int
    improvements_made: list[str]
    final_score: float
    duration_ms: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "session_id": str(self.session_id),
            "graph_id": str(self.final_graph.graph_id),
            "consensus_reached": self.consensus_reached,
            "total_rounds": self.total_rounds,
            "improvements_made": self.improvements_made,
            "final_score": self.final_score,
            "duration_ms": self.duration_ms,
        }


PRODUCER_PROMPT = """You are IR Producer Agent. Your role is to create or improve IR representations.

Current IR State:
{current_ir}

Previous Critique (if any):
{critique}

Task: {task}

Generate improved IR with:
1. Clear intents extracted from the task
2. Explicit and implicit constraints identified
3. Concrete actions to fulfill intents
4. Dependencies between actions

Return JSON:
{{
    "intents": [
        {{"type": "...", "description": "...", "target": "...", "parameters": {{}}, "priority": "medium", "confidence": 0.9}}
    ],
    "constraints": [
        {{"type": "explicit|implicit|hidden", "description": "...", "applies_to": ["intent desc"], "priority": "medium"}}
    ],
    "actions": [
        {{"type": "code_write|code_modify|...", "description": "...", "target": "...", "parameters": {{}}, "depends_on": []}}
    ],
    "reasoning": "..."
}}
"""

CRITIC_PROMPT = """You are IR Critic Agent. Your role is to critique and improve IR representations.

Current IR:
{current_ir}

Original Task:
{task}

Analyze the IR for:
1. Completeness - are all intents captured?
2. Constraints - are there hidden or false constraints?
3. Actions - are they sufficient and correctly ordered?
4. Dependencies - are they correct and complete?

Return JSON:
{{
    "score": 0.0 to 1.0,
    "issues": [
        {{"severity": "critical|major|minor", "description": "...", "suggestion": "..."}}
    ],
    "missing_intents": ["..."],
    "false_constraints": ["..."],
    "suggested_actions": ["..."],
    "consensus": true/false,
    "reasoning": "..."
}}
"""


class DeliberationCell:
    """
    2-agent deliberation cell for IR refinement.

    Uses a Producer-Critic pattern:
    - Producer creates/revises IR
    - Critic evaluates and suggests improvements
    - Iterate until consensus or max rounds
    """

    def __init__(
        self,
        api_key: str | None = None,
        model: str = "gpt-4o",
        max_rounds: int = 5,
        consensus_threshold: float = 0.85,
    ):
        """
        Initialize the deliberation cell.

        Args:
            api_key: OpenAI API key
            model: LLM model to use
            max_rounds: Maximum deliberation rounds
            consensus_threshold: Score threshold for consensus
        """
        self._client: AsyncOpenAI | None = None
        self._api_key = api_key
        self._model = model
        self._max_rounds = max_rounds
        self._consensus_threshold = consensus_threshold

        self._compiler = SemanticCompiler(api_key=api_key, model=model)
        self._validator = IRValidator()

        logger.info(
            f"DeliberationCell initialized "
            f"(max_rounds={max_rounds}, threshold={consensus_threshold})"
        )

    def _ensure_client(self) -> AsyncOpenAI:
        """Ensure OpenAI client is initialized."""
        if self._client is None:
            self._client = AsyncOpenAI(api_key=self._api_key)
        return self._client

    # ==========================================================================
    # Main Deliberation
    # ==========================================================================

    async def deliberate(
        self,
        task: str,
        initial_graph: IRGraph | None = None,
        context: dict[str, Any] | None = None,
    ) -> DeliberationResult:
        """
        Run deliberation process on a task.

        Args:
            task: Task description
            initial_graph: Optional starting IR graph
            context: Additional context

        Returns:
            DeliberationResult with final graph
        """
        session_id = uuid4()
        start_time = datetime.now(timezone.utc)

        logger.info(f"Starting deliberation session {session_id}")

        # Initialize graph
        if initial_graph:
            current_graph = initial_graph
        else:
            current_graph = await self._compiler.compile(task, context)

        rounds: list[DeliberationRound] = []
        improvements: list[str] = []
        consensus_reached = False
        last_score = 0.0

        for round_num in range(1, self._max_rounds + 1):
            logger.info(f"Deliberation round {round_num}/{self._max_rounds}")

            # Get critique from Critic agent
            critique = await self._run_critic(current_graph, task)
            last_score = critique.get("score", 0.0)

            # Check for consensus
            if (
                critique.get("consensus", False)
                or last_score >= self._consensus_threshold
            ):
                consensus_reached = True
                rounds.append(
                    DeliberationRound(
                        round_number=round_num,
                        producer_output={},
                        critique=critique,
                        revisions_made=[],
                        consensus_reached=True,
                    )
                )
                logger.info(
                    f"Consensus reached at round {round_num} (score={last_score:.2f})"
                )
                break

            # Get revisions from Producer agent
            producer_output = await self._run_producer(current_graph, task, critique)

            # Apply revisions
            revisions = self._apply_revisions(current_graph, producer_output)
            improvements.extend(revisions)

            rounds.append(
                DeliberationRound(
                    round_number=round_num,
                    producer_output=producer_output,
                    critique=critique,
                    revisions_made=revisions,
                    consensus_reached=False,
                )
            )

        # Validate final graph
        validation = self._validator.validate(current_graph)
        if validation.valid:
            current_graph.set_status(IRStatus.VALIDATED)

        duration_ms = int((datetime.now(timezone.utc) - start_time).total_seconds() * 1000)

        result = DeliberationResult(
            session_id=session_id,
            final_graph=current_graph,
            rounds=rounds,
            consensus_reached=consensus_reached,
            total_rounds=len(rounds),
            improvements_made=improvements,
            final_score=last_score,
            duration_ms=duration_ms,
        )

        logger.info(
            f"Deliberation complete: {len(rounds)} rounds, "
            f"consensus={consensus_reached}, score={last_score:.2f}"
        )

        return result

    async def _run_producer(
        self,
        graph: IRGraph,
        task: str,
        critique: dict[str, Any],
    ) -> dict[str, Any]:
        """Run the Producer agent to create/revise IR."""
        client = self._ensure_client()

        # Format current IR
        from ir_engine.ir_generator import IRGenerator

        generator = IRGenerator(include_metadata=False)
        current_ir = generator.to_json(graph)

        prompt = PRODUCER_PROMPT.format(
            current_ir=current_ir,
            critique=json.dumps(critique, indent=2),
            task=task,
        )

        try:
            response = await client.chat.completions.create(
                model=self._model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are IR Producer Agent. Return only valid JSON.",
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=0.4,
                response_format={"type": "json_object"},
            )

            content = response.choices[0].message.content or "{}"
            return json.loads(content)

        except Exception as e:
            logger.error(f"Producer agent failed: {e}")
            return {
                "intents": [],
                "constraints": [],
                "actions": [],
                "reasoning": str(e),
            }

    async def _run_critic(
        self,
        graph: IRGraph,
        task: str,
    ) -> dict[str, Any]:
        """Run the Critic agent to evaluate IR."""
        client = self._ensure_client()

        # Format current IR
        from ir_engine.ir_generator import IRGenerator

        generator = IRGenerator(include_metadata=False)
        current_ir = generator.to_json(graph)

        prompt = CRITIC_PROMPT.format(
            current_ir=current_ir,
            task=task,
        )

        try:
            response = await client.chat.completions.create(
                model=self._model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are IR Critic Agent. Return only valid JSON.",
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=0.3,
                response_format={"type": "json_object"},
            )

            content = response.choices[0].message.content or "{}"
            return json.loads(content)

        except Exception as e:
            logger.error(f"Critic agent failed: {e}")
            return {"score": 0.5, "issues": [], "consensus": False, "reasoning": str(e)}

    def _apply_revisions(
        self,
        graph: IRGraph,
        producer_output: dict[str, Any],
    ) -> list[str]:
        """Apply producer revisions to the graph."""
        revisions: list[str] = []

        # Add new intents
        for intent_data in producer_output.get("intents", []):
            # Check if similar intent exists
            desc = intent_data.get("description", "")
            existing = any(
                i.description.lower() == desc.lower() for i in graph.intents.values()
            )

            if not existing and desc:
                intent = IntentNode(
                    intent_type=self._parse_intent_type(
                        intent_data.get("type", "execute")
                    ),
                    description=desc,
                    target=intent_data.get("target", "unknown"),
                    parameters=intent_data.get("parameters", {}),
                    priority=self._parse_priority(
                        intent_data.get("priority", "medium")
                    ),
                    confidence=float(intent_data.get("confidence", 0.8)),
                )
                graph.add_intent(intent)
                revisions.append(f"Added intent: {desc[:50]}")

        # Add new constraints
        for constraint_data in producer_output.get("constraints", []):
            desc = constraint_data.get("description", "")
            existing = any(
                c.description.lower() == desc.lower()
                for c in graph.constraints.values()
            )

            if not existing and desc:
                constraint = ConstraintNode(
                    constraint_type=self._parse_constraint_type(
                        constraint_data.get("type", "explicit")
                    ),
                    description=desc,
                    priority=self._parse_priority(
                        constraint_data.get("priority", "medium")
                    ),
                )
                graph.add_constraint(constraint)
                revisions.append(f"Added constraint: {desc[:50]}")

        # Add new actions
        for action_data in producer_output.get("actions", []):
            desc = action_data.get("description", "")
            existing = any(
                a.description.lower() == desc.lower() for a in graph.actions.values()
            )

            if not existing and desc:
                action = ActionNode(
                    action_type=self._parse_action_type(
                        action_data.get("type", "code_write")
                    ),
                    description=desc,
                    target=action_data.get("target", "unknown"),
                    parameters=action_data.get("parameters", {}),
                    priority=self._parse_priority(
                        action_data.get("priority", "medium")
                    ),
                )
                graph.add_action(action)
                revisions.append(f"Added action: {desc[:50]}")

        return revisions

    # ==========================================================================
    # Type Parsers
    # ==========================================================================

    def _parse_intent_type(self, value: str) -> IntentType:
        mapping = {
            "create": IntentType.CREATE,
            "modify": IntentType.MODIFY,
            "delete": IntentType.DELETE,
            "query": IntentType.QUERY,
            "analyze": IntentType.ANALYZE,
            "transform": IntentType.TRANSFORM,
            "validate": IntentType.VALIDATE,
            "execute": IntentType.EXECUTE,
        }
        return mapping.get(value.lower(), IntentType.EXECUTE)

    def _parse_constraint_type(self, value: str) -> ConstraintType:
        mapping = {
            "explicit": ConstraintType.EXPLICIT,
            "implicit": ConstraintType.IMPLICIT,
            "hidden": ConstraintType.HIDDEN,
            "false": ConstraintType.FALSE,
            "system": ConstraintType.SYSTEM,
        }
        return mapping.get(value.lower(), ConstraintType.EXPLICIT)

    def _parse_action_type(self, value: str) -> ActionType:
        mapping = {
            "code_write": ActionType.CODE_WRITE,
            "code_read": ActionType.CODE_READ,
            "code_modify": ActionType.CODE_MODIFY,
            "file_create": ActionType.FILE_CREATE,
            "file_delete": ActionType.FILE_DELETE,
            "api_call": ActionType.API_CALL,
            "reasoning": ActionType.REASONING,
            "validation": ActionType.VALIDATION,
            "simulation": ActionType.SIMULATION,
        }
        return mapping.get(value.lower(), ActionType.CODE_WRITE)

    def _parse_priority(self, value: str) -> NodePriority:
        mapping = {
            "critical": NodePriority.CRITICAL,
            "high": NodePriority.HIGH,
            "medium": NodePriority.MEDIUM,
            "low": NodePriority.LOW,
        }
        return mapping.get(value.lower(), NodePriority.MEDIUM)

    # ==========================================================================
    # Utility Methods
    # ==========================================================================

    async def quick_refine(
        self,
        graph: IRGraph,
        focus: str = "completeness",
    ) -> IRGraph:
        """
        Quick single-round refinement.

        Args:
            graph: Graph to refine
            focus: Focus area (completeness, constraints, actions)

        Returns:
            Refined graph
        """
        critique = await self._run_critic(graph, f"Focus on {focus}")

        if critique.get("score", 0) < self._consensus_threshold:
            task = f"Improve IR focusing on {focus}"
            producer_output = await self._run_producer(graph, task, critique)
            self._apply_revisions(graph, producer_output)

        return graph


# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "IR_-INTE-005",
    "governance_level": "high",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": [
        "api",
        "async",
        "dataclass",
        "intelligence",
        "ir-compilation",
        "llm",
        "logging",
        "messaging",
        "serialization",
    ],
    "keywords": [
        "agent",
        "cell",
        "deliberate",
        "deliberation",
        "quick",
        "refine",
        "round",
    ],
    "business_value": "1. Agent A produces initial IR or revision 2. Agent B critiques and suggests improvements 3. Iterate until convergence or max rounds",
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
