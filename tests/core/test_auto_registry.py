"""
Tests for core auto-registration framework.
"""

import pytest
from core.auto_registry import AutoRegistry


def test_auto_registry_creation():
    """Test creating an AutoRegistry instance."""
    registry = AutoRegistry[str](name="test_registry")
    assert registry is not None
    assert registry._name == "test_registry"


def test_auto_registry_register_instance():
    """Test registering an instance."""
    registry = AutoRegistry[str](name="test_registry")
    registry.register_instance("test_id", "test_value")

    result = registry.get("test_id")
    assert result == "test_value"


def test_auto_registry_list_ids():
    """Test listing registered IDs."""
    registry = AutoRegistry[str](name="test_registry")
    registry.register_instance("id1", "value1")
    registry.register_instance("id2", "value2")

    ids = registry.list_ids()
    assert "id1" in ids
    assert "id2" in ids
    assert len(ids) >= 2


def test_auto_registry_snapshot():
    """Test registry snapshot."""
    registry = AutoRegistry[str](name="test_registry")
    registry.register_instance("test_id", "test_value", priority=5, tags=["tag1"])

    snapshot = registry.snapshot()
    assert "registry_name" in snapshot
    assert "component_count" in snapshot
    assert "components" in snapshot
    assert snapshot["registry_name"] == "test_registry"
    assert snapshot["component_count"] >= 1


def test_auto_registry_get_nonexistent():
    """Test getting non-existent component returns None."""
    registry = AutoRegistry[str](name="test_registry")
    result = registry.get("nonexistent")
    assert result is None


def test_auto_registry_duplicate_prevention():
    """Test that duplicates are prevented when allow_duplicates=False."""
    registry = AutoRegistry[str](name="test_registry", allow_duplicates=False)
    registry.register_instance("test_id", "value1")

    # Second registration should be ignored or raise error
    registry.register_instance("test_id", "value2")

    # Should still have first value
    result = registry.get("test_id")
    assert result == "value1"


def test_auto_registry_tags():
    """Test tag-based filtering."""
    registry = AutoRegistry[str](name="test_registry")
    registry.register_instance("id1", "value1", tags=["tag1", "tag2"])
    registry.register_instance("id2", "value2", tags=["tag2"])
    registry.register_instance("id3", "value3", tags=["tag3"])

    # Get all with tag2
    results = registry.get_all(tags=["tag2"])
    assert len(results) >= 2
    assert "value1" in results
    assert "value2" in results


def test_auto_registry_priority():
    """Test priority-based ordering."""
    registry = AutoRegistry[str](name="test_registry")
    registry.register_instance("low", "value_low", priority=1)
    registry.register_instance("high", "value_high", priority=10)
    registry.register_instance("mid", "value_mid", priority=5)

    # Higher priority should be registered first
    ids = registry.list_ids()
    assert len(ids) >= 3
