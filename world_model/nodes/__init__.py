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

# ============================================================================
__dora_meta__ = {
    "component_name": "LangGraph Nodes",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2025-12-09T01:02:49Z",
    "updated_at": "2026-01-31T22:21:54Z",
    "layer": "learning",
    "domain": "world_model",
    "module_name": "__init__",
    "type": "utility",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": [],
        "memory_layers": [],
        "imported_by": [],
    },
}
# ============================================================================

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
# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "WOR-LEAR-019",
    "governance_level": "high",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": ["learning", "utility", "world-model"],
    "keywords": [
        "backed",
        "based",
        "engine",
        "integration",
        "kernel",
        "langgraph",
        "memory",
        "model",
    ],
    "business_value": "Utility module for   init  ",
    "last_modified": "2026-01-31T22:21:54Z",
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
