"""
Graph-Backed Agent State
========================

Neo4j-based agent state management replacing static YAML kernel loading.
Enables real-time self-modification, faster startup, and full audit trails.

Exports:
- AgentGraphLoader: Load agent state from Neo4j
- GraphHydrator: Convert graph to AgentInstance
- bootstrap_l_graph: One-time graph initialization

Version: 1.0.0
Created: 2026-01-05
"""

from .agent_graph_loader import AgentGraphLoader
from .bootstrap_l_graph import bootstrap_l_graph
from .graph_hydrator import GraphHydrator
from .schema import (AGENT_LABEL,  # UKG Phase 2: Shared queries for Tool Graph
                     DIRECTIVE_LABEL, ENSURE_AGENT_QUERY, GET_AGENT_QUERY,
                     LOAD_AGENT_STATE_QUERY, RESPONSIBILITY_LABEL, SOP_LABEL,
                     TOOL_LABEL)

__all__ = [
    "AgentGraphLoader",
    "GraphHydrator",
    "bootstrap_l_graph",
    "AGENT_LABEL",
    "RESPONSIBILITY_LABEL",
    "DIRECTIVE_LABEL",
    "SOP_LABEL",
    "TOOL_LABEL",
    "LOAD_AGENT_STATE_QUERY",
    # UKG Phase 2
    "ENSURE_AGENT_QUERY",
    "GET_AGENT_QUERY",
]
