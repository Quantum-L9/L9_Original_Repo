"""
L9 Core Schemas - Event Stream Types
====================================

Security-related event stream types for L9.

Defines:
- AgentHandshake: Agent registration with capabilities
- SecurityEvent: Security audit log event
- CapabilityViolation: Capability enforcement violation event

These types extend the core packet system with security-specific events.

Version: 1.0.0
"""

from __future__ import annotations

# ============================================================================
__dora_meta__ = {
    "component_name": "Event Stream Types",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2025-12-09T01:02:49Z",
    "updated_at": "2026-01-12T22:01:05Z",
    "layer": "foundation",
    "domain": "data_models",
    "module_name": "event_stream",
    "type": "enum",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": [],
        "memory_layers": ["semantic_memory"],
        "imported_by": ["api.server", "core.schemas.__init__"],
    },
}
# ============================================================================

from datetime import UTC, datetime
from enum import Enum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from core.schemas.capabilities import AgentCapabilities, ToolName

# =============================================================================
# Enums
# =============================================================================


class HandshakeStatus(str, Enum):
    """Status of agent handshake."""

    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    EXPIRED = "expired"


class SecurityEventType(str, Enum):
    """Types of security events."""

    HANDSHAKE_INITIATED = "handshake_initiated"
    HANDSHAKE_ACCEPTED = "handshake_accepted"
    HANDSHAKE_REJECTED = "handshake_rejected"
    CAPABILITY_CHECKED = "capability_checked"
    CAPABILITY_VIOLATION = "capability_violation"
    RATE_LIMIT_EXCEEDED = "rate_limit_exceeded"
    KERNEL_INTEGRITY_CHECK = "kernel_integrity_check"
    BOUNDARY_ENFORCEMENT = "boundary_enforcement"


# =============================================================================
# Agent Handshake
# =============================================================================


class AgentHandshake(BaseModel):
    """
    Agent handshake message for registration and capability declaration.

    Sent by agents on startup to register with the orchestrator.
    Contains agent metadata and capability declarations.

    Attributes:
        agent_id: Unique agent identifier
        agent_version: Semantic version of the agent
        capabilities: List of capability string names
        agent_capabilities: Full AgentCapabilities object (if provided)
        hostname: Host where agent is running
        platform: Platform identifier (linux, darwin, win32)
        session_id: Current session identifier
        timestamp: Handshake timestamp

    Usage:
        handshake = AgentHandshake(
            agent_id="coder-agent-1",
            agent_version="2.0.0",
            capabilities=["shell", "memory_read", "memory_write"],
            hostname="dev-server-1",
            platform="darwin",
        )
    """

    # Required fields
    agent_id: str = Field(..., min_length=1, description="Unique agent identifier")

    # Version and metadata
    agent_version: str = Field(default="0.1.0", description="Agent semantic version")
    capabilities: list[str] = Field(
        default_factory=list,
        description="List of capability names (simple string list)",
    )

    # Authentication (optional, can be in query params or handshake)
    auth_token: str | None = Field(
        None, description="Authentication token (can also be provided via query params)"
    )

    # Full capability object (optional, for advanced use)
    agent_capabilities: AgentCapabilities | None = Field(
        None, description="Full AgentCapabilities object for detailed permissions"
    )

    # Environment metadata
    hostname: str | None = Field(None, description="Host where agent runs")
    platform: str | None = Field(None, description="Platform identifier")

    # Session tracking
    session_id: UUID = Field(default_factory=uuid4, description="Session identifier")
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Handshake timestamp",
    )

    # Handshake state
    status: HandshakeStatus = Field(
        default=HandshakeStatus.PENDING, description="Current handshake status"
    )

    model_config = {"extra": "allow"}

    def has_capability(self, tool: str) -> bool:
        """
        Check if agent declared a capability.

        Args:
            tool: Tool name to check

        Returns:
            True if declared, False otherwise
        """
        # Check simple list first
        if tool in self.capabilities:
            return True

        # Check full capabilities object if present
        if self.agent_capabilities:
            try:
                tool_enum = ToolName(tool)
                return self.agent_capabilities.is_tool_allowed(tool_enum)
            except ValueError:
                return False

        return False


class HandshakeResponse(BaseModel):
    """
    Response to an agent handshake.

    Sent by orchestrator to accept or reject agent registration.

    Attributes:
        handshake_id: Reference to original handshake
        agent_id: Agent being responded to
        status: Acceptance status
        effective_capabilities: Approved capabilities (may differ from requested)
        session_token: Session token for subsequent requests
        expires_at: When this handshake expires
        rejection_reason: Reason if rejected
    """

    handshake_id: UUID = Field(default_factory=uuid4, description="Response identifier")
    agent_id: str = Field(..., description="Agent being responded to")
    status: HandshakeStatus = Field(..., description="Acceptance status")

    # Approved capabilities
    effective_capabilities: list[str] = Field(
        default_factory=list, description="Capabilities actually granted"
    )

    # Session management
    session_token: str | None = Field(None, description="Session token for requests")
    expires_at: datetime | None = Field(None, description="Handshake expiration")

    # Rejection details
    rejection_reason: str | None = Field(None, description="Reason if rejected")

    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Response timestamp",
    )


# =============================================================================
# Security Events
# =============================================================================


class SecurityEvent(BaseModel):
    """
    Security audit log event.

    Captures security-relevant events for audit trail.
    All security events are immutable once created.

    Attributes:
        event_id: Unique event identifier
        event_type: Type of security event
        agent_id: Agent involved (if applicable)
        session_id: Session context
        details: Event-specific details
        severity: Event severity (info, warning, error, critical)
        timestamp: When event occurred
    """

    event_id: UUID = Field(default_factory=uuid4, description="Event identifier")
    event_type: SecurityEventType = Field(..., description="Type of security event")

    # Context
    agent_id: str | None = Field(None, description="Agent involved")
    session_id: UUID | None = Field(None, description="Session context")

    # Event details
    details: dict[str, Any] = Field(
        default_factory=dict, description="Event-specific details"
    )
    severity: str = Field(default="info", description="Event severity")

    # Timing
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Event timestamp",
    )

    # Correlation
    correlation_id: UUID | None = Field(
        None, description="Correlation ID for tracing related events"
    )
    trace_id: str | None = Field(None, description="Distributed trace ID")

    model_config = {"frozen": True}


class CapabilityViolation(BaseModel):
    """
    Capability enforcement violation event.

    Created when an agent attempts to use a tool without permission.

    Attributes:
        violation_id: Unique violation identifier
        agent_id: Agent that attempted the action
        tool_attempted: Tool that was attempted
        action_details: Details of the attempted action
        blocked: Whether the action was blocked
        timestamp: When violation occurred
    """

    violation_id: UUID = Field(
        default_factory=uuid4, description="Violation identifier"
    )
    agent_id: str = Field(..., description="Agent that attempted action")
    tool_attempted: ToolName = Field(..., description="Tool that was attempted")

    # Action details
    action_details: dict[str, Any] = Field(
        default_factory=dict, description="Details of attempted action"
    )

    # Enforcement result
    blocked: bool = Field(default=True, description="Whether action was blocked")
    enforcement_message: str = Field(
        default="Capability not allowed", description="Message returned to agent"
    )

    # Context
    session_id: UUID | None = Field(None, description="Session context")
    correlation_id: UUID | None = Field(None, description="Correlation ID")

    # Timing
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Violation timestamp",
    )

    model_config = {"frozen": True}


# =============================================================================
# Event Factories
# =============================================================================


def create_handshake_event(handshake: AgentHandshake) -> SecurityEvent:
    """Create a security event for an agent handshake."""
    return SecurityEvent(
        event_type=SecurityEventType.HANDSHAKE_INITIATED,
        agent_id=handshake.agent_id,
        session_id=handshake.session_id,
        details={
            "agent_version": handshake.agent_version,
            "capabilities_requested": handshake.capabilities,
            "hostname": handshake.hostname,
            "platform": handshake.platform,
        },
        severity="info",
    )


def create_violation_event(violation: CapabilityViolation) -> SecurityEvent:
    """Create a security event for a capability violation."""
    return SecurityEvent(
        event_type=SecurityEventType.CAPABILITY_VIOLATION,
        agent_id=violation.agent_id,
        session_id=violation.session_id,
        correlation_id=violation.correlation_id,
        details={
            "tool_attempted": violation.tool_attempted.value,
            "action_details": violation.action_details,
            "blocked": violation.blocked,
        },
        severity="warning" if violation.blocked else "error",
    )


# =============================================================================
# Public API
# =============================================================================

__all__ = [
    # Models
    "AgentHandshake",
    "CapabilityViolation",
    "HandshakeResponse",
    # Enums
    "HandshakeStatus",
    "SecurityEvent",
    "SecurityEventType",
    # Factories
    "create_handshake_event",
    "create_violation_event",
]

# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "COR-FOUN-073",
    "governance_level": "critical",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": ["core.schemas.capabilities"],
    "tags": [
        "api",
        "audit-tool",
        "auth",
        "authorization",
        "data-models",
        "enum",
        "event-driven",
        "foundation",
        "messaging",
        "pydantic",
    ],
    "keywords": [
        "agent",
        "audit",
        "capability",
        "core",
        "create",
        "event",
        "handshake",
        "security",
    ],
    "business_value": "Provides event stream components including HandshakeStatus, SecurityEventType, AgentHandshake",
    "last_modified": "2026-01-12T22:01:05Z",
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
