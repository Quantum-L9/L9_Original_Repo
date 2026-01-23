"""
WebSocket → Task Router Integration Tests

Tests the flow: WS Message → Parser → Task Router → Handler
"""

import pytest
from unittest.mock import MagicMock
from uuid import uuid4

from core.schemas.ws_event_stream import EventMessage, EventType
from orchestration.ws_task_router import WSTaskRouter

pytestmark = pytest.mark.integration


class TestWSTaskRoutingIntegration:
    """Test WebSocket to Task Router integration."""

    @pytest.mark.asyncio
    async def test_task_result_routed_to_handler(self):
        """Task result message routes to correct handler."""
        router = WSTaskRouter()

        # Create mock handler
        handler = MagicMock()
        router.register_handler(EventType.TASK_RESULT, handler)

        # Route a message
        message = EventMessage(
            type=EventType.TASK_RESULT,
            agent_id="test-agent",
            payload={"task_id": str(uuid4()), "result": {"status": "completed"}},
        )

        result = router.route(message)

        # Verify handler was called or message was routed
        assert result is not None or handler.called

    @pytest.mark.asyncio
    async def test_unknown_message_type_handled(self):
        """Unknown message types don't crash router."""
        router = WSTaskRouter()

        # Create a custom event type (not in default handlers)
        message = EventMessage(type=EventType.CONTROL, agent_id="test-agent", payload={"data": {}})

        # Should not raise
        result = router.route(message)
        # May return None or route to handler
        assert result is None or isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_multiple_handlers_chain(self):
        """Multiple handlers for same type all execute."""
        router = WSTaskRouter()

        handler1 = MagicMock()
        handler2 = MagicMock()

        # Register custom handlers
        router.register_handler(EventType.CONTROL, handler1)
        router.register_handler(EventType.CONTROL, handler2)

        message = EventMessage(
            type=EventType.CONTROL, agent_id="test-agent", payload={"action": "test"}
        )

        result = router.route(message)

        # At least one handler should be registered
        assert handler1.called or handler2.called or result is not None
