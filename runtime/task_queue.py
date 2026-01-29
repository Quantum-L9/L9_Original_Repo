"""
L9 Runtime - Task Queue
========================

Production task queue with Redis backend enforcement.

Used by ws_bridge and orchestrators to enqueue work items
that are processed by the unified controller.

Version: 2.0.0 (Redis support)

Note: Redis is mandatory; missing Redis blocks async execution.
"""

from __future__ import annotations

# ============================================================================
__dora_meta__ = {
    "component_name": "Task Queue",
    "module_version": "2.0.0 (Redis support)",
    "created_by": "Igor Beylin",
    "created_at": "2025-12-21T00:00:34Z",
    "updated_at": "2026-01-07T13:35:58Z",
    "layer": "operations",
    "domain": "runtime_operations",
    "module_name": "task_queue",
    "type": "dataclass",
    "status": "production",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": ["Redis"],
        "memory_layers": [],
        "imported_by": [
            "core.agents.executor",
            "core.tools.base_registry",
            "orchestrators.ws_bridge",
            "runtime.__init__",
            "runtime.git_tool",
            "runtime.gmp_tool",
            "runtime.gmp_worker",
            "runtime.l_tools",
            "runtime.long_plan_tool",
            "runtime.websocket_orchestrator",
        ],
    },
}
# ============================================================================

import asyncio
from collections import deque
from collections.abc import Callable, Coroutine
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from uuid import uuid4

import structlog

logger = structlog.get_logger(__name__)


async def dispatch_task_immediate(task: QueuedTask) -> str:
    """
    Execute a task immediately without queueing.

    Synchronous task execution for reactive dispatch.

    Args:
        task: QueuedTask to execute immediately

    Returns:
        Task ID
    """
    logger.info(f"Dispatching task {task.task_id} immediately: {task.name}")

    # Get handler from task queue
    task_queue = TaskQueue(queue_name="l9:tasks", use_redis=True)

    # Access handlers (they're registered via register_handler)
    # For immediate dispatch, we need to check if handler exists
    # If not, log warning and return task_id
    try:
        # Try to get handler - handlers are stored in _handlers dict
        handler = getattr(task_queue, "_handlers", {}).get(task.handler)

        if not handler:
            logger.warning(f"No handler registered for: {task.handler}")
            return task.task_id

        # Execute handler directly (matching process_one signature: handler receives payload and agent_id)
        await handler(task.payload, agent_id=task.agent_id)
        logger.info(f"Task {task.task_id} executed successfully")
    except Exception as e:
        logger.error(f"Task {task.task_id} execution failed: {e}", exc_info=True)

    return task.task_id


# Try to import Redis client
try:
    from runtime.redis_client import get_redis_client

    _has_redis_client = True
except ImportError:
    _has_redis_client = False
    logger.debug("Redis client not available")


@dataclass
class QueuedTask:
    """A task waiting in the queue."""

    task_id: str
    name: str
    payload: dict[str, Any]
    handler: str
    agent_id: str | None
    priority: int
    tags: list[str]
    created_at: datetime = field(default_factory=datetime.utcnow)
    status: str = "pending_igor_approval"
    approved_by: str | None = None
    approval_timestamp: datetime | None = None
    approval_reason: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Serialize task to dictionary for Redis storage.

        Returns:
            Dict with all task fields, timestamps as ISO strings.
        """
        return {
            "task_id": self.task_id,
            "name": self.name,
            "payload": self.payload,
            "handler": self.handler,
            "agent_id": self.agent_id,
            "priority": self.priority,
            "tags": self.tags,
            "created_at": self.created_at.isoformat(),
            "status": self.status,
            "approved_by": self.approved_by,
            "approval_timestamp": (
                self.approval_timestamp.isoformat() if self.approval_timestamp else None
            ),
            "approval_reason": self.approval_reason,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> QueuedTask:
        """Deserialize task from dictionary.

        Args:
            data: Dict with task fields from Redis.

        Returns:
            QueuedTask instance.
        """
        return cls(
            task_id=data["task_id"],
            name=data["name"],
            payload=data["payload"],
            handler=data["handler"],
            agent_id=data.get("agent_id"),
            priority=data.get("priority", 5),
            tags=data.get("tags", []),
            created_at=datetime.fromisoformat(
                data.get("created_at", datetime.now(timezone.utc).isoformat())
            ),
            status=data.get("status", "pending_igor_approval"),
            approved_by=data.get("approved_by"),
            approval_timestamp=(
                datetime.fromisoformat(data["approval_timestamp"])
                if data.get("approval_timestamp")
                else None
            ),
            approval_reason=data.get("approval_reason"),
        )


class TaskQueue:
    """
    Production task queue with Redis backend enforcement.

    Tasks are ordered by priority (lower = higher priority).
    Redis is mandatory; in-memory fallback is prohibited.
    """

    def __init__(self, queue_name: str = "l9:tasks", use_redis: bool = True) -> None:
        """
        Initialize task queue.

        Args:
            queue_name: Queue name for Redis (default: "l9:tasks")
            use_redis: Whether to attempt Redis connection (default: True)
        """
        self._queue_name = queue_name
        if not use_redis:
            raise RuntimeError("TaskQueue requires Redis; in-memory mode is disabled")
        if not _has_redis_client:
            raise RuntimeError("TaskQueue requires Redis client; none available")

        self._use_redis = True
        self._redis_client = None
        self._queue: deque[QueuedTask] = deque()
        self._lock = asyncio.Lock()
        self._handlers: dict[str, Callable[..., Coroutine[Any, Any, Any]]] = {}
        self._redis_available = False

        # Try to connect to Redis (async, will be checked on first use)
        logger.info(f"TaskQueue initialized with Redis support (queue: {queue_name})")

    async def _ensure_redis(self) -> bool:
        """Ensure Redis client is connected and available.

        Returns:
            True if Redis is available.

        Raises:
            RuntimeError: If Redis is unavailable or disabled.
        """
        if not self._use_redis:
            raise RuntimeError("TaskQueue requires Redis; in-memory mode is disabled")

        if self._redis_client is None:
            self._redis_client = await get_redis_client()
            self._redis_available = (
                self._redis_client is not None and self._redis_client.is_available()
            )

            if self._redis_available:
                logger.info("TaskQueue: Redis backend active")
            else:
                raise RuntimeError("TaskQueue: Redis unavailable; execution blocked")

        if not self._redis_available:
            raise RuntimeError("TaskQueue: Redis unavailable; execution blocked")
        return True

    async def enqueue(
        self,
        name: str,
        payload: dict[str, Any],
        handler: str = "default",
        agent_id: str | None = None,
        priority: int = 5,
        tags: list[str] | None = None,
    ) -> str:
        """
        Add a task to the queue.

        Args:
            name: Human-readable task name
            payload: Task data
            handler: Handler function name to invoke
            agent_id: Optional target agent
            priority: 1-10, lower is higher priority
            tags: Optional tags for filtering

        Returns:
            Task ID
        """
        task = QueuedTask(
            task_id=str(uuid4()),
            name=name,
            payload=payload,
            handler=handler,
            agent_id=agent_id,
            priority=priority,
            tags=tags or [],
        )

        await self._ensure_redis()
        try:
            task_id = await self._redis_client.enqueue_task(
                self._queue_name,
                task.to_dict(),
                priority=priority,
            )
            if task_id:
                logger.debug(
                    "Enqueued task %s to Redis: name=%s, priority=%d, handler=%s",
                    task_id,
                    name,
                    priority,
                    handler,
                )
                return task_id
            raise RuntimeError("Redis enqueue returned no task_id")
        except Exception as e:
            raise RuntimeError(f"Redis enqueue failed: {e}") from e

    async def dequeue(self) -> QueuedTask | None:
        """
        Remove and return the highest priority task.

        Returns:
            QueuedTask or None if queue is empty
        """
        await self._ensure_redis()
        try:
            task_data = await self._redis_client.dequeue_task(self._queue_name)
            if task_data:
                task = QueuedTask.from_dict(task_data)
                logger.debug(f"Dequeued task {task.task_id} from Redis")
                return task
            return None
        except Exception as e:
            raise RuntimeError(f"Redis dequeue failed: {e}") from e

    async def peek(self) -> QueuedTask | None:
        """Return the next task without removing it.

        Raises:
            RuntimeError: Always raised; peek not supported for Redis.
        """
        await self._ensure_redis()
        raise RuntimeError("TaskQueue.peek is not supported for Redis-backed queues")

    async def size(self) -> int:
        """Return current queue size.

        Returns:
            Number of tasks in the queue.

        Raises:
            RuntimeError: If Redis operation fails.
        """
        await self._ensure_redis()
        try:
            return await self._redis_client.queue_size(self._queue_name)
        except Exception as e:
            raise RuntimeError(f"Redis queue size failed: {e}") from e

    def register_handler(
        self,
        name: str,
        handler: Callable[..., Coroutine[Any, Any, Any]],
    ) -> None:
        """
        Register a handler function for a handler name.

        Args:
            name: Handler name (e.g., "ws_event_handler")
            handler: Async function to invoke
        """
        self._handlers[name] = handler
        logger.debug("Registered handler: %s", name)

    async def process_one(self) -> bool:
        """
        Process a single task from the queue.

        Returns:
            True if a task was processed, False if queue was empty
        """
        task = await self.dequeue()
        if task is None:
            return False

        handler = self._handlers.get(task.handler)
        if handler is None:
            logger.warning("No handler registered for: %s", task.handler)
            return True

        try:
            await handler(task.payload, agent_id=task.agent_id)
            logger.debug("Processed task %s", task.task_id)
        except Exception as e:
            logger.error(
                "Handler %s failed for task %s: %s", task.handler, task.task_id, e
            )

        return True


async def enqueue_long_plan_tasks(
    plan_id: str, task_specs: list[dict[str, Any]]
) -> list[str]:
    """
    Bulk-enqueue extracted tasks from a long plan.

    Args:
        plan_id: Plan identifier
        task_specs: List of task spec dicts from extract_tasks_from_plan()

    Returns:
        List of task IDs for enqueued tasks
    """
    task_queue = TaskQueue(queue_name="l9:tasks", use_redis=True)
    task_ids = []

    for spec in task_specs:
        try:
            # Enqueue task with plan tag
            task_id = await task_queue.enqueue(
                name=spec["name"],
                payload=spec["payload"],
                handler=spec["handler"],
                agent_id=spec.get("agent_id", "L"),
                priority=spec.get("priority", 5),
                tags=[*spec.get("tags", []), f"plan:{plan_id}"],
            )
            task_ids.append(task_id)
            logger.debug(f"Enqueued task {task_id} from plan {plan_id}")
        except Exception as e:
            logger.warning(f"Failed to enqueue task from plan {plan_id}: {e}")

    logger.info(f"Enqueued {len(task_ids)}/{len(task_specs)} tasks from plan {plan_id}")
    return task_ids


__all__ = ["QueuedTask", "TaskQueue", "enqueue_long_plan_tasks"]

# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "RUN-OPER-003",
    "governance_level": "medium",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": ["runtime.redis_client"],
    "tags": [
        "async",
        "cache",
        "dataclass",
        "debugging",
        "event-driven",
        "logging",
        "operations",
        "queue",
        "runtime-operations",
    ],
    "keywords": [
        "dequeue",
        "dispatch",
        "enqueue",
        "handler",
        "immediate",
        "long",
        "memory",
        "one",
    ],
    "business_value": "Provides task queue components including QueuedTask, TaskQueue",
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
