"""
GMP LangGraph Executor — Backwards Compatibility Shim
=====================================================

This file maintains backwards compatibility.
The actual implementation is in workflows/dags/gmp/

Usage:
    python3 workflows/dags/gmp_langgraph_executor.py "task" --tier RUNTIME

    OR (preferred):
    python3 -m workflows.dags.gmp.executor "task" --tier RUNTIME
"""

# Re-export everything from the modular package
from workflows.dags.gmp import (
    GMPLangGraphExecutor,
    GMPPhase,
    GMPState,
    build_gmp_graph,
    main,
)
from workflows.dags.gmp.nodes import (
    node_aborted,
    node_baseline,
    node_end,
    node_finalize,
    node_implement,
    node_memory_read,
    node_memory_write,
    node_scope_lock,
    node_start,
    node_validate,
)
from workflows.dags.gmp.routing import (
    route_after_scope_lock,
    route_after_validation,
)

__all__ = [
    "GMPLangGraphExecutor",
    "GMPPhase",
    "GMPState",
    "build_gmp_graph",
    "main",
    "node_aborted",
    "node_baseline",
    "node_end",
    "node_finalize",
    "node_implement",
    "node_memory_read",
    "node_memory_write",
    "node_scope_lock",
    "node_start",
    "node_validate",
    "route_after_scope_lock",
    "route_after_validation",
]

if __name__ == "__main__":
    main()
