"""
L9 World Model - Update World Model Node
========================================

LangGraph node for updating the World Model from memory packets.

Specification Sources:
- WorldModelOS.yaml → update_node
- world_model_layer.yaml → langgraph_integration
- reasoning kernel 04 (update reasoning)

This node:
1. Receives memory packets from graph state
2. Routes them to WorldModelEngine.update_from_packet()
3. Returns updated state with results

Integration:
- LangGraph: added to StateGraph via graph.add_node()
- Memory Substrate: packets from memory client
- WorldModelEngine: delegates update logic
- Research Graph: can be wired after store_insights
"""

from __future__ import annotations

# ============================================================================
__dora_meta__ = {
    "component_name": "Update World Model Node",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2025-12-09T01:02:49Z",
    "updated_at": "2026-01-17T23:47:57Z",
    "layer": "learning",
    "domain": "world_model",
    "module_name": "update_world_model_node",
    "type": "service",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": [],
        "memory_layers": ["working_memory"],
        "imported_by": ["world_model.nodes.__init__"],
    },
}
# ============================================================================

import structlog
from typing import Any, Optional, TypedDict

from world_model.engine import get_world_model_engine
from core.decorators import must_stay_async

logger = structlog.get_logger(__name__)


# =============================================================================
# Node State Definition
# =============================================================================


class WorldModelNodeState(TypedDict, total=False):
    """
    State schema for World Model LangGraph nodes.

    Specification: WorldModelOS.yaml → node_state

    This state is passed through the LangGraph DAG.
    Compatible with ResearchGraphState for integration.
    """

    # Input: packets to process
    world_model_packets: list[dict[str, Any]]

    # Output: update results
    world_model_updates: list[dict[str, Any]]

    # State snapshot (optional)
    world_model_snapshot: Optional[dict[str, Any]]

    # Errors
    world_model_errors: list[str]

    # Metadata
    thread_id: str


# =============================================================================
# Node Implementation
# =============================================================================


@must_stay_async("callers use await")
async def update_world_model_node(
    state: WorldModelNodeState,
) -> WorldModelNodeState:
    """
    LangGraph node that updates the World Model from memory packets.

    Specification Sources:
    - WorldModelOS.yaml → update_node
    - world_model_layer.yaml → langgraph_node
    - reasoning kernel 04 (update reasoning)

    Flow:
    1. Extract packets from state.world_model_packets
    2. For each packet, call engine.update_from_packet()
    3. Collect results in state.world_model_updates
    4. Optionally snapshot state
    5. Return updated state

    Usage in graph:
        graph.add_node("update_world_model", update_world_model_node)
        graph.add_edge("store_insights", "update_world_model")

    Args:
        state: WorldModelNodeState with:
            - world_model_packets: list of PacketEnvelope payloads

    Returns:
        Updated WorldModelNodeState with:
            - world_model_updates: list of update results
            - world_model_errors: any errors encountered
    """
    logger.info(f"update_world_model_node: thread={state.get('thread_id')}")

    updates: list[dict[str, Any]] = []
    errors: list[str] = []

    # Get packets to process
    packets = state.get("world_model_packets", [])

    if not packets:
        logger.debug("No packets to process")
        return {
            **state,
            "world_model_updates": [],
            "world_model_errors": [],
        }

    # Get engine
    engine = get_world_model_engine()

    # Check initialization
    if not engine.is_initialized:
        error = "WorldModelEngine not initialized"
        logger.warning(error)
        return {
            **state,
            "world_model_updates": [],
            "world_model_errors": [error],
        }

    # Process each packet
    for i, packet in enumerate(packets):
        try:
            logger.debug(f"Processing packet {i + 1}/{len(packets)}")

            # Delegate to engine
            result = engine.update_from_packet(packet)

            updates.append(
                {
                    "packet_index": i,
                    "packet_type": packet.get("packet_type", "unknown"),
                    "result": result,
                }
            )

        except Exception as e:
            error_msg = f"Failed to process packet {i}: {str(e)}"
            logger.error(error_msg)
            errors.append(error_msg)

    # Log summary
    success_count = len([u for u in updates if u.get("result", {}).get("success")])
    logger.info(f"Processed {len(packets)} packets: {success_count} succeeded")

    return {
        **state,
        "world_model_updates": updates,
        "world_model_errors": state.get("world_model_errors", []) + errors,
    }


# =============================================================================
# Helper Functions
# =============================================================================


def create_world_model_packets_from_insights(
    insights: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """
    Convert stored insights to world model packets.

    Helper for bridging store_insights → update_world_model.

    Args:
        insights: List of insights from store_insights_node

    Returns:
        List of packets formatted for world model update
    """
    packets = []

    for insight in insights:
        packet = {
            "packet_type": "insight",
            "payload": {
                "insight_type": insight.get("insight_type", "general"),
                "content": insight.get("content", ""),
                "packet_id": insight.get("packet_id"),
            },
        }
        packets.append(packet)

    return packets

# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "WOR-LEAR-018",
    "governance_level": "high",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": ["core.decorators"],
    "tags": ["async", "debugging", "learning", "logging", "service", "world-model"],
    "keywords": ["create", "graph", "insights", "kernel", "langgraph", "memory", "model", "packets"],
    "business_value": "1. Receives memory packets from graph state 2. Routes them to WorldModelEngine.update_from_packet() 3. Returns updated state with results LangGraph: added to StateGraph via graph.add_node() Memory Sub",
    "last_modified": "2026-01-17T23:47:57Z",
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
