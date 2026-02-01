"""
L9 Session DAGs - Systematic Coding Workflows
==============================================

DAG-based orchestration for Cursor coding sessions.
Provides structured, repeatable workflows with:
- Clear phases and gates
- User confirmation checkpoints
- Validation requirements
- State persistence

Version: 1.0.0
"""

# ============================================================================
__dora_meta__ = {
    "component_name": "Systematic Coding Workflows",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2026-01-25T14:33:03Z",
    "updated_at": "2026-01-31T22:21:54Z",
    "layer": "operations",
    "domain": "workflows",
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

from workflows.session.interface import (
    GateType,
    NodeType,
    SessionDAG,
    SessionEdge,
    SessionNode,
    SessionState,
)
from workflows.session.registry import (
    get_session_dag,
    list_session_dags,
    register_session_dag,
    session_dag_registry,
)

__all__ = [
    "GateType",
    "NodeType",
    # Core types
    "SessionDAG",
    "SessionEdge",
    "SessionNode",
    "SessionState",
    "get_session_dag",
    "list_session_dags",
    "register_session_dag",
    # Registry
    "session_dag_registry",
]
# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "WOR-OPER-025",
    "governance_level": "medium",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": ["operations", "utility", "workflows"],
    "keywords": ["coding", "state", "systematic", "workflows"],
    "business_value": "Clear phases and gates User confirmation checkpoints Validation requirements State persistence Version: 1.0.0",
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
