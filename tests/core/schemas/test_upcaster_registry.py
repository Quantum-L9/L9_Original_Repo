"""
Tests for L9 Schema Upcaster Auto-Discovery System
"""

import pytest
from core.schemas.upcaster_registry import (
    upcaster_registry,
    register_upcaster,
    discover_upcasters,
    get_all_upcasters,
    wire_upcasters_to_schema_registry,
)
from core.schemas.schema_registry import _SchemaRegistry


@pytest.fixture(autouse=True)
def clear_registries():
    """Clear all registries before and after each test."""
    upcaster_registry.clear()
    yield
    upcaster_registry.clear()


@register_upcaster("1.0.0", "1.0.1", "Test upcaster")
def upcast_test(packet: dict) -> dict:
    packet["test"] = True
    return packet


def test_register_upcaster_decorator():
    """Test that @register_upcaster decorator registers an upcaster."""
    discover_upcasters(package="tests.core.schemas")
    upcasters = get_all_upcasters()

    key = "1.0.0->1.0.1"
    assert key in upcasters
    config = upcasters[key]
    assert config.from_version == "1.0.0"
    assert config.to_version == "1.0.1"
    assert config.upcaster_func == upcast_test


def test_wire_upcasters_to_schema_registry():
    """Test that auto-registered upcasters can be wired to the main registry."""
    discover_upcasters(package="tests.core.schemas")

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
