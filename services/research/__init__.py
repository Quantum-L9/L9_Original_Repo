"""
L9 Research Factory Service
Version: 1.0.0

Multi-agent research orchestration using LangGraph, integrated with L9 Memory Substrate.

Provides:
- Planner Agent: Decomposes research goals into steps
- Researcher Agent: Gathers evidence via tools
- Critic Agent: Evaluates research quality
- Research Graph: DAG orchestrating the multi-agent workflow
- /research API endpoint
"""

from services.research.graph_persistence import (FindingType,
                                                 GraphPersistenceConfig,
                                                 ResearchFinding,
                                                 ResearchGraphPersistence,
                                                 create_graph_persistence,
                                                 get_graph_persistence,
                                                 init_graph_persistence)
from services.research.graph_runtime import (ResearchGraphRuntime, get_runtime,
                                             init_runtime, shutdown_runtime)
from services.research.graph_state import (Evidence, ResearchGraphState,
                                           ResearchStep, create_initial_state)
from services.research.memory_adapter import (ResearchMemoryAdapter,
                                              get_memory_adapter,
                                              init_memory_adapter)
from services.research.research_api import router as research_router
from services.research.research_graph import build_research_graph, run_research

__all__ = [
    # State
    "ResearchGraphState",
    "ResearchStep",
    "Evidence",
    "create_initial_state",
    # Memory
    "ResearchMemoryAdapter",
    "get_memory_adapter",
    "init_memory_adapter",
    # Graph
    "build_research_graph",
    "run_research",
    # Runtime
    "ResearchGraphRuntime",
    "get_runtime",
    "init_runtime",
    "shutdown_runtime",
    # API
    "research_router",
    # Graph Persistence
    "ResearchGraphPersistence",
    "ResearchFinding",
    "FindingType",
    "GraphPersistenceConfig",
    "create_graph_persistence",
    "get_graph_persistence",
    "init_graph_persistence",
]

__version__ = "1.0.0"
