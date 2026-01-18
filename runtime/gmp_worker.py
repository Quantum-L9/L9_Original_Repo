"""
L9 Runtime - GMP Worker
=======================

Dedicated worker for processing GMP (General Module Production) runs.

Features:
- Processes tasks from dedicated GMP queue (l9:gmp_runs)
- Enforces Igor approval requirement (only executes approved tasks)
- Integrates with local GMP runner (runner.py, executor.py, websocket_client.py)
- Streams/logs execution results

Version: 1.0.0
"""

from __future__ import annotations

# ============================================================================
__dora_meta__ = {
    "component_name": "GMP Worker",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2025-12-25T18:55:20Z",
    "updated_at": "2026-01-17T23:47:56Z",
    "layer": "operations",
    "domain": "runtime_operations",
    "module_name": "gmp_worker",
    "type": "engine",
    "status": "production",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": ["Redis"],
        "memory_layers": [],
        "imported_by": ["api.server", "runtime.gmp_approval", "runtime.gmp_tool"],
    },
}
# ============================================================================

import asyncio
import os
import structlog
from pathlib import Path
from typing import Any, Dict, Optional
from datetime import datetime

from runtime.task_queue import TaskQueue, QueuedTask
from core.decorators import must_stay_async

logger = structlog.get_logger(__name__)

# Cursor CLI path (configurable via environment)
CURSOR_CLI_PATH = os.getenv("CURSOR_CLI_PATH", "cursor")
GMP_TIMEOUT_SECONDS = int(os.getenv("GMP_TIMEOUT_SECONDS", "300"))  # 5 minutes default

# GMP queue instance
GMP_QUEUE = TaskQueue(queue_name="l9:gmp_runs", use_redis=True)

# Pending tasks store (in-memory for now, could be Redis-backed)
# Maps task_id -> QueuedTask
_pending_gmp_tasks: Dict[str, QueuedTask] = {}
_pending_lock = asyncio.Lock()


class GMPWorker:
    """
    Worker for processing GMP runs.

    Only executes tasks that have been approved by Igor.
    Tasks without approval remain in queue until approved.
    """

    def __init__(self, poll_interval: float = 2.0):
        """
        Initialize GMP worker.

        Args:
            poll_interval: Seconds between queue polls (default: 2.0)
        """
        self.poll_interval = poll_interval
        self._running = False
        self._task: Optional[asyncio.Task] = None

    @must_stay_async("callers use await")
    async def start(self) -> None:
        """Start the worker loop."""
        if self._running:
            logger.warning("GMP worker already running")
            return

        self._running = True
        self._task = asyncio.create_task(self._worker_loop())
        logger.info("GMP worker started")

    async def stop(self) -> None:
        """Stop the worker loop."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("GMP worker stopped")

    async def _worker_loop(self) -> None:
        """Main worker loop that processes GMP tasks."""
        logger.info("GMP worker loop started")

        while self._running:
            try:
                task = await GMP_QUEUE.dequeue()

                if task is None:
                    # No task available, wait and continue
                    await asyncio.sleep(self.poll_interval)
                    continue

                # Tasks in the queue should already be approved
                # (only approved tasks are moved from pending to queue)
                # But double-check for safety
                approved = task.payload.get("approved_by_igor", False)

                if not approved:
                    logger.warning(
                        f"GMP task {task.task_id} in queue but not approved - skipping"
                    )
                    await asyncio.sleep(self.poll_interval)
                    continue

                # Task is approved - execute it
                logger.info(f"Processing approved GMP task {task.task_id}")
                await self._execute_gmp_task(task)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in GMP worker loop: {e}", exc_info=True)
                await asyncio.sleep(self.poll_interval)

    async def _execute_gmp_task(self, task: QueuedTask) -> None:
        """
        Execute a GMP task.

        Args:
            task: Approved GMP task to execute
        """
        task_id = task.task_id
        payload = task.payload

        try:
            gmp_markdown = payload.get("gmp_markdown", "")
            repo_root = payload.get("repo_root", "")
            caller = payload.get("caller", "unknown")
            metadata = payload.get("metadata", {})

            logger.info(
                f"Executing GMP task {task_id}: caller={caller}, repo={repo_root}"
            )

            # Import GMP runner components
            # Note: These are in mac_agent/ but GMP may use similar patterns
            # For now, we'll create a stub that can be extended
            result = await self._run_gmp(gmp_markdown, repo_root, caller, metadata)

            logger.info(f"GMP task {task_id} completed: status={result.get('status')}")

            # Log result to memory or event stream if needed
            # (Implementation depends on requirements)

        except Exception as e:
            logger.error(f"Failed to execute GMP task {task_id}: {e}", exc_info=True)

    async def _run_gmp(
        self,
        gmp_markdown: str,
        repo_root: str,
        caller: str,
        metadata: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Run GMP workflow by invoking Cursor CLI.

        Writes GMP markdown to a temp file and opens it in Cursor with the target repo.

        Args:
            gmp_markdown: GMP markdown content
            repo_root: Repository root path
            caller: Caller identifier
            metadata: Additional metadata

        Returns:
            Result dictionary with success, output, error, and execution details
        """
        start_time = datetime.utcnow()

        # Validate inputs
        if not gmp_markdown:
            return {
                "success": False,
                "error": "Empty GMP markdown",
                "output": None,
                "traceback": None,
            }

        repo_path = Path(repo_root)
        if not repo_path.exists():
            return {
                "success": False,
                "error": f"Repository path does not exist: {repo_root}",
                "output": None,
                "traceback": None,
            }

        # Create GMP task file in the repo's .cursor directory
        cursor_dir = repo_path / ".cursor"
        cursor_dir.mkdir(parents=True, exist_ok=True)

        gmp_file = (
            cursor_dir / f"gmp_task_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.md"
        )

        try:
            # Write GMP markdown to file
            gmp_file.write_text(gmp_markdown, encoding="utf-8")
            logger.info(
                "GMP markdown written to file",
                gmp_file=str(gmp_file),
                caller=caller,
            )

            # Build Cursor CLI command
            # cursor --goto opens the file in an existing or new Cursor window
            cmd = [
                CURSOR_CLI_PATH,
                "--goto",
                str(gmp_file),
                "--folder-uri",
                f"file://{repo_path.resolve()}",
            ]

            logger.info(
                "Executing Cursor CLI",
                command=" ".join(cmd),
                repo=repo_root,
            )

            # Execute Cursor CLI
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=str(repo_path),
            )

            try:
                stdout, stderr = await asyncio.wait_for(
                    proc.communicate(),
                    timeout=GMP_TIMEOUT_SECONDS,
                )
            except asyncio.TimeoutError:
                proc.kill()
                await proc.wait()
                return {
                    "success": False,
                    "error": f"GMP execution timed out after {GMP_TIMEOUT_SECONDS}s",
                    "output": None,
                    "traceback": None,
                    "duration_seconds": (
                        datetime.utcnow() - start_time
                    ).total_seconds(),
                }

            stdout_str = stdout.decode("utf-8", errors="replace") if stdout else ""
            stderr_str = stderr.decode("utf-8", errors="replace") if stderr else ""

            duration = (datetime.utcnow() - start_time).total_seconds()

            if proc.returncode == 0:
                logger.info(
                    "GMP execution succeeded",
                    caller=caller,
                    duration_seconds=duration,
                )
                return {
                    "success": True,
                    "output": stdout_str,
                    "error": None,
                    "traceback": None,
                    "gmp_file": str(gmp_file),
                    "duration_seconds": duration,
                    "exit_code": 0,
                }
            else:
                logger.error(
                    "GMP execution failed",
                    caller=caller,
                    exit_code=proc.returncode,
                    stderr=stderr_str[:500],
                )
                return {
                    "success": False,
                    "output": stdout_str,
                    "error": stderr_str or f"Cursor exited with code {proc.returncode}",
                    "traceback": None,
                    "gmp_file": str(gmp_file),
                    "duration_seconds": duration,
                    "exit_code": proc.returncode,
                }

        except Exception as e:
            logger.error(
                "GMP execution error",
                caller=caller,
                error=str(e),
                exc_info=True,
            )
            return {
                "success": False,
                "error": str(e),
                "output": None,
                "traceback": str(e),
                "duration_seconds": (datetime.utcnow() - start_time).total_seconds(),
            }
        finally:
            # Optionally clean up GMP file after execution
            # For now, leave it for debugging/audit purposes
            pass


# Global worker instance
_gmp_worker: Optional[GMPWorker] = None


async def start_gmp_worker(poll_interval: float = 2.0) -> GMPWorker:
    """
    Start the global GMP worker.

    Args:
        poll_interval: Poll interval in seconds

    Returns:
        GMPWorker instance
    """
    global _gmp_worker

    if _gmp_worker is None:
        _gmp_worker = GMPWorker(poll_interval=poll_interval)
        await _gmp_worker.start()

    return _gmp_worker


async def stop_gmp_worker() -> None:
    """Stop the global GMP worker."""
    global _gmp_worker

    if _gmp_worker:
        await _gmp_worker.stop()
        _gmp_worker = None


async def store_pending_task(task: QueuedTask) -> None:
    """
    Store a pending GMP task (not yet approved).

    Args:
        task: Task to store
    """
    async with _pending_lock:
        _pending_gmp_tasks[task.task_id] = task
    logger.debug(f"Stored pending GMP task {task.task_id}")


async def get_pending_task(task_id: str) -> Optional[QueuedTask]:
    """
    Get a pending GMP task by ID.

    Args:
        task_id: Task identifier

    Returns:
        QueuedTask or None if not found
    """
    async with _pending_lock:
        return _pending_gmp_tasks.get(task_id)


async def list_pending_tasks() -> list[QueuedTask]:
    """
    List all pending GMP tasks.

    Returns:
        List of pending QueuedTask objects
    """
    async with _pending_lock:
        return list(_pending_gmp_tasks.values())


async def remove_pending_task(task_id: str) -> bool:
    """
    Remove a pending task (after approval or rejection).

    Args:
        task_id: Task identifier

    Returns:
        True if removed, False if not found
    """
    async with _pending_lock:
        if task_id in _pending_gmp_tasks:
            del _pending_gmp_tasks[task_id]
            logger.debug(f"Removed pending GMP task {task_id}")
            return True
        return False


async def approve_and_enqueue(task_id: str) -> bool:
    """
    Approve a pending task and move it to the execution queue.

    Args:
        task_id: Task identifier to approve

    Returns:
        True if approved and enqueued, False otherwise
    """
    task = await get_pending_task(task_id)
    if not task:
        logger.warning(f"Cannot approve: task {task_id} not found in pending")
        return False

    # Update payload to mark as approved
    task.payload["approved_by_igor"] = True
    task.payload["status"] = "approved"
    task.payload["approved_at"] = datetime.utcnow().isoformat()

    # Remove from pending
    await remove_pending_task(task_id)

    # Enqueue to execution queue
    await GMP_QUEUE.enqueue(
        name=task.name,
        payload=task.payload,
        handler=task.handler,
        agent_id=task.agent_id,
        priority=task.priority,
        tags=task.tags,
    )

    logger.info(f"Approved and enqueued GMP task {task_id}")
    return True


__all__ = [
    "GMP_QUEUE",
    "GMPWorker",
    "start_gmp_worker",
    "stop_gmp_worker",
    "store_pending_task",
    "get_pending_task",
    "list_pending_tasks",
    "remove_pending_task",
    "approve_and_enqueue",
]

# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "RUN-OPER-007",
    "governance_level": "medium",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": ["core.decorators", "runtime.task_queue"],
    "tags": ["async", "debugging", "engine", "event-driven", "filesystem", "logging", "operations", "queue", "realtime", "runtime-operations"],
    "keywords": ["approve", "dedicated", "enqueue", "executor", "gmp", "module", "pending", "queue"],
    "business_value": "Implements GMPWorker for gmp worker functionality",
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
