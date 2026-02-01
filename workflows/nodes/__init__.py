"""
Workflow Nodes — Reusable LangGraph node implementations.

Each node:
- Accepts WorkflowState
- Returns partial state update
- Is async for non-blocking execution
- Logs structured output
"""

# ============================================================================
__dora_meta__ = {
    "component_name": "  Init  ",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2026-01-25T14:45:56Z",
    "updated_at": "2026-01-31T22:21:53Z",
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

from workflows.nodes.checkpoint import checkpoint_node
from workflows.nodes.deploy import deploy_files_node
from workflows.nodes.extract import extract_files_node
from workflows.nodes.inject import inject_files_node
from workflows.nodes.report import report_node
from workflows.nodes.validate import validate_node

__all__ = [
    "checkpoint_node",
    "deploy_files_node",
    "extract_files_node",
    "inject_files_node",
    "report_node",
    "validate_node",
]
# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "WOR-OPER-018",
    "governance_level": "medium",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": ["operations", "utility", "workflows"],
    "keywords": ["state"],
    "business_value": "Utility module for   init  ",
    "last_modified": "2026-01-31T22:21:53Z",
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
