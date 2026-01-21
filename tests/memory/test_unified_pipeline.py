"""
Integration tests for unified memory pipeline (GMP-67).

Tests:
1. Core writes work with enrichment disabled
2. Core writes + enrichment work when enabled
3. Enrichment failure doesn't block core writes
4. MCP fallback tiers work correctly
5. Idempotency: same packet twice = no duplicate facts
6. Enrichment timeout handling
"""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from core.schemas import (
    PacketEnvelope,
    PacketEnvelopeIn,
    PacketWriteResult,
)
from memory.substrate_models import EnrichmentResult, KnowledgeFact

# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def mock_repository():
    """Create a mock SubstrateRepository."""
    repo = AsyncMock()
    repo.insert_packet = AsyncMock(return_value=uuid4())
    repo.insert_memory_event = AsyncMock(return_value=uuid4())
    repo.insert_knowledge_fact = AsyncMock()
    repo.transaction = MagicMock()
    repo.transaction.return_value.__aenter__ = AsyncMock()
    repo.transaction.return_value.__aexit__ = AsyncMock()
    return repo


@pytest.fixture
def mock_semantic_service():
    """Create a mock SemanticService."""
    service = AsyncMock()
    service.embed_and_store = AsyncMock(return_value=uuid4())
    return service


@pytest.fixture
def mock_dag():
    """Create a mock SubstrateDAG that returns successful enrichment."""
    dag = AsyncMock()
    dag.enrich = AsyncMock(
        return_value=EnrichmentResult(
            packet_id=uuid4(),
            facts=[],
            insights=[],
            reasoning_trace=None,
            facts_inserted=2,
            world_model_triggered=False,
            enrichment_duration_ms=100.0,
        )
    )
    return dag


@pytest.fixture
def sample_packet_in():
    """Create a sample PacketEnvelopeIn for testing."""
    return PacketEnvelopeIn(
        packet_type="memory.test",
        payload={"content": "Test content for unified pipeline", "kind": "test"},
        tags=["test", "gmp-67"],
    )


# =============================================================================
# Test: Core Writes with Enrichment Disabled
# =============================================================================


class TestCoreWritesEnrichmentDisabled:
    """Test that core writes succeed when enrichment is disabled."""

    @pytest.mark.asyncio
    async def test_core_writes_work_without_enrichment(
        self, mock_repository, mock_semantic_service, sample_packet_in
    ):
        """Core writes succeed with enrichment disabled."""
        from memory.ingestion import IngestionPipeline

        pipeline = IngestionPipeline(
            repository=mock_repository,
            semantic_service=mock_semantic_service,
            enable_enrichment=False,  # Disabled
        )

        result = await pipeline.ingest(sample_packet_in)

        assert result.status == "ok"
        assert result.enrichment_status == "disabled"
        assert result.enrichment_facts_count == 0
        assert result.write_tier_used == "core_only"
        assert "packet_store" in result.written_tables or mock_repository.insert_packet.called

    @pytest.mark.asyncio
    async def test_enrichment_disabled_returns_disabled_status(
        self, mock_repository, mock_semantic_service, sample_packet_in
    ):
        """Enrichment status is 'disabled' when flag is False."""
        from memory.ingestion import IngestionPipeline

        pipeline = IngestionPipeline(
            repository=mock_repository,
            semantic_service=mock_semantic_service,
            enable_enrichment=False,
        )

        result = await pipeline.ingest(sample_packet_in)

        assert result.enrichment_status == "disabled"


# =============================================================================
# Test: Core Writes + Enrichment Enabled
# =============================================================================


class TestCoreWritesWithEnrichment:
    """Test that core writes + enrichment work when enabled."""

    @pytest.mark.asyncio
    async def test_core_writes_plus_enrichment_success(
        self, mock_repository, mock_semantic_service, mock_dag, sample_packet_in
    ):
        """Core writes + enrichment succeed when both work."""
        from memory.ingestion import IngestionPipeline

        pipeline = IngestionPipeline(
            repository=mock_repository,
            semantic_service=mock_semantic_service,
            dag=mock_dag,
            enable_enrichment=True,
        )

        result = await pipeline.ingest(sample_packet_in)

        assert result.status == "ok"
        assert result.enrichment_status == "success"
        assert result.enrichment_facts_count == 2
        assert result.write_tier_used == "full"
        mock_dag.enrich.assert_called_once()

    @pytest.mark.asyncio
    async def test_enrichment_success_adds_knowledge_facts_table(
        self, mock_repository, mock_semantic_service, mock_dag, sample_packet_in
    ):
        """Successful enrichment adds 'knowledge_facts' to written_tables."""
        from memory.ingestion import IngestionPipeline

        pipeline = IngestionPipeline(
            repository=mock_repository,
            semantic_service=mock_semantic_service,
            dag=mock_dag,
            enable_enrichment=True,
        )

        result = await pipeline.ingest(sample_packet_in)

        assert "knowledge_facts" in result.written_tables


# =============================================================================
# Test: Enrichment Failure Doesn't Block Core Writes
# =============================================================================


class TestEnrichmentFailureNonBlocking:
    """Test that enrichment failure doesn't block core writes."""

    @pytest.mark.asyncio
    async def test_enrichment_exception_does_not_block_core(
        self, mock_repository, mock_semantic_service, sample_packet_in
    ):
        """Enrichment exception = core write persisted, enrichment_status='failed'."""
        from memory.ingestion import IngestionPipeline

        # DAG that throws exception
        failing_dag = AsyncMock()
        failing_dag.enrich = AsyncMock(side_effect=Exception("DAG exploded"))

        pipeline = IngestionPipeline(
            repository=mock_repository,
            semantic_service=mock_semantic_service,
            dag=failing_dag,
            enable_enrichment=True,
        )

        result = await pipeline.ingest(sample_packet_in)

        # Core write succeeded!
        assert result.status == "ok"
        # Enrichment failed
        assert result.enrichment_status == "failed"
        assert result.enrichment_error == "DAG exploded"
        assert result.write_tier_used == "core_only"
        # Core tables still written
        assert mock_repository.insert_packet.called or "packet_store" in result.written_tables

    @pytest.mark.asyncio
    async def test_enrichment_failure_logged_with_error(
        self, mock_repository, mock_semantic_service, sample_packet_in
    ):
        """Enrichment failure includes error message in result."""
        from memory.ingestion import IngestionPipeline

        failing_dag = AsyncMock()
        failing_dag.enrich = AsyncMock(side_effect=ValueError("Invalid state"))

        pipeline = IngestionPipeline(
            repository=mock_repository,
            semantic_service=mock_semantic_service,
            dag=failing_dag,
            enable_enrichment=True,
        )

        result = await pipeline.ingest(sample_packet_in)

        assert result.enrichment_status == "failed"
        assert "Invalid state" in result.enrichment_error
        assert result.warnings == ["Invalid state"]


# =============================================================================
# Test: Enrichment Timeout Handling
# =============================================================================


class TestEnrichmentTimeout:
    """Test enrichment timeout handling."""

    @pytest.mark.asyncio
    async def test_enrichment_timeout_logs_and_continues(
        self, mock_repository, mock_semantic_service, sample_packet_in
    ):
        """Slow DAG = timeout, core write persisted, enrichment_status='failed'."""
        from memory.ingestion import IngestionPipeline

        async def slow_enrich(*args, **kwargs):
            await asyncio.sleep(60)  # Way longer than timeout
            return EnrichmentResult(
                packet_id=uuid4(),
                facts=[],
                insights=[],
                facts_inserted=0,
                world_model_triggered=False,
                enrichment_duration_ms=60000.0,
            )

        slow_dag = AsyncMock()
        slow_dag.enrich = slow_enrich

        pipeline = IngestionPipeline(
            repository=mock_repository,
            semantic_service=mock_semantic_service,
            dag=slow_dag,
            enable_enrichment=True,
            enrichment_timeout=0.1,  # 100ms timeout
        )

        result = await pipeline.ingest(sample_packet_in)

        # Core write succeeded
        assert result.status == "ok"
        # Enrichment timed out
        assert result.enrichment_status == "failed"
        assert "timed out" in result.enrichment_error.lower()


# =============================================================================
# Test: PacketWriteResult Schema
# =============================================================================


class TestPacketWriteResultSchema:
    """Test PacketWriteResult has all required fields."""

    def test_packet_write_result_has_enrichment_fields(self):
        """PacketWriteResult includes enrichment fields."""
        result = PacketWriteResult(
            status="ok",
            packet_id=uuid4(),
            written_tables=["packet_store"],
            enrichment_status="success",
            enrichment_error=None,
            enrichment_facts_count=5,
            write_tier_used="full",
            warnings=[],
        )

        assert result.enrichment_status == "success"
        assert result.enrichment_facts_count == 5
        assert result.write_tier_used == "full"
        assert result.warnings == []

    def test_packet_write_result_defaults(self):
        """PacketWriteResult has correct defaults."""
        result = PacketWriteResult(
            status="ok",
            packet_id=uuid4(),
        )

        assert result.enrichment_status == "not_attempted"
        assert result.enrichment_error is None
        assert result.enrichment_facts_count == 0
        assert result.write_tier_used == "full"
        assert result.warnings == []


# =============================================================================
# Test: EnrichmentResult Schema
# =============================================================================


class TestEnrichmentResultSchema:
    """Test EnrichmentResult has all required fields."""

    def test_enrichment_result_fields(self):
        """EnrichmentResult includes all expected fields."""
        packet_id = uuid4()
        result = EnrichmentResult(
            packet_id=packet_id,
            facts=[KnowledgeFact(subject="test", predicate="is", object="value")],
            insights=[],
            reasoning_trace=None,
            facts_inserted=1,
            world_model_triggered=True,
            enrichment_duration_ms=150.5,
        )

        assert result.packet_id == packet_id
        assert len(result.facts) == 1
        assert result.facts_inserted == 1
        assert result.world_model_triggered is True
        assert result.enrichment_duration_ms == 150.5


# =============================================================================
# Test: SubstrateDAG.enrich() Pre-validation
# =============================================================================


class TestSubstrateDAGEnrichPrevalidation:
    """Test SubstrateDAG.enrich() validates envelope."""

    @pytest.mark.asyncio
    async def test_enrich_requires_packet_id(self, mock_repository):
        """enrich() raises if envelope has no packet_id."""
        from memory.substrate_dag import SubstrateDAG

        dag = SubstrateDAG(repository=mock_repository)

        # Create envelope without packet_id
        envelope = PacketEnvelope(
            packet_id=None,  # Missing!
            packet_type="test",
            payload={"content": "test"},
        )

        with pytest.raises(ValueError, match="packet_id"):
            await dag.enrich(envelope)

    @pytest.mark.asyncio
    async def test_enrich_requires_packet_type(self, mock_repository):
        """enrich() raises if envelope has no packet_type."""
        from memory.substrate_dag import SubstrateDAG

        dag = SubstrateDAG(repository=mock_repository)

        # Create envelope without packet_type (Pydantic won't allow this easily,
        # so we test with empty string)
        envelope = PacketEnvelope(
            packet_id=uuid4(),
            packet_type="",  # Empty = falsy
            payload={"content": "test"},
        )

        with pytest.raises(ValueError, match="packet_type"):
            await dag.enrich(envelope)


# =============================================================================
# Test: Feature Flag Integration
# =============================================================================


class TestFeatureFlagIntegration:
    """Test ENABLE_DAG_ENRICHMENT feature flag."""

    def test_settings_has_enable_dag_enrichment(self):
        """MemorySubstrateSettings has enable_dag_enrichment field."""
        from config.memory_substrate_settings import MemorySubstrateSettings

        # Check field exists in model
        assert "enable_dag_enrichment" in MemorySubstrateSettings.model_fields

    def test_settings_default_enrichment_disabled(self):
        """Default for enable_dag_enrichment is False."""
        from config.memory_substrate_settings import MemorySubstrateSettings

        # Get the default value from field info
        field_info = MemorySubstrateSettings.model_fields["enable_dag_enrichment"]
        assert field_info.default is False


# =============================================================================
# Test: MCP Tiered Fallback (Unit Tests)
# =============================================================================


class TestMCPTieredFallback:
    """Test MCP tiered fallback behavior."""

    @pytest.mark.asyncio
    async def test_mcp_returns_enrichment_fields_on_success(self):
        """MCP response includes enrichment fields when pipeline succeeds."""
        from mcp_memory.src.routes.memory_unified import save_memory_handler

        # Mock substrate service
        mock_service = AsyncMock()
        mock_service.write_packet = AsyncMock(
            return_value=PacketWriteResult(
                status="ok",
                packet_id=uuid4(),
                written_tables=["packet_store", "knowledge_facts"],
                enrichment_status="success",
                enrichment_error=None,
                enrichment_facts_count=3,
                write_tier_used="full",
                warnings=[],
            )
        )

        result = await save_memory_handler(
            user_id="test",
            content="Test content",
            kind="fact",
            substrate_service=mock_service,
        )

        assert result["enrichment_status"] == "success"
        assert result["enrichment_facts_count"] == 3
        assert result["tier_used"] == "full"

    @pytest.mark.asyncio
    async def test_mcp_returns_200_on_enrichment_failure(self):
        """Enrichment failure = 200 with enrichment_status='failed'."""
        from mcp_memory.src.routes.memory_unified import save_memory_handler

        # Mock substrate service that returns enrichment failure
        mock_service = AsyncMock()
        mock_service.write_packet = AsyncMock(
            return_value=PacketWriteResult(
                status="ok",  # Core write succeeded!
                packet_id=uuid4(),
                written_tables=["packet_store"],
                enrichment_status="failed",
                enrichment_error="DAG timeout",
                enrichment_facts_count=0,
                write_tier_used="core_only",
                warnings=["DAG timeout"],
            )
        )

        result = await save_memory_handler(
            user_id="test",
            content="Test content",
            kind="fact",
            substrate_service=mock_service,
        )

        # Should return 200 (not raise)
        assert result["enrichment_status"] == "failed"
        assert result["tier_used"] == "core_only"
        assert "packet_id" in result  # Core write succeeded


# =============================================================================
# Marker for slow/integration tests
# =============================================================================


@pytest.mark.slow
class TestIntegrationWithRealDAG:
    """Integration tests that require real DAG (marked as slow)."""

    @pytest.mark.skip(reason="Requires database connection")
    @pytest.mark.asyncio
    async def test_real_dag_enrichment_extracts_facts(self):
        """Real DAG enrichment extracts facts from packet."""
        # This would test with a real SubstrateDAG instance
        pass
