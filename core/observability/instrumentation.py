"""
Instrumentation decorators for automatic span creation and tracing.

Provides @trace_span, @trace_llm_call, @trace_tool_call, @trace_governance_check.
"""


import asyncio
import functools
from collections.abc import Callable
from typing import Any, TypeVar

import structlog

from .models import (
    GovernanceCheckSpan,
    LLMGenerationSpan,
    Span,
    SpanKind,
    SpanStatus,
    ToolCallSpan,
)

logger = structlog.get_logger(__name__)

T = TypeVar("T")


def trace_span(
    name: str,
    kind: SpanKind = SpanKind.INTERNAL,
    **default_attributes: Any,
) -> Callable:
    """
    Decorator to automatically create and export spans.

    Works with both sync and async functions.

    Usage:
        @trace_span("my_operation")
        @must_stay_async("callers use await")
        async def my_func():
            ...
    """

    @wraps(name)
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        """Inner decorator that wraps the target function.

        Args:
            func: The function to wrap with span tracing.

        Returns:
            Wrapped function with automatic span creation.
        """
        is_async = asyncio.iscoroutinefunction(func)

        if is_async:

            @functools.wraps(func)
            async def async_wrapper(*args: Any, **kwargs: Any) -> T:
                """Async wrapper that creates and exports spans."""
                from .service import ObservabilityService

                service = ObservabilityService.get()
                if not service or not service.config.enabled:
                    return await func(*args, **kwargs)

                ctx = service.current_trace_context()
                span = Span.start(
                    name=name,
                    trace_id=ctx.trace_id,
                    parent_span_id=ctx.span_id,
                    kind=kind,
                    **default_attributes,
                )

                try:
                    result = await func(*args, **kwargs)
                    span.finish(status=SpanStatus.OK)
                    return result
                except Exception as exc:
                    span.finish(status=SpanStatus.ERROR, error=str(exc))
                    raise
                finally:
                    service.export_span(span)

            return async_wrapper

        @functools.wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> T:
            """Sync wrapper that creates and exports spans."""
            from .service import ObservabilityService

            service = ObservabilityService.get()
            if not service or not service.config.enabled:
                return func(*args, **kwargs)

            ctx = service.current_trace_context()
            span = Span.start(
                name=name,
                trace_id=ctx.trace_id,
                parent_span_id=ctx.span_id,
                kind=kind,
                **default_attributes,
            )

            try:
                result = func(*args, **kwargs)
                span.finish(status=SpanStatus.OK)
                return result
            except Exception as exc:
                span.finish(status=SpanStatus.ERROR, error=str(exc))
                raise
            finally:
                service.export_span(span)

        return sync_wrapper

    return decorator


def trace_llm_call(
    model: str = "gpt-4",
) -> Callable:
    """
    Decorator to trace LLM generation calls.

    Usage:
        @trace_llm_call(model="gpt-4")
        @must_stay_async("callers use await")
        async def generate_response(prompt: str) -> str:
            ...
    """

    @wraps(model)
    def decorator(func: Callable) -> Callable:
        """Inner decorator that wraps the target function.

        Args:
            func: The function to wrap with LLM call tracing.

        Returns:
            Wrapped function with automatic LLM span creation.
        """
        is_async = asyncio.iscoroutinefunction(func)

        if is_async:

            @functools.wraps(func)
            async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
                """Async wrapper that creates and exports LLM spans."""
                from .service import ObservabilityService

                service = ObservabilityService.get()
                if not service or not service.config.enabled:
                    return await func(*args, **kwargs)

                ctx = service.current_trace_context()
                span = LLMGenerationSpan.start(
                    name=f"llm.{func.__name__}",
                    trace_id=ctx.trace_id,
                    parent_span_id=ctx.span_id,
                    kind=SpanKind.CLIENT,
                    model=model,
                )

                try:
                    result = await func(*args, **kwargs)
                    span.finish(status=SpanStatus.OK)
                    return result
                except Exception as exc:
                    span.finish(status=SpanStatus.ERROR, error=str(exc))
                    raise
                finally:
                    service.export_span(span)

            return async_wrapper

        @functools.wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            """Sync wrapper that creates and exports LLM spans."""
            from .service import ObservabilityService

            service = ObservabilityService.get()
            if not service or not service.config.enabled:
                return func(*args, **kwargs)

            ctx = service.current_trace_context()
            span = LLMGenerationSpan.start(
                name=f"llm.{func.__name__}",
                trace_id=ctx.trace_id,
                parent_span_id=ctx.span_id,
                kind=SpanKind.CLIENT,
                model=model,
            )

            try:
                result = func(*args, **kwargs)
                span.finish(status=SpanStatus.OK)
                return result
            except Exception as exc:
                span.finish(status=SpanStatus.ERROR, error=str(exc))
                raise
            finally:
                service.export_span(span)

        return sync_wrapper

    return decorator


def trace_tool_call(
    tool_name: str,
) -> Callable:
    """
    Decorator to trace tool invocations.

    Usage:
        @trace_tool_call("web_search")
        @must_stay_async("callers use await")
        async def search(query: str) -> str:
            ...
    """

    @wraps(tool_name)
    def decorator(func: Callable) -> Callable:
        """Inner decorator that wraps the target function.

        Args:
            func: The function to wrap with tool call tracing.

        Returns:
            Wrapped function with automatic tool span creation.
        """
        is_async = asyncio.iscoroutinefunction(func)

        if is_async:

            @functools.wraps(func)
            async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
                """Async wrapper that creates and exports tool spans."""
                from .service import ObservabilityService

                service = ObservabilityService.get()
                if not service or not service.config.enabled:
                    return await func(*args, **kwargs)

                ctx = service.current_trace_context()
                span = ToolCallSpan.start(
                    name=f"tool.{tool_name}",
                    trace_id=ctx.trace_id,
                    parent_span_id=ctx.span_id,
                    kind=SpanKind.CLIENT,
                    tool_name=tool_name,
                    tool_input=kwargs,
                )

                try:
                    result = await func(*args, **kwargs)
                    span.tool_output = result
                    span.finish(status=SpanStatus.OK)
                    return result
                except Exception as exc:
                    span.tool_error = str(exc)
                    span.finish(status=SpanStatus.ERROR, error=str(exc))
                    raise
                finally:
                    service.export_span(span)

            return async_wrapper

        @functools.wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            """Sync wrapper that creates and exports tool spans."""
            from .service import ObservabilityService

            service = ObservabilityService.get()
            if not service or not service.config.enabled:
                return func(*args, **kwargs)

            ctx = service.current_trace_context()
            span = ToolCallSpan.start(
                name=f"tool.{tool_name}",
                trace_id=ctx.trace_id,
                parent_span_id=ctx.span_id,
                kind=SpanKind.CLIENT,
                tool_name=tool_name,
                tool_input=kwargs,
            )

            try:
                result = func(*args, **kwargs)
                span.tool_output = result
                span.finish(status=SpanStatus.OK)
                return result
            except Exception as exc:
                span.tool_error = str(exc)
                span.finish(status=SpanStatus.ERROR, error=str(exc))
                raise
            finally:
                service.export_span(span)

        return sync_wrapper

    return decorator


def trace_governance_check(
    policy_name: str,
) -> Callable:
    """
    Decorator to trace governance policy checks.

    Usage:
        @trace_governance_check("allow_external_tools")
        @must_stay_async("callers use await")
        async def check_policy(action: str) -> bool:
            ...
    """

    @wraps(policy_name)
    def decorator(func: Callable) -> Callable:
        """Inner decorator that wraps the target function.

        Args:
            func: The function to wrap with governance check tracing.

        Returns:
            Wrapped function with automatic governance span creation.
        """
        is_async = asyncio.iscoroutinefunction(func)

        if is_async:

            @functools.wraps(func)
            async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
                """Async wrapper that creates and exports governance spans."""
                from .service import ObservabilityService

                service = ObservabilityService.get()
                if not service or not service.config.enabled:
                    return await func(*args, **kwargs)

                ctx = service.current_trace_context()
                span = GovernanceCheckSpan.start(
                    name=f"governance.{policy_name}",
                    trace_id=ctx.trace_id,
                    parent_span_id=ctx.span_id,
                    kind=SpanKind.INTERNAL,
                    policy_name=policy_name,
                )

                try:
                    result = await func(*args, **kwargs)
                    span.policy_result = "allow" if result else "deny"
                    span.finish(status=SpanStatus.OK)
                    return result
                except Exception as exc:
                    span.policy_result = "error"
                    span.policy_reason = str(exc)
                    span.finish(status=SpanStatus.ERROR, error=str(exc))
                    raise
                finally:
                    service.export_span(span)

            return async_wrapper

        @functools.wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            """Sync wrapper that creates and exports governance spans."""
            from .service import ObservabilityService

            service = ObservabilityService.get()
            if not service or not service.config.enabled:
                return func(*args, **kwargs)

            ctx = service.current_trace_context()
            span = GovernanceCheckSpan.start(
                name=f"governance.{policy_name}",
                trace_id=ctx.trace_id,
                parent_span_id=ctx.span_id,
                kind=SpanKind.INTERNAL,
                policy_name=policy_name,
            )

            try:
                result = func(*args, **kwargs)
                span.policy_result = "allow" if result else "deny"
                span.finish(status=SpanStatus.OK)
                return result
            except Exception as exc:
                span.policy_result = "error"
                span.policy_reason = str(exc)
                span.finish(status=SpanStatus.ERROR, error=str(exc))
                raise
            finally:
                service.export_span(span)

        return sync_wrapper

    return decorator


# Runtime execution trace - updated automatically on every execution
