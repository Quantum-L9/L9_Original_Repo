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
    print(dag.to_mermaid())

    # LangGraph Execution (runtime)
    from workflows.harvest_deploy import run_harvest_deploy
    result = await run_harvest_deploy(source_document="...", ...)

    # YAML Runner (CLI)
    python -m workflows.runner run workflow.yaml

Author: L9 Team
"""

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

# Trigger DAG auto-registration
from workflows.session import dags as _dags

__all__ = [
    "ExtractionPattern",
    "FileMapping",
    "GateType",
    "NodeType",
    # Session DAG
    "SessionDAG",
    "SessionEdge",
    "SessionNode",
    "SessionState",
    "StepResult",
    "StepStatus",
    "ValidationCheck",
    # LangGraph State
    "WorkflowState",
    "create_initial_state",
    "get_session_dag",
    "list_session_dags",
    "register_session_dag",
    "session_dag_registry",
]
