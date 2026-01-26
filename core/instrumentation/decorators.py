"""
L9 Core Instrumentation - Auto-Instrumentation Decorators
==========================================================

Decorators for automatic tracing, logging, and observability.

Implements Phase 0 Plan 10: Auto-Instrumentation Decorators

Key responsibilities:
- @traced decorator for automatic trace_id propagation
- @timed decorator for execution time tracking
- @logged decorator for automatic structured logging
- @with_source_location decorator for source code location capture

This module does NOT:
- Replace manual logging (augments it)
- Perform profiling (use profilers for that)
- Handle errors (use error handlers for that)

Version: 1.0.0
GMP: refactor-phase0-plan10
"""

from __future__ import annotations

# ============================================================================
# DORA HEADER META
# ============================================================================
__dora_meta__ = {
    "component_id": "COR-INST-001",
    "component_name": "AutoInstrumentationDecorators",
    "module_version": "1.0.0",
    "created_at": "2026-01-21T00:00:00Z",
    "created_by": "L9_Refactoring_Phase0",
    "layer": "foundation",
    "domain": "instrumentation",
    "type": "decorator",
    "status": "active",
    "governance_level": "standard",
    "compliance_required": True,
    "audit_trail": True,
    "purpose": "Auto-instrumentation decorators for observability and tracing",
    "dependencies": [
        "structlog",
    ],
}
# ============================================================================

import functools
import inspect
import time
from collections.abc import Callable
from contextvars import ContextVar
from typing import Any, TypeVar
from uuid import uuid4

import structlog

logger = structlog.get_logger(__name__)

# Type variable for generic decorator typing
F = TypeVar("F", bound=Callable[..., Any])

# Context variable for trace_id propagation
_trace_id_context: ContextVar[str | None] = ContextVar("trace_id", default=None)
_correlation_id_context: ContextVar[str | None] = ContextVar(
    "correlation_id", default=None
)


# =============================================================================
# Context Management
# =============================================================================


def get_current_trace_id() -> str | None:
    """
    Get current trace_id from context.

    Returns:
        Current trace_id or None if not set

    Example:
        >>> trace_id = get_current_trace_id()
        >>> if trace_id:
        >>>     logger.info("processing", trace_id=trace_id)
    """
    return _trace_id_context.get()


def set_trace_id(trace_id: str) -> None:
    """
    Set trace_id in current context.

    Args:
        trace_id: Trace ID to set

    Example:
        >>> set_trace_id(str(uuid4()))
        >>> # All subsequent @traced calls will use this trace_id
    """
    _trace_id_context.set(trace_id)


def get_current_correlation_id() -> str | None:
    """
    Get current correlation_id from context.

    Returns:
        Current correlation_id or None if not set
    """
    return _correlation_id_context.get()


def set_correlation_id(correlation_id: str) -> None:
    """
    Set correlation_id in current context.

    Args:
        correlation_id: Correlation ID to set
    """
    _correlation_id_context.set(correlation_id)


# =============================================================================
# Source Location Capture
# =============================================================================


def capture_source_location(frame: inspect.FrameInfo | None = None) -> dict[str, Any]:
    """
    Capture source code location from call stack.

    Args:
        frame: Optional frame info (defaults to caller's frame)

    Returns:
        Dict with file, line, function keys

    Example:
        >>> location = capture_source_location()
        >>> print(f"Called from {location['file']}:{location['line']}")
    """
    if frame is None:
        # Get caller's frame (skip this function)
        stack = inspect.stack()
        if len(stack) > 1:
            frame = stack[1]
        else:
            return {"file": "unknown", "line": 0, "function": "unknown"}

    return {
        "file": frame.filename,
        "line": frame.lineno,
        "function": frame.function,
    }


# =============================================================================
# Decorators
# =============================================================================


def traced[F: Callable[..., Any]](
    func: F | None = None,
    *,
    trace_id: str | None = None,
    correlation_id: str | None = None,
    log_entry: bool = True,
    log_exit: bool = True,
) -> F:
    """
    Decorator for automatic trace_id propagation.

    Injects trace_id and correlation_id into function context,
    enabling distributed tracing across function calls.

    Args:
        func: Function to decorate (auto-filled when used as @traced)
        trace_id: Override trace_id (defaults to context or generates new)
        correlation_id: Override correlation_id (defaults to trace_id)
        log_entry: Log function entry
        log_exit: Log function exit

    Returns:
        Decorated function with trace context

    Example:
        >>> @traced
        >>> async def process_task(task_id: str):
        >>> # trace_id automatically available in context
        >>>     logger.info("processing", task_id=task_id)

        >>> @traced(trace_id="custom-trace-id")
        >>> def custom_trace():
        >>>     pass
    """

    def decorator(f: F) -> F:
        @functools.wraps(f)
        async def async_wrapper(*args, **kwargs):
            # Get or generate trace IDs
            current_trace_id = trace_id or get_current_trace_id() or str(uuid4())
            current_correlation_id = (
                correlation_id or get_current_correlation_id() or current_trace_id
            )

            # Set context
            _trace_id_context.set(current_trace_id)
            _correlation_id_context.set(current_correlation_id)

            # Log entry
            if log_entry:
                logger.debug(
                    f"{f.__name__}.entry",
                    trace_id=current_trace_id,
                    correlation_id=current_correlation_id,
                    function=f.__name__,
                    module=f.__module__,
                )

            try:
                result = await f(*args, **kwargs)

                # Log exit
                if log_exit:
                    logger.debug(
                        f"{f.__name__}.exit",
                        trace_id=current_trace_id,
                        correlation_id=current_correlation_id,
                        function=f.__name__,
                    )

                return result
            except Exception as e:
                logger.error(
                    f"{f.__name__}.error",
                    trace_id=current_trace_id,
                    correlation_id=current_correlation_id,
                    function=f.__name__,
                    error=str(e),
                    error_type=type(e).__name__,
                )
                raise

        @functools.wraps(f)
        def sync_wrapper(*args, **kwargs):
            # Get or generate trace IDs
            current_trace_id = trace_id or get_current_trace_id() or str(uuid4())
            current_correlation_id = (
                correlation_id or get_current_correlation_id() or current_trace_id
            )

            # Set context
            _trace_id_context.set(current_trace_id)
            _correlation_id_context.set(current_correlation_id)

            # Log entry
            if log_entry:
                logger.debug(
                    f"{f.__name__}.entry",
                    trace_id=current_trace_id,
                    correlation_id=current_correlation_id,
                    function=f.__name__,
                    module=f.__module__,
                )

            try:
                result = f(*args, **kwargs)

                # Log exit
                if log_exit:
                    logger.debug(
                        f"{f.__name__}.exit",
                        trace_id=current_trace_id,
                        correlation_id=current_correlation_id,
                        function=f.__name__,
                    )

                return result
            except Exception as e:
                logger.error(
                    f"{f.__name__}.error",
                    trace_id=current_trace_id,
                    correlation_id=current_correlation_id,
                    function=f.__name__,
                    error=str(e),
                    error_type=type(e).__name__,
                )
                raise

        # Return appropriate wrapper based on function type
        if inspect.iscoroutinefunction(f):
            return async_wrapper
        return sync_wrapper

    # Support both @traced and @traced()
    if func is None:
        return decorator
    return decorator(func)


def timed[F: Callable[..., Any]](
    func: F | None = None,
    *,
    log_threshold_ms: float | None = None,
) -> F:
    """
    Decorator for execution time tracking.

    Logs execution time for function calls. Optionally only logs
    if execution time exceeds threshold.

    Args:
        func: Function to decorate
        log_threshold_ms: Only log if execution time exceeds this (milliseconds)

    Returns:
        Decorated function with timing

    Example:
        >>> @timed
        >>> async def slow_operation():
        >>>     await asyncio.sleep(1)
        >>> # Logs: slow_operation.timed duration_ms=1000.0

        >>> @timed(log_threshold_ms=100)
        >>> def fast_operation():
        >>>     pass  # Won't log if < 100ms
    """

    def decorator(f: F) -> F:
        @functools.wraps(f)
        async def async_wrapper(*args, **kwargs):
            start_time = time.perf_counter()

            try:
                return await f(*args, **kwargs)
            finally:
                duration_ms = (time.perf_counter() - start_time) * 1000

                # Only log if threshold not set or exceeded
                if log_threshold_ms is None or duration_ms >= log_threshold_ms:
                    logger.info(
                        f"{f.__name__}.timed",
                        function=f.__name__,
                        duration_ms=round(duration_ms, 2),
                        trace_id=get_current_trace_id(),
                    )

        @functools.wraps(f)
        def sync_wrapper(*args, **kwargs):
            start_time = time.perf_counter()

            try:
                return f(*args, **kwargs)
            finally:
                duration_ms = (time.perf_counter() - start_time) * 1000

                # Only log if threshold not set or exceeded
                if log_threshold_ms is None or duration_ms >= log_threshold_ms:
                    logger.info(
                        f"{f.__name__}.timed",
                        function=f.__name__,
                        duration_ms=round(duration_ms, 2),
                        trace_id=get_current_trace_id(),
                    )

        # Return appropriate wrapper based on function type
        if inspect.iscoroutinefunction(f):
            return async_wrapper
        return sync_wrapper

    # Support both @timed and @timed()
    if func is None:
        return decorator
    return decorator(func)


def logged[F: Callable[..., Any]](
    func: F | None = None,
    *,
    level: str = "info",
    log_args: bool = False,
    log_result: bool = False,
) -> F:
    """
    Decorator for automatic structured logging.

    Logs function entry, exit, and optionally arguments and results.

    Args:
        func: Function to decorate
        level: Log level (debug, info, warning, error)
        log_args: Log function arguments
        log_result: Log function result

    Returns:
        Decorated function with logging

    Example:
        >>> @logged(level="debug", log_args=True)
        >>> def process_data(data: dict):
        >>>     return data["result"]
    """

    def decorator(f: F) -> F:
        log_func = getattr(logger, level, logger.info)

        @functools.wraps(f)
        async def async_wrapper(*args, **kwargs):
            log_data = {
                "function": f.__name__,
                "module": f.__module__,
                "trace_id": get_current_trace_id(),
            }

            if log_args:
                log_data["args"] = str(args)[:100]  # Truncate for safety
                log_data["kwargs"] = {k: str(v)[:100] for k, v in kwargs.items()}

            log_func(f"{f.__name__}.called", **log_data)

            result = await f(*args, **kwargs)

            if log_result:
                log_data["result"] = str(result)[:100]  # Truncate for safety

            log_func(f"{f.__name__}.completed", **log_data)

            return result

        @functools.wraps(f)
        def sync_wrapper(*args, **kwargs):
            log_data = {
                "function": f.__name__,
                "module": f.__module__,
                "trace_id": get_current_trace_id(),
            }

            if log_args:
                log_data["args"] = str(args)[:100]  # Truncate for safety
                log_data["kwargs"] = {k: str(v)[:100] for k, v in kwargs.items()}

            log_func(f"{f.__name__}.called", **log_data)

            result = f(*args, **kwargs)

            if log_result:
                log_data["result"] = str(result)[:100]  # Truncate for safety

            log_func(f"{f.__name__}.completed", **log_data)

            return result

        # Return appropriate wrapper based on function type
        if inspect.iscoroutinefunction(f):
            return async_wrapper
        return sync_wrapper

    # Support both @logged and @logged()
    if func is None:
        return decorator
    return decorator(func)


def with_source_location[F: Callable[..., Any]](func: F) -> F:
    """
    Decorator to capture source code location.

    Injects source_location into function kwargs if it accepts it.

    Args:
        func: Function to decorate

    Returns:
        Decorated function with source location

    Example:
        >>> @with_source_location
        >>> def create_packet(payload: dict, source_location: dict = None):
        >>>     packet = PacketEnvelope(
        >>>         packet_type="event",
        >>>         payload=payload,
        >>>         source_location=source_location,
        >>>     )
    """

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        # Capture source location
        stack = inspect.stack()
        if len(stack) > 1:
            caller_frame = stack[1]
            source_location = capture_source_location(caller_frame)

            # Inject if function accepts source_location parameter
            sig = inspect.signature(func)
            if "source_location" in sig.parameters:
                kwargs["source_location"] = source_location

        return func(*args, **kwargs)

    return wrapper


# =============================================================================
# Module Exports
# =============================================================================

__all__ = [
    "capture_source_location",
    "get_current_correlation_id",
    "get_current_trace_id",
    "logged",
    "set_correlation_id",
    "set_trace_id",
    "timed",
    "traced",
    "with_source_location",
]
