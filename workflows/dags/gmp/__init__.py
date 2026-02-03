"""
GMP Package — Modular GMP execution DAG

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

Usage:
    from workflows.dags.gmp import GMPLangGraphExecutor

    executor = GMPLangGraphExecutor()
    result = executor.run("task description", tier="RUNTIME")
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
