"""
L9 Core Runtimes - ReAct Runtime
=================================

Think → Act → Observe → Repeat loop for agent reasoning.

Based on: "ReAct: Synergizing Reasoning and Acting in Language Models" (Yao et al., 2022)

Key responsibilities:
- Thought generation (reasoning step)
- Action selection (tool use or response)
- Observation integration (tool results)
- Loop control (max iterations, early stopping)

Version: 1.0.0
"""

from __future__ import annotations

__dora_meta__ = {
    "component_name": "ReAct Runtime",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2026-01-18T22:34:00Z",
    "updated_at": "2026-01-18T22:34:00Z",
    "layer": "foundation",
    "domain": "runtime",
    "module_name": "react_runtime",
    "type": "runtime",
    "status": "active",
}

from datetime import datetime
from typing import Any, Dict, List, Optional

import structlog

from core.agents.schemas import AgentTask, ExecutionResult
from core.aios.runtime import AIOSRuntime

logger = structlog.get_logger(__name__)


class ReActStep:
    """Single step in ReAct loop."""

    def __init__(
        self,
        thought: str,
        action: Optional[str] = None,
        action_input: Optional[Dict[str, Any]] = None,
        observation: Optional[str] = None,
    ):
        self.thought = thought
        self.action = action
        self.action_input = action_input
        self.observation = observation
        self.timestamp = datetime.utcnow()


class ReActRuntime:
    """
    ReAct (Reason + Act) runtime for agent task execution.

    Implements the Think → Act → Observe → Repeat pattern.
    """

    def __init__(
        self,
        aios_runtime: AIOSRuntime,
        tool_registry: Any,  # ExecutorToolRegistry
        max_iterations: int = 10,
    ):
        self._aios = aios_runtime
        self._tools = tool_registry
        self._max_iterations = max_iterations

        logger.info(
            "ReActRuntime initialized",
            max_iterations=max_iterations,
        )

    async def execute_task(
        self,
        task: AgentTask,
        agent_context: Dict[str, Any],
    ) -> ExecutionResult:
        """
        Execute task using ReAct loop.

        Args:
            task: Agent task to execute
            agent_context: Agent identity and configuration

        Returns:
            ExecutionResult with final response
        """
        start_time = datetime.utcnow()
        steps: List[ReActStep] = []

        # Initial context
        context = {
            **agent_context,
            "messages": [{"role": "user", "content": task.payload.get("message", "")}],
        }

        for iteration in range(self._max_iterations):
            logger.info(f"ReAct iteration {iteration + 1}/{self._max_iterations}")

            # THINK: Generate thought and action
            thought_context = self._build_thought_context(context, steps)
            aios_result = await self._aios.execute_reasoning(thought_context)

            if aios_result.result_type.value == "error":
                return ExecutionResult(
                    task_id=task.id,
                    status="failed",
                    error=aios_result.error,
                    iterations=iteration + 1,
                    duration_ms=self._duration_ms(start_time),
                )

            # Check if we have a final answer
            if aios_result.result_type.value == "response":
                step = ReActStep(
                    thought="Final answer",
                    observation=aios_result.content,
                )
                steps.append(step)

                return ExecutionResult(
                    task_id=task.id,
                    status="completed",
                    result=aios_result.content,
                    iterations=iteration + 1,
                    duration_ms=self._duration_ms(start_time),
                )

            # ACT: Execute tool call
            if aios_result.result_type.value == "tool_call":
                tool_request = aios_result.tool_call

                step = ReActStep(
                    thought=f"Using tool: {tool_request.tool_id}",
                    action=tool_request.tool_id,
                    action_input=tool_request.arguments,
                )

                # OBSERVE: Get tool result
                try:
                    tool_result = await self._tools.dispatch_tool(tool_request)
                    step.observation = (
                        str(tool_result.result)
                        if tool_result.success
                        else tool_result.error
                    )
                except Exception as e:
                    step.observation = f"Tool error: {str(e)}"

                steps.append(step)

                # Add observation to context for next iteration
                context["messages"].append(
                    {
                        "role": "assistant",
                        "content": f"Thought: {step.thought}\nAction: {step.action}\nInput: {step.action_input}",
                    }
                )
                context["messages"].append(
                    {"role": "user", "content": f"Observation: {step.observation}"}
                )

        # Max iterations reached
        return ExecutionResult(
            task_id=task.id,
            status="terminated",
            result=f"Max iterations ({self._max_iterations}) reached",
            iterations=self._max_iterations,
            duration_ms=self._duration_ms(start_time),
        )

    def _build_thought_context(
        self,
        base_context: Dict[str, Any],
        steps: List[ReActStep],
    ) -> Dict[str, Any]:
        """Build context for thought generation."""
        system_prompt = """You are using the ReAct (Reason + Act) framework.

For each step:
1. THINK: Reason about what to do next
2. ACT: Choose a tool to use (or provide final answer)
3. OBSERVE: See the tool result

Format your response as:
Thought: [your reasoning]
Action: [tool name or "Answer"]
Input: [tool input or final answer]
"""

        return {
            **base_context,
            "system_prompt": system_prompt,
        }

    def _duration_ms(self, start_time: datetime) -> int:
        return int((datetime.utcnow() - start_time).total_seconds() * 1000)


def create_react_runtime(
    aios_runtime: AIOSRuntime,
    tool_registry: Any,
    **kwargs,
) -> ReActRuntime:
    """Factory function to create ReAct runtime."""
    return ReActRuntime(
        aios_runtime=aios_runtime,
        tool_registry=tool_registry,
        **kwargs,
    )


__all__ = ["ReActRuntime", "ReActStep", "create_react_runtime"]
