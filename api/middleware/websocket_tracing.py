"""
L9 API Middleware - WebSocket Tracing
======================================

Middleware for injecting trace_id and correlation_id into WebSocket connections.

Implements Phase 0 Plan 5: WebSocket Tracing Middleware

Key responsibilities:
- Inject trace_id into WebSocket connection state
- Extract trace_id from query params or generate new one
- Propagate trace_id to all packets sent through WebSocket
- Log WebSocket lifecycle events with trace context

This module does NOT:
- Handle HTTP request tracing (use ASGI middleware for that)
- Modify packet payloads (only adds tracing metadata)
- Perform authentication (use auth middleware for that)

Version: 1.0.0
GMP: refactor-phase0-plan5
"""

from __future__ import annotations

# ============================================================================
# DORA HEADER META
# ============================================================================
__dora_meta__ = {
    "component_id": "API-MIDW-001",
    "component_name": "WebSocketTracingMiddleware",
    "module_version": "1.0.0",
    "created_at": "2026-01-21T00:00:00Z",
    "created_by": "L9_Refactoring_Phase0",
    "layer": "api",
    "domain": "middleware",
    "type": "middleware",
    "status": "active",
    "governance_level": "standard",
    "compliance_required": True,
    "audit_trail": True,
    "purpose": "WebSocket connection tracing with distributed trace ID propagation",
    "dependencies": [
        "fastapi",
        "starlette",
    ],
}
# ============================================================================

import structlog
from typing import Any, Callable, Optional
from uuid import uuid4
from fastapi import WebSocket
from starlette.types import ASGIApp, Receive, Scope, Send

logger = structlog.get_logger(__name__)


# =============================================================================
# Trace Context Management
# =============================================================================


class TraceContext:
    """
    Container for trace context in WebSocket connections.
    
    Attributes:
        trace_id: Distributed trace ID (UUID format)
        correlation_id: Correlation ID for grouping related operations
        connection_id: Unique WebSocket connection identifier
    """
    
    def __init__(
        self,
        trace_id: Optional[str] = None,
        correlation_id: Optional[str] = None,
        connection_id: Optional[str] = None,
    ):
        self.trace_id = trace_id or str(uuid4())
        self.correlation_id = correlation_id or self.trace_id
        self.connection_id = connection_id or str(uuid4())
    
    def to_dict(self) -> dict[str, str]:
        """Export trace context as dict for logging."""
        return {
            "trace_id": self.trace_id,
            "correlation_id": self.correlation_id,
            "connection_id": self.connection_id,
        }


# =============================================================================
# WebSocket Tracing Middleware
# =============================================================================


class WebSocketTracingMiddleware:
    """
    ASGI middleware for WebSocket tracing.
    
    Injects trace_id and correlation_id into WebSocket connection state,
    enabling distributed tracing across WebSocket messages.
    
    Usage:
        >>> from fastapi import FastAPI
        >>> app = FastAPI()
        >>> app.add_middleware(WebSocketTracingMiddleware)
    """
    
    def __init__(self, app: ASGIApp):
        """
        Initialize middleware.
        
        Args:
            app: ASGI application to wrap
        """
        self.app = app
    
    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """
        ASGI middleware entry point.
        
        Args:
            scope: ASGI connection scope
            receive: ASGI receive callable
            send: ASGI send callable
        """
        # Only process WebSocket connections
        if scope["type"] != "websocket":
            await self.app(scope, receive, send)
            return
        
        # Extract or generate trace context
        trace_context = self._extract_trace_context(scope)
        
        # Inject trace context into scope state
        if "state" not in scope:
            scope["state"] = {}
        scope["state"]["trace_context"] = trace_context
        
        # Log WebSocket connection with trace context
        logger.info(
            "websocket.connection_opened",
            **trace_context.to_dict(),
            path=scope.get("path"),
            client=scope.get("client"),
        )
        
        # Wrap send to log outgoing messages
        async def traced_send(message: dict[str, Any]) -> None:
            """Wrap send to log outgoing WebSocket messages."""
            if message["type"] == "websocket.send":
                logger.debug(
                    "websocket.message_sent",
                    **trace_context.to_dict(),
                    message_type=message.get("type"),
                )
            elif message["type"] == "websocket.close":
                logger.info(
                    "websocket.connection_closed",
                    **trace_context.to_dict(),
                    code=message.get("code"),
                    reason=message.get("reason"),
                )
            
            await send(message)
        
        # Wrap receive to log incoming messages
        async def traced_receive() -> dict[str, Any]:
            """Wrap receive to log incoming WebSocket messages."""
            message = await receive()
            
            if message["type"] == "websocket.receive":
                logger.debug(
                    "websocket.message_received",
                    **trace_context.to_dict(),
                    message_type=message.get("type"),
                )
            elif message["type"] == "websocket.disconnect":
                logger.info(
                    "websocket.disconnected",
                    **trace_context.to_dict(),
                    code=message.get("code"),
                )
            
            return message
        
        # Call wrapped app with traced send/receive
        await self.app(scope, traced_receive, traced_send)
    
    def _extract_trace_context(self, scope: Scope) -> TraceContext:
        """
        Extract trace context from WebSocket scope.
        
        Checks for trace_id in:
        1. Query parameters (?trace_id=...)
        2. Headers (X-Trace-Id)
        3. Generates new trace_id if not found
        
        Args:
            scope: ASGI connection scope
            
        Returns:
            TraceContext with extracted or generated IDs
        """
        # Extract query parameters
        query_string = scope.get("query_string", b"").decode("utf-8")
        query_params = self._parse_query_string(query_string)
        
        # Try to extract trace_id from query params
        trace_id = query_params.get("trace_id")
        correlation_id = query_params.get("correlation_id")
        
        # Try to extract from headers if not in query params
        if not trace_id:
            headers = dict(scope.get("headers", []))
            trace_id = headers.get(b"x-trace-id", b"").decode("utf-8") or None
            correlation_id = headers.get(b"x-correlation-id", b"").decode("utf-8") or None
        
        return TraceContext(
            trace_id=trace_id,
            correlation_id=correlation_id,
        )
    
    def _parse_query_string(self, query_string: str) -> dict[str, str]:
        """
        Parse query string into dict.
        
        Args:
            query_string: Raw query string (e.g., "trace_id=123&foo=bar")
            
        Returns:
            Dict of query parameters
        """
        if not query_string:
            return {}
        
        params = {}
        for pair in query_string.split("&"):
            if "=" in pair:
                key, value = pair.split("=", 1)
                params[key] = value
        
        return params


# =============================================================================
# Helper Functions
# =============================================================================


def get_trace_context(websocket: WebSocket) -> Optional[TraceContext]:
    """
    Extract trace context from WebSocket connection.
    
    Args:
        websocket: FastAPI WebSocket instance
        
    Returns:
        TraceContext if available, None otherwise
        
    Example:
        >>> @app.websocket("/ws")
        >>> async def websocket_endpoint(websocket: WebSocket):
        >>>     await websocket.accept()
        >>>     trace_ctx = get_trace_context(websocket)
        >>>     logger.info("processing", trace_id=trace_ctx.trace_id)
    """
    if not hasattr(websocket, "scope"):
        return None
    
    scope = websocket.scope
    state = scope.get("state", {})
    return state.get("trace_context")


def inject_trace_into_packet(
    packet_dict: dict[str, Any],
    trace_context: Optional[TraceContext] = None,
) -> dict[str, Any]:
    """
    Inject trace context into packet dictionary.
    
    Mutates the packet dict in-place to add trace_id and correlation_id.
    
    Args:
        packet_dict: Packet dictionary to inject trace context into
        trace_context: TraceContext to inject (if None, generates new one)
        
    Returns:
        Modified packet dict (same object, mutated in-place)
        
    Example:
        >>> packet = {"packet_type": "event", "payload": {...}}
        >>> trace_ctx = get_trace_context(websocket)
        >>> inject_trace_into_packet(packet, trace_ctx)
        >>> # packet now has trace_id and correlation_id
    """
    if trace_context is None:
        trace_context = TraceContext()
    
    packet_dict["trace_id"] = trace_context.trace_id
    packet_dict["correlation_id"] = trace_context.correlation_id
    
    return packet_dict


# =============================================================================
# Module Exports
# =============================================================================

__all__ = [
    "WebSocketTracingMiddleware",
    "TraceContext",
    "get_trace_context",
    "inject_trace_into_packet",
]
