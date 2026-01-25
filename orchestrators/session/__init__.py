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

from orchestrators.session.interface import (
    SessionDAG,
    SessionNode,
    SessionEdge,
    SessionState,
    NodeType,
    GateType,
)
from orchestrators.session.registry import (
    session_dag_registry,
    register_session_dag,
    get_session_dag,
    list_session_dags,
)

__all__ = [
    # Core types
    "SessionDAG",
    "SessionNode",
    "SessionEdge",
    "SessionState",
    "NodeType",
    "GateType",
    # Registry
    "session_dag_registry",
    "register_session_dag",
    "get_session_dag",
    "list_session_dags",
]
