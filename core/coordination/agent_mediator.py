"""
Agent Mediator Pattern for L9 AIOS
==================================

Implements the Mediator design pattern to decouple agent-to-agent communication.
Instead of agents calling each other directly, they communicate through the mediator,
which routes messages, manages subscriptions, and handles delivery guarantees.

Forked from PR #53 with L9 singleton integration (uses @register_singleton).

Benefits:
- Reduces coupling between agents
- Centralized message routing and logging
- Easier to add new agents without modifying existing ones
- Supports pub/sub patterns for broadcast messages
- Enables message queuing for offline agents

Usage:
    from core.coordination.agent_mediator import get_agent_mediator

    # Get singleton mediator instance (via L9 registry)
    mediator = await get_agent_mediator()

    # Register agents
    mediator.register_agent("l-cto", l_cto_agent)
    mediator.register_agent("research", research_agent)

    # Send direct message
    await mediator.send_message(
        from_agent="l-cto",
        to_agent="research",
        message={"task": "Research async patterns"}
    )

    # Broadcast to all agents
    await mediator.broadcast(
        from_agent="igor",
        message={"announcement": "System maintenance in 1 hour"}
    )

    # Subscribe to message types
    mediator.subscribe("task_complete", cto_agent.on_task_complete)

Version: 1.0.0
Source: Forked from PR #53, aligned with L9 singleton infrastructure
"""

from __future__ import annotations

# ============================================================================
__dora_meta__ = {
    "component_name": "Agent Mediator",
    "module_version": "1.0.0",
    "created_by": "L9 Design Patterns Initiative",
    "created_at": "2026-01-24T19:30:00Z",
    "updated_at": "2026-01-24T19:30:00Z",
    "layer": "coordination",
    "domain": "agent_communication",
    "module_name": "agent_mediator",
    "type": "service",
    "status": "active",
    "source": "Forked from PR #53 with L9 singleton integration",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": [],
        "memory_layers": [],
        "imported_by": ["core.facade.l9_facade"],
    },
}
# ============================================================================

import asyncio
from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from uuid import uuid4

import structlog

from core.singleton_auto_registry import register_singleton, register_singleton_closer
from core.singleton_registry import SingletonLifecycle

logger = structlog.get_logger(__name__)


# =============================================================================
# Message Data Structures
# =============================================================================


@dataclass
class Message:
    """
    Message structure for agent-to-agent communication.

    Attributes:
        id: Unique message identifier
        from_agent: Sender agent ID
        to_agent: Recipient agent ID (None for broadcast)
        message_type: Type of message (e.g., "task_request", "task_complete")
        payload: Message content
        timestamp: Message creation time
        priority: Message priority (0=low, 5=normal, 10=high)
        requires_ack: Whether message requires acknowledgment
    """

    id: str = field(default_factory=lambda: str(uuid4()))
    from_agent: str = ""
    to_agent: str | None = None
    message_type: str = "generic"
    payload: dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)
    priority: int = 5
    requires_ack: bool = False


@dataclass
class MessageDeliveryStatus:
    """Track message delivery status."""

    message_id: str
    delivered: bool = False
    acknowledged: bool = False
    delivery_time: datetime | None = None
    error: str | None = None


# =============================================================================
# Agent Mediator Service
# =============================================================================


class AgentMediator:
    """
    Mediator for agent-to-agent communication.

    Manages message routing, subscriptions, and delivery guarantees
    between agents in the L9 AIOS.

    This is a singleton service - use get_agent_mediator() to obtain instance.
    """

    def __init__(self):
        """Initialize the mediator."""
        # Agent registry: agent_id -> agent instance
        self.agents: dict[str, Any] = {}

        # Message type subscriptions: message_type -> list of handlers
        self.subscriptions: dict[str, list[Callable]] = defaultdict(list)

        # Message queue for offline agents: agent_id -> list of messages
        self.message_queue: dict[str, list[Message]] = defaultdict(list)

        # Delivery tracking: message_id -> status
        self.delivery_status: dict[str, MessageDeliveryStatus] = {}

        # Agent status: agent_id -> online/offline
        self.agent_status: dict[str, bool] = {}

        logger.info("AgentMediator initialized")

    def register_agent(self, agent_id: str, agent: Any) -> None:
        """
        Register an agent with the mediator.

        Args:
            agent_id: Unique agent identifier
            agent: Agent instance
        """
        self.agents[agent_id] = agent
        self.agent_status[agent_id] = True

        # Inject mediator reference into agent
        if hasattr(agent, "set_mediator"):
            agent.set_mediator(self)

        logger.info(f"Agent registered: {agent_id}")

        # Deliver queued messages
        if agent_id in self.message_queue:
            task = asyncio.create_task(self._deliver_queued_messages(agent_id))
            # Store task reference to prevent garbage collection
            self._background_tasks = getattr(self, "_background_tasks", set())
            self._background_tasks.add(task)
            task.add_done_callback(self._background_tasks.discard)

    def unregister_agent(self, agent_id: str) -> None:
        """
        Unregister an agent from the mediator.

        Args:
            agent_id: Agent identifier to unregister
        """
        if agent_id in self.agents:
            del self.agents[agent_id]
            self.agent_status[agent_id] = False
            logger.info(f"Agent unregistered: {agent_id}")

    def subscribe(self, message_type: str, handler: Callable) -> None:
        """
        Subscribe to a message type.

        Args:
            message_type: Type of message to subscribe to
            handler: Async callback function to handle messages
        """
        self.subscriptions[message_type].append(handler)
        logger.debug(f"Subscribed to message type: {message_type}")

    def unsubscribe(self, message_type: str, handler: Callable) -> None:
        """
        Unsubscribe from a message type.

        Args:
            message_type: Type of message to unsubscribe from
            handler: Handler to remove
        """
        if handler in self.subscriptions[message_type]:
            self.subscriptions[message_type].remove(handler)
            logger.debug(f"Unsubscribed from message type: {message_type}")

    async def send_message(
        self,
        from_agent: str,
        to_agent: str,
        message: dict[str, Any],
        message_type: str = "generic",
        priority: int = 5,
        requires_ack: bool = False,
    ) -> str:
        """
        Send a message from one agent to another.

        Args:
            from_agent: Sender agent ID
            to_agent: Recipient agent ID
            message: Message payload
            message_type: Type of message
            priority: Message priority (0-10)
            requires_ack: Whether to require acknowledgment

        Returns:
            Message ID
        """
        msg = Message(
            from_agent=from_agent,
            to_agent=to_agent,
            message_type=message_type,
            payload=message,
            priority=priority,
            requires_ack=requires_ack,
        )

        logger.info(
            f"Sending message: {from_agent} → {to_agent}",
            message_id=msg.id,
            message_type=message_type,
        )

        # Track delivery status
        self.delivery_status[msg.id] = MessageDeliveryStatus(message_id=msg.id)

        # Check if recipient is online
        if to_agent in self.agents and self.agent_status.get(to_agent, False):
            await self._deliver_message(to_agent, msg)
        else:
            # Queue message for later delivery
            self.message_queue[to_agent].append(msg)
            logger.warning(
                f"Agent {to_agent} offline, message queued", message_id=msg.id
            )

        # Notify subscribers
        await self._notify_subscribers(msg)

        return msg.id

    async def broadcast(
        self,
        from_agent: str,
        message: dict[str, Any],
        message_type: str = "broadcast",
        exclude: set[str] | None = None,
    ) -> list[str]:
        """
        Broadcast a message to all registered agents.

        Args:
            from_agent: Sender agent ID
            message: Message payload
            message_type: Type of message
            exclude: Set of agent IDs to exclude from broadcast

        Returns:
            List of message IDs
        """
        exclude = exclude or set()
        exclude.add(from_agent)  # Don't send to self

        logger.info(
            f"Broadcasting message from {from_agent}",
            message_type=message_type,
            recipient_count=len(self.agents) - len(exclude),
        )

        message_ids = []
        for agent_id in self.agents:
            if agent_id not in exclude:
                msg_id = await self.send_message(
                    from_agent=from_agent,
                    to_agent=agent_id,
                    message=message,
                    message_type=message_type,
                )
                message_ids.append(msg_id)

        return message_ids

    async def acknowledge_message(self, message_id: str, agent_id: str) -> None:
        """
        Acknowledge receipt of a message.

        Args:
            message_id: ID of message to acknowledge
            agent_id: Agent acknowledging the message
        """
        if message_id in self.delivery_status:
            self.delivery_status[message_id].acknowledged = True
            logger.debug(f"Message acknowledged by {agent_id}", message_id=message_id)

    async def _deliver_message(self, agent_id: str, message: Message) -> None:
        """
        Deliver a message to an agent.

        Args:
            agent_id: Recipient agent ID
            message: Message to deliver
        """
        try:
            agent = self.agents[agent_id]

            # Call agent's receive_message method if it exists
            if hasattr(agent, "receive_message"):
                await agent.receive_message(message.from_agent, message.payload)

            # Update delivery status
            status = self.delivery_status[message.id]
            status.delivered = True
            status.delivery_time = datetime.utcnow()

            logger.debug(f"Message delivered to {agent_id}", message_id=message.id)
        except Exception as e:
            logger.error(
                f"Failed to deliver message to {agent_id}",
                message_id=message.id,
                error=str(e),
            )
            self.delivery_status[message.id].error = str(e)

    async def _deliver_queued_messages(self, agent_id: str) -> None:
        """
        Deliver all queued messages to an agent.

        Args:
            agent_id: Agent to deliver messages to
        """
        if agent_id not in self.message_queue:
            return

        messages = self.message_queue[agent_id]
        logger.info(f"Delivering {len(messages)} queued messages to {agent_id}")

        for message in messages:
            await self._deliver_message(agent_id, message)

        # Clear queue
        del self.message_queue[agent_id]

    async def _notify_subscribers(self, message: Message) -> None:
        """
        Notify all subscribers of a message type.

        Args:
            message: Message to notify about
        """
        handlers = self.subscriptions.get(message.message_type, [])
        for handler in handlers:
            try:
                await handler(message)
            except Exception as e:
                logger.error(
                    f"Subscriber handler failed for {message.message_type}",
                    error=str(e),
                )

    def get_agent_status(self, agent_id: str) -> bool:
        """
        Get online/offline status of an agent.

        Args:
            agent_id: Agent to check

        Returns:
            True if online, False if offline
        """
        return self.agent_status.get(agent_id, False)

    def get_queued_message_count(self, agent_id: str) -> int:
        """
        Get number of queued messages for an agent.

        Args:
            agent_id: Agent to check

        Returns:
            Number of queued messages
        """
        return len(self.message_queue.get(agent_id, []))

    def get_delivery_status(self, message_id: str) -> MessageDeliveryStatus | None:
        """
        Get delivery status of a message.

        Args:
            message_id: Message to check

        Returns:
            Delivery status or None if not found
        """
        return self.delivery_status.get(message_id)

    async def close(self) -> None:
        """Cleanup mediator resources."""
        logger.info("Closing AgentMediator")
        # Unregister all agents
        for agent_id in list(self.agents.keys()):
            self.unregister_agent(agent_id)
        # Clear all state
        self.subscriptions.clear()
        self.message_queue.clear()
        self.delivery_status.clear()
        logger.info("AgentMediator closed")


# =============================================================================
# Singleton Registration (L9 Auto-Registry Pattern)
# =============================================================================

# Module-level instance (initialized lazily)
_mediator_instance: AgentMediator | None = None


@register_singleton(
    category="coordination",
    lifecycle=SingletonLifecycle.LAZY,
    dependencies=[],
    description="Agent-to-agent message mediator for decoupled communication",
)
async def get_agent_mediator() -> AgentMediator:
    """
    Get the singleton AgentMediator instance.

    Uses L9's @register_singleton for proper lifecycle management.

    Returns:
        The global AgentMediator instance
    """
    global _mediator_instance
    if _mediator_instance is None:
        _mediator_instance = AgentMediator()
    return _mediator_instance


@register_singleton_closer("agent_mediator")
async def close_agent_mediator() -> None:
    """Close the AgentMediator singleton."""
    global _mediator_instance
    if _mediator_instance is not None:
        await _mediator_instance.close()
        _mediator_instance = None
        logger.info("AgentMediator singleton closed")


# Convenience alias for backward compatibility
get_mediator = get_agent_mediator

# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "COR-FOUN-033",
    "governance_level": "critical",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": ["core.singleton_auto_registry", "core.singleton_registry"],
    "tags": [
        "async",
        "core",
        "dataclass",
        "debugging",
        "event-driven",
        "foundation",
        "logging",
        "messaging",
        "queue",
    ],
    "keywords": [
        "acknowledge",
        "agent",
        "agents",
        "await",
        "broadcast",
        "close",
        "count",
        "delivery",
    ],
    "business_value": "Implements the Mediator design pattern to decouple agent-to-agent communication. Instead of agents calling each other directly, they communicate through the mediator, which routes messages, manages su",
    "last_modified": "2026-01-24T15:21:11Z",
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
