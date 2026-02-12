"""
L9 Runtime - Tool Executor Auto-Registration System
====================================================

Automatic discovery and registration of tool executor functions.

This module eliminates the manual TOOL_EXECUTORS dictionary by providing
a decorator-based registration system that automatically discovers and
registers tool functions.

Version: 1.0.0
"""

from __future__ import annotations

# ============================================================================
__dora_meta__ = {
    "component_name": "Tool Executor Auto-Registration",
    "module_version": "1.0.0",
    "created_by": "L9 Auto-Wiring Team",
    "created_at": "2026-01-18T00:00:00Z",
    "updated_at": "2026-01-18T00:00:00Z",
    "layer": "runtime",
    "domain": "tools",
    "module_name": "tool_registry",
    "type": "service",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": [],
        "memory_layers": [],
        "imported_by": ["runtime.l_tools"],
    },
}
# ============================================================================

from collections.abc import Callable
from typing import Any, ParamSpec, TypeVar

import structlog

from core.auto_registry import AutoRegistry

logger = structlog.get_logger(__name__)

# Type variables for decorator type preservation
P = ParamSpec("P")
R = TypeVar("R")


# =============================================================================
# Tool Executor Registry
# =============================================================================


def _validate_tool_executor(func: Callable) -> bool:
    """Validate that an object is a callable tool executor."""
    return callable(func)


# Global tool executor registry
tool_executor_registry = AutoRegistry[Callable](
    name="tool_executors", validator=_validate_tool_executor, allow_duplicates=False
)


def register_tool(
    name: str | None = None,
    category: str | None = None,
    priority: int = 0,
    **metadata: Any,
) -> Callable[[Callable[P, R]], Callable[P, R]]:
    """
    Decorator to register a tool executor function for auto-wiring.

    This decorator marks a tool executor function for automatic
    discovery and registration in the TOOL_EXECUTORS dictionary.

    Args:
        name: Tool identifier (defaults to function name)
        category: Tool category (e.g., "memory", "redis", "neo4j")
        priority: Registration priority (higher = loaded first)
        **metadata: Additional metadata (description, rate_limit, etc.)

    Example:
        @register_tool(category="memory", priority=10)
        async def memory_search(query: str, **kwargs):
            # ... implementation ...
            return results

        # Or with explicit name
        @register_tool(name="custom_tool", category="custom")
        async def my_tool_function(**kwargs):
            return {"status": "ok"}
    """

    def decorator(func: Callable[P, R]) -> Callable[P, R]:
        """
        Performs registration of a tool executor function in the auto-registration system.
        Args:
            func: The tool executor function to be registered.
            name: Optional custom name for the tool; defaults to function's __name__.
            prio: Optional priority level for registration.
        Returns:
            The registered function, now registered in the tool executor registry.
        """
        # Register the function directly (not as a factory)
        tool_name = name or func.__name__

        # Attach metadata to the function for introspection by tests and
        # discovery pipelines (e.g. TOOL_PACKAGES scan for _tool_metadata).
        func._tool_metadata = {  # type: ignore[attr-defined]
            "name": tool_name,
            "category": category or "",
            "priority": priority,
            "description": metadata.get("description", ""),
            **{k: v for k, v in metadata.items() if k != "description"},
        }

        tool_executor_registry.register_instance(
            component_id=tool_name,
            component=func,
            priority=priority,
            tags=[category] if category else [],
            **metadata,
        )
        return func

    return decorator


def discover_tools(package: str = "runtime") -> int:
    """
    Automatically discover all tool executors in the specified package.

    Args:
        package: Python package to scan for tools

    Returns:
        Number of modules discovered
    """
    logger.info("tool_registry.discovering", package=package)
    count = tool_executor_registry.discover(package, recursive=True)
    logger.info("tool_registry.discovered", package=package, count=count)
    return count


def get_tool_executors() -> dict[str, Callable]:
    """
    Get all registered tool executors as a dictionary.

    This function returns the tool executors in the format expected
    by the existing L9 tool system (dict mapping names to functions).

    Returns:
        Dictionary mapping tool names to executor functions

    Example:
        # Get all registered tools
        executors = get_tool_executors()

        # Use with existing tool system
        tool_func = executors.get("memory_search")
        result = await tool_func(query="test")
    """
    # Initialize any factory functions
    tool_executor_registry.initialize_factories()

    # Build dictionary mapping names to functions
    executors: dict[str, Callable] = {}

    for tool_id in tool_executor_registry.list_ids():
        tool_func = tool_executor_registry.get(tool_id)
        if tool_func:
            executors[tool_id] = tool_func

    logger.info("tool_registry.executors_built", count=len(executors))
    return executors


def get_tools_by_category(category: str) -> dict[str, Callable]:
    """
    Get all tool executors in a specific category.

    Args:
        category: Category to filter by (e.g., "memory", "redis")

    Returns:
        Dictionary mapping tool names to executor functions
    """
    tool_executor_registry.initialize_factories()

    tools = tool_executor_registry.get_all(tags=[category])
    executors: dict[str, Callable] = {}

    for tool_func in tools:
        # Find the tool's ID
        for tool_id in tool_executor_registry.list_ids():
            if tool_executor_registry.get(tool_id) == tool_func:
                executors[tool_id] = tool_func
                break

    return executors


def get_tool_snapshot() -> dict:
    """Get a snapshot of all registered tools for observability."""
    return tool_executor_registry.snapshot()


def register_extension_tool_executors() -> int:
    """
    Register tools from extension modules (research, reflection, etc).

    MIGRATED: All extension tools now use @register_tool decorator.
    This function triggers auto-discovery of extension tools.

    Returns:
        Number of additional tools registered
    """
    registered = 0

    # Auto-discover research tools (all have @register_tool decorator)
    try:
        import core.tools.research_tools

        logger.debug("extension_tools.research_loaded")
        registered += 4  # run_research_query, synthesize, discover, generate_spec
    except ImportError as e:
        logger.warning(f"extension_tools.research_unavailable: {e}")

    # Auto-discover reflection tools (all have @register_tool decorator)
    try:
        import core.tools.reflection_tools  # noqa: F401 - trigger module load for @register_tool

        logger.debug("extension_tools.reflection_loaded")
        registered += 5  # reflect, analyze_failure, compare_approaches, extract_patterns, generate_improvements
    except ImportError as e:
        logger.warning(f"extension_tools.reflection_unavailable: {e}")

    if registered > 0:
        logger.info("extension_tools_registered", count=registered)

    return registered


# =============================================================================
# MCP NAMESPACE ISOLATION (Enhancement from GMP MCP-Tools)
# =============================================================================
# MCP tools are namespaced as {server_id}__{tool_name} to prevent collisions

# Track MCP tool metadata for namespace resolution
_mcp_tool_metadata: dict[str, dict[str, Any]] = {}


def register_mcp_tool(
    name: str,
    server_id: str,
    executor: Callable,
    category: str = "mcp",
    tags: list[str] | None = None,
    risk_level: str = "medium",
    requires_approval: bool = False,
    **metadata: Any,
) -> str:
    """
    Register an MCP tool with namespace isolation.

    MCP tools are namespaced as {server_id}__{tool_name} to prevent
    collisions between servers that expose tools with the same name.

    Args:
        name: Original tool name from MCP server
        server_id: MCP server identifier
        executor: Tool executor function
        category: Tool category (default: "mcp")
        tags: Optional tags for filtering (e.g., ["read-only", "admin-only"])
        risk_level: Risk classification ("low", "medium", "high")
        requires_approval: Whether requires Igor approval
        **metadata: Additional metadata

    Returns:
        Namespaced tool ID (e.g., "vercel__deploy")
    """
    # Create namespaced tool ID
    tool_id = f"{server_id}__{name}"

    # Register with existing registry
    tool_executor_registry.register_instance(
        component_id=tool_id,
        component=executor,
        priority=0,
        tags=[category] + (tags or []),
        source="mcp",
        server_id=server_id,
        original_name=name,
        risk_level=risk_level,
        requires_approval=requires_approval,
        **metadata,
    )

    # Track metadata for namespace resolution
    _mcp_tool_metadata[tool_id] = {
        "server_id": server_id,
        "original_name": name,
        "tags": tags or [],
        "risk_level": risk_level,
        "requires_approval": requires_approval,
    }

    logger.info(
        "mcp_tool.registered",
        tool_id=tool_id,
        server_id=server_id,
        original_name=name,
        tags=tags,
    )

    return tool_id


def register_mcp_tools_batch(
    tools: list[dict[str, Any]],
    server_id: str,
) -> list[str]:
    """
    Batch register MCP tools from a server with automatic namespacing.

    Args:
        tools: List of tool definitions with name, executor, etc.
        server_id: MCP server identifier

    Returns:
        List of registered namespaced tool IDs
    """
    registered_ids = []

    for tool_def in tools:
        tool_id = register_mcp_tool(
            name=tool_def["name"],
            server_id=server_id,
            executor=tool_def["executor"],
            category=tool_def.get("category", "mcp"),
            tags=tool_def.get("tags", []),
            risk_level=tool_def.get("risk_level", "medium"),
            requires_approval=tool_def.get("requires_approval", False),
            description=tool_def.get("description", ""),
        )
        registered_ids.append(tool_id)

    logger.info(
        "mcp_tools.batch_registered",
        server_id=server_id,
        count=len(registered_ids),
    )

    return registered_ids


def get_tools_by_server(server_id: str) -> dict[str, Callable]:
    """
    Get all tools registered from a specific MCP server.

    Args:
        server_id: MCP server identifier

    Returns:
        Dictionary mapping namespaced tool IDs to executors
    """
    result: dict[str, Callable] = {}

    for tool_id, meta in _mcp_tool_metadata.items():
        if meta["server_id"] == server_id:
            executor = tool_executor_registry.get(tool_id)
            if executor:
                result[tool_id] = executor

    return result


def get_mcp_tool_metadata(tool_id: str) -> dict[str, Any] | None:
    """Get metadata for a namespaced MCP tool."""
    return _mcp_tool_metadata.get(tool_id)


def resolve_mcp_tool_name(server_id: str, original_name: str) -> str | None:
    """
    Resolve original tool name to namespaced ID.

    Args:
        server_id: MCP server identifier
        original_name: Original tool name

    Returns:
        Namespaced tool ID or None if not found
    """
    tool_id = f"{server_id}__{original_name}"
    if tool_id in _mcp_tool_metadata:
        return tool_id
    return None


def get_tools_by_tags(tags: list[str]) -> dict[str, Callable]:
    """
    Get all tools that have ALL specified tags.

    Args:
        tags: List of tags to filter by

    Returns:
        Dictionary mapping tool IDs to executors
    """
    result: dict[str, Callable] = {}

    # Check MCP tools (tags tracked in _mcp_tool_metadata)
    for tool_id, meta in _mcp_tool_metadata.items():
        tool_tags = meta.get("tags", [])
        if all(tag in tool_tags for tag in tags):
            executor = tool_executor_registry.get(tool_id)
            if executor:
                result[tool_id] = executor

    # Also check regular (non-MCP) tools via registry tags
    for tool_id in tool_executor_registry.list_ids():
        if tool_id not in result:
            # Retrieve stored tags from AutoRegistry metadata
            entry_meta = tool_executor_registry.get_metadata(tool_id)
            if entry_meta:
                tool_tags = entry_meta.get("tags", [])
                if all(tag in tool_tags for tag in tags):
                    executor = tool_executor_registry.get(tool_id)
                    if executor:
                        result[tool_id] = executor

    return result


# =============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "RUN-TOOL-AUTO-REG",
    "governance_level": "critical",
    "security_reviewed": True,
    "performance_tested": True,
    "last_audit": "2026-01-31T00:00:00Z",
}
# ============================================================================
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
