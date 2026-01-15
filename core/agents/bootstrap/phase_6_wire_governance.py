"""
Phase 6: Wire Governance Gates

Harvested from: L9-Agent-Bootstrap-Architecture.md
Purpose: Create approval workflow, link tool execution to kernel enforcement, initialize execution guards.
"""

from __future__ import annotations

from typing import Dict, TYPE_CHECKING
from datetime import datetime

import structlog

if TYPE_CHECKING:
    from .phase_1_load_kernels import KernelParsed
    from .phase_2_instantiate import BootstrapInstanceData
    from memory.substrate_service import MemorySubstrateService

logger = structlog.get_logger(__name__)


async def wire_governance_gates(
    instance: "BootstrapInstanceData",
    substrate_service: "MemorySubstrateService",
    kernels: Dict[str, "KernelParsed"],
) -> None:
    """
    Wire governance gates: tool execution → kernel enforcement.

    This creates relationships between:
    - Destructive tools → Safety kernel (STRICT enforcement)
    - All tools → Execution kernel (standard governance)
    """
    # Lazy import to avoid test collection issues
    from memory.graph_client import get_neo4j_client

    neo4j_client = await get_neo4j_client()
    if not neo4j_client:
        logger.info("Neo4j not available, governance gates set in memory only")
        return

    try:
        async with neo4j_client.session() as session:
            # Get all tools bound to this agent
            result = await session.run(
                """
                MATCH (a:Agent {instance_id: $instance_id})-[:CAN_EXECUTE]->(t:Tool)
                RETURN t.tool_id as tool_id, t.name as tool_name, t.is_destructive as is_destructive
            """,
                {
                    "instance_id": instance.instance_id,
                },
            )

            tools_wired = 0
            async for record in result:
                tool_id = record["tool_id"]
                tool_name = record["tool_name"]
                is_destructive = record.get("is_destructive", False)

                # For destructive tools, link to Safety kernel
                if is_destructive:
                    await session.run(
                        """
                        MATCH (t:Tool {tool_id: $tool_id})
                        MATCH (k:Kernel) WHERE k.name CONTAINS 'safety' OR k.name CONTAINS 'Safety'
                        MERGE (t)-[rel:GUARDED_BY]->(k)
                        SET rel.enforcement_type = 'STRICT',
                            rel.wired_at = $wired_at
                    """,
                        {
                            "tool_id": tool_id,
                            "wired_at": datetime.utcnow().isoformat(),
                        },
                    )

                    logger.debug(
                        "Linked tool to Safety kernel",
                        tool=tool_name,
                        enforcement="STRICT",
                    )

                # All tools link to Execution kernel
                await session.run(
                    """
                    MATCH (t:Tool {tool_id: $tool_id})
                    MATCH (k:Kernel) WHERE k.name CONTAINS 'execution' OR k.name CONTAINS 'Execution'
                    MERGE (t)-[rel:GOVERNED_BY]->(k)
                    SET rel.wired_at = $wired_at
                """,
                    {
                        "tool_id": tool_id,
                        "wired_at": datetime.utcnow().isoformat(),
                    },
                )

                tools_wired += 1

            logger.info(
                "Governance gates wired",
                agent_id=instance.agent_id,
                tools_wired=tools_wired,
            )

    except Exception as e:
        logger.error("Failed to wire governance gates", error=str(e))
        # Non-fatal - governance can still work without Neo4j relationships
        logger.warning("Continuing without full governance wiring")
