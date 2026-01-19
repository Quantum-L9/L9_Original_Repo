"""
Tests for core.auto_registry module.

Comprehensive test suite for the AutoRegistry framework.
"""

import pytest

from core.auto_registry import (
    AutoRegistry,
    DuplicateRegistrationError,
    ValidationError,
)

# =============================================================================
# Test Fixtures
# =============================================================================


class DummyComponent:
    """Dummy component for testing."""

    def __init__(self, name: str, value: int = 0):
        self.name = name
        self.value = value


def dummy_validator(component: DummyComponent) -> bool:
    """Validator that checks if value is positive."""
    return component.value >= 0


@pytest.fixture
def registry():
    """Create a fresh registry for each test."""
    return AutoRegistry[DummyComponent]("test_registry")


@pytest.fixture
def validated_registry():
    """Create a registry with validation."""
    return AutoRegistry[DummyComponent]("validated_registry", validator=dummy_validator)


# =============================================================================
# Basic Registration Tests
# =============================================================================


def test_registry_initialization(registry):
    """Test registry initializes correctly."""
    assert registry.name == "test_registry"
    assert registry.count() == 0
    assert registry.list_ids() == []


def test_register_instance(registry):
    """Test registering a component instance."""
    component = DummyComponent("test", 42)
    registry.register_instance("comp1", component, priority=10)

    assert registry.count() == 1
    assert "comp1" in registry.list_ids()
    assert registry.get("comp1") == component


def test_register_decorator(registry):
    """Test decorator-based registration."""

    @registry.register(name="decorated", priority=5)
    class DecoratedComponent(DummyComponent):
        pass

    assert registry.count() == 1
    assert "decorated" in registry.list_ids()


def test_register_factory(registry):
    """Test registering a factory function."""

    @registry.register(name="factory_comp", priority=3)
    def create_component():
        return DummyComponent("from_factory", 99)

    # Factory should be registered but not initialized yet
    assert registry.count() == 0

    # Initialize factories
    registry.initialize_factories()

    assert registry.count() == 1
    comp = registry.get("factory_comp")
    assert comp is not None
    assert comp.name == "from_factory"
    assert comp.value == 99


# =============================================================================
# Duplicate Registration Tests
# =============================================================================


def test_duplicate_registration_blocked(registry):
    """Test that duplicate registrations are blocked by default."""
    component1 = DummyComponent("first", 1)
    component2 = DummyComponent("second", 2)

    registry.register_instance("comp1", component1)

    with pytest.raises(DuplicateRegistrationError):
        registry.register_instance("comp1", component2)


def test_duplicate_registration_allowed():
    """Test allowing duplicate registrations."""
    registry = AutoRegistry[DummyComponent]("dup_registry", allow_duplicates=True)

    component1 = DummyComponent("first", 1)
    component2 = DummyComponent("second", 2)

    registry.register_instance("comp1", component1)
    registry.register_instance("comp1", component2)  # Should not raise

    # Latest registration wins
    assert registry.get("comp1") == component2


# =============================================================================
# Validation Tests
# =============================================================================


def test_validation_success(validated_registry):
    """Test successful validation."""
    component = DummyComponent("valid", 10)
    validated_registry.register_instance("comp1", component)

    assert validated_registry.count() == 1


def test_validation_failure(validated_registry):
    """Test validation failure."""
    component = DummyComponent("invalid", -5)  # Negative value fails validation

    with pytest.raises(ValidationError):
        validated_registry.register_instance("comp1", component)

    assert validated_registry.count() == 0


# =============================================================================
# Priority and Sorting Tests
# =============================================================================


def test_priority_sorting(registry):
    """Test components are sorted by priority."""
    comp1 = DummyComponent("low", 1)
    comp2 = DummyComponent("high", 2)
    comp3 = DummyComponent("medium", 3)

    registry.register_instance("comp1", comp1, priority=1)
    registry.register_instance("comp2", comp2, priority=10)
    registry.register_instance("comp3", comp3, priority=5)

    components = registry.get_all()

    # Should be sorted by priority: high (10), medium (5), low (1)
    assert components[0] == comp2
    assert components[1] == comp3
    assert components[2] == comp1


# =============================================================================
# Tag Filtering Tests
# =============================================================================


def test_tag_filtering(registry):
    """Test filtering components by tags."""
    comp1 = DummyComponent("api", 1)
    comp2 = DummyComponent("worker", 2)
    comp3 = DummyComponent("api_admin", 3)

    registry.register_instance("comp1", comp1, tags=["api", "public"])
    registry.register_instance("comp2", comp2, tags=["worker"])
    registry.register_instance("comp3", comp3, tags=["api", "admin"])

    # Get all API components
    api_components = registry.get_all(tags=["api"])
    assert len(api_components) == 2
    assert comp1 in api_components
    assert comp3 in api_components

    # Get worker components
    worker_components = registry.get_all(tags=["worker"])
    assert len(worker_components) == 1
    assert comp2 in worker_components


# =============================================================================
# Metadata Tests
# =============================================================================


def test_metadata_storage(registry):
    """Test metadata is stored correctly."""
    component = DummyComponent("test", 42)
    registry.register_instance(
        "comp1",
        component,
        priority=5,
        tags=["test", "example"],
        custom_field="custom_value",
    )

    metadata = registry.get_metadata("comp1")
    assert metadata is not None
    assert metadata["name"] == "comp1"
    assert metadata["priority"] == 5
    assert metadata["tags"] == ["test", "example"]
    assert metadata["custom_field"] == "custom_value"


# =============================================================================
# Snapshot Tests
# =============================================================================


def test_snapshot(registry):
    """Test registry snapshot for observability."""
    comp1 = DummyComponent("first", 1)
    comp2 = DummyComponent("second", 2)

    registry.register_instance("comp1", comp1, priority=10, tags=["api"])
    registry.register_instance("comp2", comp2, priority=5, tags=["worker"])

    snapshot = registry.snapshot()

    assert snapshot["registry_name"] == "test_registry"
    assert snapshot["component_count"] == 2
    assert len(snapshot["components"]) == 2

    # Check component details
    comp_ids = [c["id"] for c in snapshot["components"]]
    assert "comp1" in comp_ids
    assert "comp2" in comp_ids


# =============================================================================
# Discovery Tests (Integration)
# =============================================================================


def test_discover_no_package(registry):
    """Test discovery with non-existent package."""
    count = registry.discover("nonexistent.package")
    assert count == 0


# =============================================================================
# Edge Cases
# =============================================================================


def test_get_nonexistent_component(registry):
    """Test getting a component that doesn't exist."""
    assert registry.get("nonexistent") is None


def test_get_metadata_nonexistent(registry):
    """Test getting metadata for nonexistent component."""
    assert registry.get_metadata("nonexistent") is None


def test_empty_registry_operations(registry):
    """Test operations on empty registry."""
    assert registry.count() == 0
    assert registry.get_all() == []
    assert registry.list_ids() == []

    snapshot = registry.snapshot()
    assert snapshot["component_count"] == 0
    assert snapshot["components"] == []
