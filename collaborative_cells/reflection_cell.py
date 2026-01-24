"""
L9 Collaborative Cells - Reflection Cell
========================================

Meta-reasoning cell for self-correction and improvement.

Uses 2 reflection agents:
- Analyst: Examines execution history and outcomes
- Synthesizer: Derives lessons and improvements
"""

from __future__ import annotations

# ============================================================================
__dora_meta__ = {
    "component_name": "Reflection Cell",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2025-12-09T01:02:49Z",
    "updated_at": "2026-01-17T23:47:56Z",
    "layer": "intelligence",
    "domain": "collaborative_reasoning",
    "module_name": "reflection_cell",
    "type": "service",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": ["OpenAI API"],
        "memory_layers": [],
        "imported_by": [
            "collaborative_cells.__init__",
            "orchestration.cell_orchestrator",
        ],
    },
}
# ============================================================================

import json
from typing import Any, Optional

import structlog
from openai import AsyncOpenAI

from collaborative_cells.base_cell import BaseCell, CellConfig
from core.decorators import must_stay_async

logger = structlog.get_logger(__name__)


ANALYST_PROMPT = """You are the Reflection Analyst. Examine the execution history and identify patterns.

Execution History:
{history}

Current State:
{current_state}

Context:
{context}

Analyze:
1. What succeeded and why?
2. What failed and why?
3. What patterns emerge?
4. What could be done differently?
5. What knowledge should be retained?

Return JSON:
{{
    "successes": [
        {{"action": "...", "outcome": "...", "contributing_factors": ["..."]}}
    ],
    "failures": [
        {{"action": "...", "outcome": "...", "root_cause": "...", "could_have_prevented": "..."}}
    ],
    "patterns": [
        {{"pattern": "...", "frequency": "...", "impact": "positive|negative|neutral"}}
    ],
    "alternative_approaches": [
        {{"situation": "...", "alternative": "...", "expected_benefit": "..."}}
    ],
    "knowledge_to_retain": [
        {{"fact": "...", "context": "...", "confidence": 0.0 to 1.0}}
    ],
    "reasoning": "..."
}}
"""

SYNTHESIZER_PROMPT = """You are the Reflection Synthesizer. Create actionable improvements from analysis.

Analysis:
{analysis}

Current Capabilities:
{capabilities}

Goals:
{goals}

Synthesize:
1. What specific improvements should be made?
2. What new capabilities are needed?
3. What processes should change?
4. What should be remembered for the future?

Return JSON:
{{
    "score": 0.0 to 1.0,
    "improvements": [
        {{
            "area": "...",
            "current_state": "...",
            "target_state": "...",
            "action_required": "...",
            "priority": "critical|high|medium|low"
        }}
    ],
    "new_capabilities_needed": [
        {{"capability": "...", "reason": "...", "implementation_hint": "..."}}
    ],
    "process_changes": [
        {{"process": "...", "change": "...", "expected_benefit": "..."}}
    ],
    "memory_updates": [
        {{"type": "add|update|remove", "key": "...", "value": "...", "reason": "..."}}
    ],
    "consensus": true/false,
    "reasoning": "..."
}}
"""


class ReflectionCell(BaseCell):
    """
    Meta-reasoning cell for self-improvement.

    Analyzes execution history to derive lessons and improvements.
    """

    cell_type = "reflection"

    def __init__(self, config: Optional[CellConfig] = None):
        """Initialize the reflection cell."""
        super().__init__(config)
        self._client: Optional[AsyncOpenAI] = None
        self._reflection_history: list[dict[str, Any]] = []

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
        """Run Analyst to examine history."""
        client = self._ensure_client()

        prompt = ANALYST_PROMPT.format(
            history=json.dumps(task.get("history", []), indent=2),
            current_state=json.dumps(task.get("current_state", {}), indent=2),
            context=json.dumps(context, indent=2),
        )

        try:
            response = await client.chat.completions.create(
                model=self._config.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a reflection analyst. Return only valid JSON.",
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=0.3,
                response_format={"type": "json_object"},
            )

            content = response.choices[0].message.content or "{}"
            return json.loads(content)

        except Exception as e:
            logger.error(f"Analyst failed: {e}")
            return {
                "successes": [],
                "failures": [],
                "patterns": [],
                "error": str(e),
            }

    async def _run_critic(
        self,
        output: dict[str, Any],
        task: dict[str, Any],
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """Run Synthesizer to derive improvements."""
        client = self._ensure_client()

        prompt = SYNTHESIZER_PROMPT.format(
            analysis=json.dumps(output, indent=2),
            capabilities=json.dumps(task.get("capabilities", []), indent=2),
            goals=json.dumps(task.get("goals", []), indent=2),
        )

        try:
            response = await client.chat.completions.create(
                model=self._config.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a reflection synthesizer. Return only valid JSON.",
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=0.3,
                response_format={"type": "json_object"},
            )

            content = response.choices[0].message.content or "{}"
            return json.loads(content)

        except Exception as e:
            logger.error(f"Synthesizer failed: {e}")
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
        """Merge synthesis with analysis."""
        revisions: list[str] = []

        # Add improvements to output
        output["improvements"] = critique.get("improvements", [])
        revisions.append(f"Added {len(output['improvements'])} improvements")

        # Add new capabilities needed
        output["new_capabilities_needed"] = critique.get("new_capabilities_needed", [])
        if output["new_capabilities_needed"]:
            revisions.append(
                f"Identified {len(output['new_capabilities_needed'])} new capabilities needed"
            )

        # Add process changes
        output["process_changes"] = critique.get("process_changes", [])
        if output["process_changes"]:
            revisions.append(
                f"Suggested {len(output['process_changes'])} process changes"
            )

        # Add memory updates
        output["memory_updates"] = critique.get("memory_updates", [])
        if output["memory_updates"]:
            revisions.append(f"Proposed {len(output['memory_updates'])} memory updates")

        return output, revisions

    @must_stay_async("callers use await")
    async def _validate_output(
        self,
        output: dict[str, Any],
        task: dict[str, Any],
    ) -> tuple[bool, list[str]]:
        """Validate reflection output."""
        errors: list[str] = []

        # Check for basic structure
        required_keys = ["successes", "failures", "patterns"]
        for key in required_keys:
            if key not in output:
                errors.append(f"Missing {key} in reflection output")

        # Validate improvements have required fields
        for idx, imp in enumerate(output.get("improvements", [])):
            if not imp.get("action_required"):
                errors.append(f"Improvement {idx} missing action_required")

        return len(errors) == 0, errors

    # ==========================================================================
    # Reflection-Specific Methods
    # ==========================================================================

    async def reflect_on_execution(
        self,
        execution_history: list[dict[str, Any]],
        current_state: dict[str, Any],
        goals: Optional[list[str]] = None,
    ) -> dict[str, Any]:
        """
        Reflect on execution history.

        Args:
            execution_history: List of execution records
            current_state: Current system state
            goals: Optional goals for improvement

        Returns:
            Reflection result with improvements
        """
        task = {
            "history": execution_history,
            "current_state": current_state,
            "goals": goals or [],
        }

        context = {
            "mode": "execution_reflection",
        }

        result = await self.execute(task, context)

        # Store in history
        self._reflection_history.append(
            {
                "input": task,
                "output": result.output,
                "timestamp": result.metadata.get("timestamp"),
            }
        )

        return result.output or {}

    async def reflect_on_failure(
        self,
        failure_context: dict[str, Any],
        error_message: str,
        stack_trace: Optional[str] = None,
    ) -> dict[str, Any]:
        """
        Reflect specifically on a failure.

        Args:
            failure_context: Context of the failure
            error_message: Error message
            stack_trace: Optional stack trace

        Returns:
            Analysis and recovery suggestions
        """
        task = {
            "history": [
                {
                    "action": failure_context.get("action", "unknown"),
                    "status": "failed",
                    "error": error_message,
                    "stack_trace": stack_trace,
                    "context": failure_context,
                }
            ],
            "current_state": {"status": "error_recovery"},
            "goals": ["Understand failure", "Prevent recurrence"],
        }

        context = {
            "mode": "failure_analysis",
        }

        result = await self.execute(task, context)
        output = result.output or {}

        # Extract recovery-specific information
        return {
            "root_cause": output.get("failures", [{}])[0].get("root_cause", "Unknown"),
            "prevention": output.get("failures", [{}])[0].get(
                "could_have_prevented", ""
            ),
            "immediate_actions": [
                imp.get("action_required")
                for imp in output.get("improvements", [])
                if imp.get("priority") in ("critical", "high")
            ],
            "process_changes": output.get("process_changes", []),
        }

    async def derive_lessons(
        self,
        session_history: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """
        Derive lessons from a session.

        Args:
            session_history: Complete session history

        Returns:
            List of lessons learned
        """
        task = {
            "history": session_history,
            "current_state": {},
            "goals": ["Extract reusable lessons"],
        }

        context = {
            "mode": "lesson_extraction",
        }

        result = await self.execute(task, context)
        output = result.output or {}

        # Format as lessons
        lessons = []

        for knowledge in output.get("knowledge_to_retain", []):
            lessons.append(
                {
                    "lesson": knowledge.get("fact", ""),
                    "context": knowledge.get("context", ""),
                    "confidence": knowledge.get("confidence", 0.5),
                    "source": "reflection",
                }
            )

        for pattern in output.get("patterns", []):
            if pattern.get("impact") in ("positive", "negative"):
                lessons.append(
                    {
                        "lesson": f"Pattern: {pattern.get('pattern', '')}",
                        "context": f"Impact: {pattern.get('impact')}",
                        "confidence": 0.7,
                        "source": "pattern_analysis",
                    }
                )

        return lessons

    def get_reflection_history(self) -> list[dict[str, Any]]:
        """Get stored reflection history."""
        return self._reflection_history.copy()

    def clear_history(self) -> None:
        """Clear reflection history."""
        self._reflection_history.clear()


# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "COL-INTE-003",
    "governance_level": "high",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": ["core.decorators"],
    "tags": [
        "api",
        "async",
        "collaborative-reasoning",
        "event-driven",
        "intelligence",
        "llm",
        "logging",
        "messaging",
        "serialization",
        "service",
    ],
    "keywords": [
        "cell",
        "clear",
        "derive",
        "execution",
        "failure",
        "history",
        "lessons",
        "reflect",
    ],
    "business_value": "Implements ReflectionCell for reflection cell functionality",
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
