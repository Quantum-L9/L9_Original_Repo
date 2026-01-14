"""
L9 Agents - Architect Agent B
=============================

Challenger and validator architect agent.

Responsibilities:
- Challenge design decisions
- Identify weaknesses and risks
- Propose improvements
- Ensure design quality
"""

from __future__ import annotations

import json
import structlog
from typing import Any, Optional

from agents.base_agent import BaseAgent, AgentConfig, AgentResponse, AgentRole

logger = structlog.get_logger(__name__)


SYSTEM_PROMPT = """You are Architect B, the challenger and validator for L9 system designs.

Your responsibilities:
1. Critically evaluate proposed architectures
2. Identify weaknesses, risks, and edge cases
3. Challenge assumptions and decisions
4. Propose improvements and alternatives
5. Ensure designs are robust and production-ready

When reviewing:
- Question every major design decision
- Look for single points of failure
- Consider security implications
- Evaluate scalability limits
- Check for missing requirements

Be constructive but thorough. Your goal is to make designs better, not to reject them.
Always provide specific, actionable feedback.
"""


class ArchitectAgentB(BaseAgent):
    """
    Challenger architect agent for design validation.
    """

    agent_role = AgentRole.ARCHITECT_CHALLENGER
    agent_name = "architect_b"

    def __init__(
        self,
        agent_id: Optional[str] = None,
        config: Optional[AgentConfig] = None,
    ):
        """Initialize Architect Agent B."""
        super().__init__(agent_id, config)

    def get_system_prompt(self) -> str:
        """Get the system prompt."""
        return self._config.system_prompt_override or SYSTEM_PROMPT

    async def run(
        self,
        task: dict[str, Any],
        context: Optional[dict[str, Any]] = None,
    ) -> AgentResponse:
        """
        Execute design challenge task.

        Args:
            task: Task with 'design' and 'requirements'
            context: Optional context

        Returns:
            AgentResponse with critique
        """
        design = task.get("design", {})
        requirements = task.get("requirements", "")
        focus_areas = task.get("focus_areas", [])

        prompt = f"""Critically evaluate this architecture design:

Design:
{json.dumps(design, indent=2)}

Original Requirements:
{requirements}

Focus Areas:
{json.dumps(focus_areas, indent=2) if focus_areas else "All aspects"}

Provide thorough critique as JSON:
{{
    "overall_score": 0.0 to 1.0,
    "verdict": "approve|request_changes|reject",
    "requirement_analysis": {{
        "met": ["..."],
        "not_met": ["..."],
        "unclear": ["..."]
    }},
    "strengths": ["..."],
    "weaknesses": [
        {{
            "area": "...",
            "severity": "critical|major|minor",
            "description": "...",
            "impact": "...",
            "suggestion": "..."
        }}
    ],
    "risks": [
        {{
            "risk": "...",
            "likelihood": "high|medium|low",
            "impact": "high|medium|low",
            "mitigation": "..."
        }}
    ],
    "missing_elements": ["..."],
    "questions": ["..."],
    "improvement_priorities": [
        {{"priority": 1, "change": "...", "reason": "..."}}
    ],
    "consensus": true/false,
    "reasoning": "..."
}}
"""

        if context:
            prompt += f"\n\nAdditional context:\n{json.dumps(context, indent=2)}"

        messages = [self.format_user_message(prompt)]
        response = await self.call_llm(messages, json_mode=True)

        # Add to conversation history
        self.add_message(messages[0])
        if response.success:
            self.add_message(self.format_assistant_message(response.content))

        return response

    async def challenge_decision(
        self,
        decision: str,
        rationale: str,
        alternatives_considered: list[str],
    ) -> dict[str, Any]:
        """
        Challenge a specific design decision.

        Args:
            decision: The decision made
            rationale: Why it was made
            alternatives_considered: What else was considered

        Returns:
            Challenge analysis
        """
        prompt = f"""Challenge this design decision:

Decision: {decision}

Stated Rationale: {rationale}

Alternatives Considered: {json.dumps(alternatives_considered, indent=2)}

Analyze and respond:
{{
    "challenge_valid": true/false,
    "concerns": [
        {{"concern": "...", "severity": "...", "counter_argument": "..."}}
    ],
    "overlooked_alternatives": [
        {{"alternative": "...", "potential_benefits": ["..."], "why_consider": "..."}}
    ],
    "assumptions_to_verify": ["..."],
    "conditions_for_approval": ["..."],
    "reasoning": "..."
}}
"""

        return await self.call_llm_json(prompt)

    async def validate_interface(
        self,
        interface: dict[str, Any],
        consumers: list[str],
    ) -> dict[str, Any]:
        """
        Validate an interface design.

        Args:
            interface: Interface specification
            consumers: Who will consume this interface

        Returns:
            Validation result
        """
        prompt = f"""Validate this interface design:

Interface:
{json.dumps(interface, indent=2)}

Consumers:
{json.dumps(consumers, indent=2)}

Evaluate:
{{
    "valid": true/false,
    "completeness_score": 0.0 to 1.0,
    "issues": [
        {{"type": "...", "description": "...", "fix": "..."}}
    ],
    "missing_methods": ["..."],
    "error_handling_gaps": ["..."],
    "versioning_concerns": ["..."],
    "documentation_needs": ["..."],
    "recommendations": ["..."]
}}
"""

        return await self.call_llm_json(prompt)

    async def stress_test_design(
        self,
        design: dict[str, Any],
        scenarios: list[str],
    ) -> dict[str, Any]:
        """
        Stress test a design against scenarios.

        Args:
            design: Design to test
            scenarios: Stress scenarios

        Returns:
            Stress test results
        """
        prompt = f"""Stress test this design against the given scenarios:

Design:
{json.dumps(design, indent=2)}

Stress Scenarios:
{json.dumps(scenarios, indent=2)}

For each scenario, evaluate:
{{
    "scenario_results": [
        {{
            "scenario": "...",
            "survives": true/false,
            "failure_points": ["..."],
            "degradation_path": "...",
            "recovery_strategy": "...",
            "improvements_needed": ["..."]
        }}
    ],
    "overall_resilience_score": 0.0 to 1.0,
    "critical_improvements": ["..."],
    "design_limits": ["..."]
}}
"""

        return await self.call_llm_json(prompt)

    async def security_review(
        self,
        design: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Perform security-focused design review.

        Args:
            design: Design to review

        Returns:
            Security review results
        """
        prompt = f"""Perform a security review of this design:

Design:
{json.dumps(design, indent=2)}

Evaluate for:
{{
    "security_score": 0.0 to 1.0,
    "vulnerabilities": [
        {{
            "type": "...",
            "component": "...",
            "severity": "critical|high|medium|low",
            "description": "...",
            "attack_vector": "...",
            "remediation": "..."
        }}
    ],
    "authentication_assessment": "...",
    "authorization_assessment": "...",
    "data_protection_assessment": "...",
    "network_security_assessment": "...",
    "compliance_gaps": ["..."],
    "security_recommendations": ["..."],
    "threat_model_summary": "..."
}}
"""

        return await self.call_llm_json(prompt)
