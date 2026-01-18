"""
L9 Agents - Reflection Agent
============================

Meta-reasoning and self-correction agent.

Responsibilities:
- Analyze execution patterns
- Identify improvements
- Self-correct behaviors
- Extract lessons learned
"""

from __future__ import annotations

# ============================================================================
__dora_meta__ = {
    "component_name": "Reflection Agent",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2025-12-09T01:02:49Z",
    "updated_at": "2026-01-17T23:47:56Z",
    "layer": "intelligence",
    "domain": "agent_execution",
    "module_name": "reflection_agent",
    "type": "agent",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": [],
        "memory_layers": [],
        "imported_by": ["agents.__init__", "api.server", "core.tools.reflection_tools"],
    },
}
# ============================================================================

import json
import structlog
from typing import Any, Optional

from agents.base_agent import BaseAgent, AgentConfig, AgentResponse, AgentRole

logger = structlog.get_logger(__name__)


SYSTEM_PROMPT = """You are the Reflection Agent for L9, responsible for meta-reasoning and self-improvement.

Your responsibilities:
1. Analyze execution history and outcomes
2. Identify patterns in successes and failures
3. Derive lessons and improvements
4. Enable self-correction behaviors
5. Build institutional knowledge

When reflecting:
- Look for root causes, not symptoms
- Identify recurring patterns
- Consider counterfactuals
- Extract generalizable lessons
- Propose concrete improvements

Your insights shape the system's evolution. Be thorough and insightful.
"""


class ReflectionAgent(BaseAgent):
    """
    Meta-reasoning agent for self-improvement.
    """

    agent_role = AgentRole.REFLECTION
    agent_name = "reflection_agent"

    def __init__(
        self,
        agent_id: Optional[str] = None,
        config: Optional[AgentConfig] = None,
    ):
        """Initialize Reflection Agent."""
        super().__init__(agent_id, config)
        self._lessons_learned: list[dict[str, Any]] = []

    def get_system_prompt(self) -> str:
        """Get the system prompt."""
        return self._config.system_prompt_override or SYSTEM_PROMPT

    async def run(
        self,
        task: dict[str, Any],
        context: Optional[dict[str, Any]] = None,
    ) -> AgentResponse:
        """
        Execute reflection task.

        Args:
            task: Task with 'history' and optional 'focus'
            context: Optional context

        Returns:
            AgentResponse with insights
        """
        history = task.get("history", [])
        focus = task.get("focus", "general")
        goals = task.get("goals", [])

        prompt = f"""Reflect on this execution history:

History:
{json.dumps(history, indent=2)}

Focus Area: {focus}
Goals: {json.dumps(goals, indent=2)}

Provide deep reflection:
{{
    "analysis": {{
        "successes": [
            {{"action": "...", "outcome": "...", "success_factors": ["..."]}}
        ],
        "failures": [
            {{"action": "...", "outcome": "...", "root_cause": "...", "could_have_prevented": "..."}}
        ],
        "patterns": [
            {{"pattern": "...", "frequency": "...", "impact": "positive|negative|neutral", "significance": "..."}}
        ]
    }},
    "insights": [
        {{"insight": "...", "evidence": ["..."], "confidence": 0.0 to 1.0, "applicability": "..."}}
    ],
    "lessons_learned": [
        {{"lesson": "...", "context": "...", "application": "...", "priority": "high|medium|low"}}
    ],
    "improvements": [
        {{
            "area": "...",
            "current_state": "...",
            "proposed_state": "...",
            "action_required": "...",
            "expected_impact": "..."
        }}
    ],
    "knowledge_updates": [
        {{"type": "add|update|remove", "key": "...", "value": "...", "reason": "..."}}
    ],
    "meta_observations": ["observations about the reflection process itself"],
    "summary": "..."
}}
"""

        if context:
            prompt += f"\n\nContext:\n{json.dumps(context, indent=2)}"

        messages = [self.format_user_message(prompt)]
        response = await self.call_llm(messages, json_mode=True)

        # Store lessons learned
        if response.success and response.structured_output:
            for lesson in response.structured_output.get("lessons_learned", []):
                self._lessons_learned.append(lesson)

        self.add_message(messages[0])
        if response.success:
            self.add_message(self.format_assistant_message(response.content))

        return response

    async def analyze_failure(
        self,
        failure_context: dict[str, Any],
        error: str,
        stack_trace: Optional[str] = None,
    ) -> dict[str, Any]:
        """
        Analyze a specific failure.

        Args:
            failure_context: Context of failure
            error: Error message
            stack_trace: Optional stack trace

        Returns:
            Failure analysis
        """
        prompt = f"""Analyze this failure deeply:

Context:
{json.dumps(failure_context, indent=2)}

Error: {error}

Stack Trace:
{stack_trace or "Not available"}

Provide:
{{
    "root_cause_analysis": {{
        "immediate_cause": "...",
        "contributing_factors": ["..."],
        "root_cause": "...",
        "chain_of_events": ["..."]
    }},
    "similar_past_failures": ["if this seems like a recurring issue"],
    "prevention_strategies": [
        {{"strategy": "...", "implementation": "...", "effort": "low|medium|high"}}
    ],
    "recovery_actions": ["immediate actions to recover"],
    "detection_improvements": ["how to catch this earlier"],
    "systemic_changes": ["broader changes to prevent similar issues"],
    "lessons": ["key takeaways"]
}}
"""

        return await self.call_llm_json(prompt)

    async def compare_approaches(
        self,
        approach_a: dict[str, Any],
        approach_b: dict[str, Any],
        criteria: list[str],
    ) -> dict[str, Any]:
        """
        Compare two approaches.

        Args:
            approach_a: First approach
            approach_b: Second approach
            criteria: Comparison criteria

        Returns:
            Comparison analysis
        """
        prompt = f"""Compare these two approaches:

Approach A:
{json.dumps(approach_a, indent=2)}

Approach B:
{json.dumps(approach_b, indent=2)}

Criteria:
{json.dumps(criteria, indent=2)}

Provide:
{{
    "comparison": [
        {{
            "criterion": "...",
            "approach_a_score": 0.0 to 1.0,
            "approach_b_score": 0.0 to 1.0,
            "analysis": "..."
        }}
    ],
    "overall_scores": {{
        "approach_a": 0.0 to 1.0,
        "approach_b": 0.0 to 1.0
    }},
    "recommendation": "A|B|hybrid",
    "hybrid_suggestion": "if applicable",
    "key_differentiators": ["..."],
    "context_dependencies": ["when A is better vs when B is better"],
    "reasoning": "..."
}}
"""

        return await self.call_llm_json(prompt)

    async def extract_patterns(
        self,
        examples: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """
        Extract patterns from examples.

        Args:
            examples: List of examples to analyze

        Returns:
            Extracted patterns
        """
        prompt = f"""Extract patterns from these examples:

Examples:
{json.dumps(examples, indent=2)}

Identify:
{{
    "patterns": [
        {{
            "name": "...",
            "description": "...",
            "frequency": "how often it appears",
            "examples": ["which examples show this"],
            "conditions": ["when this pattern applies"],
            "implications": ["what this pattern means"]
        }}
    ],
    "anti_patterns": [
        {{"name": "...", "description": "...", "why_avoid": "..."}}
    ],
    "correlations": ["relationships between patterns"],
    "outliers": ["examples that don't fit patterns"],
    "generalizations": ["broader rules that can be derived"],
    "confidence": 0.0 to 1.0
}}
"""

        return await self.call_llm_json(prompt)

    async def generate_improvements(
        self,
        current_performance: dict[str, Any],
        goals: list[str],
    ) -> dict[str, Any]:
        """
        Generate improvement suggestions.

        Args:
            current_performance: Current metrics
            goals: Improvement goals

        Returns:
            Improvement plan
        """
        prompt = f"""Generate improvements based on current performance:

Current Performance:
{json.dumps(current_performance, indent=2)}

Goals:
{json.dumps(goals, indent=2)}

Provide:
{{
    "gap_analysis": {{
        "current_vs_goal": [
            {{"metric": "...", "current": "...", "goal": "...", "gap": "..."}}
        ]
    }},
    "improvement_plan": [
        {{
            "improvement": "...",
            "target_metric": "...",
            "expected_impact": "...",
            "effort": "low|medium|high",
            "priority": 1 to 10,
            "implementation_steps": ["..."],
            "success_criteria": "..."
        }}
    ],
    "quick_wins": ["low effort, high impact improvements"],
    "strategic_changes": ["high effort, high impact improvements"],
    "risks": ["potential downsides of changes"],
    "measurement_plan": "how to track progress"
}}
"""

        return await self.call_llm_json(prompt)

    def get_lessons_learned(self) -> list[dict[str, Any]]:
        """Get accumulated lessons learned."""
        return self._lessons_learned.copy()

    def clear_lessons(self) -> None:
        """Clear lessons learned."""
        self._lessons_learned.clear()

    # =========================================================================
    # Tool-callable methods (for L-CTO integration)
    # =========================================================================

    async def reflection_agent_reflect(
        self,
        history: list[dict[str, Any]],
        focus: str = "general",
        goals: Optional[list[str]] = None,
    ) -> dict[str, Any]:
        """
        Tool-callable wrapper for reflection task.

        Args:
            history: List of execution events to reflect on
            focus: Focus area (general, failures, patterns)
            goals: Optional goals to evaluate against

        Returns:
            Reflection results with insights and lessons
        """
        task = {
            "history": history,
            "focus": focus,
            "goals": goals or [],
        }
        response = await self.run(task)
        if response.success and response.structured_output:
            return response.structured_output
        return {"error": response.content or "Reflection failed"}

    async def reflection_agent_analyze_failure(
        self,
        failure_context: dict[str, Any],
        error: str,
        stack_trace: Optional[str] = None,
    ) -> dict[str, Any]:
        """
        Tool-callable wrapper for failure analysis.

        Args:
            failure_context: Context of the failure
            error: Error message
            stack_trace: Optional stack trace

        Returns:
            Root cause analysis and recovery strategies
        """
        return await self.analyze_failure(failure_context, error, stack_trace)

    async def reflection_agent_compare_approaches(
        self,
        approach_a: dict[str, Any],
        approach_b: dict[str, Any],
        criteria: list[str],
    ) -> dict[str, Any]:
        """
        Tool-callable wrapper for approach comparison.

        Args:
            approach_a: First approach to compare
            approach_b: Second approach to compare
            criteria: List of comparison criteria

        Returns:
            Comparison with scores and recommendation
        """
        return await self.compare_approaches(approach_a, approach_b, criteria)

    async def reflection_agent_extract_patterns(
        self,
        examples: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """
        Tool-callable wrapper for pattern extraction.

        Args:
            examples: List of examples to analyze

        Returns:
            Extracted patterns, anti-patterns, and generalizations
        """
        return await self.extract_patterns(examples)

    async def reflection_agent_generate_improvements(
        self,
        current_performance: dict[str, Any],
        goals: list[str],
    ) -> dict[str, Any]:
        """
        Tool-callable wrapper for improvement generation.

        Args:
            current_performance: Current performance metrics
            goals: Improvement goals

        Returns:
            Gap analysis and improvement plan
        """
        return await self.generate_improvements(current_performance, goals)


def create_reflection_agent(
    agent_id: Optional[str] = None,
    config: Optional[AgentConfig] = None,
) -> ReflectionAgent:
    """
    Factory function to create a ReflectionAgent instance.

    Args:
        agent_id: Optional agent ID (defaults to reflection_agent)
        config: Optional AgentConfig override

    Returns:
        Configured ReflectionAgent instance
    """
    return ReflectionAgent(
        agent_id=agent_id or "reflection_agent",
        config=config,
    )


__all__ = [
    "ReflectionAgent",
    "create_reflection_agent",
    "SYSTEM_PROMPT",
]

# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "AGE-INTE-002",
    "governance_level": "critical",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": ["agents.base_agent"],
    "tags": ["agent", "agent-execution", "async", "event-driven", "intelligence", "logging", "messaging", "metrics", "serialization", "tracing"],
    "keywords": ["agent", "analyze", "approaches", "clear", "compare", "create", "extract", "failure"],
    "business_value": "Implements ReflectionAgent for reflection agent functionality",
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
