"""
L9 Agents - Architect Agent A
=============================

Primary system architect agent.

Responsibilities:
- Design system architecture
- Define component structure
- Specify interfaces and contracts
- Make technology decisions
"""

from __future__ import annotations

import json
import structlog
from typing import Any, Optional

from agents.base_agent import BaseAgent, AgentConfig, AgentResponse, AgentRole

logger = structlog.get_logger(__name__)


SYSTEM_PROMPT = """You are Architect A, the primary system designer for L9.

Your responsibilities:
1. Design comprehensive system architectures
2. Define clear component boundaries and responsibilities
3. Specify interfaces and contracts between components
4. Make informed technology decisions with rationale
5. Consider scalability, reliability, and maintainability

When designing:
- Think in terms of modules, services, and their interactions
- Define clear data flows and communication patterns
- Consider failure modes and recovery strategies
- Document assumptions and constraints

Output structured designs that can be implemented by the coding team.
Always explain your reasoning and trade-offs considered.
"""


class ArchitectAgentA(BaseAgent):
    """
    Primary architect agent for system design.
    """

    agent_role = AgentRole.ARCHITECT_PRIMARY
    agent_name = "architect_a"

    def __init__(
        self,
        agent_id: Optional[str] = None,
        config: Optional[AgentConfig] = None,
    ):
        """Initialize Architect Agent A."""
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
        Execute architecture design task.

        Args:
            task: Task with 'requirements' and optional 'constraints'
            context: Optional context

        Returns:
            AgentResponse with architecture design
        """
        requirements = task.get("requirements", "")
        constraints = task.get("constraints", [])
        existing_systems = task.get("existing_systems", [])

        prompt = f"""Design a system architecture for the following requirements:

Requirements:
{requirements}

Constraints:
{json.dumps(constraints, indent=2) if constraints else "None specified"}

Existing systems to integrate with:
{json.dumps(existing_systems, indent=2) if existing_systems else "None - greenfield project"}

Provide your design as JSON with this structure:
{{
    "architecture_name": "...",
    "summary": "...",
    "components": [
        {{
            "name": "...",
            "type": "service|module|database|cache|queue|gateway",
            "responsibility": "...",
            "interfaces": [
                {{"name": "...", "type": "sync|async|event", "protocol": "..."}}
            ],
            "dependencies": ["..."],
            "technology": "..."
        }}
    ],
    "data_flows": [
        {{"from": "...", "to": "...", "data": "...", "protocol": "..."}}
    ],
    "infrastructure": {{
        "deployment": "...",
        "scaling_strategy": "...",
        "persistence": "..."
    }},
    "considerations": {{
        "scalability": "...",
        "reliability": "...",
        "security": "...",
        "observability": "..."
    }},
    "risks": ["..."],
    "assumptions": ["..."],
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

    async def design_component(
        self,
        component_name: str,
        requirements: str,
        interfaces: list[str],
    ) -> dict[str, Any]:
        """
        Design a specific component.

        Args:
            component_name: Name of the component
            requirements: Component requirements
            interfaces: Required interfaces

        Returns:
            Component design
        """
        prompt = f"""Design the {component_name} component with these requirements:

Requirements:
{requirements}

Required Interfaces:
{json.dumps(interfaces, indent=2)}

Provide detailed component design as JSON:
{{
    "name": "{component_name}",
    "internal_structure": {{
        "modules": [
            {{"name": "...", "responsibility": "...", "dependencies": ["..."]}}
        ],
        "data_structures": ["..."],
        "algorithms": ["..."]
    }},
    "interfaces": [
        {{
            "name": "...",
            "type": "...",
            "methods": [
                {{"name": "...", "parameters": [...], "returns": "...", "description": "..."}}
            ]
        }}
    ],
    "error_handling": {{
        "strategies": ["..."],
        "recovery": ["..."]
    }},
    "testing_strategy": "...",
    "reasoning": "..."
}}
"""

        return await self.call_llm_json(prompt)

    async def review_design(
        self,
        design: dict[str, Any],
        requirements: str,
    ) -> dict[str, Any]:
        """
        Review an existing design.

        Args:
            design: Design to review
            requirements: Original requirements

        Returns:
            Review findings
        """
        prompt = f"""Review this architecture design against the requirements:

Design:
{json.dumps(design, indent=2)}

Original Requirements:
{requirements}

Evaluate and provide:
{{
    "overall_assessment": "...",
    "requirements_coverage": {{
        "met": ["..."],
        "partially_met": ["..."],
        "unmet": ["..."]
    }},
    "strengths": ["..."],
    "concerns": [
        {{"area": "...", "issue": "...", "suggestion": "..."}}
    ],
    "missing_elements": ["..."],
    "improvement_suggestions": ["..."],
    "risk_assessment": "..."
}}
"""

        return await self.call_llm_json(prompt)

    async def propose_alternatives(
        self,
        current_design: dict[str, Any],
        issue: str,
    ) -> list[dict[str, Any]]:
        """
        Propose alternative approaches.

        Args:
            current_design: Current design
            issue: Issue to address

        Returns:
            List of alternative approaches
        """
        prompt = f"""Given this design and issue, propose alternative approaches:

Current Design:
{json.dumps(current_design, indent=2)}

Issue to Address:
{issue}

Propose 2-3 alternative approaches:
{{
    "alternatives": [
        {{
            "name": "...",
            "description": "...",
            "changes_required": ["..."],
            "pros": ["..."],
            "cons": ["..."],
            "effort_estimate": "low|medium|high",
            "risk_level": "low|medium|high"
        }}
    ],
    "recommendation": "...",
    "reasoning": "..."
}}
"""

        result = await self.call_llm_json(prompt)
        return result.get("alternatives", [])
