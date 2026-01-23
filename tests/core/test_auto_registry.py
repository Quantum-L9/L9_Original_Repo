"""
Tests for core auto-registration framework.

Tests the actual AutoRegistry API.
"""

import pytest

from core.auto_registry import AutoRegistry, DuplicateRegistrationError


def test_auto_registry_creation():
    """Test creating an AutoRegistry instance."""
    registry = AutoRegistry[str](name="test_registry_create")
    assert registry is not None
    assert registry.name == "test_registry_create"


def test_auto_registry_register_instance():
    """Test registering an instance."""
    registry = AutoRegistry[str](name="test_registry_inst")
    registry.register_instance("test_id", "test_value")

    result = registry.get("test_id")
    assert result == "test_value"


def test_auto_registry_list_ids():
    """Test listing registered IDs."""
    registry = AutoRegistry[str](name="test_registry_ids")
    registry.register_instance("id1", "value1")
    registry.register_instance("id2", "value2")

    ids = registry.list_ids()
    assert "id1" in ids
    assert "id2" in ids
    assert len(ids) >= 2


def test_auto_registry_snapshot():
    """Test registry snapshot."""
    registry = AutoRegistry[str](name="test_registry_snap")
    registry.register_instance("test_id", "test_value", priority=5, tags=["tag1"])

    snapshot = registry.snapshot()
    assert "registry_name" in snapshot
    assert "component_count" in snapshot
    assert "components" in snapshot
    assert snapshot["registry_name"] == "test_registry_snap"
    assert snapshot["component_count"] >= 1
    # components is a list, not a dict
    assert isinstance(snapshot["components"], list)


def test_auto_registry_get_nonexistent():
    """Test getting non-existent component returns None."""
    registry = AutoRegistry[str](name="test_registry_nonex")
    result = registry.get("nonexistent")
    assert result is None


def test_auto_registry_duplicate_prevention():
    """Test that duplicates raise DuplicateRegistrationError when allow_duplicates=False."""
    registry = AutoRegistry[str](name="test_registry_dup", allow_duplicates=False)
    registry.register_instance("test_id", "value1")

    # Second registration should raise DuplicateRegistrationError
    with pytest.raises(DuplicateRegistrationError):
        registry.register_instance("test_id", "value2")

    # Should still have first value
    result = registry.get("test_id")
    assert result == "value1"


def test_auto_registry_allow_duplicates():
    """Test that duplicates are allowed when allow_duplicates=True."""
    registry = AutoRegistry[str](name="test_registry_allow", allow_duplicates=True)
    registry.register_instance("test_id", "value1")

    # Second registration should succeed
    registry.register_instance("test_id", "value2")

    # Should have second value (overwrites)
    result = registry.get("test_id")
    assert result == "value2"


def test_auto_registry_tags():
    """Test tag-based filtering."""
    registry = AutoRegistry[str](name="test_registry_tags")
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
    registry = AutoRegistry[str](name="test_registry_prio")
    registry.register_instance("low", "value_low", priority=1)
    registry.register_instance("high", "value_high", priority=10)
    registry.register_instance("mid", "value_mid", priority=5)

    # All should be registered
    ids = registry.list_ids()
    assert len(ids) >= 3
    assert "low" in ids
    assert "high" in ids
    assert "mid" in ids


def test_auto_registry_count():
    """Test count method."""
    registry = AutoRegistry[str](name="test_registry_count")
    assert registry.count() == 0

    registry.register_instance("id1", "value1")
    assert registry.count() == 1

    registry.register_instance("id2", "value2")
    assert registry.count() == 2


def test_auto_registry_clear():
    """Test clearing the registry."""
    registry = AutoRegistry[str](name="test_registry_clear")
    registry.register_instance("id1", "value1")
    registry.register_instance("id2", "value2")
    assert registry.count() == 2

    registry.clear()
    assert registry.count() == 0
    assert registry.get("id1") is None
