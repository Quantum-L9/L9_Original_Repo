"""
Mac Agent API endpoints for polling and reporting task results.
"""

import structlog
from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional, List

from orchestrators.agent_execution.task_queue import (
    get_next_task,
    mark_task_completed,
    complete_task,  # Legacy API for backward compatibility
    list_tasks,
)

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/mac", tags=["mac-agent"])


class TaskResultRequest(BaseModel):
    """Request model for task result submission."""

    result: str
    status: str = "done"
    screenshot_path: Optional[str] = None
    logs: Optional[List[str]] = None


@router.get("/tasks/next")
def get_next_mac_task():
    """
    Get the next queued Mac task (file-based system).
    Returns null if no task is available.
    """
    task = get_next_task()
    if task is None:
        return {"task": None}

    # Task is now a dict from file-based system
    # Extract relevant fields
    task_dict = {
        "task_id": task.get("task_id"),
        "type": task.get("type", "mac_task"),
        "status": task.get("status", "queued"),
    }

    # Include metadata
    metadata = task.get("metadata", {})
    if metadata:
        task_dict["source"] = metadata.get("source", "unknown")
        task_dict["channel"] = metadata.get("channel")
        task_dict["user"] = metadata.get("user")

    # Include steps (V2)
    if task.get("steps"):
        task_dict["steps"] = task.get("steps")

    # Include file artifacts if present
    if task.get("artifacts"):
        task_dict["artifacts"] = task.get("artifacts")

    return {"task": task_dict}


@router.post("/tasks/{task_id}/result")
async def submit_task_result(task_id: str, payload: TaskResultRequest):
    """
    Submit the result of a Mac task execution (file-based system).
    If source is "slack" and channel is set, posts result back to Slack.
    Ingests result to memory for audit trail.

    Note: task_id is now a UUID string (file-based system), not an integer.
    """

    # Mark task as completed (file-based system)
    mark_task_completed(task_id)

    # For backward compatibility, try to get task from legacy in-memory system
    # This is for legacy API compatibility only
    task = None
    try:
        task = complete_task(
            int(task_id) if task_id.isdigit() else 0,
            payload.result,
            payload.status,
            screenshot_path=payload.screenshot_path,
            logs=payload.logs,
        )
    except (ValueError, TypeError):
        # task_id is UUID string, not integer - use file-based system only
        pass

    # Ingest task result to memory (audit trail)
    try:
        from memory.ingestion import ingest_packet
        from core.schemas import PacketEnvelopeIn

        # Get task source/user from legacy system if available, otherwise use defaults
        source = task.source if task else "unknown"
        user = task.user if task else "unknown"
        channel = task.channel if task else None

        packet_in = PacketEnvelopeIn(
            packet_type="mac_task_result",
            payload={
                "task_id": task_id,
                "status": payload.status,
                "result": payload.result[:2000]
                if payload.result
                else None,  # Truncate large results
                "has_screenshot": bool(payload.screenshot_path),
                "log_count": len(payload.logs) if payload.logs else 0,
                "source": source,
                "user": user,
            },
            metadata={"agent": "mac_agent", "source": "webhook_mac_agent"},
        )
        await ingest_packet(packet_in)
    except Exception as e:
        logger.warning(f"Failed to ingest task result to memory: {e}")

    # If source is slack and channel is set, post back to Slack
    channel = task.channel if task else None
    if channel:
        try:
            import httpx
            import os
            from api.slack_client import SlackAPIClient

            # Create async client for this call
            slack_bot_token = os.getenv("SLACK_BOT_TOKEN")
            if slack_bot_token:
                http_client = httpx.AsyncClient()
                slack_client = SlackAPIClient(
                    bot_token=slack_bot_token, http_client=http_client
                )

                status_emoji = "✅" if payload.status == "done" else "❌"

                # Build message with enhanced V2 info
                message_parts = [
                    f"{status_emoji} Mac task {task_id} finished with status `{payload.status}`"
                ]

                if payload.logs:
                    # Include last few logs
                    recent_logs = (
                        payload.logs[-5:] if len(payload.logs) > 5 else payload.logs
                    )
                    message_parts.append("\nRecent logs:")
                    for log in recent_logs:
                        message_parts.append(f"  • {log}")

                message_parts.append(
                    f"\n```\n{payload.result[:500]}{'...' if len(payload.result) > 500 else ''}\n```"
                )

                if payload.screenshot_path:
                    message_parts.append(f"\n📸 Screenshot: {payload.screenshot_path}")

                message = "\n".join(message_parts)
                await slack_client.post_message(channel=task.channel, text=message)
                await http_client.aclose()
                logger.info(
                    f"[MAC-AGENT] Posted result for task {task_id} to Slack channel {task.channel}"
                )
        except Exception as e:
            logger.error(f"[MAC-AGENT] Failed to post result to Slack: {e}")
            # Don't fail the request if Slack posting fails

    return {"ok": True}


@router.get("/tasks")
def list_mac_tasks():
    """
    List all Mac tasks (for debugging).
    """
    tasks = list_tasks()
    return {"tasks": tasks}
