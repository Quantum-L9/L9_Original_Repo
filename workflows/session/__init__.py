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
