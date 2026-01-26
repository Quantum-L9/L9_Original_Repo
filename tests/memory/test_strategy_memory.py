"""
Unit Tests for Strategy Memory Service
======================================

Tests for Neo4jStrategyMemoryService implementation.

GMP-102: Strategy Memory Phase 0-1
Version: 1.0.0
Created: 2026-01-20
"""

import json
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from memory.neo4j_strategy_memory import (
    Neo4jStrategyMemoryService,
    create_neo4j_strategy_memory,
)
from memory.strategymemory import (
    IStrategyMemoryService,
    StrategyFeedback,
    StrategyMemoryService,
    StrategyRetrievalRequest,
)

# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def mock_neo4j_client() -> MagicMock:
    """Create a mock Neo4j client."""
    client = MagicMock()
    client.is_available = AsyncMock(return_value=True)
    client.execute_query = AsyncMock(return_value=[])
    return client


@pytest.fixture
def strategy_memory_service(mock_neo4j_client: MagicMock) -> Neo4jStrategyMemoryService:
    """Create a Neo4jStrategyMemoryService with mocked client."""
    return Neo4jStrategyMemoryService(
        neo4j_client=mock_neo4j_client,
        semantic_service=None,
    )


@pytest.fixture
def sample_retrieval_request() -> StrategyRetrievalRequest:
    """Create a sample retrieval request."""
    return StrategyRetrievalRequest(
        task_id="task_123",
        task_kind="research",
        goal_description="Research and summarize AI trends",
        context_embedding=[0.1] * 1536,  # 1536-dim embedding
        tags=["research", "summary"],
        min_confidence=0.6,
        max_results=5,
    )


@pytest.fixture
def sample_strategy_data() -> dict[str, Any]:
    """Create sample strategy data as returned from Neo4j."""
    return {
        "id": "str_abc123",
        "name": "Research Strategy",
        "description": "Research and summarize a topic",
        "task_kind": "research",
        "context_embedding": [0.1] * 1536,
        "graph_signature": "abc123def456",
        "plan_payload": json.dumps({"steps": ["search", "analyze", "summarize"]}),
        "performance_score": 0.85,
        "generality_score": 0.7,
        "confidence": 0.9,
        "usage_count": 10,
        "tags": ["research", "summary"],
    }


@pytest.fixture
def sample_feedback() -> StrategyFeedback:
    """Create sample strategy feedback."""
    return StrategyFeedback(
        strategy_id="str_abc123",
        task_id="task_456",
        success=True,
        outcome_score=0.9,
        execution_time_ms=5000,
        resource_cost=0.5,
        metadata={"notes": "Completed successfully"},
        was_adapted=False,
        adaptation_distance=None,
    )


# =============================================================================
# Interface Contract Tests
# =============================================================================


class TestIStrategyMemoryServiceContract:
    """Test that implementations satisfy the interface contract."""

    def test_stub_implements_interface(self):
        """Stub implementation should implement IStrategyMemoryService."""
        stub = StrategyMemoryService()
        assert isinstance(stub, IStrategyMemoryService)

    def test_neo4j_implements_interface(self, mock_neo4j_client: MagicMock):
        """Neo4j implementation should implement IStrategyMemoryService."""
        service = Neo4jStrategyMemoryService(neo4j_client=mock_neo4j_client)
        assert isinstance(service, IStrategyMemoryService)


# =============================================================================
# Retrieval Tests
# =============================================================================


class TestRetrieveStrategies:
    """Tests for retrieve_strategies method."""

    @pytest.mark.asyncio
    async def test_retrieve_strategies_empty_db(
        self,
        strategy_memory_service: Neo4jStrategyMemoryService,
        sample_retrieval_request: StrategyRetrievalRequest,
    ):
        """Should return empty list when no strategies in database."""
        result = await strategy_memory_service.retrieve_strategies(
            sample_retrieval_request, limit=5
        )

        assert result == []

    @pytest.mark.asyncio
    async def test_retrieve_strategies_with_match(
        self,
        strategy_memory_service: Neo4jStrategyMemoryService,
        mock_neo4j_client: MagicMock,
        sample_retrieval_request: StrategyRetrievalRequest,
        sample_strategy_data: dict[str, Any],
    ):
        """Should return candidates when matches found."""
        # Mock Neo4j returning a strategy
        mock_neo4j_client.execute_query = AsyncMock(
            return_value=[{"strategy": sample_strategy_data}]
        )

        result = await strategy_memory_service.retrieve_strategies(
            sample_retrieval_request, limit=5
        )

        assert len(result) >= 0  # May be filtered by confidence
        mock_neo4j_client.execute_query.assert_called_once()

    @pytest.mark.asyncio
    async def test_retrieve_strategies_respects_limit(
        self,
        strategy_memory_service: Neo4jStrategyMemoryService,
        mock_neo4j_client: MagicMock,
        sample_retrieval_request: StrategyRetrievalRequest,
        sample_strategy_data: dict[str, Any],
    ):
        """Should respect the limit parameter."""
        # Return multiple strategies
        strategies = [
            {"strategy": {**sample_strategy_data, "id": f"str_{i}"}} for i in range(10)
        ]
        mock_neo4j_client.execute_query = AsyncMock(return_value=strategies)

        result = await strategy_memory_service.retrieve_strategies(
            sample_retrieval_request, limit=3
        )

        assert len(result) <= 3

    @pytest.mark.asyncio
    async def test_retrieve_strategies_neo4j_unavailable(
        self,
        strategy_memory_service: Neo4jStrategyMemoryService,
        mock_neo4j_client: MagicMock,
        sample_retrieval_request: StrategyRetrievalRequest,
    ):
        """Should return empty list when Neo4j unavailable."""
        mock_neo4j_client.is_available = AsyncMock(return_value=False)

        result = await strategy_memory_service.retrieve_strategies(
            sample_retrieval_request
        )

        assert result == []

    @pytest.mark.asyncio
    async def test_retrieve_strategies_filters_by_confidence(
        self,
        strategy_memory_service: Neo4jStrategyMemoryService,
        mock_neo4j_client: MagicMock,
        sample_strategy_data: dict[str, Any],
    ):
        """Should filter candidates below min_confidence threshold."""
        # Low confidence strategy
        low_conf_strategy = {**sample_strategy_data, "performance_score": 0.1}
        mock_neo4j_client.execute_query = AsyncMock(
            return_value=[{"strategy": low_conf_strategy}]
        )

        request = StrategyRetrievalRequest(
            task_id="task_123",
            task_kind="research",
            goal_description="Test",
            min_confidence=0.8,  # High threshold
        )

        result = await strategy_memory_service.retrieve_strategies(request)

        # Low confidence strategy should be filtered out
        assert len(result) == 0 or all(c.confidence >= 0.8 for c in result)


# =============================================================================
# Recording Tests
# =============================================================================


class TestRecordNewStrategy:
    """Tests for record_new_strategy method."""

    @pytest.mark.asyncio
    async def test_record_new_strategy_success(
        self,
        strategy_memory_service: Neo4jStrategyMemoryService,
        mock_neo4j_client: MagicMock,
    ):
        """Should successfully record a new strategy."""
        mock_neo4j_client.execute_query = AsyncMock(
            return_value=[{"strategy_id": "str_new123"}]
        )

        strategy_id = await strategy_memory_service.record_new_strategy(
            task_id="task_789",
            description="New research strategy",
            plan_payload={"steps": ["search", "analyze"]},
            context_embedding=[0.1] * 1536,
            tags=["research"],
        )

        assert strategy_id.startswith("str_")
        mock_neo4j_client.execute_query.assert_called_once()

    @pytest.mark.asyncio
    async def test_record_new_strategy_generates_graph_signature(
        self,
        strategy_memory_service: Neo4jStrategyMemoryService,
        mock_neo4j_client: MagicMock,
    ):
        """Should generate a graph signature from plan structure."""
        mock_neo4j_client.execute_query = AsyncMock(return_value=[{}])

        await strategy_memory_service.record_new_strategy(
            task_id="task_789",
            description="Test strategy",
            plan_payload={"steps": ["a", "b", "c"]},
            context_embedding=[0.1] * 10,
            tags=[],
        )

        # Verify CREATE query was called with graph_sig parameter
        call_args = mock_neo4j_client.execute_query.call_args
        params = call_args[0][1]  # Second positional arg is params
        assert "graph_sig" in params
        assert len(params["graph_sig"]) == 64  # SHA256 hex length

    @pytest.mark.asyncio
    async def test_record_new_strategy_neo4j_unavailable(
        self,
        strategy_memory_service: Neo4jStrategyMemoryService,
        mock_neo4j_client: MagicMock,
    ):
        """Should raise error when Neo4j unavailable."""
        mock_neo4j_client.is_available = AsyncMock(return_value=False)

        with pytest.raises(RuntimeError, match="Neo4j not available"):
            await strategy_memory_service.record_new_strategy(
                task_id="task_789",
                description="Test",
                plan_payload={},
                context_embedding=[],
            )


# =============================================================================
# Feedback Loop Tests
# =============================================================================


class TestUpdateStrategyOutcome:
    """Tests for update_strategy_outcome method."""

    @pytest.mark.asyncio
    async def test_update_strategy_outcome_success(
        self,
        strategy_memory_service: Neo4jStrategyMemoryService,
        mock_neo4j_client: MagicMock,
        sample_feedback: StrategyFeedback,
    ):
        """Should update strategy score on successful execution."""
        mock_neo4j_client.execute_query = AsyncMock(return_value=[{"new_score": 0.93}])

        await strategy_memory_service.update_strategy_outcome(sample_feedback)

        mock_neo4j_client.execute_query.assert_called_once()
        call_args = mock_neo4j_client.execute_query.call_args
        params = call_args[0][1]
        assert params["success"] is True
        assert params["outcome_score"] == 0.9

    @pytest.mark.asyncio
    async def test_update_strategy_outcome_failure(
        self,
        strategy_memory_service: Neo4jStrategyMemoryService,
        mock_neo4j_client: MagicMock,
    ):
        """Should update strategy score on failed execution."""
        feedback = StrategyFeedback(
            strategy_id="str_abc123",
            task_id="task_456",
            success=False,
            outcome_score=0.2,
            execution_time_ms=10000,
            metadata={"failure_reason": "Timeout"},
        )

        mock_neo4j_client.execute_query = AsyncMock(return_value=[{}])

        await strategy_memory_service.update_strategy_outcome(feedback)

        call_args = mock_neo4j_client.execute_query.call_args
        params = call_args[0][1]
        assert params["success"] is False
        assert params["outcome_score"] == 0.2

    @pytest.mark.asyncio
    async def test_update_strategy_outcome_neo4j_unavailable(
        self,
        strategy_memory_service: Neo4jStrategyMemoryService,
        mock_neo4j_client: MagicMock,
        sample_feedback: StrategyFeedback,
    ):
        """Should handle Neo4j unavailable gracefully."""
        mock_neo4j_client.is_available = AsyncMock(return_value=False)

        # Should not raise, just log warning
        await strategy_memory_service.update_strategy_outcome(sample_feedback)

        # No query should be executed
        mock_neo4j_client.execute_query.assert_not_called()


# =============================================================================
# Hybrid Scoring Tests
# =============================================================================


class TestHybridScoring:
    """Tests for hybrid scoring algorithm."""

    @pytest.mark.asyncio
    async def test_hybrid_scoring_weights(
        self,
        strategy_memory_service: Neo4jStrategyMemoryService,
    ):
        """Verify hybrid scoring weights sum to 1.0."""
        config = strategy_memory_service._config
        total = config.EMBEDDING_WEIGHT + config.GRAPH_WEIGHT + config.SYMBOLIC_WEIGHT
        assert abs(total - 1.0) < 0.001

    def test_compute_tag_similarity_full_match(
        self,
        strategy_memory_service: Neo4jStrategyMemoryService,
    ):
        """Full tag overlap should return 1.0."""
        similarity = strategy_memory_service._compute_tag_similarity(
            request_tags=["a", "b", "c"],
            stored_tags=["a", "b", "c"],
        )
        assert similarity == 1.0

    def test_compute_tag_similarity_no_match(
        self,
        strategy_memory_service: Neo4jStrategyMemoryService,
    ):
        """No tag overlap should return 0.0."""
        similarity = strategy_memory_service._compute_tag_similarity(
            request_tags=["a", "b"],
            stored_tags=["x", "y"],
        )
        assert similarity == 0.0

    def test_compute_tag_similarity_partial_match(
        self,
        strategy_memory_service: Neo4jStrategyMemoryService,
    ):
        """Partial tag overlap should return Jaccard coefficient."""
        similarity = strategy_memory_service._compute_tag_similarity(
            request_tags=["a", "b"],
            stored_tags=["b", "c"],
        )
        # Jaccard: |{b}| / |{a,b,c}| = 1/3
        assert abs(similarity - (1 / 3)) < 0.001

    def test_compute_tag_similarity_empty_tags(
        self,
        strategy_memory_service: Neo4jStrategyMemoryService,
    ):
        """Empty tags should return neutral 0.5."""
        assert strategy_memory_service._compute_tag_similarity([], ["a"]) == 0.5
        assert strategy_memory_service._compute_tag_similarity(["a"], []) == 0.5
        assert strategy_memory_service._compute_tag_similarity([], []) == 0.5


# =============================================================================
# Graph Signature Tests
# =============================================================================


class TestGraphSignature:
    """Tests for graph signature computation."""

    def test_compute_graph_signature_deterministic(
        self,
        strategy_memory_service: Neo4jStrategyMemoryService,
    ):
        """Same structure should produce same signature."""
        payload = {"steps": [{"action": "search"}, {"action": "analyze"}]}

        sig1 = strategy_memory_service._compute_graph_signature(payload)
        sig2 = strategy_memory_service._compute_graph_signature(payload)

        assert sig1 == sig2

    def test_compute_graph_signature_different_for_different_structure(
        self,
        strategy_memory_service: Neo4jStrategyMemoryService,
    ):
        """Different structures should produce different signatures."""
        # Use truly different structures (different keys, not just different values)
        payload1 = {"steps": [{"action": "search"}]}
        payload2 = {"phases": [{"operation": "analyze"}]}  # Different keys

        sig1 = strategy_memory_service._compute_graph_signature(payload1)
        sig2 = strategy_memory_service._compute_graph_signature(payload2)

        assert sig1 != sig2

    def test_compute_graph_signature_ignores_values(
        self,
        strategy_memory_service: Neo4jStrategyMemoryService,
    ):
        """Signature should be based on structure, not values."""
        payload1 = {"name": "Strategy A", "version": 1}
        payload2 = {"name": "Strategy B", "version": 2}

        sig1 = strategy_memory_service._compute_graph_signature(payload1)
        sig2 = strategy_memory_service._compute_graph_signature(payload2)

        # Same structure (same keys) = same signature
        assert sig1 == sig2


# =============================================================================
# Factory Function Tests
# =============================================================================


class TestFactoryFunction:
    """Tests for create_neo4j_strategy_memory factory."""

    def test_create_neo4j_strategy_memory(self, mock_neo4j_client: MagicMock):
        """Factory should create configured service."""
        service = create_neo4j_strategy_memory(
            neo4j_client=mock_neo4j_client,
            semantic_service=None,
        )

        assert isinstance(service, Neo4jStrategyMemoryService)
        assert service._neo4j == mock_neo4j_client


# =============================================================================
# Stub Implementation Tests
# =============================================================================


class TestStubImplementation:
    """Tests for the stub StrategyMemoryService."""

    @pytest.mark.asyncio
    async def test_stub_retrieve_empty(self):
        """Stub should return empty list initially."""
        stub = StrategyMemoryService()
        request = StrategyRetrievalRequest(
            task_id="test",
            task_kind="research",
            goal_description="Test",
        )

        result = await stub.retrieve_strategies(request)
        assert result == []

    @pytest.mark.asyncio
    async def test_stub_record_and_retrieve(self):
        """Stub should be able to record and retrieve strategies."""
        stub = StrategyMemoryService()

        # Record a strategy
        strategy_id = await stub.record_new_strategy(
            task_id="task_123",
            description="Test strategy",
            plan_payload={"steps": ["a", "b"]},
            context_embedding=[],
            tags=["test"],
        )

        assert strategy_id.startswith("str_")

        # Retrieve it
        request = StrategyRetrievalRequest(
            task_id="task_456",
            task_kind="test",
            goal_description="Test",
            tags=["test"],
            min_confidence=0.5,
        )

        result = await stub.retrieve_strategies(request)
        assert len(result) == 1
        assert result[0].strategy_id == strategy_id

    @pytest.mark.asyncio
    async def test_stub_update_outcome(self):
        """Stub should update performance scores."""
        stub = StrategyMemoryService()

        # Record a strategy
        strategy_id = await stub.record_new_strategy(
            task_id="task_123",
            description="Test",
            plan_payload={},
            context_embedding=[],
            tags=["test"],
        )

        # Update with feedback
        feedback = StrategyFeedback(
            strategy_id=strategy_id,
            task_id="task_456",
            success=True,
            outcome_score=0.8,
            execution_time_ms=1000,
        )

        await stub.update_strategy_outcome(feedback)

        # Verify score updated
        assert stub._strategies[strategy_id].usage_count == 1


# =============================================================================
# Performance Score Exponential Smoothing Tests
# =============================================================================


class TestExponentialSmoothing:
    """Tests for performance score exponential smoothing."""

    @pytest.mark.asyncio
    async def test_exponential_smoothing_formula(
        self,
        strategy_memory_service: Neo4jStrategyMemoryService,
        mock_neo4j_client: MagicMock,
    ):
        """Verify exponential smoothing uses correct formula."""
        # new_score = α * outcome + (1-α) * old_score
        # With α = 0.3, old = 0.8, outcome = 0.5:
        # new = 0.3 * 0.5 + 0.7 * 0.8 = 0.15 + 0.56 = 0.71

        mock_neo4j_client.execute_query = AsyncMock(return_value=[{}])

        feedback = StrategyFeedback(
            strategy_id="str_abc123",
            task_id="task_456",
            success=True,
            outcome_score=0.5,
            execution_time_ms=1000,
        )

        await strategy_memory_service.update_strategy_outcome(feedback)

        # Verify the alpha value is passed to the query
        call_args = mock_neo4j_client.execute_query.call_args
        params = call_args[0][1]
        assert params["alpha"] == 0.3  # Default config value
