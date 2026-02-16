"""
GMP Package — Modular GMP execution DAG

Autonomous GMP execution for L/Emma agents via LangGraph StateGraph.
See README.md for architecture and usage.

Structure:
    gmp/
    ├── __init__.py      # This file
    ├── state.py         # GMPState, GMPPhase
    ├── routing.py       # Conditional routing functions
    ├── graph.py         # build_gmp_graph()
    ├── executor.py      # GMPLangGraphExecutor, main()
    └── nodes/
        ├── __init__.py
        └── core.py      # All node functions

Usage (SDK — preferred):
    sdk = L9SDK(agent_id="emma", tenant_id="l9")
    result = await sdk.workflows.run_dag("gmp-execution-v1", task="...", tier="RUNTIME")

Usage (direct):
    from workflows.dags.gmp import GMPLangGraphExecutor

    executor = GMPLangGraphExecutor()
    result = executor.run("task description", tier="RUNTIME", todo_plan=[...])

Usage (CLI):
    python3 -m workflows.dags.gmp.executor "task" --tier RUNTIME
"""

from workflows.dags.gmp.executor import GMPLangGraphExecutor, main
from workflows.dags.gmp.graph import build_gmp_graph
from workflows.dags.gmp.state import GMPPhase, GMPState

__all__ = [
    "GMPLangGraphExecutor",
    "GMPPhase",
    "GMPState",
    "build_gmp_graph",
    "main",
]
