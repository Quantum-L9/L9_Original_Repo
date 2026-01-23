"""
Tests for L9 Schema Upcaster Auto-Discovery System

Note: Tests register components manually within each test to avoid
decorator-at-import issues with fixture clearing.
"""

import pytest
from core.schemas.upcaster_registry import (
    upcaster_registry,
    register_upcaster,
    get_all_upcasters,
    get_upcaster,
    wire_upcasters_to_schema_registry,
)
from core.schemas.schema_registry import _SchemaRegistry


@pytest.fixture(autouse=True)
def clear_registries():
    """Clear all registries before and after each test."""
    upcaster_registry.clear()
    yield
    upcaster_registry.clear()


# Test upcaster function (NOT decorated at module level)
def upcast_test(packet: dict) -> dict:
    """Test upcaster that adds a test field."""
    packet["test"] = True
    return packet


def test_register_upcaster_decorator():
    """Test that @register_upcaster decorator registers an upcaster."""
    # Register within test (after fixture clears registry)
    register_upcaster("1.0.0", "1.0.1", "Test upcaster")(upcast_test)

    upcasters = get_all_upcasters()

    key = "1.0.0->1.0.1"
    assert key in upcasters
    config = upcasters[key]
    assert config.from_version == "1.0.0"
    assert config.to_version == "1.0.1"
    assert config.upcaster_func == upcast_test


def test_get_upcaster():
    """Test getting a specific upcaster by version pair."""
    register_upcaster("2.0.0", "2.0.1", "Version 2 upcaster")(upcast_test)

    config = get_upcaster("2.0.0", "2.0.1")
    assert config is not None
    assert config.from_version == "2.0.0"
    assert config.to_version == "2.0.1"

    # Non-existent upcaster
    assert get_upcaster("9.0.0", "9.0.1") is None


def test_wire_upcasters_to_schema_registry():
    """Test that auto-registered upcasters can be wired to the main registry."""
    # Register upcaster within test
    register_upcaster("1.0.0", "1.0.1", "Test upcaster")(upcast_test)

    # Create a mock schema registry
    class MockSchemaRegistry(_SchemaRegistry):
        def __init__(self):
            super().__init__()
            self._upcasters.clear()
            self._migration_graph.clear()

    mock_registry = MockSchemaRegistry()
    wired_count = wire_upcasters_to_schema_registry(mock_registry)

    assert wired_count == 1
    assert "1.0.0->1.0.1" in mock_registry._upcasters


def test_upcaster_registry_snapshot():
    """Test registry snapshot for observability."""
    register_upcaster("3.0.0", "3.1.0", "Snapshot test")(upcast_test)

    snapshot = upcaster_registry.snapshot()

    assert snapshot["registry_name"] == "schema_upcasters"
    assert snapshot["component_count"] == 1
