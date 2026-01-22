"""
L9 Reflection Agent Tool Executors
===================================

Tool executor functions for ReflectionAgent capabilities.
These are called by L-CTO when using reflection tools.

Version: 1.0.0
GMP: wire_reflection_agent_yaml
"""

from __future__ import annotations

# ============================================================================
__dora_meta__ = {
    "component_name": "Reflection Tools",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2026-01-16T12:13:08Z",
    "updated_at": "2026-01-17T23:47:56Z",
    "layer": "foundation",
    "domain": "tool_registry",
    "module_name": "reflection_tools",
    "type": "engine",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": [],
        "memory_layers": [],
        "imported_by": ["runtime.l_tools"],
    },
}
# ============================================================================

from typing import Any, Optional

import structlog
from runtime.tool_registry import register_tool

logger = structlog.get_logger(__name__)


@register_tool(name="reflection_agent_reflect", category="reflection", priority=10, description="Execute reflection on execution history")
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


@register_tool(name="reflection_agent_analyze_failure", category="reflection", priority=10, description="Deep failure root cause analysis")
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


@register_tool(name="reflection_agent_compare_approaches", category="reflection", priority=10, description="Compare two approaches with scoring")
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


@register_tool(name="reflection_agent_extract_patterns", category="reflection", priority=10, description="Extract patterns from examples")
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


@register_tool(name="reflection_agent_generate_improvements", category="reflection", priority=10, description="Generate improvement plan from current performance")
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


# LEGACY: REFLECTION_TOOL_EXECUTORS dictionary removed - all tools now use @register_tool decorator
# All reflection tools are auto-discovered via runtime.tool_registry.discover_tools()

__all__ = [
    "reflection_agent_reflect_executor",
    "reflection_agent_analyze_failure_executor",
    "reflection_agent_compare_approaches_executor",
    "reflection_agent_extract_patterns_executor",
    "reflection_agent_generate_improvements_executor",
]

# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "COR-FOUN-001",
    "governance_level": "critical",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": ["agents.reflection_agent"],
    "tags": [
        "async",
        "engine",
        "event-driven",
        "foundation",
        "logging",
        "messaging",
        "metrics",
        "tool-registry",
        "tracing",
    ],
    "keywords": [
        "agent",
        "analyze",
        "approaches",
        "compare",
        "executor",
        "extract",
        "failure",
        "generate",
    ],
    "business_value": "Utility module for reflection tools",
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
