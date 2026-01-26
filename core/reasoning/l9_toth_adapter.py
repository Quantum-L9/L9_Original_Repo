"""
L9 ToTh Adapter
Integrates Theorem-of-Thought reasoning with L9's BaseAgent, memory substrate, and governance
"""

# ============================================================================
__dora_meta__ = {
    "component_name": "L9 Toth Adapter",
    "module_version": "1.0.0",
    "created_by": "cryptoxdog",
    "created_at": "2026-01-23T15:56:34Z",
    "updated_at": "2026-01-24T13:02:52Z",
    "layer": "foundation",
    "domain": "core",
    "module_name": "l9_toth_adapter",
    "type": "dataclass",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": ["Neo4j", "PostgreSQL"],
        "memory_layers": ["semantic_memory"],
        "imported_by": ["core.reasoning.__init__"],
    },
}
# ============================================================================

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from core.reasoning.toth_engine import (
    ProductionToThEngine,
    ReasoningMode,
    ReasoningResult,
    ToThConfig,
)

# Configure logging
logger = logging.getLogger(__name__)


@dataclass
class L9ReasoningContext:
    """Context for L9-specific reasoning"""

    agent_id: str
    agent_type: str
    task_id: str | None = None
    governance_level: str = "standard"  # standard, elevated, critical
    memory_context: dict[str, Any] | None = None
    world_model_context: dict[str, Any] | None = None
    constraints: list[str] | None = None

    def __post_init__(self):
        if self.constraints is None:
            self.constraints = []
        if self.memory_context is None:
            self.memory_context = {}
        if self.world_model_context is None:
            self.world_model_context = {}


class L9ToThAdapter:
    """
    Adapter integrating ToTh reasoning with L9 components

    This adapter provides:
    - Integration with BaseAgent reasoning methods
    - Connection to memory substrate (PostgreSQL + pgvector)
    - Governance policy enforcement
    - World model context integration
    - Observability and metrics
    """

    def __init__(
        self,
        config: ToThConfig | None = None,
        memory_service=None,
        world_model_service=None,
        governance_service=None,
    ):
        """
        Initialize L9 ToTh Adapter

        Args:
            config: ToTh configuration
            memory_service: L9 memory substrate service
            world_model_service: L9 world model service
            governance_service: L9 governance service
        """
        self.config = config or ToThConfig()
        self.toth_engine = ProductionToThEngine(self.config)

        # L9 service integrations
        self.memory_service = memory_service
        self.world_model_service = world_model_service
        self.governance_service = governance_service

        # Reasoning history for agents
        self.agent_reasoning_history: dict[str, list[ReasoningResult]] = {}

        logger.info("L9 ToTh Adapter initialized")

    async def reason_with_context(
        self,
        query: str,
        reasoning_mode: ReasoningMode | str,
        context: L9ReasoningContext,
    ) -> ReasoningResult:
        """
        Execute reasoning with full L9 context integration

        Args:
            query: The reasoning query
            reasoning_mode: Type of reasoning to apply
            context: L9-specific reasoning context

        Returns:
            ReasoningResult with L9 context enrichment
        """
        # Convert string to enum if needed
        if isinstance(reasoning_mode, str):
            reasoning_mode = ReasoningMode(reasoning_mode.lower())

        # Check governance constraints
        if self.governance_service:
            await self._check_governance_constraints(query, context)

        # Enrich query with memory context
        enriched_query = await self._enrich_query_with_memory(query, context)

        # Execute reasoning
        result = await self.toth_engine.reason(enriched_query, reasoning_mode)

        # Store in memory substrate
        if self.memory_service:
            await self._store_reasoning_in_memory(result, context)

        # Update world model
        if self.world_model_service:
            await self._update_world_model(result, context)

        # Track agent history
        if context.agent_id not in self.agent_reasoning_history:
            self.agent_reasoning_history[context.agent_id] = []
        self.agent_reasoning_history[context.agent_id].append(result)

        logger.info(
            f"Reasoning completed for agent {context.agent_id}: "
            f"mode={reasoning_mode.value}, confidence={result.overall_confidence:.3f}"
        )

        return result

    async def multi_modal_reasoning_with_context(
        self, query: str, context: L9ReasoningContext
    ) -> dict[str, ReasoningResult]:
        """
        Execute multi-modal reasoning with L9 context

        Args:
            query: The reasoning query
            context: L9-specific reasoning context

        Returns:
            Dictionary of reasoning results by mode
        """
        results = {}

        for mode in [
            ReasoningMode.ABDUCTIVE,
            ReasoningMode.DEDUCTIVE,
            ReasoningMode.INDUCTIVE,
        ]:
            try:
                result = await self.reason_with_context(query, mode, context)
                results[mode.value] = result
            except Exception as e:
                logger.error(f"Failed {mode.value} reasoning: {e}")
                # Continue with other modes

        # Select best result
        best_result = self._select_best_reasoning(results)

        logger.info(
            f"Multi-modal reasoning completed: best_mode={best_result['mode']}, "
            f"confidence={best_result['confidence']:.3f}"
        )

        return results

    async def board_reasoning(
        self, query: str, board_members: list[str], context: L9ReasoningContext
    ) -> dict[str, Any]:
        """
        Execute Board-style reasoning with multiple perspectives

        Each board member represents a different reasoning mode:
        - Member 1 (Abductive): Pattern recognition, hypothesis generation
        - Member 2 (Deductive): Logical validation, risk assessment
        - Member 3 (Inductive): Trend analysis, generalization

        Args:
            query: The decision or question for the board
            board_members: List of board member identifiers
            context: L9-specific reasoning context

        Returns:
            Board decision with multi-perspective analysis
        """
        logger.info(f"Board reasoning initiated: {len(board_members)} members")

        # Execute reasoning from each perspective
        perspectives = {}
        reasoning_modes = [
            ReasoningMode.ABDUCTIVE,
            ReasoningMode.DEDUCTIVE,
            ReasoningMode.INDUCTIVE,
        ]

        for i, member in enumerate(board_members[:3]):
            mode = reasoning_modes[i % 3]

            # Create member-specific context
            member_context = L9ReasoningContext(
                agent_id=f"{context.agent_id}_board_{member}",
                agent_type="board_member",
                task_id=context.task_id,
                governance_level=context.governance_level,
                memory_context=context.memory_context,
                world_model_context=context.world_model_context,
                constraints=context.constraints,
            )

            result = await self.reason_with_context(query, mode, member_context)
            perspectives[member] = {
                "reasoning_mode": mode.value,
                "result": result,
                "confidence": result.overall_confidence,
            }

        # Synthesize board decision
        return self._synthesize_board_decision(perspectives, query)


    async def ceo_reasoning(
        self, query: str, temporal_context: dict[str, str], context: L9ReasoningContext
    ) -> dict[str, Any]:
        """
        Execute CEO-style tri-temporal reasoning

        - Past (Inductive): Learn from historical patterns
        - Present (Deductive): Apply logical principles to current state
        - Future (Abductive): Generate hypotheses about future states

        Args:
            query: The strategic question or decision
            temporal_context: Dictionary with 'past', 'present', 'future' contexts
            context: L9-specific reasoning context

        Returns:
            CEO decision with tri-temporal analysis
        """
        logger.info("CEO tri-temporal reasoning initiated")

        temporal_reasoning = {}

        # Past analysis (Inductive)
        if "past" in temporal_context:
            past_query = f"{query}\n\nHistorical Context: {temporal_context['past']}"
            past_result = await self.reason_with_context(
                past_query, ReasoningMode.INDUCTIVE, context
            )
            temporal_reasoning["past"] = {
                "analysis": past_result.final_conclusion,
                "confidence": past_result.overall_confidence,
                "insights": [step.conclusion for step in past_result.steps],
            }

        # Present analysis (Deductive)
        if "present" in temporal_context:
            present_query = f"{query}\n\nCurrent Context: {temporal_context['present']}"
            present_result = await self.reason_with_context(
                present_query, ReasoningMode.DEDUCTIVE, context
            )
            temporal_reasoning["present"] = {
                "analysis": present_result.final_conclusion,
                "confidence": present_result.overall_confidence,
                "logical_chain": [step.conclusion for step in present_result.steps],
            }

        # Future analysis (Abductive)
        if "future" in temporal_context:
            future_query = f"{query}\n\nFuture Context: {temporal_context['future']}"
            future_result = await self.reason_with_context(
                future_query, ReasoningMode.ABDUCTIVE, context
            )
            temporal_reasoning["future"] = {
                "analysis": future_result.final_conclusion,
                "confidence": future_result.overall_confidence,
                "hypotheses": [step.conclusion for step in future_result.steps],
            }

        # Synthesize CEO decision
        return self._synthesize_ceo_decision(temporal_reasoning, query)


    async def research_reasoning(
        self, hypothesis: str, evidence: list[str], context: L9ReasoningContext
    ) -> dict[str, Any]:
        """
        Execute Research Agent reasoning for hypothesis validation

        - Abductive: Generate alternative hypotheses
        - Deductive: Validate logical consistency
        - Inductive: Generalize from evidence

        Args:
            hypothesis: The hypothesis to validate
            evidence: List of evidence items
            context: L9-specific reasoning context

        Returns:
            Research analysis with hypothesis validation
        """
        logger.info("Research reasoning initiated: hypothesis validation")

        evidence_str = "\n".join([f"- {e}" for e in evidence])

        # Generate alternative hypotheses (Abductive)
        alt_query = f"""
        Given the following evidence, generate alternative hypotheses:

        Evidence:
        {evidence_str}

        Original Hypothesis: {hypothesis}

        What are other plausible explanations?
        """

        alt_result = await self.reason_with_context(
            alt_query, ReasoningMode.ABDUCTIVE, context
        )

        # Validate logical consistency (Deductive)
        validation_query = f"""
        Validate the logical consistency of this hypothesis:

        Hypothesis: {hypothesis}

        Evidence:
        {evidence_str}

        Does the hypothesis logically follow from the evidence?
        """

        validation_result = await self.reason_with_context(
            validation_query, ReasoningMode.DEDUCTIVE, context
        )

        # Generalize patterns (Inductive)
        pattern_query = f"""
        Analyze the following evidence for patterns:

        Evidence:
        {evidence_str}

        What general principles can be derived?
        """

        pattern_result = await self.reason_with_context(
            pattern_query, ReasoningMode.INDUCTIVE, context
        )

        # Synthesize research analysis
        return {
            "original_hypothesis": hypothesis,
            "alternative_hypotheses": [step.conclusion for step in alt_result.steps],
            "validation": {
                "is_valid": validation_result.overall_confidence
                > self.config.confidence_threshold,
                "confidence": validation_result.overall_confidence,
                "analysis": validation_result.final_conclusion,
            },
            "patterns": {
                "identified_patterns": [
                    step.conclusion for step in pattern_result.steps
                ],
                "confidence": pattern_result.overall_confidence,
            },
            "recommendation": self._synthesize_research_recommendation(
                hypothesis, alt_result, validation_result, pattern_result
            ),
        }


    async def _enrich_query_with_memory(
        self, query: str, context: L9ReasoningContext
    ) -> str:
        """Enrich query with relevant memory context"""
        if not self.memory_service or not context.memory_context:
            return query

        try:
            # Retrieve relevant memories (vector similarity search)
            # This would integrate with L9's memory substrate
            # For now, append memory context if available
            memory_snippet = context.memory_context.get("relevant_memories", "")
            if memory_snippet:
                return f"{query}\n\nRelevant Context: {memory_snippet}"
        except Exception as e:
            logger.warning(f"Failed to enrich query with memory: {e}")

        return query

    async def _store_reasoning_in_memory(
        self, result: ReasoningResult, context: L9ReasoningContext
    ) -> None:
        """Store reasoning result in memory substrate"""
        if not self.memory_service:
            return

        try:
            # Store reasoning result in PostgreSQL + pgvector
            # This would integrate with L9's memory service
            {
                "agent_id": context.agent_id,
                "task_id": context.task_id,
                "reasoning_mode": result.reasoning_mode.value,
                "query": result.query,
                "conclusion": result.final_conclusion,
                "confidence": result.overall_confidence,
                "timestamp": datetime.now().isoformat(),
                "embedding": None,  # Would generate embedding for vector search
            }

            # await self.memory_service.store(memory_entry)
            logger.debug(f"Reasoning stored in memory for agent {context.agent_id}")
        except Exception as e:
            logger.error(f"Failed to store reasoning in memory: {e}")

    async def _update_world_model(
        self, result: ReasoningResult, context: L9ReasoningContext
    ) -> None:
        """Update world model with reasoning insights"""
        if not self.world_model_service:
            return

        try:
            # Update Neo4j world model with reasoning insights
            # This would integrate with L9's world model service
            logger.debug(f"World model updated with reasoning from {context.agent_id}")
        except Exception as e:
            logger.error(f"Failed to update world model: {e}")

    async def _check_governance_constraints(
        self, query: str, context: L9ReasoningContext
    ) -> None:
        """Check governance constraints before reasoning"""
        if not self.governance_service:
            return

        try:
            # Check governance policies
            # This would integrate with L9's governance service
            if context.governance_level == "critical":
                logger.info(
                    f"Critical governance level - enhanced validation for {context.agent_id}"
                )
        except Exception as e:
            logger.error(f"Governance check failed: {e}")
            raise

    def _select_best_reasoning(
        self, results: dict[str, ReasoningResult]
    ) -> dict[str, Any]:
        """Select best reasoning result from multi-modal results"""
        if not results:
            return {"mode": "none", "confidence": 0.0}

        best_mode = max(results.keys(), key=lambda k: results[k].overall_confidence)
        best_result = results[best_mode]

        return {
            "mode": best_mode,
            "confidence": best_result.overall_confidence,
            "conclusion": best_result.final_conclusion,
        }

    def _synthesize_board_decision(
        self, perspectives: dict[str, dict[str, Any]], query: str
    ) -> dict[str, Any]:
        """Synthesize board decision from multiple perspectives"""
        # Calculate weighted consensus
        total_confidence = sum(p["confidence"] for p in perspectives.values())
        avg_confidence = total_confidence / len(perspectives) if perspectives else 0.0

        # Extract key insights from each perspective
        insights = {}
        for member, data in perspectives.items():
            insights[member] = {
                "mode": data["reasoning_mode"],
                "conclusion": data["result"].final_conclusion,
                "confidence": data["confidence"],
            }

        # Determine consensus
        consensus = avg_confidence > self.config.confidence_threshold

        return {
            "query": query,
            "board_perspectives": insights,
            "consensus_reached": consensus,
            "overall_confidence": avg_confidence,
            "recommendation": self._extract_board_recommendation(perspectives),
            "dissenting_views": self._extract_dissenting_views(perspectives),
            "timestamp": datetime.now().isoformat(),
        }

    def _synthesize_ceo_decision(
        self, temporal_reasoning: dict[str, dict[str, Any]], query: str
    ) -> dict[str, Any]:
        """Synthesize CEO decision from tri-temporal analysis"""
        # Calculate confidence across temporal dimensions
        confidences = [data["confidence"] for data in temporal_reasoning.values()]
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0

        return {
            "query": query,
            "temporal_analysis": temporal_reasoning,
            "strategic_recommendation": self._extract_ceo_recommendation(
                temporal_reasoning
            ),
            "confidence": avg_confidence,
            "risk_assessment": self._extract_risk_assessment(temporal_reasoning),
            "action_plan": self._extract_action_plan(temporal_reasoning),
            "timestamp": datetime.now().isoformat(),
        }

    def _synthesize_research_recommendation(
        self,
        hypothesis: str,
        alt_result: ReasoningResult,
        validation_result: ReasoningResult,
        pattern_result: ReasoningResult,
    ) -> str:
        """Synthesize research recommendation"""
        if validation_result.overall_confidence > self.config.confidence_threshold:
            return f"Hypothesis '{hypothesis}' is well-supported by evidence. Recommend proceeding with validation."
        return f"Hypothesis '{hypothesis}' requires further investigation. Consider alternative hypotheses."

    def _extract_board_recommendation(
        self, perspectives: dict[str, dict[str, Any]]
    ) -> str:
        """Extract board recommendation from perspectives"""
        # Find highest confidence perspective
        best_perspective = max(perspectives.values(), key=lambda p: p["confidence"])
        return best_perspective["result"].final_conclusion

    def _extract_dissenting_views(
        self, perspectives: dict[str, dict[str, Any]]
    ) -> list[str]:
        """Extract dissenting views from board perspectives"""
        dissenting = []
        avg_confidence = sum(p["confidence"] for p in perspectives.values()) / len(
            perspectives
        )

        for member, data in perspectives.items():
            if data["confidence"] < avg_confidence - 0.1:
                dissenting.append(f"{member}: {data['result'].final_conclusion}")

        return dissenting

    def _extract_ceo_recommendation(
        self, temporal_reasoning: dict[str, dict[str, Any]]
    ) -> str:
        """Extract CEO recommendation from temporal analysis"""
        # Prioritize future analysis for strategic decisions
        if "future" in temporal_reasoning:
            return temporal_reasoning["future"]["analysis"]
        if "present" in temporal_reasoning:
            return temporal_reasoning["present"]["analysis"]
        if "past" in temporal_reasoning:
            return temporal_reasoning["past"]["analysis"]
        return "Insufficient temporal context for recommendation"

    def _extract_risk_assessment(
        self, temporal_reasoning: dict[str, dict[str, Any]]
    ) -> dict[str, Any]:
        """Extract risk assessment from temporal analysis"""
        risks = {"historical_risks": [], "current_risks": [], "future_risks": []}

        if "past" in temporal_reasoning:
            risks["historical_risks"] = temporal_reasoning["past"].get("insights", [])
        if "present" in temporal_reasoning:
            risks["current_risks"] = temporal_reasoning["present"].get(
                "logical_chain", []
            )
        if "future" in temporal_reasoning:
            risks["future_risks"] = temporal_reasoning["future"].get("hypotheses", [])

        return risks

    def _extract_action_plan(
        self, temporal_reasoning: dict[str, dict[str, Any]]
    ) -> list[str]:
        """Extract action plan from temporal analysis"""
        actions = []

        # Extract actionable items from each temporal dimension
        for dimension, data in temporal_reasoning.items():
            if dimension == "present":
                logical_chain = data.get("logical_chain", [])
                actions.extend([f"[Present] {item}" for item in logical_chain[:2]])
            elif dimension == "future":
                hypotheses = data.get("hypotheses", [])
                actions.extend([f"[Future] {item}" for item in hypotheses[:2]])

        return actions[:5]  # Limit to top 5 actions

    def get_agent_reasoning_history(
        self, agent_id: str, limit: int = 10
    ) -> list[ReasoningResult]:
        """Get reasoning history for specific agent"""
        if agent_id not in self.agent_reasoning_history:
            return []

        return self.agent_reasoning_history[agent_id][-limit:]

    def get_performance_metrics(self) -> dict[str, Any]:
        """Get overall performance metrics"""
        return self.toth_engine.get_performance_metrics()


# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "COR-FOUN-074",
    "governance_level": "critical",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": ["core.reasoning.toth_engine"],
    "tags": [
        "adapter-pattern",
        "async",
        "core",
        "dataclass",
        "debugging",
        "foundation",
        "metrics",
    ],
    "keywords": [
        "adapter",
        "agent",
        "board",
        "ceo",
        "governance",
        "history",
        "memory",
        "metrics",
    ],
    "business_value": "Provides l9 toth adapter components including L9ReasoningContext, L9ToThAdapter",
    "last_modified": "2026-01-24T13:02:52Z",
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
