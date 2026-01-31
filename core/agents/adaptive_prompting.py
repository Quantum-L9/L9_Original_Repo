"""
L9 Core Agents - Adaptive Prompting
====================================

Generates adaptive context for L based on governance patterns from
past approval/rejection decisions.

Enables closed-loop learning: L adapts behavior based on Igor's
feedback without explicit retraining.

Version: 1.0.0
"""

from __future__ import annotations

# ============================================================================
__dora_meta__ = {
    "component_name": "Adaptive Prompting",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2026-01-02T15:15:57Z",
    "updated_at": "2026-01-14T15:03:00Z",
    "layer": "foundation",
    "domain": "agent_execution",
    "module_name": "adaptive_prompting",
    "type": "service",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": [],
        "memory_layers": [],
        "imported_by": [
            "core.agents.executor",
            "tests.integration.test_closed_loop_learning",
        ],
    },
}
# ============================================================================

from typing import Any

import structlog

logger = structlog.get_logger(__name__)


def generate_adaptive_context(patterns: list[dict[str, Any]]) -> str:
    """
    Generate adaptive context from governance patterns.

    Analyzes past approval/rejection decisions and generates
    natural language guidance for L to follow.

    Args:
        patterns: List of governance pattern dicts from memory

    Returns:
        Adaptive context string to prepend to L's system prompt
    """
    if not patterns:
        return ""

    # Separate by decision type
    rejections = [p for p in patterns if p.get("decision") == "rejected"]
    approvals = [p for p in patterns if p.get("decision") == "approved"]

    context_parts = []

    # Learn from rejections
    if rejections:
        rejection_lessons = _extract_lessons_from_rejections(rejections)
        if rejection_lessons:
            context_parts.append(
                "**Past Rejection Patterns (AVOID THESE):**\n" + rejection_lessons
            )

    # Learn from approvals
    if approvals:
        approval_lessons = _extract_lessons_from_approvals(approvals)
        if approval_lessons:
            context_parts.append(
                "**Past Approval Patterns (FOLLOW THESE):**\n" + approval_lessons
            )

    if not context_parts:
        return ""

    header = (
        "\n---\n"
        "**ADAPTIVE CONTEXT FROM IGOR'S PAST DECISIONS:**\n"
        "The following guidance is derived from Igor's prior approvals and rejections. "
        "Incorporate these lessons to improve proposal quality.\n\n"
    )

    return header + "\n\n".join(context_parts) + "\n---\n"


def _extract_lessons_from_rejections(rejections: list[dict[str, Any]]) -> str:
    """Extract lessons from rejection patterns."""
    lessons = []
    seen_conditions = set()

    for pattern in rejections:
        conditions = pattern.get("conditions", [])
        reason = pattern.get("reason", "")
        tool_name = pattern.get("tool_name", "")

        for condition in set(conditions):
            if condition not in seen_conditions:
                seen_conditions.add(condition)

                # Map conditions to actionable advice
                if condition == "requires_tests":
                    lessons.append(
                        f"- Prior {tool_name} rejected for lacking tests. "
                        "Always include comprehensive test coverage."
                    )
                elif condition == "requires_runbook":
                    lessons.append(
                        f"- Prior {tool_name} rejected for missing runbook. "
                        "Draft detailed runbook with rollback steps before proposing."
                    )
                elif condition == "requires_documentation":
                    lessons.append(
                        f"- Prior {tool_name} rejected for lacking documentation. "
                        "Include clear documentation for all changes."
                    )
                elif condition == "requires_rollback_plan":
                    lessons.append(
                        f"- Prior {tool_name} rejected for no rollback plan. "
                        "Always specify how to revert changes if needed."
                    )
                elif condition == "scope_concern":
                    lessons.append(
                        f"- Prior {tool_name} rejected for scope being too broad. "
                        "Keep changes focused and incremental."
                    )
                elif condition == "high_risk":
                    lessons.append(
                        f"- Prior {tool_name} flagged as high risk. "
                        "Provide extra justification and safety analysis."
                    )

        # If no conditions extracted, use the raw reason
        if not conditions and reason:
            lessons.append(f"- Rejection reason: {reason[:100]}...")

    return "\n".join(lessons[:5])  # Limit to top 5 lessons


def _extract_lessons_from_approvals(approvals: list[dict[str, Any]]) -> str:
    """Extract lessons from approval patterns."""
    lessons = []
    seen_conditions = set()

    for pattern in approvals:
        conditions = pattern.get("conditions", [])
        tool_name = pattern.get("tool_name", "")

        for condition in set(conditions):
            if condition not in seen_conditions:
                seen_conditions.add(condition)

                if condition == "good_test_coverage":
                    lessons.append(
                        f"- {tool_name} approved with good test coverage. "
                        "Continue providing comprehensive tests."
                    )
                elif condition == "good_documentation":
                    lessons.append(
                        f"- {tool_name} approved with clear documentation. "
                        "Maintain this level of clarity."
                    )
                elif condition == "incremental_change":
                    lessons.append(
                        f"- {tool_name} approved as incremental change. "
                        "Small, focused changes are preferred."
                    )

    return "\n".join(lessons[:3])  # Limit to top 3 lessons


async def get_adaptive_context_for_tool(tool_name: str) -> str:
    """
    Get adaptive context for a specific tool.

    Queries governance patterns for the tool and generates context.

    Args:
        tool_name: Tool name (e.g., "gmprun", "git_commit")

    Returns:
        Adaptive context string
    """
    try:
        from memory.retrieval import get_governance_patterns

        patterns = await get_governance_patterns(
            tool_name=tool_name,
            limit=10,  # Get recent patterns for this tool
        )

        return generate_adaptive_context(patterns)

    except ImportError as e:
        logger.error(f"Missing dependency for adaptive context: {e}")
        raise
    except Exception as e:
        logger.error(f"Failed to get adaptive context for {tool_name}: {e}", exc_info=True)
        raise


async def get_world_model_context_for_agent(agent_name: str = "L") -> str:
    """
    Get world model context for an agent.

    Queries the world model for agent capabilities, infrastructure status,
    and integration status to provide situational awareness.

    Args:
        agent_name: Agent name (e.g., "L", "CA")

    Returns:
        World model context string to prepend to agent prompts
    """
    try:
        from core.worldmodel.service import get_world_model_service

        service = get_world_model_service()
        return await service.get_world_model_context(agent_name)

    except ImportError as e:
        logger.error(f"Missing dependency for world model context: {e}")
        raise
    except Exception as e:
        logger.error(f"Failed to get world model context for {agent_name}: {e}", exc_info=True)
        raise


async def get_combined_adaptive_context(
    tool_name: str,
    agent_name: str = "L",
    include_world_model: bool = True,
) -> str:
    """
    Get combined adaptive context including governance patterns and world model.

    Args:
        tool_name: Tool being used
        agent_name: Agent using the tool
        include_world_model: Whether to include world model context

    Returns:
        Combined context string
    """
    context_parts = []

    # Get governance-based adaptive context
    governance_context = await get_adaptive_context_for_tool(tool_name)
    if governance_context:
        context_parts.append(governance_context)

    # Get world model context
    if include_world_model:
        world_model_context = await get_world_model_context_for_agent(agent_name)
        if world_model_context:
            context_parts.append(world_model_context)

    return "\n\n".join(context_parts)


async def get_test_failure_context(task_id: str) -> str:
    """
    Get adaptive context from test failures for a task.

    Queries test_results segment for failures and generates
    adaptive guidance for L to refine proposals.

    Args:
        task_id: Task ID to check for test failures

    Returns:
        Adaptive context string based on test failures
    """
    try:
        from memory.retrieval import get_test_results_for_task

        test_results = await get_test_results_for_task(task_id)

        if not test_results:
            return ""

        # Find failed tests
        failed_results = [r for r in test_results if not r.get("success", True)]

        if not failed_results:
            return ""

        context_parts = ["\n---\n**PRIOR TEST FAILURES FOR THIS TASK:**\n"]

        for result in failed_results[:3]:  # Limit to 3 most recent
            tests_failed = result.get("tests_failed", 0)
            recommendations = result.get("recommendations", [])

            context_parts.append(
                f"- Previous attempt had {tests_failed} failing test(s)"
            )
            for rec in recommendations[:2]:
                context_parts.append(f"  - {rec}")

        context_parts.append("\nAddress these issues in your revised proposal.\n---\n")

        return "\n".join(context_parts)

    except ImportError as e:
        logger.error(f"Missing dependency for test failure context: {e}")
        raise
    except Exception as e:
        logger.error(f"Failed to get test failure context: {e}", exc_info=True)
        raise


# =============================================================================
# Public API
# =============================================================================

__all__ = [
    "generate_adaptive_context",
    "get_adaptive_context_for_tool",
    "get_combined_adaptive_context",
    "get_test_failure_context",
    "get_world_model_context_for_agent",
]

# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "COR-FOUN-001",
    "governance_level": "critical",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": ["core.worldmodel.service", "memory.retrieval"],
    "tags": [
        "agent-execution",
        "api",
        "async",
        "foundation",
        "logging",
        "service",
        "testing",
    ],
    "keywords": [
        "adaptive",
        "agent",
        "based",
        "combined",
        "failure",
        "generate",
        "governance",
        "model",
    ],
    "business_value": "Utility module for adaptive prompting",
    "last_modified": "2026-01-14T15:03:00Z",
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
