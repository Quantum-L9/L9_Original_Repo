"""
L9 Research Factory - Graph State Definition
Version: 1.0.0

Defines the TypedDict state structure for the research LangGraph DAG.
This state is persisted to the Memory Substrate via PacketEnvelope.
"""


from datetime import UTC, datetime
from typing import Any, TypedDict


class ResearchStep(TypedDict, total=False):
    """Single step in a research plan."""

    step_id: str
    agent: str  # "planner", "researcher", "critic"
    description: str
    query: str
    tools: list[str]
    status: str  # "pending", "in_progress", "completed", "failed"
    result: dict[str, Any] | None


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
    packet_id: str | None

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
        timestamp=datetime.now(UTC).isoformat(),
        packet_id=None,
        # Memory Substrate Integration
        stored_insights=[],
    )


# Runtime execution trace - updated automatically on every execution
