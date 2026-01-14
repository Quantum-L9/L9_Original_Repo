"""
L9 Orchestration - Unified Controller
=====================================

GOD-MODE top-level controller for the L9 system.

This is the primary façade for L9, coordinating:
- IR Engine (semantic compiler, validator, generator, planner)
- World Model Runtime
- Simulation Engine (via SimulationRouter)
- Memory Substrate (PacketEnvelope API)
- Collaborative cells (architect/coder/reviewer)

Architecture:
┌─────────────────────────────────────────────────────────────────────────┐
│                       UnifiedController                                  │
│                      (GOD-MODE Façade)                                  │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                 async handle_request(text, context)              │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                              │                                          │
│  ┌────────────────┬──────────┴──────────┬─────────────────────────┐    │
│  │   TaskRouter   │  OrchestratorKernel │   CellOrchestrator      │    │
│  │  (Routing)     │  (IR Pipeline)      │   (Cell Workflows)      │    │
│  └────────────────┴─────────────────────┴─────────────────────────┘    │
│                              │                                          │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                      PlanExecutor                               │   │
│  │  (Execution with Memory + World Model hooks)                    │   │
│  └─────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────┘

Deterministic Phases:
  ingest → IR → validate → simulate → plan → execute → reflect

Usage:
    controller = UnifiedController(config)
    result = await controller.handle_request(
        text="Build a user authentication system",
        context={"project": "my-app"}
    )

Version: 2.0.0
"""

from __future__ import annotations

import structlog
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional
from uuid import UUID, uuid4

logger = structlog.get_logger(__name__)


# =============================================================================
# Enums
# =============================================================================


class ExecutionMode(str, Enum):
    """Execution modes for the controller."""

    NORMAL = "normal"  # Standard flow
    GOD_MODE = "god_mode"  # Full pipeline with all phases
    DEBUG = "debug"  # Extra logging, slower
    SAFE = "safe"  # Extra validation, no real execution
    FAST = "fast"  # Skip simulation for speed


class ControllerPhase(str, Enum):
    """Phases of controller execution (deterministic ordering)."""

    IDLE = "idle"
    ROUTING = "routing"
    COMPILING = "compiling"
    VALIDATING = "validating"
    CHALLENGING = "challenging"
    DELIBERATING = "deliberating"
    SIMULATING = "simulating"
    PLANNING = "planning"
    EXECUTING = "executing"
    REFLECTING = "reflecting"
    COMPLETE = "complete"
    ERROR = "error"


# =============================================================================
# Configuration
# =============================================================================


@dataclass
class ControllerConfig:
    """Configuration for the unified controller."""

    # Mode
    mode: ExecutionMode = ExecutionMode.GOD_MODE

    # Self-correction
    auto_self_correct: bool = True
    max_correction_attempts: int = 3

    # Pipeline options
    require_simulation: bool = True
    require_deliberation: bool = True
    require_collaboration: bool = False  # Use cells for complex tasks
    min_simulation_score: float = 0.6

    # API
    api_key: Optional[str] = None
    model: str = "gpt-4o"

    # Memory
    emit_packets: bool = True
    packet_source: str = "unified_controller"

    # Execution
    real_execution: bool = False  # When True, actually modify files


# =============================================================================
# State
# =============================================================================


@dataclass
class ControllerState:
    """Current state of the controller."""

    phase: ControllerPhase = ControllerPhase.IDLE
    current_graph: Optional[Any] = None  # IRGraph
    current_plan: Optional[Any] = None  # ExecutionPlan
    routing_decision: Optional[Any] = None  # RoutingDecision
    execution_history: list[dict[str, Any]] = field(default_factory=list)
    correction_count: int = 0
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    started_at: Optional[datetime] = None
    phase_times: dict[str, int] = field(default_factory=dict)


# =============================================================================
# Result
# =============================================================================


@dataclass
class ControllerResult:
    """Result from controller execution."""

    result_id: UUID = field(default_factory=uuid4)
    success: bool = False
    phase_reached: ControllerPhase = ControllerPhase.IDLE

    # Pipeline outputs
    graph: Optional[Any] = None
    plan: Optional[Any] = None

    # Routing info
    task_type: Optional[str] = None
    complexity: Optional[str] = None
    risk: Optional[str] = None
    route_target: Optional[str] = None

    # Scores
    simulation_score: float = 0.0
    consensus_score: float = 0.0

    # Execution
    execution_results: list[dict[str, Any]] = field(default_factory=list)
    artifacts: dict[str, Any] = field(default_factory=dict)

    # Corrections
    corrections_made: int = 0

    # Errors
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    # Timing
    duration_ms: int = 0
    phase_times: dict[str, int] = field(default_factory=dict)

    # Memory
    packets_emitted: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "result_id": str(self.result_id),
            "success": self.success,
            "phase_reached": self.phase_reached.value,
            "graph_id": str(self.graph.graph_id) if self.graph else None,
            "plan_id": str(self.plan.plan_id) if self.plan else None,
            "task_type": self.task_type,
            "complexity": self.complexity,
            "risk": self.risk,
            "route_target": self.route_target,
            "simulation_score": self.simulation_score,
            "corrections_made": self.corrections_made,
            "errors": self.errors,
            "duration_ms": self.duration_ms,
            "packets_emitted": self.packets_emitted,
        }


# =============================================================================
# Unified Controller
# =============================================================================


class UnifiedController:
    """
    GOD-MODE unified controller for L9.

    This is the primary interface for L9 task execution. It coordinates:

    1. **Task Routing**: Analyzes task complexity/risk to select execution path
    2. **IR Pipeline**: Compiles NL → IR → Validated IR → Plan
    3. **Simulation**: Evaluates plan viability before execution
    4. **Cell Collaboration**: Optional multi-agent refinement
    5. **Execution**: Runs plan with dependency management
    6. **Reflection**: Updates memory and world model

    Deterministic Phase Chain:
        routing → compiling → validating → challenging →
        deliberating → simulating → planning → executing → reflecting

    Usage:
        controller = UnifiedController(config)

        # Simple usage
        result = await controller.handle_request(
            text="Build a REST API for user management",
            context={"project": "my-app"}
        )

        # Access results
        if result.success:
            logger.info(f"Plan: {result.plan}")
            logger.info(f"Artifacts: {result.artifacts}")
    """

    def __init__(self, config: Optional[ControllerConfig] = None):
        """
        Initialize the unified controller.

        Args:
            config: Controller configuration
        """
        self._config = config or ControllerConfig()
        self._state = ControllerState()

        # Sub-components (lazy-loaded)
        self._router: Optional[Any] = None
        self._kernel: Optional[Any] = None
        self._cell_orchestrator: Optional[Any] = None
        self._plan_executor: Optional[Any] = None

        # IR Engine components
        self._compiler: Optional[Any] = None
        self._validator: Optional[Any] = None
        self._challenger: Optional[Any] = None
        self._deliberation: Optional[Any] = None
        self._simulation_router: Optional[Any] = None
        self._plan_adapter: Optional[Any] = None

        # External services
        self._memory_client: Optional[Any] = None
        self._world_model: Optional[Any] = None

        logger.info(f"UnifiedController initialized in {self._config.mode.value} mode")

    # =========================================================================
    # Component Initialization
    # =========================================================================

    def _ensure_components(self) -> None:
        """Lazy-load all components on first use."""
        if self._router is not None:
            return

        # Orchestration components
        from orchestration.task_router import TaskRouter
        from orchestration.orchestrator_kernel import OrchestratorKernel, KernelConfig
        from orchestration.cell_orchestrator import CellOrchestrator
        from orchestration.plan_executor import PlanExecutor, ExecutorConfig

        self._router = TaskRouter()

        self._kernel = OrchestratorKernel(
            KernelConfig(
                api_key=self._config.api_key,
                model=self._config.model,
                require_validation=True,
                require_simulation=self._config.require_simulation,
                emit_packets=self._config.emit_packets,
            )
        )

        self._cell_orchestrator = CellOrchestrator(
            {
                "api_key": self._config.api_key,
                "model": self._config.model,
                "emit_packets": self._config.emit_packets,
            }
        )

        self._plan_executor = PlanExecutor(
            ExecutorConfig(
                emit_packets=self._config.emit_packets,
                real_execution=self._config.real_execution,
            )
        )

        # IR Engine components
        try:
            from ir_engine.semantic_compiler import SemanticCompiler
            from ir_engine.ir_validator import IRValidator
            from ir_engine.constraint_challenger import ConstraintChallenger
            from ir_engine.simulation_router import SimulationRouter
            from ir_engine.ir_to_plan_adapter import IRToPlanAdapter
            from ir_engine.deliberation_cell import DeliberationCell

            self._compiler = SemanticCompiler(
                api_key=self._config.api_key,
                model=self._config.model,
            )
            self._validator = IRValidator()
            self._challenger = ConstraintChallenger(
                api_key=self._config.api_key,
                model=self._config.model,
                auto_apply=True,
            )
            self._deliberation = DeliberationCell(
                api_key=self._config.api_key,
                model=self._config.model,
            )
            self._simulation_router = SimulationRouter()
            self._plan_adapter = IRToPlanAdapter()

        except ImportError as e:
            logger.warning(f"Failed to load IR Engine components: {e}")

        # Wire up memory client if available
        if self._memory_client:
            self._kernel.set_memory_client(self._memory_client)
            self._cell_orchestrator.set_memory_client(self._memory_client)
            self._plan_executor.set_memory_client(self._memory_client)

        # Wire up world model if available
        if self._world_model:
            self._plan_executor.set_world_model(self._world_model)

        logger.info("UnifiedController components loaded")

    def set_memory_client(self, client: Any) -> None:
        """
        Set the memory substrate client.

        Args:
            client: MemorySubstrateService instance
        """
        self._memory_client = client

        # Propagate to sub-components if already initialized
        if self._kernel:
            self._kernel.set_memory_client(client)
        if self._cell_orchestrator:
            self._cell_orchestrator.set_memory_client(client)
        if self._plan_executor:
            self._plan_executor.set_memory_client(client)

        logger.info("Memory client attached to UnifiedController")

    def set_world_model(self, world_model: Any) -> None:
        """
        Set the world model runtime.

        Args:
            world_model: WorldModelService or WorldModelOrchestrator instance
        """
        self._world_model = world_model

        if self._plan_executor:
            self._plan_executor.set_world_model(world_model)

        logger.info("World model attached to UnifiedController")

    # =========================================================================
    # Main Entry Point
    # =========================================================================

    async def handle_request(
        self,
        text: str,
        context: Optional[dict[str, Any]] = None,
    ) -> ControllerResult:
        """
        Handle a request through the full L9 pipeline.

        This is the primary entry point for L9. It:
        1. Routes the task based on complexity/risk
        2. Runs the appropriate pipeline (IR only, IR+Sim, IR+Sim+Cells)
        3. Executes the generated plan
        4. Updates memory and world model

        Args:
            text: Natural language task description
            context: Optional execution context:
                - project: Project name/path
                - constraints: Additional constraints
                - preferences: Execution preferences
                - session_id: Session identifier

        Returns:
            ControllerResult with all pipeline outputs
        """
        self._ensure_components()

        # Reset state
        self._state = ControllerState(started_at=datetime.utcnow())
        result = ControllerResult()

        logger.info(
            f"Handling request in {self._config.mode.value} mode: {text[:100]}..."
        )

        try:
            # Phase 1: Route task
            await self._phase_routing(text, context or {}, result)

            # Phase 2-4: Compile, Validate, Challenge
            await self._phase_ir_pipeline(text, context or {}, result)

            # Phase 5: Deliberate (optional)
            if self._config.require_deliberation and self._should_deliberate(result):
                await self._phase_deliberate(text, result)

            # Phase 6: Simulate (optional)
            if (
                self._config.require_simulation
                and self._config.mode != ExecutionMode.FAST
            ):
                await self._phase_simulate(result)

                # Check score threshold
                if result.simulation_score < self._config.min_simulation_score:
                    await self._handle_low_simulation_score(text, context, result)

            # Phase 7: Plan
            await self._phase_plan(result)

            # Phase 8: Execute
            await self._phase_execute(context or {}, result)

            # Phase 9: Reflect
            await self._phase_reflect(context or {}, result)

            # Complete
            self._state.phase = ControllerPhase.COMPLETE
            result.success = True

        except Exception as e:
            logger.error(f"Controller execution failed: {e}")
            self._state.phase = ControllerPhase.ERROR
            self._state.errors.append(str(e))

            if self._config.auto_self_correct:
                await self._attempt_self_correction(text, context, e, result)

        # Finalize result
        result.phase_reached = self._state.phase
        result.graph = self._state.current_graph
        result.plan = self._state.current_plan
        result.corrections_made = self._state.correction_count
        result.errors = self._state.errors
        result.warnings = self._state.warnings
        result.phase_times = self._state.phase_times
        result.duration_ms = (
            self._elapsed_ms(self._state.started_at) if self._state.started_at else 0
        )

        logger.info(
            f"Request complete: success={result.success}, "
            f"phase={result.phase_reached.value}, "
            f"duration={result.duration_ms}ms"
        )

        return result

    # =========================================================================
    # Pipeline Phases
    # =========================================================================

    async def _phase_routing(
        self,
        text: str,
        context: dict[str, Any],
        result: ControllerResult,
    ) -> None:
        """Phase 1: Route task to appropriate execution path."""
        self._state.phase = ControllerPhase.ROUTING
        phase_start = datetime.utcnow()

        logger.info("Phase ROUTING: Analyzing task")

        task = {
            "text": text,
            "task_id": str(uuid4()),
            **context,
        }

        decision = self._router.route(task, context)
        self._state.routing_decision = decision

        # Record in result
        result.task_type = decision.task_type.value
        result.complexity = decision.complexity.value
        result.risk = decision.risk.value
        result.route_target = decision.primary_route.target.value

        self._state.execution_history.append(
            {
                "phase": "routing",
                "task_type": decision.task_type.value,
                "complexity": decision.complexity.value,
                "risk": decision.risk.value,
                "target": decision.primary_route.target.value,
                "confidence": decision.confidence,
            }
        )

        self._record_phase_time("routing", phase_start)

    async def _phase_ir_pipeline(
        self,
        text: str,
        context: dict[str, Any],
        result: ControllerResult,
    ) -> None:
        """Phases 2-4: Compile, Validate, Challenge."""
        # Phase 2: Compile
        self._state.phase = ControllerPhase.COMPILING
        phase_start = datetime.utcnow()

        logger.info("Phase COMPILING: Converting to IR")

        graph = await self._compiler.compile(text, context)
        self._state.current_graph = graph

        self._record_phase_time("compile", phase_start)

        # Phase 3: Validate
        self._state.phase = ControllerPhase.VALIDATING
        phase_start = datetime.utcnow()

        logger.info("Phase VALIDATING: Checking IR structure")

        validation_result = self._validator.validate(graph)

        if not validation_result.valid:
            errors = [e.message for e in validation_result.errors]
            raise ValueError(f"IR validation failed: {errors}")

        from ir_engine.ir_schema import IRStatus

        graph.set_status(IRStatus.VALIDATED)

        self._record_phase_time("validate", phase_start)

        # Phase 4: Challenge
        self._state.phase = ControllerPhase.CHALLENGING
        phase_start = datetime.utcnow()

        logger.info("Phase CHALLENGING: Checking constraints")

        challenge_result = await self._challenger.challenge(graph)

        self._state.execution_history.append(
            {
                "phase": "challenge",
                "challenged": len(challenge_result.challenged),
                "invalidated": len(challenge_result.invalidated),
                "hidden_found": len(challenge_result.hidden_found),
            }
        )

        self._record_phase_time("challenge", phase_start)

    async def _phase_deliberate(
        self,
        text: str,
        result: ControllerResult,
    ) -> None:
        """Phase 5: Agent deliberation for IR refinement."""
        self._state.phase = ControllerPhase.DELIBERATING
        phase_start = datetime.utcnow()

        logger.info("Phase DELIBERATING: Multi-agent refinement")

        if not self._state.current_graph:
            raise ValueError("No graph to deliberate")

        delib_result = await self._deliberation.deliberate(
            task=text,
            initial_graph=self._state.current_graph,
        )

        self._state.current_graph = delib_result.final_graph
        result.consensus_score = delib_result.final_score

        self._state.execution_history.append(
            {
                "phase": "deliberate",
                "rounds": delib_result.total_rounds,
                "consensus": delib_result.consensus_reached,
                "score": delib_result.final_score,
            }
        )

        self._record_phase_time("deliberate", phase_start)

    async def _phase_simulate(
        self,
        result: ControllerResult,
    ) -> None:
        """Phase 6: Simulate execution."""
        self._state.phase = ControllerPhase.SIMULATING
        phase_start = datetime.utcnow()

        logger.info("Phase SIMULATING: Evaluating plan viability")

        if not self._state.current_graph:
            raise ValueError("No graph to simulate")

        request = self._simulation_router.create_request(self._state.current_graph)
        sim_result = await self._simulation_router.route(request)

        result.simulation_score = sim_result.score

        from ir_engine.ir_schema import IRStatus

        self._state.current_graph.set_status(IRStatus.SIMULATED)

        self._state.execution_history.append(
            {
                "phase": "simulate",
                "score": sim_result.score,
                "success": sim_result.success,
                "failure_modes": sim_result.failure_modes,
            }
        )

        self._record_phase_time("simulate", phase_start)

    async def _phase_plan(
        self,
        result: ControllerResult,
    ) -> None:
        """Phase 7: Generate execution plan."""
        self._state.phase = ControllerPhase.PLANNING
        phase_start = datetime.utcnow()

        logger.info("Phase PLANNING: Generating execution plan")

        if not self._state.current_graph:
            raise ValueError("No graph to plan")

        plan = self._plan_adapter.to_execution_plan(self._state.current_graph)
        self._state.current_plan = plan

        self._state.execution_history.append(
            {
                "phase": "plan",
                "steps": len(plan.steps),
                "plan_id": str(plan.plan_id),
            }
        )

        self._record_phase_time("plan", phase_start)

    async def _phase_execute(
        self,
        context: dict[str, Any],
        result: ControllerResult,
    ) -> None:
        """Phase 8: Execute the plan."""
        self._state.phase = ControllerPhase.EXECUTING
        phase_start = datetime.utcnow()

        logger.info("Phase EXECUTING: Running plan")

        if not self._state.current_plan:
            raise ValueError("No plan to execute")

        # Check if we should use collaborative cells
        if self._should_use_cells(result):
            exec_result = await self._execute_with_cells(context, result)
        else:
            exec_result = await self._plan_executor.execute(
                self._state.current_plan,
                context,
            )

        result.execution_results = [sr.to_dict() for sr in exec_result.step_results]
        result.artifacts = exec_result.artifacts
        result.packets_emitted += exec_result.packets_emitted

        self._state.execution_history.append(
            {
                "phase": "execute",
                "steps_completed": exec_result.completed_steps,
                "steps_failed": exec_result.failed_steps,
                "status": exec_result.status.value,
            }
        )

        self._record_phase_time("execute", phase_start)

    async def _phase_reflect(
        self,
        context: dict[str, Any],
        result: ControllerResult,
    ) -> None:
        """Phase 9: Reflect and update memory/world model."""
        self._state.phase = ControllerPhase.REFLECTING
        phase_start = datetime.utcnow()

        logger.info("Phase REFLECTING: Updating memory")

        # Emit summary packet
        if self._memory_client and self._config.emit_packets:
            try:
                from core.schemas import PacketEnvelopeIn

                packet = PacketEnvelopeIn(
                    source=self._config.packet_source,
                    kind="controller_execution",
                    payload={
                        "result_id": str(result.result_id),
                        "success": result.success,
                        "task_type": result.task_type,
                        "complexity": result.complexity,
                        "risk": result.risk,
                        "simulation_score": result.simulation_score,
                        "corrections_made": result.corrections_made,
                        "duration_ms": self._elapsed_ms(self._state.started_at)
                        if self._state.started_at
                        else 0,
                    },
                    session_id=context.get("session_id"),
                )

                write_result = await self._memory_client.write_packet(packet)
                if write_result.success:
                    result.packets_emitted += 1

            except Exception as e:
                logger.warning(f"Failed to emit reflection packet: {e}")

        # Update world model
        if self._world_model:
            try:
                insights = self._build_reflection_insights(result)
                await self._world_model.update_from_insights(insights)
            except Exception as e:
                logger.warning(f"Failed to update world model: {e}")

        self._state.execution_history.append(
            {
                "phase": "reflect",
                "total_phases": len(self._state.phase_times),
                "total_duration_ms": sum(self._state.phase_times.values()),
            }
        )

        self._record_phase_time("reflect", phase_start)

    # =========================================================================
    # Self-Correction
    # =========================================================================

    async def _attempt_self_correction(
        self,
        text: str,
        context: Optional[dict[str, Any]],
        error: Exception,
        result: ControllerResult,
    ) -> None:
        """Attempt to self-correct after an error."""
        if self._state.correction_count >= self._config.max_correction_attempts:
            logger.warning("Max correction attempts reached")
            return

        self._state.correction_count += 1
        logger.info(
            f"Attempting self-correction (attempt {self._state.correction_count})"
        )

        error_str = str(error).lower()

        try:
            if "validation" in error_str:
                # Re-compile with stricter constraints
                logger.info("Re-compiling with validation feedback")
                enhanced_context = {
                    **(context or {}),
                    "previous_error": str(error),
                    "require_validation": True,
                }
                await self._phase_ir_pipeline(text, enhanced_context, result)

            elif "simulation" in error_str or "score" in error_str:
                # Re-deliberate with simulation feedback
                logger.info("Re-deliberating after simulation feedback")
                if self._state.current_graph:
                    await self._phase_deliberate(text, result)

            else:
                # General re-try from compile
                logger.info("General retry from compile phase")
                await self._phase_ir_pipeline(text, context or {}, result)

            # Continue pipeline if correction succeeded
            if self._state.current_graph:
                if not self._state.current_plan:
                    await self._phase_plan(result)
                await self._phase_execute(context or {}, result)
                await self._phase_reflect(context or {}, result)
                result.success = True

        except Exception as e:
            logger.error(f"Self-correction failed: {e}")
            self._state.errors.append(f"Self-correction failed: {e}")

    async def _handle_low_simulation_score(
        self,
        text: str,
        context: Optional[dict[str, Any]],
        result: ControllerResult,
    ) -> None:
        """Handle low simulation score by re-deliberating."""
        logger.warning(
            f"Simulation score {result.simulation_score:.2f} below threshold "
            f"{self._config.min_simulation_score}, attempting improvement"
        )

        if self._state.correction_count < self._config.max_correction_attempts:
            self._state.correction_count += 1

            # Re-deliberate with more rounds
            await self._phase_deliberate(text, result)
            await self._phase_simulate(result)

    # =========================================================================
    # Cell Integration
    # =========================================================================

    def _should_deliberate(self, result: ControllerResult) -> bool:
        """Determine if deliberation is needed based on task analysis."""
        # Always deliberate in GOD_MODE
        if self._config.mode == ExecutionMode.GOD_MODE:
            return True

        # Deliberate for complex/high-risk tasks
        if result.complexity in ("complex", "critical"):
            return True
        if result.risk in ("high", "critical"):
            return True

        return False

    def _should_use_cells(self, result: ControllerResult) -> bool:
        """Determine if collaborative cells should be used."""
        if not self._config.require_collaboration:
            return False

        # Use cells for design tasks
        if result.task_type == "design":
            return True

        # Use cells for complex/high-risk
        if result.complexity == "critical" or result.risk == "critical":
            return True

        return False

    async def _execute_with_cells(
        self,
        context: dict[str, Any],
        result: ControllerResult,
    ) -> Any:
        """Execute plan with collaborative cell refinement."""
        logger.info("Using collaborative cells for execution")

        # Run architect cell first
        arch_result = await self._cell_orchestrator.run_architect_cell(
            self._state.current_graph,
            context,
        )

        if arch_result.get("success"):
            # Refine plan based on architecture
            if arch_result.get("architecture"):
                # Update context with architecture
                context["architecture"] = arch_result["architecture"]

        # Run coder cell
        code_result = await self._cell_orchestrator.run_coder_cell(
            self._state.current_plan,
            context,
        )

        # Run regular execution for remaining steps
        exec_result = await self._plan_executor.execute(
            self._state.current_plan,
            context,
        )

        # Merge cell outputs into artifacts
        exec_result.artifacts["architecture"] = arch_result
        exec_result.artifacts["code"] = code_result

        return exec_result

    # =========================================================================
    # Reflection Helpers
    # =========================================================================

    def _build_reflection_insights(
        self,
        result: ControllerResult,
    ) -> list[dict[str, Any]]:
        """Build insights for world model update."""
        insights = []

        # Execution insight
        insights.append(
            {
                "insight_id": str(uuid4()),
                "insight_type": "controller_execution",
                "entities": [result.task_type, result.route_target]
                if result.task_type
                else [],
                "content": f"Controller executed {result.task_type} task via {result.route_target}",
                "confidence": 0.8,
                "trigger_world_model": result.success,
            }
        )

        # Error insight if failed
        if not result.success and result.errors:
            insights.append(
                {
                    "insight_id": str(uuid4()),
                    "insight_type": "execution_error",
                    "entities": [result.phase_reached.value],
                    "content": f"Execution failed at {result.phase_reached.value}: {result.errors[0]}",
                    "confidence": 0.9,
                    "trigger_world_model": True,
                }
            )

        return insights

    # =========================================================================
    # Utility Methods
    # =========================================================================

    def _record_phase_time(self, phase: str, start_time: datetime) -> None:
        """Record the duration of a phase."""
        duration_ms = self._elapsed_ms(start_time)
        self._state.phase_times[phase] = duration_ms

    def _elapsed_ms(self, start: datetime) -> int:
        """Calculate elapsed milliseconds from start time."""
        return int((datetime.utcnow() - start).total_seconds() * 1000)

    def get_state(self) -> ControllerState:
        """Get current controller state."""
        return self._state

    def get_phase(self) -> ControllerPhase:
        """Get current phase."""
        return self._state.phase

    def reset(self) -> None:
        """Reset controller state."""
        self._state = ControllerState()
        logger.info("Controller state reset")

    # =========================================================================
    # Alternative Entry Points
    # =========================================================================

    async def compile_only(
        self,
        text: str,
        context: Optional[dict[str, Any]] = None,
    ) -> Any:
        """
        Compile task to IR without full execution.

        Useful for inspection and debugging.

        Args:
            text: Task description
            context: Optional context

        Returns:
            IRGraph
        """
        self._ensure_components()

        graph = await self._compiler.compile(text, context)
        validation_result = self._validator.validate(graph)

        if not validation_result.valid:
            logger.warning(f"IR validation warnings: {validation_result.warnings}")

        return graph

    async def plan_only(
        self,
        text: str,
        context: Optional[dict[str, Any]] = None,
    ) -> Any:
        """
        Generate plan without execution.

        Useful for plan review before execution.

        Args:
            text: Task description
            context: Optional context

        Returns:
            ExecutionPlan
        """
        self._ensure_components()

        graph = await self._compiler.compile(text, context)
        self._validator.validate(graph)

        from ir_engine.ir_schema import IRStatus

        graph.set_status(IRStatus.VALIDATED)

        plan = self._plan_adapter.to_execution_plan(graph)

        return plan

    async def execute(
        self,
        task: str,
        context: Optional[dict[str, Any]] = None,
    ) -> ControllerResult:
        """
        Alias for handle_request for backwards compatibility.

        Args:
            task: Task description
            context: Optional context

        Returns:
            ControllerResult
        """
        return await self.handle_request(task, context)


# =============================================================================
# WebSocket Task Dispatch (Phase 2.5)
# =============================================================================

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from runtime.websocket_orchestrator import WebSocketOrchestrator


def get_ws_orchestrator() -> "WebSocketOrchestrator":
    """
    Get the shared WebSocket orchestrator singleton.

    Uses the module-level singleton from runtime.websocket_orchestrator.

    Returns:
        WebSocketOrchestrator instance
    """
    from runtime.websocket_orchestrator import ws_orchestrator

    return ws_orchestrator


def set_ws_orchestrator(orchestrator: "WebSocketOrchestrator") -> None:
    """
    Deprecated: The orchestrator is now a module-level singleton.

    This function is kept for backwards compatibility but does nothing.
    Import ws_orchestrator directly from runtime.websocket_orchestrator.

    Args:
        orchestrator: Ignored (singleton is used instead)
    """
    logger.warning(
        "set_ws_orchestrator is deprecated. "
        "Import ws_orchestrator from runtime.websocket_orchestrator instead."
    )


async def dispatch_task_to_agent(
    agent_id: str,
    task_payload: dict[str, Any],
    task_type: str = "command",
    priority: int = 5,
    trace_id: Optional[str] = None,
) -> None:
    """
    Convert controller task payload → EventMessage → WS outbound.

    This is the primary integration point for the unified controller
    to dispatch tasks to connected agents via WebSocket.

    Args:
        agent_id: Target agent identifier
        task_payload: Task parameters and data
        task_type: Type of task (default: "command")
        priority: Task priority 1-10 (default: 5)
        trace_id: Optional trace ID for distributed tracing

    Usage:
        await dispatch_task_to_agent(
            agent_id="coder-agent-1",
            task_payload={"action": "build", "target": "api"},
            task_type="execution"
        )

    Raises:
        RuntimeError: If agent is not connected
    """
    from core.schemas.ws_event_stream import EventMessage, EventType
    from uuid import uuid4

    ws = get_ws_orchestrator()

    event = EventMessage(
        type=EventType.TASK_ASSIGNED,
        channel="task",
        agent_id=agent_id,
        payload={
            "task_id": str(uuid4()),
            "task_type": task_type,
            "priority": priority,
            **task_payload,
        },
        trace_id=trace_id,
    )

    await ws.dispatch_event(agent_id, event)
    logger.info(
        "Dispatched task to agent %s: type=%s, trace=%s", agent_id, task_type, trace_id
    )


async def broadcast_task(
    task_payload: dict[str, Any],
    task_type: str = "broadcast",
    exclude_agents: Optional[set[str]] = None,
) -> int:
    """
    Broadcast a task to all connected agents.

    Phase 2 integration for multi-agent coordination.

    Args:
        task_payload: Task parameters
        task_type: Type of task
        exclude_agents: Agents to exclude from broadcast

    Returns:
        Number of agents task was sent to
    """
    from core.schemas.ws_event_stream import EventMessage, EventType
    from uuid import uuid4

    ws = get_ws_orchestrator()

    event = EventMessage(
        type=EventType.TASK_ASSIGNED,
        channel="broadcast",
        payload={
            "task_id": str(uuid4()),
            "task_type": task_type,
            **task_payload,
        },
    )

    count = await ws.broadcast(event, exclude=exclude_agents)
    logger.info("Broadcast task to %d agents: type=%s", count, task_type)

    return count
