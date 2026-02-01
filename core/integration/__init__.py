"""
L9 Core Integration Package
===========================

Cross-system integration services for the Unified Knowledge Graph.

This package contains services that synchronize state between:
- Neo4j Graph State (agent identity, tools, relationships)
- World Model (PostgreSQL entity store)
- Memory Substrate (packet store, insights)

Exports:
- GraphToWorldModelSync: Sync agent state from Neo4j to World Model
- WMToGraphSync: Sync causal data from World Model to Neo4j

Version: 1.1.0
Created: 2026-01-05
Updated: 2026-01-16 (added WMToGraphSync)
"""

# ============================================================================
__dora_meta__ = {
    "component_name": "  Init  ",
    "module_version": "1.1.0",
    "created_by": "Igor Beylin",
    "created_at": "2026-01-06T15:07:54Z",
    "updated_at": "2026-01-31T22:21:46Z",
    "layer": "foundation",
    "domain": "core",
    "module_name": "__init__",
    "type": "utility",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": ["Neo4j", "PostgreSQL"],
        "memory_layers": [],
        "imported_by": [],
    },
}
# ============================================================================

from .graph_to_wm_sync import GraphToWorldModelSync
from .tool_pattern_extractor import ToolPatternExtractor
from .wm_to_graph_sync import WMToGraphSync, start_wm_graph_sync, stop_wm_graph_sync

__all__ = [
    "GraphToWorldModelSync",
    "ToolPatternExtractor",
    "WMToGraphSync",
    "start_wm_graph_sync",
    "stop_wm_graph_sync",
]
# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "COR-FOUN-067",
    "governance_level": "critical",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": ["core", "foundation", "graph-db", "utility"],
    "keywords": [
        "agent",
        "graph",
        "integration",
        "memory",
        "model",
        "package",
        "services",
        "state",
    ],
    "business_value": "Neo4j Graph State (agent identity, tools, relationships) World Model (PostgreSQL entity store) Memory Substrate (packet store, insights) GraphToWorldModelSync: Sync agent state from Neo4j to World Mod",
    "last_modified": "2026-01-31T22:21:46Z",
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
