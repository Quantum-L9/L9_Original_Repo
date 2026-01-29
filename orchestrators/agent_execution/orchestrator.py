"""
L9 Agent Execution Orchestrator - Implementation
Version: 1.0.0

Orchestrates Mac Agent task execution from file-based queue.
ONLY handles mac_task types - email tasks are handled separately.
"""

# ============================================================================
__dora_meta__ = {
    "component_name": "Implementation",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2026-01-08T15:53:43Z",
    "updated_at": "2026-01-17T23:47:56Z",
    "layer": "intelligence",
    "domain": "orchestration",
    "module_name": "orchestrator",
    "type": "service",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": ["Slack API"],
        "memory_layers": [],
        "imported_by": [],
    },
}
# ============================================================================

import asyncio
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import aiofiles
import structlog

from .interface import (
    AgentExecutionRequest,
    AgentExecutionResponse,
    IAgentExecutionOrchestrator,
    TaskExecutionStatus,
)
from .task_queue import get_next_task, mark_task_completed

logger = structlog.get_logger(__name__)

# Check if Mac Agent is enabled
try:
    from config.settings import settings

    MAC_AGENT_ENABLED = settings.mac_agent_enabled
except ImportError:
    MAC_AGENT_ENABLED = os.getenv("MAC_AGENT_ENABLED", "true").lower() == "true"

# Import pyautogui for desktop screenshots on failure
try:
    import pyautogui

    PYTHON_AUTOGUI_AVAILABLE = True
except ImportError:
    PYTHON_AUTOGUI_AVAILABLE = False
    logger.warning("pyautogui not available - desktop screenshots disabled")


class AgentExecutionOrchestrator(IAgentExecutionOrchestrator):
    """
    Agent Execution Orchestrator implementation.

    Polls file-based queue and executes Mac Agent tasks only.
    Email tasks are handled by separate email task orchestrator.
    """

    def __init__(self):
        """Initialize agent execution orchestrator."""
        # Add parent directory to path to import services
        parent_dir = os.path.dirname(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        )
        if parent_dir not in sys.path:
            sys.path.insert(0, parent_dir)

        try:
            from api.slack_client import post_result_async
            from mac_agent.executor import AutomationExecutor

            self._post_result_async = post_result_async
            self._AutomationExecutor = AutomationExecutor
            logger.info("AgentExecutionOrchestrator initialized")
        except ImportError as e:
            logger.warning(f"Some dependencies not available: {e}")
            self._post_result_async = None
            self._AutomationExecutor = None

    async def execute(self, request: AgentExecutionRequest) -> AgentExecutionResponse:
        """
        Execute a Mac Agent task.

        Args:
            request: AgentExecutionRequest with task details

        Returns:
            AgentExecutionResponse with execution result
        """
        if request.task_type != "mac_task":
            return AgentExecutionResponse(
                success=False,
                status=TaskExecutionStatus.FAILED,
                error=f"AgentExecutionOrchestrator only handles mac_task, got: {request.task_type}",
                task_id=request.task_id,
            )

        if not self._AutomationExecutor:
            return AgentExecutionResponse(
                success=False,
                status=TaskExecutionStatus.FAILED,
                error="AutomationExecutor not available",
                task_id=request.task_id,
            )

        try:
            executor = self._AutomationExecutor()
            result = await executor.run_steps(
                request.steps, headless=False, task_id=request.task_id
            )

            # If execution failed and no screenshots, take desktop screenshot
            if result.get("status") == "error" and not result.get("screenshots"):
                if PYTHON_AUTOGUI_AVAILABLE:
                    try:
                        screenshot_dir = Path(
                            os.path.expanduser(
                                f"~/.l9/mac_tasks/screenshots/{request.task_id}"
                            )
                        )
                        screenshot_dir.mkdir(parents=True, exist_ok=True)
                        desktop_screenshot = (
                            screenshot_dir / f"desktop_error_{int(time.time())}.png"
                        )
                        pyautogui.screenshot(str(desktop_screenshot))
                        result["screenshots"] = [str(desktop_screenshot)]
                        result["screenshot_path"] = str(desktop_screenshot)
                        logger.info(
                            f"Captured desktop screenshot: {desktop_screenshot}"
                        )
                    except Exception as e:
                        logger.error(f"Failed to capture desktop screenshot: {e}")

            status = (
                TaskExecutionStatus.COMPLETED
                if result.get("status") == "success"
                else TaskExecutionStatus.FAILED
            )

            return AgentExecutionResponse(
                success=result.get("status") == "success",
                status=status,
                result=result,
                task_id=request.task_id,
            )

        except Exception as e:
            logger.error(f"Task execution failed: {e}", exc_info=True)
            return AgentExecutionResponse(
                success=False,
                status=TaskExecutionStatus.FAILED,
                error=str(e),
                task_id=request.task_id,
            )

    async def poll_and_execute(self) -> None:
        """
        Main polling loop (file-based task system).

        Polls queue every 3 seconds and executes mac_task types only.
        Email tasks are handled separately and should not appear in this queue.
        """
        if not MAC_AGENT_ENABLED:
            logger.info("Mac Agent is disabled (MAC_AGENT_ENABLED=false). Exiting.")
            return

        logger.info(
            "Agent Execution Orchestrator starting. Polling file-based task queue every 3 seconds"
        )

        while True:
            task = None
            task_id = None
            try:
                # Get next task from file-based queue
                task = get_next_task()

                if not task:
                    # No task available, sleep and continue
                    await asyncio.sleep(3)
                    continue

                task_id = task.get("task_id", "unknown")
                steps = task.get("steps", [])
                task_type = task.get("type", "mac_task")

                # Safety check: Only process mac_task
                if task_type != "mac_task":
                    logger.warning(
                        f"Found non-mac_task in queue: {task_type}. "
                        f"Email tasks should use separate routing. Skipping."
                    )
                    mark_task_completed(task_id)
                    await asyncio.sleep(3)
                    continue

                logger.info(
                    f"[Agent Execution] Executing mac_task {task_id} with {len(steps)} steps."
                )

                if not steps:
                    logger.warning(f"Task {task_id} has no steps, skipping")
                    mark_task_completed(task_id)
                    continue

                # Execute Mac automation task
                request = AgentExecutionRequest(
                    task_id=task_id,
                    task_type=task_type,
                    steps=steps,
                    metadata=task.get("metadata", {}),
                    artifacts=task.get("artifacts"),
                )

                response = await self.execute(request)

                # Post result back to Slack (async)
                if self._post_result_async and response.result:
                    try:
                        metadata = task.get("metadata", {})
                        user = metadata.get("user")
                        channel = metadata.get("channel", user)

                        if user or channel:
                            await self._post_result_async(
                                channel or user, task, response.result
                            )
                            logger.info(f"Posted result for task {task_id} to Slack")
                        else:
                            logger.warning(
                                f"No user/channel in task {task_id} metadata, skipping Slack post"
                            )
                    except Exception as e:
                        logger.error(
                            f"Failed to post result to Slack for task {task_id}: {e}",
                            exc_info=True,
                        )

                # Mark task as completed
                mark_task_completed(task_id)
                logger.info(
                    f"Task {task_id} completed with status: {response.status.value}"
                )

            except KeyboardInterrupt:
                logger.info("Agent Execution Orchestrator stopped by user")
                break
            except Exception as e:
                # Isolate errors per task - never crash the loop
                logger.error(
                    f"Unexpected error processing task {task_id if task_id else 'unknown'}: {e}",
                    exc_info=True,
                )

                # Try to save failure state if we have a task
                if task_id and task:
                    try:
                        failure_result = {
                            "status": "error",
                            "logs": [
                                {
                                    "step": 0,
                                    "action": "orchestrator_error",
                                    "status": "error",
                                    "details": str(e),
                                    "timestamp": datetime.now(timezone.utc).isoformat(),
                                }
                            ],
                            "screenshots": [],
                            "data": {"error": f"Orchestrator error: {e!s}"},
                        }

                        # Take desktop screenshot if possible
                        if PYTHON_AUTOGUI_AVAILABLE:
                            try:
                                screenshot_dir = Path(
                                    os.path.expanduser(
                                        f"~/.l9/mac_tasks/screenshots/{task_id}"
                                    )
                                )
                                screenshot_dir.mkdir(parents=True, exist_ok=True)
                                desktop_screenshot = (
                                    screenshot_dir
                                    / f"desktop_crash_{int(time.time())}.png"
                                )
                                pyautogui.screenshot(str(desktop_screenshot))
                                failure_result["screenshots"] = [
                                    str(desktop_screenshot)
                                ]
                            except Exception:
                                pass

                        # Try to post failure to Slack
                        if self._post_result:
                            try:
                                metadata = task.get("metadata", {})
                                channel = metadata.get("channel", metadata.get("user"))
                                if channel:
                                    self._post_result(channel, task, failure_result)
                            except Exception:
                                pass

                        # Save failure JSON
                        try:
                            completed_file = Path(
                                os.path.expanduser(
                                    f"~/.l9/mac_tasks/completed/{task_id}.json"
                                )
                            )
                            async with aiofiles.open(completed_file, "w") as f:
                                await f.write(
                                    json.dumps(
                                        {"task": task, "result": failure_result},
                                        indent=2,
                                    )
                                )
                        except Exception:
                            pass

                        mark_task_completed(task_id)
                    except Exception as inner_e:
                        logger.error(f"Failed to save failure state: {inner_e}")

                await asyncio.sleep(3)


async def main():
    """Entry point for orchestrator."""
    orchestrator = AgentExecutionOrchestrator()
    await orchestrator.poll_and_execute()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Agent Execution Orchestrator stopped by user")
        sys.exit(0)

# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "ORC-INTE-029",
    "governance_level": "high",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": ["api.slack_client"],
    "tags": [
        "api",
        "async",
        "filesystem",
        "intelligence",
        "logging",
        "orchestration",
        "queue",
        "serialization",
        "service",
    ],
    "keywords": [
        "agent",
        "execute",
        "execution",
        "implementation",
        "orchestrator",
        "poll",
        "queue",
    ],
    "business_value": "Orchestrates Mac Agent task execution from file-based queue. ONLY handles mac_task types - email tasks are handled separately.",
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
