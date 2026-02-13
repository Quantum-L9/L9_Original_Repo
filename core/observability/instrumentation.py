"""
Instrumentation decorators for automatic span creation and tracing.

Provides @trace_span, @trace_llm_call, @trace_tool_call, @trace_governance_check.
"""

# ============================================================================
__dora_meta__ = {
    "component_name": "Instrumentation",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2026-01-06T15:07:54Z",
    "updated_at": "2026-01-14T15:03:00Z",
    "layer": "foundation",
    "domain": "core",
    "module_name": "instrumentation",
    "type": "service",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": [],
        "memory_layers": [],
        "imported_by": ["tests.core.observability.test_observability_integration"],
    },
}
# ============================================================================

import asyncio
import functools
from collections.abc import Callable
from typing import Any, TypeVar

import structlog

from core.decorators import must_stay_async

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


# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "COR-FOUN-001",
    "governance_level": "critical",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": ["async", "core", "foundation", "logging", "service", "tracing"],
    "keywords": [
        "async",
        "check",
        "decorator",
        "generate",
        "governance",
        "instrumentation",
        "llm",
        "policy",
    ],
    "business_value": "Provides @trace_span, @trace_llm_call, @trace_tool_call, @trace_governance_check.",
    "last_modified": "2026-01-14T15:03:00Z",
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
