"""
L9 IR Engine Tests - Simulation Router Integration
=================================================

Test Matrix:
┌─────────────────────────────────────────────────────────────────────────────┐
│ Scenario                    │ Modules Touched              │ Expected       │
├─────────────────────────────────────────────────────────────────────────────┤
│ Create simulation request   │ SimulationRouter             │ Request obj    │
│                             │ create_request               │ with graph     │
├─────────────────────────────────────────────────────────────────────────────┤
│ Route with stub mode        │ SimulationRouter.route       │ Heuristic      │
│ (no engine)                 │ _stub_simulation             │ score returned │
├─────────────────────────────────────────────────────────────────────────────┤
│ Result contains metrics     │ SimulationResult             │ Non-empty      │
│                             │                              │ metrics dict   │
├─────────────────────────────────────────────────────────────────────────────┤
│ Execution time tracked      │ SimulationResult             │ execution_ms   │
│                             │                              │ is set         │
├─────────────────────────────────────────────────────────────────────────────┤
│ Results retrievable         │ get_results_for_graph        │ Returns        │
│                             │                              │ stored result  │
├─────────────────────────────────────────────────────────────────────────────┤
│ Multi-candidate simulation  │ simulate_candidates          │ Ranked list    │
├─────────────────────────────────────────────────────────────────────────────┤
│ Select best candidate       │ select_best                  │ Best or None   │
└─────────────────────────────────────────────────────────────────────────────┘
"""

from __future__ import annotations

from uuid import uuid4

import pytest

from core.decorators import must_stay_async
from ir_engine.ir_schema import (
    ActionNode,
    ActionType,
    ConstraintNode,
    ConstraintType,
    IntentNode,
    IntentType,
    IRGraph,
    IRMetadata,
    IRStatus,
)
from ir_engine.simulation_router import (
    RankedCandidate,
    SimulationRequest,
    SimulationResult,
    SimulationRouter,
)


class TestSimulationRequestCreation:
    """Test simulation request creation."""

    def test_create_request_from_validated_graph(
        self,
        validated_graph: IRGraph,
    ):
        """Test creating a simulation request from a validated graph."""
        # Arrange
        router = SimulationRouter()

        # Act
        request = router.create_request(validated_graph)

        # Assert
        assert isinstance(request, SimulationRequest)
        assert request.graph_id == validated_graph.graph_id
        assert request.graph_snapshot is not None
        assert len(request.graph_snapshot) > 0

    def test_request_includes_graph_snapshot(
        self,
        validated_graph: IRGraph,
    ):
        """Test that request includes full graph snapshot."""
        # Arrange
        router = SimulationRouter()

        # Act
        request = router.create_request(validated_graph)

        # Assert
        snapshot = request.graph_snapshot
        assert "intents" in snapshot
        assert "actions" in snapshot
        assert "constraints" in snapshot
        assert len(snapshot["intents"]) == len(validated_graph.intents)

    def test_request_with_custom_scenario(
        self,
        validated_graph: IRGraph,
    ):
        """Test creating request with custom scenario type."""
        # Arrange
        router = SimulationRouter()

        # Act
        request = router.create_request(
            validated_graph,
            scenario_type="stress_test",
            parameters={"load": 100},
        )

        # Assert
        assert request.scenario_type == "stress_test"
        assert request.parameters["load"] == 100

    def test_request_priority_clamped(
        self,
        validated_graph: IRGraph,
    ):
        """Test that priority is clamped to valid range."""
        # Arrange
        router = SimulationRouter()

        # Act
        request_low = router.create_request(validated_graph, priority=0)
        request_high = router.create_request(validated_graph, priority=100)

        # Assert: Priority clamped to 1-10
        assert request_low.priority == 1
        assert request_high.priority == 10

    def test_request_stored_in_pending(
        self,
        validated_graph: IRGraph,
    ):
        """Test that created request is stored in pending."""
        # Arrange
        router = SimulationRouter()

        # Act
        router.create_request(validated_graph)

        # Assert
        assert router.get_pending_count() == 1


class TestSimulationRouting:
    """Test simulation routing with stub mode."""

    @pytest.mark.asyncio
    async def test_route_with_no_engine_uses_stub(
        self,
        validated_graph: IRGraph,
    ):
        """Test that routing without engine uses stub simulation."""
        # Arrange
        router = SimulationRouter()  # No engine attached
        request = router.create_request(validated_graph)

        # Act
        result = await router.route(request)

        # Assert
        assert isinstance(result, SimulationResult)
        assert result.success is True
        assert result.metrics.get("stub_simulation") is True

    @pytest.mark.asyncio
    async def test_stub_simulation_produces_reasonable_score(
        self,
        validated_graph: IRGraph,
    ):
        """Test that stub simulation produces a reasonable score."""
        # Arrange
        router = SimulationRouter()
        request = router.create_request(validated_graph)

        # Act
        result = await router.route(request)

        # Assert: Score should be between 0 and 1
        assert 0.0 <= result.score <= 1.0

        # A valid graph with intents and actions should score reasonably well
        assert result.score >= 0.5, "Valid graph should score at least 0.5"

    @pytest.mark.asyncio
    async def test_result_contains_metrics(
        self,
        validated_graph: IRGraph,
    ):
        """Test that result contains populated metrics."""
        # Arrange
        router = SimulationRouter()
        request = router.create_request(validated_graph)

        # Act
        result = await router.route(request)

        # Assert
        assert result.metrics is not None
        assert len(result.metrics) > 0
        assert "intent_count" in result.metrics
        assert "action_count" in result.metrics

    @pytest.mark.asyncio
    async def test_execution_time_tracked(
        self,
        validated_graph: IRGraph,
    ):
        """Test that execution time is tracked."""
        # Arrange
        router = SimulationRouter()
        request = router.create_request(validated_graph)

        # Act
        result = await router.route(request)

        # Assert
        assert result.execution_time_ms >= 0
        assert result.completed_at is not None

    @pytest.mark.asyncio
    async def test_result_stored_after_routing(
        self,
        validated_graph: IRGraph,
    ):
        """Test that result is stored after routing."""
        # Arrange
        router = SimulationRouter()
        request = router.create_request(validated_graph)

        # Act
        result = await router.route(request)

        # Assert
        stored = router.get_result(request.request_id)
        assert stored is not None
        assert stored.request_id == result.request_id

    @pytest.mark.asyncio
    async def test_pending_cleared_after_routing(
        self,
        validated_graph: IRGraph,
    ):
        """Test that pending request is cleared after routing."""
        # Arrange
        router = SimulationRouter()
        request = router.create_request(validated_graph)
        assert router.get_pending_count() == 1

        # Act
        await router.route(request)

        # Assert
        assert router.get_pending_count() == 0


class TestResultRetrieval:
    """Test simulation result retrieval."""

    @pytest.mark.asyncio
    async def test_get_results_for_graph(
        self,
        validated_graph: IRGraph,
    ):
        """Test retrieving results by graph ID."""
        # Arrange
        router = SimulationRouter()
        request = router.create_request(validated_graph)
        await router.route(request)

        # Act
        results = router.get_results_for_graph(validated_graph.graph_id)

        # Assert
        assert len(results) == 1
        assert results[0].graph_id == validated_graph.graph_id

    @pytest.mark.asyncio
    async def test_get_result_by_request_id(
        self,
        validated_graph: IRGraph,
    ):
        """Test retrieving result by request ID."""
        # Arrange
        router = SimulationRouter()
        request = router.create_request(validated_graph)
        await router.route(request)

        # Act
        result = router.get_result(request.request_id)

        # Assert
        assert result is not None
        assert result.request_id == request.request_id

    def test_get_nonexistent_result_returns_none(self):
        """Test that getting non-existent result returns None."""
        # Arrange
        router = SimulationRouter()

        # Act
        result = router.get_result(uuid4())

        # Assert
        assert result is None

    @pytest.mark.asyncio
    async def test_clear_results(
        self,
        validated_graph: IRGraph,
    ):
        """Test clearing all results."""
        # Arrange
        router = SimulationRouter()
        request = router.create_request(validated_graph)
        await router.route(request)
        assert router.get_result(request.request_id) is not None

        # Act
        router.clear_results()

        # Assert
        assert router.get_result(request.request_id) is None


class TestMultiCandidateSimulation:
    """Test multi-candidate simulation and ranking."""

    @pytest.fixture
    def candidate_graphs(self) -> list[IRGraph]:
        """Create multiple candidate graphs with varying quality."""
        graphs = []

        # High quality graph (complete)
        g1 = IRGraph(metadata=IRMetadata(source="test"))
        intent1 = IntentNode(
            intent_type=IntentType.CREATE,
            description="Create feature A",
            target="feature_a",
        )
        i1_id = g1.add_intent(intent1)
        constraint1 = ConstraintNode(
            constraint_type=ConstraintType.EXPLICIT,
            description="Must be tested",
            applies_to=[i1_id],
        )
        c1_id = g1.add_constraint(constraint1)
        action1 = ActionNode(
            action_type=ActionType.CODE_WRITE,
            description="Implement feature A",
            target="feature_a.py",
            derived_from_intent=i1_id,
            constrained_by=[c1_id],
        )
        g1.add_action(action1)
        g1.set_status(IRStatus.VALIDATED)
        graphs.append(g1)

        # Medium quality graph (no constraints)
        g2 = IRGraph(metadata=IRMetadata(source="test"))
        intent2 = IntentNode(
            intent_type=IntentType.CREATE,
            description="Create feature B",
            target="feature_b",
        )
        i2_id = g2.add_intent(intent2)
        action2 = ActionNode(
            action_type=ActionType.CODE_WRITE,
            description="Implement feature B",
            target="feature_b.py",
            derived_from_intent=i2_id,
        )
        g2.add_action(action2)
        g2.set_status(IRStatus.VALIDATED)
        graphs.append(g2)

        # Low quality graph (no actions)
        g3 = IRGraph(metadata=IRMetadata(source="test"))
        intent3 = IntentNode(
            intent_type=IntentType.CREATE,
            description="Create feature C",
            target="feature_c",
        )
        g3.add_intent(intent3)
        g3.set_status(IRStatus.VALIDATED)
        graphs.append(g3)

        return graphs

    @pytest.mark.asyncio
    async def test_simulate_candidates_returns_ranked_list(
        self,
        candidate_graphs: list[IRGraph],
    ):
        """Test that simulate_candidates returns ranked list."""
        # Arrange
        router = SimulationRouter()

        # Act
        ranked = await router.simulate_candidates(candidate_graphs)

        # Assert
        assert len(ranked) == 3
        assert all(isinstance(r, RankedCandidate) for r in ranked)

        # Should be sorted by score (best first)
        scores = [r.result.score for r in ranked]
        assert scores == sorted(scores, reverse=True)

    @pytest.mark.asyncio
    async def test_ranked_candidates_have_correct_ranks(
        self,
        candidate_graphs: list[IRGraph],
    ):
        """Test that ranked candidates have sequential ranks."""
        # Arrange
        router = SimulationRouter()

        # Act
        ranked = await router.simulate_candidates(candidate_graphs)

        # Assert
        ranks = [r.rank for r in ranked]
        assert ranks == [1, 2, 3]

    @pytest.mark.asyncio
    async def test_ranked_candidates_include_selection_reason(
        self,
        candidate_graphs: list[IRGraph],
    ):
        """Test that ranked candidates include selection reason."""
        # Arrange
        router = SimulationRouter()

        # Act
        ranked = await router.simulate_candidates(candidate_graphs)

        # Assert
        assert ranked[0].selection_reason.startswith("Highest score")
        for candidate in ranked:
            assert candidate.selection_reason is not None

    @pytest.mark.asyncio
    async def test_candidate_limit_enforced(
        self,
        candidate_graphs: list[IRGraph],
    ):
        """Test that max_candidates limit is enforced."""
        # Arrange
        router = SimulationRouter(max_candidates=2)

        # Act
        ranked = await router.simulate_candidates(candidate_graphs)

        # Assert
        assert len(ranked) == 2


class TestSelectBest:
    """Test best candidate selection."""

    @pytest.mark.asyncio
    async def test_select_best_returns_highest_scoring(
        self,
        validated_graph: IRGraph,
    ):
        """Test that select_best returns highest scoring candidate."""
        # Arrange
        router = SimulationRouter()

        # Act
        best = await router.select_best([validated_graph], min_score=0.0)

        # Assert
        assert best is not None
        assert best.graph_id == validated_graph.graph_id

    @pytest.mark.asyncio
    async def test_select_best_returns_none_below_threshold(self):
        """Test that select_best returns None if no candidate meets threshold."""
        # Arrange
        router = SimulationRouter()

        # Create a minimal graph that will score low
        graph = IRGraph(metadata=IRMetadata(source="test"))
        intent = IntentNode(
            intent_type=IntentType.CREATE,
            description="Minimal intent",
            target="target",
        )
        graph.add_intent(intent)
        # No actions -> low score

        # Act
        best = await router.select_best([graph], min_score=0.99)  # Very high threshold

        # Assert
        assert best is None


class TestSimulationResultSerialization:
    """Test SimulationResult serialization."""

    def test_result_to_dict(self):
        """Test SimulationResult.to_dict()."""
        # Arrange
        result = SimulationResult(
            request_id=uuid4(),
            graph_id=uuid4(),
            success=True,
            score=0.85,
            metrics={"test": 123},
            failure_modes=["mode1"],
            execution_time_ms=100,
        )

        # Act
        data = result.to_dict()

        # Assert
        assert "request_id" in data
        assert "graph_id" in data
        assert data["success"] is True
        assert data["score"] == 0.85
        assert data["metrics"]["test"] == 123
        assert "mode1" in data["failure_modes"]
        assert data["execution_time_ms"] == 100
        assert "completed_at" in data


class TestSimulationEdgeCases:
    """Test edge cases in simulation routing."""

    @pytest.mark.asyncio
    async def test_empty_graph_simulation(self, empty_graph: IRGraph):
        """Test simulating an empty graph."""
        # Arrange
        router = SimulationRouter()
        request = router.create_request(empty_graph)

        # Act
        result = await router.route(request)

        # Assert: Should still succeed but with low score
        assert result.success is True
        assert result.score < 0.5  # Low score for incomplete graph

    @pytest.mark.asyncio
    @must_stay_async("callers use await")
    async def test_simulation_with_custom_timeout(
        self,
        validated_graph: IRGraph,
    ):
        """Test simulation with custom timeout."""
        # Arrange
        router = SimulationRouter()

        # Act
        request = router.create_request(
            validated_graph,
            timeout_ms=60000,
        )

        # Assert
        assert request.timeout_ms == 60000

    def test_set_engine(self):
        """Test setting the simulation engine."""
        # Arrange
        router = SimulationRouter()
        mock_engine = object()

        # Act
        router.set_engine(mock_engine)

        # Assert
        assert router._engine is mock_engine
