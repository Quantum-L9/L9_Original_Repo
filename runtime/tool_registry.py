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
import threading
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
_tool_registry_lock = threading.Lock()


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
        with _tool_registry_lock:
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
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "RUN-TOOL-AUTO-REG",
    "governance_level": "critical",
    "security_reviewed": True,
    "performance_tested": True,
    "last_audit": "2026-01-18T00:00:00Z",
}
# ============================================================================
