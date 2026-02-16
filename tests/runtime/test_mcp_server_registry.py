"""
Tests for runtime.mcp_server_registry module.

Test suite for the MCP server auto-registration system.
"""

import tempfile
from pathlib import Path

import pytest

from runtime.mcp_server_registry import (
    MCPServerConfig,
    get_all_mcp_servers,
    get_mcp_server_snapshot,
    get_mcp_servers_by_category,
    load_mcp_servers_from_yaml,
    mcp_server_registry,
    register_mcp_server,
)

# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def clean_registry():
    """Clean the MCP server registry before each test."""
    # Save original state
    original_components = mcp_server_registry._components.copy()
    original_metadata = mcp_server_registry._metadata.copy()
    original_factories = mcp_server_registry._factories.copy()

    # Clear registry
    mcp_server_registry._components.clear()
    mcp_server_registry._metadata.clear()
    mcp_server_registry._factories.clear()

    yield mcp_server_registry

    # Restore original state
    mcp_server_registry._components = original_components
    mcp_server_registry._metadata = original_metadata
    mcp_server_registry._factories = original_factories


# =============================================================================
# Basic Registration Tests
# =============================================================================


def test_register_mcp_server(clean_registry):
    """Test registering an MCP server."""
    config = register_mcp_server(
        server_id="filesystem",
        command=["npx", "-y", "@modelcontextprotocol/server-filesystem", "/tmp"],  # noqa: S108 — test fixture
        env={"NODE_ENV": "production"},
        category="storage",
    )

    assert config.server_id == "filesystem"
    assert config.command == [
        "npx",
        "-y",
        "@modelcontextprotocol/server-filesystem",
        "/tmp",  # noqa: S108 — test fixture
    ]
    assert config.env == {"NODE_ENV": "production"}
    assert config.enabled is True


def test_register_disabled_server(clean_registry):
    """Test registering a disabled MCP server."""
    config = register_mcp_server(
        server_id="github",
        command=["npx", "-y", "@modelcontextprotocol/server-github"],
        enabled=False,
    )

    assert config.enabled is False

    # Disabled servers should not appear in get_all_mcp_servers
    servers = get_all_mcp_servers()
    assert "github" not in servers


def test_register_multiple_servers(clean_registry):
    """Test registering multiple MCP servers."""
    register_mcp_server(
        server_id="filesystem",
        command=["npx", "-y", "@modelcontextprotocol/server-filesystem"],
    )

    register_mcp_server(
        server_id="github", command=["npx", "-y", "@modelcontextprotocol/server-github"]
    )

    register_mcp_server(
        server_id="custom", command=["python", "-m", "custom_mcp_server"]
    )

    servers = get_all_mcp_servers()
    assert len(servers) == 3
    assert "filesystem" in servers
    assert "github" in servers
    assert "custom" in servers


# =============================================================================
# YAML Loading Tests
# =============================================================================


def test_load_mcp_servers_from_yaml(clean_registry):
    """Test loading MCP servers from YAML file."""
    yaml_content = """
servers:
  - server_id: filesystem
    command: ["npx", "-y", "@modelcontextprotocol/server-filesystem", "/tmp"]
    env:
      NODE_ENV: production
    enabled: true
    priority: 10
    category: storage

  - server_id: github
    command: ["npx", "-y", "@modelcontextprotocol/server-github"]
    enabled: false
    priority: 5
    category: development
"""

    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        f.write(yaml_content)
        yaml_path = f.name

    try:
        count = load_mcp_servers_from_yaml(yaml_path)
        assert count == 2

        servers = get_all_mcp_servers()
        assert "filesystem" in servers
        # github is disabled, should not appear
        assert "github" not in servers

    finally:
        Path(yaml_path).unlink()


def test_load_from_nonexistent_yaml(clean_registry):
    """Test loading from non-existent YAML file."""
    count = load_mcp_servers_from_yaml("/nonexistent/path.yaml")
    assert count == 0


def test_load_from_empty_yaml(clean_registry):
    """Test loading from empty YAML file."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        f.write("")
        yaml_path = f.name

    try:
        count = load_mcp_servers_from_yaml(yaml_path)
        assert count == 0
    finally:
        Path(yaml_path).unlink()


# =============================================================================
# Category Filtering Tests
# =============================================================================


def test_get_servers_by_category(clean_registry):
    """Test filtering servers by category."""
    register_mcp_server(
        server_id="filesystem",
        command=["npx", "-y", "@modelcontextprotocol/server-filesystem"],
        category="storage",
    )

    register_mcp_server(
        server_id="s3",
        command=["npx", "-y", "@modelcontextprotocol/server-s3"],
        category="storage",
    )

    register_mcp_server(
        server_id="github",
        command=["npx", "-y", "@modelcontextprotocol/server-github"],
        category="development",
    )

    storage_servers = get_mcp_servers_by_category("storage")
    assert len(storage_servers) == 2
    assert "filesystem" in storage_servers
    assert "s3" in storage_servers

    dev_servers = get_mcp_servers_by_category("development")
    assert len(dev_servers) == 1
    assert "github" in dev_servers


# =============================================================================
# Snapshot Tests
# =============================================================================


def test_mcp_server_snapshot(clean_registry):
    """Test getting MCP server registry snapshot."""
    register_mcp_server(
        server_id="filesystem",
        command=["npx", "-y", "@modelcontextprotocol/server-filesystem"],
    )

    register_mcp_server(
        server_id="github", command=["npx", "-y", "@modelcontextprotocol/server-github"]
    )

    snapshot = get_mcp_server_snapshot()
    assert snapshot["registry_name"] == "mcp_servers"
    assert snapshot["component_count"] == 2


# =============================================================================
# Configuration Tests
# =============================================================================


def test_mcp_server_config_to_dict():
    """Test MCPServerConfig to_dict method."""
    config = MCPServerConfig(
        server_id="test",
        command=["test", "command"],
        env={"KEY": "value"},
        enabled=True,
        priority=5,
        description="Test server",
    )

    config_dict = config.to_dict()
    assert config_dict["server_id"] == "test"
    assert config_dict["command"] == ["test", "command"]
    assert config_dict["env"] == {"KEY": "value"}
    assert config_dict["enabled"] is True
    assert config_dict["priority"] == 5
    assert config_dict["description"] == "Test server"
