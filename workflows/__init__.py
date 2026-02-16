"""
L9 Workflows — DAG-Based Workflow Orchestration
================================================

Production-grade workflow orchestration with two complementary systems:

1. **Session DAGs** (workflows.session)
   - Python-defined workflow graphs
   - Human-readable, self-documenting
   - Mermaid diagram generation
   - Step-by-step execution guides

2. **LangGraph Execution** (workflows.harvest_deploy)
   - StateGraph-based runtime
   - Async execution
   - State persistence
   - Programmatic API

Structure:
    workflows/
    ├── session/              # Session DAG definitions
    │   ├── interface.py      # SessionDAG, SessionNode, SessionEdge
    │   ├── registry.py       # DAG registry
    │   └── dags/             # DAG definitions
    │       ├── refactoring_dag.py
    │       └── harvest_deploy_dag.py
    ├── state.py              # LangGraph state schemas
    ├── nodes/                # LangGraph reusable nodes
    ├── harvest_deploy.py     # LangGraph StateGraph
    ├── runner.py             # YAML-based CLI runner
    └── defs/                 # Simple YAML definitions

Usage:
    # Session DAG (documentation/planning)
    from workflows.session import get_session_dag
    dag = get_session_dag("harvest-deploy-v1")
    print(dag.to_mermaid())  # noqa: ADR-0019

    # LangGraph Execution (runtime)
    from workflows.harvest_deploy import run_harvest_deploy
    result = await run_harvest_deploy(source_document="...", ...)

    # YAML Runner (CLI)
    python -m workflows.runner run workflow.yaml

Author: L9 Team
"""

# ============================================================================
__dora_meta__ = {
    "component_name": "  Init  ",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2026-01-25T14:45:56Z",
    "updated_at": "2026-01-31T22:27:11Z",
    "layer": "operations",
    "domain": "workflows",
    "module_name": "__init__",
    "type": "utility",
    "status": "production",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": [],
        "memory_layers": [],
        "imported_by": [],
    },
}
# ============================================================================

# === LangGraph State & Types ===
# These work with or without LangGraph installed
from workflows.state import (
    ExtractionPattern,
    FileMapping,
    StepResult,
    StepStatus,
    ValidationCheck,
    WorkflowState,
    create_initial_state,
)

# LangGraph execution is available when langgraph is installed
_LANGGRAPH_AVAILABLE = False
try:
    from langgraph.graph import StateGraph

    _LANGGRAPH_AVAILABLE = True
except ImportError:
    pass

# === Session DAG System ===
# Trigger DAG auto-registration
from workflows import dags as _dags
from workflows.session import (
    GateType,
    NodeType,
    SessionDAG,
    SessionEdge,
    SessionNode,
    SessionState,
    get_session_dag,
    list_session_dags,
    register_session_dag,
    session_dag_registry,
)

__all__ = [
    "NodeType",
    # Session DAG
    "SessionState",
    "StepResult",
    "StepStatus",
    "create_initial_state",
]
# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "WOR-OPER-005",
    "governance_level": "medium",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": ["api", "auth", "operations", "utility", "workflows"],
    "keywords": [
        "based",
        "dags",
        "definitions",
        "execution",
        "langgraph",
        "nodes",
        "orchestration",
        "python",
    ],
    "business_value": "1. **Session DAGs** (workflows.session) Python-defined workflow graphs Human-readable, self-documenting Mermaid diagram generation Step-by-step execution guides 2. **LangGraph Execution** (workflows.h",
    "last_modified": "2026-01-31T22:27:11Z",
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
