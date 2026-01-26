"""
L9 Tests - WebSocket Protocol Static Tests
Version: 1.0.0

Covers:
- EventMessage default behavior
- AgentHeartbeat schema constraints
- ErrorEvent structure
"""

from uuid import UUID

from core.schemas.ws_event_stream import (
    AgentHeartbeat,
    ErrorEvent,
    EventMessage,
    EventType,
)


class TestEventMessageBasics:
    def test_minimal_event_defaults(self):
        """
        Contract: EventMessage creates with minimal required fields and assigns defaults.
        """
        event = EventMessage(
            type=EventType.TASK_RESULT,
            agent_id="agent-1",
            payload={"task_id": "abc123", "result": "ok"},
        )

        assert isinstance(event.id, UUID)
        assert event.type == EventType.TASK_RESULT
        assert event.channel == "agent"
        assert event.agent_id == "agent-1"
        assert isinstance(event.timestamp, type(event.timestamp))
        assert isinstance(event.payload, dict)
        assert event.payload["task_id"] == "abc123"

    def test_handshake_event_roundtrip(self):
        """
        Contract: EventMessage can be serialized and deserialized preserving all fields.
        """
        event = EventMessage(
            type=EventType.HANDSHAKE,
            agent_id="mac_agent_01",
            payload={
                "capabilities": ["shell", "browser"],
                "version": "1.0.0",
            },
        )

        data = event.model_dump(mode="json")
        restored = EventMessage(**data)

        assert restored.type == EventType.HANDSHAKE
        assert restored.agent_id == "mac_agent_01"
        assert restored.payload["capabilities"] == ["shell", "browser"]
        assert restored.payload["version"] == "1.0.0"


class TestAgentHeartbeat:
    def test_heartbeat_defaults_and_constraints(self):
        """
        Contract: AgentHeartbeat initializes with defaults for optional metrics.
        """
        hb = AgentHeartbeat(agent_id="mac_agent_01")

        assert hb.agent_id == "mac_agent_01"
        assert hb.running_tasks == 0
        assert hb.load_avg is None
        assert hb.memory_usage_mb is None
        assert hb.cpu_percent is None

    def test_heartbeat_with_metrics(self):
        """
        Contract: AgentHeartbeat accepts and stores all metric values.
        """
        hb = AgentHeartbeat(
            agent_id="mac_agent_01",
            load_avg=0.5,
            running_tasks=3,
            memory_usage_mb=512.0,
            cpu_percent=42.0,
        )

        assert hb.load_avg == 0.5
        assert hb.running_tasks == 3
        assert hb.memory_usage_mb == 512.0
        assert hb.cpu_percent == 42.0


class TestErrorEvent:
    def test_error_event_basic(self):
        """
        Contract: ErrorEvent can be serialized and deserialized preserving error details.
        """
        err = ErrorEvent(
            agent_id="mac_agent_01",
            code="AUTH_FAILED",
            message="Invalid token",
            details={"reason": "token_mismatch"},
        )

        data = err.model_dump(mode="json")
        restored = ErrorEvent(**data)

        assert restored.code == "AUTH_FAILED"
        assert restored.message == "Invalid token"
        assert restored.details["reason"] == "token_mismatch"
        assert restored.agent_id == "mac_agent_01"
