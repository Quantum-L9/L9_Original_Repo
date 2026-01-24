"""
L9 Runtime - Long Plan Tool Implementation
==========================================

Tool implementations for long_plan.execute and long_plan.simulate.

These tools expose the LangGraph DAG as callable tools for agent L.

Version: 1.0.0
"""

from __future__ import annotations

# ============================================================================
__dora_meta__ = {
    "component_name": "Long Plan Tool Implementation",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2025-12-25T18:55:20Z",
    "updated_at": "2026-01-09T01:57:28Z",
    "layer": "operations",
    "domain": "runtime_operations",
    "module_name": "long_plan_tool",
    "type": "service",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": [],
        "memory_layers": [],
        "imported_by": ["runtime.l_tools"],
    },
}
# ============================================================================

from typing import Any, Dict, List, Optional

import structlog

from orchestration.long_plan_graph import (execute_long_plan,
                                           extract_tasks_from_plan,
                                           simulate_long_plan)
from runtime.task_queue import enqueue_long_plan_tasks
from runtime.tool_call_wrapper import tool_call_wrapper

logger = structlog.get_logger(__name__)


async def long_plan_execute_tool(
    goal: str,
    constraints: List[str] | None = None,
    target_apps: List[str] | None = None,
    agent_id: str = "L",
    thread_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Execute a long plan through the LangGraph DAG.

    Args:
        goal: Goal description
        constraints: List of constraints
        target_apps: List of target apps (e.g., ["github", "notion", "vercel"])
        agent_id: Agent identifier (default: "L")
        thread_id: Optional thread identifier

    Returns:
        Dictionary with:
            - success: bool
            - state: Final DAG state
            - pending_actions: Actions requiring Igor approval
            - review_summary: Summary for review
    """
    if not goal:
        return {
            "success": False,
            "error": "goal is required",
        }

    try:
        # Use tool_call_wrapper to ensure logging
        result = await tool_call_wrapper(
            tool_name="long_plan_execute",
            tool_func=execute_long_plan,
            agent_id=agent_id,
            goal=goal,
            constraints=constraints or [],
            target_apps=target_apps or [],
            thread_id=thread_id,
        )

        logger.info(
            f"Long plan executed: goal={goal[:50]}..., success={result.get('success')}"
        )

        return result

    except Exception as e:
        logger.error(f"Long plan execution failed: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
        }


async def long_plan_simulate_tool(
    goal: str,
    constraints: List[str] | None = None,
    target_apps: List[str] | None = None,
    agent_id: str = "L",
) -> Dict[str, Any]:
    """
    Simulate a long plan without executing (dry run).

    Args:
        goal: Goal description
        constraints: List of constraints
        target_apps: List of target apps
        agent_id: Agent identifier (default: "L")

    Returns:
        Dictionary with simulation results
    """
    if not goal:
        return {
            "success": False,
            "error": "goal is required",
        }

    try:
        # Use tool_call_wrapper to ensure logging
        result = await tool_call_wrapper(
            tool_name="long_plan_simulate",
            tool_func=simulate_long_plan,
            agent_id=agent_id,
            goal=goal,
            constraints=constraints or [],
            target_apps=target_apps or [],
        )

        logger.info(f"Long plan simulated: goal={goal[:50]}...")

        return result

    except Exception as e:
        logger.error(f"Long plan simulation failed: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
        }


async def execute_long_plan_tasks(plan_id: str, repo_root: str) -> Dict[str, Any]:
    """
    Execute tasks from a completed long plan.

    Extracts tasks from plan, enqueues them, and triggers execution.

    Args:
        plan_id: Plan identifier (thread_id from execute_long_plan)
        repo_root: Repository root path

    Returns:
        Dictionary with execution results
    """
    if not plan_id:
        return {
            "success": False,
            "error": "plan_id is required",
        }

    try:
        # Extract tasks from plan
        task_specs = await extract_tasks_from_plan(plan_id)

        if not task_specs:
            return {
                "success": False,
                "error": f"No tasks found in plan {plan_id}",
            }

        # Enqueue tasks
        task_ids = await enqueue_long_plan_tasks(plan_id, task_specs)

        logger.info(f"Enqueued {len(task_ids)} tasks from plan {plan_id} for execution")

        # Note: Actual execution happens via task queue handlers
        # Tasks will be processed by their respective handlers (gmp_worker, git_worker)
        # Approval checks are enforced at execution time

        return {
            "success": True,
            "plan_id": plan_id,
            "enqueued_tasks": len(task_ids),
            "task_ids": task_ids,
            "message": f"Enqueued {len(task_ids)} tasks from plan {plan_id}. Tasks will execute via queue handlers.",
        }

    except Exception as e:
        logger.error(f"Failed to execute plan tasks {plan_id}: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
        }


__all__ = [
    "long_plan_execute_tool",
    "long_plan_simulate_tool",
    "execute_long_plan_tasks",
]

# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "RUN-OPER-001",
    "governance_level": "medium",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": ["runtime.task_queue", "runtime.tool_call_wrapper"],
    "tags": [
        "async",
        "logging",
        "messaging",
        "operations",
        "queue",
        "runtime-operations",
        "service",
    ],
    "keywords": [
        "agent",
        "execute",
        "implementation",
        "long",
        "plan",
        "simulate",
        "tasks",
        "tool",
    ],
    "business_value": "Utility module for long plan tool",
    "last_modified": "2026-01-09T01:57:28Z",
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
