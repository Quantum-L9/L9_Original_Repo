"""
Phase 2: Instantiate Agent Instance

Harvested from: L9-Agent-Bootstrap-Architecture.md
Purpose: Create agent instance in memory and register in Neo4j + Redis.

NOTE: This module returns BootstrapInstanceData (initialization metadata),
NOT the runtime AgentInstance class. The main AgentInstance lives in
core/agents/agent_instance.py and is the production runtime class.

Redis Working Memory:
- Initializes Redis key for agent session state
- TTL: 24 hours (auto-expires if not renewed)
- Stores: kernel_state, current task, last activity
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Optional
from dataclasses import dataclass, field
from datetime import datetime
import uuid

import structlog

if TYPE_CHECKING:
    from core.agents.schemas import AgentConfig
    from memory.substrate_service import MemorySubstrateService

logger = structlog.get_logger(__name__)

# Redis TTL for working memory (24 hours)
WORKING_MEMORY_TTL_SECONDS = 24 * 60 * 60


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

    # Register in Neo4j if available (lazy import to avoid test collection issues)
    from memory.graph_client import get_neo4j_client

    neo4j_client = await get_neo4j_client()
    if neo4j_client:
        try:
            async with neo4j_client.session() as session:
                await session.run(
                    """
                    MERGE (a:Agent {agent_id: $agent_id})
                    SET a.instance_id = $instance_id,
                        a.name = $name,
                        a.kernel_state = 'LOADING',
                        a.status = 'INITIALIZING',
                        a.created_at = $created_at
                """,
                    {
                        "instance_id": instance_id,
                        "agent_id": config.agent_id,
                        "name": config.name,
                        "created_at": instance.created_at.isoformat(),
                    },
                )
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

    # Initialize Redis working memory
    redis_initialized = await _init_redis_working_memory(
        instance_id=instance_id,
        agent_id=config.agent_id,
    )

    logger.info(
        "Instantiated agent",
        agent_id=config.agent_id,
        instance_id=instance_id,
        redis_working_memory=redis_initialized,
    )
    return instance


async def _init_redis_working_memory(
    instance_id: str,
    agent_id: str,
) -> bool:
    """
    Initialize Redis working memory for agent session.

    Creates a Redis key with initial state and 24h TTL.
    The working memory stores:
    - kernel_state: Current kernel activation state
    - current_task: Currently executing task (if any)
    - last_activity: Timestamp of last activity
    - session_context: Running session context

    Args:
        instance_id: Unique instance identifier
        agent_id: Agent identifier

    Returns:
        True if Redis initialized, False if unavailable
    """
    try:
        from runtime.redis_client import get_redis_client

        redis = await get_redis_client()
        if not redis or not redis.is_available():
            logger.debug(
                "Redis unavailable for working memory",
                agent_id=agent_id,
            )
            return False

        # Redis key format: l9:agent:{agent_id}:working_memory
        key = f"l9:agent:{agent_id}:working_memory"

        # Initial working memory state
        initial_state = {
            "instance_id": instance_id,
            "agent_id": agent_id,
            "kernel_state": "LOADING",
            "status": "INITIALIZING",
            "current_task": None,
            "last_activity": datetime.utcnow().isoformat(),
            "session_context": {},
            "created_at": datetime.utcnow().isoformat(),
        }

        # Set with TTL (24 hours)
        await redis.set(
            key,
            json.dumps(initial_state),
            ex=WORKING_MEMORY_TTL_SECONDS,
        )

        logger.debug(
            "Redis working memory initialized",
            agent_id=agent_id,
            key=key,
            ttl_hours=24,
        )
        return True

    except Exception as e:
        logger.warning(
            "Failed to initialize Redis working memory, continuing",
            agent_id=agent_id,
            error=str(e),
        )
        return False
