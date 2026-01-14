"""
Agent Bootstrap Orchestrator - Master 7-Phase Controller

Harvested from: L9-Agent-Bootstrap-Architecture.md
Purpose: Orchestrate all 7 phases atomically. All succeed or all rollback.
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Optional

import structlog

from core.agents.agent_instance import AgentInstance
from memory.graph_client import get_neo4j_client

from . import (
    phase_0_validate,
    phase_1_load_kernels,
    phase_2_instantiate,
    phase_3_bind_kernels,
    phase_4_load_identity,
    phase_5_bind_tools,
    phase_6_wire_governance,
    phase_7_verify_and_lock,
)

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
        
        logger.info(
            "╔════════════════════════════════════════╗",
            extra={"markup": True},
        )
        logger.info(f"║  BOOTSTRAP: Agent {config.agent_id}")
        logger.info("╚════════════════════════════════════════╝")
        
        instance: Optional[AgentInstance] = None
        
        try:
            # Phase 0: Validate blueprint
            logger.info("Phase 0: Validating blueprint...")
            success, error = await phase_0_validate.validate_agent_blueprint(
                config, self.substrate
            )
            if not success:
                raise RuntimeError(f"Phase 0 failed: {error}")
            logger.info("✓ Phase 0 complete")
            
            # Phase 1: Load kernels
            logger.info("Phase 1: Loading & parsing kernels...")
            kernels = await phase_1_load_kernels.load_and_parse_kernels(kernel_dir)
            logger.info(f"✓ Phase 1 complete ({len(kernels)} kernels loaded)")
            
            # Phase 2: Instantiate agent
            logger.info("Phase 2: Instantiating agent...")
            instance = await phase_2_instantiate.instantiate_agent(config, self.substrate)
            logger.info(f"✓ Phase 2 complete (instance: {instance.instance_id[:8]}...)")
            
            # Phase 3: Bind kernels
            logger.info("Phase 3: Binding kernels...")
            await phase_3_bind_kernels.bind_kernels_to_agent(
                instance, kernels, self.substrate
            )
            logger.info("✓ Phase 3 complete")
            
            # Phase 4: Load identity
            logger.info("Phase 4: Loading identity persona...")
            await phase_4_load_identity.load_identity_persona(instance, self.substrate)
            logger.info("✓ Phase 4 complete")
            
            # Phase 5: Bind tools
            logger.info("Phase 5: Binding tools & capabilities...")
            await phase_5_bind_tools.bind_tools_and_capabilities(instance, self.substrate)
            logger.info("✓ Phase 5 complete")
            
            # Phase 6: Wire governance
            logger.info("Phase 6: Wiring governance gates...")
            await phase_6_wire_governance.wire_governance_gates(
                instance, self.substrate, kernels
            )
            logger.info("✓ Phase 6 complete")
            
            # Phase 7: Verify & lock
            logger.info("Phase 7: Verifying & locking...")
            signature = await phase_7_verify_and_lock.verify_and_lock(
                instance, self.substrate, kernels
            )
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
            logger.error("║  Rolling back...")
            logger.error("╚════════════════════════════════════════╝")
            
            # Rollback: Delete agent node (cascade deletes relationships)
            neo4j_client = await get_neo4j_client()
            if instance and neo4j_client:
                try:
                    async with neo4j_client.session() as session:
                        await session.run("""
                            MATCH (a:Agent {agent_id: $agent_id})
                            DETACH DELETE a
                        """, {
                            "agent_id": config.agent_id,
                        })
                    logger.info("Rollback complete: Agent removed from graph")
                except Exception as rollback_error:
                    logger.error("Rollback failed", error=str(rollback_error))
            
            raise RuntimeError(f"Agent bootstrap failed: {e}")


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

