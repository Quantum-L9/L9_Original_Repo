"""
Graph-Backed Agent State
========================

Neo4j-based agent state management replacing static YAML kernel loading.
Enables real-time self-modification, faster startup, and full audit trails.

Exports:
- AgentGraphLoader: Load agent state from Neo4j
- GraphHydrator: Convert graph to AgentInstance
- bootstrap_l_graph: One-time graph initialization

Version: 1.0.0
Created: 2026-01-05
"""

# ============================================================================
__dora_meta__ = {
    "component_name": "  Init  ",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2026-01-06T15:07:54Z",
    "updated_at": "2026-01-31T22:21:47Z",
    "layer": "foundation",
    "domain": "agent_execution",
    "module_name": "__init__",
    "type": "utility",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": ["Neo4j"],
        "memory_layers": [],
        "imported_by": [],
    },
}
# ============================================================================

from .agent_graph_loader import AgentGraphLoader
from .bootstrap_l_graph import bootstrap_l_graph
from .graph_hydrator import GraphHydrator
from .schema import (  # UKG Phase 2: Shared queries for Tool Graph
    AGENT_LABEL,
    DIRECTIVE_LABEL,
    ENSURE_AGENT_QUERY,
    GET_AGENT_QUERY,
    LOAD_AGENT_STATE_QUERY,
    RESPONSIBILITY_LABEL,
    SOP_LABEL,
    TOOL_LABEL,
)

__all__ = [
    "AGENT_LABEL",
    "DIRECTIVE_LABEL",
    # UKG Phase 2
    "ENSURE_AGENT_QUERY",
    "GET_AGENT_QUERY",
    "LOAD_AGENT_STATE_QUERY",
    "RESPONSIBILITY_LABEL",
    "SOP_LABEL",
    "TOOL_LABEL",
    "AgentGraphLoader",
    "GraphHydrator",
    "bootstrap_l_graph",
]
# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "COR-FOUN-242",
    "governance_level": "critical",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": ["agent-execution", "audit-tool", "foundation", "graph-db", "utility"],
    "keywords": ["agent", "audit", "graph", "kernel", "state", "time"],
    "business_value": "Utility module for   init  ",
    "last_modified": "2026-01-31T22:21:47Z",
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
