"""
Phase 3: Bind Kernels to Agent

Harvested from: L9-Agent-Bootstrap-Architecture.md
Purpose: Activate all 10 kernels on the agent instance. Verify kernel integrity.
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


async def bind_kernels_to_agent(
    instance: "BootstrapInstanceData",
    kernels: Dict[str, "KernelParsed"],
    substrate_service: "MemorySubstrateService",
) -> None:
    """
    Activate all kernels on agent. Create agent→kernel relationships in Neo4j.
    """
    # Get Neo4j client from global singleton (lazy import to avoid test collection issues)
    from memory.graph_client import get_neo4j_client

    neo4j_client = await get_neo4j_client()
    if not neo4j_client:
        logger.warning("Neo4j not available, skipping kernel binding in graph")
        # Still mark kernels as bound in instance
        instance.kernel_state = "BOUND"
        return

    try:
        async with neo4j_client.session() as session:
            for kernel_name, kernel_parsed in kernels.items():
                # Create or merge kernel node
                await session.run(
                    """
                    MERGE (k:Kernel {name: $name})
                    SET k.version = $version,
                        k.hash = $hash,
                        k.activated_at = $activated_at
                """,
                    {
                        "name": kernel_name,
                        "version": kernel_parsed.version,
                        "hash": kernel_parsed.hash,
                        "activated_at": datetime.utcnow().isoformat(),
                    },
                )

                # Create relationship: Agent → Kernel
                await session.run(
                    """
                    MATCH (a:Agent {instance_id: $instance_id})
                    MATCH (k:Kernel {name: $kernel_name})
                    MERGE (a)-[rel:GOVERNED_BY]->(k)
                    SET rel.activated_at = $activated_at
                """,
                    {
                        "instance_id": instance.instance_id,
                        "kernel_name": kernel_name,
                        "activated_at": datetime.utcnow().isoformat(),
                    },
                )

                logger.debug(
                    "Bound kernel to agent",
                    kernel=kernel_name,
                    agent_id=instance.agent_id,
                )

        # Verify all kernels bound
        async with neo4j_client.session() as session:
            result = await session.run(
                """
                MATCH (a:Agent {instance_id: $instance_id})-[:GOVERNED_BY]->(k:Kernel)
                RETURN count(k) as kernel_count
            """,
                {
                    "instance_id": instance.instance_id,
                },
            )

            record = await result.single()
            kernel_count = record["kernel_count"] if record else 0

            if kernel_count != len(kernels):
                logger.warning(
                    "Kernel count mismatch",
                    expected=len(kernels),
                    actual=kernel_count,
                )

            logger.info(
                "Verified kernels bound to agent",
                agent_id=instance.agent_id,
                kernel_count=kernel_count,
            )

    except Exception as e:
        logger.error("Failed to bind kernels", error=str(e))
        raise RuntimeError(f"Kernel binding failed: {e}")
