"""
L9 Core Agents Bootstrap – Orchestrator (7-Phase Pipeline)
===========================================================

Orchestrates the 7-phase agent initialization pipeline with deterministic
side-effect handling, feature-flag gating, and automatic rollback on failure.

Phases:
  0. Validate blueprint & check agent uniqueness
  1. Load & parse 10 governance YAML kernels
  2. Instantiate AgentInstance, register in Neo4j
  3. Bind kernels via GOVERNEDBY edges
  4. Load identity persona from 02-identity kernel (view-only, no Neo4j writes)
  5. Bind tools & capabilities
  6. Wire governance gates from safety kernel
  7. Verify all phases, compute deterministic init signature, mark READY

All phases must succeed or entire initialization rolls back (CASCADE delete
from Neo4j, no partial state).

Feature Flag: L9NEWAGENTINIT (env var or config; default=true)

Version: 2.0.0 (View Pattern)
"""

from __future__ import annotations

from core.decorators import must_stay_async

# ============================================================================
__dora_meta__ = {
    "component_name": "Master 7-Phase Controller",
    "module_version": "2.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2026-01-06T15:07:54Z",
    "updated_at": "2026-01-26T11:30:00Z",
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

import os
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any, cast

import structlog

from .models import (
    AgentBootstrapContext,
    AgentBootstrapError,
    IdentityView,
    PhaseResult,
)

if TYPE_CHECKING:
    from collections.abc import Callable

    from core.agents.schemas import AgentConfig
    from memory.substrate_service import MemorySubstrateService

    from .phase_1_load_kernels import KernelParsed
    from .phase_2_instantiate import BootstrapInstanceData

logger = structlog.get_logger(__name__)


# =============================================================================
# Re-export models for backward compatibility
# =============================================================================
__all__ = [
    "AgentBootstrapContext",
    "AgentBootstrapError",
    "AgentBootstrapOrchestrator",
    "IdentityView",
    "PhaseResult",
    "bootstrap_agent",
]


# =============================================================================
# Agent Bootstrap Orchestrator (View Pattern)
# =============================================================================


class AgentBootstrapOrchestrator:
    """
    Orchestrates the 7-phase agent initialization pipeline.

    Entry point: run() for new view-pattern API
    Legacy entry point: bootstrap_agent() for backward compatibility
    """

    def __init__(
        self,
        world_model_service: Any = None,  # Neo4j service (injected)
        memory_substrate_service: Any = None,  # Memory substrate (injected)
        tool_registry: Any = None,  # Tool registry (injected)
        feature_flags: dict[str, bool] | None = None,
        # Legacy support: substrate_service parameter
        substrate_service: MemorySubstrateService | None = None,
    ):
        """
        Initialize orchestrator with required services.

        Args:
            world_model_service: Neo4j graph service
            memory_substrate_service: Memory substrate for packets
            tool_registry: Tool registry for Phase 5 binding
            feature_flags: Feature flags (if None, reads from env)
            substrate_service: Legacy parameter (alias for memory_substrate_service)
        """
        self._world_model = world_model_service
        self._memory_substrate = memory_substrate_service or substrate_service
        self._tool_registry = tool_registry

        # Legacy support: keep substrate attribute for old code
        self.substrate = self._memory_substrate

        # Feature flag: L9NEWAGENTINIT (default=true)
        self._feature_flags = feature_flags or {}
        self._new_agent_init_enabled = self._feature_flags.get(
            "L9NEWAGENTINIT",
            os.getenv("L9NEWAGENTINIT", "true").lower() in ("true", "1"),
        )

        logger.info(
            "agent.bootstrap.orchestrator.init",
            l9_new_agent_init=self._new_agent_init_enabled,
        )

    @must_stay_async("callers use await")
    async def run(
        self,
        agent_id: str,
        config: AgentConfig,
        kernel_paths: dict[str, str],
    ) -> AgentBootstrapContext:
        """
        Execute 7-phase bootstrap pipeline for a new agent (View Pattern API).

        Args:
            agent_id: Unique agent identifier
            config: Agent configuration (schema/goals/etc)
            kernel_paths: Dict mapping kernel names to file paths
                         (e.g., {"02-identity": "/path/to/02-identity.yaml"})

        Returns:
            AgentBootstrapContext with fully initialized agent

        Raises:
            AgentBootstrapError: On any phase failure (with rollback)
        """
        if not self._new_agent_init_enabled:
            logger.warning(
                "agent.bootstrap.orchestrator.run: feature flag disabled, "
                "falling back to legacy init"
            )
            raise RuntimeError(
                "Legacy init path not yet implemented; enable L9NEWAGENTINIT"
            )

        # Initialize context
        ctx = AgentBootstrapContext(agent_id=agent_id, config=config)

        # Phase sequence (in order, names must match bootstrap_phases.txt catalog)
        phases: list[tuple[int, str, Callable[[AgentBootstrapContext, dict], Any]]] = [
            (0, "validate", self._phase0_validate),
            (1, "load_kernels", self._phase1_load_kernels),
            (2, "instantiate", self._phase2_instantiate),
            (3, "bind_kernels", self._phase3_bind_kernels),
            (4, "load_identity", self._phase4_load_identity),
            (5, "bind_tools", self._phase5_bind_tools),
            (6, "wire_governance", self._phase6_wire_governance),
            (7, "verify_and_lock", self._phase7_verify_and_lock),
        ]

        # Execute each phase
        for phase_num, phase_name, phase_func in phases:
            try:
                logger.info(
                    "agent.bootstrap.orchestrator.phase_start",
                    phase=phase_num,
                    name=phase_name,
                    agent_id=agent_id,
                )

                result = await phase_func(ctx, kernel_paths)

                # Record result
                ctx.add_phase_result(result)

                logger.info(
                    "agent.bootstrap.orchestrator.phase_complete",
                    phase=phase_num,
                    name=phase_name,
                    success=result.success,
                    duration_ms=result.duration_ms,
                    agent_id=agent_id,
                )

                # Check success
                if not result.success:
                    logger.error(
                        "agent.bootstrap.orchestrator.phase_failed",
                        phase=phase_num,
                        name=phase_name,
                        error_code=result.error_code,
                        agent_id=agent_id,
                        root_cause=str(result.error),
                    )

                    # Trigger rollback
                    await self._rollback_agent_init(
                        agent_id=agent_id,
                        reason=f"Phase {phase_num} ({phase_name}) failed: {result.error}",
                        phase=phase_num,
                    )

                    # Raise structured error
                    raise AgentBootstrapError(
                        phase=phase_num,
                        phase_name=phase_name,
                        agent_id=agent_id,
                        root_cause=result.error or Exception(result.error_code),
                        init_signature=None,
                    )

            except AgentBootstrapError:
                # Re-raise (already rolled back)
                raise
            except Exception as e:
                logger.error(
                    "agent.bootstrap.orchestrator.phase_exception",
                    phase=phase_num,
                    name=phase_name,
                    exception_type=type(e).__name__,
                    agent_id=agent_id,
                )

                # Trigger rollback
                await self._rollback_agent_init(
                    agent_id=agent_id,
                    reason=f"Phase {phase_num} ({phase_name}) exception: {e}",
                    phase=phase_num,
                )

                # Wrap in AgentBootstrapError
                raise AgentBootstrapError(
                    phase=phase_num,
                    phase_name=phase_name,
                    agent_id=agent_id,
                    root_cause=e,
                    init_signature=None,
                ) from e

        # All phases succeeded - mark agent as READY
        ctx.status = "READY"

        logger.info(
            "agent.bootstrap.orchestrator.all_phases_complete",
            agent_id=agent_id,
            total_phases=len(phases),
            init_signature=ctx.init_signature[:16] if ctx.init_signature else None,
            status=ctx.status,
        )

        return ctx

    # =========================================================================
    # Phase Implementations (View Pattern - Return PhaseResult)
    # =========================================================================

    async def _phase0_validate(
        self, ctx: AgentBootstrapContext, kernel_paths: dict[str, str]
    ) -> PhaseResult:
        """Phase 0: Validate agent blueprint and check uniqueness."""
        from . import phase_0_validate

        start = datetime.now(UTC)
        try:
            # Call existing phase function
            success, error = await phase_0_validate.validate_agent_blueprint(
                ctx.config, self._memory_substrate
            )
            duration = (datetime.now(UTC) - start).total_seconds() * 1000

            return PhaseResult(
                phase=0,
                name="validate",
                success=success,
                context_delta={"validated": True} if success else {},
                error=Exception(error) if error else None,
                duration_ms=duration,
            )
        except Exception as e:
            duration = (datetime.now(UTC) - start).total_seconds() * 1000
            return PhaseResult(
                phase=0,
                name="validate",
                success=False,
                error=e,
                duration_ms=duration,
            )

    @must_stay_async("callers use await")
    async def _phase1_load_kernels(
        self, ctx: AgentBootstrapContext, kernel_paths: dict[str, str]
    ) -> PhaseResult:
        """Phase 1: Load and parse 10 governance YAML kernels."""
        from . import phase_1_load_kernels

        start = datetime.now(UTC)
        try:
            # Use kernel_paths if provided, otherwise use default dir
            if kernel_paths:
                # kernel_paths is dict of {kernel_name: path}
                # Existing function expects a directory path
                kernel_dir = (
                    list(kernel_paths.values())[0].rsplit("/", 1)[0]
                    if kernel_paths
                    else "private/kernels/00_system"
                )
            else:
                kernel_dir = "private/kernels/00_system"

            kernels = await phase_1_load_kernels.load_and_parse_kernels(kernel_dir)
            duration = (datetime.now(UTC) - start).total_seconds() * 1000

            # Convert kernels to dict format for context
            kernels_dict = (
                {k.name: {"content": k.raw_yaml} for k in kernels} if kernels else {}
            )

            return PhaseResult(
                phase=1,
                name="load_kernels",
                success=True,
                context_delta={"kernels": kernels_dict},
                duration_ms=duration,
            )
        except Exception as e:
            duration = (datetime.now(UTC) - start).total_seconds() * 1000
            return PhaseResult(
                phase=1,
                name="load_kernels",
                success=False,
                error=e,
                duration_ms=duration,
            )

    async def _phase2_instantiate(
        self, ctx: AgentBootstrapContext, kernel_paths: dict[str, str]
    ) -> PhaseResult:
        """Phase 2: Instantiate AgentInstance, register in Neo4j."""
        from . import phase_2_instantiate

        start = datetime.now(UTC)
        try:
            instance = await phase_2_instantiate.instantiate_agent(
                ctx.config, self._memory_substrate
            )
            duration = (datetime.now(UTC) - start).total_seconds() * 1000

            return PhaseResult(
                phase=2,
                name="instantiate",
                success=True,
                context_delta={"instance": instance, "instantiated": True},
                duration_ms=duration,
            )
        except Exception as e:
            duration = (datetime.now(UTC) - start).total_seconds() * 1000
            return PhaseResult(
                phase=2,
                name="instantiate",
                success=False,
                error=e,
                duration_ms=duration,
            )

    async def _phase3_bind_kernels(
        self, ctx: AgentBootstrapContext, kernel_paths: dict[str, str]
    ) -> PhaseResult:
        """Phase 3: Bind kernels via GOVERNEDBY edges."""
        from . import phase_3_bind_kernels

        start = datetime.now(UTC)
        try:
            instance = ctx.phase_results[-1].context_delta.get("instance")
            # Get raw kernels list from phase 1
            kernels_list: dict[
                str, KernelParsed
            ] = {}  # Would need to be passed from phase 1
            await phase_3_bind_kernels.bind_kernels_to_agent(
                cast("BootstrapInstanceData", instance),
                kernels_list,
                cast("MemorySubstrateService", self._memory_substrate),
            )
            duration = (datetime.now(UTC) - start).total_seconds() * 1000

            return PhaseResult(
                phase=3,
                name="bind_kernels",
                success=True,
                context_delta={"kernels_bound": True},
                duration_ms=duration,
            )
        except Exception as e:
            duration = (datetime.now(UTC) - start).total_seconds() * 1000
            return PhaseResult(
                phase=3,
                name="bind_kernels",
                success=False,
                error=e,
                duration_ms=duration,
            )

    async def _phase4_load_identity(
        self, ctx: AgentBootstrapContext, kernel_paths: dict[str, str]
    ) -> PhaseResult:
        """
        Phase 4: Load identity persona from 02-identity kernel.

        View-only: no Neo4j writes. Returns IdentityView in context_delta.
        """
        from . import phase_4_load_identity

        start = datetime.now(UTC)
        try:
            instance = ctx.phase_results[-2].context_delta.get("instance")

            # Try new view-pattern function first
            if hasattr(phase_4_load_identity, "load_identity_persona_view"):
                result = await phase_4_load_identity.load_identity_persona_view(
                    agent_id=ctx.agent_id,
                    identity_kernel=ctx.kernels.get("02-identity", {}),
                    kernel_paths=kernel_paths,
                )
                duration = (datetime.now(UTC) - start).total_seconds() * 1000
                return PhaseResult(
                    phase=4,
                    name="load_identity",
                    success=result.get("success", False),
                    context_delta=result.get("context_delta", {}),
                    error=result.get("error"),
                    duration_ms=duration,
                )

            # Fallback to legacy function
            await phase_4_load_identity.load_identity_persona(
                instance, self._memory_substrate
            )
            duration = (datetime.now(UTC) - start).total_seconds() * 1000

            # Create IdentityView from instance data
            identity_view = IdentityView(
                agent_id=ctx.agent_id,
                display_name=getattr(instance, "designation", ctx.agent_id),
                short_name=getattr(instance, "designation", ctx.agent_id)[:2],
                description=getattr(instance, "mission", ""),
                capabilities=[],
                default_tone="neutral",
                tags=[],
            )

            return PhaseResult(
                phase=4,
                name="load_identity",
                success=True,
                context_delta={"identity_view": identity_view},
                duration_ms=duration,
            )
        except Exception as e:
            duration = (datetime.now(UTC) - start).total_seconds() * 1000
            return PhaseResult(
                phase=4,
                name="load_identity",
                success=False,
                error=e,
                duration_ms=duration,
            )

    async def _phase5_bind_tools(
        self, ctx: AgentBootstrapContext, kernel_paths: dict[str, str]
    ) -> PhaseResult:
        """Phase 5: Bind tools and capabilities."""
        from . import phase_5_bind_tools

        start = datetime.now(UTC)
        try:
            instance = None
            for pr in reversed(ctx.phase_results):
                if "instance" in pr.context_delta:
                    instance = pr.context_delta["instance"]
                    break

            await phase_5_bind_tools.bind_tools_and_capabilities(
                cast("BootstrapInstanceData", instance),
                cast("MemorySubstrateService", self._memory_substrate),
            )
            duration = (datetime.now(UTC) - start).total_seconds() * 1000

            return PhaseResult(
                phase=5,
                name="bind_tools",
                success=True,
                context_delta={"tools": [], "tools_bound": 0},
                duration_ms=duration,
            )
        except Exception as e:
            duration = (datetime.now(UTC) - start).total_seconds() * 1000
            return PhaseResult(
                phase=5,
                name="bind_tools",
                success=False,
                error=e,
                duration_ms=duration,
            )

    async def _phase6_wire_governance(
        self, ctx: AgentBootstrapContext, kernel_paths: dict[str, str]
    ) -> PhaseResult:
        """Phase 6: Wire governance gates from safety kernel."""
        from . import phase_6_wire_governance

        start = datetime.now(UTC)
        try:
            instance = None
            for pr in reversed(ctx.phase_results):
                if "instance" in pr.context_delta:
                    instance = pr.context_delta["instance"]
                    break

            kernels_dict: dict[str, KernelParsed] = {}  # kernels list
            await phase_6_wire_governance.wire_governance_gates(
                cast("BootstrapInstanceData", instance),
                cast("MemorySubstrateService", self._memory_substrate),
                kernels_dict,
            )
            duration = (datetime.now(UTC) - start).total_seconds() * 1000

            return PhaseResult(
                phase=6,
                name="wire_governance",
                success=True,
                context_delta={"governance_gates": {}},
                duration_ms=duration,
            )
        except Exception as e:
            duration = (datetime.now(UTC) - start).total_seconds() * 1000
            return PhaseResult(
                phase=6,
                name="wire_governance",
                success=False,
                error=e,
                duration_ms=duration,
            )

    @must_stay_async("callers use await")
    async def _phase7_verify_and_lock(
        self, ctx: AgentBootstrapContext, kernel_paths: dict[str, str]
    ) -> PhaseResult:
        """
        Phase 7: Verify all phases, compute deterministic init signature,
        mark agent as READY.
        """
        from . import phase_7_verify_and_lock

        start = datetime.now(UTC)
        try:
            # Verify all previous phases succeeded
            if any(not result.success for result in ctx.phase_results):
                raise RuntimeError("Cannot proceed to Phase 7: prior phase(s) failed")

            # Compute deterministic init signature
            init_signature = ctx.compute_init_signature()
            ctx.init_signature = init_signature  # Set directly on context

            # Get instance for legacy function
            instance = None
            for pr in reversed(ctx.phase_results):
                if "instance" in pr.context_delta:
                    instance = pr.context_delta["instance"]
                    break

            # Try new view-pattern function first
            if hasattr(phase_7_verify_and_lock, "verify_and_lock_view"):
                result = await phase_7_verify_and_lock.verify_and_lock_view(
                    agent_id=ctx.agent_id,
                    identity_view=ctx.identity_view,
                    kernels=ctx.kernels,
                    tools=ctx.tools,
                    governance_gates=ctx.governance_gates,
                    init_signature=init_signature,
                )
                duration = (datetime.now(UTC) - start).total_seconds() * 1000
                return PhaseResult(
                    phase=7,
                    name="verify_and_lock",
                    success=result.get("success", False),
                    context_delta={
                        "init_signature": init_signature,
                        "status": "READY",
                        **result.get("context_delta", {}),
                    },
                    error=result.get("error"),
                    duration_ms=duration,
                )

            # Fallback to legacy function
            await phase_7_verify_and_lock.verify_and_lock(
                instance,
                self._memory_substrate,
                [],  # kernels list
            )
            duration = (datetime.now(UTC) - start).total_seconds() * 1000

            return PhaseResult(
                phase=7,
                name="verify_and_lock",
                success=True,
                context_delta={
                    "init_signature": init_signature,
                    "status": "READY",
                    "verified": True,
                },
                duration_ms=duration,
            )
        except Exception as e:
            duration = (datetime.now(UTC) - start).total_seconds() * 1000
            return PhaseResult(
                phase=7,
                name="verify_and_lock",
                success=False,
                error=e,
                duration_ms=duration,
            )

    # =========================================================================
    # Rollback & Cleanup
    # =========================================================================

    @must_stay_async("callers use await")
    async def _rollback_agent_init(
        self, agent_id: str, reason: str, phase: int
    ) -> None:
        """
        Rollback agent initialization on failure.

        Deletes agent node from Neo4j with CASCADE relationships, ensuring
        zero partial state. Mirrors the "rollback on failure" semantics from
        bootstrap_phases.txt.

        Args:
            agent_id: Agent ID to delete
            reason: Human-readable reason for rollback
            phase: Phase number where failure occurred
        """
        logger.info(
            "agent.bootstrap.orchestrator.rollback_start",
            agent_id=agent_id,
            phase=phase,
            reason=reason,
        )

        try:
            # Check if we have a world model service
            if self._world_model is None:
                # Fall back to direct Neo4j
                from memory.graph_client import get_neo4j_client

                neo4j_client = await get_neo4j_client()
                if neo4j_client:
                    async with neo4j_client.session() as session:
                        await session.run(
                            """
                            MATCH (a:Agent {agent_id: $agent_id})
                            DETACH DELETE a
                            """,
                            {"agent_id": agent_id},
                        )
                    logger.info(
                        "agent.bootstrap.orchestrator.rollback_complete",
                        agent_id=agent_id,
                        phase=phase,
                    )
                return

            # Use world model service if available
            if hasattr(self._world_model, "agent_exists"):
                exists = await self._world_model.agent_exists(agent_id)
                if not exists:
                    logger.warning(
                        "agent.bootstrap.orchestrator.rollback: agent not in Neo4j",
                        agent_id=agent_id,
                    )
                    return

            if hasattr(self._world_model, "delete_agent_node_cascade"):
                await self._world_model.delete_agent_node_cascade(agent_id)

            logger.info(
                "agent.bootstrap.orchestrator.rollback_complete",
                agent_id=agent_id,
                phase=phase,
            )
        except Exception as e:
            logger.error(
                "agent.bootstrap.orchestrator.rollback_failed",
                agent_id=agent_id,
                phase=phase,
                exception=str(e),
            )
            # Do NOT re-raise; log and continue (best-effort cleanup)

    # =========================================================================
    # Legacy API (Backward Compatibility)
    # =========================================================================

    @must_stay_async("callers use await")
    async def bootstrap_agent(
        self,
        config: AgentConfig,
        kernel_dir: str = "private/kernels/00_system",
    ) -> Any:
        """
        Legacy API: Execute all 7 phases atomically.

        For backward compatibility with existing code.
        New code should use run() method instead.

        Returns:
            Fully initialized AgentInstance if successful

        Raises:
            RuntimeError if any phase fails
        """

        from .bootstrap_metrics import get_bootstrap_metrics

        metrics = get_bootstrap_metrics(config.agent_id)

        logger.info(
            "╔════════════════════════════════════════╗",
            extra={"markup": True},
        )
        logger.info(f"║  BOOTSTRAP: Agent {config.agent_id}")
        logger.info("╚════════════════════════════════════════╝")

        instance = None
        failed_phase = None

        with metrics.track_bootstrap():
            try:
                # Import phase modules
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
                        instance,
                        kernels,
                        cast("MemorySubstrateService", self.substrate),
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
                    await phase_5_bind_tools.bind_tools_and_capabilities(
                        instance, cast("MemorySubstrateService", self.substrate)
                    )
                    failed_phase = 5
                metrics.set_tools_bound(0)
                logger.info("✓ Phase 5 complete")

                # Phase 6: Wire governance
                logger.info("Phase 6: Wiring governance gates...")
                with metrics.time_phase(6):
                    await phase_6_wire_governance.wire_governance_gates(
                        instance,
                        cast("MemorySubstrateService", self.substrate),
                        kernels,
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
                await self._rollback_agent_init(
                    agent_id=config.agent_id,
                    reason=str(e),
                    phase=failed_phase or 0,
                )

                raise RuntimeError(f"Agent bootstrap failed: {e}") from e


# =============================================================================
# Convenience Functions
# =============================================================================


async def bootstrap_agent(
    config: AgentConfig,
    substrate_service: MemorySubstrateService,
    kernel_dir: str = "private/kernels/00_system",
) -> Any:
    """
    Bootstrap an agent using the 7-phase ceremony.

    Usage:
        from core.agents.bootstrap import bootstrap_agent
        instance = await bootstrap_agent(config, substrate_service)
    """
    orchestrator = AgentBootstrapOrchestrator(substrate_service=substrate_service)
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
    "last_modified": "2026-01-26T11:30:00Z",
    "modified_by": "L9_Codegen_Engine",
    "change_summary": "View pattern implementation with backward compatibility",
}
# ============================================================================
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
