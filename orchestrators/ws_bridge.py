"""
L9 Orchestrators - WebSocket Bridge
====================================

Bridge module connecting WebSocket EventMessages to the task_queue system.

Responsibilities:
- Convert inbound EventMessage frames into TaskEnvelope objects
- Enqueue tasks into runtime.task_queue for processing
- Provide entry point for WebSocketOrchestrator.handle_incoming

Phase 2:
- Handle TASK_RESULT and ERROR as internal tasks

Phase 3 (planned):
- Handle CONTROL, LOG, custom event types
- Route to LangGraph or specialized orchestrators

Version: 1.0.0
"""

from __future__ import annotations

# ============================================================================
__dora_meta__ = {
    "component_name": "WebSocket Bridge",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2025-12-09T01:02:49Z",
    "updated_at": "2026-01-07T13:35:57Z",
    "layer": "intelligence",
    "domain": "orchestration",
    "module_name": "ws_bridge",
    "type": "adapter",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": [],
        "memory_layers": [],
        "imported_by": ["runtime.websocket_orchestrator"],
    },
}
# ============================================================================

from typing import Optional

import structlog

from core.schemas.tasks import AgentTask, TaskEnvelope
from core.schemas.ws_event_stream import EventMessage, EventType

logger = structlog.get_logger(__name__)


# =============================================================================
# Event → Task Conversion
# =============================================================================


def event_to_task(event: EventMessage) -> Optional[TaskEnvelope]:
    """
    Convert an inbound EventMessage into a TaskEnvelope, if applicable.

    Phase 2:
      - Handle TASK_RESULT and ERROR as internal tasks
      - Future: handle CONTROL, LOG, custom types

    Args:
        event: Inbound WebSocket EventMessage

    Returns:
        TaskEnvelope if the event should generate a task, None otherwise

    Usage:
        envelope = event_to_task(event)
        if envelope:
            task_queue.enqueue(envelope)
    """
    if event.type == EventType.TASK_RESULT:
        return TaskEnvelope(
            task=AgentTask(
                kind="result",
                payload={
                    "original_task_id": event.payload.get("task_id"),
                    "result": event.payload.get("result"),
                    "status": event.payload.get("status", "completed"),
                    **{
                        k: v
                        for k, v in event.payload.items()
                        if k not in ("task_id", "result", "status")
                    },
                },
                trace_id=event.trace_id,
            ),
            agent_id=event.agent_id,
            source_event_id=event.id,
        )

    if event.type == EventType.ERROR:
        return TaskEnvelope(
            task=AgentTask(
                kind="error",
                payload={
                    "error_code": event.payload.get("code", "UNKNOWN"),
                    "message": event.payload.get("message", "No message"),
                    "details": event.payload.get("details", {}),
                    "recoverable": event.payload.get("recoverable", True),
                    **{
                        k: v
                        for k, v in event.payload.items()
                        if k not in ("code", "message", "details", "recoverable")
                    },
                },
                priority=2,  # Errors are high priority
                trace_id=event.trace_id,
            ),
            agent_id=event.agent_id,
            source_event_id=event.id,
        )

    # Phase 3: Handle CONTROL events
    if event.type == EventType.CONTROL:
        control_action = event.payload.get("action")
        if control_action in ("pause", "resume", "shutdown", "reconfigure"):
            return TaskEnvelope(
                task=AgentTask(
                    kind="control",
                    payload={
                        "control_action": control_action,
                        **event.payload,
                    },
                    priority=1,  # Control messages highest priority
                    trace_id=event.trace_id,
                ),
                agent_id=event.agent_id,
                source_event_id=event.id,
            )

    # For other event types (HEARTBEAT, HANDSHAKE, LOG), we don't enqueue tasks
    return None


# =============================================================================
# Bridge Entry Point
# =============================================================================


def handle_ws_event(event: EventMessage) -> Optional[TaskEnvelope]:
    """
    Entry point from WebSocketOrchestrator.handle_incoming.

    If the event should generate a task, enqueue it into the runtime task_queue.

    Args:
        event: Validated EventMessage from WebSocket

    Returns:
        TaskEnvelope if a task was created, None otherwise

    Usage:
        # Called from WebSocketOrchestrator._route_to_task_queue
        envelope = handle_ws_event(event)
        if envelope:
            await task_queue.enqueue(...)
    """
    envelope = event_to_task(event)

    if envelope is not None:
        logger.debug(
            "Created TaskEnvelope from WS event: type=%s, agent=%s, task_kind=%s",
            event.type,
            event.agent_id,
            envelope.task.kind,
        )

        # Note: Actual enqueue is handled by the caller (WebSocketOrchestrator)
        # which has access to the task_queue instance

    return envelope


async def enqueue_ws_event(event: EventMessage) -> bool:
    """
    Convert event to task and enqueue it.

    This is the async version that directly enqueues to task_queue.
    Use when you have an event and want one-line integration.

    Args:
        event: EventMessage to process

    Returns:
        True if task was enqueued, False otherwise
    """
    envelope = event_to_task(event)

    if envelope is None:
        return False

    try:
        from runtime.task_queue import TaskQueue

        # Get or create task queue (lazy load)
        task_queue = TaskQueue()

        await task_queue.enqueue(
            name=f"ws_event_{event.type.value}",
            payload=envelope.to_dict(),
            handler="ws_event_handler",
            agent_id=envelope.agent_id,
            tags=["websocket", event.type.value],
        )

        logger.info(
            "Enqueued task from WS event: type=%s, agent=%s",
            event.type,
            envelope.agent_id,
        )
        return True

    except ImportError:
        logger.warning("task_queue not available for ws_bridge")
        return False
    except Exception as e:
        logger.error("Failed to enqueue WS event: %s", e)
        return False


# =============================================================================
# Phase 3 Stubs
# =============================================================================


class WSBridgeConfig:
    """
    Phase 3: Configuration for the WS bridge.

    Will support:
    - Custom event type handlers
    - Priority overrides
    - Routing rules
    """

    def __init__(
        self,
        enable_control_events: bool = True,
        default_priority: int = 5,
        error_priority: int = 2,
        control_priority: int = 1,
    ):
        self.enable_control_events = enable_control_events
        self.default_priority = default_priority
        self.error_priority = error_priority
        self.control_priority = control_priority


class WSEventRouter:
    """
    Phase 3: Extensible event router with handler registration.

    Will support:
    - Custom handlers for specific event types
    - LangGraph integration for stateful routing
    - Conditional routing based on agent capabilities
    """

    def __init__(self, config: Optional[WSBridgeConfig] = None):
        self._config = config or WSBridgeConfig()
        self._handlers: dict = {}

    def register_handler(self, event_type: EventType, handler) -> None:
        """Register a custom handler for an event type."""
        self._handlers[event_type] = handler

    def route(self, event: EventMessage) -> Optional[TaskEnvelope]:
        """Route event using registered handlers or default logic."""
        if event.type in self._handlers:
            return self._handlers[event.type](event)
        return event_to_task(event)


# =============================================================================
# Public API
# =============================================================================

__all__ = [
    "event_to_task",
    "handle_ws_event",
    "enqueue_ws_event",
    "WSBridgeConfig",
    "WSEventRouter",
]

# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "ORC-INTE-001",
    "governance_level": "high",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [
        "core.schemas.tasks",
        "core.schemas.ws_event_stream",
        "runtime.task_queue",
    ],
    "tags": [
        "adapter",
        "api",
        "async",
        "debugging",
        "event-driven",
        "intelligence",
        "logging",
        "messaging",
        "orchestration",
        "queue",
    ],
    "keywords": [
        "bridge",
        "enqueue",
        "event",
        "handle",
        "handler",
        "into",
        "module",
        "orchestrators",
    ],
    "business_value": "Provides ws bridge components including WSBridgeConfig, WSEventRouter",
    "last_modified": "2026-01-07T13:35:57Z",
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
