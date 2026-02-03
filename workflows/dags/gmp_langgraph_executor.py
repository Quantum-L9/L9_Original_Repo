"""
GMP LangGraph Executor — Backwards Compatibility Shim
=====================================================

This file maintains backwards compatibility.
The actual implementation is now modular in workflows/dags/gmp/

Structure:
    workflows/dags/gmp/
    ├── state.py         # GMPState, GMPPhase (~85 lines)
    ├── routing.py       # Conditional routing (~25 lines)
    ├── graph.py         # build_gmp_graph() (~80 lines)
    ├── executor.py      # GMPLangGraphExecutor, CLI (~135 lines)
    └── nodes/
        └── core.py      # All node functions (~235 lines)

Usage:
    python3 workflows/dags/gmp_langgraph_executor.py "task" --tier RUNTIME

    OR (preferred):
    python3 -m workflows.dags.gmp.executor "task" --tier RUNTIME
"""

import sys
from pathlib import Path

# Add workspace root to path for direct script execution
_workspace = Path(__file__).parent.parent.parent
if str(_workspace) not in sys.path:
    sys.path.insert(0, str(_workspace))

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
    node_user_confirm_scope,
    node_user_confirm_validation,
    node_validate,
)
from workflows.dags.gmp.routing import (
    route_after_scope_confirm,
    route_after_validation_confirm,
)

__all__ = [
    # State
    "GMPState",
    "GMPPhase",
    # Nodes
    "node_start",
    "node_memory_read",
    "node_scope_lock",
    "node_user_confirm_scope",
    "node_baseline",
    "node_implement",
    "node_validate",
    "node_user_confirm_validation",
    "node_memory_write",
    "node_finalize",
    "node_end",
    "node_aborted",
    # Routing
    "route_after_scope_confirm",
    "route_after_validation_confirm",
    # Graph
    "build_gmp_graph",
    # Executor
    "GMPLangGraphExecutor",
    "main",
]

if __name__ == "__main__":
    main()
