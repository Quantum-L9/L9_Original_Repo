"""
L9 Runtime - WebSocket Orchestrator
=====================================

Manages WebSocket connections from L9 agents.

Responsibilities:
- Accept and validate agent handshakes
- Track connected agents with metadata
- Route incoming messages to the ws_bridge for task conversion
- Dispatch outbound events to specific agents

The module-level singleton `ws_orchestrator` is the canonical instance.

Version: 1.0.0
"""

from __future__ import annotations

import structlog
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import WebSocket
from core.decorators import must_stay_async

logger = structlog.get_logger(__name__)


class WebSocketOrchestrator:
    """
    Manages live WebSocket connections from L9 agents.

    Thread-safe singleton - use `ws_orchestrator` module-level instance.
    """

    def __init__(self) -> None:
        self._connections: Dict[str, WebSocket] = {}
        self._metadata: Dict[str, Dict[str, Any]] = {}
        self._connected_at: Dict[str, datetime] = {}
        logger.info("WebSocketOrchestrator initialized")

    # =========================================================================
    # Connection Management
    # =========================================================================

    @must_stay_async("callers use await")
    async def register(
        self,
        agent_id: str,
        websocket: WebSocket,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Register an agent's WebSocket connection.

        Args:
            agent_id: Unique identifier for the agent
            websocket: Active WebSocket connection
            metadata: Optional handshake metadata (capabilities, version, etc.)
        """
        self._connections[agent_id] = websocket
        self._metadata[agent_id] = metadata or {}
        self._connected_at[agent_id] = datetime.utcnow()
        logger.info(
            "Agent %s registered (metadata=%s)",
            agent_id,
            list((metadata or {}).keys()),
        )

    @must_stay_async("callers use await")
    async def unregister(self, agent_id: str) -> None:
        """
        Unregister an agent and clean up resources.

        Args:
            agent_id: Agent to unregister
        """
        self._connections.pop(agent_id, None)
        self._metadata.pop(agent_id, None)
        self._connected_at.pop(agent_id, None)
        logger.info("Agent %s unregistered", agent_id)

    def is_connected(self, agent_id: str) -> bool:
        """Check if an agent is currently connected."""
        return agent_id in self._connections

    def get_connected_agents(self) -> list[str]:
        """Get list of currently connected agent IDs."""
        return list(self._connections.keys())

    def get_metadata(self, agent_id: str) -> Dict[str, Any]:
        """Get metadata for a connected agent."""
        return self._metadata.get(agent_id, {})

    # =========================================================================
    # Message Handling
    # =========================================================================

    @must_stay_async("callers use await")
    async def handle_incoming(self, agent_id: str, data: Dict[str, Any]) -> None:
        """
        Handle an incoming message from an agent.

        Routes the message through ws_bridge for task conversion and enqueueing.

        Args:
            agent_id: Agent that sent the message
            data: Raw JSON payload from WebSocket
        """
        from core.schemas.ws_event_stream import EventMessage, EventType
        from orchestrators.ws_bridge import handle_ws_event

        # Convert raw data to EventMessage if possible
        try:
            event_type_str = data.get("type", "log")
            event_type = EventType(event_type_str)
        except ValueError:
            event_type = EventType.LOG

        event = EventMessage(
            type=event_type,
            agent_id=agent_id,
            payload=data.get("payload", data),
            trace_id=data.get("trace_id"),
            correlation_id=data.get("correlation_id"),
        )

        # Route through ws_bridge
        envelope = handle_ws_event(event)
        if envelope:
            logger.debug(
                "Created task envelope from agent %s: kind=%s",
                agent_id,
                envelope.task.kind,
            )

    async def on_user_message(self, message: str) -> List[str]:
        """
        Handle user message and trigger reactive task generation and dispatch.

        Args:
            message: User message text

        Returns:
            List of task IDs for generated and dispatched tasks
        """
        from core.agents.executor import _generate_tasks_from_query
        from runtime.task_queue import dispatch_task_immediate, QueuedTask
        from uuid import uuid4

        # Generate tasks from query
        task_specs = await _generate_tasks_from_query(message)

        if not task_specs:
            logger.warning(f"No tasks generated from message: {message[:100]}")
            return []

        task_ids = []

        # Dispatch each task immediately
        for spec in task_specs:
            try:
                task = QueuedTask(
                    task_id=str(uuid4()),
                    name=spec["name"],
                    payload=spec["payload"],
                    handler=spec["handler"],
                    agent_id="L",
                    priority=spec.get("priority", 5),
                    tags=["reactive", "user_message"],
                )

                task_id = await dispatch_task_immediate(task)
                task_ids.append(task_id)
                logger.info(f"Dispatched reactive task {task_id} from user message")
            except Exception as e:
                logger.error(
                    f"Failed to dispatch task from message: {e}", exc_info=True
                )

        return task_ids

    # =========================================================================
    # Outbound Dispatch
    # =========================================================================

    async def dispatch_event(self, agent_id: str, event: Any) -> None:
        """
        Send an event to a specific agent.

        Args:
            agent_id: Target agent
            event: EventMessage or dict to send

        Raises:
            RuntimeError: If agent is not connected
        """
        ws = self._connections.get(agent_id)
        if ws is None:
            raise RuntimeError(f"Agent {agent_id} is not connected")

        # Serialize event
        if hasattr(event, "model_dump"):
            payload = event.model_dump(mode="json")
        else:
            payload = dict(event)

        await ws.send_json(payload)
        logger.debug(
            "Dispatched event to agent %s: type=%s", agent_id, payload.get("type")
        )

    async def broadcast(self, event: Any, exclude: Optional[list[str]] = None) -> int:
        """
        Broadcast an event to all connected agents.

        Args:
            event: EventMessage or dict to send
            exclude: Optional list of agent IDs to skip

        Returns:
            Number of agents the event was sent to
        """
        exclude = exclude or []
        count = 0

        for agent_id in list(self._connections.keys()):
            if agent_id in exclude:
                continue
            try:
                await self.dispatch_event(agent_id, event)
                count += 1
            except Exception as e:
                logger.warning("Failed to broadcast to %s: %s", agent_id, e)

        return count


# =============================================================================
# Module-level Singleton
# =============================================================================

ws_orchestrator = WebSocketOrchestrator()

__all__ = ["WebSocketOrchestrator", "ws_orchestrator"]
