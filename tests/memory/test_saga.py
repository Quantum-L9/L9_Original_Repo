"""
Tests for Cross-DB Saga Pattern (GMP-56)

Tests the saga executor and pre-built saga patterns.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID

from memory.saga import (
    SagaBuilder,
    SagaContext,
    SagaExecutor,
    SagaResult,
    SagaStepResult,
    SagaStepStatus,
    SagaStatus,
    DatabaseType,
)

from memory.saga_patterns import (
    SagaPatterns,
    create_fetch_and_enrich_saga,
    create_entity_enrichment_saga,
    create_timeline_correlation_saga,
    fetch_and_enrich,
)


class TestSagaContext:
    """Test SagaContext functionality."""

    def test_context_creation(self):
        """Test creating a saga context."""
        context = SagaContext(
            saga_id=UUID("12345678-1234-1234-1234-123456789012"),
            input_data={"query": "test"},
        )

        assert context.saga_id == UUID("12345678-1234-1234-1234-123456789012")
        assert context.input_data["query"] == "test"
        assert context.entities == []
        assert context.relationships == []

    def test_step_output_management(self):
        """Test setting and getting step outputs."""
        context = SagaContext(saga_id=UUID("12345678-1234-1234-1234-123456789012"))

        context.set_step_output("step1", {"data": [1, 2, 3]})

        assert context.get_step_output("step1") == {"data": [1, 2, 3]}
        assert context.get_step_output("nonexistent") is None

    def test_entity_accumulation(self):
        """Test adding entities to context."""
        context = SagaContext(saga_id=UUID("12345678-1234-1234-1234-123456789012"))

        context.add_entities(
            [
                {"type": "User", "id": "user-1"},
                {"type": "User", "id": "user-2"},
            ]
        )

        context.add_entities(
            [
                {"type": "GMP", "id": "gmp-55"},
            ]
        )

        assert len(context.entities) == 3
        assert context.entities[0]["id"] == "user-1"
        assert context.entities[2]["id"] == "gmp-55"

    def test_relationship_accumulation(self):
        """Test adding relationships to context."""
        context = SagaContext(saga_id=UUID("12345678-1234-1234-1234-123456789012"))

        context.add_relationships(
            [
                {"from": "user-1", "to": "user-2", "type": "FOLLOWS"},
            ]
        )

        assert len(context.relationships) == 1
        assert context.relationships[0]["type"] == "FOLLOWS"


class TestSagaBuilder:
    """Test SagaBuilder fluent API."""

    def test_build_simple_saga(self):
        """Test building a simple saga."""

        async def step1(context, **kwargs):
            return {"result": "step1"}

        async def step2(context, **kwargs):
            return {"result": "step2"}

        saga = (
            SagaBuilder("test_saga", "A test saga")
            .add_step(
                name="step1",
                database=DatabaseType.POSTGRES,
                execute_fn=step1,
            )
            .add_step(
                name="step2",
                database=DatabaseType.NEO4J,
                execute_fn=step2,
                required=False,
            )
            .build()
        )

        assert saga.name == "test_saga"
        assert saga.description == "A test saga"
        assert len(saga.steps) == 2
        assert saga.steps[0].name == "step1"
        assert saga.steps[1].required is False

    def test_custom_output_builder(self):
        """Test saga with custom output builder."""

        async def step1(context, **kwargs):
            return [1, 2, 3]

        def custom_output(context):
            return {"custom": True, "data": context.step_outputs}

        saga = (
            SagaBuilder("custom_saga")
            .add_step(name="step1", database=DatabaseType.MEMORY, execute_fn=step1)
            .with_output_builder(custom_output)
            .build()
        )

        context = SagaContext(saga_id=UUID("12345678-1234-1234-1234-123456789012"))
        context.set_step_output("step1", [1, 2, 3])

        output = saga.build_output(context)
        assert output["custom"] is True


class TestSagaExecutor:
    """Test SagaExecutor functionality."""

    @pytest.mark.asyncio
    async def test_execute_simple_saga(self):
        """Test executing a simple saga."""

        async def step1(context, **kwargs):
            return {"value": 1}

        async def step2(context, **kwargs):
            prev = context.get_step_output("step1")
            return {"value": prev["value"] + 1}

        saga = (
            SagaBuilder("simple")
            .add_step(name="step1", database=DatabaseType.MEMORY, execute_fn=step1)
            .add_step(name="step2", database=DatabaseType.MEMORY, execute_fn=step2)
            .build()
        )

        executor = SagaExecutor()
        result = await executor.execute(saga)

        assert result.status == SagaStatus.COMPLETED
        assert result.steps_completed == 2
        assert result.steps_failed == 0
        assert len(result.step_results) == 2

    @pytest.mark.asyncio
    async def test_execute_with_failing_required_step(self):
        """Test saga with failing required step triggers compensation."""

        async def step1(context, **kwargs):
            return {"value": 1}

        async def step2_fail(context, **kwargs):
            raise ValueError("Intentional failure")

        compensated = []

        async def compensate_step1(context, **kwargs):
            compensated.append("step1")

        saga = (
            SagaBuilder("failing")
            .add_step(
                name="step1",
                database=DatabaseType.MEMORY,
                execute_fn=step1,
                compensate_fn=compensate_step1,
            )
            .add_step(
                name="step2",
                database=DatabaseType.MEMORY,
                execute_fn=step2_fail,
                required=True,
            )
            .build()
        )

        executor = SagaExecutor()
        result = await executor.execute(saga)

        assert result.status == SagaStatus.COMPENSATED
        assert result.steps_failed == 1
        assert result.failed_step == "step2"
        assert "step1" in compensated

    @pytest.mark.asyncio
    async def test_execute_with_failing_optional_step(self):
        """Test saga continues when optional step fails."""

        async def step1(context, **kwargs):
            return {"value": 1}

        async def step2_fail(context, **kwargs):
            raise ValueError("Intentional failure")

        async def step3(context, **kwargs):
            return {"value": 3}

        saga = (
            SagaBuilder("optional_failure")
            .add_step(name="step1", database=DatabaseType.MEMORY, execute_fn=step1)
            .add_step(
                name="step2",
                database=DatabaseType.MEMORY,
                execute_fn=step2_fail,
                required=False,  # Optional
            )
            .add_step(name="step3", database=DatabaseType.MEMORY, execute_fn=step3)
            .build()
        )

        executor = SagaExecutor()
        result = await executor.execute(saga)

        assert result.status == SagaStatus.PARTIALLY_COMPLETED
        assert result.steps_completed == 2
        assert result.steps_failed == 1

    @pytest.mark.asyncio
    async def test_execute_with_condition(self):
        """Test step with condition function."""

        async def step1(context, **kwargs):
            return {"should_run_step2": False}

        async def step2(context, **kwargs):
            return {"ran": True}

        def should_run_step2(context):
            prev = context.get_step_output("step1") or {}
            return prev.get("should_run_step2", False)

        saga = (
            SagaBuilder("conditional")
            .add_step(name="step1", database=DatabaseType.MEMORY, execute_fn=step1)
            .add_step(
                name="step2",
                database=DatabaseType.MEMORY,
                execute_fn=step2,
                condition_fn=should_run_step2,
            )
            .build()
        )

        executor = SagaExecutor()
        result = await executor.execute(saga)

        assert result.status == SagaStatus.COMPLETED
        assert result.steps_completed == 1
        assert result.steps_skipped == 1

    @pytest.mark.asyncio
    async def test_execute_with_input_data(self):
        """Test saga receives input data."""

        async def step1(context, **kwargs):
            return {"query": context.input_data.get("query")}

        saga = (
            SagaBuilder("with_input")
            .add_step(name="step1", database=DatabaseType.MEMORY, execute_fn=step1)
            .build()
        )

        executor = SagaExecutor()
        result = await executor.execute(
            saga,
            input_data={"query": "test query"},
        )

        assert result.status == SagaStatus.COMPLETED
        assert result.output["step_outputs"]["step1"]["query"] == "test query"


class TestPrebuiltSagas:
    """Test pre-built saga patterns."""

    def test_fetch_and_enrich_saga_structure(self):
        """Test fetch_and_enrich saga has correct steps."""
        saga = create_fetch_and_enrich_saga()

        assert saga.name == "fetch_and_enrich"
        assert len(saga.steps) == 4

        step_names = [s.name for s in saga.steps]
        assert "vector_search" in step_names
        assert "extract_entities" in step_names
        assert "graph_enrich" in step_names
        assert "assemble_result" in step_names

        # Graph enrich should be optional
        graph_step = next(s for s in saga.steps if s.name == "graph_enrich")
        assert graph_step.required is False

    def test_entity_enrichment_saga_structure(self):
        """Test entity_enrichment saga has correct steps."""
        saga = create_entity_enrichment_saga()

        assert saga.name == "entity_enrichment"
        assert len(saga.steps) == 2

        step_names = [s.name for s in saga.steps]
        assert "lookup_entities" in step_names
        assert "graph_enrich" in step_names

    def test_timeline_correlation_saga_structure(self):
        """Test timeline_correlation saga has correct steps."""
        saga = create_timeline_correlation_saga()

        assert saga.name == "timeline_correlation"
        assert len(saga.steps) == 2

        step_names = [s.name for s in saga.steps]
        assert "fetch_events" in step_names
        assert "trace_causal_chains" in step_names


class TestSagaPatterns:
    """Test SagaPatterns high-level API."""

    @pytest.mark.asyncio
    async def test_patterns_fetch_and_enrich(self):
        """Test SagaPatterns.fetch_and_enrich()."""
        # Create mock services
        mock_semantic = MagicMock()
        mock_semantic.search = AsyncMock(return_value=[])

        mock_neo4j = MagicMock()
        mock_neo4j.is_available.return_value = False

        executor = SagaExecutor(
            semantic_service=mock_semantic,
            neo4j_client=mock_neo4j,
        )

        patterns = SagaPatterns(executor)
        result = await patterns.fetch_and_enrich(query="test query", limit=5)

        assert result.saga_name == "fetch_and_enrich"
        assert result.status in (SagaStatus.COMPLETED, SagaStatus.PARTIALLY_COMPLETED)

    @pytest.mark.asyncio
    async def test_patterns_enrich_entities(self):
        """Test SagaPatterns.enrich_entities()."""
        mock_neo4j = MagicMock()
        mock_neo4j.is_available.return_value = True
        mock_neo4j.run_query = AsyncMock(
            return_value=[{"id": "user-1", "properties": {"name": "Alice"}}]
        )

        executor = SagaExecutor(neo4j_client=mock_neo4j)
        patterns = SagaPatterns(executor)

        result = await patterns.enrich_entities(
            entity_ids=["user-1"],
            entity_type="User",
        )

        assert result.saga_name == "entity_enrichment"

    @pytest.mark.asyncio
    async def test_patterns_correlate_timeline(self):
        """Test SagaPatterns.correlate_timeline()."""
        mock_neo4j = MagicMock()
        mock_neo4j.is_available.return_value = True
        mock_neo4j.run_query = AsyncMock(return_value=[])

        executor = SagaExecutor(neo4j_client=mock_neo4j)
        patterns = SagaPatterns(executor)

        result = await patterns.correlate_timeline(
            start_time="2026-01-01T00:00:00Z",
            end_time="2026-01-12T23:59:59Z",
        )

        assert result.saga_name == "timeline_correlation"


class TestConvenienceFunctions:
    """Test convenience functions."""

    @pytest.mark.asyncio
    async def test_fetch_and_enrich_convenience(self):
        """Test fetch_and_enrich() convenience function."""
        mock_semantic = MagicMock()
        mock_semantic.search = AsyncMock(return_value=[])

        mock_neo4j = MagicMock()
        mock_neo4j.is_available.return_value = False

        # Reset singleton
        import memory.saga_patterns

        memory.saga_patterns._patterns = None
        import memory.saga

        memory.saga._executor = None

        result = await fetch_and_enrich(
            query="test",
            semantic_service=mock_semantic,
            neo4j_client=mock_neo4j,
        )

        assert isinstance(result, SagaResult)
        assert result.saga_name == "fetch_and_enrich"


class TestSagaResult:
    """Test SagaResult functionality."""

    def test_result_to_dict(self):
        """Test converting result to dictionary."""
        result = SagaResult(
            saga_id=UUID("12345678-1234-1234-1234-123456789012"),
            saga_name="test_saga",
            status=SagaStatus.COMPLETED,
            steps_completed=2,
            steps_failed=0,
            total_duration_ms=100.5,
        )

        result.step_results.append(
            SagaStepResult(
                step_id="step-1",
                step_name="step1",
                status=SagaStepStatus.COMPLETED,
                database=DatabaseType.POSTGRES,
                duration_ms=50.0,
                records_processed=10,
            )
        )

        d = result.to_dict()

        assert d["saga_id"] == "12345678-1234-1234-1234-123456789012"
        assert d["saga_name"] == "test_saga"
        assert d["status"] == "completed"
        assert d["steps_completed"] == 2
        assert len(d["step_results"]) == 1
        assert d["step_results"][0]["step_name"] == "step1"
