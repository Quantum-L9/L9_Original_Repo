"""
Agent Execution Task Queue
==========================

File-based task queue for Mac Agent execution only.

This module handles ONLY mac_task types. Email tasks are handled separately.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
import threading
import json
import os
import shutil
import structlog
from pathlib import Path
from uuid import uuid4

logger = structlog.get_logger(__name__)


@dataclass
class MacTask:
    """Mac task dataclass (legacy support)."""

    id: int
    source: str
    channel: str
    user: str
    command: Optional[str] = None  # Legacy: shell command
    steps: Optional[List[Dict[str, Any]]] = None  # V2: automation steps
    attachments: Optional[List[Dict[str, Any]]] = None  # File attachments from Slack
    status: str = "queued"  # "queued" | "running" | "done" | "failed"
    result: Optional[str] = None
    screenshot_path: Optional[str] = None
    logs: Optional[List[str]] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


# File-based storage directories
TASKS_DIR = Path(os.path.expanduser("~/.l9/mac_tasks"))
IN_PROGRESS_DIR = TASKS_DIR / "in_progress"
COMPLETED_DIR = TASKS_DIR / "completed"

# Ensure directories exist
TASKS_DIR.mkdir(parents=True, exist_ok=True)
IN_PROGRESS_DIR.mkdir(parents=True, exist_ok=True)
COMPLETED_DIR.mkdir(parents=True, exist_ok=True)

# In-memory storage (legacy support)
_tasks: Dict[int, MacTask] = {}
_next_id: int = 1
_lock = threading.Lock()


def enqueue_mac_task(
    source: str,
    channel: str,
    user: str,
    command: Optional[str] = None,
    steps: Optional[List[Dict[str, Any]]] = None,
    attachments: Optional[List[Dict[str, Any]]] = None,
) -> int:
    """
    Enqueue a new Mac task (legacy function signature).
    Also ingests to memory for audit trail.

    Args:
        source: Source of the task (e.g., "slack")
        channel: Channel identifier (e.g., Slack channel ID)
        user: User identifier (e.g., Slack user ID)
        command: Shell command to execute (legacy)
        steps: Automation steps for V2 (list of action dicts)
        attachments: File attachments from Slack (list of file artifact dicts)

    Returns:
        Task ID (integer, legacy)
    """
    global _next_id
    with _lock:
        task_id = _next_id
        _next_id += 1
        task = MacTask(
            id=task_id,
            source=source,
            channel=channel,
            user=user,
            command=command,
            steps=steps,
            attachments=attachments,
            status="queued",
        )
        _tasks[task_id] = task

    # Ingest task to memory (fire-and-forget)
    try:
        import asyncio
        from memory.ingestion import ingest_packet
        from core.schemas import PacketEnvelopeIn

        packet_in = PacketEnvelopeIn(
            packet_type="mac_task_enqueued",
            payload={
                "task_id": task_id,
                "source": source,
                "channel": channel,
                "user": user,
                "command": command[:500] if command else None,
                "step_count": len(steps) if steps else 0,
                "has_attachments": bool(attachments),
            },
            metadata={"agent": "mac_agent", "source": "agent_execution"},
        )
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(ingest_packet(packet_in))
        except RuntimeError:
            pass  # No running loop - skip in sync context
    except Exception as mem_err:
        logger.warning(f"Failed to ingest mac task to memory: {mem_err}")

    return task_id


def enqueue_mac_task_dict(task_dict: Dict[str, Any]) -> str:
    """
    Enqueue a Mac task from task router (file-based storage).
    
    This function ONLY accepts mac_task type. Email tasks must use separate routing.

    Args:
        task_dict: Task dictionary with type="mac_task" and steps

    Returns:
        Task ID (UUID string)

    Raises:
        ValueError: If task_dict type is not "mac_task"
    """
    task_type = task_dict.get("type", "mac_task")
    if task_type != "mac_task":
        raise ValueError(
            f"agent_execution task queue only accepts mac_task, got: {task_type}. "
            f"Email tasks must use separate email task routing."
        )

    task_id = str(uuid4())
    task_file = TASKS_DIR / f"{task_id}.json"

    # Add task_id to dict
    task_dict["task_id"] = task_id
    task_dict["status"] = "queued"
    task_dict["created_at"] = datetime.now(timezone.utc).isoformat()

    try:
        with open(task_file, "w") as f:
            json.dump(task_dict, f, indent=2)
        logger.info(f"Enqueued mac_task {task_id} to {task_file}")

        # Ingest task to memory (fire-and-forget, don't block on failure)
        try:
            import asyncio
            from memory.ingestion import ingest_packet
            from core.schemas import PacketEnvelopeIn

            packet_in = PacketEnvelopeIn(
                packet_type="mac_task_enqueued",
                payload={
                    "task_id": task_id,
                    "task_type": "mac_task",
                    "user": task_dict.get("metadata", {}).get("user"),
                    "instructions": task_dict.get("metadata", {}).get(
                        "instructions", ""
                    )[:500],
                    "step_count": len(task_dict.get("steps", [])),
                    "has_artifacts": bool(task_dict.get("artifacts")),
                },
                metadata={"agent": "mac_agent", "source": "agent_execution"},
            )
            # Run async ingestion in current event loop if available
            try:
                loop = asyncio.get_running_loop()
                loop.create_task(ingest_packet(packet_in))
            except RuntimeError:
                # No running loop - skip async ingestion in sync context
                pass
        except Exception as mem_err:
            logger.warning(f"Failed to ingest task to memory: {mem_err}")

        return task_id
    except Exception as e:
        logger.error(f"Failed to enqueue mac_task: {e}", exc_info=True)
        raise


def get_next_task() -> Optional[Dict[str, Any]]:
    """
    Get the oldest queued mac_task from file-based queue.

    Once returned, move file to in_progress/ directory.

    Returns:
        Task dictionary if available, None otherwise
    """
    try:
        # Find oldest task file
        task_files = sorted(TASKS_DIR.glob("*.json"), key=lambda p: p.stat().st_mtime)

        if not task_files:
            return None

        task_file = task_files[0]

        # Read task
        with open(task_file, "r") as f:
            task_dict = json.load(f)

        # Validate it's a mac_task (safety check)
        task_type = task_dict.get("type", "mac_task")
        if task_type != "mac_task":
            logger.warning(
                f"Found non-mac_task in queue: {task_type}. Skipping. "
                f"Email tasks should use separate routing."
            )
            # Move to completed to avoid reprocessing
            completed_file = COMPLETED_DIR / task_file.name
            shutil.move(str(task_file), str(completed_file))
            return None

        # Move to in_progress
        in_progress_file = IN_PROGRESS_DIR / task_file.name
        shutil.move(str(task_file), str(in_progress_file))

        logger.info(f"Retrieved mac_task {task_dict.get('task_id')} from {task_file.name}")
        return task_dict

    except Exception as e:
        logger.error(f"Error getting next task: {e}", exc_info=True)
        return None


def mark_task_completed(task_id: str):
    """
    Mark a task as completed by moving it to completed/ directory.

    Args:
        task_id: Task ID
    """
    try:
        in_progress_file = IN_PROGRESS_DIR / f"{task_id}.json"
        if in_progress_file.exists():
            completed_file = COMPLETED_DIR / f"{task_id}.json"
            shutil.move(str(in_progress_file), str(completed_file))
            logger.info(f"Marked mac_task {task_id} as completed")
        else:
            logger.warning(f"Task {task_id} not found in in_progress")
    except Exception as e:
        logger.error(f"Error marking task completed: {e}", exc_info=True)


def complete_task(
    task_id: int,
    result: str,
    status: str = "done",
    screenshot_path: Optional[str] = None,
    logs: Optional[List[str]] = None,
) -> Optional[MacTask]:
    """
    Complete a task with result and status (legacy API for backward compatibility).

    Args:
        task_id: Task ID (integer, legacy)
        result: Result string
        status: Status ("done" or "failed")
        screenshot_path: Path to screenshot (V2)
        logs: Execution logs (V2)

    Returns:
        Updated MacTask if found, None otherwise
    """
    with _lock:
        task = _tasks.get(task_id)
        if task:
            task.status = status
            task.result = result
            if screenshot_path:
                task.screenshot_path = screenshot_path
            if logs:
                task.logs = logs
            return task
    return None


def list_tasks() -> List[Dict]:
    """
    List all tasks as dictionaries (legacy support).

    Returns:
        List of task dictionaries
    """
    with _lock:
        return [
            {
                "id": task.id,
                "source": task.source,
                "channel": task.channel,
                "user": task.user,
                "command": task.command,
                "steps": task.steps,
                "attachments": task.attachments,
                "status": task.status,
                "result": task.result,
                "screenshot_path": task.screenshot_path,
                "logs": task.logs,
                "created_at": task.created_at.isoformat(),
            }
            for task in sorted(_tasks.values(), key=lambda t: t.id, reverse=True)
        ]


# Legacy function name for backward compatibility
# This will be deprecated - use enqueue_mac_task_dict instead
def enqueue_task(task_dict: Dict[str, Any]) -> str:
    """
    DEPRECATED: Use enqueue_mac_task_dict() instead.
    
    This function exists for backward compatibility but only accepts mac_task.
    Email tasks must use separate routing.
    """
    return enqueue_mac_task_dict(task_dict)

