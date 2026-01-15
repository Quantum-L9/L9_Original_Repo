"""
L9 Core Agents - Agent Executor Service
========================================

The Agent Executor is the heart of the agentic system, orchestrating agent
instantiation, tool binding, and the execution loop.

Key responsibilities:
- Instantiate agents based on registered configurations
- Bind governance-approved tools to agent instances
- Run the execution loop (reasoning <-> tool_use state machine)
- Dispatch tool calls through the tool registry
- Store reasoning traces and results via memory substrate

This module does NOT:
- Define agent personalities or core reasoning (AIOS does that)
- Approve or deny tool usage (Governance Engine does that)
- Create new database tables

Version: 1.0.0
"""

from __future__ import annotations

import json
import os
import structlog
from datetime import datetime
from typing import Any, Dict, List, Optional, Protocol
from uuid import UUID, uuid4

from core.agents.schemas import (
    AgentTask,
    AgentConfig,
    AIOSResult,
    AIOSResultType,
    ExecutorState,
    ExecutionResult,
    DuplicateTaskResponse,
    ToolCallRequest,
    ToolCallResult,
    ToolBinding,
)
from core.agents.agent_instance import AgentInstance
from core.schemas import PacketEnvelopeIn
from memory.agent_persistence import AgentPersistenceService
from core.governance.approvals import ApprovalManager
from core.tools.tool_graph import ToolGraph
from core.worldmodel.insight_emitter import get_insight_emitter
from runtime.dora import emit_executor_trace
from core.observability.circuit_breaker import CircuitBreaker, CircuitBreakerConfig

# Initialize logger early for import error handling
logger = structlog.get_logger(__name__)

# Self-reflection imports (optional - graceful degradation if not available)
try:
    from core.agents.selfreflection import (
        TaskExecutionContext,
        analyze_task_execution,
    )
    from core.agents.kernelevolution import create_evolution_plan

    _has_self_reflection = True
except ImportError:
    _has_self_reflection = False

# Prompt defense imports (GMP-60: Runtime hardening)
try:
    from core.agents.prompt_defense import (
        detect_prompt_injection,
        should_block_request,
        get_blocked_response,
        InjectionDetectionResult,
    )

    _has_prompt_defense = True
except ImportError:
    _has_prompt_defense = False
    logger.warning("prompt_defense not available - injection detection disabled")

# Kernel-aware prompt builder (GMP-60: Runtime hardening)
try:
    from core.agents.prompt_builder import (
        build_kernel_system_prompt,
        build_runtime_prompt,
    )

    _has_prompt_builder = True
except ImportError:
    _has_prompt_builder = False
    logger.warning("prompt_builder not available - kernel prompts disabled")


# =============================================================================
# Reactive Task Generation
# =============================================================================


async def _generate_tasks_from_query(query: str) -> List[Dict[str, Any]]:
    """
    Parse user requests into task specifications.

    Analyzes query text, extracts intent, and generates task specs.

    Args:
        query: User query text

    Returns:
        List of task spec dicts with: name, payload, handler, priority
    """
    if not query or not query.strip():
        return []

    query_lower = query.lower().strip()
    task_specs = []

    # Simple intent detection (can be enhanced with LLM in future)
    if "gmp" in query_lower or "governance" in query_lower:
        # GMP task
        task_specs.append(
            {
                "name": f"GMP Run: {query[:50]}",
                "payload": {
                    "type": "gmp_run",
                    "query": query,
                    "status": "pending_igor_approval",
                },
                "handler": "gmp_worker",
                "priority": 5,
            }
        )
    elif "git" in query_lower or "commit" in query_lower:
        # Git commit task
        task_specs.append(
            {
                "name": f"Git Commit: {query[:50]}",
                "payload": {
                    "type": "git_commit",
                    "query": query,
                    "status": "pending_igor_approval",
                },
                "handler": "git_worker",
                "priority": 5,
            }
        )
    elif "plan" in query_lower or "long" in query_lower:
        # Long plan task
        task_specs.append(
            {
                "name": f"Long Plan: {query[:50]}",
                "payload": {
                    "type": "long_plan",
                    "goal": query,
                    "status": "pending",
                },
                "handler": "long_plan_worker",
                "priority": 5,
            }
        )
    else:
        # Default: general agent task
        task_specs.append(
            {
                "name": f"Agent Task: {query[:50]}",
                "payload": {
                    "type": "agent_task",
                    "query": query,
                    "status": "pending",
                },
                "handler": "agent_executor",
                "priority": 5,
            }
        )

    logger.info(f"Generated {len(task_specs)} task(s) from query: {query[:100]}")
    return task_specs


# =============================================================================
# Protocol Definitions (Interfaces)
# =============================================================================


class AIOSRuntime(Protocol):
    """Protocol for AIOS runtime interface."""

    async def execute_reasoning(
        self,
        context: dict[str, Any],
    ) -> AIOSResult:
        """
        Execute reasoning with the given context.

        Args:
            context: Context bundle from AgentInstance.assemble_context()

        Returns:
            AIOSResult with response or tool call
        """
        ...


class ToolRegistryProtocol(Protocol):
    """Protocol for tool registry interface."""

    async def dispatch_tool_call(
        self,
        tool_id: str,
        arguments: dict[str, Any],
        context: dict[str, Any],
    ) -> ToolCallResult:
        """
        Dispatch a tool call.

        Args:
            tool_id: Canonical tool identity
            arguments: Arguments for tool
            context: Execution context

        Returns:
            ToolCallResult with result or error (includes tool_id)
        """
        ...

    def get_approved_tools(
        self,
        agent_id: str,
        principal_id: str,
    ) -> list[ToolBinding]:
        """
        Get list of tools approved for an agent.

        Args:
            agent_id: Agent identifier
            principal_id: Principal requesting tools

        Returns:
            List of approved tool bindings
        """
        ...


class SubstrateServiceProtocol(Protocol):
    """Protocol for memory substrate service interface."""

    async def write_packet(
        self,
        packet_in: PacketEnvelopeIn,
    ) -> Any:
        """
        Write a packet to the substrate.

        Args:
            packet_in: Packet envelope to write

        Returns:
            Write result
        """
        ...

    async def search_packets(
        self,
        thread_id: UUID,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """
        Search packets by thread ID.

        Args:
            thread_id: Thread identifier
            limit: Max results

        Returns:
            List of matching packets
        """
        ...

    async def search_packets_by_thread(
        self,
        thread_id: str,
        packet_type: Optional[str] = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """
        Search packets by thread ID with optional packet type filter.

        Args:
            thread_id: Thread identifier (string)
            packet_type: Optional packet type filter
            limit: Max results

        Returns:
            List of matching packets
        """
        ...


class AgentRegistryProtocol(Protocol):
    """Protocol for agent registry interface."""

    def get_agent_config(self, agent_id: str) -> Optional[AgentConfig]:
        """
        Get configuration for an agent.

        Args:
            agent_id: Agent identifier

        Returns:
            AgentConfig or None if not found
        """
        ...

    def agent_exists(self, agent_id: str) -> bool:
        """Check if an agent is registered."""
        ...


# =============================================================================
# Agent Executor Service
# =============================================================================


class AgentExecutorService:
    """
    Service for executing agent tasks.

    Orchestrates the agent execution loop:
    1. Validate and instantiate agent
    2. Bind approved tools
    3. Run reasoning loop until completion or max iterations
    4. Store traces and results

    All dependencies are injected - no singletons.
    """

    def __init__(
        self,
        aios_runtime: AIOSRuntime,
        tool_registry: ToolRegistryProtocol,
        substrate_service: SubstrateServiceProtocol,
        agent_registry: AgentRegistryProtocol,
        default_agent_id: Optional[str] = None,
        max_iterations: Optional[int] = None,
        agent_persistence: Optional[AgentPersistenceService] = None,
    ):
        """
        Initialize the executor service.

        Args:
            aios_runtime: AIOS runtime for reasoning
            tool_registry: Tool registry for dispatching
            substrate_service: Memory substrate for persistence
            agent_registry: Agent registry for configs
            default_agent_id: Default agent ID (from env if not provided)
            max_iterations: Max iterations (from env if not provided)
            agent_persistence: Agent persistence service for checkpoint management
        """
        self._aios_runtime = aios_runtime
        self._tool_registry = tool_registry
        self._substrate_service = substrate_service
        self._agent_registry = agent_registry
        self._agent_persistence = agent_persistence

        # Configuration from env vars (read at init, not import time)
        self._default_agent_id = default_agent_id or os.getenv(
            "DEFAULT_AGENT_ID", "l9-standard-v1"
        )
        self._max_iterations = max_iterations or int(
            os.getenv("AGENT_MAX_ITERATIONS", "10")
        )

        # Idempotency cache
        # LIMITATION: In-memory only - cleared on process restart.
        # NOT durable: If executor restarts, duplicate tasks will re-execute.
        # For substrate-backed idempotency, see roadmap v1.2.
        self._processed_tasks: dict[str, ExecutionResult] = {}

        # Kernel-aware agent reference (for guarded execution)
        self._kernel_aware_agent: Optional[Any] = None

        logger.info(
            "agent.executor.init: default_agent_id=%s, max_iterations=%d, persistence=%s",
            self._default_agent_id,
            self._max_iterations,
            "enabled" if agent_persistence else "disabled",
        )

    def set_kernel_aware_agent(self, agent: Any) -> None:
        """
        Set the kernel-aware agent for guarded execution.

        This should be called after the agent registry initializes L-CTO
        with kernels. The executor will use this agent for kernel-aware
        tool dispatch via guarded_execute.

        Args:
            agent: Kernel-aware agent (must have kernel_state attribute)
        """
        self._kernel_aware_agent = agent
        kernel_state = getattr(agent, "kernel_state", "UNKNOWN")
        kernel_count = len(getattr(agent, "kernels", {}))
        logger.info(
            "agent.executor.kernel_agent_set: state=%s, kernels=%d",
            kernel_state,
            kernel_count,
        )

    async def shutdown(self) -> None:
        """
        Shutdown the executor service, creating checkpoints for agent state.

        Called during server shutdown to persist agent state for recovery.
        Implements memory_spec_v3.0.yaml checkpoint trigger: on_agent_shutdown.
        """
        logger.info("agent.executor.shutdown: starting checkpoint creation")

        if self._agent_persistence is None:
            logger.warning(
                "agent.executor.shutdown: persistence not available, skipping checkpoints"
            )
            return

        try:
            # Create checkpoint for the default agent with executor state
            state = {
                "agent_id": self._default_agent_id,
                "processed_task_count": len(self._processed_tasks),
                "processed_task_ids": list(self._processed_tasks.keys())[
                    -20:
                ],  # Last 20 task IDs
                "max_iterations": self._max_iterations,
                "kernel_agent_state": getattr(
                    self._kernel_aware_agent, "kernel_state", None
                ),
                "shutdown_timestamp": datetime.utcnow().isoformat(),
            }

            checkpoint_id = await self._agent_persistence.create_checkpoint(
                agent_id=self._default_agent_id,
                state=state,
                reason="on_agent_shutdown",
            )

            logger.info(
                "agent.executor.shutdown: checkpoint created",
                checkpoint_id=str(checkpoint_id),
                agent_id=self._default_agent_id,
                task_count=len(self._processed_tasks),
            )

        except Exception as e:
            # Best-effort: don't fail shutdown due to checkpoint failure
            logger.error(
                "agent.executor.shutdown: checkpoint creation failed",
                error=str(e),
                exc_info=True,
            )

    def _get_kernel_aware_agent(self) -> Optional[Any]:
        """
        Get the kernel-aware agent if available and active.

        Returns:
            Agent with active kernels, or None if not available
        """
        if self._kernel_aware_agent is None:
            return None

        kernel_state = getattr(self._kernel_aware_agent, "kernel_state", None)
        if kernel_state != "ACTIVE":
            return None

        return self._kernel_aware_agent

    # =========================================================================
    # Public API
    # =========================================================================

    async def start_agent_task(
        self,
        task: AgentTask,
    ) -> ExecutionResult | DuplicateTaskResponse:
        """
        Start executing an agent task.

        This is the main entry point for task execution.

        Args:
            task: The task to execute

        Returns:
            ExecutionResult or DuplicateTaskResponse if duplicate
        """
        start_time = datetime.utcnow()
        task_id_str = str(task.id)

        # Log start
        logger.info(
            "agent.executor.start: task_id=%s, agent_id=%s, thread_id=%s",
            task_id_str,
            task.agent_id,
            str(task.get_thread_id()),
        )

        # Idempotency check
        dedupe_key = task.get_dedupe_key()
        if dedupe_key in self._processed_tasks:
            logger.info("agent.executor.duplicate: task_id=%s", task_id_str)
            return DuplicateTaskResponse(task_id=task.id)

        try:
            # Validate task
            validation_error = self._validate_task(task)
            if validation_error:
                return await self._handle_error(
                    task,
                    validation_error,
                    start_time,
                    "validation_failed",
                )

            # Prompt injection defense (GMP-60)
            if _has_prompt_defense:
                user_message = task.payload.get("message", "") if task.payload else ""
                injection_result = detect_prompt_injection(
                    user_message,
                    context={
                        "task_id": task_id_str,
                        "agent_id": task.agent_id,
                        "source_id": task.source_id,
                    },
                )

                if should_block_request(injection_result):
                    # Emit violation packet
                    await self._emit_packet(
                        packet_type="agent.executor.violation",
                        payload={
                            "event": "prompt_injection_blocked",
                            "task_id": task_id_str,
                            "agent_id": task.agent_id,
                            "severity": injection_result.severity.value
                            if injection_result.severity
                            else "unknown",
                            "patterns": injection_result.patterns_matched,
                            "redacted_input": injection_result.redacted_input,
                        },
                        thread_id=task.get_thread_id(),
                    )

                    logger.warning(
                        "agent.executor.prompt_injection_blocked",
                        task_id=task_id_str,
                        severity=injection_result.severity.value
                        if injection_result.severity
                        else "unknown",
                        patterns=injection_result.patterns_matched,
                    )

                    # Return blocked response
                    blocked_message = get_blocked_response(injection_result)
                    return ExecutionResult(
                        task_id=task.id,
                        status="blocked",
                        result=blocked_message,
                        iterations=0,
                        duration_ms=int(
                            (datetime.utcnow() - start_time).total_seconds() * 1000
                        ),
                        error="Prompt injection detected",
                    )

            # Instantiate agent
            instance = await self._instantiate_agent(task)
            if instance is None:
                return await self._handle_error(
                    task,
                    f"Agent not found: {task.agent_id}",
                    start_time,
                    "agent_not_found",
                )

            # Emit start packet (with agent_id in payload for metadata extraction)
            await self._emit_packet(
                packet_type="agent.executor.trace",
                payload={
                    "event": "start",
                    "task_id": task_id_str,
                    "agent_id": task.agent_id,  # Used to set metadata.agent
                    "iteration": 0,
                },
                thread_id=task.get_thread_id(),
            )

            # Run execution loop
            result = await self._run_execution_loop(instance)

            # Cache result for idempotency
            self._processed_tasks[dedupe_key] = result

            # Emit result packet (with agent_id in payload for metadata extraction)
            await self._emit_packet(
                packet_type="agent.executor.result",
                payload={
                    "task_id": task_id_str,
                    "agent_id": task.agent_id,  # Used to set metadata.agent
                    "status": result.status,
                    "iterations": result.iterations,
                    "duration_ms": result.duration_ms,
                    "error": result.error,
                },
                thread_id=task.get_thread_id(),
            )

            # Log completion
            log_level = "info" if result.status == "completed" else "error"
            event_name = "success" if result.status == "completed" else "error"
            getattr(logger, log_level)(
                "agent.executor.finish.%s: task_id=%s, total_iterations=%d, duration_ms=%d, error=%s",
                event_name,
                task_id_str,
                result.iterations,
                result.duration_ms,
                result.error,
            )

            # Emit DORA trace block (auto-updates on every execution)
            await emit_executor_trace(
                task_id=task_id_str,
                task_name=getattr(task, "name", None) or f"task_{task.kind.value}",
                agent_id=task.agent_id,
                inputs={"query": task.payload.get("query", "") if task.payload else ""},
                outputs={
                    "status": result.status,
                    "iterations": result.iterations,
                    "result": str(result.result)[:500] if result.result else None,
                },
                duration_ms=result.duration_ms,
                errors=[result.error] if result.error else None,
                patterns=["agent_execution", "reasoning_loop"],
            )

            # Active memory encoding hook (GMP-80-A7: Frontier Memory)
            # System automatically extracts and encodes learnings from task outcomes
            await self._run_active_memory_encoding(task, result, instance)

            # Self-reflection hook (v3.4+ / GMP-KERNEL-BOOT)
            # Analyze task execution for behavioral gaps
            if _has_self_reflection:
                await self._run_self_reflection(task, result, instance)

            return result

        except Exception as e:
            logger.exception(
                "agent.executor.finish.error: task_id=%s, error=%s",
                task_id_str,
                str(e),
            )
            return await self._handle_error(
                task,
                str(e),
                start_time,
                "execution_error",
            )

    async def _bind_memory_context(self, task_id: str, agent_id: str) -> Dict[str, Any]:
        """
        Load and inject memory state into executor.

        Retrieves task context from memory substrate (Postgres/Redis) and
        returns context dict for use in task execution.

        Args:
            task_id: Task identifier
            agent_id: Agent identifier

        Returns:
            Context dict with memory state (governance rules, project history, etc.)
        """
        context = {}

        try:
            # Try to get task context from Redis cache first
            from runtime.redis_client import get_redis_client

            redis_client = await get_redis_client()
            if redis_client and redis_client.is_available():
                cached_context = await redis_client.get_task_context(task_id)
                if cached_context:
                    context.update(cached_context)
                    logger.debug(f"Loaded task context from Redis cache: {task_id}")

            # Load from memory substrate (Postgres)
            if self._substrate_service:
                # Search for task-related packets
                packets = await self._substrate_service.search_packets_by_thread(
                    thread_id=task_id,
                    packet_type="task_execution",
                    limit=10,
                )

                if packets:
                    # Extract context from recent packets
                    for packet in packets[-5:]:  # Last 5 packets
                        payload = packet.get("payload", {})
                        if payload:
                            context.setdefault("history", []).append(payload)

                    logger.debug(
                        f"Loaded {len(packets)} packets for task context: {task_id}"
                    )

            # Load governance rules and project history via memory_helpers
            # Safe import pattern: gracefully handle missing module
            try:
                from runtime.memory_helpers import (
                    memory_search,
                    MEMORY_SEGMENT_GOVERNANCE_META,
                    MEMORY_SEGMENT_PROJECT_HISTORY,
                )

                _has_memory_helpers = True
            except ImportError:
                _has_memory_helpers = False
                logger.debug(
                    "memory_helpers not available - skipping governance/history context"
                )

            if _has_memory_helpers:
                try:
                    governance_rules = await memory_search(
                        segment=MEMORY_SEGMENT_GOVERNANCE_META,
                        query=f"task {task_id}",
                        agent_id=agent_id,
                        top_k=5,
                    )
                    if governance_rules:
                        context["governance_rules"] = governance_rules

                    project_history = await memory_search(
                        segment=MEMORY_SEGMENT_PROJECT_HISTORY,
                        query=f"task {task_id}",
                        agent_id=agent_id,
                        top_k=5,
                    )
                    if project_history:
                        context["project_history"] = project_history
                except Exception as e:
                    logger.warning(
                        f"Failed to load memory segments for task {task_id}: {e}"
                    )

        except Exception as e:
            logger.warning(f"Failed to bind memory context for task {task_id}: {e}")

        return context

    async def _persist_task_result(self, task_id: str, result: dict) -> bool:
        """
        Write execution results to Postgres via memory substrate.

        Persists task execution results to memory substrate for later retrieval.

        Args:
            task_id: Task identifier
            result: Execution result dict with status, iterations, duration_ms, error, etc.

        Returns:
            True if persisted successfully, False otherwise
        """
        if not self._substrate_service:
            logger.warning(
                "Memory substrate service not available - cannot persist task result"
            )
            return False

        try:
            from core.schemas import PacketEnvelopeIn

            # Write task result packet
            packet = PacketEnvelopeIn(
                packet_type="task_execution_result",
                agent_id=result.get("agent_id", "L"),
                payload={
                    "task_id": task_id,
                    "status": result.get("status", "unknown"),
                    "iterations": result.get("iterations", 0),
                    "duration_ms": result.get("duration_ms", 0),
                    "error": result.get("error"),
                    "completed_at": result.get("completed_at"),
                },
            )

            write_result = await self._substrate_service.write_packet(packet)

            if write_result.success:
                logger.info(f"Persisted task result to memory substrate: {task_id}")

                # Also cache in Redis for fast retrieval
                try:
                    from runtime.redis_client import get_redis_client

                    redis_client = await get_redis_client()
                    if redis_client and redis_client.is_available():
                        await redis_client.set_task_context(
                            task_id, result, ttl=3600
                        )  # 1 hour TTL
                except Exception as e:
                    logger.warning(f"Failed to cache task result in Redis: {e}")

                return True
            else:
                logger.warning(f"Failed to persist task result: {task_id}")
                return False

        except Exception as e:
            logger.error(f"Error persisting task result {task_id}: {e}", exc_info=True)
            return False

    async def _reactive_dispatch_loop(self) -> None:
        """
        Continuously process user messages and execute generated tasks.

        Reactive dispatch loop that polls for user messages, generates tasks,
        and dispatches them immediately with approval gate enforcement.
        """
        import asyncio
        from runtime.task_queue import dispatch_task_immediate, QueuedTask
        from core.governance.approvals import ApprovalManager
        from uuid import uuid4

        logger.info("Reactive dispatch loop started")
        approval_manager = ApprovalManager(self._substrate_service)

        # Message queue (in-memory for now, could be Redis-backed)
        message_queue = []

        while True:
            try:
                # Poll for messages (placeholder - would integrate with actual message source)
                # For now, this is a stub that can be extended
                await asyncio.sleep(1.0)  # Poll interval

                # Process any pending messages
                while message_queue:
                    message = message_queue.pop(0)

                    # Generate tasks from query
                    task_specs = await _generate_tasks_from_query(message)

                    for spec in task_specs:
                        # Check if task requires approval
                        task_type = spec["payload"].get("type", "")
                        if task_type in ["gmp_run", "git_commit"]:
                            # High-risk task - check approval
                            task_id = str(uuid4())
                            is_approved = await approval_manager.is_approved(task_id)

                            if not is_approved:
                                logger.info(
                                    f"Task {task_id} requires approval, skipping immediate dispatch"
                                )
                                continue

                        # Dispatch immediately
                        task = QueuedTask(
                            task_id=str(uuid4()),
                            name=spec["name"],
                            payload=spec["payload"],
                            handler=spec["handler"],
                            agent_id="L",
                            priority=spec.get("priority", 5),
                            tags=["reactive"],
                        )

                        await dispatch_task_immediate(task)
                        logger.info(f"Dispatched reactive task {task.task_id}")

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in reactive dispatch loop: {e}", exc_info=True)
                await asyncio.sleep(1.0)

        logger.info("Reactive dispatch loop stopped")

    # =========================================================================
    # Validation
    # =========================================================================

    def _validate_task(self, task: AgentTask) -> Optional[str]:
        """
        Validate an incoming task. Does NOT mutate the task object.

        Args:
            task: Task to validate (read-only)

        Returns:
            Error message or None if valid
        """
        # Check task has valid ID and kind
        if not task.id:
            return "Task ID is required"

        if not task.kind:
            return "Task kind is required"

        # Check agent ID - reject if missing (no silent patching)
        if not task.agent_id:
            return (
                f"agent_id is required (hint: use default '{self._default_agent_id}')"
            )

        # Verify agent exists
        if not self._agent_registry.agent_exists(task.agent_id):
            return f"Agent not registered: {task.agent_id}"

        return None

    # =========================================================================
    # Agent Instantiation
    # =========================================================================

    async def _instantiate_agent(self, task: AgentTask) -> Optional[AgentInstance]:
        """
        Instantiate an agent for the given task.

        Args:
            task: Task to execute

        Returns:
            AgentInstance or None if agent not found
        """
        # Get agent config from registry
        config = self._agent_registry.get_agent_config(task.agent_id)
        if config is None:
            logger.error("agent_id_not_found: agent_id=%s", task.agent_id)
            return None

        # Bind governance-approved tools
        approved_tools = self._tool_registry.get_approved_tools(
            agent_id=task.agent_id,
            principal_id=task.source_id,
        )

        # Update config with approved tools
        config.tools = approved_tools

        # Create instance
        instance = AgentInstance(config=config, task=task)

        # Inject kernel-aware system prompt if available (GMP-60)
        if _has_prompt_builder and self._kernel_aware_agent:
            kernel_state = getattr(self._kernel_aware_agent, "kernel_state", None)
            if kernel_state == "ACTIVE":
                kernel_prompt = build_kernel_system_prompt(self._kernel_aware_agent)

                # Build runtime context from task
                memory_context = task.context or {}
                runtime_prompt = build_runtime_prompt(
                    task_payload=task.payload or {},
                    memory_context=memory_context,
                    channel=task.source_id,
                )

                # Combine kernel prompt with existing system prompt
                existing_prompt = config.system_prompt or ""
                full_prompt = kernel_prompt + runtime_prompt + "\n\n" + existing_prompt
                config.system_prompt = full_prompt

                logger.info(
                    "agent.executor.kernel_prompt_injected",
                    agent_id=task.agent_id,
                    kernel_count=len(getattr(self._kernel_aware_agent, "kernels", {})),
                )

        # Load context from previous thread if exists
        await self._hydrate_context(instance)

        return instance

    async def _hydrate_context(self, instance: AgentInstance) -> None:
        """
        Hydrate agent context from thread history.

        Behavior:
        - Searches substrate for previous thread packets
        - Injects last 5 relevant packets as system context (bounded)
        - Logs if search fails (does not block execution)

        Args:
            instance: Agent instance to hydrate
        """
        # Max packets to inject for context (bounded to prevent context overflow)
        MAX_CONTEXT_PACKETS = 5

        try:
            # Search for previous packets in this thread
            history = await self._substrate_service.search_packets(
                thread_id=instance.thread_id,
                limit=50,
            )

            if history:
                # Filter to relevant packet types for context
                relevant_types = {
                    "agent.executor.result",
                    "agent.executor.trace",
                    "slack.message",
                    "user.message",
                }
                relevant_packets = [
                    p
                    for p in history
                    if p.get("packet_type") in relevant_types
                    or p.get("payload", {}).get("event") in ("start", "iteration")
                ]

                # Take last N packets for bounded context
                context_packets = relevant_packets[-MAX_CONTEXT_PACKETS:]

                if context_packets:
                    # Build context summary for system prompt injection
                    context_lines = ["Previous context from this thread:"]
                    for packet in context_packets:
                        payload = packet.get("payload", {})
                        ptype = packet.get("packet_type", "unknown")
                        # Extract meaningful content
                        content = (
                            payload.get("content")
                            or payload.get("text")
                            or payload.get("result")
                            or payload.get("message")
                            or ""
                        )
                        if content:
                            # Truncate long content
                            content_preview = str(content)[:200]
                            context_lines.append(f"- [{ptype}]: {content_preview}")

                    if len(context_lines) > 1:
                        # Inject as system-level context
                        context_text = "\n".join(context_lines)
                        instance.add_user_message(
                            f"[SYSTEM CONTEXT]\n{context_text}\n[END CONTEXT]",
                            metadata={
                                "hydrated": True,
                                "packet_count": len(context_packets),
                            },
                        )

                logger.info(
                    "agent.executor.hydrate: thread_id=%s, found=%d, injected=%d",
                    str(instance.thread_id),
                    len(history),
                    len(context_packets) if context_packets else 0,
                )

        except Exception as e:
            # Hydration failure does not block execution
            logger.warning(
                "agent.executor.hydrate_failed: thread_id=%s, error=%s",
                str(instance.thread_id),
                str(e),
            )

    # =========================================================================
    # Execution Loop
    # =========================================================================

    async def _run_execution_loop(
        self,
        instance: AgentInstance,
    ) -> ExecutionResult:
        """
        Run the main execution loop.

        State machine transitions:
        INITIALIZING -> REASONING -> TOOL_USE -> REASONING -> ... -> COMPLETED

        Args:
            instance: Agent instance to run

        Returns:
            ExecutionResult
        """
        start_time = datetime.utcnow()

        # Pre-execution governance validation
        try:
            from core.governance.validation import validate_authority, validate_safety

            # Extract action from task
            action = (
                instance.task.payload.get("message")
                or instance.task.payload.get("query")
                or str(instance.task.payload)
            )

            # Authority check
            authority_check = validate_authority(
                action=action, agent_id=instance.task.agent_id
            )
            if not authority_check["valid"]:
                logger.warning(
                    "agent.executor.governance.blocked: authority violation",
                    extra={
                        "agent_id": instance.task.agent_id,
                        "violation": authority_check.get("violation"),
                        "task_id": str(instance.task.id),
                    },
                )
                # Track authority block for self-reflection
                instance.add_governance_block(
                    block_type="authority_block",
                    violation=authority_check.get("violation"),
                )
                return ExecutionResult(
                    task_id=instance.task.id,
                    status="blocked",
                    error=f"Authority violation: {authority_check.get('violation')}",
                    iterations=0,
                    duration_ms=int(
                        (datetime.utcnow() - start_time).total_seconds() * 1000
                    ),
                    governance_blocks=instance.governance_blocks,
                )

            # Safety check
            safety_check = validate_safety(action=action, payload=instance.task.payload)
            if not safety_check["safe"]:
                logger.warning(
                    "agent.executor.governance.blocked: safety violation",
                    extra={
                        "agent_id": instance.task.agent_id,
                        "violation": safety_check.get("violation"),
                        "pattern": safety_check.get("pattern"),
                        "task_id": str(instance.task.id),
                    },
                )
                # Track safety block for self-reflection
                instance.add_governance_block(
                    block_type="safety_block",
                    violation=safety_check.get("violation"),
                    pattern=safety_check.get("pattern"),
                )
                return ExecutionResult(
                    task_id=instance.task.id,
                    status="blocked",
                    error=f"Safety violation: {safety_check.get('violation')}",
                    iterations=0,
                    duration_ms=int(
                        (datetime.utcnow() - start_time).total_seconds() * 1000
                    ),
                    governance_blocks=instance.governance_blocks,
                )
        except ImportError:
            # Governance validation not available - skip (non-fatal)
            logger.debug(
                "agent.executor.governance: validation module not available, skipping"
            )
        except Exception as e:
            # Governance check failed - log but continue (non-fatal)
            logger.warning(
                f"agent.executor.governance: validation error (non-fatal): {e}"
            )

        max_iterations = min(
            instance.task.max_iterations,
            self._max_iterations,
        )

        # Circuit breaker: track AIOS failures with windowed counting
        _aios_circuit_breaker = CircuitBreaker(
            CircuitBreakerConfig(
                failure_threshold=3,
                window_seconds=60,
                reset_timeout=30,
                name="aios",
            )
        )

        # Initialize with task payload as first message
        user_message = (
            instance.task.payload.get("message")
            or instance.task.payload.get("query")
            or instance.task.payload.get("content")
            or ""
        )
        if user_message:
            instance.add_user_message(user_message)

        # GMP-78: Semantic tool shortlisting
        # Instead of binding all 100+ tools, find the most relevant ones
        if user_message and hasattr(self._tool_registry, "get_relevant_tools"):
            try:
                relevant_tools = await self._tool_registry.get_relevant_tools(
                    agent_id=instance.task.agent_id,
                    principal_id=instance.task.principal_id,
                    query=user_message,
                    top_k=7,  # Slightly more than 5 to account for governance filtering
                )
                if relevant_tools:
                    instance.bind_tools(relevant_tools)
                    logger.info(
                        "agent.executor.tools.shortlisted",
                        task_id=str(instance.task.id),
                        tool_count=len(relevant_tools),
                        tools=[t.tool_id for t in relevant_tools],
                    )
            except Exception as e:
                logger.warning(
                    f"Tool shortlisting failed, using all approved tools: {e}"
                )

        # Transition to reasoning
        instance.transition_to(ExecutorState.REASONING)

        final_result: Optional[str] = None
        error: Optional[str] = None

        while instance.iteration < max_iterations:
            iteration = instance.increment_iteration()

            # GMP-78: Warn when approaching max iterations (loop guard enhancement)
            if iteration >= max_iterations - 2:
                logger.warning(
                    "agent.executor.approaching_max_iterations",
                    task_id=str(instance.task.id),
                    iteration=iteration,
                    max_iterations=max_iterations,
                    message="Consider stopping and providing partial answer",
                )

            # Log iteration
            logger.debug(
                "agent.executor.loop.iteration: task_id=%s, iteration=%d, action_type=%s",
                str(instance.task.id),
                iteration,
                instance.state.value,
            )

            # Emit trace packet
            await self._emit_packet(
                packet_type="agent.executor.trace",
                payload={
                    "event": "iteration",
                    "task_id": str(instance.task.id),
                    "agent_id": instance.task.agent_id,  # Used to set metadata.agent
                    "iteration": iteration,
                    "state": instance.state.value,
                },
                thread_id=instance.thread_id,
            )

            # Circuit breaker check before AIOS call
            if _aios_circuit_breaker.is_open():
                cb_stats = _aios_circuit_breaker.get_stats()
                logger.error(
                    "agent.executor.circuit_breaker_tripped",
                    task_id=str(instance.task.id),
                    circuit_state=cb_stats["state"],
                    failures_in_window=cb_stats["failures_in_window"],
                    total_trips=cb_stats["total_trips"],
                )
                instance.transition_to(ExecutorState.FAILED)
                error = f"Circuit breaker tripped: {cb_stats['failures_in_window']} failures in {cb_stats['window_seconds']}s window"
                # Emit escalation packet
                await self._emit_packet(
                    packet_type="agent.executor.escalation",
                    payload={
                        "event": "circuit_breaker_tripped",
                        "task_id": str(instance.task.id),
                        "agent_id": instance.task.agent_id,
                        "circuit_breaker_stats": cb_stats,
                        "requires_igor_approval": True,
                    },
                    thread_id=instance.thread_id,
                )
                break

            # Call AIOS
            context = instance.assemble_context()
            try:
                aios_result = await self._aios_runtime.execute_reasoning(context)
                # Record success for circuit breaker (resets on non-error)
                if aios_result.result_type != AIOSResultType.ERROR:
                    _aios_circuit_breaker.record_success()
            except Exception as aios_exc:
                _aios_circuit_breaker.record_failure(str(aios_exc))
                logger.warning(
                    "agent.executor.aios_call_exception",
                    task_id=str(instance.task.id),
                    error=str(aios_exc),
                    circuit_state=_aios_circuit_breaker.get_state(),
                )
                if _aios_circuit_breaker.is_open():
                    continue  # Will trip circuit breaker on next iteration
                # Create error result to continue loop
                aios_result = AIOSResult.error_result(str(aios_exc))

            instance.add_tokens(aios_result.tokens_used)

            # Handle result based on type
            if aios_result.result_type == AIOSResultType.RESPONSE:
                # Final answer - done!
                final_result = aios_result.content
                instance.add_assistant_message(final_result or "")
                instance.transition_to(ExecutorState.COMPLETED)
                break

            elif aios_result.result_type == AIOSResultType.TOOL_CALL:
                # Need to call a tool
                instance.transition_to(ExecutorState.TOOL_USE)

                tool_call = aios_result.tool_call
                if tool_call is None:
                    error = "AIOS returned tool_call type but no tool_call data"
                    instance.transition_to(ExecutorState.FAILED)
                    break
                openai_tool_name = tool_call.tool_id
                resolved_tool_id = instance.resolve_tool_id(openai_tool_name)
                if resolved_tool_id != tool_call.tool_id:
                    logger.warning(
                        "tool_call_name_resolved",
                        task_id=str(instance.task.id),
                        tool_name=tool_call.tool_id,
                        tool_id=resolved_tool_id,
                    )
                    tool_call.tool_id = resolved_tool_id

                # CRITICAL: Add assistant message with tool_calls BEFORE tool result
                # OpenAI requires: assistant (with tool_calls) → tool (with matching tool_call_id)
                instance.add_assistant_message_with_tool_calls(
                    tool_calls=[
                        {
                            "id": str(tool_call.call_id),
                            "type": "function",
                            "function": {
                                "name": openai_tool_name,
                                "arguments": json.dumps(tool_call.arguments),
                            },
                        }
                    ],
                    content=None,  # Tool call messages typically have no content
                )

                # Dispatch tool call using tool_id
                tool_result = await self._dispatch_tool_call(instance, tool_call)

                # Add result to history using tool_id (canonical identity)
                instance.add_tool_result(
                    tool_id=tool_call.tool_id,
                    call_id=str(tool_call.call_id),
                    result=tool_result.result
                    if tool_result.success
                    else tool_result.error,
                    success=tool_result.success,
                )

                # Continue reasoning
                instance.transition_to(ExecutorState.REASONING)

            elif aios_result.result_type == AIOSResultType.ERROR:
                # AIOS error - track for circuit breaker
                error = aios_result.error or "Unknown AIOS error"
                _aios_circuit_breaker.record_failure(error)
                logger.error(
                    "agent_aios_call_failed",
                    task_id=str(instance.task.id),
                    error=error,
                    circuit_state=_aios_circuit_breaker.get_state(),
                    failures_in_window=_aios_circuit_breaker.get_stats()[
                        "failures_in_window"
                    ],
                )
                # Only fail immediately if circuit breaker not yet tripped
                # (let circuit breaker handle escalation on next iteration)
                if _aios_circuit_breaker.is_open():
                    continue  # Will trip circuit breaker on next iteration
                instance.transition_to(ExecutorState.FAILED)
                break

        # Check if we exceeded max iterations
        if (
            instance.iteration >= max_iterations
            and instance.state == ExecutorState.REASONING
        ):
            logger.warning(
                "agent_max_iterations_exceeded: task_id=%s, max_iterations=%d",
                str(instance.task.id),
                max_iterations,
            )
            instance.transition_to(ExecutorState.TERMINATED)
            error = f"Max iterations exceeded ({max_iterations})"

        # Calculate duration
        duration_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)

        # Determine final status
        if instance.state == ExecutorState.COMPLETED:
            status = "completed"
        elif instance.state == ExecutorState.TERMINATED:
            status = "terminated"
        else:
            status = "failed"

        # Post-execution audit logging
        try:
            from core.governance.validation import audit_log

            action = (
                instance.task.payload.get("message")
                or instance.task.payload.get("query")
                or str(instance.task.payload)
            )
            audit_log(
                agent_id=instance.task.agent_id,
                action=action[:200],  # Truncate for audit trail
                success=(status == "completed"),
                metadata={
                    "task_id": str(instance.task.id),
                    "iterations": instance.iteration,
                    "duration_ms": duration_ms,
                    "status": status,
                },
            )
        except ImportError:
            # Audit logging not available - skip (non-fatal)
            pass
        except Exception as e:
            # Audit logging failed - log but don't fail execution
            logger.debug(f"agent.executor.audit: logging failed (non-fatal): {e}")

        # Collect tool calls from instance for result
        tool_call_results = []
        for tr in instance.tool_results:
            tool_call_results.append(
                ToolCallResult(
                    call_id=UUID(tr["call_id"])
                    if isinstance(tr.get("call_id"), str)
                    else tr.get("call_id", uuid4()),
                    tool_id=tr.get("tool_id", "unknown"),
                    result=tr.get("result"),
                    success=tr.get("success", True),
                    error=str(tr.get("result")) if not tr.get("success") else None,
                )
            )

        return ExecutionResult(
            task_id=instance.task.id,
            status=status,
            result=final_result,
            iterations=instance.iteration,
            duration_ms=duration_ms,
            error=error,
            trace_id=instance.instance_id,
            tool_calls=tool_call_results if tool_call_results else None,
            tokens_used=instance.total_tokens,
            governance_blocks=instance.governance_blocks
            if instance.governance_blocks
            else None,
            user_corrections=instance.user_corrections
            if instance.user_corrections
            else None,
        )

    # =========================================================================
    # Tool Dispatch
    # =========================================================================

    async def _dispatch_tool_call(
        self,
        instance: AgentInstance,
        tool_call: ToolCallRequest,
    ) -> ToolCallResult:
        """
        Dispatch a tool call through the registry.

        Uses tool_id as the sole identity for binding verification and dispatch.

        Args:
            instance: Agent instance
            tool_call: Tool call to dispatch (contains tool_id)

        Returns:
            ToolCallResult (includes tool_id for context re-entry)
        """
        # Log dispatch with tool_id (canonical identity)
        logger.info(
            "agent.executor.tool_call.dispatch: task_id=%s, tool_id=%s, arguments=%s",
            str(instance.task.id),
            tool_call.tool_id,
            tool_call.arguments,
        )

        # Emit packet with tool_id
        await self._emit_packet(
            packet_type="agent.executor.tool_call",
            payload={
                "event": "dispatch",
                "task_id": str(instance.task.id),
                "agent_id": instance.task.agent_id,  # Used to set metadata.agent
                "call_id": str(tool_call.call_id),
                "tool_id": tool_call.tool_id,
                "arguments": tool_call.arguments,
            },
            thread_id=instance.thread_id,
        )

        # Verify tool is bound using tool_id
        if not instance.has_tool(tool_call.tool_id):
            logger.error(
                "tool_binding_failed: task_id=%s, tool_id=%s",
                str(instance.task.id),
                tool_call.tool_id,
            )
            return ToolCallResult(
                call_id=tool_call.call_id,
                tool_id=tool_call.tool_id,
                success=False,
                error=f"Tool not bound to agent: {tool_call.tool_id}",
            )

        # Bind memory context before execution
        memory_context = await self._bind_memory_context(
            task_id=str(instance.task.id),
            agent_id=instance.config.agent_id,
        )
        if memory_context:
            logger.debug(
                f"Loaded memory context for task {instance.task.id}: {len(memory_context)} keys"
            )

        # Check if tool requires Igor approval
        catalog = await ToolGraph.get_l_tool_catalog()
        tool_def = next((t for t in catalog if t["name"] == tool_call.tool_id), None)

        if tool_def and tool_def.get("requires_igor_approval"):
            approval_manager = ApprovalManager(self._substrate_service)
            is_approved = await approval_manager.is_approved(str(tool_call.call_id))

            if not is_approved:
                # Get adaptive context from past patterns for high-risk tools
                adaptive_context = ""
                try:
                    from core.agents.adaptive_prompting import (
                        get_adaptive_context_for_tool,
                    )

                    adaptive_context = await get_adaptive_context_for_tool(
                        tool_call.tool_id
                    )
                    if adaptive_context:
                        logger.info(
                            f"Loaded adaptive context for {tool_call.tool_id}",
                            context_length=len(adaptive_context),
                        )
                except Exception as e:
                    logger.debug(f"Could not load adaptive context: {e}")

                logger.warning(
                    f"Tool {tool_call.tool_id} requires approval but not approved. task_id=%s, call_id=%s",
                    str(instance.task.id),
                    str(tool_call.call_id),
                )
                # Track tool approval block for self-reflection
                instance.add_governance_block(
                    block_type="tool_approval_block",
                    tool_id=tool_call.tool_id,
                    metadata={"call_id": str(tool_call.call_id)},
                )
                return ToolCallResult(
                    call_id=tool_call.call_id,
                    tool_id=tool_call.tool_id,
                    success=False,
                    error="PENDING_IGOR_APPROVAL",
                    result={
                        "status": "pending",
                        "message": "Awaiting Igor approval",
                        "adaptive_context": adaptive_context,
                    },
                )

        # Dispatch through registry using tool_id
        # Use guarded_execute if available (kernel-aware execution)
        try:
            context = {
                "task_id": str(instance.task.id),
                "agent_id": instance.config.agent_id,
                "thread_id": str(instance.thread_id),
                "iteration": instance.iteration,
                "memory_context": memory_context,  # Inject memory context
            }

            # Check if registry supports guarded execution and agent has kernels
            agent = self._get_kernel_aware_agent()
            if agent and hasattr(self._tool_registry, "guarded_execute"):
                # Use guarded execution (kernel-aware)
                result = await self._tool_registry.guarded_execute(
                    agent=agent,
                    tool_id=tool_call.tool_id,
                    arguments=tool_call.arguments,
                    context=context,
                )
            else:
                # Fallback to standard dispatch
                result = await self._tool_registry.dispatch_tool_call(
                    tool_id=tool_call.tool_id,
                    arguments=tool_call.arguments,
                    context=context,
                )

            # Persist task result after execution
            await self._persist_task_result(
                task_id=str(instance.task.id),
                result={
                    "agent_id": instance.config.agent_id,
                    "tool_id": tool_call.tool_id,
                    "call_id": str(tool_call.call_id),
                    "status": "completed" if result.success else "failed",
                    "error": result.error,
                    "duration_ms": result.duration_ms or 0,
                    "completed_at": datetime.utcnow().isoformat(),
                },
            )

            # Audit: log tool call in ToolGraph (best-effort)
            try:
                await ToolGraph.log_tool_call(
                    tool_name=tool_call.tool_id,
                    agent_id=instance.config.agent_id,
                    success=result.success,
                    duration_ms=result.duration_ms,
                    error=result.error,
                )
            except Exception as log_err:
                logger.warning(
                    "tool_call_audit_failed: task_id=%s, tool_id=%s, error=%s",
                    str(instance.task.id),
                    tool_call.tool_id,
                    str(log_err),
                )

            # Emit world model insight (best-effort)
            try:
                insight_emitter = get_insight_emitter(self._substrate_service)
                await insight_emitter.on_tool_called(
                    tool_name=tool_call.tool_id,
                    agent_id=instance.config.agent_id,
                    success=result.success,
                    duration_ms=result.duration_ms,
                    error=result.error,
                )
            except Exception as insight_err:
                logger.debug(f"Insight emission failed (non-fatal): {insight_err}")

            return result

        except Exception as e:
            logger.exception(
                "tool_dispatch_error: task_id=%s, tool_id=%s, error=%s",
                str(instance.task.id),
                tool_call.tool_id,
                str(e),
            )
            # Audit failure case as well
            try:
                await ToolGraph.log_tool_call(
                    tool_name=tool_call.tool_id,
                    agent_id=instance.config.agent_id,
                    success=False,
                    duration_ms=None,
                    error=str(e),
                )
            except Exception as log_err:
                logger.warning(
                    "tool_call_audit_failed: task_id=%s, tool_id=%s, error=%s",
                    str(instance.task.id),
                    tool_call.tool_id,
                    str(log_err),
                )

            return ToolCallResult(
                call_id=tool_call.call_id,
                tool_id=tool_call.tool_id,
                success=False,
                error=str(e),
            )

    async def _execute_plan_sequence(self, plan_id: str) -> Dict[str, Any]:
        """
        Dequeue and execute tasks from a plan in order, with approval checks.

        Args:
            plan_id: Plan identifier (thread_id)

        Returns:
            Dict with execution summary: completed, failed, pending_approvals
        """
        from runtime.task_queue import TaskQueue
        from core.governance.approvals import ApprovalManager

        task_queue = TaskQueue(queue_name="l9:tasks", use_redis=True)
        approval_manager = ApprovalManager(self._substrate_service)

        completed = []
        failed = []
        pending_approvals = []

        # Dequeue tasks with plan tag
        max_iterations = 100  # Safety limit
        iteration = 0

        while iteration < max_iterations:
            task = await task_queue.dequeue()
            if task is None:
                break

            # Check if task belongs to this plan
            plan_tag = f"plan:{plan_id}"
            if plan_tag not in task.tags:
                # Re-enqueue if not for this plan
                await task_queue.enqueue(
                    name=task.name,
                    payload=task.payload,
                    handler=task.handler,
                    agent_id=task.agent_id,
                    priority=task.priority,
                    tags=task.tags,
                )
                iteration += 1
                continue

            # Check if task requires approval
            task_type = task.payload.get("type", "")
            if task_type in ["gmp_run", "git_commit"]:
                is_approved = await approval_manager.is_approved(task.task_id)
                if not is_approved:
                    pending_approvals.append(
                        {
                            "task_id": task.task_id,
                            "name": task.name,
                            "type": task_type,
                        }
                    )
                    logger.info(f"Task {task.task_id} requires approval, skipping")
                    iteration += 1
                    continue

            # Execute task via handler
            try:
                handler = task_queue._handlers.get(task.handler)
                if handler:
                    result = await handler(task)
                    completed.append(
                        {
                            "task_id": task.task_id,
                            "name": task.name,
                            "result": str(result)[:200] if result else "success",
                        }
                    )
                else:
                    failed.append(
                        {
                            "task_id": task.task_id,
                            "name": task.name,
                            "error": f"No handler for {task.handler}",
                        }
                    )
            except Exception as e:
                failed.append(
                    {
                        "task_id": task.task_id,
                        "name": task.name,
                        "error": str(e),
                    }
                )

            iteration += 1

        return {
            "plan_id": plan_id,
            "completed": completed,
            "failed": failed,
            "pending_approvals": pending_approvals,
            "summary": {
                "total_completed": len(completed),
                "total_failed": len(failed),
                "total_pending": len(pending_approvals),
            },
        }

    # =========================================================================
    # Packet Emission (best-effort, non-blocking)
    # =========================================================================

    async def _emit_packet(
        self,
        packet_type: str,
        payload: dict[str, Any],
        thread_id: UUID,
    ) -> None:
        """
        Emit a packet to the memory substrate.

        BEHAVIOR: Best-effort, non-blocking.
        - Packet write failures are logged but do NOT stop execution.
        - This is intentional: execution must complete even if observability fails.
        - Critical failures (e.g., substrate down) are logged at WARNING level.

        REQUIRED FIELDS (all packets include):
        - packet_type: Discriminator for packet routing
        - payload: Contains task_id and event-specific data (should include agent_id)
        - thread_id: Thread identity for grouping
        - metadata.agent: Agent ID from payload.agent_id or "agent.executor" as fallback
        - metadata.schema_version: "1.0.0"

        NOTE: Per PacketEnvelope.yaml spec, metadata should use agent_id field.
        Current implementation uses metadata.agent (field name discrepancy to be resolved).

        Args:
            packet_type: Type of packet (e.g., "agent.executor.trace")
            payload: Packet payload (must contain task_id)
            thread_id: Thread identifier
        """
        try:
            # Use task.agent_id if available in payload, otherwise "agent.executor"
            agent_id = payload.get("agent_id", "agent.executor")

            packet = PacketEnvelopeIn(
                packet_type=packet_type,
                payload=payload,
                thread_id=thread_id,
                metadata={"agent": agent_id, "schema_version": "1.0.0"},
            )
            await self._substrate_service.write_packet(packet)

        except Exception as e:
            # Best-effort: log but don't fail execution
            logger.warning(
                "agent.executor.packet_write_failed: packet_type=%s, thread_id=%s, error=%s",
                packet_type,
                str(thread_id),
                str(e),
            )

    # =========================================================================
    # Active Memory Encoding (GMP-80-A7: Frontier Memory)
    # =========================================================================

    async def _run_active_memory_encoding(
        self,
        task: AgentTask,
        result: ExecutionResult,
        instance: AgentInstance,
    ) -> None:
        """
        Run active memory encoding on completed task execution.

        Extracts learnings from task outcomes and encodes them as semantic facts,
        creates episodic records, and updates importance scores.

        Args:
            task: The completed task
            result: The execution result
            instance: The agent instance that executed the task
        """
        try:
            from memory.ingestion import on_task_completion
        except ImportError:
            logger.debug("Active memory encoding not available - skipping")
            return

        try:
            # Extract learnings from result
            learnings = []
            if result.result:
                result_str = str(result.result)
                # Simple heuristic: extract sentences with learning indicators
                if any(
                    kw in result_str.lower()
                    for kw in ["prefer", "should", "always", "never", "learned"]
                ):
                    # Truncate to reasonable length
                    learnings.append(
                        result_str[:500] if len(result_str) > 500 else result_str
                    )

            # Only encode if task completed successfully and has meaningful output
            if result.status != "completed" or not result.result:
                return

            # Call on_task_completion with task outcome
            encoding_result = await on_task_completion(
                task_id=str(task.id),
                task_type=task.kind.value
                if hasattr(task.kind, "value")
                else str(task.kind),
                description=task.payload.get("message", "") if task.payload else "",
                outcome_text=str(result.result)[:1000] if result.result else "",
                success=result.status == "completed",
                learnings=learnings,
                entities=task.payload.get("entities", []) if task.payload else [],
                impact_score=0.5 + (0.3 if result.status == "completed" else -0.2),
                agent_id=task.agent_id,
                project_id=task.project_id if hasattr(task, "project_id") else None,
                session_id=str(task.get_thread_id())
                if hasattr(task, "get_thread_id")
                else None,
                metadata={
                    "iterations": result.iterations,
                    "duration_ms": result.duration_ms,
                    "tool_calls": len(result.tool_calls) if result.tool_calls else 0,
                },
            )

            if (
                encoding_result.get("facts_created", 0) > 0
                or encoding_result.get("facts_updated", 0) > 0
            ):
                logger.info(
                    "agent.executor.memory_encoded",
                    task_id=str(task.id),
                    facts_created=encoding_result.get("facts_created", 0),
                    facts_updated=encoding_result.get("facts_updated", 0),
                    episodes_created=encoding_result.get("episodes_created", 0),
                )

        except Exception as e:
            # Don't fail task execution if memory encoding fails
            logger.warning(
                "agent.executor.memory_encoding_failed",
                task_id=str(task.id),
                error=str(e),
            )

    # =========================================================================
    # Self-Reflection (v3.4+ / GMP-KERNEL-BOOT)
    # =========================================================================

    async def _run_self_reflection(
        self,
        task: AgentTask,
        result: ExecutionResult,
        instance: AgentInstance,
    ) -> None:
        """
        Run self-reflection analysis on completed task execution.

        Detects behavioral gaps and generates kernel evolution proposals
        if significant issues are found.

        Args:
            task: The completed task
            result: The execution result
            instance: The agent instance that executed the task
        """
        if not _has_self_reflection:
            return

        try:
            # Build execution context for analysis
            context = TaskExecutionContext(
                task_id=str(task.id),
                agent_id=task.agent_id,
                task_kind=task.kind.value
                if hasattr(task.kind, "value")
                else str(task.kind),
                success=result.status == "completed",
                duration_ms=float(result.duration_ms),
                tool_calls=[
                    {
                        "tool_id": tc.tool_id if hasattr(tc, "tool_id") else str(tc),
                        "success": tc.success if hasattr(tc, "success") else True,
                    }
                    for tc in (result.tool_calls or [])
                ],
                errors=[result.error] if result.error else [],
                warnings=[],
                iterations=result.iterations,
                tokens_used=result.tokens_used or 0,
                governance_blocks=result.governance_blocks or [],
                user_corrections=[
                    uc.get("correction", str(uc))
                    for uc in (result.user_corrections or [])
                ],
                metadata={
                    "thread_id": str(task.get_thread_id())
                    if task.get_thread_id()
                    else None,
                },
            )

            # Analyze execution
            reflection_result = await analyze_task_execution(context)

            # Persist reflection result to substrate
            if self._substrate_service:
                try:
                    from core.schemas import PacketEnvelopeIn

                    reflection_packet = PacketEnvelopeIn(
                        packet_type="agent.reflection.result",
                        agent_id=task.agent_id,
                        thread_id=str(task.get_thread_id())
                        if task.get_thread_id()
                        else None,
                        payload={
                            "reflection_id": reflection_result.reflection_id,
                            "task_id": str(task.id),
                            "gaps_detected": [
                                {
                                    "gap_type": gap.gap_type.value
                                    if hasattr(gap.gap_type, "value")
                                    else str(gap.gap_type),
                                    "severity": gap.severity.value
                                    if hasattr(gap.severity, "value")
                                    else str(gap.severity),
                                    "description": gap.description,
                                    "suggested_action": gap.suggested_action,
                                }
                                for gap in reflection_result.gaps_detected
                            ],
                            "kernel_update_needed": reflection_result.kernel_update_needed,
                            "summary": reflection_result.summary,
                            "confidence": reflection_result.confidence,
                        },
                        metadata={
                            "source": "self_reflection",
                            "execution_status": result.status,
                        },
                    )
                    await self._substrate_service.write_packet(reflection_packet)
                    logger.debug(
                        "executor.self_reflection.persisted",
                        task_id=str(task.id),
                        reflection_id=reflection_result.reflection_id,
                    )
                except Exception as persist_err:
                    logger.warning(
                        "executor.self_reflection.persist_failed",
                        task_id=str(task.id),
                        error=str(persist_err),
                    )

            # Log reflection results
            if reflection_result.gaps_detected:
                logger.info(
                    "executor.self_reflection.gaps_detected",
                    task_id=str(task.id),
                    gap_count=len(reflection_result.gaps_detected),
                    kernel_update_needed=reflection_result.kernel_update_needed,
                )

                # Generate evolution plan if kernel update is needed
                if reflection_result.kernel_update_needed:
                    evolution_plan = await create_evolution_plan(
                        reflection_result,
                        substrate_service=self._substrate_service,
                    )
                    logger.info(
                        "executor.self_reflection.evolution_plan_created",
                        task_id=str(task.id),
                        plan_id=evolution_plan.plan_id,
                        proposal_count=len(evolution_plan.proposals),
                        requires_igor_approval=evolution_plan.requires_igor_approval,
                    )

                    # Emit evolution plan packet for review
                    await self._emit_packet(
                        packet_type="kernel.evolution.plan",
                        payload={
                            "plan_id": evolution_plan.plan_id,
                            "reflection_id": reflection_result.reflection_id,
                            "agent_id": task.agent_id,
                            "proposal_count": len(evolution_plan.proposals),
                            "requires_igor_approval": evolution_plan.requires_igor_approval,
                            "estimated_impact": evolution_plan.estimated_impact,
                        },
                        thread_id=task.get_thread_id(),
                    )
            else:
                logger.debug(
                    "executor.self_reflection.no_gaps",
                    task_id=str(task.id),
                )

        except Exception as e:
            # Self-reflection should never fail the task
            logger.warning(
                "executor.self_reflection.error",
                task_id=str(task.id),
                error=str(e),
            )

    # =========================================================================
    # Error Handling
    # =========================================================================

    async def _handle_error(
        self,
        task: AgentTask,
        error: str,
        start_time: datetime,
        error_type: str,
    ) -> ExecutionResult:
        """
        Handle an error during execution.

        Args:
            task: Failed task
            error: Error message
            start_time: When execution started
            error_type: Type of error for logging

        Returns:
            ExecutionResult with error
        """
        duration_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)

        # Emit error packet
        await self._emit_packet(
            packet_type="agent.executor.result",
            payload={
                "task_id": str(task.id),
                "agent_id": task.agent_id,  # Used to set metadata.agent
                "status": "failed",
                "error": error,
                "error_type": error_type,
            },
            thread_id=task.get_thread_id(),
        )

        return ExecutionResult(
            task_id=task.id,
            status="failed",
            error=error,
            duration_ms=duration_ms,
        )


# =============================================================================
# Public API
# =============================================================================

__all__ = [
    "AgentExecutorService",
    "AIOSRuntime",
    "ToolRegistryProtocol",
    "SubstrateServiceProtocol",
    "AgentRegistryProtocol",
]
