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

# ============================================================================
__dora_meta__ = {
    "component_name": "WebSocket Event Stream",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2025-12-09T01:02:49Z",
    "updated_at": "2026-01-07T13:35:57Z",
    "layer": "foundation",
    "domain": "data_models",
    "module_name": "ws_event_stream",
    "type": "enum",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": [],
        "memory_layers": [],
        "imported_by": [
            "core.schemas.__init__",
            "orchestration.unified_controller",
            "orchestration.ws_task_router",
            "orchestrators.ws_bridge",
            "runtime.websocket_orchestrator",
            "tests.integration.test_ws_task_routing_integration",
            "tests.orchestrators.test_ws_task_router_routing",
            "tests.runtime.test_websocket_orchestrator_basic",
            "tests.runtime.test_ws_protocol_static",
        ],
    },
}
# ============================================================================

from datetime import datetime, UTC
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
        default_factory=lambda: datetime.now(UTC), description="Event creation timestamp"
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

# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "COR-FOUN-069",
    "governance_level": "critical",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": [
        "api",
        "data-models",
        "enum",
        "event-driven",
        "foundation",
        "messaging",
        "monitoring",
        "pydantic",
        "realtime",
        "streaming",
    ],
    "keywords": [
        "agent",
        "event",
        "heartbeat",
        "specific",
        "stream",
        "structure",
        "types",
        "websocket",
    ],
    "business_value": "Provides ws event stream components including EventType, EventMessage, AgentHeartbeat",
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
