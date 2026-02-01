"""
L9 Memory Checkpoint Module
Version: 1.0.0

Checkpoint management for LangGraph and Cursor integrations.
"""

# ============================================================================
__dora_meta__ = {
    "component_name": "  Init  ",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2026-01-11T18:13:39Z",
    "updated_at": "2026-01-31T22:21:48Z",
    "layer": "learning",
    "domain": "memory_substrate",
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

from memory.checkpoint.cursor_checkpoint_manager import CursorCheckpointManager
from memory.checkpoint.postgres_saver import L9PostgresSaver

__all__ = [
    "CursorCheckpointManager",
    "L9PostgresSaver",
]
# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "MEM-LEAR-070",
    "governance_level": "critical",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [
        "memory.checkpoint.cursor_checkpoint_manager",
        "memory.checkpoint.postgres_saver",
    ],
    "tags": ["learning", "memory-substrate", "utility"],
    "keywords": ["checkpoint", "memory", "module"],
    "business_value": "Utility module for   init  ",
    "last_modified": "2026-01-31T22:21:48Z",
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
