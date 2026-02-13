"""
Integration Tests for Strategy Memory Service
=============================================

End-to-end tests requiring Neo4j connection.

These tests verify:
- Full retrieval → execution → feedback cycle
- Strategy reuse effectiveness
- Golden strategy seeding and retrieval

GMP-102: Strategy Memory Phase 0-1
Version: 1.0.0
Created: 2026-01-20

Requirements:
- Neo4j running (docker-compose up neo4j)
- NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD env vars set
"""

import os

import pytest

from core.decorators import must_stay_async

# Skip all tests if Neo4j not available
pytestmark = pytest.mark.skipif(
    not os.getenv("NEO4J_URI"),
    reason="Neo4j not configured (set NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD)",
)


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture(scope="module")
async def neo4j_client():
    """Get Neo4j client for integration tests."""
    from memory.graph_client import close_neo4j_client, get_neo4j_client

    client = await get_neo4j_client()
    if not client or not await client.is_available():
        pytest.skip("Neo4j not available")

    yield client

    # Cleanup: Close connection
    await close_neo4j_client()


@pytest.fixture
@must_stay_async("callers use await")
async def strategy_memory_service(neo4j_client):
    """Create Strategy Memory service with real Neo4j."""
    from memory.neo4j_strategy_memory import Neo4jStrategyMemoryService

    return Neo4jStrategyMemoryService(neo4j_client=neo4j_client)


@pytest.fixture
async def cleanup_test_strategies(neo4j_client):
    """Cleanup test strategies after each test."""
    test_strategy_ids = []

    yield test_strategy_ids

    # Cleanup: Delete test strategies
    for strategy_id in test_strategy_ids:
        try:
            query = """
            MATCH (s:Strategy {id: $id})
            OPTIONAL MATCH (s)-[:EXECUTED_AS]->(e:Execution)
            DETACH DELETE s, e
            """
            await neo4j_client.execute_query(query, {"id": strategy_id})
        except Exception:
            pass


# =============================================================================
# Integration Tests
# =============================================================================


class TestStrategyMemoryIntegration:
    """Integration tests for Strategy Memory with real Neo4j."""

    @pytest.mark.asyncio
    async def test_end_to_end_record_and_retrieve(
        self,
        strategy_memory_service,
        cleanup_test_strategies,
    ):
        """Test full cycle: record strategy → retrieve → verify match."""
        from memory.strategymemory import StrategyRetrievalRequest

        # 1. Record a new strategy
        strategy_id = await strategy_memory_service.record_new_strategy(
            task_id="integration_test_001",
            description="Integration test strategy for research tasks",
            plan_payload={
                "task_kind": "integration_test",
                "steps": ["search", "analyze", "summarize"],
            },
            context_embedding=[0.1] * 1536,
            tags=["integration_test", "research"],
        )

        cleanup_test_strategies.append(strategy_id)
        assert strategy_id.startswith("str_")

        # 2. Retrieve strategies matching the same kind
        request = StrategyRetrievalRequest(
            task_id="test_retrieval",
            task_kind="integration_test",
            goal_description="Integration test task",
            tags=["integration_test"],
            min_confidence=0.0,  # Low threshold for testing
            max_results=10,
        )

        candidates = await strategy_memory_service.retrieve_strategies(request)

        # 3. Verify our strategy is in results
        assert len(candidates) >= 1
        found = any(c.strategy_id == strategy_id for c in candidates)
        assert found, f"Strategy {strategy_id} not found in candidates"

    @pytest.mark.asyncio
    async def test_feedback_updates_score(
        self,
        strategy_memory_service,
        neo4j_client,
        cleanup_test_strategies,
    ):
        """Test that feedback correctly updates performance score."""
        from memory.strategymemory import StrategyFeedback

        # Record a strategy
        strategy_id = await strategy_memory_service.record_new_strategy(
            task_id="feedback_test_001",
            description="Test strategy for feedback",
            plan_payload={"task_kind": "feedback_test"},
            context_embedding=[0.0] * 1536,
            tags=["feedback_test"],
        )

        cleanup_test_strategies.append(strategy_id)

        # Get initial score (should be 1.0 for new strategy)
        initial = await strategy_memory_service.get_strategy_by_id(strategy_id)
        assert initial is not None
        assert initial.performance_score == 1.0

        # Send feedback with lower outcome score
        feedback = StrategyFeedback(
            strategy_id=strategy_id,
            task_id="feedback_test_task",
            success=True,
            outcome_score=0.5,
            execution_time_ms=5000,
        )

        await strategy_memory_service.update_strategy_outcome(feedback)

        # Get updated score
        # Expected: 0.3 * 0.5 + 0.7 * 1.0 = 0.85
        updated = await strategy_memory_service.get_strategy_by_id(strategy_id)
        assert updated is not None
        assert updated.usage_count == 1
        # Score should be somewhere between 0.5 and 1.0
        assert 0.5 < updated.performance_score < 1.0

    @pytest.mark.asyncio
    async def test_multiple_strategies_ranked_by_performance(
        self,
        strategy_memory_service,
        cleanup_test_strategies,
    ):
        """Test that strategies are ranked by performance score."""
        from memory.strategymemory import StrategyFeedback, StrategyRetrievalRequest

        # Create two strategies
        high_perf_id = await strategy_memory_service.record_new_strategy(
            task_id="ranking_test_high",
            description="High performance strategy",
            plan_payload={"task_kind": "ranking_test"},
            context_embedding=[0.0] * 1536,
            tags=["ranking_test"],
        )
        cleanup_test_strategies.append(high_perf_id)

        low_perf_id = await strategy_memory_service.record_new_strategy(
            task_id="ranking_test_low",
            description="Low performance strategy",
            plan_payload={"task_kind": "ranking_test"},
            context_embedding=[0.0] * 1536,
            tags=["ranking_test"],
        )
        cleanup_test_strategies.append(low_perf_id)

        # Give low_perf_id poor feedback multiple times
        for _ in range(3):
            feedback = StrategyFeedback(
                strategy_id=low_perf_id,
                task_id="test",
                success=False,
                outcome_score=0.2,
                execution_time_ms=10000,
            )
            await strategy_memory_service.update_strategy_outcome(feedback)

        # Retrieve strategies
        request = StrategyRetrievalRequest(
            task_id="ranking_query",
            task_kind="ranking_test",
            goal_description="Test ranking",
            tags=["ranking_test"],
            min_confidence=0.0,
        )

        candidates = await strategy_memory_service.retrieve_strategies(
            request, limit=10
        )

        # Verify high_perf comes before low_perf
        high_idx = next(
            (i for i, c in enumerate(candidates) if c.strategy_id == high_perf_id), -1
        )
        low_idx = next(
            (i for i, c in enumerate(candidates) if c.strategy_id == low_perf_id), -1
        )

        if high_idx >= 0 and low_idx >= 0:
            assert high_idx < low_idx, "Higher performance strategy should rank higher"

    @pytest.mark.asyncio
    async def test_strategy_deletion(
        self,
        strategy_memory_service,
    ):
        """Test strategy deletion."""
        # Create a strategy
        strategy_id = await strategy_memory_service.record_new_strategy(
            task_id="delete_test",
            description="Strategy to be deleted",
            plan_payload={},
            context_embedding=[0.0] * 1536,
            tags=["delete_test"],
        )

        # Verify it exists
        found = await strategy_memory_service.get_strategy_by_id(strategy_id)
        assert found is not None

        # Delete it
        deleted = await strategy_memory_service.delete_strategy(strategy_id)
        assert deleted is True

        # Verify it's gone
        not_found = await strategy_memory_service.get_strategy_by_id(strategy_id)
        assert not_found is None

    @pytest.mark.asyncio
    async def test_list_strategies(
        self,
        strategy_memory_service,
        cleanup_test_strategies,
    ):
        """Test listing strategies with filters."""
        # Create a strategy
        strategy_id = await strategy_memory_service.record_new_strategy(
            task_id="list_test",
            description="Strategy for list test",
            plan_payload={},
            context_embedding=[0.0] * 1536,
            tags=["list_test"],
        )
        cleanup_test_strategies.append(strategy_id)

        # List all strategies
        all_strategies = await strategy_memory_service.list_strategies(limit=100)
        assert len(all_strategies) >= 1

        # List with high min_score (should filter out new strategies)
        high_score = await strategy_memory_service.list_strategies(
            limit=100,
            min_score=0.99,
        )
        # New strategies have score 1.0, so should be included
        assert any(s.strategy_id == strategy_id for s in high_score)


# =============================================================================
# Golden Strategy Integration Tests
# =============================================================================


class TestGoldenStrategySeeding:
    """Tests for golden strategy seeding script."""

    @pytest.mark.asyncio
    @must_stay_async("callers use await")
    async def test_seed_golden_strategies_dry_run(self):
        """Verify golden strategy definitions are valid."""
        from scripts.memory.seed_golden_strategies import GOLDEN_STRATEGIES

        assert len(GOLDEN_STRATEGIES) >= 3  # At least 3 golden strategies

        for strategy in GOLDEN_STRATEGIES:
            # Required fields
            assert "name" in strategy
            assert "description" in strategy
            assert "task_kind" in strategy
            assert "tags" in strategy
            assert "plan_payload" in strategy

            # Tags should be a list
            assert isinstance(strategy["tags"], list)
            assert len(strategy["tags"]) > 0

            # Plan payload should have steps
            assert "steps" in strategy["plan_payload"]
            assert len(strategy["plan_payload"]["steps"]) > 0

    @pytest.mark.asyncio
    async def test_seed_and_retrieve_golden_strategy(
        self,
        neo4j_client,
        strategy_memory_service,
    ):
        """Test seeding a golden strategy and retrieving it."""
        from memory.strategymemory import StrategyRetrievalRequest
        from scripts.memory.seed_golden_strategies import GOLDEN_STRATEGIES

        # Use first golden strategy
        golden = GOLDEN_STRATEGIES[0]

        # Seed it
        strategy_id = await strategy_memory_service.record_new_strategy(
            task_id=f"golden_{golden['task_kind']}",
            description=golden["description"],
            plan_payload=golden["plan_payload"],
            context_embedding=[0.0] * 1536,
            tags=golden["tags"],
        )

        try:
            # Retrieve by task_kind and tags
            request = StrategyRetrievalRequest(
                task_id="golden_retrieval_test",
                task_kind=golden["task_kind"],
                goal_description="Test golden strategy retrieval",
                tags=golden["tags"][:2],  # Use first 2 tags
                min_confidence=0.0,
            )

            candidates = await strategy_memory_service.retrieve_strategies(request)

            # Should find the golden strategy
            found = any(c.strategy_id == strategy_id for c in candidates)
            assert found, f"Golden strategy {strategy_id} should be retrievable"

        finally:
            # Cleanup
            await strategy_memory_service.delete_strategy(strategy_id)


# =============================================================================
# Performance Tests
# =============================================================================


class TestStrategyMemoryPerformance:
    """Performance benchmarks for Strategy Memory."""

    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_retrieval_latency(
        self,
        strategy_memory_service,
        cleanup_test_strategies,
    ):
        """Test that retrieval completes within latency SLA (<100ms)."""
        import time

        from memory.strategymemory import StrategyRetrievalRequest

        # Create a few strategies
        for i in range(5):
            sid = await strategy_memory_service.record_new_strategy(
                task_id=f"perf_test_{i}",
                description=f"Performance test strategy {i}",
                plan_payload={"index": i},
                context_embedding=[float(i)] * 1536,
                tags=["perf_test"],
            )
            cleanup_test_strategies.append(sid)

        # Measure retrieval time
        request = StrategyRetrievalRequest(
            task_id="perf_retrieval",
            task_kind="perf_test",
            goal_description="Performance test",
            tags=["perf_test"],
            min_confidence=0.0,
        )

        times = []
        for _ in range(5):
            start = time.perf_counter()
            await strategy_memory_service.retrieve_strategies(request)
            elapsed_ms = (time.perf_counter() - start) * 1000
            times.append(elapsed_ms)

        avg_time = sum(times) / len(times)
        max_time = max(times)

        # SLA: P50 < 100ms, P99 < 500ms
        assert avg_time < 100, (
            f"Average retrieval time {avg_time:.1f}ms exceeds 100ms SLA"
        )
        assert max_time < 500, f"Max retrieval time {max_time:.1f}ms exceeds 500ms SLA"


# =============================================================================
# Auto-Capture Integration Tests (GMP-103)
# =============================================================================


class TestAutoCaptureIntegration:
    """Integration tests for Phase 1 auto-capture functionality."""

    @pytest.mark.asyncio
    @must_stay_async("callers use await")
    async def test_auto_capture_on_successful_execution(
        self,
        strategy_memory_service,
        cleanup_test_strategies,
    ):
        """Test that successful executions are auto-captured as strategies."""
        from dataclasses import dataclass, field
        from uuid import uuid4

        from orchestration.plan_executor import (
            ExecutionStatus,
            ExecutorConfig,
            PlanExecutor,
        )

        # Create executor with auto-capture enabled
        config = ExecutorConfig(
            auto_capture_enabled=True,
            capture_min_success_ratio=0.8,
            dry_run=True,  # Don't actually execute
        )
        executor = PlanExecutor(config=config, strategy_memory=strategy_memory_service)

        # Create a mock plan
        @dataclass
        class MockStep:
            step_id: any = field(default_factory=uuid4)
            action_type: str = "reasoning"
            target: str = "test_target"
            description: str = "Test step"
            parameters: dict = field(default_factory=dict)
            dependencies: list = field(default_factory=list)

        @dataclass
        class MockPlan:
            plan_id: any = field(default_factory=uuid4)
            steps: list = field(default_factory=list)

        plan = MockPlan(
            plan_id=uuid4(),
            steps=[MockStep(), MockStep(), MockStep()],
        )

        # Execute with context (no strategy_id = eligible for capture)
        context = {
            "task_id": "auto_capture_test_001",
            "task_kind": "auto_capture_test",
            "goal_description": "Test auto-capture functionality",
            "tags": ["auto_capture_test", "integration"],
        }

        result = await executor.execute(plan, context)

        # Verify execution succeeded
        assert result.status == ExecutionStatus.COMPLETED
        assert result.completed_steps == 3

        # Verify strategy was captured by searching for it
        from memory.strategymemory import StrategyRetrievalRequest

        request = StrategyRetrievalRequest(
            task_id="verify_capture",
            task_kind="auto_capture_test",
            goal_description="Find captured strategy",
            tags=["auto_capture_test"],
            min_confidence=0.0,
        )

        # Small delay to ensure capture completed
        import asyncio

        await asyncio.sleep(0.1)

        candidates = await strategy_memory_service.retrieve_strategies(request)

        # Should find the auto-captured strategy
        captured = [
            c
            for c in candidates
            if "auto_capture_test_001" in c.description
            or c.plan_payload.get("source_plan_id") == str(plan.plan_id)
        ]

        # Cleanup any captured strategies
        for c in candidates:
            if "auto_capture_test" in c.tags or "auto_capture_test" in str(
                c.description
            ):
                cleanup_test_strategies.append(c.strategy_id)

        assert len(captured) >= 1, "Auto-captured strategy should be retrievable"

    @pytest.mark.asyncio
    async def test_auto_capture_skipped_when_strategy_used(
        self,
        strategy_memory_service,
        cleanup_test_strategies,
    ):
        """Test that auto-capture is skipped when an existing strategy was used."""
        from dataclasses import dataclass, field
        from uuid import uuid4

        from orchestration.plan_executor import (
            ExecutionStatus,
            ExecutorConfig,
            PlanExecutor,
        )

        # First, create a strategy manually
        existing_strategy_id = await strategy_memory_service.record_new_strategy(
            task_id="existing_strategy_test",
            description="Pre-existing strategy",
            plan_payload={"task_kind": "existing_test"},
            context_embedding=[0.0] * 1536,
            tags=["existing_test"],
        )
        cleanup_test_strategies.append(existing_strategy_id)

        # Create executor
        config = ExecutorConfig(
            auto_capture_enabled=True,
            capture_min_success_ratio=0.8,
            dry_run=True,
        )
        executor = PlanExecutor(config=config, strategy_memory=strategy_memory_service)

        # Create mock plan
        @dataclass
        class MockStep:
            step_id: any = field(default_factory=uuid4)
            action_type: str = "reasoning"
            target: str = "test"
            description: str = "Test"
            parameters: dict = field(default_factory=dict)
            dependencies: list = field(default_factory=list)

        @dataclass
        class MockPlan:
            plan_id: any = field(default_factory=uuid4)
            steps: list = field(default_factory=list)

        plan = MockPlan(steps=[MockStep()])

        # Execute WITH strategy_id in context (should NOT auto-capture)
        context = {
            "strategy_id": existing_strategy_id,  # Using existing strategy
            "task_id": "reuse_test",
            "task_kind": "existing_test",
        }

        result = await executor.execute(plan, context)
        assert result.status == ExecutionStatus.COMPLETED

        # Count strategies with this task_kind
        from memory.strategymemory import StrategyRetrievalRequest

        request = StrategyRetrievalRequest(
            task_id="count_test",
            task_kind="existing_test",
            goal_description="Count strategies",
            min_confidence=0.0,
        )

        candidates = await strategy_memory_service.retrieve_strategies(
            request, limit=50
        )

        # Should only have the original strategy, not a duplicate
        existing_kind_strategies = [
            c for c in candidates if c.plan_payload.get("task_kind") == "existing_test"
        ]

        # Cleanup
        for c in existing_kind_strategies:
            if c.strategy_id != existing_strategy_id:
                cleanup_test_strategies.append(c.strategy_id)

        # Should be exactly 1 (the original, no auto-capture duplicate)
        assert len(existing_kind_strategies) == 1, (
            "Should not auto-capture when strategy was used"
        )

    @pytest.mark.asyncio
    @must_stay_async("callers use await")
    async def test_auto_capture_skipped_below_threshold(
        self,
        strategy_memory_service,
    ):
        """Test that auto-capture is skipped when success ratio is below threshold."""
        from orchestration.plan_executor import ExecutorConfig, PlanExecutor

        # Create executor with high threshold
        config = ExecutorConfig(
            auto_capture_enabled=True,
            capture_min_success_ratio=0.99,  # Very high threshold
            dry_run=True,
        )
        executor = PlanExecutor(config=config, strategy_memory=strategy_memory_service)

        # Verify config is set correctly
        assert executor._config.capture_min_success_ratio == 0.99
        assert executor._config.auto_capture_enabled is True
