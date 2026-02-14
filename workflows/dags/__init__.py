"""
Session DAGs - Auto-Discovery
=============================

Import this module to auto-register all session DAGs.

DAGs are being migrated from fake dataclass-based "documentation DAGs"
to real executable LangGraph DAGs.

REAL LangGraph DAGs (executable):
- inspect_dag: Unified first-touch analysis + evaluation + routing

LEGACY dataclass DAGs (documentation only - TO BE MIGRATED):
- dag_authoring_dag, gmp_execution_dag, harvest_deploy_dag, etc.
"""

# ============================================================================
__dora_meta__ = {
    "component_name": "Auto-Discovery",
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

# Legacy DAGs (dataclass-based documentation)
from workflows.dags.component_audit_dag import COMPONENT_AUDIT_DAG
from workflows.dags.confirm_wiring_dag import CONFIRM_WIRING_DAG
from workflows.dags.dag_authoring_dag import DAG_AUTHORING_DAG
from workflows.dags.gmp_execution_dag import GMP_EXECUTION_DAG
from workflows.dags.harvest_deploy_dag import HARVEST_DEPLOY_DAG

# Real LangGraph DAGs (executable)
from workflows.dags.inspect_dag import (
    INSPECT_DAG,
    InspectState,
    build_inspect_graph,
    run_inspect,
)
from workflows.dags.readme_pipeline_dag import README_PIPELINE_DAG
from workflows.dags.refactoring_dag import REFACTORING_DAG
from workflows.dags.slash_command_update_dag import SLASH_COMMAND_UPDATE_DAG
from workflows.dags.test_pipeline_dag import TEST_PIPELINE_DAG
from workflows.dags.wire_dag import WIRE_DAG

__all__ = [
    "COMPONENT_AUDIT_DAG",
    "CONFIRM_WIRING_DAG",
    "DAG_AUTHORING_DAG",
    "GMP_EXECUTION_DAG",
    "HARVEST_DEPLOY_DAG",
    "INSPECT_DAG",
    "README_PIPELINE_DAG",
    "REFACTORING_DAG",
    "SLASH_COMMAND_UPDATE_DAG",
    "TEST_PIPELINE_DAG",
    "WIRE_DAG",
    "InspectState",
    "build_inspect_graph",
    "run_inspect",
]
# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "WOR-OPER-031",
    "governance_level": "medium",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": ["operations", "testing", "utility", "workflows"],
    "keywords": [
        "analysis",
        "auto",
        "dags",
        "dataclass",
        "discovery",
        "documentation",
        "executable",
        "langgraph",
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
