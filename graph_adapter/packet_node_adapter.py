"""
L9 LangGraph - Packet Node Adapter
Version: 1.0.0

Helpers to wrap arbitrary LangGraph node functions so they:
- emit PacketEnvelopes via MemorySubstrateService
- optionally log reasoning traces
"""

from __future__ import annotations

from typing import Any, Awaitable, Callable, Dict, TYPE_CHECKING

from core.schemas.packet_envelope_v2 import PacketEnvelopeIn

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
