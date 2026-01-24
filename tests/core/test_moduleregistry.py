"""
Tests for module registry system.

Tests the actual ModuleRegistry API using ModuleDefinition objects.
"""

import pytest

from core.moduleregistry import ModuleDefinition, ModuleRegistry, ModuleStatus


def test_module_registry_creation():
    """Test creating a ModuleRegistry instance."""
    registry = ModuleRegistry()
    assert registry is not None


def test_module_registry_register():
    """Test registering a module using ModuleDefinition."""
    registry = ModuleRegistry()

    definition = ModuleDefinition(
        module_id="test_module",
        display_name="Test Module",
        version="1.0.0",
    )
    registry.register(definition)

    # Check that module was registered via get_definition
    retrieved = registry.get_definition("test_module")
    assert retrieved is not None
    assert retrieved.module_id == "test_module"


def test_module_registry_get_definition():
    """Test getting a registered module definition."""
    registry = ModuleRegistry()

    definition = ModuleDefinition(
        module_id="test_module",
        display_name="Test Module",
        version="1.0.0",
        owner="test_owner",
    )
    registry.register(definition)

    module = registry.get_definition("test_module")
    assert module is not None
    assert module.module_id == "test_module"
    assert module.display_name == "Test Module"
    assert module.version == "1.0.0"
    assert module.owner == "test_owner"


def test_module_registry_multiple_modules():
    """Test registering multiple modules."""
    registry = ModuleRegistry()

    registry.register(ModuleDefinition(module_id="module1", display_name="Module 1"))
    registry.register(ModuleDefinition(module_id="module2", display_name="Module 2"))

    # Both should be retrievable
    assert registry.get_definition("module1") is not None
    assert registry.get_definition("module2") is not None


def test_module_registry_get_nonexistent():
    """Test getting non-existent module returns None."""
    registry = ModuleRegistry()
    module = registry.get_definition("nonexistent")
    assert module is None


def test_module_registry_snapshot():
    """Test module registry snapshot."""
    registry = ModuleRegistry()

    registry.register(
        ModuleDefinition(
            module_id="test_module",
            display_name="Test Module",
            version="1.0.0",
        )
    )

    snapshot = registry.snapshot()
    assert "count" in snapshot
    assert "modules" in snapshot
    assert snapshot["count"] >= 1
    assert isinstance(snapshot["modules"], list)


def test_module_registry_snapshot_content():
    """Test module registry snapshot contains correct data."""
    registry = ModuleRegistry()

    registry.register(
        ModuleDefinition(
            module_id="snapshot_test",
            display_name="Snapshot Test Module",
            version="2.0.0",
            route_prefix="/test",
        )
    )

    snapshot = registry.snapshot()

    # Find our module in the snapshot
    found = False
    for module_data in snapshot["modules"]:
        if module_data["module_id"] == "snapshot_test":
            found = True
            assert module_data["definition"]["display_name"] == "Snapshot Test Module"
            assert module_data["definition"]["version"] == "2.0.0"
            assert module_data["definition"]["route_prefix"] == "/test"
            break

    assert found, "Module not found in snapshot"


def test_module_registry_set_status():
    """Test setting module status."""
    registry = ModuleRegistry()

    # Register module first
    registry.register(
        ModuleDefinition(module_id="status_test", display_name="Status Test")
    )

    # Set status
    status = ModuleStatus(
        module_id="status_test",
        enabled=True,
        available=True,
        initialized=True,
        notes="Running normally",
    )
    registry.set_status(status)

    # Retrieve status
    retrieved_status = registry.get_status("status_test")
    assert retrieved_status is not None
    assert retrieved_status.enabled is True
    assert retrieved_status.available is True
    assert retrieved_status.initialized is True
    assert retrieved_status.notes == "Running normally"


def test_module_registry_get_status_nonexistent():
    """Test getting status for non-existent module returns None."""
    registry = ModuleRegistry()
    status = registry.get_status("nonexistent")
    assert status is None


def test_module_definition_frozen():
    """Test that ModuleDefinition is immutable (frozen dataclass)."""
    definition = ModuleDefinition(
        module_id="frozen_test",
        display_name="Frozen Test",
    )

    # Should raise FrozenInstanceError when trying to modify
    with pytest.raises(AttributeError):
        definition.module_id = "changed"


def test_module_status_frozen():
    """Test that ModuleStatus is immutable (frozen dataclass)."""
    status = ModuleStatus(
        module_id="frozen_test",
        enabled=True,
        available=True,
        initialized=False,
    )

    # Should raise FrozenInstanceError when trying to modify
    with pytest.raises(AttributeError):
        status.enabled = False
