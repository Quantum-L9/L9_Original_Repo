"""
L9 World Model - LangGraph Nodes
================================

LangGraph node implementations for World Model integration.

Specification Sources:
- WorldModelOS.yaml → graph_nodes
- world_model_layer.yaml → langgraph_integration
- reasoning kernel 01-05 (node reasoning)

These nodes enable World Model operations within LangGraph DAGs:
- update_world_model_node: Apply memory packets to world model (engine-based)
- world_model_service_update_node: Update from insights (service-based, DB-backed)
- world_model_snapshot_node: Create state snapshots
- world_model_query_node: Query entities

Integration:
- LangGraph: nodes added to StateGraph
- Memory Substrate: receives packets from memory
- WorldModelEngine: delegates to engine methods
- WorldModelService: DB-backed operations (v1.0.0+)
"""

# Service-based nodes (v1.0.0+ with DB persistence)
from world_model.nodes.service_nodes import (
    WorldModelGraphState,
    create_insights_from_facts,
    world_model_query_node,
    world_model_service_update_node,
    world_model_snapshot_node,
)

# Engine-based node (original)
from world_model.nodes.update_world_model_node import (
    WorldModelNodeState,
    update_world_model_node,
)

__all__ = [
    "WorldModelGraphState",
    "WorldModelNodeState",
    "create_insights_from_facts",
    # Engine-based
    "update_world_model_node",
    "world_model_query_node",
    # Service-based (DB-backed)
    "world_model_service_update_node",
    "world_model_snapshot_node",
]
