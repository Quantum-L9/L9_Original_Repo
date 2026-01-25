"""
Session DAGs - Auto-Discovery
=============================

Import this module to auto-register all session DAGs.

Available DAGs:
- refactoring_dag: Systematic refactoring/migration workflow
- harvest_deploy_dag: Harvest code from docs and deploy
"""

# Import DAGs to trigger registration
from workflows.session.dags.harvest_deploy_dag import HARVEST_DEPLOY_DAG
from workflows.session.dags.refactoring_dag import REFACTORING_DAG

__all__ = [
    "HARVEST_DEPLOY_DAG",
    "REFACTORING_DAG",
]
