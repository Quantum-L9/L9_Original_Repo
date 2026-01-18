"""
L9 Research Factory - Graph State Definition
Version: 1.0.0

Defines the TypedDict state structure for the research LangGraph DAG.
This state is persisted to the Memory Substrate via PacketEnvelope.
"""

# ============================================================================
__dora_meta__ = {
    "component_name": "Graph State Definition",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2025-12-09T01:02:49Z",
    "updated_at": "2026-01-07T13:35:58Z",
    "layer": "operations",
    "domain": "research_services",
    "module_name": "graph_state",
    "type": "utility",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": [],
        "memory_layers": ["working_memory"],
        "imported_by": ["services.research.__init__", "services.research.agents.critic_agent", "services.research.agents.planner_agent", "services.research.agents.researcher_agent", "services.research.memory_adapter", "services.research.research_graph", "tests.integration.test_research_tool_integration", "tests.test_memory_adapter", "tests.test_research_graph"],
    },
}
# ============================================================================

from datetime import datetime
from typing import Any, Optional, TypedDict


class ResearchStep(TypedDict, total=False):
    """Single step in a research plan."""

    step_id: str
    agent: str  # "planner", "researcher", "critic"
    description: str
    query: str
    tools: list[str]
    status: str  # "pending", "in_progress", "completed", "failed"
    result: Optional[dict[str, Any]]


class Evidence(TypedDict, total=False):
    """Evidence gathered by a researcher."""

    source: str
    content: str
    confidence: float
    timestamp: str
    metadata: dict[str, Any]


class ResearchGraphState(TypedDict, total=False):
    """
    Shared state across all research graph nodes.

    This state is serialized to the Memory Substrate's graph_checkpoints table
    and packet_store for persistence and recovery.

    Fields:
        # Identity
        thread_id: Unique conversation/research session ID
        request_id: Unique request ID for this research run
        user_id: User who initiated the research

        # Input
        original_query: Raw user query
        refined_goal: Normalized/refined research goal

        # Planning
        plan: List of ResearchStep objects
        current_step_idx: Current step being executed

        # Research Results
        evidence: List of gathered Evidence objects
        sources: De-duplicated source list

        # Parallel Execution
        swarm_results: Results from parallel researchers

        # Quality Control
        critic_score: Quality score 0.0-1.0
        critic_feedback: Textual feedback from critic
        retry_count: Number of retry attempts

        # Output
        final_summary: Synthesized research summary
        final_output: Complete output JSON

        # Errors
        errors: List of error messages

        # Metadata
        timestamp: Creation timestamp
        packet_id: Associated memory substrate packet ID
    """

    # Identity
    thread_id: str
    request_id: str
    user_id: str

    # Input
    original_query: str
    refined_goal: str

    # Planning
    plan: list[ResearchStep]
    current_step_idx: int

    # Research Results
    evidence: list[Evidence]
    sources: list[str]

    # Parallel Execution
    swarm_results: list[dict[str, Any]]

    # Quality Control
    critic_score: float
    critic_feedback: str
    retry_count: int

    # Output
    final_summary: str
    final_output: dict[str, Any]

    # Errors
    errors: list[str]

    # Metadata
    timestamp: str
    packet_id: Optional[str]

    # Memory Substrate Integration
    stored_insights: list[dict[str, Any]]


def create_initial_state(
    query: str,
    thread_id: str,
    request_id: str,
    user_id: str = "anonymous",
) -> ResearchGraphState:
    """
    Create an initial research graph state from a query.

    Args:
        query: The research query
        thread_id: Unique thread ID
        request_id: Unique request ID
        user_id: User identifier

    Returns:
        Initialized ResearchGraphState
    """
    return ResearchGraphState(
        # Identity
        thread_id=thread_id,
        request_id=request_id,
        user_id=user_id,
        # Input
        original_query=query,
        refined_goal=query,  # Will be refined by planner
        # Planning
        plan=[],
        current_step_idx=0,
        # Research Results
        evidence=[],
        sources=[],
        # Parallel Execution
        swarm_results=[],
        # Quality Control
        critic_score=0.0,
        critic_feedback="",
        retry_count=0,
        # Output
        final_summary="",
        final_output={},
        # Errors
        errors=[],
        # Metadata
        timestamp=datetime.utcnow().isoformat(),
        packet_id=None,
        # Memory Substrate Integration
        stored_insights=[],
    )

# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "SER-OPER-002",
    "governance_level": "medium",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": ["messaging", "operations", "research-services", "utility"],
    "keywords": ["create", "definition", "evidence", "graph", "initial", "memory", "research", "state"],
    "business_value": "This state is persisted to the Memory Substrate via PacketEnvelope.",
    "last_modified": "2026-01-07T13:35:58Z",
    "modified_by": "L9_Codegen_Engine",
    "change_summary": "Initial generation with DORA compliance",
}
# ============================================================================
# L9 DORA BLOCK - AUTO-UPDATED - DO NOT EDIT
# Runtime execution trace - updated automatically on every execution
# ============================================================================
__l9_trace__ = {
    "trace_id": "",
    "task": "",
    "timestamp": "",
    "patterns_used": [],
    "graph": {"nodes": [], "edges": []},
    "inputs": {},
    "outputs": {},
    "metrics": {"confidence": "", "errors_detected": [], "stability_score": ""},
}
# ============================================================================
# END L9 DORA BLOCK
# ============================================================================
