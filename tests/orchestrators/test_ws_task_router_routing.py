"""
L9 Tests - WS Task Router Routing
Version: 1.0.0

Covers:
- TASK_RESULT routing → TaskEnvelope
- ERROR routing → TaskEnvelope
- HEARTBEAT → None (no task)
"""

from core.schemas.tasks import TaskEnvelope, TaskKind
from core.schemas.ws_event_stream import EventMessage, EventType
from orchestration.ws_task_router import RouterConfig, route_event_to_task


class TestWSTaskRouterRouting:
    def test_task_result_routing(self):
        event = EventMessage(
            type=EventType.TASK_RESULT,
            agent_id="mac_agent_01",
            payload={
                "task_id": "t-123",
                "result": {"status": "ok"},
                "status": "completed",
                "extra": "meta",
            },
        )

        cfg = RouterConfig(emit_packets=True, trace_events=True, default_priority=3)
        envelope = route_event_to_task(event, cfg)

        assert isinstance(envelope, TaskEnvelope)
        assert envelope.agent_id == "mac_agent_01"
        assert envelope.source_event_id == event.id

        task = envelope.task
        assert task.kind == TaskKind.RESULT.value
        assert task.priority == 3
        assert task.trace_id == event.trace_id
        assert task.payload["original_task_id"] == "t-123"
        assert task.payload["result"]["status"] == "ok"
        assert task.payload["status"] == "completed"
        assert task.payload["extra"] == "meta"

    def test_error_event_routing(self):
        event = EventMessage(
            type=EventType.ERROR,
            agent_id="mac_agent_01",
            payload={
                "code": "AUTH_FAILED",
                "message": "bad token",
                "details": {"reason": "mismatch"},
                "recoverable": False,
            },
        )

        cfg = RouterConfig()
        envelope = route_event_to_task(event, cfg)

        assert isinstance(envelope, TaskEnvelope)
        assert envelope.agent_id == "mac_agent_01"

        task = envelope.task
        assert task.kind == TaskKind.ERROR.value
        assert task.payload["error_code"] == "AUTH_FAILED"
        assert task.payload["message"] == "bad token"
        assert task.payload["details"]["reason"] == "mismatch"
        assert task.payload["recoverable"] is False

    def test_heartbeat_does_not_generate_task(self):
        event = EventMessage(
            type=EventType.HEARTBEAT,
            agent_id="mac_agent_01",
            payload={"running_tasks": 3},
        )

        cfg = RouterConfig()
        envelope = route_event_to_task(event, cfg)

        assert envelope is None
