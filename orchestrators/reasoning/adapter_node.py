"""
L9 Reasoning Orchestrator - AdapterNode
Version: 1.1.0

Specialized component for reasoning orchestration.
Adapts reasoning engine for LangGraph node integration.
"""

from __future__ import annotations

from core.decorators import must_stay_async

# ============================================================================
__dora_meta__ = {
    "component_name": "AdapterNode",
    "module_version": "1.1.0",
    "created_by": "Igor Beylin",
    "created_at": "2025-12-09T01:02:49Z",
    "updated_at": "2026-01-07T13:35:57Z",
    "layer": "intelligence",
    "domain": "orchestration",
    "module_name": "adapter_node",
    "type": "adapter",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": [],
        "memory_layers": [],
        "imported_by": [],
    },
}
# ============================================================================

from typing import Any, TypedDict

import structlog

from .interface import ReasoningMode, ReasoningRequest
from .orchestrator import ReasoningOrchestrator

logger = structlog.get_logger(__name__)


class ReasoningNodeState(TypedDict):
    """State for reasoning LangGraph node."""

    context: str
    mode: str
    depth: int
    branch_factor: int
    result: dict[str, Any] | None
    errors: list[str]


class ReasoningAdapterNode:
    """
    AdapterNode for Reasoning Orchestrator.

    Bridges reasoning orchestrator with LangGraph execution.
    Provides both sync and async interfaces for flexibility.
    """

    def __init__(self, orchestrator: ReasoningOrchestrator | None = None):
        """
        Initialize adapter node.

        Args:
            orchestrator: Optional pre-configured orchestrator
        """
        self._orchestrator = orchestrator or ReasoningOrchestrator()
        logger.info("ReasoningAdapterNode initialized")

    @must_stay_async("callers use await")
    async def process(self, state: ReasoningNodeState) -> ReasoningNodeState:
        """
        Process state through reasoning orchestrator.

        LangGraph-compatible async node function.

        Args:
            state: ReasoningNodeState with context and parameters

        Returns:
            Updated state with reasoning result
        """
        logger.info(
            f"Processing reasoning: mode={state.get('mode', 'chain_of_thought')}"
        )

        errors = list(state.get("errors", []))

        try:
            request = ReasoningRequest(
                context=state.get("context", ""),
                mode=ReasoningMode(state.get("mode", "chain_of_thought")),
                depth=state.get("depth", 3),
                branch_factor=state.get("branch_factor", 3),
            )

            response = await self._orchestrator.execute(request)

            return {
                **state,
                "result": response.model_dump(),
                "errors": errors,
            }

        except Exception as e:
            logger.error(f"Reasoning adapter error: {e}")
            errors.append(f"reasoning_adapter error: {e!s}")
            return {
                **state,
                "result": None,
                "errors": errors,
            }

    def __call__(self, state: ReasoningNodeState) -> ReasoningNodeState:
        """
        Sync callable for LangGraph integration.

        Wraps async process for synchronous execution.
        """
        import asyncio

        loop = asyncio.get_event_loop()
        if loop.is_running():
            # Already in async context - create new loop in thread
            import concurrent.futures

            with concurrent.futures.ThreadPoolExecutor() as pool:
                return pool.submit(asyncio.run, self.process(state)).result()
        else:
            return asyncio.run(self.process(state))


def create_reasoning_node(orchestrator: ReasoningOrchestrator | None = None):
    """
    Factory function to create a reasoning LangGraph node.

    Returns an async function suitable for graph.add_node().

    Args:
        orchestrator: Optional pre-configured orchestrator

    Returns:
        Async node function
    """
    adapter = ReasoningAdapterNode(orchestrator)
    return adapter.process


# Backwards compatibility alias
AdapterNode = ReasoningAdapterNode

# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "ORC-INTE-016",
    "governance_level": "high",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": [
        "adapter",
        "adapter-pattern",
        "async",
        "event-driven",
        "intelligence",
        "logging",
        "orchestration",
    ],
    "keywords": [
        "adapter",
        "adapternode",
        "create",
        "orchestrator",
        "process",
        "reasoning",
        "state",
    ],
    "business_value": "Provides adapter node components including ReasoningNodeState, ReasoningAdapterNode",
    "last_modified": "2026-01-07T13:35:57Z",
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
