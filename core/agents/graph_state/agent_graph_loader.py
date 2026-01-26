"""
Agent Graph Loader
==================

Loads agent state from Neo4j graph instead of YAML kernels.
This enables faster startup (~100-500ms vs 5-7s) and runtime state persistence.

Usage:
    loader = AgentGraphLoader(neo4j_driver)
    state = await loader.load("L")

Version: 1.0.0
Created: 2026-01-05
"""

from __future__ import annotations

# ============================================================================
__dora_meta__ = {
    "component_name": "Agent Graph Loader",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2026-01-06T15:07:54Z",
    "updated_at": "2026-01-14T15:03:00Z",
    "layer": "foundation",
    "domain": "agent_execution",
    "module_name": "agent_graph_loader",
    "type": "dataclass",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": ["Neo4j"],
        "memory_layers": [],
        "imported_by": [
            "tests.core.bootstrap.test_graph_state",
            "tests.memory.test_consolidation_graph",
        ],
    },
}
# ============================================================================

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

import structlog

from .schema import (
    AGENT_EXISTS_QUERY,
    GET_DIRECTIVES_BY_SEVERITY_QUERY,
    GET_TOOLS_QUERY,
    LOAD_AGENT_STATE_QUERY,
)

if TYPE_CHECKING:
    from neo4j import AsyncDriver

logger = structlog.get_logger(__name__)


@dataclass
class AgentResponsibility:
    """A responsibility assigned to an agent."""

    title: str
    description: str
    priority: int = 1


@dataclass
class AgentDirective:
    """A behavioral directive for an agent."""

    text: str
    context: str
    severity: str  # CRITICAL, HIGH, MEDIUM, LOW


@dataclass
class AgentSOP:
    """A standard operating procedure."""

    name: str
    steps: list[str]


@dataclass
class AgentTool:
    """A tool available to the agent."""

    name: str
    risk_level: str  # HIGH, MEDIUM, LOW
    requires_approval: bool
    approval_source: str | None = None


@dataclass
class AgentGraphState:
    """
    Complete agent state loaded from Neo4j graph.

    This replaces the kernel-based AgentConfig for mutable state.
    """

    agent_id: str
    designation: str
    role: str
    mission: str
    authority_level: str
    status: str = "ACTIVE"

    responsibilities: list[AgentResponsibility] = field(default_factory=list)
    directives: list[AgentDirective] = field(default_factory=list)
    sops: list[AgentSOP] = field(default_factory=list)
    tools: list[AgentTool] = field(default_factory=list)

    supervisor_id: str | None = None
    collaborator_ids: list[str] = field(default_factory=list)

    def get_critical_directives(self) -> list[AgentDirective]:
        """Get all CRITICAL severity directives."""
        return [d for d in self.directives if d.severity == "CRITICAL"]

    def get_high_risk_tools(self) -> list[AgentTool]:
        """Get tools requiring Igor approval."""
        return [t for t in self.tools if t.requires_approval]

    def get_sop_steps(self, sop_name: str) -> list[str]:
        """Get steps for a specific SOP."""
        for sop in self.sops:
            if sop.name == sop_name:
                return sop.steps
        return []


class AgentGraphLoader:
    """
    Loads agent state from Neo4j graph.

    This replaces KernelLoader for mutable agent state, enabling:
    - Faster startup (single query vs multiple YAML parses)
    - Runtime state persistence across restarts
    - Real-time self-modification
    - Full audit trail in Neo4j
    """

    def __init__(self, neo4j_driver: AsyncDriver):
        self.driver = neo4j_driver
        self._cache: dict[str, AgentGraphState] = {}

    async def load(
        self,
        agent_id: str,
        use_cache: bool = True,
    ) -> AgentGraphState:
        """
        Load complete agent state from Neo4j.

        Args:
            agent_id: The agent to load (e.g., "L")
            use_cache: Whether to use cached state if available

        Returns:
            AgentGraphState with all responsibilities, directives, SOPs, tools

        Raises:
            ValueError: If agent not found in graph
        """
        # Check cache
        if use_cache and agent_id in self._cache:
            logger.debug("Using cached agent state", agent_id=agent_id)
            return self._cache[agent_id]

        logger.info("Loading agent state from Neo4j", agent_id=agent_id)

        async with self.driver.session() as session:
            # Run main query
            result = await session.run(
                LOAD_AGENT_STATE_QUERY,
                agent_id=agent_id,
            )
            record = await result.single()

            if not record or not record["a"]:
                raise ValueError(f"Agent not found in graph: {agent_id}")

            # Parse agent node
            agent_node = record["a"]

            # Parse responsibilities
            responsibilities = [
                AgentResponsibility(
                    title=r["title"],
                    description=r["description"],
                    priority=r.get("priority", 1),
                )
                for r in record["responsibilities"]
                if r is not None
            ]

            # Parse directives
            directives = [
                AgentDirective(
                    text=d["text"],
                    context=d.get("context", "general"),
                    severity=d.get("severity", "MEDIUM"),
                )
                for d in record["directives"]
                if d is not None
            ]

            # Parse SOPs
            sops = [
                AgentSOP(
                    name=s["name"],
                    steps=s.get("steps", []),
                )
                for s in record["sops"]
                if s is not None
            ]

            # Parse tools
            tools = [
                AgentTool(
                    name=t["name"],
                    risk_level=t.get("risk_level", "LOW"),
                    requires_approval=t.get("requires_approval", False),
                    approval_source=t.get("approval_source"),
                )
                for t in record["tools"]
                if t is not None
            ]

            # Parse supervisor
            supervisor = record["supervisor"]
            supervisor_id = supervisor["agent_id"] if supervisor else None

            # Parse collaborators
            collaborator_ids = [
                p["agent_id"] for p in record["collaborators"] if p is not None
            ]

            # Build state object
            state = AgentGraphState(
                agent_id=agent_node["agent_id"],
                designation=agent_node.get("designation", "Unknown"),
                role=agent_node.get("role", "Unknown"),
                mission=agent_node.get("mission", ""),
                authority_level=agent_node.get("authority_level", "AGENT"),
                status=agent_node.get("status", "ACTIVE"),
                responsibilities=responsibilities,
                directives=directives,
                sops=sops,
                tools=tools,
                supervisor_id=supervisor_id,
                collaborator_ids=collaborator_ids,
            )

            # Cache result
            self._cache[agent_id] = state

            logger.info(
                "Loaded agent state from Neo4j",
                agent_id=agent_id,
                responsibilities=len(responsibilities),
                directives=len(directives),
                sops=len(sops),
                tools=len(tools),
                supervisor=supervisor_id,
            )

            return state

    async def exists(self, agent_id: str) -> bool:
        """Check if agent exists in graph."""
        async with self.driver.session() as session:
            result = await session.run(
                AGENT_EXISTS_QUERY,
                agent_id=agent_id,
            )
            record = await result.single()
            return record is not None and record["exists"]

    def invalidate_cache(self, agent_id: str | None = None) -> None:
        """
        Invalidate cached agent state.

        Args:
            agent_id: Specific agent to invalidate, or None for all
        """
        if agent_id:
            self._cache.pop(agent_id, None)
            logger.debug("Invalidated cache for agent", agent_id=agent_id)
        else:
            self._cache.clear()
            logger.debug("Invalidated all agent state cache")

    async def get_critical_directives(
        self,
        agent_id: str,
    ) -> list[AgentDirective]:
        """Get only CRITICAL directives for fast governance checks."""
        async with self.driver.session() as session:
            result = await session.run(
                GET_DIRECTIVES_BY_SEVERITY_QUERY,
                agent_id=agent_id,
                severity="CRITICAL",
            )
            records = await result.data()

            return [
                AgentDirective(
                    text=r["text"],
                    context=r["context"],
                    severity=r["severity"],
                )
                for r in records
            ]

    async def get_tools_requiring_approval(
        self,
        agent_id: str,
    ) -> list[AgentTool]:
        """Get tools that require Igor approval."""
        async with self.driver.session() as session:
            result = await session.run(
                GET_TOOLS_QUERY,
                agent_id=agent_id,
            )
            records = await result.data()

            return [
                AgentTool(
                    name=r["name"],
                    risk_level=r["risk_level"],
                    requires_approval=r["requires_approval"],
                    approval_source=r.get("approval_source"),
                )
                for r in records
                if r["requires_approval"]
            ]


# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "COR-FOUN-047",
    "governance_level": "critical",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": [
        "agent-execution",
        "async",
        "auth",
        "caching",
        "dataclass",
        "debugging",
        "foundation",
        "graph-db",
        "loader",
        "logging",
    ],
    "keywords": [
        "agent",
        "approval",
        "cache",
        "critical",
        "directive",
        "directives",
        "exists",
        "graph",
    ],
    "business_value": "This enables faster startup (~100-500ms vs 5-7s) and runtime state persistence. loader = AgentGraphL",
    "last_modified": "2026-01-14T15:03:00Z",
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
