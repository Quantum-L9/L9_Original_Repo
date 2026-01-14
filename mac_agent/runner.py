#!/usr/bin/env python3
"""
Mac Agent Runner V2
Polls L9 for Mac automation tasks and executes them using Playwright.
"""

import os
import sys
import time
import asyncio
import logging
import subprocess
import structlog
import json
from pathlib import Path
from datetime import datetime

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = structlog.get_logger(__name__)

# Check if Mac Agent is enabled
try:
    from config.settings import settings

    if not settings.mac_agent_enabled:
        logger.info("Mac Agent is disabled (MAC_AGENT_ENABLED=false). Exiting.")
        sys.exit(0)
except ImportError:
    # If settings can't be imported, check env var directly
    if os.getenv("MAC_AGENT_ENABLED", "true").lower() != "true":
        logger.info("Mac Agent is disabled (MAC_AGENT_ENABLED=false). Exiting.")
        sys.exit(0)

from mac_agent.config import get_config
from mac_agent.executor import AutomationExecutor

config = get_config()
L9_BASE_URL = config.l9_base_url
L9_API_KEY = config.l9_api_key
POLL_INTERVAL = 4  # seconds


def execute_command(command: str) -> tuple[str, str]:
    """
    Execute a shell command locally (legacy support).

    Returns:
        Tuple of (result_string, status)
        status is "done" on success, "failed" on error
    """
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=300,  # 5 minute timeout
        )

        if result.returncode == 0:
            output = result.stdout.strip() if result.stdout.strip() else "(no output)"
            return output, "done"
        else:
            error_msg = (
                result.stderr.strip()
                if result.stderr.strip()
                else result.stdout.strip()
            )
            output = (
                f"Exit code: {result.returncode}\n{error_msg}"
                if error_msg
                else f"Exit code: {result.returncode}"
            )
            return output, "failed"
    except subprocess.TimeoutExpired:
        return "Command timed out after 5 minutes", "failed"
    except Exception as e:
        return f"Execution error: {str(e)}", "failed"


async def execute_steps(task: dict) -> dict:
    """
    Execute automation steps using Playwright.

    Args:
        task: Task dictionary with 'steps' field

    Returns:
        Result dictionary with status, logs, screenshot_path, data
    """
    steps = task.get("steps", [])
    if not steps:
        return {
            "status": "error",
            "logs": ["No steps provided"],
            "screenshot_path": None,
            "data": {"error": "No steps provided"},
        }

    executor = AutomationExecutor()
    headless = task.get("headless")  # Allow per-task override
    return await executor.run_steps(steps, headless=headless)


def format_result(result: dict) -> str:
    """Format execution result as string for API."""
    status = result.get("status", "unknown")
    logs = result.get("logs", [])
    screenshot_path = result.get("screenshot_path")
    data = result.get("data", {})

    lines = [f"Status: {status}"]
    lines.append("\nLogs:")
    for log in logs:
        lines.append(f"  {log}")

    if screenshot_path:
        lines.append(f"\nScreenshot: {screenshot_path}")

    if data:
        lines.append("\nData:")
        lines.append(json.dumps(data, indent=2))

    return "\n".join(lines)


async def poll_and_execute():
    """Main polling loop (file-based task system)."""
    logger.info(
        "Mac Agent V2 runner starting. Polling file-based task queue every 3 seconds"
    )

    # Import here to avoid circular dependencies
    # Add parent directory to path to import services
    parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if parent_dir not in sys.path:
        sys.path.insert(0, parent_dir)

    from orchestrators.agent_execution.task_queue import get_next_task, mark_task_completed
    from services.slack_client import post_result
    from mac_agent.executor import AutomationExecutor

    # Import pyautogui for desktop screenshots on failure
    try:
        import pyautogui

        PYTHON_AUTOGUI_AVAILABLE = True
    except ImportError:
        PYTHON_AUTOGUI_AVAILABLE = False
        logger.warning("pyautogui not available - desktop screenshots disabled")

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

            logger.info(
                f"[L9 Mac Agent] Executing task {task_id} with {len(steps)} steps."
            )
            logger.info(f"Received task {task_id} with {len(steps)} steps")

            if not steps:
                logger.warning(f"Task {task_id} has no steps, skipping")
                mark_task_completed(task_id)
                continue

            # Check task type and execute accordingly
            task_type = task.get("type", "mac_task")

            if task_type == "email_task":
                # Execute email task
                try:
                    parent_dir = os.path.dirname(
                        os.path.dirname(os.path.abspath(__file__))
                    )
                    if parent_dir not in sys.path:
                        sys.path.insert(0, parent_dir)

                    from email_agent.client import execute_email_task

                    result = execute_email_task(task)
                    logger.info(f"Executed email task {task_id}")
                except Exception as e:
                    logger.error(f"Email task execution failed: {e}", exc_info=True)
                    result = {
                        "status": "error",
                        "logs": [
                            {
                                "step": 0,
                                "action": "email_task",
                                "status": "error",
                                "details": str(e),
                                "timestamp": datetime.utcnow().isoformat(),
                            }
                        ],
                        "screenshots": [],
                        "data": {"error": str(e)},
                    }
            else:
                # Execute Mac automation task (visible browser - headless=False)
                executor = AutomationExecutor()
                result = await executor.run_steps(
                    steps, headless=False, task_id=task_id
                )

            # If execution failed and no screenshots, take desktop screenshot
            if result.get("status") == "error" and not result.get("screenshots"):
                if PYTHON_AUTOGUI_AVAILABLE:
                    try:
                        screenshot_dir = Path(
                            os.path.expanduser(f"~/.l9/mac_tasks/screenshots/{task_id}")
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

            # Post result back to Slack
            try:
                metadata = task.get("metadata", {})
                user = metadata.get("user")
                channel = metadata.get(
                    "channel", user
                )  # Fallback to user if no channel

                if user or channel:
                    post_result(channel or user, task, result)
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
            logger.info(f"Task {task_id} completed with status: {result.get('status')}")

        except KeyboardInterrupt:
            logger.info("Mac Agent runner stopped by user")
            sys.exit(0)
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
                                "action": "runner_error",
                                "status": "error",
                                "details": str(e),
                                "timestamp": datetime.utcnow().isoformat(),
                            }
                        ],
                        "screenshots": [],
                        "data": {"error": f"Runner error: {str(e)}"},
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
                                screenshot_dir / f"desktop_crash_{int(time.time())}.png"
                            )
                            pyautogui.screenshot(str(desktop_screenshot))
                            failure_result["screenshots"] = [str(desktop_screenshot)]
                        except Exception:
                            pass

                    # Try to post failure to Slack
                    try:
                        metadata = task.get("metadata", {})
                        channel = metadata.get("channel", metadata.get("user"))
                        if channel:
                            post_result(channel, task, failure_result)
                    except Exception:
                        pass

                    # Save failure JSON
                    try:
                        completed_file = Path(
                            os.path.expanduser(
                                f"~/.l9/mac_tasks/completed/{task_id}.json"
                            )
                        )
                        with open(completed_file, "w") as f:
                            json.dump(
                                {"task": task, "result": failure_result}, f, indent=2
                            )
                    except Exception:
                        pass

                    mark_task_completed(task_id)
                except Exception as inner_e:
                    logger.error(f"Failed to save failure state: {inner_e}")

            await asyncio.sleep(3)


def main():
    """Entry point."""
    try:
        asyncio.run(poll_and_execute())
    except KeyboardInterrupt:
        logger.info("Mac Agent runner stopped by user")
        sys.exit(0)


if __name__ == "__main__":
    main()
