"""
L9 Agents - Agent Auto-Discovery System
========================================

Automatic discovery and registration of agent classes.

This module eliminates manual agent imports and __all__ maintenance by
providing a decorator-based registration system that automatically discovers
and registers agent classes.

Version: 1.0.0
"""

from __future__ import annotations

# ============================================================================
__dora_meta__ = {
    "component_name": "Agent Auto-Discovery",
    "module_version": "1.0.0",
    "created_by": "L9 Auto-Wiring Team",
    "created_at": "2026-01-18T00:00:00Z",
    "updated_at": "2026-01-18T00:00:00Z",
    "layer": "agents",
    "domain": "agents",
    "module_name": "agent_registry",
    "type": "service",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": [],
        "memory_layers": [],
        "imported_by": ["agents.__init__"],
    },
}
# ============================================================================

from typing import Any
import threading

import structlog

from core.auto_registry import AutoRegistry

logger = structlog.get_logger(__name__)


# =============================================================================
# Agent Registry
# =============================================================================


def _validate_agent_class(cls: type) -> bool:
    """Validate that an object is an agent class."""
    # Check if it's a class and has required agent attributes
    return isinstance(cls, type) and hasattr(cls, "__name__")


# Global agent registry
agent_registry = AutoRegistry[type](
    name="agents", validator=_validate_agent_class, allow_duplicates=False
)
agent_registry_lock = threading.Lock()


def register_agent(
    name: str | None = None,
    role: str | None = None,
    category: str | None = None,
    priority: int = 0,
    **metadata: Any,
):
    """
    Decorator to register an agent class for auto-discovery.

    This decorator marks an agent class for automatic discovery and
    registration in the agents module.

    Args:
        name: Agent identifier (defaults to class name)
        role: Agent role (e.g., "architect", "coder", "qa")
        category: Agent category (e.g., "primary", "secondary", "meta")
        priority: Registration priority (higher = loaded first)
        **metadata: Additional metadata

    Example:
        @register_agent(role="architect", category="primary")
        class ArchitectAgentA(BaseAgent):
            # ... implementation ...
            pass

        # Or with explicit name
        @register_agent(name="custom_agent", role="custom")
        class MyCustomAgent(BaseAgent):
            pass
    """
    tags = []
    if role:
        tags.append(role)
    if category:
        tags.append(category)

    def decorator(cls: type) -> type:
        """
        Registers an agent class for automatic discovery within the agent registry system.

        Args:
            cls: The agent class to be registered.
            name: Optional custom name for the agent; defaults to class name.
            priority: Registration priority level.
            tags: List of tags associated with the agent.

        Returns:
            The registered agent class.
        """
        # Register the class directly (not as a factory)
        agent_name = name or cls.__name__
        with agent_registry_lock:
        agent_registry.register_instance(
            component_id=agent_name,
            component=cls,
            priority=priority,
            tags=tags,
            **metadata,
        )
        return cls

    return decorator


def discover_agents(package: str = "agents") -> int:
    """
    Automatically discover all agents in the specified package.

    Args:
        package: Python package to scan for agents

    Returns:
        Number of modules discovered
    """
    logger.info("agent_registry.discovering", package=package)
    count = agent_registry.discover(package, recursive=True)
    logger.info("agent_registry.discovered", package=package, count=count)
    return count


def get_all_agents() -> dict[str, type]:
    """
    Get all registered agent classes as a dictionary.

    Returns:
        Dictionary mapping agent names to agent classes

    Example:
        agents = get_all_agents()
        architect = agents["ArchitectAgentA"]
        instance = architect(config)
    """
    # Initialize any factory functions
    agent_registry.initialize_factories()

    # Build dictionary mapping names to classes
    agents: dict[str, type] = {}

    for agent_id in agent_registry.list_ids():
        agent_cls = agent_registry.get(agent_id)
        if agent_cls:
            agents[agent_id] = agent_cls

    logger.info("agent_registry.agents_built", count=len(agents))
    return agents


def get_agents_by_role(role: str) -> dict[str, type]:
    """
    Get all agent classes with a specific role.

    Args:
        role: Role to filter by (e.g., "architect", "coder", "qa")

    Returns:
        Dictionary mapping agent names to agent classes
    """
    agent_registry.initialize_factories()

    agents_list = agent_registry.get_all(tags=[role])
    agents: dict[str, type] = {}

    for agent_cls in agents_list:
        # Find the agent's ID
        for agent_id in agent_registry.list_ids():
            if agent_registry.get(agent_id) == agent_cls:
                agents[agent_id] = agent_cls
                break

    return agents


def get_agents_by_category(category: str) -> dict[str, type]:
    """
    Get all agent classes in a specific category.

    Args:
        category: Category to filter by (e.g., "primary", "secondary", "meta")

    Returns:
        Dictionary mapping agent names to agent classes
    """
    agent_registry.initialize_factories()

    agents_list = agent_registry.get_all(tags=[category])
    agents: dict[str, type] = {}

    for agent_cls in agents_list:
        # Find the agent's ID
        for agent_id in agent_registry.list_ids():
            if agent_registry.get(agent_id) == agent_cls:
                agents[agent_id] = agent_cls
                break

    return agents


def build_agent_exports() -> list[str]:
    """
    Build the __all__ list for agents/__init__.py.

    This function generates the list of agent names that should be
    exported from the agents module, eliminating manual maintenance.

    Returns:
        List of agent names to export

    Example:
        # In agents/__init__.py
        from agents.agent_registry import build_agent_exports
        __all__ = build_agent_exports()
    """
    agent_registry.initialize_factories()
    return agent_registry.list_ids()


def get_agent_snapshot() -> dict:
    """Get a snapshot of all registered agents for observability."""
    return agent_registry.snapshot()


def register_legacy_agents() -> int:
    """
    Bridge function: Register all agents from agents/__init__.py exports.

    This allows existing agent classes to be discovered by the new
    auto-registration system without adding decorators to each class.

    Returns:
        Number of agents registered
    """
    import importlib.util
    from pathlib import Path

    registered = 0

    # Find agents directory
    agents_dir = Path(__file__).parent

    # Define agents to register with their metadata (name, file_path, role, category)
    agent_specs = [
        # Architect agents
        (
            "ArchitectAgentA",
            "architect_agent/architect_agent_a.py",
            "architect",
            "design",
        ),
        (
            "ArchitectAgentB",
            "architect_agent/architect_agent_b.py",
            "architect",
            "design",
        ),
        # Coder agents
        ("CoderAgentA", "coder_agent/coder_agent_a.py", "coder", "implementation"),
        ("CoderAgentB", "coder_agent/coder_agent_b.py", "coder", "implementation"),
        # Quality agent
        ("QAAgent", "qa_agent.py", "qa", "quality"),
        # Meta agent
        ("ReflectionAgent", "reflection_agent.py", "reflection", "meta"),
        # L-CTO agent
        ("LCTOAgent", "l_cto.py", "cto", "leadership"),
    ]

    for agent_name, file_path, role, category in agent_specs:
        try:
            full_path = agents_dir / file_path
            if not full_path.exists():
                logger.debug(
                    "legacy_agent_file_not_found", agent=agent_name, path=str(full_path)
                )
                continue

            # Import directly from file to avoid package __init__.py
            spec = importlib.util.spec_from_file_location(agent_name, full_path)
            if spec and spec.loader:
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
                agent_cls = getattr(mod, agent_name, None)

                if agent_cls:
                    with agent_registry_lock:
        agent_registry.register_instance(
                        component_id=agent_name,
                        component=agent_cls,
                        priority=10 if role == "cto" else 5,
                        tags=[role, category, "legacy"],
                        role=role,
                        category=category,
                        source="legacy_bridge",
                    )
                    registered += 1
                    logger.debug("legacy_agent_registered", agent=agent_name, role=role)
        except (ImportError, AttributeError) as e:
            logger.debug("legacy_agent_skip", agent=agent_name, error=str(e))

    if registered > 0:
        logger.info("legacy_agents_registered", count=registered)

    return registered


# =============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "AGT-AUTO-DISC",
    "governance_level": "critical",
    "security_reviewed": True,
    "performance_tested": True,
    "last_audit": "2026-01-18T00:00:00Z",
}
# ============================================================================
