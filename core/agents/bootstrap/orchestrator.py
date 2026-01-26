"""
Agent Bootstrap Orchestrator - Master 7-Phase Controller

Harvested from: L9-Agent-Bootstrap-Architecture.md
Purpose: Orchestrate all 7 phases atomically. All succeed or all rollback.

Metrics:
- l9_bootstrap_phase_duration_seconds (histogram per phase)
- l9_bootstrap_phase_errors_total (counter)
- l9_bootstrap_rollbacks_total (counter)
- l9_bootstrap_init_signatures_generated_total (counter)
"""

from __future__ import annotations

# ============================================================================
__dora_meta__ = {
    "component_name": "Master 7-Phase Controller",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2026-01-06T15:07:54Z",
    "updated_at": "2026-01-17T23:47:56Z",
    "layer": "foundation",
    "domain": "agent_execution",
    "module_name": "orchestrator",
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

from typing import TYPE_CHECKING, Optional

import structlog

from core.agents.agent_instance import AgentInstance

from . import (phase_0_validate, phase_1_load_kernels, phase_2_instantiate,
               phase_3_bind_kernels, phase_4_load_identity, phase_5_bind_tools,
               phase_6_wire_governance, phase_7_verify_and_lock)
from .bootstrap_metrics import get_bootstrap_metrics

if TYPE_CHECKING:
    from core.agents.schemas import AgentConfig
    from memory.substrate_service import MemorySubstrateService

logger = structlog.get_logger(__name__)


class AgentBootstrapOrchestrator:
    """
    Orchestrates 7-phase atomic agent initialization.
    All phases must succeed or entire initialization rolls back.
    """

    def __init__(self, substrate_service: "MemorySubstrateService"):
        self.substrate = substrate_service

    async def bootstrap_agent(
        self,
        config: "AgentConfig",
        kernel_dir: str = "private/kernels/00_system",
    ) -> AgentInstance:
        """
        Execute all 7 phases atomically.

        Returns:
            Fully initialized AgentInstance if successful

        Raises:
            RuntimeError if any phase fails
        """
        metrics = get_bootstrap_metrics(config.agent_id)

        logger.info(
            "╔════════════════════════════════════════╗",
            extra={"markup": True},
        )
        logger.info(f"║  BOOTSTRAP: Agent {config.agent_id}")
        logger.info("╚════════════════════════════════════════╝")

        instance: Optional[AgentInstance] = None
        failed_phase: Optional[int] = None

        with metrics.track_bootstrap():
            try:
                # Phase 0: Validate blueprint
                logger.info("Phase 0: Validating blueprint...")
                with metrics.time_phase(0):
                    success, error = await phase_0_validate.validate_agent_blueprint(
                        config, self.substrate
                    )
                    if not success:
                        failed_phase = 0
                        raise RuntimeError(f"Phase 0 failed: {error}")
                logger.info("✓ Phase 0 complete")

                # Phase 1: Load kernels
                logger.info("Phase 1: Loading & parsing kernels...")
                with metrics.time_phase(1):
                    kernels = await phase_1_load_kernels.load_and_parse_kernels(
                        kernel_dir
                    )
                    failed_phase = 1
                metrics.set_kernels_bound(len(kernels))
                logger.info(f"✓ Phase 1 complete ({len(kernels)} kernels loaded)")

                # Phase 2: Instantiate agent
                logger.info("Phase 2: Instantiating agent...")
                with metrics.time_phase(2):
                    instance = await phase_2_instantiate.instantiate_agent(
                        config, self.substrate
                    )
                    failed_phase = 2
                logger.info(
                    f"✓ Phase 2 complete (instance: {instance.instance_id[:8]}...)"
                )

                # Phase 3: Bind kernels
                logger.info("Phase 3: Binding kernels...")
                with metrics.time_phase(3):
                    await phase_3_bind_kernels.bind_kernels_to_agent(
                        instance, kernels, self.substrate
                    )
                    failed_phase = 3
                logger.info("✓ Phase 3 complete")

                # Phase 4: Load identity
                logger.info("Phase 4: Loading identity persona...")
                with metrics.time_phase(4):
                    await phase_4_load_identity.load_identity_persona(
                        instance, self.substrate
                    )
                    failed_phase = 4
                logger.info("✓ Phase 4 complete")

                # Phase 5: Bind tools
                logger.info("Phase 5: Binding tools & capabilities...")
                with metrics.time_phase(5):
                    tool_count = await phase_5_bind_tools.bind_tools_and_capabilities(
                        instance, self.substrate
                    )
                    failed_phase = 5
                metrics.set_tools_bound(
                    tool_count if isinstance(tool_count, int) else 0
                )
                logger.info("✓ Phase 5 complete")

                # Phase 6: Wire governance
                logger.info("Phase 6: Wiring governance gates...")
                with metrics.time_phase(6):
                    await phase_6_wire_governance.wire_governance_gates(
                        instance, self.substrate, kernels
                    )
                    failed_phase = 6
                logger.info("✓ Phase 6 complete")

                # Phase 7: Verify & lock
                logger.info("Phase 7: Verifying & locking...")
                with metrics.time_phase(7):
                    signature = await phase_7_verify_and_lock.verify_and_lock(
                        instance, self.substrate, kernels
                    )
                    failed_phase = 7
                metrics.record_init_signature()
                logger.info(f"✓ Phase 7 complete (signature: {signature[:16]}...)")

                # All phases complete
                logger.info("╔════════════════════════════════════════╗")
                logger.info(f"║  SUCCESS: {config.agent_id} initialized")
                logger.info(f"║  Instance: {instance.instance_id[:12]}...")
                logger.info("║  Status: READY")
                logger.info("╚════════════════════════════════════════╝")

                return instance

            except Exception as e:
                logger.error("╔════════════════════════════════════════╗")
                logger.error(f"║  BOOTSTRAP FAILED: {str(e)[:30]}...")
                logger.error(f"║  Agent: {config.agent_id}")
                logger.error(f"║  Failed Phase: {failed_phase}")
                logger.error("║  Rolling back...")
                logger.error("╚════════════════════════════════════════╝")

                # Record rollback metric
                if failed_phase is not None:
                    metrics.record_rollback(failed_phase)

                # Rollback: Delete agent node (cascade deletes relationships)
                # Lazy import to avoid test collection issues
                from memory.graph_client import get_neo4j_client

                neo4j_client = await get_neo4j_client()
                if instance and neo4j_client:
                    try:
                        async with neo4j_client.session() as session:
                            await session.run(
                                """
                                MATCH (a:Agent {agent_id: $agent_id})
                                DETACH DELETE a
                            """,
                                {
                                    "agent_id": config.agent_id,
                                },
                            )
                        logger.info("Rollback complete: Agent removed from graph")
                    except Exception as rollback_error:
                        logger.error("Rollback failed", error=str(rollback_error))

                raise RuntimeError(f"Agent bootstrap failed: {e}") from rollback_error


# Convenience function for direct use
async def bootstrap_agent(
    config: "AgentConfig",
    substrate_service: "MemorySubstrateService",
    kernel_dir: str = "private/kernels/00_system",
) -> AgentInstance:
    """
    Bootstrap an agent using the 7-phase ceremony.

    Usage:
        from core.agents.bootstrap import bootstrap_agent
        instance = await bootstrap_agent(config, substrate_service)
    """
    orchestrator = AgentBootstrapOrchestrator(substrate_service)
    return await orchestrator.bootstrap_agent(config, kernel_dir)


# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "COR-FOUN-044",
    "governance_level": "critical",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [
        "core.agents.agent_instance",
        "core.agents.schemas",
        "memory.graph_client",
        "memory.substrate_service",
    ],
    "tags": [
        "agent-execution",
        "async",
        "foundation",
        "logging",
        "metrics",
        "orchestration",
        "service",
        "testing",
    ],
    "keywords": [
        "agent",
        "bootstrap",
        "controller",
        "counter",
        "master",
        "orchestrator",
        "phase",
    ],
    "business_value": "Implements AgentBootstrapOrchestrator for orchestrator functionality",
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
