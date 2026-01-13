"""
Phase 5: Bind Tools & Capabilities

Harvested from: L9-Agent-Bootstrap-Architecture.md
Purpose: Load tool definitions, register in Neo4j, create tool→governance mappings.
"""
from __future__ import annotations

from typing import TYPE_CHECKING, List, Optional
from dataclasses import dataclass
from datetime import datetime

import structlog

from memory.graph_client import get_neo4j_client

if TYPE_CHECKING:
    from .phase_2_instantiate import BootstrapInstanceData
    from memory.substrate_service import MemorySubstrateService

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


async def get_agent_capabilities(agent_id: str) -> List[ToolDefinition]:
    """
    Get tool definitions available to this agent.
    
    This loads from the tool registry or returns default tools.
    """
    try:
        from core.tools.registry_adapter import get_tools_for_agent
        return await get_tools_for_agent(agent_id)
    except ImportError:
        logger.debug("Tool registry not available, using default tools")
    
    # Default tools for L-CTO
    default_tools = [
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
    
    return default_tools


async def bind_tools_and_capabilities(
    instance: "BootstrapInstanceData",
    substrate_service: "MemorySubstrateService",
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
                await session.run("""
                    MERGE (t:Tool {tool_id: $tool_id})
                    SET t.name = $name,
                        t.description = $description,
                        t.category = $category,
                        t.scope = $scope,
                        t.risk_level = $risk_level,
                        t.requires_igor_approval = $requires_approval,
                        t.is_destructive = $is_destructive,
                        t.registered_at = $registered_at
                """, {
                    "tool_id": tool_def.tool_id,
                    "name": tool_def.name,
                    "description": tool_def.description,
                    "category": tool_def.category,
                    "scope": tool_def.scope,
                    "risk_level": tool_def.risk_level,
                    "requires_approval": tool_def.requires_igor_approval,
                    "is_destructive": tool_def.is_destructive,
                    "registered_at": datetime.utcnow().isoformat(),
                })
                
                # Create relationship: Agent → Tool
                await session.run("""
                    MATCH (a:Agent {instance_id: $instance_id})
                    MATCH (t:Tool {tool_id: $tool_id})
                    MERGE (a)-[rel:CAN_EXECUTE]->(t)
                    SET rel.bound_at = $bound_at,
                        rel.requires_approval = $requires_approval
                """, {
                    "instance_id": instance.instance_id,
                    "tool_id": tool_def.tool_id,
                    "bound_at": datetime.utcnow().isoformat(),
                    "requires_approval": tool_def.requires_igor_approval,
                })
                
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
        raise RuntimeError(f"Tool binding failed: {e}")

