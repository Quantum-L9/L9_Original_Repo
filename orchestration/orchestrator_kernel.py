"""
L9 Orchestration - Orchestrator Kernel
======================================

Core deterministic execution loop for the L9 IR Engine pipeline.

Responsibilities:
- Accept task spec (NL + metadata)
- Run: SemanticCompiler → IRValidator → SimulationRouter → IRToPlanAdapter
- Emit PacketEnvelopes to Memory Substrate
- Enforce deterministic phases + logging

Deterministic Phases:
  1. INGEST    - Receive and normalize task input
  2. COMPILE   - SemanticCompiler: NL → IRGraph
  3. VALIDATE  - IRValidator: Schema + completeness checks
  4. CHALLENGE - ConstraintChallenger: Detect false constraints
  5. SIMULATE  - SimulationRouter: Evaluate IR candidates (optional)
  6. PLAN      - IRToPlanAdapter: IR → ExecutionPlan
  7. EXECUTE   - PlanExecutor: Run plan steps
  8. REFLECT   - Update memory, world model, metrics

Version: 2.0.0
"""

from __future__ import annotations

import structlog
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Optional
from uuid import UUID, uuid4

logger = structlog.get_logger(__name__)


# =============================================================================
# Enums and Types
# =============================================================================


class ChainStatus(str, Enum):
    """Status of an execution chain."""

    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class KernelPhase(str, Enum):
    """Phases of kernel execution - strict ordering enforced."""

    IDLE = "idle"
    INGEST = "ingest"
    COMPILE = "compile"
    VALIDATE = "validate"
    CHALLENGE = "challenge"
    SIMULATE = "simulate"
    PLAN = "plan"
    EXECUTE = "execute"
    REFLECT = "reflect"
    COMPLETE = "complete"
    ERROR = "error"


# Phase transition rules (deterministic ordering)
VALID_PHASE_TRANSITIONS = {
    KernelPhase.IDLE: [KernelPhase.INGEST],
    KernelPhase.INGEST: [KernelPhase.COMPILE, KernelPhase.ERROR],
    KernelPhase.COMPILE: [KernelPhase.VALIDATE, KernelPhase.ERROR],
    KernelPhase.VALIDATE: [KernelPhase.CHALLENGE, KernelPhase.ERROR],
    KernelPhase.CHALLENGE: [KernelPhase.SIMULATE, KernelPhase.PLAN, KernelPhase.ERROR],
    KernelPhase.SIMULATE: [KernelPhase.PLAN, KernelPhase.CHALLENGE, KernelPhase.ERROR],
    KernelPhase.PLAN: [KernelPhase.EXECUTE, KernelPhase.ERROR],
    KernelPhase.EXECUTE: [KernelPhase.REFLECT, KernelPhase.ERROR],
    KernelPhase.REFLECT: [KernelPhase.COMPLETE, KernelPhase.ERROR],
    KernelPhase.COMPLETE: [KernelPhase.IDLE],
    KernelPhase.ERROR: [KernelPhase.IDLE, KernelPhase.INGEST],  # Recovery paths
}


# =============================================================================
# Data Classes
# =============================================================================


@dataclass
class ChainStep:
    """A step in an execution chain."""

    step_id: UUID = field(default_factory=uuid4)
    name: str = ""
    handler: Optional[str] = None
    parameters: dict[str, Any] = field(default_factory=dict)
    status: str = "pending"
    result: Optional[dict[str, Any]] = None
    error: Optional[str] = None
    duration_ms: int = 0


@dataclass
class ExecutionChain:
    """A deterministic execution chain."""

    chain_id: UUID = field(default_factory=uuid4)
    name: str = ""
    steps: list[ChainStep] = field(default_factory=list)
    status: ChainStatus = ChainStatus.PENDING
    current_step: int = 0
    context: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "chain_id": str(self.chain_id),
            "name": self.name,
            "status": self.status.value,
            "current_step": self.current_step,
            "total_steps": len(self.steps),
            "steps": [{"name": s.name, "status": s.status} for s in self.steps],
        }


@dataclass
class KernelConfig:
    """Configuration for the orchestrator kernel."""

    max_chain_steps: int = 100
    step_timeout_ms: int = 60000
    allow_parallel_chains: bool = False
    checkpoint_interval: int = 5
    retry_on_failure: bool = True
    max_retries: int = 3
    # IR Engine options
    require_validation: bool = True
    require_simulation: bool = True
    min_simulation_score: float = 0.6
    auto_challenge_constraints: bool = True
    # Memory options
    emit_packets: bool = True
    packet_source: str = "orchestrator_kernel"
    # API options
    api_key: Optional[str] = None
    model: str = "gpt-4o"


@dataclass
class KernelState:
    """State of the orchestrator kernel."""

    phase: KernelPhase = KernelPhase.IDLE
    active_chains: dict[UUID, ExecutionChain] = field(default_factory=dict)
    completed_chains: list[UUID] = field(default_factory=list)
    failed_chains: list[UUID] = field(default_factory=list)
    total_steps_executed: int = 0
    checkpoints: list[dict[str, Any]] = field(default_factory=list)
    phase_history: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class IRPipelineResult:
    """
    Result from running the IR Engine pipeline.

    Contains the graph, plan, simulation results, and metadata
    from a complete ingest→reflect cycle.
    """

    result_id: UUID = field(default_factory=uuid4)
    success: bool = False

    # Phase outputs
    graph: Optional[Any] = None  # IRGraph
    plan: Optional[Any] = None  # ExecutionPlan
    simulation_score: float = 0.0
    simulation_metrics: dict[str, Any] = field(default_factory=dict)

    # Challenge results
    constraints_challenged: int = 0
    constraints_invalidated: int = 0
    hidden_constraints_found: int = 0

    # Execution results
    steps_executed: int = 0
    steps_failed: int = 0
    execution_artifacts: dict[str, Any] = field(default_factory=dict)

    # Timing
    phase_times: dict[str, int] = field(default_factory=dict)
    total_duration_ms: int = 0

    # Errors
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    # Memory packets emitted
    packets_emitted: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "result_id": str(self.result_id),
            "success": self.success,
            "graph_id": str(self.graph.graph_id) if self.graph else None,
            "plan_id": str(self.plan.plan_id) if self.plan else None,
            "simulation_score": self.simulation_score,
            "constraints_challenged": self.constraints_challenged,
            "steps_executed": self.steps_executed,
            "total_duration_ms": self.total_duration_ms,
            "errors": self.errors,
            "packets_emitted": self.packets_emitted,
        }


# =============================================================================
# Orchestrator Kernel
# =============================================================================


class OrchestratorKernel:
    """
    Core kernel for deterministic IR Engine execution.

    Executes the full pipeline:
      ingest → compile → validate → challenge → simulate → plan → execute → reflect

    Each phase transition is validated against VALID_PHASE_TRANSITIONS.
    State is logged at each transition for debugging and replay.

    Memory Integration:
    - Emits PacketEnvelopes at key phases for persistence
    - Supports checkpoint/restore for long-running operations

    Usage:
        kernel = OrchestratorKernel(config)
        result = await kernel.run_pipeline(
            task="Create a user authentication system",
            context={"project": "my-app"}
        )
    """

    def __init__(self, config: Optional[KernelConfig] = None):
        """
        Initialize the kernel.

        Args:
            config: Kernel configuration
        """
        self._config = config or KernelConfig()
        self._state = KernelState()
        self._handlers: dict[str, Callable] = {}

        # IR Engine components (lazy-loaded)
        self._compiler: Optional[Any] = None
        self._validator: Optional[Any] = None
        self._challenger: Optional[Any] = None
        self._simulation_router: Optional[Any] = None
        self._plan_adapter: Optional[Any] = None

        # Memory substrate client (optional)
        self._memory_client: Optional[Any] = None

        # Callbacks
        self._phase_callbacks: list[Callable[[KernelPhase, dict[str, Any]], None]] = []

        logger.info("OrchestratorKernel initialized")

    # =========================================================================
    # Component Initialization
    # =========================================================================

    def _ensure_components(self) -> None:
        """Lazy-load IR Engine components on first use."""
        if self._compiler is not None:
            return

        try:
            from ir_engine.semantic_compiler import SemanticCompiler
            from ir_engine.ir_validator import IRValidator
            from ir_engine.constraint_challenger import ConstraintChallenger
            from ir_engine.simulation_router import SimulationRouter
            from ir_engine.ir_to_plan_adapter import IRToPlanAdapter

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
            self._simulation_router = SimulationRouter()
            self._plan_adapter = IRToPlanAdapter()

            logger.info("IR Engine components loaded")
        except ImportError as e:
            logger.error(f"Failed to load IR Engine components: {e}")
            raise

    def set_memory_client(self, client: Any) -> None:
        """
        Set the memory substrate client for packet emission.

        Args:
            client: MemorySubstrateService instance
        """
        self._memory_client = client
        logger.info("Memory substrate client attached to kernel")

    def on_phase_change(
        self,
        callback: Callable[[KernelPhase, dict[str, Any]], None],
    ) -> None:
        """
        Register a callback for phase transitions.

        Args:
            callback: Function(phase, context) called on each transition
        """
        self._phase_callbacks.append(callback)

    # =========================================================================
    # Phase Management
    # =========================================================================

    def _transition_phase(
        self,
        new_phase: KernelPhase,
        context: Optional[dict[str, Any]] = None,
    ) -> bool:
        """
        Attempt to transition to a new phase.

        Validates the transition against VALID_PHASE_TRANSITIONS.
        Logs all transitions for audit trail.

        Args:
            new_phase: Target phase
            context: Optional context data

        Returns:
            True if transition succeeded
        """
        current = self._state.phase
        valid_next = VALID_PHASE_TRANSITIONS.get(current, [])

        if new_phase not in valid_next:
            logger.error(
                f"Invalid phase transition: {current.value} → {new_phase.value}. "
                f"Valid transitions: {[p.value for p in valid_next]}"
            )
            return False

        # Record transition
        transition_record = {
            "from": current.value,
            "to": new_phase.value,
            "timestamp": datetime.utcnow().isoformat(),
            "context": context or {},
        }
        self._state.phase_history.append(transition_record)
        self._state.phase = new_phase

        logger.info(f"Phase transition: {current.value} → {new_phase.value}")

        # Fire callbacks
        for callback in self._phase_callbacks:
            try:
                callback(new_phase, context or {})
            except Exception as e:
                logger.warning(f"Phase callback error: {e}")

        return True

    # =========================================================================
    # Main Pipeline
    # =========================================================================

    async def run_pipeline(
        self,
        task: str,
        context: Optional[dict[str, Any]] = None,
        skip_simulation: bool = False,
    ) -> IRPipelineResult:
        """
        Run the complete IR Engine pipeline on a task.

        Deterministic phase chain:
          ingest → compile → validate → challenge → simulate → plan → execute → reflect

        Args:
            task: Natural language task description
            context: Optional execution context (project info, constraints, etc.)
            skip_simulation: Skip simulation phase (for fast iteration)

        Returns:
            IRPipelineResult with graph, plan, and execution results
        """
        self._ensure_components()

        result = IRPipelineResult()
        start_time = datetime.utcnow()
        context = context or {}

        logger.info(f"Starting IR pipeline for task: {task[:100]}...")

        try:
            # Phase 1: INGEST
            self._transition_phase(KernelPhase.INGEST, {"task_length": len(task)})
            phase_start = datetime.utcnow()
            normalized_task, normalized_context = await self._phase_ingest(
                task, context
            )
            result.phase_times["ingest"] = self._elapsed_ms(phase_start)

            # Phase 2: COMPILE
            self._transition_phase(KernelPhase.COMPILE)
            phase_start = datetime.utcnow()
            graph = await self._phase_compile(normalized_task, normalized_context)
            result.graph = graph
            result.phase_times["compile"] = self._elapsed_ms(phase_start)

            # Phase 3: VALIDATE
            self._transition_phase(KernelPhase.VALIDATE)
            phase_start = datetime.utcnow()
            await self._phase_validate(graph)
            result.phase_times["validate"] = self._elapsed_ms(phase_start)

            # Phase 4: CHALLENGE
            if self._config.auto_challenge_constraints:
                self._transition_phase(KernelPhase.CHALLENGE)
                phase_start = datetime.utcnow()
                challenge_stats = await self._phase_challenge(graph)
                result.constraints_challenged = challenge_stats.get("challenged", 0)
                result.constraints_invalidated = challenge_stats.get("invalidated", 0)
                result.hidden_constraints_found = challenge_stats.get("hidden_found", 0)
                result.phase_times["challenge"] = self._elapsed_ms(phase_start)

            # Phase 5: SIMULATE (optional)
            if self._config.require_simulation and not skip_simulation:
                self._transition_phase(KernelPhase.SIMULATE)
                phase_start = datetime.utcnow()
                sim_result = await self._phase_simulate(graph)
                result.simulation_score = sim_result.get("score", 0.0)
                result.simulation_metrics = sim_result.get("metrics", {})
                result.phase_times["simulate"] = self._elapsed_ms(phase_start)

                # Check score threshold
                if result.simulation_score < self._config.min_simulation_score:
                    result.warnings.append(
                        f"Simulation score {result.simulation_score:.2f} below threshold "
                        f"{self._config.min_simulation_score}"
                    )
            else:
                # Skip directly to PLAN
                self._transition_phase(KernelPhase.PLAN)

            # Phase 6: PLAN
            if self._state.phase != KernelPhase.PLAN:
                self._transition_phase(KernelPhase.PLAN)
            phase_start = datetime.utcnow()
            plan = await self._phase_plan(graph)
            result.plan = plan
            result.phase_times["plan"] = self._elapsed_ms(phase_start)

            # Phase 7: EXECUTE
            self._transition_phase(KernelPhase.EXECUTE)
            phase_start = datetime.utcnow()
            exec_result = await self._phase_execute(plan, context)
            result.steps_executed = exec_result.get("completed", 0)
            result.steps_failed = exec_result.get("failed", 0)
            result.execution_artifacts = exec_result.get("artifacts", {})
            result.phase_times["execute"] = self._elapsed_ms(phase_start)

            # Phase 8: REFLECT
            self._transition_phase(KernelPhase.REFLECT)
            phase_start = datetime.utcnow()
            packets = await self._phase_reflect(result, context)
            result.packets_emitted = packets
            result.phase_times["reflect"] = self._elapsed_ms(phase_start)

            # Complete
            self._transition_phase(KernelPhase.COMPLETE)
            result.success = True

        except Exception as e:
            logger.error(f"Pipeline failed at phase {self._state.phase.value}: {e}")
            self._transition_phase(KernelPhase.ERROR, {"error": str(e)})
            result.errors.append(str(e))
            result.success = False

        result.total_duration_ms = self._elapsed_ms(start_time)

        # Reset to idle for next run
        self._state.phase = KernelPhase.IDLE

        logger.info(
            f"Pipeline complete: success={result.success}, "
            f"duration={result.total_duration_ms}ms, "
            f"steps_executed={result.steps_executed}"
        )

        return result

    # =========================================================================
    # Phase Implementations
    # =========================================================================

    async def _phase_ingest(
        self,
        task: str,
        context: dict[str, Any],
    ) -> tuple[str, dict[str, Any]]:
        """
        Phase 1: INGEST - Normalize and prepare task input.

        Args:
            task: Raw task string
            context: Raw context

        Returns:
            Tuple of (normalized_task, normalized_context)
        """
        logger.info("Phase INGEST: Normalizing task input")

        # Normalize whitespace
        normalized_task = " ".join(task.split())

        # Ensure required context fields
        normalized_context = {
            "session_id": context.get("session_id", str(uuid4())),
            "user_id": context.get("user_id"),
            "agent_id": context.get("agent_id"),
            "timestamp": datetime.utcnow().isoformat(),
            **context,
        }

        return normalized_task, normalized_context

    async def _phase_compile(
        self,
        task: str,
        context: dict[str, Any],
    ) -> Any:
        """
        Phase 2: COMPILE - Convert NL to IR using SemanticCompiler.

        Args:
            task: Normalized task description
            context: Execution context

        Returns:
            IRGraph
        """
        logger.info("Phase COMPILE: Compiling task to IR")

        graph = await self._compiler.compile(task, context)

        logger.info(
            f"Compiled IR: {len(graph.intents)} intents, "
            f"{len(graph.constraints)} constraints, "
            f"{len(graph.actions)} actions"
        )

        return graph

    async def _phase_validate(self, graph: Any) -> None:
        """
        Phase 3: VALIDATE - Validate IR structure and completeness.

        Args:
            graph: IRGraph to validate

        Raises:
            ValueError if validation fails
        """
        logger.info("Phase VALIDATE: Validating IR structure")

        result = self._validator.validate(graph)

        if not result.valid:
            errors = [e.message for e in result.errors]
            logger.error(f"IR validation failed: {errors}")
            raise ValueError(f"IR validation failed: {errors}")

        # Update graph status
        from ir_engine.ir_schema import IRStatus

        graph.set_status(IRStatus.VALIDATED)

        logger.info(
            f"Validation passed: {len(result.warnings)} warnings, "
            f"{len(result.info)} info messages"
        )

    async def _phase_challenge(self, graph: Any) -> dict[str, Any]:
        """
        Phase 4: CHALLENGE - Detect and challenge false constraints.

        Args:
            graph: Validated IRGraph

        Returns:
            Stats dict with challenged/invalidated/hidden counts
        """
        logger.info("Phase CHALLENGE: Challenging constraints")

        challenge_result = await self._challenger.challenge(graph)

        stats = {
            "challenged": len(challenge_result.challenged),
            "invalidated": len(challenge_result.invalidated),
            "hidden_found": len(challenge_result.hidden_found),
        }

        logger.info(
            f"Challenge complete: {stats['challenged']} challenged, "
            f"{stats['invalidated']} invalidated, "
            f"{stats['hidden_found']} hidden found"
        )

        return stats

    async def _phase_simulate(self, graph: Any) -> dict[str, Any]:
        """
        Phase 5: SIMULATE - Evaluate IR via simulation.

        Args:
            graph: Challenged IRGraph

        Returns:
            Dict with score and metrics
        """
        logger.info("Phase SIMULATE: Running simulation")

        request = self._simulation_router.create_request(graph)
        sim_result = await self._simulation_router.route(request)

        # Update graph status
        from ir_engine.ir_schema import IRStatus

        graph.set_status(IRStatus.SIMULATED)

        logger.info(f"Simulation score: {sim_result.score:.2f}")

        return {
            "score": sim_result.score,
            "metrics": sim_result.metrics,
            "failure_modes": sim_result.failure_modes,
        }

    async def _phase_plan(self, graph: Any) -> Any:
        """
        Phase 6: PLAN - Convert IR to execution plan.

        Args:
            graph: Simulated IRGraph

        Returns:
            ExecutionPlan
        """
        logger.info("Phase PLAN: Generating execution plan")

        plan = self._plan_adapter.to_execution_plan(graph)

        logger.info(f"Generated plan with {len(plan.steps)} steps")

        return plan

    async def _phase_execute(
        self,
        plan: Any,
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Phase 7: EXECUTE - Execute the plan steps.

        In kernel mode, we simulate execution.
        Full execution is delegated to PlanExecutor.

        Args:
            plan: ExecutionPlan
            context: Execution context

        Returns:
            Dict with execution stats
        """
        logger.info(f"Phase EXECUTE: Executing {len(plan.steps)} steps")

        # Kernel performs simulated execution
        # Real execution is handled by PlanExecutor in UnifiedController
        completed = 0
        failed = 0
        artifacts = {}

        for step in plan.steps:
            try:
                # Simulated execution
                step.status = "completed"
                step.result = {
                    "action_type": step.action_type,
                    "target": step.target,
                    "status": "simulated",
                }
                completed += 1
                artifacts[str(step.step_id)] = step.result
            except Exception as e:
                step.status = "failed"
                step.error = str(e)
                failed += 1

        logger.info(f"Execution complete: {completed} completed, {failed} failed")

        return {
            "completed": completed,
            "failed": failed,
            "artifacts": artifacts,
        }

    async def _phase_reflect(
        self,
        result: IRPipelineResult,
        context: dict[str, Any],
    ) -> int:
        """
        Phase 8: REFLECT - Emit memory packets and update metrics.

        Args:
            result: Pipeline result
            context: Execution context

        Returns:
            Number of packets emitted
        """
        logger.info("Phase REFLECT: Emitting memory packets")

        packets_emitted = 0

        if self._config.emit_packets and self._memory_client:
            try:
                # Emit pipeline result packet
                from core.schemas.packet_envelope_v2 import PacketEnvelopeIn

                packet = PacketEnvelopeIn(
                    source=self._config.packet_source,
                    kind="ir_pipeline_result",
                    payload={
                        "result_id": str(result.result_id),
                        "success": result.success,
                        "graph_id": str(result.graph.graph_id)
                        if result.graph
                        else None,
                        "plan_id": str(result.plan.plan_id) if result.plan else None,
                        "simulation_score": result.simulation_score,
                        "steps_executed": result.steps_executed,
                        "duration_ms": result.total_duration_ms,
                        "phase_times": result.phase_times,
                    },
                    session_id=context.get("session_id"),
                    agent_id=context.get("agent_id"),
                )

                write_result = await self._memory_client.write_packet(packet)
                if write_result.success:
                    packets_emitted += 1

            except Exception as e:
                logger.warning(f"Failed to emit memory packet: {e}")

        logger.info(f"Reflect complete: {packets_emitted} packets emitted")

        return packets_emitted

    # =========================================================================
    # Chain Management (for step-based execution)
    # =========================================================================

    def register_handler(
        self,
        name: str,
        handler: Callable[[dict[str, Any], dict[str, Any]], dict[str, Any]],
    ) -> None:
        """
        Register a step handler.

        Args:
            name: Handler name
            handler: Handler function (params, context) -> result
        """
        self._handlers[name] = handler
        logger.debug(f"Registered handler: {name}")

    def get_handler(self, name: str) -> Optional[Callable]:
        """Get a registered handler."""
        return self._handlers.get(name)

    def create_chain(
        self,
        name: str,
        steps: list[dict[str, Any]],
        context: Optional[dict[str, Any]] = None,
    ) -> ExecutionChain:
        """
        Create an execution chain.

        Args:
            name: Chain name
            steps: List of step definitions
            context: Initial context

        Returns:
            Created ExecutionChain
        """
        chain_steps = []
        for step_def in steps:
            step = ChainStep(
                name=step_def.get("name", "unnamed"),
                handler=step_def.get("handler"),
                parameters=step_def.get("parameters", {}),
            )
            chain_steps.append(step)

        chain = ExecutionChain(
            name=name,
            steps=chain_steps,
            context=context or {},
        )

        self._state.active_chains[chain.chain_id] = chain

        logger.info(f"Created chain {chain.chain_id} with {len(chain_steps)} steps")

        return chain

    async def execute_chain(self, chain_id: UUID) -> ExecutionChain:
        """
        Execute a chain to completion.

        Args:
            chain_id: Chain to execute

        Returns:
            Completed chain
        """
        chain = self._state.active_chains.get(chain_id)
        if not chain:
            raise ValueError(f"Chain {chain_id} not found")

        if chain.status == ChainStatus.RUNNING:
            raise ValueError(f"Chain {chain_id} already running")

        chain.status = ChainStatus.RUNNING
        chain.started_at = datetime.utcnow()

        logger.info(f"Executing chain {chain_id}")

        try:
            while chain.current_step < len(chain.steps):
                step = chain.steps[chain.current_step]
                await self._execute_chain_step(chain, step)

                if step.status == "failed":
                    if self._config.retry_on_failure:
                        retries = 0
                        while (
                            retries < self._config.max_retries
                            and step.status == "failed"
                        ):
                            retries += 1
                            logger.info(
                                f"Retrying step {step.name} (attempt {retries})"
                            )
                            step.status = "pending"
                            step.error = None
                            await self._execute_chain_step(chain, step)

                    if step.status == "failed":
                        chain.status = ChainStatus.FAILED
                        break

                chain.current_step += 1
                self._state.total_steps_executed += 1

                # Checkpoint
                if chain.current_step % self._config.checkpoint_interval == 0:
                    self._create_checkpoint(chain)

            if chain.status != ChainStatus.FAILED:
                chain.status = ChainStatus.COMPLETED
                self._state.completed_chains.append(chain_id)
            else:
                self._state.failed_chains.append(chain_id)

        except Exception as e:
            logger.error(f"Chain {chain_id} failed: {e}")
            chain.status = ChainStatus.FAILED
            self._state.failed_chains.append(chain_id)

        chain.completed_at = datetime.utcnow()

        if chain_id in self._state.active_chains:
            del self._state.active_chains[chain_id]

        logger.info(f"Chain {chain_id} completed with status {chain.status.value}")

        return chain

    async def _execute_chain_step(
        self,
        chain: ExecutionChain,
        step: ChainStep,
    ) -> None:
        """Execute a single chain step."""
        step.status = "running"
        start_time = datetime.utcnow()

        logger.debug(f"Executing step: {step.name}")

        try:
            if step.handler and step.handler in self._handlers:
                handler = self._handlers[step.handler]
                result = handler(step.parameters, chain.context)

                if hasattr(result, "__await__"):
                    result = await result

                step.result = result
                step.status = "completed"
                chain.context[f"step_{step.name}_result"] = result
            else:
                step.result = {"status": "no_handler"}
                step.status = "completed"

        except Exception as e:
            logger.error(f"Step {step.name} failed: {e}")
            step.status = "failed"
            step.error = str(e)

        step.duration_ms = self._elapsed_ms(start_time)

    # =========================================================================
    # Checkpointing
    # =========================================================================

    def _create_checkpoint(self, chain: ExecutionChain) -> None:
        """Create a checkpoint for a chain."""
        checkpoint = {
            "chain_id": str(chain.chain_id),
            "current_step": chain.current_step,
            "context": chain.context.copy(),
            "timestamp": datetime.utcnow().isoformat(),
        }
        self._state.checkpoints.append(checkpoint)
        logger.debug(
            f"Checkpoint created for chain {chain.chain_id} at step {chain.current_step}"
        )

    # =========================================================================
    # State Access
    # =========================================================================

    def get_chain(self, chain_id: UUID) -> Optional[ExecutionChain]:
        """Get a chain by ID."""
        return self._state.active_chains.get(chain_id)

    def get_active_chains(self) -> list[ExecutionChain]:
        """Get all active chains."""
        return list(self._state.active_chains.values())

    def get_state(self) -> KernelState:
        """Get kernel state."""
        return self._state

    def get_phase(self) -> KernelPhase:
        """Get current phase."""
        return self._state.phase

    def get_statistics(self) -> dict[str, Any]:
        """Get kernel statistics."""
        return {
            "current_phase": self._state.phase.value,
            "active_chains": len(self._state.active_chains),
            "completed_chains": len(self._state.completed_chains),
            "failed_chains": len(self._state.failed_chains),
            "total_steps_executed": self._state.total_steps_executed,
            "checkpoints": len(self._state.checkpoints),
            "phase_transitions": len(self._state.phase_history),
            "registered_handlers": len(self._handlers),
        }

    # =========================================================================
    # Utility
    # =========================================================================

    def _elapsed_ms(self, start: datetime) -> int:
        """Calculate elapsed milliseconds from start time."""
        return int((datetime.utcnow() - start).total_seconds() * 1000)
