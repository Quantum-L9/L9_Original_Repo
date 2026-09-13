"""
L9 Runtime - Git Tool Implementation
====================================

Tool implementation for git_commit that enqueues pending git commit tasks.

This tool is called by agent L to request git commits.
It only creates pending tasks - actual execution requires Igor's approval.

Version: 1.0.0
"""

from __future__ import annotations

from core.decorators import must_stay_async


from typing import Any
from uuid import uuid4

import structlog

from runtime.task_queue import QueuedTask, TaskQueue

logger = structlog.get_logger(__name__)

# Git queue instance
GIT_QUEUE = TaskQueue(queue_name="l9:git_commits", use_redis=True)


@must_stay_async("callers use await")
async def git_commit_tool(
    message: str,
    repo_root: str,
    files: list[str] | None = None,
    caller: str = "L",
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Git commit tool implementation.

    Enqueues a pending git commit task that requires Igor's approval before execution.

    Args:
        message: Commit message
        repo_root: Repository root path
        files: Optional list of files to commit (None = all changes)
        caller: Caller identifier (default: "L")
        metadata: Additional metadata dictionary

    Returns:
        Dictionary with:
            - task_id: Task identifier
            - status: "pending_igor_approval"
            - message: Human-readable message
    """
    if not message:
        return {
            "task_id": None,
            "status": "error",
            "message": "message is required",
            "error": "Missing message parameter",
        }

    if not repo_root:
        return {
            "task_id": None,
            "status": "error",
            "message": "repo_root is required",
            "error": "Missing repo_root parameter",
        }

    # Create task payload
    payload = {
        "type": "git_commit",
        "message": message,
        "repo_root": repo_root,
        "files": files or [],
        "caller": caller,
        "metadata": metadata or {},
        "approved_by_igor": False,  # Must be False - requires approval
        "status": "pending_igor_approval",
    }

    # Create task and enqueue as pending
    try:
        task_id = str(uuid4())
        QueuedTask(
            task_id=task_id,
            name="Git Commit",
            payload=payload,
            handler="git_worker",
            agent_id="L",
            priority=5,  # Default priority
            tags=["git", "pending_approval"],
            status="pending_igor_approval",
        )

        # Enqueue to git queue (will remain pending until approved)
        await GIT_QUEUE.enqueue(
            name="Git Commit",
            payload=payload,
            handler="git_worker",
            agent_id="L",
            priority=5,
            tags=["git", "pending_approval"],
        )

        logger.info(
            f"Created pending git commit task {task_id}: repo={repo_root}, caller={caller}"
        )

        # Log tool call via ToolGraph
        try:
            # Use runtime import to avoid circular dependency
            import importlib

            module = importlib.import_module("core.tools.tool_graph")
            ToolGraph = module.ToolGraph

            await ToolGraph.log_tool_call(
                tool_name="git_commit",
                agent_id=caller,
                success=True,
                duration_ms=0,  # Enqueue is fast
                error=None,
            )

            # Also write to tool_audit memory segment
            try:
                from runtime.memory_helpers import memory_write

                await memory_write(
                    segment="tool_audit",
                    payload={
                        "tool_name": "git_commit",
                        "agent_id": caller,
                        "task_id": task_id,
                        "status": "pending_igor_approval",
                        "success": True,
                    },
                    agent_id=caller,
                )
            except Exception as mem_err:
                logger.warning(f"Failed to write git tool audit to memory: {mem_err}")

        except Exception as log_err:
            logger.warning(f"Failed to log git tool call: {log_err}")

        return {
            "task_id": task_id,
            "status": "pending_igor_approval",
            "message": f"Git commit task {task_id} created and pending Igor's approval",
        }

    except Exception as e:
        logger.error(f"Failed to create git commit task: {e}", exc_info=True)

        # Log failed tool call
        try:
            # Use runtime import to avoid circular dependency
            import importlib

            module = importlib.import_module("core.tools.tool_graph")
            ToolGraph = module.ToolGraph

            await ToolGraph.log_tool_call(
                tool_name="git_commit",
                agent_id=caller,
                success=False,
                duration_ms=0,
                error=str(e),
            )
        except Exception:
            logger.debug("git_tool.log_tool_call_failed")

        return {
            "task_id": None,
            "status": "error",
            "message": f"Failed to create git commit task: {e!s}",
            "error": str(e),
        }


__all__ = ["git_commit_tool"]

# Runtime execution trace - updated automatically on every execution
