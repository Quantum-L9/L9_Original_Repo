"""
Tests for L9 Governance Policy Auto-Discovery System

Note: Tests use proper Policy schema format with required fields.
"""

from pathlib import Path

import pytest
import yaml

from core.governance.policy_registry import (
    discover_policy_sources,
    get_all_policy_sources,
    get_policy_source_snapshot,
    policy_source_registry,
    register_policy_source,
)


@pytest.fixture(autouse=True)
def clear_registries():
    """Clear all registries before and after each test."""
    policy_source_registry.clear()
    yield
    policy_source_registry.clear()


@pytest.fixture
def create_test_policies(tmp_path: Path) -> Path:
    """Create a directory with test policy YAML files."""
    policy_dir = tmp_path / "policies"
    policy_dir.mkdir()

    # Valid policy format matching core/governance/schemas.py Policy class
    policy1 = {
        "id": "test_policy_1",
        "name": "test_policy_1",
        "description": "Test policy 1",
        "effect": "allow",
        "priority": 10,
        "subjects": ["*"],
        "actions": ["test.action"],
        "resources": ["*"],
        "conditions": [],
        "enabled": True,
    }

    policy2 = {
        "id": "test_policy_2",
        "name": "test_policy_2",
        "description": "Test policy 2",
        "effect": "deny",
        "priority": 5,
        "subjects": ["*"],
        "actions": ["test.deny"],
        "resources": ["*"],
        "conditions": [],
        "enabled": True,
    }

    (policy_dir / "policy1.yaml").write_text(yaml.dump(policy1))
    (policy_dir / "policy2.yaml").write_text(yaml.dump(policy2))

    return policy_dir


def test_register_policy_source(create_test_policies: Path):
    """Test that a policy source can be registered."""
    register_policy_source(
        name="test_policies", path=create_test_policies, description="Test policies"
    )

    sources = discover_policy_sources()
    assert len(sources) == 1
    source = sources[0]
    assert source.name == "test_policies"
    assert source.path == create_test_policies


def test_get_all_policy_sources(create_test_policies: Path):
    """Test getting all policy sources as a dictionary."""
    register_policy_source(
        name="test_policies",
        path=create_test_policies,
        description="Test policies",
        priority=100,
    )

    sources = get_all_policy_sources()
    assert "test_policies" in sources
    assert sources["test_policies"].priority == 100


def test_policy_source_snapshot(create_test_policies: Path):
    """Test registry snapshot for observability."""
    register_policy_source(
        name="test_policies",
        path=create_test_policies,
        description="Test policies",
    )

    snapshot = get_policy_source_snapshot()
    assert snapshot["registry_name"] == "governance_policy_sources"
    assert snapshot["component_count"] == 1


def test_disabled_policy_source(create_test_policies: Path):
    """Test that disabled sources are not returned by discover."""
    register_policy_source(
        name="disabled_policies",
        path=create_test_policies,
        description="Disabled test policies",
        enabled=False,
    )

    sources = discover_policy_sources()
    # discover_policy_sources() filters out disabled sources
    assert len(sources) == 0

    # But get_all returns all (including disabled)
    all_sources = get_all_policy_sources()
    assert "disabled_policies" in all_sources
