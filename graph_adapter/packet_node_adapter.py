"""
L9 LangGraph - Packet Node Adapter
Version: 1.0.0

Helpers to wrap arbitrary LangGraph node functions so they:
- emit PacketEnvelopes via MemorySubstrateService
- optionally log reasoning traces
"""

from __future__ import annotations

# ============================================================================
__dora_meta__ = {
    "component_name": "Packet Node Adapter",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2025-12-09T01:02:49Z",
    "updated_at": "2026-01-14T13:21:36Z",
    "layer": "integration",
    "domain": "graph_integration",
    "module_name": "packet_node_adapter",
    "type": "adapter",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": [],
        "memory_layers": ["working_memory"],
        "imported_by": ["graph_adapter.__init__"],
    },
}
# ============================================================================

from typing import Any, Awaitable, Callable, Dict, TYPE_CHECKING

from core.schemas import PacketEnvelopeIn

# Lazy import to avoid circular dependency with memory module
if TYPE_CHECKING:
    from memory.substrate_service import MemorySubstrateService


def _get_memory_service():
    """Lazy import of MemorySubstrateService to avoid circular imports."""
    from memory.substrate_service import MemorySubstrateService

    return MemorySubstrateService


GraphState = Dict[str, Any]
NodeFn = Callable[[GraphState], Awaitable[GraphState]]


class PacketNodeAdapter:
    """
    Wraps a node function, ensuring its input/output are logged to memory
    via PacketEnvelopeIn + MemorySubstrateService.write_packet.
    """

    def __init__(
        self,
        service: MemorySubstrateService,
        agent_id: str,
        event_type: str = "graph_node",
    ) -> None:
        self._service = service
        self._agent_id = agent_id
        self._event_type = event_type

    async def __call__(
        self, state: GraphState, node: NodeFn, node_name: str
    ) -> GraphState:
        """
        Execute the node, logging before/after packets to the substrate.

        This is intended for manual wiring inside a StateGraph, e.g.:

            adapter = PacketNodeAdapter(service, agent_id="l9_research")
            async def wrapped(state): return await adapter(state, my_node, "my_node")
        """
        # Pre-node packet
        pre_packet = PacketEnvelopeIn(
            packet_type="event",
            payload={
                "kind": self._event_type,
                "phase": "before",
                "node": node_name,
                "state": state,
            },
            metadata={"agent": self._agent_id},
        )
        await self._service.write_packet(pre_packet)

        # Run node
        new_state = await node(state)

        # Post-node packet
        post_packet = PacketEnvelopeIn(
            packet_type="event",
            payload={
                "kind": self._event_type,
                "phase": "after",
                "node": node_name,
                "state": new_state,
            },
            metadata={"agent": self._agent_id},
        )
        await self._service.write_packet(post_packet)

        return new_state


# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "GRA-INTE-001",
    "governance_level": "medium",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": ["core.schemas", "memory.substrate_service"],
    "tags": [
        "adapter",
        "adapter-pattern",
        "async",
        "event-driven",
        "graph-integration",
        "integration",
        "tracing",
    ],
    "keywords": ["adapter", "langgraph", "packet", "wrapped"],
    "business_value": "Implements PacketNodeAdapter for packet node adapter functionality",
    "last_modified": "2026-01-14T13:21:36Z",
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
