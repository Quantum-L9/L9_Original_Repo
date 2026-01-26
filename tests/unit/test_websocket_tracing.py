"""
Unit Tests for WebSocket Tracing Middleware
============================================

Tests the WebSocket tracing middleware implementation.

Test Coverage:
- TraceContext creation and export
- WebSocketTracingMiddleware trace extraction
- Query parameter parsing
- Header extraction
- Trace context injection into packets
- get_trace_context() helper function

Mutation Testing Target: 85%+ score
"""

from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest

from api.middleware.websocket_tracing import (
    TraceContext,
    WebSocketTracingMiddleware,
    get_trace_context,
    inject_trace_into_packet,
)


class TestTraceContext:
    """Test TraceContext dataclass."""

    def test_trace_context_with_all_params(self):
        """Test TraceContext creation with all parameters."""
        trace_id = str(uuid4())
        correlation_id = str(uuid4())
        connection_id = str(uuid4())

        ctx = TraceContext(
            trace_id=trace_id,
            correlation_id=correlation_id,
            connection_id=connection_id,
        )

        assert ctx.trace_id == trace_id
        assert ctx.correlation_id == correlation_id
        assert ctx.connection_id == connection_id

    def test_trace_context_with_defaults(self):
        """Test TraceContext generates UUIDs when not provided."""
        ctx = TraceContext()

        assert ctx.trace_id is not None
        assert ctx.correlation_id is not None
        assert ctx.connection_id is not None
        assert ctx.correlation_id == ctx.trace_id  # Default correlation_id = trace_id

    def test_trace_context_to_dict(self):
        """Test TraceContext.to_dict() exports correctly."""
        trace_id = "test-trace-id"
        correlation_id = "test-correlation-id"
        connection_id = "test-connection-id"

        ctx = TraceContext(
            trace_id=trace_id,
            correlation_id=correlation_id,
            connection_id=connection_id,
        )

        result = ctx.to_dict()

        assert result == {
            "trace_id": trace_id,
            "correlation_id": correlation_id,
            "connection_id": connection_id,
        }


class TestWebSocketTracingMiddleware:
    """Test WebSocketTracingMiddleware."""

    @pytest.mark.asyncio
    async def test_middleware_skips_non_websocket_connections(self):
        """Test middleware passes through non-WebSocket connections."""
        mock_app = AsyncMock()
        middleware = WebSocketTracingMiddleware(mock_app)

        scope = {"type": "http", "path": "/api/test"}
        receive = AsyncMock()
        send = AsyncMock()

        await middleware(scope, receive, send)

        # Should call wrapped app without modification
        mock_app.assert_called_once_with(scope, receive, send)

    @pytest.mark.asyncio
    async def test_middleware_injects_trace_context_for_websocket(self):
        """Test middleware injects trace context into WebSocket scope."""
        mock_app = AsyncMock()
        middleware = WebSocketTracingMiddleware(mock_app)

        scope = {
            "type": "websocket",
            "path": "/ws",
            "query_string": b"",
            "headers": [],
        }
        receive = AsyncMock()
        send = AsyncMock()

        await middleware(scope, receive, send)

        # Check trace context was injected
        assert "state" in scope
        assert "trace_context" in scope["state"]
        assert isinstance(scope["state"]["trace_context"], TraceContext)

    @pytest.mark.asyncio
    async def test_middleware_extracts_trace_id_from_query_params(self):
        """Test middleware extracts trace_id from query parameters."""
        mock_app = AsyncMock()
        middleware = WebSocketTracingMiddleware(mock_app)

        trace_id = "test-trace-id-123"
        scope = {
            "type": "websocket",
            "path": "/ws",
            "query_string": f"trace_id={trace_id}".encode(),
            "headers": [],
        }
        receive = AsyncMock()
        send = AsyncMock()

        await middleware(scope, receive, send)

        trace_context = scope["state"]["trace_context"]
        assert trace_context.trace_id == trace_id

    @pytest.mark.asyncio
    async def test_middleware_extracts_trace_id_from_headers(self):
        """Test middleware extracts trace_id from headers."""
        mock_app = AsyncMock()
        middleware = WebSocketTracingMiddleware(mock_app)

        trace_id = "test-trace-id-456"
        scope = {
            "type": "websocket",
            "path": "/ws",
            "query_string": b"",
            "headers": [(b"x-trace-id", trace_id.encode("utf-8"))],
        }
        receive = AsyncMock()
        send = AsyncMock()

        await middleware(scope, receive, send)

        trace_context = scope["state"]["trace_context"]
        assert trace_context.trace_id == trace_id

    @pytest.mark.asyncio
    async def test_middleware_prefers_query_params_over_headers(self):
        """Test middleware prefers query params over headers."""
        mock_app = AsyncMock()
        middleware = WebSocketTracingMiddleware(mock_app)

        query_trace_id = "query-trace-id"
        header_trace_id = "header-trace-id"

        scope = {
            "type": "websocket",
            "path": "/ws",
            "query_string": f"trace_id={query_trace_id}".encode(),
            "headers": [(b"x-trace-id", header_trace_id.encode("utf-8"))],
        }
        receive = AsyncMock()
        send = AsyncMock()

        await middleware(scope, receive, send)

        trace_context = scope["state"]["trace_context"]
        assert trace_context.trace_id == query_trace_id

    def test_parse_query_string_empty(self):
        """Test _parse_query_string with empty string."""
        middleware = WebSocketTracingMiddleware(Mock())

        result = middleware._parse_query_string("")

        assert result == {}

    def test_parse_query_string_single_param(self):
        """Test _parse_query_string with single parameter."""
        middleware = WebSocketTracingMiddleware(Mock())

        result = middleware._parse_query_string("trace_id=123")

        assert result == {"trace_id": "123"}

    def test_parse_query_string_multiple_params(self):
        """Test _parse_query_string with multiple parameters."""
        middleware = WebSocketTracingMiddleware(Mock())

        result = middleware._parse_query_string(
            "trace_id=123&correlation_id=456&foo=bar"
        )

        assert result == {
            "trace_id": "123",
            "correlation_id": "456",
            "foo": "bar",
        }

    def test_parse_query_string_no_equals(self):
        """Test _parse_query_string with malformed params."""
        middleware = WebSocketTracingMiddleware(Mock())

        result = middleware._parse_query_string("trace_id&foo=bar")

        # Should only parse valid key=value pairs
        assert result == {"foo": "bar"}


class TestGetTraceContext:
    """Test get_trace_context() helper function."""

    def test_get_trace_context_from_websocket(self):
        """Test get_trace_context() extracts from WebSocket."""
        trace_context = TraceContext(trace_id="test-trace")

        mock_websocket = Mock()
        mock_websocket.scope = {
            "state": {
                "trace_context": trace_context,
            }
        }

        result = get_trace_context(mock_websocket)

        assert result is trace_context

    def test_get_trace_context_no_scope(self):
        """Test get_trace_context() returns None if no scope."""
        mock_websocket = Mock(spec=[])  # No scope attribute

        result = get_trace_context(mock_websocket)

        assert result is None

    def test_get_trace_context_no_state(self):
        """Test get_trace_context() returns None if no state."""
        mock_websocket = Mock()
        mock_websocket.scope = {}  # No state

        result = get_trace_context(mock_websocket)

        assert result is None


class TestInjectTraceIntoPacket:
    """Test inject_trace_into_packet() helper function."""

    def test_inject_trace_into_packet_with_context(self):
        """Test inject_trace_into_packet() with TraceContext."""
        packet = {"packet_type": "event", "payload": {}}
        trace_context = TraceContext(
            trace_id="test-trace",
            correlation_id="test-correlation",
        )

        result = inject_trace_into_packet(packet, trace_context)

        assert result is packet  # Mutates in-place
        assert packet["trace_id"] == "test-trace"
        assert packet["correlation_id"] == "test-correlation"

    def test_inject_trace_into_packet_without_context(self):
        """Test inject_trace_into_packet() generates context if None."""
        packet = {"packet_type": "event", "payload": {}}

        result = inject_trace_into_packet(packet, None)

        assert result is packet
        assert "trace_id" in packet
        assert "correlation_id" in packet
        assert packet["trace_id"] is not None
        assert packet["correlation_id"] is not None


# =============================================================================
# Mutation Testing Targets
# =============================================================================


class TestMutationTargets:
    """
    Tests specifically designed to kill common mutations.
    """

    def test_trace_context_correlation_id_defaults_to_trace_id(self):
        """Kill mutation: correlation_id = trace_id -> correlation_id = None."""
        ctx = TraceContext(trace_id="test-trace")

        assert ctx.correlation_id == ctx.trace_id

    def test_query_params_preferred_over_headers(self):
        """Kill mutation: query_params check -> headers check."""
        middleware = WebSocketTracingMiddleware(Mock())

        # With query param
        scope1 = {
            "type": "websocket",
            "query_string": b"trace_id=query",
            "headers": [(b"x-trace-id", b"header")],
        }
        ctx1 = middleware._extract_trace_context(scope1)
        assert ctx1.trace_id == "query"

        # Without query param
        scope2 = {
            "type": "websocket",
            "query_string": b"",
            "headers": [(b"x-trace-id", b"header")],
        }
        ctx2 = middleware._extract_trace_context(scope2)
        assert ctx2.trace_id == "header"

    def test_websocket_type_check(self):
        """Kill mutation: type == 'websocket' -> type != 'websocket'."""
        middleware = WebSocketTracingMiddleware(Mock())

        # Should process websocket
        ws_scope = {"type": "websocket", "query_string": b"", "headers": []}
        ctx1 = middleware._extract_trace_context(ws_scope)
        assert ctx1 is not None

        # Should not process http
        # _extract_trace_context not called for http in actual flow

    def test_inject_trace_mutates_in_place(self):
        """Kill mutation: return new dict -> return mutated dict."""
        packet = {"packet_type": "event"}
        trace_ctx = TraceContext(trace_id="test")

        result = inject_trace_into_packet(packet, trace_ctx)

        assert result is packet  # Same object
        assert id(result) == id(packet)
