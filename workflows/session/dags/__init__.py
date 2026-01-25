"""
Session DAGs - Auto-Discovery
=============================

Import this module to auto-register all session DAGs.

Available DAGs:
- refactoring_dag: Systematic refactoring/migration workflow
"""

# Import DAGs to trigger registration
from workflows.session.dags.refactoring_dag import REFACTORING_DAG

__all__ = [
    "REFACTORING_DAG",
]
