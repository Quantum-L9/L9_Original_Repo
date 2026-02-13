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

from core.decorators import must_stay_async

# ============================================================================
__dora_meta__ = {
    "component_name": "Phase 2 Instantiate",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2026-01-06T15:07:54Z",
    "updated_at": "2026-01-17T23:47:56Z",
    "layer": "foundation",
    "domain": "agent_execution",
    "module_name": "phase_2_instantiate",
    "type": "dataclass",
    "status": "production",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": ["Neo4j", "Redis"],
        "memory_layers": ["working_memory"],
        "imported_by": [
            "tests.core.bootstrap.conftest",
            "tests.core.bootstrap.test_bootstrap_phases",
        ],
    },
}
# ============================================================================

import json
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import TYPE_CHECKING

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
    config: AgentConfig
    kernel_state: str = "LOADING"
    status: str = "INITIALIZING"
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    initialized_at: datetime | None = None
    initialization_signature: str | None = None
    designation: str | None = None
    role: str | None = None
    mission: str | None = None
    authority: str | None = None


@must_stay_async("callers use await")
async def instantiate_agent(
    config: AgentConfig,
    substrate_service: MemorySubstrateService,
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
        created_at=datetime.now(UTC),
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


@must_stay_async("callers use await")
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
            "last_activity": datetime.now(UTC).isoformat(),
            "session_context": {},
            "created_at": datetime.now(UTC).isoformat(),
        }

        # Set with TTL (24 hours)
        await redis.set(
            key,
            json.dumps(initial_state, default=str),
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


# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "COR-FOUN-042",
    "governance_level": "critical",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [
        "core.agents.schemas",
        "memory.graph_client",
        "memory.substrate_service",
        "runtime.redis_client",
    ],
    "tags": [
        "agent-execution",
        "api",
        "async",
        "auth",
        "dataclass",
        "debugging",
        "foundation",
        "logging",
        "serialization",
        "testing",
    ],
    "keywords": [
        "agent",
        "agentinstance",
        "bootstrap",
        "instance",
        "instantiate",
        "memory",
        "module",
        "phase",
    ],
    "business_value": "Implements BootstrapInstanceData for phase 2 instantiate functionality",
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
