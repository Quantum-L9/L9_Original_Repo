"""
Tests for Research Factory schema models and nodes.

Validates:
- Model instantiation
- Field constraints
- LangGraph node signatures
- State transitions
"""

from uuid import uuid4

import pytest

from core.schemas.research_factory_models import (IntegrationResult,
                                                  ParsedObject, Query,
                                                  QueryPlan, ResearchJobSpec,
                                                  ResearchMetrics,
                                                  ValidationStatus)
from core.schemas.research_factory_state import PassStatus, ResearchState


class TestResearchJobSpec:
    """Test ResearchJobSpec model."""

    def test_valid_job_spec(self):
        """Verify valid job spec creation."""
        spec = ResearchJobSpec(
            domain="plastics", polymer="HDPE", regions=["US", "EU"], max_results=100
        )

        assert spec.domain == "plastics"
        assert spec.polymer == "HDPE"
        assert spec.regions == ["US", "EU"]
        assert spec.max_results == 100

    def test_regions_normalized_to_uppercase(self):
        """Verify regions are normalized to uppercase."""
        spec = ResearchJobSpec(
            domain="test", polymer="PE", regions=["us", "eu", "Asia"]
        )

        assert spec.regions == ["US", "EU", "ASIA"]

    def test_empty_regions_rejected(self):
        """Verify empty regions list is rejected."""
        with pytest.raises(ValueError):
            ResearchJobSpec(domain="test", polymer="PE", regions=[])

    def test_max_results_bounds(self):
        """Verify max_results bounds are enforced."""
        # Valid min
        spec = ResearchJobSpec(
            domain="test", polymer="PE", regions=["US"], max_results=1
        )
        assert spec.max_results == 1

        # Invalid: below min
        with pytest.raises(ValueError):
            ResearchJobSpec(domain="test", polymer="PE", regions=["US"], max_results=0)

        # Invalid: above max
        with pytest.raises(ValueError):
            ResearchJobSpec(
                domain="test", polymer="PE", regions=["US"], max_results=10000
            )


class TestQueryPlan:
    """Test QueryPlan model."""

    def test_valid_query_plan(self):
        """Verify valid query plan creation."""
        queries = [
            Query(query_text="HDPE suppliers US", priority=1),
            Query(query_text="HDPE market analysis", priority=2),
        ]

        plan = QueryPlan(job_id=uuid4(), queries=queries, strategy="breadth_first")

        assert len(plan.queries) == 2
        assert plan.strategy == "breadth_first"

    def test_empty_queries_rejected(self):
        """Verify empty queries list is rejected."""
        with pytest.raises(ValueError):
            QueryPlan(job_id=uuid4(), queries=[], strategy="test")


class TestParsedObject:
    """Test ParsedObject model."""

    def test_valid_parsed_object(self):
        """Verify valid parsed object creation."""
        obj = ParsedObject(
            batch_id=uuid4(),
            extracted_data={"key": "value"},
            validation_status=ValidationStatus.VALID,
            confidence=0.95,
        )

        assert obj.validation_status == ValidationStatus.VALID
        assert obj.confidence == 0.95

    def test_confidence_bounds(self):
        """Verify confidence bounds are enforced."""
        # Valid: at bounds
        obj = ParsedObject(
            batch_id=uuid4(),
            extracted_data={},
            validation_status=ValidationStatus.VALID,
            confidence=0.0,
        )
        assert obj.confidence == 0.0

        obj = ParsedObject(
            batch_id=uuid4(),
            extracted_data={},
            validation_status=ValidationStatus.VALID,
            confidence=1.0,
        )
        assert obj.confidence == 1.0

        # Invalid: above 1.0
        with pytest.raises(ValueError):
            ParsedObject(
                batch_id=uuid4(),
                extracted_data={},
                validation_status=ValidationStatus.VALID,
                confidence=1.5,
            )


class TestResearchMetrics:
    """Test ResearchMetrics model."""

    def test_valid_metrics(self):
        """Verify valid metrics creation."""
        metrics = ResearchMetrics(
            total_queries=10,
            total_results=100,
            valid_results=85,
            invalid_results=15,
            avg_confidence=0.87,
            total_latency_ms=5000.0,
            pass_durations_ms={"pass_1": 100, "pass_2": 200},
        )

        assert metrics.total_queries == 10
        assert metrics.valid_results == 85


class TestResearchState:
    """Test ResearchState model."""

    def test_initial_state(self):
        """Verify initial state creation."""
        state = ResearchState()

        assert state.current_pass == 0
        assert state.job_spec is None
        assert state.query_plan is None
        assert not state.is_complete
        assert not state.has_errors

    def test_start_pass(self):
        """Verify pass start updates state."""
        state = ResearchState()
        state = state.start_pass(1)

        assert state.current_pass == 1
        assert state.pass_metadata["pass_1"].status == PassStatus.RUNNING
        assert state.pass_metadata["pass_1"].started_at is not None

    def test_complete_pass_success(self):
        """Verify successful pass completion."""
        state = ResearchState()
        state = state.start_pass(1)
        state = state.complete_pass(1)

        assert state.pass_metadata["pass_1"].status == PassStatus.COMPLETED
        assert state.pass_metadata["pass_1"].completed_at is not None
        assert state.pass_metadata["pass_1"].duration_ms is not None

    def test_complete_pass_failure(self):
        """Verify failed pass completion."""
        state = ResearchState()
        state = state.start_pass(1)
        state = state.complete_pass(1, error="Test error")

        assert state.pass_metadata["pass_1"].status == PassStatus.FAILED
        assert state.pass_metadata["pass_1"].error == "Test error"
        assert state.has_errors
        assert "Pass 1: Test error" in state.errors

    def test_add_error(self):
        """Verify error addition."""
        state = ResearchState()
        state = state.add_error("Error 1")
        state = state.add_error("Error 2")

        assert len(state.errors) == 2
        assert "Error 1" in state.errors
        assert "Error 2" in state.errors

    def test_is_complete(self):
        """Verify is_complete property."""
        state = ResearchState()

        # Complete all passes
        for i in range(1, 6):
            state = state.start_pass(i)
            state = state.complete_pass(i)

        assert state.is_complete


class TestIntegrationResult:
    """Test IntegrationResult model."""

    def test_success_rate_property(self):
        """Verify success_rate calculation."""
        job_spec = ResearchJobSpec(domain="test", polymer="PE", regions=["US"])

        query_plan = QueryPlan(
            job_id=job_spec.job_id, queries=[Query(query_text="test")], strategy="test"
        )

        parsed_objects = [
            ParsedObject(
                batch_id=uuid4(),
                extracted_data={},
                validation_status=ValidationStatus.VALID,
                confidence=0.9,
            ),
            ParsedObject(
                batch_id=uuid4(),
                extracted_data={},
                validation_status=ValidationStatus.VALID,
                confidence=0.8,
            ),
            ParsedObject(
                batch_id=uuid4(),
                extracted_data={},
                validation_status=ValidationStatus.INVALID,
                confidence=0.3,
            ),
        ]

        metrics = ResearchMetrics(
            total_queries=1,
            total_results=3,
            valid_results=2,
            invalid_results=1,
            avg_confidence=0.67,
            total_latency_ms=100.0,
        )

        result = IntegrationResult(
            job_spec=job_spec,
            query_plan=query_plan,
            superprompts=[],
            retrieval_batches=1,
            parsed_objects=parsed_objects,
            integration_summary={},
            metrics=metrics,
        )

        assert result.success_rate == pytest.approx(2 / 3, rel=0.01)


@pytest.mark.asyncio
class TestResearchFactoryNodes:
    """Test LangGraph node functions."""

    async def test_pass_1_plan_queries(self):
        """Test pass_1_plan_queries node."""
        from core.schemas.research_factory_nodes import pass_1_plan_queries

        job_spec = ResearchJobSpec(
            domain="plastics", polymer="HDPE", regions=["US", "EU"]
        )

        state = ResearchState(job_spec=job_spec)
        result = await pass_1_plan_queries(state)

        assert result.query_plan is not None
        assert len(result.query_plan.queries) > 0
        assert result.pass_metadata["pass_1"].status == PassStatus.COMPLETED

    async def test_pass_2_build_superprompts(self):
        """Test pass_2_build_superprompts node."""
        from core.schemas.research_factory_nodes import (
            pass_1_plan_queries, pass_2_build_superprompts)

        job_spec = ResearchJobSpec(domain="plastics", polymer="HDPE", regions=["US"])

        state = ResearchState(job_spec=job_spec)
        state = await pass_1_plan_queries(state)
        result = await pass_2_build_superprompts(state)

        assert len(result.superprompts) > 0
        assert result.pass_metadata["pass_2"].status == PassStatus.COMPLETED

    async def test_full_pipeline(self):
        """Test full 5-pass pipeline execution."""
        from core.schemas.research_factory_nodes import (
            pass_1_plan_queries, pass_2_build_superprompts,
            pass_3_execute_retrieval, pass_4_extract_results,
            pass_5_integrate_results)

        job_spec = ResearchJobSpec(domain="plastics", polymer="HDPE", regions=["US"])

        state = ResearchState(job_spec=job_spec)

        # Execute all passes
        state = await pass_1_plan_queries(state)
        state = await pass_2_build_superprompts(state)
        state = await pass_3_execute_retrieval(state)
        state = await pass_4_extract_results(state)
        state = await pass_5_integrate_results(state)

        # Verify final state
        assert state.is_complete
        assert state.integration_result is not None
        assert state.integration_result.status in ["completed", "completed_with_errors"]
