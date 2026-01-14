"""
L9-specific observability integration helpers.

Provides high-level wrappers to instrument L9 services with minimal friction.

This module instruments the actual L9 service methods:
- AgentExecutorService.start_agent_task()
- ExecutorToolRegistry.dispatch_tool_call()
- GovernanceEngineService.evaluate()
- MemorySubstrateService.write_packet() / semantic_search() / get_packet()
"""

import structlog
from typing import Any

from .instrumentation import (
    trace_span, trace_tool_call, trace_governance_check,
)
from .models import SpanKind

logger = structlog.get_logger(__name__)


async def instrument_agent_executor(executor_service: Any) -> None:
    """
    Wrap agent executor methods with observability decorators.
    
    Instruments:
    - start_agent_task(): Initializes trace context for new tasks
    
    Note: AgentExecutorService does not have a separate 'step' method.
    The execution loop is internal to start_agent_task.
    """
    if not executor_service:
        logger.debug("instrument_agent_executor: no executor_service provided")
        return

    # Check if start_agent_task exists
    if not hasattr(executor_service, 'start_agent_task'):
        logger.warning("instrument_agent_executor: executor_service has no start_agent_task method")
        return

    original_start_task = executor_service.start_agent_task

    async def traced_start_task(*args: Any, **kwargs: Any) -> Any:
        from .service import ObservabilityService
        
        # Initialize trace context for this task
        service = ObservabilityService.get()
        if service:
            ctx = service.current_trace_context()
            if ctx:
                service.set_trace_context(ctx)
        
        # Wrap the actual call with a span
        @trace_span("agent.start_task", kind=SpanKind.INTERNAL)
        async def _start_task():
            return await original_start_task(*args, **kwargs)
        
        return await _start_task()

    executor_service.start_agent_task = traced_start_task
    logger.info("Instrumented agent executor (start_agent_task)")


async def instrument_tool_registry(tool_registry: Any) -> None:
    """
    Wrap tool registry methods with observability.
    
    Instruments:
    - dispatch_tool_call(tool_id, arguments, context): Main tool dispatch method
    """
    if not tool_registry:
        logger.debug("instrument_tool_registry: no tool_registry provided")
        return

    # Check if dispatch_tool_call exists (ExecutorToolRegistry interface)
    if not hasattr(tool_registry, 'dispatch_tool_call'):
        logger.warning("instrument_tool_registry: tool_registry has no dispatch_tool_call method")
        return

    original_dispatch = tool_registry.dispatch_tool_call

    async def traced_dispatch_tool_call(
        tool_id: str,
        arguments: dict[str, Any],
        context: dict[str, Any],
    ) -> Any:
        """Traced wrapper for dispatch_tool_call."""
        
        @trace_tool_call(tool_id)
        async def _dispatch():
            return await original_dispatch(tool_id, arguments, context)

        return await _dispatch()

    tool_registry.dispatch_tool_call = traced_dispatch_tool_call
    logger.info("Instrumented tool registry (dispatch_tool_call)")


async def instrument_governance_engine(governance_engine: Any) -> None:
    """
    Wrap governance engine with observability.
    
    Instruments:
    - evaluate(request: EvaluationRequest): Policy evaluation method
    """
    if not governance_engine:
        logger.debug("instrument_governance_engine: no governance_engine provided")
        return

    # Check if evaluate exists (GovernanceEngineService interface)
    if not hasattr(governance_engine, 'evaluate'):
        logger.warning("instrument_governance_engine: governance_engine has no evaluate method")
        return

    original_evaluate = governance_engine.evaluate

    async def traced_evaluate(request: Any) -> Any:
        """Traced wrapper for governance evaluate."""
        # Extract policy info from request for span naming
        policy_name = "governance.evaluate"
        if hasattr(request, 'action'):
            policy_name = f"governance.evaluate:{request.action}"
        
        @trace_governance_check(policy_name)
        async def _evaluate():
            return await original_evaluate(request)

        return await _evaluate()

    governance_engine.evaluate = traced_evaluate
    logger.info("Instrumented governance engine (evaluate)")


async def instrument_memory_substrate(substrate_service: Any) -> None:
    """
    Wrap memory substrate with observability.
    
    Instruments:
    - write_packet(packet_in, ...): Packet ingestion
    - semantic_search(request): Semantic memory search
    - get_packet(packet_id): Single packet retrieval
    """
    if not substrate_service:
        logger.debug("instrument_memory_substrate: no substrate_service provided")
        return

    instrumented_count = 0

    # Instrument write_packet if it exists
    if hasattr(substrate_service, 'write_packet'):
        original_write_packet = substrate_service.write_packet

        async def traced_write_packet(*args: Any, **kwargs: Any) -> Any:
            """Traced wrapper for write_packet."""
            @trace_span("substrate.write_packet", kind=SpanKind.CLIENT)
            async def _write_packet():
                return await original_write_packet(*args, **kwargs)

            return await _write_packet()

        substrate_service.write_packet = traced_write_packet
        instrumented_count += 1
        logger.debug("Instrumented substrate.write_packet")

    # Instrument semantic_search if it exists
    if hasattr(substrate_service, 'semantic_search'):
        original_semantic_search = substrate_service.semantic_search

        async def traced_semantic_search(request: Any) -> Any:
            """Traced wrapper for semantic_search."""
            @trace_span("substrate.semantic_search", kind=SpanKind.CLIENT)
            async def _semantic_search():
                return await original_semantic_search(request)

            return await _semantic_search()

        substrate_service.semantic_search = traced_semantic_search
        instrumented_count += 1
        logger.debug("Instrumented substrate.semantic_search")

    # Instrument get_packet if it exists
    if hasattr(substrate_service, 'get_packet'):
        original_get_packet = substrate_service.get_packet

        async def traced_get_packet(packet_id: str) -> Any:
            """Traced wrapper for get_packet."""
            @trace_span("substrate.get_packet", kind=SpanKind.CLIENT)
            async def _get_packet():
                return await original_get_packet(packet_id)

            return await _get_packet()

        substrate_service.get_packet = traced_get_packet
        instrumented_count += 1
        logger.debug("Instrumented substrate.get_packet")

    # Instrument query_packets if it exists
    if hasattr(substrate_service, 'query_packets'):
        original_query_packets = substrate_service.query_packets

        async def traced_query_packets(*args: Any, **kwargs: Any) -> Any:
            """Traced wrapper for query_packets."""
            @trace_span("substrate.query_packets", kind=SpanKind.CLIENT)
            async def _query_packets():
                return await original_query_packets(*args, **kwargs)

            return await _query_packets()

        substrate_service.query_packets = traced_query_packets
        instrumented_count += 1
        logger.debug("Instrumented substrate.query_packets")

    if instrumented_count > 0:
        logger.info(f"Instrumented memory substrate ({instrumented_count} methods)")
    else:
        logger.warning("instrument_memory_substrate: no instrumentable methods found")


async def instrument_aios_runtime(runtime_service: Any) -> None:
    """
    Wrap AIOS runtime with observability (if available).
    
    Instruments:
    - execute_reasoning(): Main reasoning loop (if exists)
    """
    if not runtime_service:
        logger.debug("instrument_aios_runtime: no runtime_service provided")
        return

    # Instrument execute_reasoning if it exists
    if hasattr(runtime_service, 'execute_reasoning'):
        original_execute_reasoning = runtime_service.execute_reasoning

        async def traced_execute_reasoning(*args: Any, **kwargs: Any) -> Any:
            """Traced wrapper for execute_reasoning."""
            @trace_span("aios.execute_reasoning", kind=SpanKind.INTERNAL)
            async def _execute_reasoning():
                return await original_execute_reasoning(*args, **kwargs)

            return await _execute_reasoning()

        runtime_service.execute_reasoning = traced_execute_reasoning
        logger.info("Instrumented AIOS runtime (execute_reasoning)")
    else:
        logger.debug("instrument_aios_runtime: runtime has no execute_reasoning method")
