"""
L9 Runtime - GMP Approval Interface
====================================

Interface for Igor to approve or reject pending GMP tasks.

Provides:
- List pending GMP tasks
- Approve tasks (sets approved_by_igor=True)
- Reject tasks (removes from queue)
- Get task details

Version: 1.0.0
"""

from __future__ import annotations

# ============================================================================
__dora_meta__ = {
    "component_name": "GMP Approval Interface",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2025-12-25T18:55:20Z",
    "updated_at": "2026-01-07T13:35:58Z",
    "layer": "operations",
    "domain": "runtime_operations",
    "module_name": "gmp_approval",
    "type": "service",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": [],
        "memory_layers": [],
        "imported_by": [],
    },
}
# ============================================================================

import structlog
from typing import Any, Dict, List, Optional

from runtime.gmp_worker import (
    list_pending_tasks,
    get_pending_task,
    remove_pending_task,
    approve_and_enqueue,
)

logger = structlog.get_logger(__name__)


async def list_pending_gmp_tasks() -> List[Dict[str, Any]]:
    """
    List all pending GMP tasks (not yet approved).

    Returns:
        List of task dictionaries with task_id, name, payload, created_at
    """
    pending_tasks = await list_pending_tasks()

    return [
        {
            "task_id": task.task_id,
            "name": task.name,
            "payload": task.payload,
            "created_at": task.created_at.isoformat(),
            "caller": task.payload.get("caller", "unknown"),
            "repo_root": task.payload.get("repo_root", "unknown"),
        }
        for task in pending_tasks
    ]


async def get_gmp_task(task_id: str) -> Optional[Dict[str, Any]]:
    """
    Get details of a specific GMP task.

    Args:
        task_id: Task identifier

    Returns:
        Task dictionary or None if not found
    """
    task = await get_pending_task(task_id)
    if not task:
        return None

    return {
        "task_id": task.task_id,
        "name": task.name,
        "payload": task.payload,
        "created_at": task.created_at.isoformat(),
        "caller": task.payload.get("caller", "unknown"),
        "repo_root": task.payload.get("repo_root", "unknown"),
    }


async def approve_gmp_task(task_id: str) -> bool:
    """
    Approve a GMP task for execution.

    Moves the task from pending to the execution queue.

    Args:
        task_id: Task identifier to approve

    Returns:
        True if approved successfully, False otherwise
    """
    return await approve_and_enqueue(task_id)


async def reject_gmp_task(task_id: str) -> bool:
    """
    Reject a GMP task (remove it from pending queue).

    Args:
        task_id: Task identifier to reject

    Returns:
        True if rejected successfully, False otherwise
    """
    return await remove_pending_task(task_id)


# CLI interface for Igor
async def cli_list_pending() -> None:
    """CLI command: List pending GMP tasks."""
    tasks = await list_pending_gmp_tasks()

    if not tasks:
        logger.info("No pending GMP tasks")
        return

    logger.info(f"\nPending GMP Tasks ({len(tasks)}):")
    logger.info("=" * 80)

    for task in tasks:
        logger.info(f"\nTask ID: {task.get('task_id')}")
        logger.info(f"Name: {task.get('name')}")
        logger.info(f"Created: {task.get('created_at')}")
        logger.info(f"Caller: {task.get('payload', {}).get('caller', 'unknown')}")
        logger.info(f"Repo: {task.get('payload', {}).get('repo_root', 'unknown')}")
        logger.info("-" * 80)


async def cli_approve(task_id: str) -> None:
    """CLI command: Approve a GMP task."""
    success = await approve_gmp_task(task_id)

    if success:
        logger.info(f"✓ Approved GMP task {task_id}")
    else:
        logger.error(f"✗ Failed to approve GMP task {task_id}")


async def cli_reject(task_id: str) -> None:
    """CLI command: Reject a GMP task."""
    success = await reject_gmp_task(task_id)

    if success:
        logger.info(f"✓ Rejected GMP task {task_id}")
    else:
        logger.error(f"✗ Failed to reject GMP task {task_id}")


__all__ = [
    "list_pending_gmp_tasks",
    "get_gmp_task",
    "approve_gmp_task",
    "reject_gmp_task",
    "cli_list_pending",
    "cli_approve",
    "cli_reject",
]

# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "RUN-OPER-001",
    "governance_level": "medium",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": ["runtime.gmp_worker"],
    "tags": [
        "async",
        "logging",
        "operations",
        "queue",
        "runtime-operations",
        "service",
    ],
    "keywords": [
        "approval",
        "approve",
        "cli",
        "gmp",
        "interface",
        "pending",
        "queue",
        "reject",
    ],
    "business_value": "List pending GMP tasks Approve tasks (sets approved_by_igor=True) Reject tasks (removes from queue) Get task details Version: 1.0.0",
    "last_modified": "2026-01-07T13:35:58Z",
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
