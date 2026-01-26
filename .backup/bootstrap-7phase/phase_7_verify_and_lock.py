"""
Phase 7: Verify & Lock

Harvested from: L9-Agent-Bootstrap-Architecture.md
Purpose: Smoke test all systems, sign initialization hash, write audit trail, flag agent READY.
"""

from __future__ import annotations

# ============================================================================
__dora_meta__ = {
    "component_name": "Phase 7 Verify And Lock",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2026-01-06T15:07:54Z",
    "updated_at": "2026-01-17T23:47:56Z",
    "layer": "foundation",
    "domain": "agent_execution",
    "module_name": "phase_7_verify_and_lock",
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

import hashlib
from datetime import datetime
from typing import TYPE_CHECKING

import structlog

if TYPE_CHECKING:
    from memory.substrate_service import MemorySubstrateService

    from .phase_1_load_kernels import KernelParsed
    from .phase_2_instantiate import BootstrapInstanceData

logger = structlog.get_logger(__name__)


async def verify_and_lock(
    instance: BootstrapInstanceData,
    substrate_service: MemorySubstrateService,
    kernels: dict[str, KernelParsed],
) -> str:
    """
    Verify initialization, sign, and lock agent.

    Returns:
        Initialization signature (hex string)
    """
    verification_results = []

    # Check 1: Kernels loaded
    if len(kernels) > 0:
        verification_results.append(("kernels_loaded", True, len(kernels)))
        logger.info("✓ Kernels verified", count=len(kernels))
    else:
        logger.warning("No kernels loaded")
        verification_results.append(("kernels_loaded", False, 0))

    # Check 2: Identity loaded
    if instance.designation:
        verification_results.append(("identity_loaded", True, instance.designation))
        logger.info("✓ Identity verified", designation=instance.designation)
    else:
        logger.warning("Identity not loaded")
        verification_results.append(("identity_loaded", False, None))

    # Check 3: Neo4j verification (if available - lazy import to avoid test collection issues)
    from memory.graph_client import get_neo4j_client

    neo4j_client = await get_neo4j_client()
    if neo4j_client:
        try:
            async with neo4j_client.session() as session:
                # Check kernels in graph
                kernel_check = await session.run(
                    """
                    MATCH (a:Agent {instance_id: $instance_id})-[:GOVERNED_BY]->(k:Kernel)
                    RETURN count(k) as kernel_count
                """,
                    {
                        "instance_id": instance.instance_id,
                    },
                )

                record = await kernel_check.single()
                graph_kernel_count = record["kernel_count"] if record else 0
                verification_results.append(("graph_kernels", True, graph_kernel_count))

                # Check tools in graph
                tools_check = await session.run(
                    """
                    MATCH (a:Agent {instance_id: $instance_id})-[:CAN_EXECUTE]->(t:Tool)
                    RETURN count(t) as tool_count
                """,
                    {
                        "instance_id": instance.instance_id,
                    },
                )

                record = await tools_check.single()
                tool_count = record["tool_count"] if record else 0
                verification_results.append(("graph_tools", True, tool_count))
                logger.info("✓ Tools verified", count=tool_count)

        except Exception as e:
            logger.warning("Graph verification failed", error=str(e))
            verification_results.append(("graph_check", False, str(e)))

    # Create initialization signature
    signature_data = (
        f"{instance.instance_id}|"
        f"{instance.agent_id}|"
        f"{datetime.utcnow().isoformat()}|"
        f"{len(kernels)}kernels|"
        f"{instance.designation or 'unknown'}"
    )
    signature = hashlib.sha256(signature_data.encode()).hexdigest()

    # Update instance
    instance.initialization_signature = signature
    instance.initialized_at = datetime.utcnow()
    instance.kernel_state = "ACTIVE"
    instance.status = "READY"

    # Write audit trail
    audit_entry = {
        "event": "agent_initialized",
        "agent_id": instance.agent_id,
        "instance_id": instance.instance_id,
        "kernel_count": len(kernels),
        "initialization_signature": signature,
        "verification_results": verification_results,
        "timestamp": datetime.utcnow().isoformat(),
        "status": "READY",
    }

    # Store audit in memory substrate if available
    if hasattr(substrate_service, "write_packet"):
        try:
            from config.rls_config import get_rls_config
            from core.schemas import PacketEnvelopeIn
            from memory.governance_gate import (
                build_governance_context,
                governance_context,
            )

            # GMP-94: Bootstrap requires governance context for write_packet
            rls_config = get_rls_config()
            ctx = build_governance_context(
                caller_id="L",
                role="system",
                scope="developer",
                project_id="l9-bootstrap",
                allowed_scopes=["developer", "global"],
                tenant_id=rls_config.tenant_uuid,
                org_id=rls_config.org_uuid,
                user_id=rls_config.user_uuid,
                creator="bootstrap",
                source="phase_7_verify_and_lock",
            )

            packet = PacketEnvelopeIn(
                packet_type="memory_write",
                payload={
                    "chunk_type": "audit",
                    "event": audit_entry["event"],
                    "initialization_signature": signature,
                    "kernel_count": len(kernels),
                    "timestamp": audit_entry["timestamp"],
                    "agent_id": instance.agent_id,
                },
                metadata={"agent": instance.agent_id, "schema_version": "1.0.0"},
            )
            async with governance_context(ctx):
                await substrate_service.write_packet(packet)
            logger.info("✓ Audit trail written")
        except ImportError:
            logger.debug("PacketEnvelopeIn not available, audit logged only")

    # Update agent state in Neo4j
    if neo4j_client:
        try:
            async with neo4j_client.session() as session:
                await session.run(
                    """
                    MATCH (a:Agent {instance_id: $instance_id})
                    SET a.kernel_state = 'ACTIVE',
                        a.initialization_signature = $signature,
                        a.initialized_at = $initialized_at,
                        a.status = 'READY'
                """,
                    {
                        "instance_id": instance.instance_id,
                        "signature": signature,
                        "initialized_at": datetime.utcnow().isoformat(),
                    },
                )
        except Exception as e:
            logger.warning("Failed to update Neo4j state", error=str(e))

    logger.info(
        "✓ Agent initialized and READY",
        agent_id=instance.agent_id,
        signature=signature[:16] + "...",
    )

    return signature


# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "COR-FOUN-001",
    "governance_level": "critical",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [
        "core.schemas",
        "memory.governance_gate",
        "memory.graph_client",
        "memory.substrate_service",
    ],
    "tags": [
        "agent-execution",
        "api",
        "async",
        "audit-tool",
        "debugging",
        "event-driven",
        "foundation",
        "logging",
        "security",
        "service",
    ],
    "keywords": ["agent", "audit", "lock", "phase", "verify"],
    "business_value": "Utility module for phase 7 verify and lock",
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
