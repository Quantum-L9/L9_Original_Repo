"""
Tests for orchestrator auto-registration system.

Tests the actual orchestrator_registry API which uses AutoRegistry.
"""

from orchestrators.orchestrator_registry import (
    discover_orchestrators,
    get_orchestrator_snapshot,
    register_legacy_orchestrators,
)


def test_register_legacy_orchestrators():
    """Test legacy orchestrator registration."""
    count = register_legacy_orchestrators()
    assert count >= 0
    assert isinstance(count, int)


def test_discover_orchestrators():
    """Test orchestrator discovery."""
    count = discover_orchestrators("orchestrators")
    assert count >= 0
    assert isinstance(count, int)


def test_get_orchestrator_snapshot():
    """Test orchestrator snapshot returns valid structure."""
    snapshot = get_orchestrator_snapshot()
    assert "component_count" in snapshot
    assert "components" in snapshot
    assert isinstance(snapshot["component_count"], int)
    # components is a list (from AutoRegistry.snapshot())
    assert isinstance(snapshot["components"], list)


def test_orchestrator_snapshot_structure():
    """Test orchestrator snapshot has correct structure from AutoRegistry."""
    snapshot = get_orchestrator_snapshot()

    # Check top-level keys (matches AutoRegistry.snapshot() format)
    assert "registry_name" in snapshot
    assert "component_count" in snapshot
    assert "factory_count" in snapshot
    assert "components" in snapshot

    # Check types
    assert isinstance(snapshot["registry_name"], str)
    assert snapshot["registry_name"] == "orchestrators"
    assert isinstance(snapshot["component_count"], int)
    assert isinstance(snapshot["factory_count"], int)
    assert isinstance(snapshot["components"], list)


def test_orchestrator_snapshot_components_format():
    """Test that components in snapshot have correct format."""
    snapshot = get_orchestrator_snapshot()

    # Each component should be a dict with at least 'id' key
    for component in snapshot["components"]:
        assert isinstance(component, dict)
        assert "id" in component
