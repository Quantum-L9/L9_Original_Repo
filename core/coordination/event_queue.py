"""
Event-Driven Coordination Layer

Harvested from: L9-Implementation-Suite-Ready-to-Deploy.md
Purpose: Async message queue for agent coordination, replacing synchronous calls.
"""

from __future__ import annotations

# ============================================================================
__dora_meta__ = {
    "component_name": "Event Queue",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2026-01-06T15:07:54Z",
    "updated_at": "2026-01-17T23:47:56Z",
    "layer": "foundation",
    "domain": "data_models",
    "module_name": "event_queue",
    "type": "dataclass",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": [],
        "memory_layers": [],
        "imported_by": ["api.server"],
    },
}
# ============================================================================

import asyncio
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any
from uuid import uuid4

import structlog

from core.decorators import must_stay_async

logger = structlog.get_logger(__name__)


class EventKind(Enum):
    """Event types in the coordination system"""

    AGENT_REQUEST = "agent_request"
    AGENT_RESPONSE = "agent_response"
    TOOL_CALL = "tool_call"
    TOOL_RESULT = "tool_result"
    ERROR = "error"
    STATUS_UPDATE = "status_update"
    HEARTBEAT = "heartbeat"
    # Task lifecycle events (Stage 7: GMP-WIRE-VC-EQ)
    TASK_CREATED = "task_created"
    TASK_STARTED = "task_started"
    TASK_COMPLETED = "task_completed"
    TASK_FAILED = "task_failed"


@dataclass
class Event:
    """Event in the async coordination system"""

    kind: EventKind
    source_agent: str
    target_agent: str
    payload: dict
    request_id: str | None = None
    timestamp: str | None = None

    def __post_init__(self):
        if not self.request_id:
            self.request_id = str(uuid4())
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()


class EventQueue:
    """Async message queue for agent coordination"""

    def __init__(self, max_size: int = 10000, backpressure_enabled: bool = True):
        self.queue: asyncio.Queue = asyncio.Queue(maxsize=max_size)
        self.subscribers: dict[str, list[Callable]] = {}  # agent_id → handlers
        self.backpressure_enabled = backpressure_enabled
        self.metrics = {
            "events_published": 0,
            "events_processed": 0,
            "events_dropped": 0,
            "current_queue_depth": 0,
            "backpressure_activations": 0,
            "errors": 0,
        }
        self._running = False

    async def publish(self, event: Event) -> bool:
        """Publish event to queue (non-blocking with backpressure)"""
        try:
            if self.queue.full():
                self.metrics["backpressure_activations"] += 1
                if not self.backpressure_enabled:
                    self.metrics["events_dropped"] += 1
                    logger.warning("Event dropped (queue full)", kind=event.kind.value)
                    return False
                # Wait for space (upstream agent pauses)
                try:
                    await asyncio.wait_for(self.queue.put(event), timeout=5.0)
                except TimeoutError:
                    self.metrics["events_dropped"] += 1
                    logger.error("Event timeout (backpressure)", kind=event.kind.value)
                    return False
            else:
                self.queue.put_nowait(event)

            self.metrics["events_published"] += 1
            self.metrics["current_queue_depth"] = self.queue.qsize()
            return True

        except Exception as e:
            self.metrics["errors"] += 1
            logger.error("Error publishing event", error=str(e))
            return False

    @must_stay_async("callers use await")
    async def subscribe(self, agent_id: str, handler: Callable) -> None:
        """Agent subscribes to events"""
        if agent_id not in self.subscribers:
            self.subscribers[agent_id] = []
        self.subscribers[agent_id].append(handler)
        logger.info("Agent subscribed", agent_id=agent_id)

    async def process_forever(self) -> None:
        """Main event loop (blocks until stop)"""
        self._running = True
        logger.info("Event queue processor started")

        try:
            while self._running:
                try:
                    # Get event (block with timeout)
                    event = await asyncio.wait_for(self.queue.get(), timeout=60)

                    # Route to subscribers
                    if event.target_agent in self.subscribers:
                        handlers = self.subscribers[event.target_agent]
                        for handler in handlers:
                            try:
                                await handler(event)
                            except Exception as e:
                                self.metrics["errors"] += 1
                                logger.error(
                                    "Handler error",
                                    agent=event.target_agent,
                                    error=str(e),
                                )

                                # Send error event back to source
                                error_event = Event(
                                    kind=EventKind.ERROR,
                                    source_agent="event_queue",
                                    target_agent=event.source_agent,
                                    payload={
                                        "error": str(e),
                                        "original_request_id": event.request_id,
                                    },
                                )
                                await self.publish(error_event)
                    else:
                        logger.warning(
                            "No subscribers for agent", agent=event.target_agent
                        )

                    self.metrics["events_processed"] += 1
                    self.queue.task_done()

                except TimeoutError:
                    # No events in last 60s, continue
                    continue

        finally:
            self._running = False
            logger.info("Event queue processor stopped")

    def stop(self) -> None:
        """Stop the event processor"""
        self._running = False

    def get_metrics(self) -> dict:
        """Get event queue metrics"""
        return {
            **self.metrics,
            "subscriber_count": len(self.subscribers),
            "agents_subscribed": list(self.subscribers.keys()),
        }


class EventRouter:
    """Routes events to correct handlers based on rules"""

    def __init__(self, event_queue: EventQueue):
        self.queue = event_queue
        self.routes: dict[EventKind, list[Callable]] = {}

    @must_stay_async("callers use await")
    async def register_route(self, event_kind: EventKind, handler: Callable) -> None:
        """Register handler for event type"""
        if event_kind not in self.routes:
            self.routes[event_kind] = []
        self.routes[event_kind].append(handler)

    async def route_event(self, event: Event) -> None:
        """Route event based on type"""
        if event.kind in self.routes:
            for handler in self.routes[event.kind]:
                try:
                    await handler(event)
                except Exception as e:
                    logger.error("Route handler error", error=str(e))


@must_stay_async("callers use await")
async def init_event_driven_coordination(app_state: Any) -> EventQueue:
    """Initialize event-driven coordination at startup"""
    event_queue = EventQueue(max_size=10000)

    # Create event processor task
    processor_task = asyncio.create_task(event_queue.process_forever())

    # Store in app state
    app_state.event_queue = event_queue
    app_state.event_processor_task = processor_task

    logger.info("Event-driven coordination initialized")
    return event_queue


@must_stay_async("health endpoint")
async def event_queue_health(event_queue: EventQueue) -> dict:
    """Health check for event queue"""
    metrics = event_queue.get_metrics()
    queue_health = "healthy" if metrics["errors"] < 100 else "degraded"
    return {
        "status": queue_health,
        "metrics": metrics,
    }


# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "COR-FOUN-022",
    "governance_level": "critical",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": ["core.decorators"],
    "tags": [
        "async",
        "data-models",
        "dataclass",
        "event-driven",
        "foundation",
        "logging",
        "messaging",
        "metrics",
        "queue",
        "routing",
    ],
    "keywords": [
        "agent",
        "coordination",
        "driven",
        "event",
        "forever",
        "health",
        "kind",
        "metrics",
    ],
    "business_value": "Provides event queue components including EventKind, Event, EventQueue",
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
