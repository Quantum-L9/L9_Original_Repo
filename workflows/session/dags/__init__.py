"""
Session DAGs - Auto-Discovery
=============================

Import this module to auto-register all session DAGs.

Available DAGs:
- refactoring_dag: Systematic refactoring/migration workflow
- harvest_deploy_dag: Harvest code from docs and deploy
- readme_pipeline_dag: README generation and validation
"""

# Import DAGs to trigger registration
from workflows.session.dags.harvest_deploy_dag import HARVEST_DEPLOY_DAG
from workflows.session.dags.readme_pipeline_dag import README_PIPELINE_DAG
from workflows.session.dags.refactoring_dag import REFACTORING_DAG

__all__ = [
    "HARVEST_DEPLOY_DAG",
    "README_PIPELINE_DAG",
    "REFACTORING_DAG",
]
