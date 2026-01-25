# core/observability/observability_context.py
"""
Unified OpenTelemetry Context Propagation

Provides:
- W3C Trace Context support
- Correlation ID for request chains
- Span tracking
- Automatic telemetry logging

All async code should use these context managers.
"""

# ============================================================================
__dora_meta__ = {
    "component_name": "Observability Context",
    "module_version": "1.0.0",
    "created_by": "L9_Codegen_Engine",
    "created_at": "2026-01-25T06:00:00Z",
    "updated_at": "2026-01-25T06:00:00Z",
    "layer": "foundation",
    "domain": "observability",
    "module_name": "observability_context",
    "type": "context_manager",
    "status": "active",
}
# ============================================================================

import contextvars
import uuid
from contextlib import asynccontextmanager
from typing import Any

import structlog

logger = structlog.get_logger(__name__)

# =========================================================================
# Context Variables (thread-safe, async-safe)
# =========================================================================

_trace_id: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "trace_id",
    default=None,
)
_span_id: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "span_id",
    default=None,
)
_correlation_id: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "correlation_id",
    default=None,
)
_user_id: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "user_id",
    default=None,
)
_request_id: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "request_id",
    default=None,
)


# =========================================================================
# Context Access
# =========================================================================


def get_trace_id() -> str:
    """Get current trace ID (or generate new one)."""
    tid = _trace_id.get()
    if not tid:
        tid = str(uuid.uuid4())
        _trace_id.set(tid)
    return tid


def get_span_id() -> str:
    """Get current span ID (or generate new one)."""
    sid = _span_id.get()
    if not sid:
        sid = str(uuid.uuid4())[:16]  # 16 chars for span ID
        _span_id.set(sid)
    return sid


def get_correlation_id() -> str:
    """Get current correlation ID (or generate new one)."""
    cid = _correlation_id.get()
    if not cid:
        cid = str(uuid.uuid4())
        _correlation_id.set(cid)
    return cid


def get_user_id() -> str | None:
    """Get current user ID."""
    return _user_id.get()


def get_request_id() -> str | None:
    """Get current request ID."""
    return _request_id.get()


# =========================================================================
# Context Setting
# =========================================================================


def set_trace_id(trace_id: str) -> None:
    """Set trace ID."""
    _trace_id.set(trace_id)


def set_span_id(span_id: str) -> None:
    """Set span ID."""
    _span_id.set(span_id)


def set_correlation_id(correlation_id: str) -> None:
    """Set correlation ID."""
    _correlation_id.set(correlation_id)


def set_user_id(user_id: str | None) -> None:
    """Set user ID."""
    _user_id.set(user_id)


def set_request_id(request_id: str | None) -> None:
    """Set request ID."""
    _request_id.set(request_id)


# =========================================================================
# W3C Trace Context
# =========================================================================


def get_trace_context() -> dict[str, str]:
    """
    Get W3C Trace Context headers.

    Returns dict suitable for HTTP headers or span creation.
    """
    return {
        "traceparent": f"00-{get_trace_id()}-{get_span_id()}-01",
        "tracestate": f"correlation={get_correlation_id()}",
    }


def set_trace_context_from_headers(headers: dict[str, str]) -> None:
    """
    Extract and set trace context from W3C headers.

    Supports:
    - traceparent: "00-trace_id-span_id-flags"
    - tracestate: "correlation=..."
    - X-Correlation-ID (fallback)
    """
    # Parse traceparent
    if "traceparent" in headers:
        parts = headers["traceparent"].split("-")
        if len(parts) >= 3:
            set_trace_id(parts[1])
            set_span_id(parts[2])

    # Parse tracestate
    if "tracestate" in headers:
        state = headers["tracestate"]
        if "correlation=" in state:
            cid = state.split("correlation=")[1].split(";")[0]
            set_correlation_id(cid)

    # Fallback: X-Correlation-ID
    if "x-correlation-id" in headers:
        set_correlation_id(headers["x-correlation-id"])


# =========================================================================
# Context Managers
# =========================================================================


@asynccontextmanager
async def observability_context(
    operation: str,
    trace_id: str | None = None,
    correlation_id: str | None = None,
    user_id: str | None = None,
    **metadata: Any,
):
    """
    Async context manager for observability.

    Sets up tracing, correlation, and automatic logging.

    Usage:
        async with observability_context("write_packet", user_id="user123"):
            # Code here has tracing enabled
            pass

    Args:
        operation: Operation name for logging
        trace_id: Optional trace ID (auto-generated if not provided)
        correlation_id: Optional correlation ID (auto-generated if not provided)
        user_id: Optional user ID
        **metadata: Additional context metadata

    Yields:
        Context dict with trace/correlation IDs
    """
    # Set context variables
    old_trace_id = _trace_id.get()
    old_span_id = _span_id.get()
    old_correlation_id = _correlation_id.get()
    old_user_id = _user_id.get()

    if trace_id:
        _trace_id.set(trace_id)
    else:
        _trace_id.set(str(uuid.uuid4()))

    if correlation_id:
        _correlation_id.set(correlation_id)
    else:
        _correlation_id.set(str(uuid.uuid4()))

    new_span_id = str(uuid.uuid4())[:16]
    _span_id.set(new_span_id)

    if user_id:
        _user_id.set(user_id)

    # Log operation start
    context_dict = {
        "trace_id": get_trace_id(),
        "span_id": new_span_id,
        "correlation_id": get_correlation_id(),
        **metadata,
    }

    logger.info(f"{operation}_start", **context_dict)

    try:
        yield context_dict
        logger.info(f"{operation}_success", **context_dict)

    except Exception as e:
        logger.error(
            f"{operation}_error",
            error=str(e),
            error_type=type(e).__name__,
            **context_dict,
        )
        raise

    finally:
        # Restore old context
        if old_trace_id is not None:
            _trace_id.set(old_trace_id)
        else:
            _trace_id.set(None)

        if old_span_id is not None:
            _span_id.set(old_span_id)
        else:
            _span_id.set(None)

        if old_correlation_id is not None:
            _correlation_id.set(old_correlation_id)
        else:
            _correlation_id.set(None)

        if old_user_id is not None:
            _user_id.set(old_user_id)
        else:
            _user_id.set(None)


@asynccontextmanager
async def span(
    name: str,
    **metadata: Any,
):
    """
    Create a new span within current trace.

    Usage:
        async with span("write_entities", count=10):
            # Nested span
            pass

    Args:
        name: Span name
        **metadata: Span metadata

    Yields:
        Span dict with IDs
    """
    new_span_id = str(uuid.uuid4())[:16]
    old_span_id = _span_id.get()
    _span_id.set(new_span_id)

    span_dict = {
        "trace_id": get_trace_id(),
        "span_id": new_span_id,
        "parent_span_id": old_span_id,
        **metadata,
    }

    logger.debug(f"{name}_span_start", **span_dict)

    try:
        yield span_dict
        logger.debug(f"{name}_span_success", **span_dict)

    except Exception as e:
        logger.error(
            f"{name}_span_error",
            error=str(e),
            **span_dict,
        )
        raise

    finally:
        if old_span_id is not None:
            _span_id.set(old_span_id)
        else:
            _span_id.set(None)


# =========================================================================
# DORA Footer
# =========================================================================

__dora_footer__ = {
    "component_id": "CORE-OBSV-001",
    "governance_level": "standard",
    "compliance_required": False,
    "tags": ["observability", "tracing", "context"],
    "keywords": ["trace", "span", "correlation", "context"],
    "business_value": "Unified OpenTelemetry context propagation for distributed tracing.",
    "last_modified": "2026-01-25T06:00:00Z",
    "modified_by": "L9_Codegen_Engine",
}
# ============================================================================
