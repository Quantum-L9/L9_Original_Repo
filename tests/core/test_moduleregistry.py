"""
Tests for module registry system.
"""

import pytest
from core.moduleregistry import ModuleRegistry


def test_module_registry_creation():
    """Test creating a ModuleRegistry instance."""
    registry = ModuleRegistry()
    assert registry is not None


def test_module_registry_register():
    """Test registering a module."""
    registry = ModuleRegistry()

    registry.register(
        name="test_module", version="1.0.0", description="Test module", dependencies=[]
    )

    # Check that module was registered
    modules = registry.list_modules()
    assert "test_module" in modules


def test_module_registry_get():
    """Test getting a registered module."""
    registry = ModuleRegistry()

    registry.register(
        name="test_module", version="1.0.0", description="Test module", dependencies=[]
    )

    module = registry.get("test_module")
    assert module is not None
    assert module["name"] == "test_module"
    assert module["version"] == "1.0.0"


def test_module_registry_list_modules():
    """Test listing all registered modules."""
    registry = ModuleRegistry()

    registry.register("module1", "1.0.0", "Module 1", [])
    registry.register("module2", "2.0.0", "Module 2", [])

    modules = registry.list_modules()
    assert "module1" in modules
    assert "module2" in modules


def test_module_registry_dependencies():
    """Test module dependency tracking."""
    registry = ModuleRegistry()

    registry.register("module_a", "1.0.0", "Module A", [])
    registry.register("module_b", "1.0.0", "Module B", ["module_a"])

    module_b = registry.get("module_b")
    assert "module_a" in module_b["dependencies"]


def test_module_registry_get_nonexistent():
    """Test getting non-existent module returns None."""
    registry = ModuleRegistry()
    module = registry.get("nonexistent")
    assert module is None


def test_module_registry_snapshot():
    """Test module registry snapshot."""
    registry = ModuleRegistry()

    registry.register("test_module", "1.0.0", "Test", [])

    snapshot = registry.snapshot()
    assert "module_count" in snapshot
    assert "modules" in snapshot
    assert snapshot["module_count"] >= 1


def test_module_registry_validate_dependencies():
    """Test dependency validation."""
    registry = ModuleRegistry()

    # Register modules with dependencies
    registry.register("base", "1.0.0", "Base module", [])
    registry.register("dependent", "1.0.0", "Dependent module", ["base"])

    # Validate should pass
    is_valid = registry.validate_dependencies()
    assert is_valid is True


def test_module_registry_circular_dependency_detection():
    """Test circular dependency detection."""
    registry = ModuleRegistry()

    # Try to create circular dependency
    registry.register("module_a", "1.0.0", "Module A", ["module_b"])
    registry.register("module_b", "1.0.0", "Module B", ["module_a"])

    # Validation should detect circular dependency
    is_valid = registry.validate_dependencies()
    assert is_valid is False
