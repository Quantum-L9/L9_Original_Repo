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

# ============================================================================
# DORA HEADER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# See footer for extended metadata
# ============================================================================
__dora_meta__ = {
    "component_id": "COR-FOUN-001",
    "component_name": "Executor",
    "module_version": "1.0.0",
    "created_at": "2026-01-18T05:25:09Z",
    "created_by": "L9_Codegen_Engine",
    "layer": "foundation",
    "domain": "agent_execution",
    "type": "engine",
    "status": "active",
    "governance_level": "critical",
    "compliance_required": True,
    "audit_trail": True,
    "purpose": "Provides executor components including AIOSRuntime, ToolRegistryProtocol, SubstrateServiceProtocol",
    "dependencies": [
        "core.agents.adaptive_prompting",
        "core.agents.agent_instance",
        "core.agents.kernelevolution",
        "core.agents.prompt_builder",
        "core.agents.prompt_defense",
    ],
}
# ============================================================================

import json
import os
from datetime import datetime
from typing import Any, Protocol
from uuid import UUID, uuid4

import structlog

from core.agents.agent_instance import AgentInstance
from core.agents.schemas import (
    AgentConfig,
    AgentTask,
    AIOSResult,
    AIOSResultType,
    DuplicateTaskResponse,
    ExecutionResult,
    ExecutorState,
    ToolBinding,
    ToolCallRequest,
    ToolCallResult,
)
from core.governance.approvals import ApprovalManager
from core.observability.circuit_breaker import CircuitBreaker, CircuitBreakerConfig
from core.schemas import PacketEnvelopeIn
from core.tools.tool_graph import ToolGraph
from core.worldmodel.insight_emitter import get_insight_emitter
from memory.agent_persistence import AgentPersistenceService
from runtime.dora import emit_executor_trace, update_dora_block_in_file

# Virtual Context Manager import (optional - graceful degradation)
try:
    from core.memory.virtual_context import VirtualContextManager

    _has_virtual_context = True
except ImportError:
    _has_virtual_context = False
    VirtualContextManager = None  # type: ignore

# Event Queue import (optional - graceful degradation)
try:
    from core.coordination.event_queue import Event, EventKind, EventQueue

    _has_event_queue = True
except ImportError:
    _has_event_queue = False
    EventQueue = None  # type: ignore
    Event = None  # type: ignore
    EventKind = None  # type: ignore

# Tool Audit import (optional - graceful degradation)
try:
    from core.tools.tool_audit import ToolAuditService

    _has_tool_audit = True
except ImportError:
    _has_tool_audit = False
    ToolAuditService = None  # type: ignore

# Domain Tensor Bridge import (optional - graceful degradation)
try:
    from domain_tensor_bridge import ReasoningEngine as DTBReasoningEngine

    _has_tensor_bridge = True
except ImportError:
    DTBReasoningEngine = None  # type: ignore[misc, assignment]
    _has_tensor_bridge = False

# Initialize logger early for import error handling
logger = structlog.get_logger(__name__)

# Self-reflection imports (optional - graceful degradation if not available)
try:
    from core.agents.kernelevolution import create_evolution_plan
    from core.agents.selfreflection import TaskExecutionContext, analyze_task_execution

    _has_self_reflection = True
except ImportError:
    _has_self_reflection = False

# Prompt defense imports (GMP-60: Runtime hardening)
try:
    from core.agents.prompt_defense import (
        InjectionDetectionResult,
        detect_prompt_injection,
        get_blocked_response,
        should_block_request,
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

from core.decorators import must_stay_async

# Stage 5: Predictive Memory Warming (optional - graceful degradation)
try:
    from memory.warming_service import MemoryWarmingService

    _has_memory_warming = True
except ImportError:
    _has_memory_warming = False
    logger.debug("memory_warming not available - warming disabled")


# =============================================================================
# Reactive Task Generation
# =============================================================================


@must_stay_async("callers use await")
async def _generate_tasks_from_query(query: str) -> list[dict[str, Any]]:
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

    @must_stay_async("callers use await")
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

    @must_stay_async("callers use await")
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

    @must_stay_async("callers use await")
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

    @must_stay_async("callers use await")
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

    @must_stay_async("callers use await")
    async def search_packets_by_thread(
        self,
        thread_id: str,
        packet_type: str | None = None,
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

    def get_agent_config(self, agent_id: str) -> AgentConfig | None:
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
        default_agent_id: str | None = None,
        max_iterations: int | None = None,
        agent_persistence: AgentPersistenceService | None = None,
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
        self._kernel_aware_agent: Any | None = None

        # Stage 5: Predictive Memory Warming service (optional)
        self._memory_warming_service: Any | None = None

        # Stage 5: Graph Hydrator for loading agent context from Neo4j (optional)
        self._graph_hydrator: Any | None = None

        # Domain Tensor Bridge for tensor reasoning enrichment (optional)
        self._tensor_bridge: Any | None = None

        # Stage 7: Virtual Context Manager for tiered memory (optional)
        self._virtual_context_manager: Any | None = None

        # Stage 7: Event Queue for async coordination (optional)
        self._event_queue: Any | None = None

        # Stage 7: Tool Audit Service for execution tracking (optional)
        self._tool_audit_service: Any | None = None

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

    def set_memory_warming_service(self, service: Any) -> None:
        """
        Set the memory warming service for predictive cache warming.

        Stage 5: Predictive Memory Warming (GMP-STAGE5).
        Warms relevant entities before agent reasoning to reduce latency.

        Args:
            service: MemoryWarmingService instance
        """
        self._memory_warming_service = service
        logger.info(
            "agent.executor.memory_warming_set: enabled=%s",
            service is not None,
        )

    def set_graph_hydrator(self, hydrator: Any) -> None:
        """
        Set the graph hydrator for loading agent context from Neo4j.

        Stage 5: Graph-Backed Agent State (GMP-76).
        Hydrates agent context (responsibilities, directives, tools) from
        Neo4j graph before task execution.

        Args:
            hydrator: GraphHydrator instance
        """
        self._graph_hydrator = hydrator
        logger.info(
            "agent.executor.graph_hydrator_set: enabled=%s",
            hydrator is not None,
        )

    def set_tensor_bridge(self, bridge: Any) -> None:
        """
        Set the Domain Tensor Bridge for tensor reasoning enrichment.

        Stage 6: Domain Tensor Bridge Integration (GMP-DTB-WIRE).
        Enables tensor-based context enrichment before agent execution.
        The bridge provides multi-modal reasoning (causal, symbolic, analogical).

        Args:
            bridge: ReasoningEngine instance from domain_tensor_bridge
        """
        self._tensor_bridge = bridge
        logger.info(
            "agent.executor.tensor_bridge_set: enabled=%s",
            bridge is not None,
        )

    def set_virtual_context_manager(self, manager: Any) -> None:
        """
        Set the Virtual Context Manager for tiered memory operations.

        Stage 7: Virtual Context Management (GMP-WIRE-VC-EQ).
        Enables tiered memory (main/working/archival) with LLM-driven
        eviction and page fault handling for long conversations.

        Args:
            manager: VirtualContextManager instance from core.memory.virtual_context
        """
        self._virtual_context_manager = manager
        logger.info(
            "agent.executor.virtual_context_set: enabled=%s",
            manager is not None,
        )

    def set_event_queue(self, queue: Any) -> None:
        """
        Set the Event Queue for async agent coordination.

        Stage 7: Event-Driven Coordination (GMP-WIRE-VC-EQ).
        Enables publish/subscribe pattern for decoupled agent communication.
        Replaces synchronous supervisor calls with async event publishing.

        Args:
            queue: EventQueue instance from core.coordination.event_queue
        """
        self._event_queue = queue
        logger.info(
            "agent.executor.event_queue_set: enabled=%s",
            queue is not None,
        )

    def set_tool_audit_service(self, service: Any) -> None:
        """
        Set the Tool Audit Service for execution tracking.

        Stage 7: Tool Audit Trail (GMP-WIRE-VC-EQ).
        Enables automatic audit logging of all tool executions with
        cost estimation, latency tracking, and error recording.

        Args:
            service: ToolAuditService instance from core.tools.tool_audit
        """
        self._tool_audit_service = service
        logger.info(
            "agent.executor.tool_audit_set: enabled=%s",
            service is not None,
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

    def _get_kernel_aware_agent(self) -> Any | None:
        """
        Get the kernel-aware agent if available and active.

        Returns:
            Agent with active kernels, or None if not available
        """
        if self._kernel_aware_agent is None:
            return None

        kernel_state = getattr(self._kernel_aware_agent, "kernel_state", None)
        if kernel_state is None:
            return None
        if isinstance(kernel_state, str):
            if kernel_state != "ACTIVE":
                return None
        elif hasattr(kernel_state, "initialized"):
            if not kernel_state.initialized:
                return None
        else:
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
                            "severity": (
                                injection_result.severity.value
                                if injection_result.severity
                                else "unknown"
                            ),
                            "patterns": injection_result.patterns_matched,
                            "redacted_input": injection_result.redacted_input,
                        },
                        thread_id=task.get_thread_id(),
                    )

                    logger.warning(
                        "agent.executor.prompt_injection_blocked",
                        task_id=task_id_str,
                        severity=(
                            injection_result.severity.value
                            if injection_result.severity
                            else "unknown"
                        ),
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

            # Stage 5: Predictive Memory Warming (GMP-STAGE5)
            # Warm relevant entities before agent reasoning
            if _has_memory_warming and self._memory_warming_service is not None:
                try:
                    user_message = (
                        task.payload.get("message", "") if task.payload else ""
                    )
                    if user_message:
                        # Extract simple entity mentions (words that might be entities)
                        # In production, use NER or semantic extraction
                        words = user_message.split()
                        mentioned_entities = [
                            w.strip(".,!?;:()[]{}\"'")
                            for w in words
                            if len(w) > 3 and w[0].isupper()
                        ]

                        if mentioned_entities:
                            warming_result = (
                                await self._memory_warming_service.warm_for_query(
                                    query=user_message,
                                    mentioned_entities=mentioned_entities[:20],
                                    max_gaps_to_warm=10,
                                )
                            )
                            logger.debug(
                                "agent.executor.memory_warming",
                                task_id=task_id_str,
                                gaps_detected=warming_result.get("gaps_detected", 0),
                                entities_warmed=warming_result.get(
                                    "entities_warmed", 0
                                ),
                                latency_ms=warming_result.get("warming_latency_ms", 0),
                            )
                except Exception as warming_error:
                    # Non-fatal - log and continue
                    logger.warning(
                        "agent.executor.memory_warming_failed",
                        task_id=task_id_str,
                        error=str(warming_error),
                    )

            # Stage 5: Graph Hydration (GMP-76)
            # Load agent context from Neo4j graph before execution
            hydrated_context = None
            if self._graph_hydrator is not None:
                try:
                    hydrated_context = await self._graph_hydrator.hydrate(
                        agent_id=task.agent_id,
                        include_kernels=True,
                    )
                    logger.debug(
                        "agent.executor.graph_hydration",
                        task_id=task_id_str,
                        agent_id=task.agent_id,
                        responsibilities=(
                            len(hydrated_context.responsibilities)
                            if hydrated_context
                            else 0
                        ),
                        tools=(
                            len(hydrated_context.available_tools)
                            if hydrated_context
                            else 0
                        ),
                    )
                except Exception as hydration_error:
                    # Non-fatal - log and continue without hydrated context
                    logger.warning(
                        "agent.executor.graph_hydration_failed",
                        task_id=task_id_str,
                        agent_id=task.agent_id,
                        error=str(hydration_error),
                    )

            # Stage 6: Domain Tensor Bridge Enrichment (GMP-DTB-WIRE)
            # Enrich context with tensor-based reasoning before execution
            tensor_enrichment = None
            if _has_tensor_bridge and self._tensor_bridge is not None:
                try:
                    user_message = (
                        task.payload.get("message", "") if task.payload else ""
                    )
                    if user_message:
                        # Use DTB ReasoningEngine for context enrichment
                        tensor_enrichment = await self._tensor_bridge.enrich_context(
                            query=user_message,
                            domain_id=task.agent_id,
                            reasoning_modes=["causal", "symbolic"],
                        )
                        logger.debug(
                            "agent.executor.tensor_enrichment",
                            task_id=task_id_str,
                            enrichment_type=type(tensor_enrichment).__name__,
                            has_enrichment=tensor_enrichment is not None,
                        )
                except Exception as tensor_error:
                    # Non-fatal - log and continue without tensor enrichment
                    logger.warning(
                        "agent.executor.tensor_enrichment_failed",
                        task_id=task_id_str,
                        error=str(tensor_error),
                    )

            # Stage 7: Virtual Context Loading (GMP-WIRE-VC-EQ)
            # Load tiered memory context (main + working) before execution
            virtual_context = None
            if _has_virtual_context and self._virtual_context_manager is not None:
                try:
                    virtual_context = await self._virtual_context_manager.load_context(
                        agent_id=task.agent_id,
                        task_id=task_id_str,
                    )
                    logger.debug(
                        "agent.executor.virtual_context_loaded",
                        task_id=task_id_str,
                        agent_id=task.agent_id,
                        main_context_count=(
                            len(virtual_context.main_context)
                            if virtual_context and virtual_context.main_context
                            else 0
                        ),
                        working_memory_count=(
                            len(virtual_context.working_memory)
                            if virtual_context and virtual_context.working_memory
                            else 0
                        ),
                    )
                except Exception as context_error:
                    # Non-fatal - log and continue without virtual context
                    logger.warning(
                        "agent.executor.virtual_context_load_failed",
                        task_id=task_id_str,
                        agent_id=task.agent_id,
                        error=str(context_error),
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

            # Stage 7: Event Queue - Publish task start (GMP-WIRE-VC-EQ)
            if _has_event_queue and self._event_queue is not None:
                try:
                    await self._event_queue.publish(
                        Event(
                            kind=EventKind.TASK_STARTED,
                            source_agent=task.agent_id,
                            target_agent="*",  # Broadcast to all subscribers
                            payload={
                                "task_id": task_id_str,
                                "agent_id": task.agent_id,
                                "task_kind": task.kind.value
                                if task.kind
                                else "unknown",
                            },
                        )
                    )
                except Exception as event_error:
                    # Non-fatal - log and continue
                    logger.warning(
                        "agent.executor.event_publish_failed",
                        task_id=task_id_str,
                        event_kind="TASK_STARTED",
                        error=str(event_error),
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

            # Stage 7: Event Queue - Publish task completion (GMP-WIRE-VC-EQ)
            if _has_event_queue and self._event_queue is not None:
                try:
                    event_kind = (
                        EventKind.TASK_COMPLETED
                        if result.status == "completed"
                        else EventKind.TASK_FAILED
                    )
                    await self._event_queue.publish(
                        Event(
                            kind=event_kind,
                            source_agent=task.agent_id,
                            target_agent="*",  # Broadcast to all subscribers
                            payload={
                                "task_id": task_id_str,
                                "agent_id": task.agent_id,
                                "status": result.status,
                                "iterations": result.iterations,
                                "duration_ms": result.duration_ms,
                                "error": result.error,
                            },
                        )
                    )
                except Exception as event_error:
                    # Non-fatal - log and continue
                    logger.warning(
                        "agent.executor.event_publish_failed",
                        task_id=task_id_str,
                        event_kind=str(event_kind),
                        error=str(event_error),
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
            _dora_trace = await emit_executor_trace(
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

            # Update DORA trace block in executor source file (GMP-DORA-WIRE)
            # This writes the runtime trace to __l9_trace__ at end of this file
            if os.environ.get("L9_DORA_UPDATE_SOURCE", "").lower() == "true":
                update_dora_block_in_file(__file__, _dora_trace)

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

    async def _bind_memory_context(self, task_id: str, agent_id: str) -> dict[str, Any]:
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
                    MEMORY_SEGMENT_GOVERNANCE_META,
                    MEMORY_SEGMENT_PROJECT_HISTORY,
                    memory_search,
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
                payload={
                    "task_id": task_id,
                    "status": result.get("status", "unknown"),
                    "iterations": result.get("iterations", 0),
                    "duration_ms": result.get("duration_ms", 0),
                    "error": result.get("error"),
                    "completed_at": result.get("completed_at"),
                },
                metadata={"agent": result.get("agent_id", "L")},
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
        from uuid import uuid4

        from core.governance.approvals import ApprovalManager
        from runtime.task_queue import QueuedTask, dispatch_task_immediate

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

    def _validate_task(self, task: AgentTask) -> str | None:
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

    async def _instantiate_agent(self, task: AgentTask) -> AgentInstance | None:
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
            # Governance validation not available - BLOCK (fail-closed)
            logger.error(
                "agent.executor.governance.missing",
                task_id=str(instance.task.id),
            )
            return ExecutionResult(
                task_id=instance.task.id,
                status="blocked",
                error="Governance validation unavailable. Execution blocked.",
                iterations=0,
                duration_ms=int(
                    (datetime.utcnow() - start_time).total_seconds() * 1000
                ),
                governance_blocks=instance.governance_blocks,
            )
        except Exception as e:
            # Governance check failed - BLOCK (fail-closed)
            logger.error(
                "agent.executor.governance.error",
                task_id=str(instance.task.id),
                error=str(e),
            )
            return ExecutionResult(
                task_id=instance.task.id,
                status="blocked",
                error=f"Governance validation failed: {e}",
                iterations=0,
                duration_ms=int(
                    (datetime.utcnow() - start_time).total_seconds() * 1000
                ),
                governance_blocks=instance.governance_blocks,
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
                # principal_id may be in task context or payload
                principal_id = (
                    instance.task.context.get("principal_id")
                    or instance.task.payload.get("principal_id")
                    or instance.task.source_id
                )
                relevant_tools = await self._tool_registry.get_relevant_tools(
                    agent_id=instance.task.agent_id,
                    principal_id=principal_id,
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
                # Tool shortlisting failed - BLOCK (fail-closed)
                logger.error(
                    "agent.executor.tools.shortlisting_failed",
                    task_id=str(instance.task.id),
                    error=str(e),
                )
                return ExecutionResult(
                    task_id=instance.task.id,
                    status="blocked",
                    error=f"Tool shortlisting failed: {e}",
                    iterations=0,
                    duration_ms=int(
                        (datetime.utcnow() - start_time).total_seconds() * 1000
                    ),
                    governance_blocks=instance.governance_blocks,
                )

        # Transition to reasoning
        instance.transition_to(ExecutorState.REASONING)

        final_result: str | None = None
        error: str | None = None

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

            # GMP-78 Phase 2: Dynamic tool discovery (semantic search for relevant tools)
            # Run once at start of execution, tools are cached in instance
            if iteration == 0:
                await instance.prepare_dynamic_tools()

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

            # GMP-88: ReAct THOUGHT logging
            # Emit structured packet for reasoning transparency
            if (
                aios_result.content
                or aios_result.result_type == AIOSResultType.TOOL_CALL
            ):
                thought_content = (
                    aios_result.content
                    or f"Calling tool: {aios_result.tool_call.tool_id if aios_result.tool_call else 'unknown'}"
                )
                await self._emit_packet(
                    packet_type="agent.executor.thought",
                    payload={
                        "task_id": str(instance.task.id),
                        "iteration": iteration,
                        "thought": thought_content[:500],  # Truncate for storage
                        "action_type": aios_result.result_type.value,
                    },
                    agent_id=instance.task.agent_id,
                    thread_id=instance.thread_id,
                )

            # Handle result based on type
            if aios_result.result_type == AIOSResultType.RESPONSE:
                # Final answer - done!
                final_result = aios_result.content
                instance.add_assistant_message(final_result or "")
                instance.transition_to(ExecutorState.COMPLETED)
                break

            if aios_result.result_type == AIOSResultType.TOOL_CALL:
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
                    result=(
                        tool_result.result if tool_result.success else tool_result.error
                    ),
                    success=tool_result.success,
                )

                # GMP-88: ReAct OBSERVATION logging
                # Emit structured packet for tool result transparency
                observation_content = (
                    str(tool_result.result)[:500]
                    if tool_result.success
                    else f"Error: {tool_result.error}"
                )
                await self._emit_packet(
                    packet_type="agent.executor.observation",
                    payload={
                        "task_id": str(instance.task.id),
                        "iteration": iteration,
                        "tool_id": tool_call.tool_id,
                        "observation": observation_content,
                        "success": tool_result.success,
                        "duration_ms": getattr(tool_result, "duration_ms", 0),
                    },
                    agent_id=instance.task.agent_id,
                    thread_id=instance.thread_id,
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
                    call_id=(
                        UUID(tr["call_id"])
                        if isinstance(tr.get("call_id"), str)
                        else tr.get("call_id", uuid4())
                    ),
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
            governance_blocks=(
                instance.governance_blocks if instance.governance_blocks else None
            ),
            user_corrections=(
                instance.user_corrections if instance.user_corrections else None
            ),
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

            # Require guarded execution with active kernels (fail-closed)
            agent = self._get_kernel_aware_agent()
            if not agent:
                return ToolCallResult(
                    call_id=tool_call.call_id,
                    tool_id=tool_call.tool_id,
                    success=False,
                    error="Kernel-aware agent required for tool dispatch",
                )
            if not hasattr(self._tool_registry, "guarded_execute"):
                return ToolCallResult(
                    call_id=tool_call.call_id,
                    tool_id=tool_call.tool_id,
                    success=False,
                    error="Tool registry missing guarded_execute enforcement",
                )

            # Use guarded execution (kernel-aware)
            result = await self._tool_registry.guarded_execute(
                agent=agent,
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

    async def _execute_plan_sequence(self, plan_id: str) -> dict[str, Any]:
        """
        Dequeue and execute tasks from a plan in order, with approval checks.

        Args:
            plan_id: Plan identifier (thread_id)

        Returns:
            Dict with execution summary: completed, failed, pending_approvals
        """
        from core.governance.approvals import ApprovalManager
        from runtime.task_queue import TaskQueue

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

        BEHAVIOR: Enforced, fail-closed.
        - Packet write failures are logged and raised to stop execution.

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
        # Use task.agent_id if available in payload, otherwise "agent.executor"
        agent_id = payload.get("agent_id", "agent.executor")

        packet = PacketEnvelopeIn(
            packet_type=packet_type,
            payload=payload,
            thread_id=thread_id,
            metadata={"agent": agent_id, "schema_version": "1.0.0"},
        )
        try:
            await self._substrate_service.write_packet(packet)
        except Exception as e:
            logger.error(
                "agent.executor.packet_write_failed: packet_type=%s, thread_id=%s, error=%s",
                packet_type,
                str(thread_id),
                str(e),
            )
            raise

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
                task_type=(
                    task.kind.value if hasattr(task.kind, "value") else str(task.kind)
                ),
                description=task.payload.get("message", "") if task.payload else "",
                outcome_text=str(result.result)[:1000] if result.result else "",
                success=result.status == "completed",
                learnings=learnings,
                entities=task.payload.get("entities", []) if task.payload else [],
                impact_score=0.5 + (0.3 if result.status == "completed" else -0.2),
                agent_id=task.agent_id,
                project_id=task.project_id if hasattr(task, "project_id") else None,
                session_id=(
                    str(task.get_thread_id())
                    if hasattr(task, "get_thread_id")
                    else None
                ),
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
                task_kind=(
                    task.kind.value if hasattr(task.kind, "value") else str(task.kind)
                ),
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
                    "thread_id": (
                        str(task.get_thread_id()) if task.get_thread_id() else None
                    ),
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
                        thread_id=task.get_thread_id(),
                        payload={
                            "reflection_id": reflection_result.reflection_id,
                            "task_id": str(task.id),
                            "gaps_detected": [
                                {
                                    "gap_type": (
                                        gap.gap_type.value
                                        if hasattr(gap.gap_type, "value")
                                        else str(gap.gap_type)
                                    ),
                                    "severity": (
                                        gap.severity.value
                                        if hasattr(gap.severity, "value")
                                        else str(gap.severity)
                                    ),
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
                            "agent": task.agent_id,
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
    "AIOSRuntime",
    "AgentExecutorService",
    "AgentRegistryProtocol",
    "SubstrateServiceProtocol",
    "ToolRegistryProtocol",
]

# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# Extended metadata referenced by header
# ============================================================================
__dora_footer__ = {
    "component_id": "COR-FOUN-001",
    "security_classification": "internal",
    "execution_mode": "on-demand",
    "timeout_seconds": 30,
    "performance_tier": "batch",
    "last_modified": "2026-01-18T05:25:09Z",
    "modified_by": "L9_Codegen_Engine",
    "change_summary": "Initial generation with DORA compliance",
}
# ============================================================================

# ============================================================================
# L9 DORA BLOCK - AUTO-UPDATED - DO NOT EDIT
# ============================================================================
__l9_trace__ = {
    "trace_id": "f892b0df",
    "task": "l_agent:second_test",
    "timestamp": "2026-01-18T06:31:09.967674+00:00",
    "patterns_used": ["agent_execution", "reasoning_loop"],
    "graph": {"nodes": [], "edges": []},
    "inputs": {
        "task_id": "test-456",
        "agent_id": "l_agent",
        "query": "verify replacement",
    },
    "outputs": {"status": "success", "iterations": 3},
    "metrics": {
        "confidence": "0.95",
        "errors_detected": [],
        "stability_score": "1.0",
        "duration_ms": 250,
    },
}
# ============================================================================
# END L9 DORA BLOCK
# ============================================================================
