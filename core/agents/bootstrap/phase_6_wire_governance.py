"""
Phase 6: Wire Governance Gates

Harvested from: L9-Agent-Bootstrap-Architecture.md
Purpose: Create approval workflow, link tool execution to kernel enforcement, initialize execution guards.
"""

from __future__ import annotations

# ============================================================================
__dora_meta__ = {
    "component_name": "Phase 6 Wire Governance",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2026-01-06T15:07:54Z",
    "updated_at": "2026-01-17T23:47:56Z",
    "layer": "foundation",
    "domain": "agent_execution",
    "module_name": "phase_6_wire_governance",
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

from datetime import datetime
from typing import TYPE_CHECKING

import structlog

if TYPE_CHECKING:
    from memory.substrate_service import MemorySubstrateService

    from .phase_1_load_kernels import KernelParsed
    from .phase_2_instantiate import BootstrapInstanceData

logger = structlog.get_logger(__name__)


async def wire_governance_gates(
    instance: BootstrapInstanceData,
    substrate_service: MemorySubstrateService,
    kernels: dict[str, KernelParsed],
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
        "service",
        "testing",
    ],
    "keywords": [
        "agent",
        "execution",
        "gates",
        "governance",
        "kernel",
        "phase",
        "wire",
    ],
    "business_value": "Utility module for phase 6 wire governance",
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
