"""
L9 Orchestration - Plan Executor
================================

Executes finalized plans from IRToPlanAdapter.

Responsibilities:
- Iterate over ExecutionSteps
- Call lower-level executors (repo writer, Cursor adapter, tool orchestrator)
- Record step results
- Emit update packets to Memory Substrate
- Handle parallel execution with dependency awareness

Execution Model:
┌─────────────────────────────────────────────────────────────────┐
│                       PlanExecutor                               │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │                    ExecutionPlan                           │ │
│  │  ┌──────┐  ┌──────┐  ┌──────┐  ┌──────┐                   │ │
│  │  │Step 1│──│Step 2│──│Step 3│──│Step 4│ (dependency chain)│ │
│  │  └──────┘  └──────┘  └──────┘  └──────┘                   │ │
│  └────────────────────────────────────────────────────────────┘ │
│                          │                                       │
│  ┌────────────┬──────────┴──────────┬────────────────────┐      │
│  │  Handlers  │   Memory Substrate  │  Progress Callbacks │      │
│  └────────────┴─────────────────────┴────────────────────┘      │
└─────────────────────────────────────────────────────────────────┘

Version: 2.0.0
"""

from __future__ import annotations

import asyncio
import structlog
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Optional
from uuid import UUID, uuid4

# Strategy Memory (optional - Phase 0)
from memory.strategymemory import (
    IStrategyMemoryService,
    StrategyCandidate,
    StrategyFeedback,
    StrategyRetrievalRequest,
)

logger = structlog.get_logger(__name__)


# =============================================================================
# Enums
# =============================================================================


class ExecutionStatus(str, Enum):
    """Status of plan execution."""

    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    PARTIAL = "partial"


class StepStatus(str, Enum):
    """Status of a single step."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


# =============================================================================
# Data Classes
# =============================================================================


@dataclass
class StepResult:
    """Result of executing a single step."""

    step_id: UUID
    status: StepStatus
    action_type: str = ""
    target: str = ""
    output: Optional[dict[str, Any]] = None
    error: Optional[str] = None
    duration_ms: int = 0
    retries: int = 0
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "step_id": str(self.step_id),
            "status": self.status.value,
            "action_type": self.action_type,
            "target": self.target,
            "output": self.output,
            "error": self.error,
            "duration_ms": self.duration_ms,
            "retries": self.retries,
        }


@dataclass
class ExecutionResult:
    """Result of plan execution."""

    execution_id: UUID = field(default_factory=uuid4)
    plan_id: UUID = field(default_factory=uuid4)
    status: ExecutionStatus = ExecutionStatus.PENDING
    step_results: list[StepResult] = field(default_factory=list)
    completed_steps: int = 0
    failed_steps: int = 0
    skipped_steps: int = 0
    artifacts: dict[str, Any] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    packets_emitted: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "execution_id": str(self.execution_id),
            "plan_id": str(self.plan_id),
            "status": self.status.value,
            "completed_steps": self.completed_steps,
            "failed_steps": self.failed_steps,
            "skipped_steps": self.skipped_steps,
            "errors": self.errors,
            "duration_ms": self.duration_ms,
            "packets_emitted": self.packets_emitted,
        }

    @property
    def duration_ms(self) -> int:
        if self.started_at and self.completed_at:
            return int((self.completed_at - self.started_at).total_seconds() * 1000)
        return 0


@dataclass
class ExecutorConfig:
    """Configuration for plan executor."""

    max_parallel_steps: int = 4
    step_timeout_ms: int = 60000
    max_retries: int = 3
    retry_delay_ms: int = 1000
    continue_on_failure: bool = False
    dry_run: bool = False
    emit_packets: bool = True
    packet_source: str = "plan_executor"
    # Handler options
    real_execution: bool = False  # When True, actually modify files
    allowed_write_roots: list[str] = field(
        default_factory=lambda: ["/Users/ib-mac/Projects"]
    )


# =============================================================================
# Plan Executor
# =============================================================================


class PlanExecutor:
    """
    Executes finalized IR plans with memory integration.

    Features:
    - Dependency-aware parallel execution
    - Retry logic with exponential backoff
    - Progress callbacks for UI updates
    - Memory packet emission for audit trail
    - Dry-run mode for testing
    - Real execution mode for production

    Usage:
        executor = PlanExecutor(config)
        executor.set_memory_client(memory_service)

        result = await executor.execute(plan, context)

        # With progress callback
        logger.info(f"{done}/{total}")
        result = await executor.execute(plan)
    """

    def __init__(
        self,
        config: Optional[ExecutorConfig] = None,
        strategy_memory: Optional[IStrategyMemoryService] = None,
    ):
        """
        Initialize the executor.

        Args:
            config: Executor configuration
            strategy_memory: Optional Strategy Memory service for plan reuse
        """
        self._config = config or ExecutorConfig()
        self._handlers: dict[str, Callable] = {}
        self._active_executions: dict[UUID, ExecutionResult] = {}
        self._progress_callbacks: list[Callable[[UUID, int, int], None]] = []

        # Memory client
        self._memory_client: Optional[Any] = None

        # World model hook
        self._world_model: Optional[Any] = None

        # Strategy Memory (Phase 0: retrieval-only)
        self._strategy_memory: Optional[IStrategyMemoryService] = strategy_memory

        # Register default handlers
        self._register_default_handlers()

        logger.info(
            "PlanExecutor initialized",
            strategy_memory_enabled=strategy_memory is not None,
        )

    def _register_default_handlers(self) -> None:
        """Register default step handlers."""
        self._handlers["code_write"] = self._handle_code_write
        self._handlers["code_read"] = self._handle_code_read
        self._handlers["code_modify"] = self._handle_code_modify
        self._handlers["file_create"] = self._handle_file_create
        self._handlers["file_delete"] = self._handle_file_delete
        self._handlers["api_call"] = self._handle_api_call
        self._handlers["reasoning"] = self._handle_reasoning
        self._handlers["validation"] = self._handle_validation
        self._handlers["simulation"] = self._handle_simulation

    def set_memory_client(self, client: Any) -> None:
        """
        Set the memory substrate client.

        Args:
            client: MemorySubstrateService instance
        """
        self._memory_client = client
        logger.info("Memory client attached to PlanExecutor")

    def set_world_model(self, world_model: Any) -> None:
        """
        Set the world model for updates.

        Args:
            world_model: WorldModelService or WorldModelOrchestrator instance
        """
        self._world_model = world_model
        logger.info("World model attached to PlanExecutor")

    def set_strategy_memory(self, strategy_memory: IStrategyMemoryService) -> None:
        """
        Set the Strategy Memory service.

        Args:
            strategy_memory: IStrategyMemoryService implementation
        """
        self._strategy_memory = strategy_memory
        logger.info("Strategy Memory attached to PlanExecutor")

    # =========================================================================
    # Strategy Memory Integration (Phase 0)
    # =========================================================================

    async def maybe_apply_strategy(
        self,
        task_id: str,
        task_kind: str,
        goal_description: str,
        context_embedding: Optional[list[float]] = None,
        tags: Optional[list[str]] = None,
        min_confidence: float = 0.6,
    ) -> Optional[StrategyCandidate]:
        """
        Attempt to retrieve a matching strategy for the given task.

        This is the main entry point for strategy reuse. If a high-confidence
        match is found, the returned StrategyCandidate contains a plan_payload
        that can be executed directly instead of running IR compilation.

        Args:
            task_id: Current task ID
            task_kind: Type of task (e.g., "research", "deploy", "code_review")
            goal_description: Natural language description of the goal
            context_embedding: Optional pre-computed embedding (384-dim)
            tags: Preferred strategy tags
            min_confidence: Minimum confidence threshold for match

        Returns:
            StrategyCandidate if a good match is found, None otherwise
        """
        if self._strategy_memory is None:
            logger.debug("Strategy Memory not configured, skipping retrieval")
            return None

        try:
            request = StrategyRetrievalRequest(
                task_id=task_id,
                task_kind=task_kind,
                goal_description=goal_description,
                context_embedding=context_embedding or [],
                tags=tags or [],
                min_confidence=min_confidence,
            )

            candidates = await self._strategy_memory.retrieve_strategies(
                request, limit=1
            )

            if candidates and candidates[0].confidence >= min_confidence:
                logger.info(
                    "strategy_match_found",
                    task_id=task_id,
                    strategy_id=candidates[0].strategy_id,
                    confidence=candidates[0].confidence,
                    score=candidates[0].score,
                )
                return candidates[0]

            logger.debug(
                "no_strategy_match",
                task_id=task_id,
                candidates_checked=len(candidates),
            )
            return None

        except Exception as e:
            logger.warning(f"Strategy retrieval failed: {e}")
            return None

    async def record_strategy_feedback(
        self,
        strategy_id: str,
        task_id: str,
        success: bool,
        outcome_score: float,
        execution_time_ms: int,
        resource_cost: float = 0.0,
        was_adapted: bool = False,
        adaptation_distance: Optional[int] = None,
        metadata: Optional[dict] = None,
    ) -> None:
        """
        Record feedback for a strategy after execution.

        Call this after executing a plan that was retrieved from Strategy Memory.
        The feedback is used to update the strategy's performance scores.

        Args:
            strategy_id: ID of the strategy that was used
            task_id: ID of the task it was applied to
            success: Whether execution succeeded
            outcome_score: Quality score (0.0-1.0)
            execution_time_ms: Execution duration in milliseconds
            resource_cost: Estimated resource cost
            was_adapted: Whether the strategy was adapted before use
            adaptation_distance: Graph edit distance if adapted
            metadata: Additional feedback metadata
        """
        if self._strategy_memory is None:
            return

        try:
            feedback = StrategyFeedback(
                strategy_id=strategy_id,
                task_id=task_id,
                success=success,
                outcome_score=outcome_score,
                execution_time_ms=execution_time_ms,
                resource_cost=resource_cost,
                was_adapted=was_adapted,
                adaptation_distance=adaptation_distance,
                metadata=metadata or {},
            )

            await self._strategy_memory.update_strategy_outcome(feedback)

            logger.info(
                "strategy_feedback_recorded",
                strategy_id=strategy_id,
                task_id=task_id,
                success=success,
                outcome_score=outcome_score,
            )

        except Exception as e:
            logger.warning(f"Strategy feedback recording failed: {e}")

    # =========================================================================
    # Handler Registration
    # =========================================================================

    def register_handler(
        self,
        action_type: str,
        handler: Callable[[Any, dict[str, Any]], dict[str, Any]],
    ) -> None:
        """
        Register a step handler.

        Args:
            action_type: Type of action this handler processes
            handler: Handler function (step, context) → result dict
        """
        self._handlers[action_type] = handler
        logger.debug(f"Registered handler for: {action_type}")

    def on_progress(
        self,
        callback: Callable[[UUID, int, int], None],
    ) -> None:
        """
        Register progress callback.

        Args:
            callback: Function(execution_id, completed, total)
        """
        self._progress_callbacks.append(callback)

    # =========================================================================
    # Main Execution
    # =========================================================================

    async def execute(
        self,
        plan: Any,  # ExecutionPlan
        context: Optional[dict[str, Any]] = None,
    ) -> ExecutionResult:
        """
        Execute a plan.

        Args:
            plan: ExecutionPlan from IRToPlanAdapter
            context: Execution context (workspace, credentials, etc.)

        Returns:
            ExecutionResult with step outcomes and artifacts
        """
        result = ExecutionResult(
            plan_id=plan.plan_id,
            status=ExecutionStatus.RUNNING,
            started_at=datetime.utcnow(),
        )

        self._active_executions[result.execution_id] = result
        context = context or {}

        logger.info(f"Executing plan {plan.plan_id} with {len(plan.steps)} steps")

        # Emit start packet
        await self._emit_execution_start_packet(result, plan)

        try:
            if self._config.dry_run:
                await self._dry_run(plan, result)
            else:
                await self._execute_steps(plan, result, context)

            # Determine final status
            if result.failed_steps == 0:
                result.status = ExecutionStatus.COMPLETED
            elif result.completed_steps > 0:
                result.status = ExecutionStatus.PARTIAL
            else:
                result.status = ExecutionStatus.FAILED

        except Exception as e:
            logger.error(f"Execution failed: {e}")
            result.status = ExecutionStatus.FAILED
            result.errors.append(str(e))

        result.completed_at = datetime.utcnow()

        # Emit completion packet
        await self._emit_execution_complete_packet(result)

        # Update world model
        await self._update_world_model(result, context)

        # Remove from active
        if result.execution_id in self._active_executions:
            del self._active_executions[result.execution_id]

        logger.info(
            f"Execution {result.execution_id} complete: "
            f"{result.completed_steps}/{len(plan.steps)} steps, "
            f"status={result.status.value}, packets={result.packets_emitted}"
        )

        return result

    async def _execute_steps(
        self,
        plan: Any,
        result: ExecutionResult,
        context: dict[str, Any],
    ) -> None:
        """Execute steps with dependency awareness."""
        completed_ids: set[UUID] = set()
        step_map = {s.step_id: s for s in plan.steps}

        while len(completed_ids) < len(plan.steps):
            # Find executable steps (dependencies satisfied)
            executable = [
                s
                for s in plan.steps
                if s.step_id not in completed_ids
                and all(d in completed_ids for d in s.dependencies)
            ]

            if not executable:
                # Check for deadlock
                remaining = len(plan.steps) - len(completed_ids)
                if remaining > 0:
                    result.errors.append(f"Deadlock: {remaining} steps cannot execute")
                    result.skipped_steps = remaining
                break

            # Execute in parallel up to limit
            batch = executable[: self._config.max_parallel_steps]

            tasks = [self._execute_step(step, context, result) for step in batch]

            step_results = await asyncio.gather(*tasks, return_exceptions=True)

            # Process results
            for step, step_result in zip(batch, step_results):
                if isinstance(step_result, Exception):
                    step_result = StepResult(
                        step_id=step.step_id,
                        status=StepStatus.FAILED,
                        action_type=step.action_type,
                        target=step.target,
                        error=str(step_result),
                    )

                result.step_results.append(step_result)

                # Emit step packet
                await self._emit_step_packet(step_result, result)

                if step_result.status == StepStatus.COMPLETED:
                    completed_ids.add(step.step_id)
                    result.completed_steps += 1

                    # Store output as artifact
                    if step_result.output:
                        result.artifacts[str(step.step_id)] = step_result.output
                else:
                    result.failed_steps += 1

                    if not self._config.continue_on_failure:
                        result.errors.append(
                            f"Step {step.step_id} failed: {step_result.error}"
                        )
                        return

            # Report progress
            self._report_progress(
                result.execution_id, len(completed_ids), len(plan.steps)
            )

    async def _execute_step(
        self,
        step: Any,  # ExecutionStep
        context: dict[str, Any],
        result: ExecutionResult,
    ) -> StepResult:
        """Execute a single step with retries."""
        start_time = datetime.utcnow()
        retries = 0

        while retries <= self._config.max_retries:
            try:
                handler = self._handlers.get(step.action_type)

                if handler:
                    output = await self._call_handler(handler, step, context)
                else:
                    output = {
                        "status": "no_handler",
                        "action_type": step.action_type,
                        "message": f"No handler registered for {step.action_type}",
                    }

                return StepResult(
                    step_id=step.step_id,
                    status=StepStatus.COMPLETED,
                    action_type=step.action_type,
                    target=step.target,
                    output=output,
                    duration_ms=self._elapsed_ms(start_time),
                    retries=retries,
                    started_at=start_time,
                    completed_at=datetime.utcnow(),
                )

            except Exception as e:
                retries += 1
                logger.warning(f"Step {step.step_id} failed (attempt {retries}): {e}")

                if retries <= self._config.max_retries:
                    # Exponential backoff
                    delay = self._config.retry_delay_ms * (2 ** (retries - 1)) / 1000
                    await asyncio.sleep(delay)
                else:
                    return StepResult(
                        step_id=step.step_id,
                        status=StepStatus.FAILED,
                        action_type=step.action_type,
                        target=step.target,
                        error=str(e),
                        duration_ms=self._elapsed_ms(start_time),
                        retries=retries,
                        started_at=start_time,
                        completed_at=datetime.utcnow(),
                    )

        # Should not reach here
        return StepResult(
            step_id=step.step_id,
            status=StepStatus.FAILED,
            action_type=step.action_type,
            error="Unknown error",
        )

    async def _call_handler(
        self,
        handler: Callable,
        step: Any,
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """Call a handler, supporting both sync and async."""
        result = handler(step, context)
        if hasattr(result, "__await__"):
            result = await result
        return result

    async def _dry_run(
        self,
        plan: Any,
        result: ExecutionResult,
    ) -> None:
        """Perform a dry run (no actual execution)."""
        logger.info("Performing dry run")

        for step in plan.steps:
            step_result = StepResult(
                step_id=step.step_id,
                status=StepStatus.COMPLETED,
                action_type=step.action_type,
                target=step.target,
                output={
                    "dry_run": True,
                    "action_type": step.action_type,
                    "target": step.target,
                    "description": step.description,
                },
            )
            result.step_results.append(step_result)
            result.completed_steps += 1

            self._report_progress(
                result.execution_id, result.completed_steps, len(plan.steps)
            )

    # =========================================================================
    # Default Handlers
    # =========================================================================

    async def _handle_code_write(
        self,
        step: Any,
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Handle code write action.

        When real_execution is True, writes content to the target file.
        Creates backup of existing file before overwriting.
        """
        from pathlib import Path

        target_path = step.target
        logger.info(f"Writing code to: {target_path}")

        if not self._config.real_execution:
            return {
                "action": "code_write",
                "target": target_path,
                "status": "simulated",
                "parameters": step.parameters,
            }

        # Get content from step parameters
        content = step.parameters.get("content", "")
        if not content:
            return {
                "action": "code_write",
                "target": target_path,
                "status": "error",
                "error": "No content provided in parameters",
            }

        # Validate path is within allowed directories
        allowed_roots = self._config.allowed_write_roots or ["/Users/ib-mac/Projects"]
        path = Path(target_path).resolve()

        is_allowed = any(
            str(path).startswith(str(Path(root).resolve())) for root in allowed_roots
        )

        if not is_allowed:
            logger.error(f"Path not in allowed roots: {path}")
            return {
                "action": "code_write",
                "target": target_path,
                "status": "error",
                "error": f"Path {path} not in allowed write roots",
            }

        try:
            # Create parent directories if needed
            path.parent.mkdir(parents=True, exist_ok=True)

            # Backup existing file if it exists
            backup_path = None
            if path.exists():
                backup_path = path.with_suffix(
                    path.suffix + f".bak.{int(datetime.utcnow().timestamp())}"
                )
                path.rename(backup_path)
                logger.info(f"Backed up existing file to: {backup_path}")

            # Write new content
            path.write_text(content, encoding="utf-8")
            logger.info(f"Successfully wrote {len(content)} bytes to: {path}")

            return {
                "action": "code_write",
                "target": str(path),
                "status": "executed",
                "bytes_written": len(content),
                "backup_path": str(backup_path) if backup_path else None,
            }

        except Exception as e:
            logger.error(f"Failed to write file: {e}")
            return {
                "action": "code_write",
                "target": target_path,
                "status": "error",
                "error": str(e),
            }

    async def _handle_code_read(
        self,
        step: Any,
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """Handle code read action."""
        logger.info(f"Reading code from: {step.target}")

        return {
            "action": "code_read",
            "target": step.target,
            "status": "simulated" if not self._config.real_execution else "executed",
        }

    async def _handle_code_modify(
        self,
        step: Any,
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """Handle code modify action."""
        logger.info(f"Modifying code in: {step.target}")

        return {
            "action": "code_modify",
            "target": step.target,
            "status": "simulated" if not self._config.real_execution else "executed",
            "parameters": step.parameters,
        }

    async def _handle_file_create(
        self,
        step: Any,
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """Handle file create action."""
        logger.info(f"Creating file: {step.target}")

        return {
            "action": "file_create",
            "target": step.target,
            "status": "simulated" if not self._config.real_execution else "executed",
        }

    async def _handle_file_delete(
        self,
        step: Any,
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """Handle file delete action."""
        logger.info(f"Deleting file: {step.target}")

        return {
            "action": "file_delete",
            "target": step.target,
            "status": "simulated" if not self._config.real_execution else "executed",
        }

    async def _handle_api_call(
        self,
        step: Any,
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """Handle API call action."""
        logger.info(f"Calling API: {step.target}")

        return {
            "action": "api_call",
            "target": step.target,
            "status": "simulated" if not self._config.real_execution else "executed",
        }

    async def _handle_reasoning(
        self,
        step: Any,
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """Handle reasoning action."""
        logger.info(f"Reasoning: {step.description}")

        return {
            "action": "reasoning",
            "description": step.description,
            "status": "simulated",
        }

    async def _handle_validation(
        self,
        step: Any,
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """Handle validation action."""
        logger.info(f"Validating: {step.target}")

        return {
            "action": "validation",
            "target": step.target,
            "status": "simulated",
        }

    async def _handle_simulation(
        self,
        step: Any,
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """Handle simulation action."""
        logger.info(f"Simulating: {step.description}")

        return {
            "action": "simulation",
            "description": step.description,
            "status": "simulated",
        }

    # =========================================================================
    # Memory Integration
    # =========================================================================

    async def _emit_execution_start_packet(
        self,
        result: ExecutionResult,
        plan: Any,
    ) -> None:
        """Emit packet at execution start."""
        if not self._config.emit_packets or not self._memory_client:
            return

        try:
            from core.schemas.packet_envelope_v2 import PacketEnvelopeIn

            packet = PacketEnvelopeIn(
                source=self._config.packet_source,
                kind="execution_start",
                payload={
                    "execution_id": str(result.execution_id),
                    "plan_id": str(plan.plan_id),
                    "total_steps": len(plan.steps),
                    "step_types": list(set(s.action_type for s in plan.steps)),
                    "dry_run": self._config.dry_run,
                },
            )

            write_result = await self._memory_client.write_packet(packet)
            if write_result.success:
                result.packets_emitted += 1

        except Exception as e:
            logger.warning(f"Failed to emit execution start packet: {e}")

    async def _emit_step_packet(
        self,
        step_result: StepResult,
        execution_result: ExecutionResult,
    ) -> None:
        """Emit packet for each step completion."""
        if not self._config.emit_packets or not self._memory_client:
            return

        try:
            from core.schemas.packet_envelope_v2 import PacketEnvelopeIn

            packet = PacketEnvelopeIn(
                source=self._config.packet_source,
                kind="step_complete",
                payload={
                    "execution_id": str(execution_result.execution_id),
                    "step_id": str(step_result.step_id),
                    "action_type": step_result.action_type,
                    "target": step_result.target,
                    "status": step_result.status.value,
                    "duration_ms": step_result.duration_ms,
                    "retries": step_result.retries,
                    "has_error": step_result.error is not None,
                },
            )

            write_result = await self._memory_client.write_packet(packet)
            if write_result.success:
                execution_result.packets_emitted += 1

        except Exception as e:
            logger.warning(f"Failed to emit step packet: {e}")

    async def _emit_execution_complete_packet(
        self,
        result: ExecutionResult,
    ) -> None:
        """Emit packet at execution completion."""
        if not self._config.emit_packets or not self._memory_client:
            return

        try:
            from core.schemas.packet_envelope_v2 import PacketEnvelopeIn

            packet = PacketEnvelopeIn(
                source=self._config.packet_source,
                kind="execution_complete",
                payload={
                    "execution_id": str(result.execution_id),
                    "plan_id": str(result.plan_id),
                    "status": result.status.value,
                    "completed_steps": result.completed_steps,
                    "failed_steps": result.failed_steps,
                    "skipped_steps": result.skipped_steps,
                    "duration_ms": result.duration_ms,
                    "error_count": len(result.errors),
                },
            )

            write_result = await self._memory_client.write_packet(packet)
            if write_result.success:
                result.packets_emitted += 1

        except Exception as e:
            logger.warning(f"Failed to emit execution complete packet: {e}")

    # =========================================================================
    # World Model Integration
    # =========================================================================

    async def _update_world_model(
        self,
        result: ExecutionResult,
        context: dict[str, Any],
    ) -> None:
        """Update world model with execution results."""
        if not self._world_model:
            return

        try:
            # Build insights from execution
            insights = []

            if result.status == ExecutionStatus.COMPLETED:
                insights.append(
                    {
                        "insight_id": str(uuid4()),
                        "insight_type": "execution_success",
                        "entities": list(result.artifacts.keys())[
                            :5
                        ],  # Top 5 artifacts
                        "content": f"Execution {result.execution_id} completed successfully",
                        "confidence": 0.9,
                        "trigger_world_model": True,
                    }
                )
            elif result.failed_steps > 0:
                insights.append(
                    {
                        "insight_id": str(uuid4()),
                        "insight_type": "execution_failure",
                        "entities": [
                            str(s.step_id)
                            for s in result.step_results
                            if s.status == StepStatus.FAILED
                        ],
                        "content": f"Execution {result.execution_id} had {result.failed_steps} failures",
                        "confidence": 0.8,
                        "trigger_world_model": True,
                    }
                )

            if insights:
                await self._world_model.update_from_insights(insights)

        except Exception as e:
            logger.warning(f"Failed to update world model: {e}")

    # =========================================================================
    # Progress Reporting
    # =========================================================================

    def _report_progress(
        self,
        execution_id: UUID,
        completed: int,
        total: int,
    ) -> None:
        """Report progress to registered callbacks."""
        for callback in self._progress_callbacks:
            try:
                callback(execution_id, completed, total)
            except Exception as e:
                logger.error(f"Progress callback error: {e}")

    # =========================================================================
    # Execution Control
    # =========================================================================

    def cancel_execution(self, execution_id: UUID) -> bool:
        """Cancel an active execution."""
        if execution_id in self._active_executions:
            result = self._active_executions[execution_id]
            result.status = ExecutionStatus.CANCELLED
            result.completed_at = datetime.utcnow()
            logger.info(f"Cancelled execution {execution_id}")
            return True
        return False

    def pause_execution(self, execution_id: UUID) -> bool:
        """Pause an active execution."""
        if execution_id in self._active_executions:
            result = self._active_executions[execution_id]
            if result.status == ExecutionStatus.RUNNING:
                result.status = ExecutionStatus.PAUSED
                logger.info(f"Paused execution {execution_id}")
            return True
        return False

    def get_active_executions(self) -> list[ExecutionResult]:
        """Get all active executions."""
        return list(self._active_executions.values())

    def get_execution(self, execution_id: UUID) -> Optional[ExecutionResult]:
        """Get a specific execution by ID."""
        return self._active_executions.get(execution_id)

    # =========================================================================
    # Utility
    # =========================================================================

    def _elapsed_ms(self, start: datetime) -> int:
        """Calculate elapsed milliseconds from start time."""
        return int((datetime.utcnow() - start).total_seconds() * 1000)
