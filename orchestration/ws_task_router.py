"""
L9 Orchestration - WebSocket Task Router
=========================================

Routes inbound WebSocket EventMessages into actionable tasks.

Phase 2:
- Handle TASK_RESULT events → TaskEnvelope
- Handle ERROR events → TaskEnvelope
- Provide routing hooks for task_queue integration

Phase 3 (stub):
- LangGraph-based routing with state machine
- CONTROL and LOG event handling
- Custom event type registration

Version: 1.0.0
"""

from __future__ import annotations

import structlog
from typing import Callable, Dict, Optional

from core.schemas.ws_event_stream import EventMessage, EventType
from core.schemas.tasks import AgentTask, TaskEnvelope, TaskKind
from core.decorators import must_stay_async

logger = structlog.get_logger(__name__)


# =============================================================================
# Router Configuration
# =============================================================================


class RouterConfig:
    """Configuration for the WebSocket task router."""

    def __init__(
        self,
        emit_packets: bool = True,
        trace_events: bool = False,
        default_priority: int = 5,
    ):
        self.emit_packets = emit_packets
        self.trace_events = trace_events
        self.default_priority = default_priority


# =============================================================================
# Core Routing Function
# =============================================================================


def route_event_to_task(
    event: EventMessage,
    config: Optional[RouterConfig] = None,
) -> Optional[TaskEnvelope]:
    """
    Convert inbound WebSocket EventMessages into actionable tasks.

    This is the primary routing function that bridges WebSocket events
    to the task queue system.

    Phase 2:
      - Handle TASK_RESULT → route to completion handler
      - Handle ERROR → route to error handler
      - Future: CONTROL, LOG, custom events

    Args:
        event: Inbound WebSocket EventMessage
        config: Router configuration (optional)

    Returns:
        TaskEnvelope if event generates a task, None otherwise

    Usage:
        event = EventMessage(type=EventType.TASK_RESULT, ...)
        envelope = route_event_to_task(event)
        if envelope:
            task_queue.enqueue(envelope)
    """
    config = config or RouterConfig()

    if config.trace_events:
        logger.debug(f"Routing event: type={event.type}, agent={event.agent_id}")

    # Route based on event type
    if event.type == EventType.TASK_RESULT:
        return _route_task_result(event, config)

    elif event.type == EventType.ERROR:
        return _route_error_event(event, config)

    elif event.type == EventType.HEARTBEAT:
        # Heartbeats don't generate tasks
        return None

    elif event.type == EventType.HANDSHAKE:
        # Handshakes are handled separately by security layer
        return None

    elif event.type == EventType.CONTROL:
        # Phase 3: Route to control handler
        return _route_control_event(event, config)

    elif event.type == EventType.LOG:
        # Phase 3: Route to logging pipeline
        return None

    else:
        logger.warning(f"Unknown event type: {event.type}")
        return None


# =============================================================================
# Event-Specific Routing
# =============================================================================


def _route_task_result(
    event: EventMessage,
    config: RouterConfig,
) -> TaskEnvelope:
    """Route TASK_RESULT events to completion handler."""
    task = AgentTask(
        kind=TaskKind.RESULT.value,
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
        priority=config.default_priority,
        trace_id=event.trace_id,
    )

    envelope = TaskEnvelope(
        task=task,
        agent_id=event.agent_id,
        source_event_id=event.id,
    )

    logger.info(
        f"Routed TASK_RESULT from {event.agent_id}: "
        f"task_id={event.payload.get('task_id')}"
    )

    return envelope


def _route_error_event(
    event: EventMessage,
    config: RouterConfig,
) -> TaskEnvelope:
    """Route ERROR events to error handler."""
    task = AgentTask(
        kind=TaskKind.ERROR.value,
        payload={
            "error_code": event.payload.get("code", "UNKNOWN"),
            "message": event.payload.get("message", "No message provided"),
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
    )

    envelope = TaskEnvelope(
        task=task,
        agent_id=event.agent_id,
        source_event_id=event.id,
    )

    logger.warning(
        f"Routed ERROR from {event.agent_id}: "
        f"code={event.payload.get('code', 'UNKNOWN')}"
    )

    return envelope


def _route_control_event(
    event: EventMessage,
    config: RouterConfig,
) -> Optional[TaskEnvelope]:
    """
    Phase 3 Stub: Route CONTROL events.

    Control events include:
    - PAUSE/RESUME agent
    - SHUTDOWN requests
    - Configuration updates
    - Priority adjustments
    """
    control_action = event.payload.get("action")

    if control_action in ("pause", "resume", "shutdown", "reconfigure"):
        task = AgentTask(
            kind=TaskKind.COMMAND.value,
            payload={
                "control_action": control_action,
                **event.payload,
            },
            priority=1,  # Control messages are highest priority
            trace_id=event.trace_id,
        )

        envelope = TaskEnvelope(
            task=task,
            agent_id=event.agent_id,
            source_event_id=event.id,
        )

        logger.info(f"Routed CONTROL action={control_action} to {event.agent_id}")
        return envelope

    logger.debug(f"Ignoring CONTROL event with unknown action: {control_action}")
    return None


# =============================================================================
# Router Registry (Phase 3 Expansion Point)
# =============================================================================


class WSTaskRouter:
    """
    Extensible WebSocket task router.

    Provides registration hooks for custom event handlers.
    Phase 3 will integrate with LangGraph for state-machine routing.

    Usage:
        router = WSTaskRouter()
        router.register_handler(EventType.CUSTOM, my_handler)
        envelope = router.route(event)
    """

    def __init__(self, config: Optional[RouterConfig] = None):
        """Initialize the router with optional configuration."""
        self._config = config or RouterConfig()
        self._handlers: Dict[
            EventType, Callable[[EventMessage], Optional[TaskEnvelope]]
        ] = {}
        self._default_handlers_registered = False

        # Register default handlers
        self._register_default_handlers()

    def _register_default_handlers(self) -> None:
        """Register built-in event handlers."""
        if self._default_handlers_registered:
            return

        self._handlers[EventType.TASK_RESULT] = lambda e: _route_task_result(
            e, self._config
        )
        self._handlers[EventType.ERROR] = lambda e: _route_error_event(e, self._config)
        self._handlers[EventType.CONTROL] = lambda e: _route_control_event(
            e, self._config
        )

        self._default_handlers_registered = True

    def register_handler(
        self,
        event_type: EventType,
        handler: Callable[[EventMessage], Optional[TaskEnvelope]],
    ) -> None:
        """
        Register a custom event handler.

        Args:
            event_type: Event type to handle
            handler: Handler function
        """
        self._handlers[event_type] = handler
        logger.info(f"Registered custom handler for {event_type}")

    def unregister_handler(self, event_type: EventType) -> bool:
        """
        Unregister an event handler.

        Args:
            event_type: Event type to unregister

        Returns:
            True if handler was removed
        """
        if event_type in self._handlers:
            del self._handlers[event_type]
            logger.info(f"Unregistered handler for {event_type}")
            return True
        return False

    def route(self, event: EventMessage) -> Optional[TaskEnvelope]:
        """
        Route an event to a task envelope.

        Args:
            event: EventMessage to route

        Returns:
            TaskEnvelope or None
        """
        if self._config.trace_events:
            logger.debug(f"Routing via registry: type={event.type}")

        handler = self._handlers.get(event.type)

        if handler:
            return handler(event)

        # Fall back to static routing
        return route_event_to_task(event, self._config)

    def get_registered_types(self) -> list[EventType]:
        """Get list of registered event types."""
        return list(self._handlers.keys())


# =============================================================================
# LangGraph-Based Router
# =============================================================================

# Try to import LangGraph
try:
    from langgraph.graph import StateGraph, START, END

    LANGGRAPH_AVAILABLE = True
except ImportError:
    LANGGRAPH_AVAILABLE = False
    logger.warning(
        "LangGraph not installed. LangGraphRouter will use fallback routing."
    )

from typing import Any, TypedDict, List


class RouterState(TypedDict):
    """State for the routing graph."""

    event: Dict[str, Any]
    event_type: str
    context: Dict[str, Any]
    world_model_context: Dict[str, Any]
    classification: str
    task_envelope: Optional[Dict[str, Any]]
    errors: List[str]


class LangGraphRouter:
    """
    LangGraph-based state machine router.

    Provides:
    - Stateful routing decisions via StateGraph
    - Context loading from world model
    - Classification-based routing
    - Enriched task envelopes
    """

    def __init__(self, world_model_runtime: Optional[Any] = None):
        """
        Initialize LangGraph router.

        Args:
            world_model_runtime: Optional WorldModelRuntime instance for context enrichment
        """
        self._world_model = world_model_runtime
        self._graph = None

        if LANGGRAPH_AVAILABLE:
            self._build_graph()
            logger.info("LangGraphRouter initialized with StateGraph")
        else:
            logger.info("LangGraphRouter initialized with fallback routing")

    def _build_graph(self) -> None:
        """Build the routing state graph."""
        if not LANGGRAPH_AVAILABLE:
            return

        # Create the graph
        graph = StateGraph(RouterState)

        # Add nodes
        graph.add_node("load_context", self._load_context_node)
        graph.add_node("classify", self._classify_node)
        graph.add_node("create_task", self._create_task_node)

        # Add edges
        graph.add_edge(START, "load_context")
        graph.add_edge("load_context", "classify")
        graph.add_edge("classify", "create_task")
        graph.add_edge("create_task", END)

        # Compile the graph
        self._graph = graph.compile()

    async def _load_context_node(self, state: RouterState) -> RouterState:
        """Load context from world model."""
        world_context = {}

        if self._world_model:
            try:
                # Query world model for relevant context
                event_type = state.get("event_type", "")

                if hasattr(self._world_model, "query_patterns"):
                    patterns = await self._world_model.query_patterns(
                        pattern_type="routing",
                        limit=5,
                    )
                    world_context["patterns"] = patterns

                if hasattr(self._world_model, "get_loop_stats"):
                    world_context["model_stats"] = self._world_model.get_loop_stats()

            except Exception as e:
                logger.warning(f"Failed to load world model context: {e}")

        return {
            **state,
            "world_model_context": world_context,
        }

    @must_stay_async("callers use await")
    async def _classify_node(self, state: RouterState) -> RouterState:
        """Classify the event for routing."""
        event_type = state.get("event_type", "")
        event = state.get("event", {})

        # Classification logic
        if event_type == "TASK_RESULT":
            classification = "result_processing"
        elif event_type == "ERROR":
            classification = "error_handling"
        elif event_type == "CONTROL":
            classification = "control_flow"
        elif event_type == "LOG":
            classification = "logging"
        else:
            # Check for high-priority indicators
            payload = event.get("payload", {})
            if payload.get("priority", 5) <= 2:
                classification = "high_priority"
            elif payload.get("require_approval"):
                classification = "approval_required"
            else:
                classification = "standard"

        return {
            **state,
            "classification": classification,
        }

    @must_stay_async("callers use await")
    async def _create_task_node(self, state: RouterState) -> RouterState:
        """Create task envelope from classified event."""
        event = state.get("event", {})
        context = state.get("context", {})
        world_context = state.get("world_model_context", {})
        classification = state.get("classification", "standard")

        # Create EventMessage from event dict
        try:
            event_msg = EventMessage(
                event_type=EventType(state.get("event_type", "TASK_RESULT")),
                session_id=event.get("session_id", ""),
                payload=event.get("payload", {}),
            )

            # Use base routing to create task
            task_envelope = route_event_to_task(event_msg)

            if task_envelope:
                # Enrich with world model context
                task_dict = {
                    "task_id": str(task_envelope.task_id),
                    "task": task_envelope.task.model_dump()
                    if hasattr(task_envelope.task, "model_dump")
                    else {},
                    "kind": task_envelope.kind,
                    "priority": task_envelope.priority,
                    "world_context": world_context,
                    "classification": classification,
                }

                return {
                    **state,
                    "task_envelope": task_dict,
                }

        except Exception as e:
            logger.error(f"Failed to create task envelope: {e}")
            return {
                **state,
                "task_envelope": None,
                "errors": state.get("errors", []) + [str(e)],
            }

        return {
            **state,
            "task_envelope": None,
        }

    async def route(
        self, event: EventMessage, context: Dict[str, Any]
    ) -> Optional[TaskEnvelope]:
        """
        Route event using LangGraph state machine.

        Args:
            event: EventMessage to route
            context: Additional routing context

        Returns:
            TaskEnvelope with enriched context, or None if routing failed
        """
        if not LANGGRAPH_AVAILABLE or self._graph is None:
            # Fallback to simple routing
            return route_event_to_task(event)

        try:
            # Prepare initial state
            initial_state: RouterState = {
                "event": {
                    "event_type": event.event_type.value,
                    "session_id": event.session_id,
                    "payload": event.payload,
                    "timestamp": event.timestamp.isoformat()
                    if hasattr(event, "timestamp")
                    else None,
                },
                "event_type": event.event_type.value,
                "context": context,
                "world_model_context": {},
                "classification": "",
                "task_envelope": None,
                "errors": [],
            }

            # Execute the graph
            final_state = await self._graph.ainvoke(initial_state)

            # Extract task envelope from final state
            task_dict = final_state.get("task_envelope")
            if task_dict:
                # Return the base-routed envelope (world context is logged, not embedded)
                logger.info(
                    "LangGraph routing complete",
                    classification=final_state.get("classification"),
                    has_world_context=bool(final_state.get("world_model_context")),
                )
                return route_event_to_task(event)

            return None

        except Exception as e:
            logger.error(f"LangGraph routing failed, using fallback: {e}")
            return route_event_to_task(event)


# =============================================================================
# Public API
# =============================================================================

__all__ = [
    "route_event_to_task",
    "RouterConfig",
    "WSTaskRouter",
    "LangGraphRouter",  # Phase 3 stub
]
