"""
Core decorators for L9 codebase.

Provides reusable decorators for marking code patterns and intentions.
"""

# ============================================================================
__dora_meta__ = {
    "component_name": "Decorators",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2026-01-17T14:57:53Z",
    "updated_at": "2026-01-17T23:47:56Z",
    "layer": "foundation",
    "domain": "core",
    "module_name": "decorators",
    "type": "service",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": [],
        "memory_layers": [],
        "imported_by": [
            "agents.base_agent",
            "agents.cursor.integrations.cursor_gateway",
            "agents.cursor.integrations.cursor_langgraph",
            "agents.research_agent",
            "api.agent_routes",
            "api.e2e_slack_audit",
            "api.memory.router",
            "api.os_routes",
            "api.routes.commands",
            "api.routes.cursor",
        ],
    },
}
# ============================================================================

from typing import Callable, TypeVar, Any

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

    def decorator(func: F) -> F:
        func._must_stay_async = reason  # type: ignore[attr-defined]
        func._must_stay_async_marker = True  # type: ignore[attr-defined]
        return func

    return decorator


def must_stay_async_route(func: F) -> F:
    """Shorthand for FastAPI/ASGI route handlers."""
    return must_stay_async("FastAPI/ASGI route handler")(func)


def must_stay_async_protocol(func: F) -> F:
    """Shorthand for async protocol methods (__aenter__, __aexit__, __call__)."""
    return must_stay_async("async protocol method")(func)


def must_stay_async_interface(func: F) -> F:
    """Shorthand for interface methods where callers use await."""
    return must_stay_async("callers use await")(func)


# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "COR-FOUN-001",
    "governance_level": "critical",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": [
        "api",
        "async",
        "core",
        "event-driven",
        "foundation",
        "linting",
        "service",
    ],
    "keywords": [
        "async",
        "decorator",
        "decorators",
        "interface",
        "memory",
        "must",
        "protocol",
        "route",
    ],
    "business_value": "Provides reusable decorators for marking code patterns and intentions.",
    "last_modified": "2026-01-17T23:47:56Z",
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
