"""
Consolidation Pipeline Tests
============================

Tests for memory.consolidation.ConsolidationPipeline.
Verifies memory consolidation strategies and reporting.
"""

import os

import pytest

from memory.consolidation import ConsolidationPipeline, ConsolidationReport
from memory.substrate_service import (MemorySubstrateService, close_service,
                                      init_service)

TEST_DB_URL = os.getenv("TEST_DATABASE_URL") or os.getenv("DATABASE_URL")


@pytest.fixture(scope="function")
async def memory_substrate_service():
    """Provide a memory substrate service for testing."""
    if not TEST_DB_URL:
        pytest.skip(
            "TEST_DATABASE_URL or DATABASE_URL not set; skipping consolidation tests."
        )
    service = await init_service(TEST_DB_URL)
    yield service
    await close_service()


@pytest.fixture
def consolidation_pipeline(memory_substrate_service):
    """Provide a ConsolidationPipeline instance."""
    pipeline = ConsolidationPipeline(
        repository=memory_substrate_service._repository,
        dry_run=True,  # Use dry-run for tests
    )
    return pipeline


class TestConsolidationPipeline:
    """Tests for ConsolidationPipeline."""

    def test_initialization(self, consolidation_pipeline):
        """Test ConsolidationPipeline can be instantiated."""
        assert consolidation_pipeline is not None
        assert consolidation_pipeline._dry_run is True

    def test_initialization_with_dry_run_false(self, memory_substrate_service):
        """Test ConsolidationPipeline with dry_run=False."""
        pipeline = ConsolidationPipeline(
            repository=memory_substrate_service._repository,
            dry_run=False,
        )
        assert pipeline._dry_run is False

    @pytest.mark.asyncio
    async def test_run_consolidation_dry_run(self, consolidation_pipeline):
        """Test run_consolidation in dry-run mode."""
        report = await consolidation_pipeline.run_consolidation(
            batch_size=100,
            sleep_between_batches_ms=10,
        )

        assert isinstance(report, ConsolidationReport)
        assert report.start_time is not None
        assert report.end_time is not None
        assert report.deduplication_count >= 0
        assert report.archived_count >= 0
        assert report.summarized_count >= 0
        assert report.expired_count >= 0

    @pytest.mark.asyncio
    async def test_run_consolidation_report_structure(self, consolidation_pipeline):
        """Test consolidation report structure."""
        report = await consolidation_pipeline.run_consolidation()

        report_dict = report.to_dict()

        assert "deduplication_count" in report_dict
        assert "archived_count" in report_dict
        assert "summarized_count" in report_dict
        assert "expired_count" in report_dict
        assert "errors" in report_dict
        assert "start_time" in report_dict
        assert "end_time" in report_dict
        assert "duration_seconds" in report_dict

    @pytest.mark.asyncio
    async def test_ttl_expiration_strategy(
        self,
        memory_substrate_service: MemorySubstrateService,
    ):
        """Test TTL expiration strategy (requires actual DB)."""
        # Create pipeline without dry-run for TTL test
        pipeline = ConsolidationPipeline(
            repository=memory_substrate_service._repository,
            dry_run=False,
        )

        # Run only TTL expiration
        # Note: This will only work if there are expired packets
        expired_count = await pipeline._run_ttl_expiration(
            batch_size=10,
            sleep_ms=0,
        )

        # Should return count (may be 0 if no expired packets)
        assert isinstance(expired_count, int)
        assert expired_count >= 0

    def test_consolidation_config(self, consolidation_pipeline):
        """Test consolidation config values match spec."""
        # Check deduplication config
        assert consolidation_pipeline._deduplication_config["enabled"] is True
        assert (
            consolidation_pipeline._deduplication_config["similarity_threshold"] == 0.95
        )
        assert (
            consolidation_pipeline._deduplication_config["merge_policy"]
            == "keep_highest_confidence"
        )

        # Check archival config
        assert consolidation_pipeline._archival_config["enabled"] is True
        assert len(consolidation_pipeline._archival_config["triggers"]) > 0

        # Check summarization config
        assert consolidation_pipeline._summarization_config["enabled"] is True

        # Check TTL config
        assert consolidation_pipeline._ttl_config["enabled"] is True
        assert consolidation_pipeline._ttl_config["grace_period_hours"] == 24

    @pytest.mark.asyncio
    async def test_consolidation_with_repository_none(self):
        """Test consolidation handles missing repository gracefully."""
        pipeline = ConsolidationPipeline(repository=None, dry_run=True)

        # Should raise RuntimeError when repository not set
        with pytest.raises(RuntimeError, match="Repository not set"):
            await pipeline.run_consolidation()
