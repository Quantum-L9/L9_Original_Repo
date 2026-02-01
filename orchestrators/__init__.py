"""
L9 Orchestrator Layer
=====================

Central nervous system for L9 agent coordination.
7 specialized orchestrators for different system aspects.

Version: 1.0.0
"""

# ============================================================================
__dora_meta__ = {
    "component_name": "  Init  ",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2025-12-09T01:02:49Z",
    "updated_at": "2026-01-31T22:21:55Z",
    "layer": "intelligence",
    "domain": "orchestration",
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

from .action_tool.orchestrator import ActionToolOrchestrator
from .evolution.orchestrator import EvolutionOrchestrator
from .memory.orchestrator import MemoryOrchestrator
from .meta.orchestrator import MetaOrchestrator
from .reasoning.orchestrator import ReasoningOrchestrator
from .research_swarm.orchestrator import ResearchSwarmOrchestrator
from .world_model.orchestrator import WorldModelOrchestrator

# WebSocket Bridge (Phase 2.5)
from .ws_bridge import (
    WSBridgeConfig,
    WSEventRouter,
    enqueue_ws_event,
    event_to_task,
    handle_ws_event,
)

__all__ = [
    "ActionToolOrchestrator",
    "EvolutionOrchestrator",
    "MemoryOrchestrator",
    "MetaOrchestrator",
    "ReasoningOrchestrator",
    "ResearchSwarmOrchestrator",
    "WSBridgeConfig",
    "WSEventRouter",
    "WorldModelOrchestrator",
    "enqueue_ws_event",
    # WebSocket Bridge
    "event_to_task",
    "handle_ws_event",
]
# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "ORC-INTE-003",
    "governance_level": "high",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": ["memory.orchestrator"],
    "tags": [
        "event-driven",
        "intelligence",
        "orchestration",
        "queue",
        "realtime",
        "utility",
    ],
    "keywords": ["agent", "orchestrator", "system"],
    "business_value": "Utility module for   init  ",
    "last_modified": "2026-01-31T22:21:55Z",
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
