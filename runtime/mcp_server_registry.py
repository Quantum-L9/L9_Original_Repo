"""
L9 Runtime - MCP Server Auto-Registration System
=================================================

Automatic discovery and registration of MCP (Model Context Protocol) servers.

This module eliminates hardcoded MCP server definitions by providing
a YAML-based configuration system with automatic discovery and registration.

Version: 1.0.0
"""

from __future__ import annotations

# ============================================================================
__dora_meta__ = {
    "component_name": "MCP Server Auto-Registration",
    "module_version": "1.0.0",
    "created_by": "L9 Auto-Wiring Team",
    "created_at": "2026-01-18T00:00:00Z",
    "updated_at": "2026-01-18T00:00:00Z",
    "layer": "runtime",
    "domain": "mcp",
    "module_name": "mcp_server_registry",
    "type": "service",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": [],
        "memory_layers": [],
        "imported_by": ["runtime.mcp_client"],
    },
}
# ============================================================================

from pathlib import Path
from typing import Any, Dict, List, Optional

import structlog
import yaml

from core.auto_registry import AutoRegistry

logger = structlog.get_logger(__name__)


# =============================================================================
# MCP Server Configuration
# =============================================================================


class MCPServerConfig:
    """Configuration for an MCP server."""

    def __init__(
        self,
        server_id: str,
        command: List[str],
        env: Optional[Dict[str, str]] = None,
        enabled: bool = True,
        priority: int = 0,
        **metadata: Any,
    ):
        self.server_id = server_id
        self.command = command
        self.env = env or {}
        self.enabled = enabled
        self.priority = priority
        self.metadata = metadata

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "server_id": self.server_id,
            "command": self.command,
            "env": self.env,
            "enabled": self.enabled,
            "priority": self.priority,
            **self.metadata,
        }


# =============================================================================
# MCP Server Registry
# =============================================================================


def _validate_mcp_server(config: MCPServerConfig) -> bool:
    """Validate that an object is a valid MCP server config."""
    return isinstance(config, MCPServerConfig) and bool(config.command)


# Global MCP server registry
mcp_server_registry = AutoRegistry[MCPServerConfig](
    name="mcp_servers", validator=_validate_mcp_server, allow_duplicates=False
)


def register_mcp_server(
    server_id: str,
    command: List[str],
    env: Optional[Dict[str, str]] = None,
    enabled: bool = True,
    priority: int = 0,
    **metadata: Any,
) -> MCPServerConfig:
    """
    Register an MCP server programmatically.

    Args:
        server_id: Unique server identifier
        command: Command to start the server (e.g., ["npx", "-y", "@modelcontextprotocol/server-filesystem"])
        env: Environment variables for the server
        enabled: Whether the server is enabled
        priority: Registration priority (higher = loaded first)
        **metadata: Additional metadata (description, category, etc.)

    Returns:
        MCPServerConfig instance

    Example:
        register_mcp_server(
            server_id="filesystem",
            command=["npx", "-y", "@modelcontextprotocol/server-filesystem", "/tmp"],
            env={"NODE_ENV": "production"},
            category="storage"
        )
    """
    config = MCPServerConfig(
        server_id=server_id,
        command=command,
        env=env,
        enabled=enabled,
        priority=priority,
        **metadata,
    )

    mcp_server_registry.register_instance(
        component_id=server_id,
        component=config,
        priority=priority,
        tags=[metadata.get("category", "general")],
        **metadata,
    )

    logger.info("mcp_server_registry.registered", server_id=server_id)
    return config


def load_mcp_servers_from_yaml(yaml_path: str | Path) -> int:
    """
    Load MCP server configurations from a YAML file.

    YAML format:
    ```yaml
    servers:
      - server_id: filesystem
        command: ["npx", "-y", "@modelcontextprotocol/server-filesystem", "/tmp"]
        env:
          NODE_ENV: production
        enabled: true
        priority: 10
        category: storage
        description: Filesystem access MCP server

      - server_id: github
        command: ["npx", "-y", "@modelcontextprotocol/server-github"]
        env:
          GITHUB_TOKEN: ${GITHUB_TOKEN}
        enabled: true
        priority: 5
        category: development
    ```

    Args:
        yaml_path: Path to YAML configuration file

    Returns:
        Number of servers loaded
    """
    yaml_path = Path(yaml_path)

    if not yaml_path.exists():
        logger.warning("mcp_server_registry.yaml_not_found", path=str(yaml_path))
        return 0

    try:
        with open(yaml_path, "r") as f:
            config = yaml.safe_load(f)

        if not config or "servers" not in config:
            logger.warning(
                "mcp_server_registry.no_servers_in_yaml", path=str(yaml_path)
            )
            return 0

        count = 0
        for server_def in config["servers"]:
            server_id = server_def.get("server_id")
            command = server_def.get("command")

            if not server_id or not command:
                logger.warning(
                    "mcp_server_registry.invalid_server_def", server_def=server_def
                )
                continue

            # Extract configuration
            env = server_def.get("env", {})
            enabled = server_def.get("enabled", True)
            priority = server_def.get("priority", 0)

            # Extract metadata
            metadata = {
                k: v
                for k, v in server_def.items()
                if k not in ["server_id", "command", "env", "enabled", "priority"]
            }

            # Register server
            register_mcp_server(
                server_id=server_id,
                command=command,
                env=env,
                enabled=enabled,
                priority=priority,
                **metadata,
            )
            count += 1

        logger.info("mcp_server_registry.yaml_loaded", path=str(yaml_path), count=count)
        return count

    except Exception as e:
        logger.error(
            "mcp_server_registry.yaml_load_error", path=str(yaml_path), error=str(e)
        )
        return 0


def get_all_mcp_servers() -> Dict[str, MCPServerConfig]:
    """
    Get all registered MCP server configurations.

    Returns:
        Dictionary mapping server IDs to configurations

    Example:
        servers = get_all_mcp_servers()
        for server_id, config in servers.items():
            print(f"Server: {server_id}, Command: {config.command}")
    """
    mcp_server_registry.initialize_factories()

    servers: Dict[str, MCPServerConfig] = {}

    for server_id in mcp_server_registry.list_ids():
        config = mcp_server_registry.get(server_id)
        if config and config.enabled:
            servers[server_id] = config

    logger.info("mcp_server_registry.servers_retrieved", count=len(servers))
    return servers


def get_mcp_servers_by_category(category: str) -> Dict[str, MCPServerConfig]:
    """
    Get all MCP servers in a specific category.

    Args:
        category: Category to filter by (e.g., "storage", "development")

    Returns:
        Dictionary mapping server IDs to configurations
    """
    mcp_server_registry.initialize_factories()

    configs = mcp_server_registry.get_all(tags=[category])
    servers: Dict[str, MCPServerConfig] = {}

    for config in configs:
        if config.enabled:
            servers[config.server_id] = config

    return servers


def get_mcp_server_snapshot() -> dict:
    """Get a snapshot of all registered MCP servers for observability."""
    return mcp_server_registry.snapshot()


# =============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "RUN-MCP-AUTO-REG",
    "governance_level": "critical",
    "security_reviewed": True,
    "performance_tested": True,
    "last_audit": "2026-01-18T00:00:00Z",
}
# ============================================================================
