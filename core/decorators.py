"""
Core decorators for L9 codebase.

Provides reusable decorators for marking code patterns and intentions.
"""

from __future__ import annotations


from collections.abc import Callable
from typing import TYPE_CHECKING, Any, TypeVar
from functools import wraps

F = TypeVar("F", bound=Callable[..., Any])


def must_stay_async(reason: str) -> Callable[[F], F]:
    """
    Marker decorator documenting why a function must remain async.

    Use this to prevent AI code reviewers and linters from flagging
    async functions that don't contain await as issues.

    Categories:
    - "FastAPI/ASGI route handler" - ASGI requires async def
    - "async context manager protocol" - __aenter__/__aexit__ must be async
    - "callers use await" - Changing would break API contract
    - "LangGraph node protocol" - LangGraph requires async callable
    - "health endpoint convention" - FastAPI health check pattern
    - "future await planned" - Placeholder for upcoming async implementation

    Example:
        @must_stay_async("callers use await")
        async def search_memory(self, query: str) -> List[Dict]:
            # Currently returns sync, but callers use `await search_memory()`
            return []

    Args:
        reason: Human-readable explanation of why async is required

    Returns:
        Decorated function with _must_stay_async attribute set
    """

    @wraps(reason)
    def decorator(func: F) -> F:
        """
        Marks a function as requiring to stay asynchronous within the L9 codebase.
        Args:
            func: The function to be decorated, indicating it must remain async.
        Returns:
            The decorated function with added attributes for async enforcement.
        """
        func._must_stay_async = reason  # type: ignore[attr-defined]
        func._must_stay_async_marker = True  # type: ignore[attr-defined]
        return func

    return decorator


def must_stay_async_route[F](func: F) -> F:
    """Shorthand for FastAPI/ASGI route handlers."""
    return must_stay_async("FastAPI/ASGI route handler")(func)


def must_stay_async_protocol[F](func: F) -> F:
    """Shorthand for async protocol methods (__aenter__, __aexit__, __call__)."""
    return must_stay_async("async protocol method")(func)


def must_stay_async_interface[F](func: F) -> F:
    """Shorthand for interface methods where callers use await."""
    return must_stay_async("callers use await")(func)


def __getattr__(name: str):
    """Lazy re-export of register_tool to avoid circular import with runtime."""
    if name == "register_tool":
        if TYPE_CHECKING:
            from runtime.tool_registry import register_tool
        else:
            # Runtime import to break cycle
            from runtime.tool_registry import register_tool
        return register_tool
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


# Runtime execution trace - updated automatically on every execution
