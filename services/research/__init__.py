"""
L9 Research Factory Service
Version: 1.0.0

Multi-agent research orchestration using LangGraph, integrated with L9 Memory Substrate.

Provides:
- Planner Agent: Decomposes research goals into steps
- Researcher Agent: Gathers evidence via tools
- Critic Agent: Evaluates research quality
- Research Graph: DAG orchestrating the multi-agent workflow
- /research API endpoint
"""

# ============================================================================
__dora_meta__ = {
    "component_name": "  Init  ",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2025-12-09T01:02:49Z",
    "updated_at": "2026-01-31T22:22:00Z",
    "layer": "operations",
    "domain": "research_services",
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

from services.research.graph_persistence import (
    FindingType,
    GraphPersistenceConfig,
    ResearchFinding,
    ResearchGraphPersistence,
    create_graph_persistence,
    get_graph_persistence,
    init_graph_persistence,
)
from services.research.graph_runtime import (
    ResearchGraphRuntime,
    get_runtime,
    init_runtime,
    shutdown_runtime,
)
from services.research.graph_state import (
    Evidence,
    ResearchGraphState,
    ResearchStep,
    create_initial_state,
)
from services.research.memory_adapter import (
    ResearchMemoryAdapter,
    get_memory_adapter,
    init_memory_adapter,
)
from services.research.research_api import router as research_router
from services.research.research_graph import build_research_graph, run_research

__all__ = [
    "Evidence",
    "FindingType",
    "GraphPersistenceConfig",
    "ResearchFinding",
    # Graph Persistence
    "ResearchGraphPersistence",
    # Runtime
    "ResearchGraphRuntime",
    # State
    "ResearchGraphState",
    # Memory
    "ResearchMemoryAdapter",
    "ResearchStep",
    # Graph
    "build_research_graph",
    "create_graph_persistence",
    "create_initial_state",
    "get_graph_persistence",
    "get_memory_adapter",
    "get_runtime",
    "init_graph_persistence",
    "init_memory_adapter",
    "init_runtime",
    # API
    "research_router",
    "run_research",
    "shutdown_runtime",
]

__version__ = "1.0.0"
# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "SER-OPER-013",
    "governance_level": "medium",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": ["operations", "research-services", "utility"],
    "keywords": ["agent", "memory", "multi", "research", "service", "substrate"],
    "business_value": "Planner Agent: Decomposes research goals into steps Researcher Agent: Gathers evidence via tools Critic Agent: Evaluates research quality Research Graph: DAG orchestrating the multi-agent workflow /re",
    "last_modified": "2026-01-31T22:22:00Z",
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
