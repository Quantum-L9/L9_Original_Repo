"""
L9 Research Factory - Glue Layer Resolver
==========================================

Resolves inter-agent dependencies from glue YAML configuration.

The glue layer defines:
- Agent wirings (API calls, packet sends, event subscriptions)
- Memory harmonization (shared backends)
- Governance harmonization (shared anchors, escalation triggers)
- Communication harmonization (protocol, auth, encryption)

Version: 1.0.0
"""

from __future__ import annotations

# ============================================================================
__dora_meta__ = {
    "component_name": "Glue Layer Resolver",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2025-12-20T15:08:40Z",
    "updated_at": "2026-01-06T16:58:23Z",
    "layer": "foundation",
    "domain": "data_models",
    "module_name": "glue_resolver",
    "type": "dataclass",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": ["Neo4j", "PostgreSQL", "Redis", "S3"],
        "memory_layers": ["working_memory"],
        "imported_by": [],
    },
}
# ============================================================================

import structlog
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

import yaml
from pydantic import BaseModel, Field

logger = structlog.get_logger(__name__)


# =============================================================================
# Glue Configuration Models
# =============================================================================


class WiringSpec(BaseModel):
    """Specification for an agent-to-agent wiring."""

    from_agent: str = Field(..., description="Source agent name")
    to_agent: str = Field(..., description="Target agent name")
    connection_type: str = Field(
        ..., description="Type: api_call, packet_send, event_observe"
    )
    import_path: str = Field(..., description="Python import path for the connection")
    method_names: list[str] = Field(
        default_factory=list, description="Methods to call (for api_call)"
    )
    packet_types: list[str] = Field(
        default_factory=list, description="Packet types (for packet_send)"
    )
    event_subscriptions: list[str] = Field(
        default_factory=list, description="Events (for event_observe)"
    )


class MemoryBackendsConfig(BaseModel):
    """Shared memory backend configuration."""

    redis: Optional[str] = Field(None, description="Redis connection string")
    postgres: Optional[str] = Field(None, description="PostgreSQL connection string")
    neo4j: Optional[str] = Field(None, description="Neo4j connection string")
    hypergraph: Optional[str] = Field(
        None, description="HypergraphDB connection string"
    )
    s3: Optional[str] = Field(None, description="S3 bucket URL")


class GovernanceHarmonizationConfig(BaseModel):
    """Shared governance configuration."""

    anchors: list[str] = Field(
        default_factory=list, description="Governance anchor names"
    )
    shared_escalation_triggers: list[str] = Field(
        default_factory=list, description="Shared triggers"
    )


class CommunicationHarmonizationConfig(BaseModel):
    """Shared communication configuration."""

    protocol: str = Field(
        default="PacketEnvelope", description="Communication protocol"
    )
    auth: str = Field(default="JWT", description="Authentication method")
    encryption: str = Field(default="TLS 1.3", description="Encryption method")


class GlueConfig(BaseModel):
    """Complete glue layer configuration."""

    wirings: list[WiringSpec] = Field(default_factory=list, description="Agent wirings")
    memory_harmonization: Optional[dict[str, Any]] = Field(
        None, description="Memory config"
    )
    governance_harmonization: Optional[GovernanceHarmonizationConfig] = None
    communication_harmonization: Optional[CommunicationHarmonizationConfig] = None

    model_config = {"extra": "allow"}


# =============================================================================
# Import Specification
# =============================================================================


@dataclass
class ImportSpec:
    """Specification for a Python import."""

    module_path: str
    names: list[str] = field(default_factory=list)
    alias: Optional[str] = None

    def to_import_statement(self) -> str:
        """Generate Python import statement."""
        if self.names:
            names_str = ", ".join(self.names)
            return f"from {self.module_path} import {names_str}"
        elif self.alias:
            return f"import {self.module_path} as {self.alias}"
        else:
            return f"import {self.module_path}"


# =============================================================================
# Dependency Graph
# =============================================================================


@dataclass
class DependencyNode:
    """Node in the dependency graph."""

    agent_name: str
    dependencies: set[str] = field(default_factory=set)
    dependents: set[str] = field(default_factory=set)


class DependencyGraph:
    """
    Directed acyclic graph of agent dependencies.

    Used to determine extraction order and detect circular dependencies.
    """

    def __init__(self):
        self._nodes: dict[str, DependencyNode] = {}

    def add_agent(self, agent_name: str) -> None:
        """Add an agent to the graph."""
        if agent_name not in self._nodes:
            self._nodes[agent_name] = DependencyNode(agent_name)

    def add_dependency(self, agent: str, depends_on: str) -> None:
        """Add a dependency edge: agent depends on depends_on."""
        self.add_agent(agent)
        self.add_agent(depends_on)

        self._nodes[agent].dependencies.add(depends_on)
        self._nodes[depends_on].dependents.add(agent)

    def get_dependencies(self, agent: str) -> set[str]:
        """Get direct dependencies of an agent."""
        if agent not in self._nodes:
            return set()
        return self._nodes[agent].dependencies.copy()

    def get_dependents(self, agent: str) -> set[str]:
        """Get agents that depend on this agent."""
        if agent not in self._nodes:
            return set()
        return self._nodes[agent].dependents.copy()

    def has_circular_dependency(self) -> tuple[bool, Optional[list[str]]]:
        """
        Check for circular dependencies using DFS.

        Returns:
            (has_cycle, cycle_path) - If cycle found, returns the cycle path
        """
        visited = set()
        rec_stack = set()
        path = []

        def dfs(node: str) -> Optional[list[str]]:
            visited.add(node)
            rec_stack.add(node)
            path.append(node)

            for dep in self._nodes[node].dependencies:
                if dep not in visited:
                    cycle = dfs(dep)
                    if cycle:
                        return cycle
                elif dep in rec_stack:
                    # Found cycle
                    cycle_start = path.index(dep)
                    return path[cycle_start:] + [dep]

            path.pop()
            rec_stack.remove(node)
            return None

        for node in self._nodes:
            if node not in visited:
                cycle = dfs(node)
                if cycle:
                    return True, cycle

        return False, None

    def topological_sort(self) -> list[str]:
        """
        Return agents in topological order (dependencies first).

        Raises:
            ValueError: If circular dependency exists
        """
        has_cycle, cycle = self.has_circular_dependency()
        if has_cycle:
            raise ValueError(f"Circular dependency detected: {' -> '.join(cycle)}")

        visited = set()
        result = []

        def visit(node: str) -> None:
            if node in visited:
                return
            visited.add(node)

            for dep in self._nodes[node].dependencies:
                visit(dep)

            result.append(node)

        for node in self._nodes:
            visit(node)

        return result

    def get_parallel_groups(self) -> list[list[str]]:
        """
        Get groups of agents that can be extracted in parallel.

        Agents in the same group have no dependencies on each other.

        Returns:
            List of groups, where each group can be processed in parallel
        """
        has_cycle, cycle = self.has_circular_dependency()
        if has_cycle:
            raise ValueError(f"Circular dependency detected: {' -> '.join(cycle)}")

        groups = []
        remaining = set(self._nodes.keys())
        completed = set()

        while remaining:
            # Find all nodes whose dependencies are satisfied
            ready = {
                node
                for node in remaining
                if self._nodes[node].dependencies.issubset(completed)
            }

            if not ready:
                # Should not happen if no cycles
                raise ValueError("Unable to make progress - possible cycle")

            groups.append(sorted(ready))
            completed.update(ready)
            remaining -= ready

        return groups


# =============================================================================
# Glue Resolver
# =============================================================================


class GlueResolver:
    """
    Resolves inter-agent dependencies from glue configuration.

    Usage:
        resolver = GlueResolver(glue_config)

        # Get imports for an agent
        imports = resolver.resolve_imports("MainAgent")

        # Get wirings for an agent
        wirings = resolver.resolve_wirings("MainAgent")

        # Get extraction order
        order = resolver.get_dependency_order(["MainAgent", "TensorAIOS", "PlastOS"])
    """

    def __init__(self, config: GlueConfig):
        """
        Initialize resolver with glue configuration.

        Args:
            config: Parsed GlueConfig
        """
        self.config = config
        self._dependency_graph = self._build_dependency_graph()

    @classmethod
    def from_yaml(cls, yaml_content: str) -> GlueResolver:
        """
        Create resolver from YAML string.

        Args:
            yaml_content: YAML glue configuration

        Returns:
            GlueResolver instance
        """
        data = yaml.safe_load(yaml_content)
        config = GlueConfig.model_validate(data or {})
        return cls(config)

    @classmethod
    def from_file(cls, filepath: str | Path) -> GlueResolver:
        """
        Create resolver from YAML file.

        Args:
            filepath: Path to glue YAML file

        Returns:
            GlueResolver instance
        """
        path = Path(filepath)
        if not path.exists():
            raise FileNotFoundError(f"Glue file not found: {path}")

        with open(path, "r") as f:
            content = f.read()

        return cls.from_yaml(content)

    def _build_dependency_graph(self) -> DependencyGraph:
        """Build dependency graph from wirings."""
        graph = DependencyGraph()

        for wiring in self.config.wirings:
            # from_agent depends on to_agent
            graph.add_dependency(wiring.from_agent, wiring.to_agent)

        return graph

    def resolve_imports(self, agent_name: str) -> list[ImportSpec]:
        """
        Resolve what imports an agent needs from other agents.

        Args:
            agent_name: Name of the agent

        Returns:
            List of ImportSpec for the agent's dependencies
        """
        imports = []

        for wiring in self.config.wirings:
            if wiring.from_agent == agent_name:
                # This agent imports from to_agent
                module_path = wiring.import_path.replace("/", ".").replace(".py", "")

                # Remove L9 prefix if present
                if module_path.startswith("L9."):
                    module_path = module_path[3:]

                names = []
                if wiring.connection_type == "api_call":
                    names = wiring.method_names
                elif wiring.connection_type == "packet_send":
                    names = ["PacketEnvelope"]  # Standard packet protocol
                elif wiring.connection_type == "event_observe":
                    names = ["EventSubscriber"]  # Standard event subscriber

                imports.append(
                    ImportSpec(
                        module_path=module_path,
                        names=names,
                    )
                )

        return imports

    def resolve_wirings(self, agent_name: str) -> list[WiringSpec]:
        """
        Resolve wirings for an agent.

        Args:
            agent_name: Name of the agent

        Returns:
            List of WiringSpec where this agent is the source
        """
        return [
            wiring for wiring in self.config.wirings if wiring.from_agent == agent_name
        ]

    def resolve_inbound_wirings(self, agent_name: str) -> list[WiringSpec]:
        """
        Resolve inbound wirings to an agent.

        Args:
            agent_name: Name of the agent

        Returns:
            List of WiringSpec where this agent is the target
        """
        return [
            wiring for wiring in self.config.wirings if wiring.to_agent == agent_name
        ]

    def get_dependency_order(self, agents: list[str]) -> list[str]:
        """
        Get extraction order for a set of agents.

        Args:
            agents: List of agent names to order

        Returns:
            Agents in dependency order (extract first dependencies first)
        """
        # Build a subgraph for just these agents
        subgraph = DependencyGraph()

        for agent in agents:
            subgraph.add_agent(agent)

        for wiring in self.config.wirings:
            if wiring.from_agent in agents and wiring.to_agent in agents:
                subgraph.add_dependency(wiring.from_agent, wiring.to_agent)

        return subgraph.topological_sort()

    def get_parallel_extraction_groups(self, agents: list[str]) -> list[list[str]]:
        """
        Get groups of agents that can be extracted in parallel.

        Args:
            agents: List of agent names

        Returns:
            List of groups for parallel extraction
        """
        # Build subgraph
        subgraph = DependencyGraph()

        for agent in agents:
            subgraph.add_agent(agent)

        for wiring in self.config.wirings:
            if wiring.from_agent in agents and wiring.to_agent in agents:
                subgraph.add_dependency(wiring.from_agent, wiring.to_agent)

        return subgraph.get_parallel_groups()

    def check_circular_dependencies(self) -> tuple[bool, Optional[list[str]]]:
        """
        Check for circular dependencies in the glue configuration.

        Returns:
            (has_cycle, cycle_path)
        """
        return self._dependency_graph.has_circular_dependency()

    def get_memory_backends(self) -> MemoryBackendsConfig:
        """
        Get shared memory backend configuration.

        Returns:
            MemoryBackendsConfig with connection strings
        """
        if self.config.memory_harmonization:
            backends = self.config.memory_harmonization.get("shared_backends", {})
            return MemoryBackendsConfig.model_validate(backends)
        return MemoryBackendsConfig()

    def get_governance_anchors(self) -> list[str]:
        """
        Get shared governance anchors.

        Returns:
            List of anchor names
        """
        if self.config.governance_harmonization:
            return self.config.governance_harmonization.anchors
        return []

    def get_communication_protocol(self) -> str:
        """
        Get the communication protocol.

        Returns:
            Protocol name (default: PacketEnvelope)
        """
        if self.config.communication_harmonization:
            return self.config.communication_harmonization.protocol
        return "PacketEnvelope"


# =============================================================================
# Convenience Functions
# =============================================================================


def load_glue_config(filepath: str | Path) -> GlueConfig:
    """
    Load glue configuration from a YAML file.

    Args:
        filepath: Path to glue YAML file

    Returns:
        GlueConfig instance
    """
    path = Path(filepath)
    if not path.exists():
        raise FileNotFoundError(f"Glue file not found: {path}")

    with open(path, "r") as f:
        data = yaml.safe_load(f)

    return GlueConfig.model_validate(data or {})


def create_empty_glue_config() -> GlueConfig:
    """
    Create an empty glue configuration.

    Returns:
        Empty GlueConfig
    """
    return GlueConfig()


# =============================================================================
# Public API
# =============================================================================

__all__ = [
    # Main classes
    "GlueResolver",
    "GlueConfig",
    # Models
    "WiringSpec",
    "ImportSpec",
    "MemoryBackendsConfig",
    "GovernanceHarmonizationConfig",
    "CommunicationHarmonizationConfig",
    # Graph
    "DependencyGraph",
    "DependencyNode",
    # Functions
    "load_glue_config",
    "create_empty_glue_config",
]

# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "COD-FOUN-005",
    "governance_level": "critical",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": [
        "config",
        "data-models",
        "dataclass",
        "event-driven",
        "filesystem",
        "foundation",
        "logging",
        "pydantic",
        "security",
        "validation",
    ],
    "keywords": [
        "agent",
        "anchors",
        "backends",
        "check",
        "circular",
        "communication",
        "create",
        "dependencies",
    ],
    "business_value": "Agent wirings (API calls, packet sends, event subscriptions) Memory harmonization (shared backends) Governance harmonization (shared anchors, escalation triggers) Communication harmonization (protocol",
    "last_modified": "2026-01-06T16:58:23Z",
    "modified_by": "L9_Codegen_Engine",
    "change_summary": "Initial generation with DORA compliance",
}
# ============================================================================
# L9 DORA BLOCK - AUTO-UPDATED - DO NOT EDIT
# Runtime execution trace - updated automatically on every execution
# ============================================================================
__l9_trace__ = {
    "trace_id": "",
    "task": "",
    "timestamp": "",
    "patterns_used": [],
    "graph": {"nodes": [], "edges": []},
    "inputs": {},
    "outputs": {},
    "metrics": {"confidence": "", "errors_detected": [], "stability_score": ""},
}
# ============================================================================
# END L9 DORA BLOCK
# ============================================================================
