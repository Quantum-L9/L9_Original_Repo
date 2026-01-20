"""
Tests for orchestrator auto-registration system.
"""

import pytest
from orchestrators.orchestrator_registry import (
    register_legacy_orchestrators,
    discover_orchestrators,
    get_orchestrator_snapshot,
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
    """Test orchestrator snapshot."""
    snapshot = get_orchestrator_snapshot()
    assert "component_count" in snapshot
    assert "components" in snapshot
    assert isinstance(snapshot["component_count"], int)
    assert isinstance(snapshot["components"], dict)


def test_orchestrator_snapshot_structure():
    """Test orchestrator snapshot has correct structure."""
    snapshot = get_orchestrator_snapshot()

    # Check top-level keys
    assert "registry_name" in snapshot
    assert "component_count" in snapshot
    assert "components" in snapshot
    assert "tags" in snapshot

    # Check types
    assert isinstance(snapshot["registry_name"], str)
    assert isinstance(snapshot["component_count"], int)
    assert isinstance(snapshot["components"], dict)
    assert isinstance(snapshot["tags"], dict)
