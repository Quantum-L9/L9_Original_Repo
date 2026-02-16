"""
Mac Agent API endpoints for polling and reporting task results.
"""

# ============================================================================
__dora_meta__ = {
    "component_name": "Webhook Mac Agent",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2025-12-14T12:48:58Z",
    "updated_at": "2026-01-17T23:47:56Z",
    "layer": "operations",
    "domain": "api_gateway",
    "module_name": "webhook_mac_agent",
    "type": "router",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [
            "GET /tasks/next",
            "POST /tasks/{task_id}/result",
            "GET /tasks",
        ],
        "datasources": ["HTTP API", "Slack API"],
        "memory_layers": ["working_memory"],
        "imported_by": ["api.server", "api.server_memory"],
    },
}
# ============================================================================


import structlog
from fastapi import APIRouter
from pydantic import BaseModel

from api.routes.registry import router_registry
from core.decorators import must_stay_async
from orchestrators.agent_execution.task_queue import (
    complete_task,  # Legacy API for backward compatibility
    get_next_task,
    list_tasks,
    mark_task_completed,
)

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/mac", tags=["mac-agent"])

# Auto-register with RouterRegistry
router_registry.register(
    router=router,
    prefix="",  # Router already has prefix="/mac"
    tags=["mac-agent"],
    module_id="mac_agent_api",
    display_name="Mac Agent API",
)


class TaskResultRequest(BaseModel):
    """Request model for task result submission."""

    result: str
    status: str = "done"
    screenshot_path: str | None = None
    logs: list[str] | None = None


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
@must_stay_async("callers use await")
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
        from core.schemas import PacketEnvelopeIn
        from memory.ingestion import ingest_packet

        # Get task source/user from legacy system if available, otherwise use defaults
        source = task.source if task else "unknown"
        user = task.user if task else "unknown"
        channel = task.channel if task else None

        packet_in = PacketEnvelopeIn(
            packet_type="mac_task_result",
            payload={
                "task_id": task_id,
                "status": payload.status,
                "result": (
                    payload.result[:2000] if payload.result else None
                ),  # Truncate large results
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
            import os

            import httpx

            from api.slack_client import SlackAPIClient

            # Create async client for this call
            slack_bot_token = os.getenv("SLACK_BOT_TOKEN")
            if slack_bot_token:
                async with httpx.AsyncClient() as http_client:
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
                        message_parts.append(
                            f"\n📸 Screenshot: {payload.screenshot_path}"
                        )

                    message = "\n".join(message_parts)
                    if task.channel:
                        await slack_client.post_message(channel=task.channel, text=message)
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


# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "API-OPER-002",
    "governance_level": "medium",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": ["api.slack_client", "core.schemas", "memory.ingestion"],
    "tags": [
        "api",
        "api-gateway",
        "async",
        "debugging",
        "endpoint",
        "http-client",
        "logging",
        "messaging",
        "operations",
        "pydantic",
    ],
    "keywords": ["agent", "mac", "submit", "task", "tasks", "webhook"],
    "business_value": "Implements TaskResultRequest for webhook mac agent functionality",
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
