"""
Tests for runtime.tool_registry module.

Test suite for the tool executor auto-registration system.
"""

import pytest

from runtime.tool_registry import (get_tool_executors, get_tool_snapshot,
                                   get_tools_by_category, register_tool,
                                   tool_executor_registry)

# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def clean_registry():
    """Clean the tool registry before each test."""
    # Save original state
    original_components = tool_executor_registry._components.copy()
    original_metadata = tool_executor_registry._metadata.copy()
    original_factories = tool_executor_registry._factories.copy()

    # Clear registry
    tool_executor_registry._components.clear()
    tool_executor_registry._metadata.clear()
    tool_executor_registry._factories.clear()

    yield tool_executor_registry

    # Restore original state
    tool_executor_registry._components = original_components
    tool_executor_registry._metadata = original_metadata
    tool_executor_registry._factories = original_factories


# =============================================================================
# Basic Registration Tests
# =============================================================================


def test_register_tool_decorator(clean_registry):
    """Test registering a tool with decorator."""

    @register_tool(category="memory", priority=10)
    async def memory_search(query: str, **kwargs):
        return {"results": []}

    # Check registration
    executors = get_tool_executors()
    assert "memory_search" in executors
    assert executors["memory_search"] == memory_search


def test_register_tool_with_custom_name(clean_registry):
    """Test registering a tool with custom name."""

    @register_tool(name="custom_tool", category="custom")
    async def my_function(**kwargs):
        return {"status": "ok"}

    executors = get_tool_executors()
    assert "custom_tool" in executors
    assert executors["custom_tool"] == my_function


def test_register_multiple_tools(clean_registry):
    """Test registering multiple tools."""

    @register_tool(category="memory")
    async def memory_write(**kwargs):
        return {"written": True}

    @register_tool(category="redis")
    async def redis_get(**kwargs):
        return {"value": None}

    @register_tool(category="neo4j")
    async def neo4j_query(**kwargs):
        return {"nodes": []}

    executors = get_tool_executors()
    assert len(executors) == 3
    assert "memory_write" in executors
    assert "redis_get" in executors
    assert "neo4j_query" in executors


# =============================================================================
# Category Filtering Tests
# =============================================================================


def test_get_tools_by_category(clean_registry):
    """Test filtering tools by category."""

    @register_tool(category="memory")
    async def memory_search(**kwargs):
        return {}

    @register_tool(category="memory")
    async def memory_write(**kwargs):
        return {}

    @register_tool(category="redis")
    async def redis_get(**kwargs):
        return {}

    memory_tools = get_tools_by_category("memory")
    assert len(memory_tools) == 2
    assert "memory_search" in memory_tools
    assert "memory_write" in memory_tools

    redis_tools = get_tools_by_category("redis")
    assert len(redis_tools) == 1
    assert "redis_get" in redis_tools


# =============================================================================
# Priority Tests
# =============================================================================


def test_tool_priority_ordering(clean_registry):
    """Test tools are ordered by priority."""

    @register_tool(priority=1)
    async def low_priority_tool(**kwargs):
        return {}

    @register_tool(priority=10)
    async def high_priority_tool(**kwargs):
        return {}

    @register_tool(priority=5)
    async def medium_priority_tool(**kwargs):
        return {}

    # Get all tools
    executors = get_tool_executors()
    assert len(executors) == 3


# =============================================================================
# Snapshot Tests
# =============================================================================


def test_tool_snapshot(clean_registry):
    """Test getting tool registry snapshot."""

    @register_tool(category="memory")
    async def memory_search(**kwargs):
        return {}

    @register_tool(category="redis")
    async def redis_get(**kwargs):
        return {}

    snapshot = get_tool_snapshot()
    assert snapshot["registry_name"] == "tool_executors"
    assert snapshot["component_count"] == 2


# =============================================================================
# Integration Tests
# =============================================================================


def test_tool_execution(clean_registry):
    """Test that registered tools can be executed."""

    @register_tool(category="test")
    async def test_tool(value: int, **kwargs):
        return {"result": value * 2}

    executors = get_tool_executors()
    tool_func = executors["test_tool"]

    # Execute the tool
    import asyncio

    result = asyncio.run(tool_func(value=5))
    assert result == {"result": 10}


def test_sync_tool_registration(clean_registry):
    """Test registering synchronous tools."""

    @register_tool(category="sync")
    def sync_tool(**kwargs):
        return {"sync": True}

    executors = get_tool_executors()
    assert "sync_tool" in executors

    # Execute sync tool
    result = executors["sync_tool"]()
    assert result == {"sync": True}
