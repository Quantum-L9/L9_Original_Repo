"""
L9 Tests - WebSocketOrchestrator Basic Behavior
Version: 1.0.0

Covers:
- register / unregister
- is_connected
- send_to_agent
- broadcast
"""

import pytest

from core.decorators import must_stay_async

# Try to import the orchestrator - may fail if runtime path not in sys.path
try:
    from runtime.websocket_orchestrator import WebSocketOrchestrator

    HAS_ORCHESTRATOR = True
except ImportError:
    HAS_ORCHESTRATOR = False
    WebSocketOrchestrator = None

from core.schemas.ws_event_stream import EventMessage, EventType


class FakeWebSocket:
    def __init__(self):
        self.sent = []
        self.accepted = False
        self.closed = False

    @must_stay_async("callers use await")
    async def accept(self):
        self.accepted = True

    @must_stay_async("callers use await")
    async def send_json(self, data):
        self.sent.append(data)

    @must_stay_async("callers use await")
    async def close(self, code: int = 1000):
        self.closed = True
        self.close_code = code


@pytest.mark.skipif(
    not HAS_ORCHESTRATOR,
    reason="WebSocketOrchestrator not importable in test environment",
)
@pytest.mark.asyncio
class TestWebSocketOrchestratorBasic:
    async def test_register_and_is_connected(self):
        orch = WebSocketOrchestrator()
        ws = FakeWebSocket()

        await orch.register("agent-1", ws, metadata={"role": "mac"})

        assert orch.is_connected("agent-1") is True
        agents = orch.get_connected_agents()
        assert "agent-1" in agents

        meta = orch.get_metadata("agent-1")
        assert meta["role"] == "mac"

    async def test_send_to_agent_and_unregistered_error(self):
        orch = WebSocketOrchestrator()
        ws = FakeWebSocket()
        await orch.register("agent-1", ws)

        event = EventMessage(
            type=EventType.TASK_ASSIGNED,
            agent_id="agent-1",
            payload={"task_id": "t-1"},
        )

        await orch.dispatch_event("agent-1", event)

        assert len(ws.sent) == 1
        frame = ws.sent[0]
        assert frame["type"] == EventType.TASK_ASSIGNED.value
        assert frame["payload"]["task_id"] == "t-1"

        # Unregistered agent should raise
        with pytest.raises(RuntimeError):
            await orch.dispatch_event("agent-2", event)

    async def test_broadcast_exclude(self):
        orch = WebSocketOrchestrator()
        ws1 = FakeWebSocket()
        ws2 = FakeWebSocket()
        ws3 = FakeWebSocket()

        await orch.register("a1", ws1)
        await orch.register("a2", ws2)
        await orch.register("a3", ws3)

        event = EventMessage(
            type=EventType.LOG,
            payload={"msg": "hello"},
        )

        count = await orch.broadcast(event, exclude={"a2"})

        assert count == 2
        assert len(ws1.sent) == 1
        assert len(ws2.sent) == 0
        assert len(ws3.sent) == 1

    async def test_unregister_clears_state(self):
        orch = WebSocketOrchestrator()
        ws = FakeWebSocket()
        await orch.register("agent-1", ws)

        await orch.unregister("agent-1")
        assert orch.is_connected("agent-1") is False
        assert orch.get_metadata("agent-1") == {}
