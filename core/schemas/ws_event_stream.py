"""
L9 Core Schemas - WebSocket Event Stream
=========================================

WebSocket-specific event stream types for L9 agent communication.

Defines:
- EventType: High-level event categories for WS messages
- EventMessage: Canonical event structure for WS frames
- AgentHeartbeat: Periodic health check from agents
- ErrorEvent: Error reporting structure

These types complement the security event stream with WebSocket-specific
transport models.

Version: 1.0.0
"""

from __future__ import annotations


from datetime import UTC, datetime
from enum import Enum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

# =============================================================================
# Event Type Enum
# =============================================================================


class EventType(str, Enum):
    """
    High-level event categories for WebSocket communication.

    Used to route and handle incoming WS frames efficiently.
    """

    HEARTBEAT = "heartbeat"
    TASK_ASSIGNED = "task_assigned"
    TASK_RESULT = "task_result"
    ERROR = "error"
    CONTROL = "control"
    HANDSHAKE = "handshake"
    LOG = "log"


# =============================================================================
# Event Message (Canonical WS Frame)
# =============================================================================


class EventMessage(BaseModel):
    """
    Canonical event structure for L9's internal EventStream.

    This is the standard format for all WebSocket frames exchanged
    between agents and orchestrator.

    Attributes:
        id: Unique event identifier
        type: High-level event category
        timestamp: When the event was created
        channel: Logical bus (e.g. "agent", "orchestrator", "task")
        agent_id: Which agent this relates to (if any)
        payload: Event-specific data dictionary
        trace_id: Distributed tracing identifier
        correlation_id: For request/response correlation

    Usage:
        event = EventMessage(
            type=EventType.TASK_RESULT,
            agent_id="mac-agent-1",
            payload={"task_id": "abc123", "result": "success"}
        )
    """

    id: UUID = Field(default_factory=uuid4, description="Unique event identifier")
    type: EventType = Field(..., description="High-level event category")
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Event creation timestamp",
    )
    channel: str = Field(default="agent", description="Logical message bus")
    agent_id: str | None = Field(None, description="Related agent identifier")
    payload: dict[str, Any] = Field(
        default_factory=dict, description="Event-specific data"
    )
    trace_id: str | None = Field(None, description="Distributed trace ID")
    correlation_id: str | None = Field(None, description="Request/response correlation")

    model_config = {"extra": "allow"}


# =============================================================================
# Agent Heartbeat
# =============================================================================


class AgentHeartbeat(BaseModel):
    """
    Periodic heartbeat message from connected agents.

    Sent at regular intervals to indicate agent liveness and load.
    Used by orchestrator for health monitoring and load balancing.

    Attributes:
        agent_id: Identifier of the reporting agent
        timestamp: When heartbeat was generated
        load_avg: System load average (if available)
        running_tasks: Count of currently executing tasks
        memory_usage_mb: Memory usage in megabytes
        cpu_percent: CPU utilization percentage

    Usage:
        heartbeat = AgentHeartbeat(
            agent_id="mac-agent-1",
            running_tasks=3,
            load_avg=1.5
        )
    """

    agent_id: str = Field(..., min_length=1, description="Agent identifier")
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(UTC), description="Heartbeat timestamp"
    )
    load_avg: float | None = Field(None, ge=0, description="System load average")
    running_tasks: int = Field(default=0, ge=0, description="Active task count")
    memory_usage_mb: float | None = Field(None, ge=0, description="Memory usage (MB)")
    cpu_percent: float | None = Field(
        None, ge=0, le=100, description="CPU utilization %"
    )

    model_config = {"extra": "allow"}


# =============================================================================
# Error Event
# =============================================================================


class ErrorEvent(BaseModel):
    """
    Error reporting structure for WebSocket communication.

    Used to report errors from agents back to the orchestrator,
    or from orchestrator to agents.

    Attributes:
        agent_id: Agent that experienced/reported the error
        code: Machine-readable error code
        message: Human-readable error description
        details: Additional error context
        timestamp: When error occurred
        recoverable: Whether the error is recoverable

    Usage:
        error = ErrorEvent(
            agent_id="mac-agent-1",
            code="TASK_TIMEOUT",
            message="Task execution exceeded 30s limit",
            details={"task_id": "abc123", "elapsed_seconds": 35}
        )
    """

    agent_id: str | None = Field(None, description="Agent reporting error")
    code: str = Field(..., min_length=1, description="Error code")
    message: str = Field(..., description="Human-readable error message")
    details: dict[str, Any] = Field(
        default_factory=dict, description="Additional error context"
    )
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(UTC), description="Error timestamp"
    )
    recoverable: bool = Field(default=True, description="Is error recoverable")

    model_config = {"extra": "allow"}


# =============================================================================
# Public API
# =============================================================================

__all__ = [
    "AgentHeartbeat",
    "ErrorEvent",
    "EventMessage",
    "EventType",
]

# Runtime execution trace - updated automatically on every execution
