"""
Phase 2: Instantiate Agent Instance

Harvested from: L9-Agent-Bootstrap-Architecture.md
Purpose: Create agent instance in memory and register in Neo4j.

NOTE: This module returns BootstrapInstanceData (initialization metadata),
NOT the runtime AgentInstance class. The main AgentInstance lives in
core/agents/agent_instance.py and is the production runtime class.
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Optional
from dataclasses import dataclass, field
from datetime import datetime
import uuid

import structlog

from memory.graph_client import get_neo4j_client

if TYPE_CHECKING:
    from core.agents.schemas import AgentConfig
    from memory.substrate_service import MemorySubstrateService

logger = structlog.get_logger(__name__)


@dataclass
class BootstrapInstanceData:
    """
    Bootstrap initialization data for an agent instance.
    
    This is NOT the runtime AgentInstance class. This dataclass holds
    metadata generated during bootstrap Phase 2 that can be used to
    initialize the main AgentInstance (core/agents/agent_instance.py).
    
    The separation ensures:
    - Bootstrap generates instance metadata + Neo4j registration
    - Main AgentInstance handles runtime execution, task processing, DAG context
    """
    instance_id: str
    agent_id: str
    name: str
    config: "AgentConfig"
    kernel_state: str = "LOADING"
    status: str = "INITIALIZING"
    created_at: datetime = field(default_factory=datetime.utcnow)
    initialized_at: Optional[datetime] = None
    initialization_signature: Optional[str] = None
    designation: Optional[str] = None
    role: Optional[str] = None
    mission: Optional[str] = None
    authority: Optional[str] = None


async def instantiate_agent(
    config: "AgentConfig",
    substrate_service: "MemorySubstrateService",
) -> BootstrapInstanceData:
    """
    Create bootstrap instance data and register agent in Neo4j.
    
    NOTE: This returns BootstrapInstanceData for use in bootstrap phases 3-7.
    The runtime AgentInstance (core/agents/agent_instance.py) is created
    separately in executor.py when processing tasks.
    """
    # Generate unique instance ID
    instance_id = str(uuid.uuid4())
    
    # Create bootstrap instance data
    instance = BootstrapInstanceData(
        instance_id=instance_id,
        agent_id=config.agent_id,
        name=config.name,
        config=config,
        kernel_state="LOADING",
        created_at=datetime.utcnow(),
    )
    
    # Register in Neo4j if available
    neo4j_client = await get_neo4j_client()
    if neo4j_client:
        try:
            async with neo4j_client.session() as session:
                await session.run("""
                    MERGE (a:Agent {agent_id: $agent_id})
                    SET a.instance_id = $instance_id,
                        a.name = $name,
                        a.kernel_state = 'LOADING',
                        a.status = 'INITIALIZING',
                        a.created_at = $created_at
                """, {
                    "instance_id": instance_id,
                    "agent_id": config.agent_id,
                    "name": config.name,
                    "created_at": instance.created_at.isoformat(),
                })
            logger.info(
                "Agent registered in Neo4j",
                agent_id=config.agent_id,
                instance_id=instance_id,
            )
        except Exception as e:
            logger.warning(
                "Failed to register agent in Neo4j, continuing",
                error=str(e),
            )
    
    logger.info(
        "Instantiated agent",
        agent_id=config.agent_id,
        instance_id=instance_id,
    )
    return instance

