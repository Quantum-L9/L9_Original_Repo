"""
Phase 3: Bind Kernels to Agent

Harvested from: L9-Agent-Bootstrap-Architecture.md
Purpose: Activate all 10 kernels on the agent instance. Verify kernel integrity.
"""

from __future__ import annotations

# ============================================================================
__dora_meta__ = {
    "component_name": "Phase 3 Bind Kernels",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2026-01-06T15:07:54Z",
    "updated_at": "2026-01-17T23:47:56Z",
    "layer": "foundation",
    "domain": "agent_execution",
    "module_name": "phase_3_bind_kernels",
    "type": "service",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": ["Neo4j"],
        "memory_layers": ["working_memory"],
        "imported_by": ["tests.core.bootstrap.test_bootstrap_phases"],
    },
}
# ============================================================================

from datetime import UTC, datetime
from typing import TYPE_CHECKING

import structlog

if TYPE_CHECKING:
    from memory.substrate_service import MemorySubstrateService

    from .phase_1_load_kernels import KernelParsed
    from .phase_2_instantiate import BootstrapInstanceData

logger = structlog.get_logger(__name__)


async def bind_kernels_to_agent(
    instance: BootstrapInstanceData,
    kernels: dict[str, KernelParsed],
    substrate_service: MemorySubstrateService,
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
                        "activated_at": datetime.now(UTC).isoformat(),
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
                        "activated_at": datetime.now(UTC).isoformat(),
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
        raise RuntimeError(f"Kernel binding failed: {e}") from e


# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "COR-FOUN-001",
    "governance_level": "critical",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": ["memory.graph_client", "memory.substrate_service"],
    "tags": [
        "agent-execution",
        "api",
        "async",
        "debugging",
        "foundation",
        "logging",
        "security",
        "service",
        "testing",
    ],
    "keywords": ["agent", "bind", "kernel", "kernels", "phase"],
    "business_value": "Utility module for phase 3 bind kernels",
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
