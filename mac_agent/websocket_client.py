"""
L9 Mac Agent - WebSocket Client
===============================

Persistent WebSocket client for Mac Agent communication with L9 server.

Features:
- Auto-reconnect with exponential backoff
- AgentHandshake on connect
- Periodic heartbeat loop
- Task event reception and dispatch
- Graceful shutdown handling

Protocol:
1. Connect to wss://<host>/ws/agent
2. Send AgentHandshake JSON
3. Spawn heartbeat + listener tasks
4. Receive EventMessage frames
5. Dispatch TASK_ASSIGNED to executor
6. Send TASK_RESULT back to server

Version: 1.0.0
"""

from __future__ import annotations

import asyncio
import json
import structlog
import os
import platform
import signal
import socket
import sys
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional
from uuid import uuid4

try:
    import websockets
    from websockets.client import WebSocketClientProtocol
    from websockets.exceptions import ConnectionClosedError, ConnectionClosedOK
except ImportError:
    logger.error(
        "ERROR: websockets library required. Install with: pip install websockets"
    )
    sys.exit(1)


logger = structlog.get_logger(__name__)


# =============================================================================
# Configuration
# =============================================================================


@dataclass
class AgentConfig:
    """Configuration for the Mac Agent WebSocket client."""

    # Connection
    ws_url: str = field(
        default_factory=lambda: os.getenv(
            "L9_WS_URL", "wss://l9.quantumaipartners.com/ws/agent"
        )
    )
    agent_id: str = field(
        default_factory=lambda: os.getenv(
            "L9_AGENT_ID", f"mac-agent-{socket.gethostname()}"
        )
    )
    agent_version: str = "1.0.0"

    # Capabilities declared during handshake
    capabilities: List[str] = field(
        default_factory=lambda: [
            "shell",
            "memory_read",
            "memory_write",
            "file_read",
            "file_write",
        ]
    )

    # Timing
    heartbeat_interval: float = 10.0  # seconds
    reconnect_base_delay: float = 1.0  # seconds
    reconnect_max_delay: float = 60.0  # seconds
    reconnect_factor: float = 2.0

    # Limits
    max_reconnect_attempts: int = 0  # 0 = unlimited
    task_timeout: float = 300.0  # 5 minutes

    @classmethod
    def from_env(cls) -> "AgentConfig":
        """Load configuration from environment variables."""
        return cls(
            ws_url=os.getenv("L9_WS_URL", cls.ws_url),
            agent_id=os.getenv("L9_AGENT_ID", f"mac-agent-{socket.gethostname()}"),
            agent_version=os.getenv("L9_AGENT_VERSION", "1.0.0"),
            heartbeat_interval=float(os.getenv("L9_HEARTBEAT_INTERVAL", "10")),
            reconnect_base_delay=float(os.getenv("L9_RECONNECT_BASE_DELAY", "1")),
            reconnect_max_delay=float(os.getenv("L9_RECONNECT_MAX_DELAY", "60")),
        )


# =============================================================================
# Message Types (Standalone - no Pydantic dependency for agent)
# =============================================================================


class EventType:
    """Event type constants matching server EventType enum."""

    HEARTBEAT = "heartbeat"
    TASK_ASSIGNED = "task_assigned"
    TASK_RESULT = "task_result"
    ERROR = "error"
    CONTROL = "control"
    HANDSHAKE = "handshake"
    LOG = "log"


def create_handshake(config: AgentConfig) -> dict:
    """Create AgentHandshake payload."""
    return {
        "agent_id": config.agent_id,
        "agent_version": config.agent_version,
        "capabilities": config.capabilities,
        "hostname": socket.gethostname(),
        "platform": platform.system().lower(),
    }


def create_heartbeat(
    agent_id: str,
    running_tasks: int = 0,
    load_avg: Optional[float] = None,
    memory_usage_mb: Optional[float] = None,
    cpu_percent: Optional[float] = None,
) -> dict:
    """Create EventMessage with HEARTBEAT type."""
    # Get system load if available
    if load_avg is None:
        try:
            load_avg = os.getloadavg()[0]
        except (OSError, AttributeError):
            load_avg = None

    return {
        "type": EventType.HEARTBEAT,
        "agent_id": agent_id,
        "channel": "agent",
        "payload": {
            "running_tasks": running_tasks,
            "load_avg": load_avg,
            "memory_usage_mb": memory_usage_mb,
            "cpu_percent": cpu_percent,
            "timestamp": datetime.utcnow().isoformat(),
        },
    }


def create_task_result(
    agent_id: str,
    task_id: str,
    status: str,
    output: Dict[str, Any],
    error: Optional[str] = None,
    trace_id: Optional[str] = None,
) -> dict:
    """Create EventMessage with TASK_RESULT type."""
    return {
        "type": EventType.TASK_RESULT,
        "agent_id": agent_id,
        "channel": "task",
        "trace_id": trace_id,
        "payload": {
            "task_id": task_id,
            "status": status,
            "result": output,
            "error": error,
            "completed_at": datetime.utcnow().isoformat(),
        },
    }


def create_error_event(
    agent_id: str,
    code: str,
    message: str,
    details: Optional[Dict[str, Any]] = None,
    recoverable: bool = True,
) -> dict:
    """Create EventMessage with ERROR type."""
    return {
        "type": EventType.ERROR,
        "agent_id": agent_id,
        "channel": "agent",
        "payload": {
            "code": code,
            "message": message,
            "details": details or {},
            "recoverable": recoverable,
            "timestamp": datetime.utcnow().isoformat(),
        },
    }


# =============================================================================
# Task Executor
# =============================================================================


class TaskExecutor:
    """
    Task executor for Mac Agent.

    Dispatches tasks to appropriate executors based on task_type:
      - shell: Execute shell commands via LocalAPI or subprocess
      - browser: Playwright-based browser automation
      - python: Sandboxed Python code execution
      - file_read/file_write: File operations
      - memory_read/memory_write: L9 memory substrate operations
    """

    def __init__(self):
        self._running_tasks: Dict[str, asyncio.Task] = {}
        self._task_results: Dict[str, Dict[str, Any]] = {}

    @property
    def running_count(self) -> int:
        """Number of currently running tasks."""
        return len(self._running_tasks)

    async def execute(
        self,
        task_id: str,
        task_type: str,
        payload: Dict[str, Any],
        timeout: float = 300.0,
    ) -> Dict[str, Any]:
        """
        Execute a task and return the result.

        Args:
            task_id: Unique task identifier
            task_type: Type of task (shell, browser, etc.)
            payload: Task parameters
            timeout: Execution timeout in seconds

        Returns:
            Result dictionary with status, output, and error fields
        """
        logger.info("[Executor] Starting task %s: type=%s", task_id, task_type)

        try:
            # Dispatch to real executor based on task_type
            if task_type == "shell":
                result = await self._execute_shell(payload)
            elif task_type == "browser":
                result = await self._execute_browser(payload)
            elif task_type == "python":
                result = await self._execute_python(payload)
            elif task_type == "file_read":
                result = await self._execute_file_read(payload)
            elif task_type == "file_write":
                result = await self._execute_file_write(payload)
            elif task_type == "memory_read":
                result = await self._execute_memory_read(payload)
            elif task_type == "memory_write":
                result = await self._execute_memory_write(payload)
            else:
                # Unknown task type - return error, don't silently succeed
                logger.warning("[Executor] Unknown task type: %s", task_type)
                result = {
                    "status": "error",
                    "output": {},
                    "error": f"Unknown task type: {task_type}. Supported: shell, browser, python, file_read, file_write, memory_read, memory_write",
                }

            logger.info(
                "[Executor] Task %s completed: status=%s", task_id, result.get("status")
            )
            return result

        except asyncio.TimeoutError:
            logger.error("[Executor] Task %s timed out after %ds", task_id, timeout)
            return {
                "status": "failed",
                "output": {},
                "error": f"Task timed out after {timeout}s",
            }
        except Exception as e:
            logger.error("[Executor] Task %s failed: %s", task_id, e)
            return {
                "status": "failed",
                "output": {},
                "error": str(e),
            }

    # Task type executors
    async def _execute_shell(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute shell command with security validation.

        Uses LocalAPI for whitelisted command execution with safety checks.

        Args:
            payload: Dict with:
                - command: Shell command to execute
                - cwd: Working directory (default: /opt/l9)
                - timeout: Execution timeout in seconds (default: 30)

        Returns:
            Result dict with status, output, error, exit_code
        """
        command = payload.get("command", "")
        cwd = payload.get("cwd", "/opt/l9")
        timeout = payload.get("timeout", 30)

        if not command:
            return {
                "status": "error",
                "error": "No command provided",
                "output": "",
                "exit_code": -1,
            }

        try:
            from runtime.local_api import LocalAPI

            api = LocalAPI({"base_path": cwd, "request_timeout": timeout})

            if not api.validate_command(command):
                return {
                    "status": "error",
                    "error": f"Command not allowed: {command.split()[0] if command.split() else 'empty'}",
                    "output": "",
                    "exit_code": -1,
                    "allowed_commands": list(api.ALLOWED_COMMANDS),
                }

            result = api.execute_shell(command, cwd=cwd)
            return {
                "status": "completed" if result["success"] else "failed",
                "output": result["output"],
                "error": result["error"],
                "exit_code": result["exit_code"],
            }
        except ImportError:
            # Fallback to subprocess if LocalAPI not available
            import subprocess
            import shlex

            logger.warning("LocalAPI not available, using subprocess fallback")
            try:
                cmd_parts = shlex.split(command)
                result = subprocess.run(
                    cmd_parts,
                    cwd=cwd,
                    capture_output=True,
                    text=True,
                    timeout=timeout,
                    check=False,
                )
                return {
                    "status": "completed" if result.returncode == 0 else "failed",
                    "output": result.stdout,
                    "error": result.stderr,
                    "exit_code": result.returncode,
                }
            except subprocess.TimeoutExpired:
                return {
                    "status": "failed",
                    "error": "Command timeout",
                    "output": "",
                    "exit_code": -1,
                }
            except Exception as e:
                return {
                    "status": "error",
                    "error": str(e),
                    "output": "",
                    "exit_code": -1,
                }
        except Exception as e:
            logger.error(f"Shell execution error: {e}")
            return {"status": "error", "error": str(e), "output": "", "exit_code": -1}

    async def _execute_browser(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute browser automation via Playwright.

        Uses AutomationExecutor for step-based browser control.

        Args:
            payload: Dict with:
                - steps: List of automation steps (goto, click, fill, etc.)
                - headless: Whether to run headless (default: False)
                - task_id: Task ID for screenshot organization

        Returns:
            Result dict with status, logs, screenshots, data
        """
        steps = payload.get("steps", [])
        headless = payload.get("headless", False)
        task_id = payload.get("task_id", str(uuid4()))

        if not steps:
            return {
                "status": "error",
                "error": "No steps provided",
                "logs": [],
                "screenshots": [],
            }

        try:
            from mac_agent.executor import AutomationExecutor

            executor = AutomationExecutor()

            result = await executor.run_steps(steps, headless=headless, task_id=task_id)

            return {
                "status": "completed" if result["status"] == "success" else "failed",
                "output": {
                    "logs": result.get("logs", []),
                    "screenshots": result.get("screenshots", []),
                    "data": result.get("data", {}),
                    "started_at": result.get("started_at"),
                    "finished_at": result.get("finished_at"),
                },
                "error": result.get("data", {}).get("error"),
            }
        except ImportError as e:
            return {
                "status": "error",
                "error": f"Playwright not available: {e}. Install with: pip install playwright && playwright install",
                "logs": [],
                "screenshots": [],
            }
        except Exception as e:
            logger.error(f"Browser execution error: {e}")
            return {"status": "error", "error": str(e), "logs": [], "screenshots": []}

    async def _execute_python(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute Python code in a sandboxed environment.

        For production: Uses Docker container with network disabled.
        For development: Falls back to subprocess with minimal env.

        Args:
            payload: Dict with:
                - code: Python code to execute
                - timeout: Execution timeout in seconds (default: 30)
                - use_docker: Force Docker execution (default: True in production)

        Returns:
            Result dict with status, output, error, exit_code
        """
        import subprocess
        import tempfile
        import os as os_module

        code = payload.get("code", "")
        timeout = payload.get("timeout", 30)
        use_docker = payload.get("use_docker", True)

        if not code:
            return {
                "status": "error",
                "error": "No code provided",
                "output": "",
                "exit_code": -1,
            }

        # Try Docker execution first (more secure)
        if use_docker:
            try:
                import docker

                client = docker.from_env()

                # Create container with security restrictions
                container = client.containers.run(
                    "python:3.11-slim",
                    command=["python", "-c", code],
                    detach=True,
                    network_disabled=True,
                    mem_limit="128m",
                    cpu_period=100000,
                    cpu_quota=50000,  # 50% of one CPU
                    remove=True,
                )

                # Wait for completion with timeout
                try:
                    result = container.wait(timeout=timeout)
                    logs = container.logs(stdout=True, stderr=True).decode("utf-8")
                    exit_code = result.get("StatusCode", -1)

                    return {
                        "status": "completed" if exit_code == 0 else "failed",
                        "output": logs,
                        "error": "" if exit_code == 0 else logs,
                        "exit_code": exit_code,
                        "executor": "docker",
                    }
                except Exception as wait_error:
                    container.kill()
                    return {
                        "status": "failed",
                        "error": f"Container timeout: {wait_error}",
                        "output": "",
                        "exit_code": -1,
                    }

            except ImportError:
                logger.warning("Docker SDK not available, falling back to subprocess")
            except Exception as docker_error:
                logger.warning(
                    f"Docker execution failed: {docker_error}, falling back to subprocess"
                )

        # Fallback: subprocess with restricted environment (less secure)
        logger.warning(
            "Using subprocess fallback for Python execution - less secure than Docker"
        )

        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(code)
            temp_path = f.name

        try:
            result = subprocess.run(
                ["python3", temp_path],
                capture_output=True,
                text=True,
                timeout=timeout,
                env={"PATH": "/usr/bin:/bin", "HOME": "/tmp"},  # Minimal env
                cwd="/tmp",
            )
            return {
                "status": "completed" if result.returncode == 0 else "failed",
                "output": result.stdout,
                "error": result.stderr,
                "exit_code": result.returncode,
                "executor": "subprocess",
                "warning": "Executed without Docker sandbox - less secure",
            }
        except subprocess.TimeoutExpired:
            return {
                "status": "failed",
                "error": "Execution timeout",
                "output": "",
                "exit_code": -1,
            }
        except Exception as e:
            return {"status": "error", "error": str(e), "output": "", "exit_code": -1}
        finally:
            try:
                os_module.unlink(temp_path)
            except Exception:
                pass


# =============================================================================
# Mac Agent WebSocket Client
# =============================================================================


class MacAgentClient:
    """
    Persistent WebSocket client for L9 Mac Agent.

    Maintains connection to L9 server with:
    - Automatic reconnection with exponential backoff
    - Heartbeat loop for health monitoring
    - Task reception and execution
    - Graceful shutdown handling

    Usage:
        config = AgentConfig.from_env()
        client = MacAgentClient(config)
        await client.run()
    """

    def __init__(self, config: Optional[AgentConfig] = None):
        """
        Initialize the Mac Agent client.

        Args:
            config: Agent configuration (defaults to AgentConfig.from_env())
        """
        self.config = config or AgentConfig.from_env()
        self.executor = TaskExecutor()

        # Connection state
        self._ws: Optional[WebSocketClientProtocol] = None
        self._connected = False
        self._reconnect_count = 0

        # Task management
        self._running = False
        self._shutdown_event = asyncio.Event()
        self._tasks: Dict[str, asyncio.Task] = {}

        # Callbacks
        self._on_connect_callbacks: List[Callable] = []
        self._on_disconnect_callbacks: List[Callable] = []
        self._on_task_callbacks: List[Callable] = []

    # =========================================================================
    # Public API
    # =========================================================================

    async def run(self) -> None:
        """
        Run the agent client with automatic reconnection.

        This is the main entry point. Call this to start the agent.
        It will run until shutdown() is called or the process is terminated.
        """
        self._running = True
        self._setup_signal_handlers()

        logger.info(
            "[MacAgent] Starting: agent_id=%s, url=%s",
            self.config.agent_id,
            self.config.ws_url,
        )

        delay = self.config.reconnect_base_delay

        while self._running:
            try:
                await self._connect_and_run()

                # If we get here cleanly, reset backoff
                delay = self.config.reconnect_base_delay
                self._reconnect_count = 0

            except (ConnectionClosedError, ConnectionClosedOK) as e:
                logger.warning("[MacAgent] Connection closed: %s", e)
            except Exception as e:
                logger.error("[MacAgent] Connection error: %s", e)

            if not self._running:
                break

            # Check reconnect limit
            if (
                self.config.max_reconnect_attempts > 0
                and self._reconnect_count >= self.config.max_reconnect_attempts
            ):
                logger.error(
                    "[MacAgent] Max reconnect attempts (%d) reached, stopping",
                    self.config.max_reconnect_attempts,
                )
                break

            # Backoff before reconnecting
            self._reconnect_count += 1
            logger.info(
                "[MacAgent] Reconnecting in %.1fs (attempt %d)...",
                delay,
                self._reconnect_count,
            )

            try:
                await asyncio.wait_for(self._shutdown_event.wait(), timeout=delay)
                # Shutdown requested during wait
                break
            except asyncio.TimeoutError:
                pass

            # Exponential backoff
            delay = min(
                delay * self.config.reconnect_factor, self.config.reconnect_max_delay
            )

        logger.info("[MacAgent] Stopped")

    async def shutdown(self) -> None:
        """
        Gracefully shutdown the agent.

        Cancels all running tasks and closes the WebSocket connection.
        """
        logger.info("[MacAgent] Shutdown requested")
        self._running = False
        self._shutdown_event.set()

        # Cancel running tasks
        for task_id, task in self._tasks.items():
            if not task.done():
                logger.info("[MacAgent] Cancelling task %s", task_id)
                task.cancel()

        # Close WebSocket
        if self._ws and not self._ws.closed:
            await self._ws.close(code=1000, reason="Agent shutdown")

        self._connected = False

    @property
    def is_connected(self) -> bool:
        """Check if currently connected to server."""
        return self._connected and self._ws is not None and not self._ws.closed

    # =========================================================================
    # Connection Management
    # =========================================================================

    async def _connect_and_run(self) -> None:
        """Establish connection and run event loops."""
        async with websockets.connect(
            self.config.ws_url,
            ping_interval=20,
            ping_timeout=20,
            close_timeout=10,
        ) as ws:
            self._ws = ws
            self._connected = True

            logger.info("[MacAgent] Connected to %s", self.config.ws_url)

            # Send handshake
            await self._send_handshake()

            # Notify callbacks
            for callback in self._on_connect_callbacks:
                try:
                    await callback() if asyncio.iscoroutinefunction(
                        callback
                    ) else callback()
                except Exception as e:
                    logger.error("[MacAgent] Connect callback error: %s", e)

            # Run heartbeat and listener concurrently
            listener_task = asyncio.create_task(self._message_listener())
            heartbeat_task = asyncio.create_task(self._heartbeat_loop())

            try:
                # Wait for either to complete (usually due to disconnect)
                done, pending = await asyncio.wait(
                    [listener_task, heartbeat_task],
                    return_when=asyncio.FIRST_COMPLETED,
                )

                # Cancel the other task
                for task in pending:
                    task.cancel()
                    try:
                        await task
                    except asyncio.CancelledError:
                        pass

                # Re-raise any exception from completed task
                for task in done:
                    if task.exception():
                        raise task.exception()

            finally:
                self._connected = False

                # Notify disconnect callbacks
                for callback in self._on_disconnect_callbacks:
                    try:
                        await callback() if asyncio.iscoroutinefunction(
                            callback
                        ) else callback()
                    except Exception as e:
                        logger.error("[MacAgent] Disconnect callback error: %s", e)

    async def _send_handshake(self) -> None:
        """Send AgentHandshake to server."""
        handshake = create_handshake(self.config)

        logger.info(
            "[MacAgent] Sending handshake: agent_id=%s, capabilities=%s",
            handshake["agent_id"],
            handshake["capabilities"],
        )

        await self._ws.send(json.dumps(handshake))

    # =========================================================================
    # Message Handling
    # =========================================================================

    async def _message_listener(self) -> None:
        """Listen for incoming messages from server."""
        logger.info("[MacAgent] Message listener started")

        async for message in self._ws:
            if not self._running:
                break

            try:
                data = json.loads(message)
                await self._handle_message(data)
            except json.JSONDecodeError as e:
                logger.error("[MacAgent] Invalid JSON received: %s", e)
            except Exception as e:
                logger.error("[MacAgent] Message handling error: %s", e)

    async def _handle_message(self, data: Dict[str, Any]) -> None:
        """
        Handle an incoming EventMessage from server.

        Args:
            data: Parsed JSON payload
        """
        event_type = data.get("type")

        if event_type == EventType.TASK_ASSIGNED:
            await self._handle_task_assigned(data)
        elif event_type == EventType.CONTROL:
            await self._handle_control(data)
        elif event_type == EventType.ERROR:
            await self._handle_error(data)
        else:
            logger.debug("[MacAgent] Received event: type=%s", event_type)

    async def _handle_task_assigned(self, data: Dict[str, Any]) -> None:
        """Handle TASK_ASSIGNED event from server."""
        payload = data.get("payload", {})
        task_id = payload.get("task_id", str(uuid4()))
        task_type = payload.get("task_type", "unknown")
        task_payload = payload.get("task_payload", payload)
        trace_id = data.get("trace_id")

        logger.info("[MacAgent] Task assigned: id=%s, type=%s", task_id, task_type)

        # Notify callbacks
        for callback in self._on_task_callbacks:
            try:
                await callback(data) if asyncio.iscoroutinefunction(
                    callback
                ) else callback(data)
            except Exception as e:
                logger.error("[MacAgent] Task callback error: %s", e)

        # Execute task asynchronously
        task = asyncio.create_task(
            self._execute_and_report(task_id, task_type, task_payload, trace_id)
        )
        self._tasks[task_id] = task

        # Cleanup when done
        task.add_done_callback(lambda t: self._tasks.pop(task_id, None))

    async def _execute_and_report(
        self,
        task_id: str,
        task_type: str,
        payload: Dict[str, Any],
        trace_id: Optional[str],
    ) -> None:
        """Execute task and send result back to server."""
        try:
            result = await asyncio.wait_for(
                self.executor.execute(task_id, task_type, payload),
                timeout=self.config.task_timeout,
            )

            # Send result back to server
            result_event = create_task_result(
                agent_id=self.config.agent_id,
                task_id=task_id,
                status=result.get("status", "completed"),
                output=result.get("output", {}),
                error=result.get("error"),
                trace_id=trace_id,
            )

            await self._send(result_event)

        except asyncio.TimeoutError:
            error_event = create_task_result(
                agent_id=self.config.agent_id,
                task_id=task_id,
                status="failed",
                output={},
                error=f"Task timed out after {self.config.task_timeout}s",
                trace_id=trace_id,
            )
            await self._send(error_event)

        except Exception as e:
            logger.error("[MacAgent] Task %s execution failed: %s", task_id, e)
            error_event = create_task_result(
                agent_id=self.config.agent_id,
                task_id=task_id,
                status="failed",
                output={},
                error=str(e),
                trace_id=trace_id,
            )
            await self._send(error_event)

    async def _handle_control(self, data: Dict[str, Any]) -> None:
        """Handle CONTROL event from server."""
        payload = data.get("payload", {})
        action = payload.get("action")

        logger.info("[MacAgent] Control event: action=%s", action)

        if action == "shutdown":
            await self.shutdown()
        elif action == "pause":
            logger.info("[MacAgent] Pausing (not implemented)")
        elif action == "resume":
            logger.info("[MacAgent] Resuming (not implemented)")
        else:
            logger.warning("[MacAgent] Unknown control action: %s", action)

    async def _handle_error(self, data: Dict[str, Any]) -> None:
        """Handle ERROR event from server."""
        payload = data.get("payload", {})
        code = payload.get("code", "UNKNOWN")
        message = payload.get("message", "No message")

        logger.error("[MacAgent] Server error: code=%s, message=%s", code, message)

    # =========================================================================
    # Heartbeat
    # =========================================================================

    async def _heartbeat_loop(self) -> None:
        """Send periodic heartbeats to server."""
        logger.info(
            "[MacAgent] Heartbeat loop started (interval=%ds)",
            self.config.heartbeat_interval,
        )

        while self._running and self._connected:
            try:
                heartbeat = create_heartbeat(
                    agent_id=self.config.agent_id,
                    running_tasks=self.executor.running_count,
                )

                await self._send(heartbeat)
                logger.debug("[MacAgent] Heartbeat sent")

            except Exception as e:
                logger.error("[MacAgent] Heartbeat error: %s", e)
                raise

            # Wait for next heartbeat or shutdown
            try:
                await asyncio.wait_for(
                    self._shutdown_event.wait(), timeout=self.config.heartbeat_interval
                )
                # Shutdown requested
                break
            except asyncio.TimeoutError:
                pass

    # =========================================================================
    # Utilities
    # =========================================================================

    async def _send(self, data: Dict[str, Any]) -> None:
        """Send JSON data to server."""
        if self._ws and not self._ws.closed:
            await self._ws.send(json.dumps(data, default=str))
        else:
            logger.warning("[MacAgent] Cannot send: not connected")

    def _setup_signal_handlers(self) -> None:
        """Setup graceful shutdown on SIGINT/SIGTERM."""
        loop = asyncio.get_running_loop()

        for sig in (signal.SIGINT, signal.SIGTERM):
            try:
                loop.add_signal_handler(
                    sig, lambda: asyncio.create_task(self.shutdown())
                )
            except NotImplementedError:
                # Windows doesn't support add_signal_handler
                pass

    # =========================================================================
    # Callbacks
    # =========================================================================

    def on_connect(self, callback: Callable) -> None:
        """Register callback for connection events."""
        self._on_connect_callbacks.append(callback)

    def on_disconnect(self, callback: Callable) -> None:
        """Register callback for disconnection events."""
        self._on_disconnect_callbacks.append(callback)

    def on_task(self, callback: Callable) -> None:
        """Register callback for task events."""
        self._on_task_callbacks.append(callback)


# =============================================================================
# CLI Entry Point
# =============================================================================


async def main():
    """Run the Mac Agent client."""
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Reduce noise from websockets library
    logging.getLogger("websockets").setLevel(logging.WARNING)

    # Load config and run
    config = AgentConfig.from_env()
    client = MacAgentClient(config)

    # Example: register callbacks
    client.on_connect(lambda: logger.info("=== CONNECTED ==="))
    client.on_disconnect(lambda: logger.info("=== DISCONNECTED ==="))

    await client.run()


if __name__ == "__main__":
    asyncio.run(main())
