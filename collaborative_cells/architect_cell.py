"""
L9 Collaborative Cells - Architect Cell
=======================================

Collaborative cell for system architecture design.

Uses 2 architect agents:
- Architect A: Primary designer
- Architect B: Challenger/validator
"""

from __future__ import annotations

import json
import structlog
from typing import Any, Optional

from openai import AsyncOpenAI

from collaborative_cells.base_cell import BaseCell, CellConfig
from core.decorators import must_stay_async

logger = structlog.get_logger(__name__)


ARCHITECT_A_PROMPT = """You are Architect A, the primary system designer.

Task: {task}

Previous critique (if any):
{critique}

Context:
{context}

Design a comprehensive architecture including:
1. System components and their responsibilities
2. Data flow between components
3. Key interfaces and contracts
4. Technology choices with rationale
5. Scalability and reliability considerations

Return JSON:
{{
    "architecture_name": "...",
    "components": [
        {{
            "name": "...",
            "type": "service|module|database|cache|queue",
            "responsibility": "...",
            "interfaces": ["..."],
            "dependencies": ["..."]
        }}
    ],
    "data_flows": [
        {{
            "from": "...",
            "to": "...",
            "data_type": "...",
            "protocol": "..."
        }}
    ],
    "technology_stack": {{
        "language": "...",
        "framework": "...",
        "database": "...",
        "other": ["..."]
    }},
    "considerations": {{
        "scalability": "...",
        "reliability": "...",
        "security": "..."
    }},
    "reasoning": "..."
}}
"""

ARCHITECT_B_PROMPT = """You are Architect B, the challenger and validator.

Proposed Architecture:
{architecture}

Original Task:
{task}

Context:
{context}

Critically evaluate the architecture:
1. Does it meet all requirements?
2. Are there missing components or flows?
3. Are technology choices appropriate?
4. What are potential failure points?
5. What improvements would you suggest?

Return JSON:
{{
    "score": 0.0 to 1.0,
    "strengths": ["..."],
    "weaknesses": ["..."],
    "missing_components": ["..."],
    "suggested_changes": [
        {{
            "component": "...",
            "change": "...",
            "reason": "..."
        }}
    ],
    "failure_points": ["..."],
    "consensus": true/false,
    "reasoning": "..."
}}
"""


class ArchitectCell(BaseCell):
    """
    Collaborative cell for architecture design.

    Coordinates two architect agents to design robust system architectures.
    """

    cell_type = "architect"

    def __init__(self, config: Optional[CellConfig] = None):
        """Initialize the architect cell."""
        super().__init__(config)
        self._client: Optional[AsyncOpenAI] = None

    def _ensure_client(self) -> AsyncOpenAI:
        """Ensure OpenAI client is initialized."""
        if self._client is None:
            self._client = AsyncOpenAI(api_key=self._config.api_key)
        return self._client

    async def _run_producer(
        self,
        task: dict[str, Any],
        context: dict[str, Any],
        previous_critique: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        """Run Architect A to produce architecture design."""
        client = self._ensure_client()

        prompt = ARCHITECT_A_PROMPT.format(
            task=json.dumps(task, indent=2),
            critique=json.dumps(previous_critique, indent=2)
            if previous_critique
            else "None",
            context=json.dumps(context, indent=2),
        )

        try:
            response = await client.chat.completions.create(
                model=self._config.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are Architect A, a senior system designer. Return only valid JSON.",
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=0.4,
                response_format={"type": "json_object"},
            )

            content = response.choices[0].message.content or "{}"
            return json.loads(content)

        except Exception as e:
            logger.error(f"Architect A failed: {e}")
            return {
                "architecture_name": "error",
                "components": [],
                "error": str(e),
            }

    async def _run_critic(
        self,
        output: dict[str, Any],
        task: dict[str, Any],
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """Run Architect B to critique the design."""
        client = self._ensure_client()

        prompt = ARCHITECT_B_PROMPT.format(
            architecture=json.dumps(output, indent=2),
            task=json.dumps(task, indent=2),
            context=json.dumps(context, indent=2),
        )

        try:
            response = await client.chat.completions.create(
                model=self._config.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are Architect B, a critical reviewer. Return only valid JSON.",
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=0.3,
                response_format={"type": "json_object"},
            )

            content = response.choices[0].message.content or "{}"
            return json.loads(content)

        except Exception as e:
            logger.error(f"Architect B failed: {e}")
            return {
                "score": 0.5,
                "consensus": False,
                "error": str(e),
            }

    def _apply_revisions(
        self,
        output: dict[str, Any],
        critique: dict[str, Any],
    ) -> tuple[dict[str, Any], list[str]]:
        """Apply critique revisions to architecture."""
        revisions: list[str] = []

        # Add missing components
        existing_names = {c.get("name", "") for c in output.get("components", [])}
        for missing in critique.get("missing_components", []):
            if missing not in existing_names:
                output.setdefault("components", []).append(
                    {
                        "name": missing,
                        "type": "service",
                        "responsibility": f"Added from critique: {missing}",
                        "interfaces": [],
                        "dependencies": [],
                    }
                )
                revisions.append(f"Added missing component: {missing}")

        # Apply suggested changes
        for change in critique.get("suggested_changes", []):
            component_name = change.get("component", "")
            change_desc = change.get("change", "")

            for component in output.get("components", []):
                if component.get("name") == component_name:
                    # Add change to component notes
                    component.setdefault("notes", []).append(change_desc)
                    revisions.append(
                        f"Applied change to {component_name}: {change_desc[:50]}"
                    )
                    break

        # Add failure points to considerations
        for failure_point in critique.get("failure_points", []):
            output.setdefault("considerations", {}).setdefault(
                "failure_points", []
            ).append(failure_point)
            revisions.append(f"Added failure point consideration: {failure_point[:50]}")

        return output, revisions

    @must_stay_async("callers use await")
    async def _validate_output(
        self,
        output: dict[str, Any],
        task: dict[str, Any],
    ) -> tuple[bool, list[str]]:
        """Validate the architecture design."""
        errors: list[str] = []

        # Check for required fields
        if not output.get("architecture_name"):
            errors.append("Missing architecture name")

        if not output.get("components"):
            errors.append("No components defined")

        # Check component validity
        for idx, component in enumerate(output.get("components", [])):
            if not component.get("name"):
                errors.append(f"Component {idx} missing name")
            if not component.get("responsibility"):
                errors.append(
                    f"Component {component.get('name', idx)} missing responsibility"
                )

        # Check data flows reference valid components
        component_names = {c.get("name") for c in output.get("components", [])}
        for flow in output.get("data_flows", []):
            if flow.get("from") not in component_names:
                errors.append(
                    f"Data flow references unknown source: {flow.get('from')}"
                )
            if flow.get("to") not in component_names:
                errors.append(f"Data flow references unknown target: {flow.get('to')}")

        return len(errors) == 0, errors

    # ==========================================================================
    # Architecture-Specific Methods
    # ==========================================================================

    async def design(
        self,
        requirements: str,
        constraints: Optional[list[str]] = None,
        existing_systems: Optional[list[str]] = None,
    ) -> dict[str, Any]:
        """
        Design an architecture from requirements.

        Args:
            requirements: System requirements description
            constraints: Optional constraints
            existing_systems: Systems to integrate with

        Returns:
            Architecture design
        """
        task = {
            "requirements": requirements,
            "constraints": constraints or [],
            "existing_systems": existing_systems or [],
        }

        context = {
            "mode": "greenfield" if not existing_systems else "integration",
        }

        result = await self.execute(task, context)
        return result.output or {}

    async def review_architecture(
        self,
        architecture: dict[str, Any],
        requirements: str,
    ) -> dict[str, Any]:
        """
        Review an existing architecture.

        Args:
            architecture: Existing architecture
            requirements: Original requirements

        Returns:
            Review results
        """
        task = {"requirements": requirements}
        context = {"mode": "review"}

        # Run only critic
        critique = await self._run_critic(architecture, task, context)
        return critique
