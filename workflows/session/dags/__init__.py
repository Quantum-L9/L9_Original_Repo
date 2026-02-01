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

# Legacy DAGs (dataclass-based documentation)
from workflows.session.dags.dag_authoring_dag import DAG_AUTHORING_DAG
from workflows.session.dags.gmp_execution_dag import GMP_EXECUTION_DAG
from workflows.session.dags.harvest_deploy_dag import HARVEST_DEPLOY_DAG
from workflows.session.dags.readme_pipeline_dag import README_PIPELINE_DAG
from workflows.session.dags.refactoring_dag import REFACTORING_DAG
from workflows.session.dags.slash_command_update_dag import SLASH_COMMAND_UPDATE_DAG
from workflows.session.dags.test_pipeline_dag import TEST_PIPELINE_DAG
from workflows.session.dags.wire_dag import WIRE_DAG

# Real LangGraph DAGs (executable)
from workflows.session.dags.inspect_dag import (
    INSPECT_DAG,
    InspectState,
    build_inspect_graph,
    run_inspect,
)

__all__ = [
    # Real LangGraph (use these)
    "INSPECT_DAG",
    "InspectState",
    "build_inspect_graph",
    "run_inspect",
    # Legacy (to be migrated)
    "DAG_AUTHORING_DAG",
    "GMP_EXECUTION_DAG",
    "HARVEST_DEPLOY_DAG",
    "README_PIPELINE_DAG",
    "REFACTORING_DAG",
    "SLASH_COMMAND_UPDATE_DAG",
    "TEST_PIPELINE_DAG",
    "WIRE_DAG",
]
