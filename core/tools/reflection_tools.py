"""
L9 Reflection Agent Tool Executors
===================================

Tool executor functions for ReflectionAgent capabilities.
These are called by L-CTO when using reflection tools.

Version: 1.0.0
GMP: wire_reflection_agent_yaml
"""

from __future__ import annotations

from typing import Any, Optional

import structlog

logger = structlog.get_logger(__name__)


async def reflection_agent_reflect_executor(
    history: list[dict[str, Any]],
    focus: str = "general",
    goals: Optional[list[str]] = None,
) -> dict[str, Any]:
    """
    Execute reflection on execution history.

    Args:
        history: List of execution events to reflect on
        focus: Focus area (general, failures, patterns)
        goals: Optional goals to evaluate against

    Returns:
        Reflection results with insights and lessons
    """
    from agents.reflection_agent import create_reflection_agent

    logger.info(
        "reflection_tool.reflect",
        focus=focus,
        history_size=len(history),
    )

    agent = create_reflection_agent()
    return await agent.reflection_agent_reflect(
        history=history,
        focus=focus,
        goals=goals,
    )


async def reflection_agent_analyze_failure_executor(
    failure_context: dict[str, Any],
    error: str,
    stack_trace: Optional[str] = None,
) -> dict[str, Any]:
    """
    Deep failure root cause analysis.

    Args:
        failure_context: Context of the failure
        error: Error message
        stack_trace: Optional stack trace

    Returns:
        Root cause analysis with prevention strategies
    """
    from agents.reflection_agent import create_reflection_agent

    logger.info(
        "reflection_tool.analyze_failure",
        error=error[:100],
        has_stack_trace=stack_trace is not None,
    )

    agent = create_reflection_agent()
    return await agent.reflection_agent_analyze_failure(
        failure_context=failure_context,
        error=error,
        stack_trace=stack_trace,
    )


async def reflection_agent_compare_approaches_executor(
    approach_a: dict[str, Any],
    approach_b: dict[str, Any],
    criteria: list[str],
) -> dict[str, Any]:
    """
    Compare two approaches with scoring.

    Args:
        approach_a: First approach to compare
        approach_b: Second approach to compare
        criteria: List of comparison criteria

    Returns:
        Comparison with scores and recommendation
    """
    from agents.reflection_agent import create_reflection_agent

    logger.info(
        "reflection_tool.compare_approaches",
        criteria_count=len(criteria),
    )

    agent = create_reflection_agent()
    return await agent.reflection_agent_compare_approaches(
        approach_a=approach_a,
        approach_b=approach_b,
        criteria=criteria,
    )


async def reflection_agent_extract_patterns_executor(
    examples: list[dict[str, Any]],
) -> dict[str, Any]:
    """
    Extract patterns from examples.

    Args:
        examples: List of examples to analyze

    Returns:
        Extracted patterns, anti-patterns, and generalizations
    """
    from agents.reflection_agent import create_reflection_agent

    logger.info(
        "reflection_tool.extract_patterns",
        examples_count=len(examples),
    )

    agent = create_reflection_agent()
    return await agent.reflection_agent_extract_patterns(examples=examples)


async def reflection_agent_generate_improvements_executor(
    current_performance: dict[str, Any],
    goals: list[str],
) -> dict[str, Any]:
    """
    Generate improvement plan from current performance.

    Args:
        current_performance: Current performance metrics
        goals: Improvement goals

    Returns:
        Gap analysis and improvement plan
    """
    from agents.reflection_agent import create_reflection_agent

    logger.info(
        "reflection_tool.generate_improvements",
        goals_count=len(goals),
    )

    agent = create_reflection_agent()
    return await agent.reflection_agent_generate_improvements(
        current_performance=current_performance,
        goals=goals,
    )


# Export all executors for registration
REFLECTION_TOOL_EXECUTORS = {
    "reflection_agent_reflect": reflection_agent_reflect_executor,
    "reflection_agent_analyze_failure": reflection_agent_analyze_failure_executor,
    "reflection_agent_compare_approaches": reflection_agent_compare_approaches_executor,
    "reflection_agent_extract_patterns": reflection_agent_extract_patterns_executor,
    "reflection_agent_generate_improvements": reflection_agent_generate_improvements_executor,
}

__all__ = [
    "reflection_agent_reflect_executor",
    "reflection_agent_analyze_failure_executor",
    "reflection_agent_compare_approaches_executor",
    "reflection_agent_extract_patterns_executor",
    "reflection_agent_generate_improvements_executor",
    "REFLECTION_TOOL_EXECUTORS",
]
