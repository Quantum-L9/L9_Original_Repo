"""
Phase 5: Bind Tools & Capabilities

Harvested from: L9-Agent-Bootstrap-Architecture.md
Purpose: Load tool definitions, register in Neo4j, create tool→governance mappings.
"""

from __future__ import annotations

# ============================================================================
__dora_meta__ = {
    "component_name": "Phase 5 Bind Tools",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2026-01-06T15:07:54Z",
    "updated_at": "2026-01-17T23:47:56Z",
    "layer": "foundation",
    "domain": "agent_execution",
    "module_name": "phase_5_bind_tools",
    "type": "dataclass",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": ["Neo4j"],
        "memory_layers": ["working_memory"],
        "imported_by": ["tests.core.bootstrap.test_bootstrap_phases"],
    },
}
# ============================================================================

from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING

import structlog

if TYPE_CHECKING:
    from memory.substrate_service import MemorySubstrateService

    from .phase_2_instantiate import BootstrapInstanceData

logger = structlog.get_logger(__name__)


@dataclass
class ToolDefinition:
    """Tool definition with governance metadata"""

    tool_id: str
    name: str
    description: str
    category: str = "general"
    scope: str = "agent"
    risk_level: str = "low"
    requires_igor_approval: bool = False
    is_destructive: bool = False


async def get_agent_capabilities(agent_id: str) -> list[ToolDefinition]:
    """
    Get tool definitions available to this agent.

    .. deprecated:: 2026-01-25
        Use `core.tools.dynamic_discovery.discover_tools_for_task()` instead.
        This static binding approach is replaced by dynamic semantic search.
        See GMP-TD-WIRE for migration details.

    This loads from the tool registry or returns default tools.
    """
    import warnings

    warnings.warn(
        "get_agent_capabilities() is deprecated. "
        "Use core.tools.dynamic_discovery.discover_tools_for_task() for "
        "dynamic tool discovery via semantic + BM25 hybrid search.",
        DeprecationWarning,
        stacklevel=2,
    )

    try:
        from core.tools.registry_adapter import get_tools_for_agent

        return await get_tools_for_agent(agent_id)
    except ImportError:
        logger.debug("Tool registry not available, using default tools")

    # Default tools for L-CTO
    return [
        ToolDefinition(
            tool_id="memory_search",
            name="memory_search",
            description="Search agent memory",
            category="memory",
            risk_level="low",
        ),
        ToolDefinition(
            tool_id="memory_write",
            name="memory_write",
            description="Write to agent memory",
            category="memory",
            risk_level="low",
        ),
        ToolDefinition(
            tool_id="gmp_run",
            name="gmp_run",
            description="Execute GMP protocol",
            category="governance",
            risk_level="high",
            requires_igor_approval=True,
        ),
        ToolDefinition(
            tool_id="git_commit",
            name="git_commit",
            description="Commit changes to git",
            category="code",
            risk_level="high",
            requires_igor_approval=True,
            is_destructive=True,
        ),
    ]



async def bind_tools_and_capabilities(
    instance: BootstrapInstanceData,
    substrate_service: MemorySubstrateService,
) -> None:
    """
    Load tool definitions and bind to agent.
    """
    # Get tool definitions for this agent
    tool_definitions = await get_agent_capabilities(instance.agent_id)

    if not tool_definitions:
        logger.warning(
            "No tools found for agent",
            agent_id=instance.agent_id,
        )
        return

    # Lazy import to avoid test collection issues
    from memory.graph_client import get_neo4j_client

    neo4j_client = await get_neo4j_client()
    if not neo4j_client:
        logger.info(
            "Neo4j not available, tools bound in memory only",
            tool_count=len(tool_definitions),
        )
        return

    try:
        async with neo4j_client.session() as session:
            for tool_def in tool_definitions:
                # Create or merge tool node
                await session.run(
                    """
                    MERGE (t:Tool {tool_id: $tool_id})
                    SET t.name = $name,
                        t.description = $description,
                        t.category = $category,
                        t.scope = $scope,
                        t.risk_level = $risk_level,
                        t.requires_igor_approval = $requires_approval,
                        t.is_destructive = $is_destructive,
                        t.registered_at = $registered_at
                """,
                    {
                        "tool_id": tool_def.tool_id,
                        "name": tool_def.name,
                        "description": tool_def.description,
                        "category": tool_def.category,
                        "scope": tool_def.scope,
                        "risk_level": tool_def.risk_level,
                        "requires_approval": tool_def.requires_igor_approval,
                        "is_destructive": tool_def.is_destructive,
                        "registered_at": datetime.utcnow().isoformat(),
                    },
                )

                # Create relationship: Agent → Tool
                await session.run(
                    """
                    MATCH (a:Agent {instance_id: $instance_id})
                    MATCH (t:Tool {tool_id: $tool_id})
                    MERGE (a)-[rel:CAN_EXECUTE]->(t)
                    SET rel.bound_at = $bound_at,
                        rel.requires_approval = $requires_approval
                """,
                    {
                        "instance_id": instance.instance_id,
                        "tool_id": tool_def.tool_id,
                        "bound_at": datetime.utcnow().isoformat(),
                        "requires_approval": tool_def.requires_igor_approval,
                    },
                )

                logger.debug(
                    "Bound tool to agent",
                    tool=tool_def.name,
                    agent_id=instance.agent_id,
                )

        logger.info(
            "Tools bound to agent",
            agent_id=instance.agent_id,
            tool_count=len(tool_definitions),
        )

    except Exception as e:
        logger.error("Failed to bind tools", error=str(e))
        raise RuntimeError(f"Tool binding failed: {e}") from e


# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "COR-FOUN-041",
    "governance_level": "critical",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [
        "core.tools.registry_adapter",
        "memory.graph_client",
        "memory.substrate_service",
    ],
    "tags": [
        "agent-execution",
        "api",
        "async",
        "dataclass",
        "debugging",
        "foundation",
        "logging",
        "testing",
    ],
    "keywords": [
        "agent",
        "bind",
        "capabilities",
        "definition",
        "governance",
        "phase",
        "tool",
        "tools",
    ],
    "business_value": "Implements ToolDefinition for phase 5 bind tools functionality",
    "last_modified": "2026-01-17T23:47:56Z",
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
