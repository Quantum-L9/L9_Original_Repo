"""
GMP Graph — Build the GMP execution graph

Autonomous execution graph for L/Emma agents.
No interactive user gates — agents provide scope at invocation.
Checkpoints at every node boundary for resume/audit.
"""

from __future__ import annotations

from langgraph.graph import END, START, StateGraph

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
from workflows.dags.gmp.state import GMPState


def build_gmp_graph() -> StateGraph:
    """
    Build the GMP execution graph using LangGraph.

    Flow:
        start → memory_read → scope_lock → [baseline | aborted]
        baseline → implement → validate → [memory_write | implement | aborted]
        memory_write → finalize → end → END
        aborted → END

    Features:
    - Enforced step ordering
    - Automatic routing (no user gates)
    - Memory operations as mandatory nodes
    - Validation retry loop with max_retries
    - Checkpoints at every node for resume/audit
    - NO commit/push (handled by caller)
    """
    graph = StateGraph(GMPState)

    # Add all nodes
    graph.add_node("start", node_start)
    graph.add_node("memory_read", node_memory_read)
    graph.add_node("scope_lock", node_scope_lock)
    graph.add_node("baseline", node_baseline)
    graph.add_node("implement", node_implement)
    graph.add_node("validate", node_validate)
    graph.add_node("memory_write", node_memory_write)
    graph.add_node("finalize", node_finalize)
    graph.add_node("end", node_end)
    graph.add_node("aborted", node_aborted)

    # Define edges
    # Entry
    graph.add_edge(START, "start")
    graph.add_edge("start", "memory_read")
    graph.add_edge("memory_read", "scope_lock")

    # Scope lock → conditional: proceed or abort
    graph.add_conditional_edges(
        "scope_lock",
        route_after_scope_lock,
        {"baseline": "baseline", "aborted": "aborted"},
    )

    # Baseline → implement → validate
    graph.add_edge("baseline", "implement")
    graph.add_edge("implement", "validate")

    # Validate → conditional: proceed, retry, or abort
    graph.add_conditional_edges(
        "validate",
        route_after_validation,
        {
            "memory_write": "memory_write",
            "implement": "implement",  # Retry loop
            "aborted": "aborted",
        },
    )

    # Memory write → finalize → end
    graph.add_edge("memory_write", "finalize")
    graph.add_edge("finalize", "end")

    # Terminal nodes
    graph.add_edge("end", END)
    graph.add_edge("aborted", END)

    return graph
