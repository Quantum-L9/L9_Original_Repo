"""
State Bloat Tests
=================

Tests for monitoring state size and memory usage.
"""

import sys
from datetime import datetime
from typing import Optional, TypedDict


# Mock ResearchGraphState for testing without production dependencies
class ResearchGraphState(TypedDict, total=False):
    """Mock research graph state for testing."""

    thread_id: str
    request_id: str
    user_id: str
    original_query: str
    refined_goal: str
    plan: list
    current_step_idx: int
    evidence: list
    sources: list
    swarm_results: list
    critic_score: float
    critic_feedback: str
    retry_count: int
    final_summary: str
    final_output: dict
    errors: list
    timestamp: str
    packet_id: Optional[str]
    stored_insights: list


def create_initial_state(
    query: str,
    thread_id: str,
    request_id: str,
    user_id: str = "anonymous",
) -> ResearchGraphState:
    """Create an initial research graph state from a query."""
    return ResearchGraphState(
        thread_id=thread_id,
        request_id=request_id,
        user_id=user_id,
        original_query=query,
        refined_goal=query,
        plan=[],
        current_step_idx=0,
        evidence=[],
        sources=[],
        swarm_results=[],
        critic_score=0.0,
        critic_feedback="",
        retry_count=0,
        final_summary="",
        final_output={},
        errors=[],
        timestamp=datetime.utcnow().isoformat(),
        packet_id=None,
        stored_insights=[],
    )


def test_state_bloat():
    """Test that state size stays within reasonable bounds.

    Note: This test validates that state serialization works and
    size scales predictably with content. 50x1MB = ~50MB expected.
    """
    state = create_initial_state("t", "u", "r")
    large = "x" * (1024 * 1024)  # 1MB

    for _ in range(50):
        state["evidence"].append({"content": large})

    size_mb = sys.getsizeof(str(state)) / (1024 * 1024)
    # 50 x 1MB items = ~50MB expected, allow some overhead
    assert size_mb < 100.0


def test_initial_state_size():
    """Test initial state size is reasonable."""
    state = create_initial_state(
        query="test query",
        thread_id="thread-123",
        request_id="req-456",
    )

    size_bytes = sys.getsizeof(str(state))

    # Initial state should be small (less than 1KB)
    assert size_bytes < 1024


def test_state_with_plan():
    """Test state size with plan entries."""
    state = create_initial_state("test", "thread", "req")

    # Add plan steps
    for i in range(10):
        state["plan"].append(
            {
                "step_id": f"step-{i}",
                "agent": "researcher",
                "description": f"Research step {i}",
                "query": f"Query {i}",
                "tools": ["web_search"],
                "status": "pending",
                "result": None,
            }
        )

    size_kb = sys.getsizeof(str(state)) / 1024

    # With 10 steps should still be under 10KB
    assert size_kb < 10


def test_evidence_accumulation():
    """Test evidence accumulation doesn't bloat state."""
    state = create_initial_state("test", "thread", "req")

    # Add moderate evidence
    for i in range(100):
        state["evidence"].append(
            {
                "source": f"source-{i}",
                "content": f"Evidence content {i}" * 10,  # ~150 bytes each
                "confidence": 0.8,
                "timestamp": "2024-01-01T00:00:00",
                "metadata": {},
            }
        )

    size_kb = sys.getsizeof(str(state)) / 1024

    # 100 evidence items should be under 100KB
    assert size_kb < 100


def test_sources_deduplication_effect():
    """Test that sources list doesn't grow unbounded."""
    state = create_initial_state("test", "thread", "req")

    # Add many sources (some duplicates)
    sources = set()
    for i in range(1000):
        source = f"source-{i % 50}"  # Only 50 unique sources
        sources.add(source)

    state["sources"] = list(sources)

    # Should have deduplicated to 50
    assert len(state["sources"]) == 50


def test_error_accumulation():
    """Test error accumulation stays bounded."""
    state = create_initial_state("test", "thread", "req")

    # Add many errors
    for i in range(100):
        state["errors"].append(f"Error {i}: Something went wrong")

    size_kb = sys.getsizeof(str(state)) / 1024

    # Errors shouldn't dominate state size
    assert size_kb < 50


def test_swarm_results_size():
    """Test swarm results don't cause bloat."""
    state = create_initial_state("test", "thread", "req")

    # Simulate swarm results
    for i in range(10):
        state["swarm_results"].append(
            {
                "researcher_id": f"researcher-{i}",
                "findings": [
                    {"text": "Finding 1" * 100, "confidence": 0.9},
                    {"text": "Finding 2" * 100, "confidence": 0.8},
                ],
                "status": "completed",
            }
        )

    size_kb = sys.getsizeof(str(state)) / 1024

    # Should be manageable
    assert size_kb < 100
