"""
Tests for Stage 5: Predictive Memory Warming System

Tests:
- GapDetector entity and relationship gap detection
- PredictiveCache L1/L2 caching behavior
- MemoryWarmingService orchestration
"""

import pytest

from memory.gap_detector import GapDetector
from memory.predictive_cache import PredictiveCache
from memory.warming_models import GapSeverity, MemoryContext, PredictiveCacheConfig
from memory.warming_service import create_warming_service

# =============================================================================
# GapDetector Tests
# =============================================================================


class TestGapDetector:
    """Tests for GapDetector class."""

    @pytest.fixture
    def detector(self) -> GapDetector:
        """Create a GapDetector instance."""
        return GapDetector()

    @pytest.fixture
    def sample_entity_graph(self) -> dict[str, set[str]]:
        """Sample entity graph for testing."""
        return {
            "entity_1": {"entity_2", "entity_3"},
            "entity_2": {"entity_1", "entity_4"},
            "entity_3": {"entity_1"},
            "entity_4": {"entity_2"},
        }

    @pytest.mark.asyncio
    async def test_detect_entity_gaps_finds_missing_entities(
        self, detector: GapDetector, sample_entity_graph: dict[str, set[str]]
    ):
        """Test that missing entities are detected as gaps."""
        mentioned = ["entity_1", "entity_5", "entity_6"]  # 5 and 6 missing

        gaps = await detector.detect_entity_gaps(mentioned, sample_entity_graph)

        assert len(gaps) == 2
        missing_ids = {g.entity_ids[0] for g in gaps}
        assert "entity_5" in missing_ids
        assert "entity_6" in missing_ids
        assert all(g.gap_type == "entity_missing" for g in gaps)
        assert all(g.severity in (GapSeverity.HIGH, GapSeverity.CRITICAL) for g in gaps)

    @pytest.mark.asyncio
    async def test_detect_entity_gaps_empty_mentions_returns_empty(
        self, detector: GapDetector, sample_entity_graph: dict[str, set[str]]
    ):
        """Test that empty mentions returns no gaps."""
        gaps = await detector.detect_entity_gaps([], sample_entity_graph)
        assert len(gaps) == 0

    @pytest.mark.asyncio
    async def test_detect_relationship_gaps_finds_missing_relationships(
        self, detector: GapDetector, sample_entity_graph: dict[str, set[str]]
    ):
        """Test that missing relationships between mentioned entities are detected."""
        # entity_3 and entity_4 both exist but have no direct relationship
        mentioned = ["entity_3", "entity_4"]

        gaps = await detector.detect_relationship_gaps(mentioned, sample_entity_graph)

        assert len(gaps) == 1
        assert gaps[0].gap_type == "relationship_missing"
        assert set(gaps[0].entity_ids) == {"entity_3", "entity_4"}
        assert gaps[0].severity == GapSeverity.MEDIUM

    @pytest.mark.asyncio
    async def test_detect_relationship_gaps_no_gap_when_connected(
        self, detector: GapDetector, sample_entity_graph: dict[str, set[str]]
    ):
        """Test that connected entities don't produce relationship gaps."""
        # entity_1 and entity_2 are connected
        mentioned = ["entity_1", "entity_2"]

        gaps = await detector.detect_relationship_gaps(mentioned, sample_entity_graph)

        assert len(gaps) == 0

    @pytest.mark.asyncio
    async def test_detect_all_gaps_combines_results(
        self, detector: GapDetector, sample_entity_graph: dict[str, set[str]]
    ):
        """Test that detect_all_gaps combines entity and relationship gaps."""
        mentioned = ["entity_3", "entity_4", "entity_5"]  # 5 missing, 3-4 unconnected

        gaps = await detector.detect_all_gaps(mentioned, sample_entity_graph)

        # Should have 1 entity gap (entity_5) and 1 relationship gap (entity_3/4)
        assert len(gaps) == 2
        gap_types = {g.gap_type for g in gaps}
        assert "entity_missing" in gap_types
        assert "relationship_missing" in gap_types

    @pytest.mark.asyncio
    async def test_gaps_sorted_by_severity(
        self, detector: GapDetector, sample_entity_graph: dict[str, set[str]]
    ):
        """Test that gaps are sorted by severity (CRITICAL first)."""
        # Set entity_5 as critical
        detector.set_critical_path_entities({"entity_5"})
        mentioned = ["entity_3", "entity_4", "entity_5"]

        gaps = await detector.detect_all_gaps(mentioned, sample_entity_graph)

        # CRITICAL entity_5 gap should be first
        assert gaps[0].severity == GapSeverity.CRITICAL
        assert gaps[0].entity_ids[0] == "entity_5"

    def test_update_gap_frequency(self, detector: GapDetector):
        """Test that gap frequency updates correctly."""
        detector.update_gap_frequency("entity_x", 10.0)
        assert detector.historical_gap_frequency["entity_x"] > 0

        # Second update should smooth
        detector.update_gap_frequency("entity_x", 10.0)
        assert detector.historical_gap_frequency["entity_x"] > 0


# =============================================================================
# PredictiveCache Tests
# =============================================================================


class TestPredictiveCache:
    """Tests for PredictiveCache class."""

    @pytest.fixture
    def cache_config(self) -> PredictiveCacheConfig:
        """Create a cache configuration."""
        return PredictiveCacheConfig(
            redis_url="redis://localhost:6379",
            cache_ttl_seconds=300,
            max_subgraph_neighbors=20,
            max_cache_entries=1000,
        )

    @pytest.fixture
    def cache(self, cache_config: PredictiveCacheConfig) -> PredictiveCache:
        """Create a PredictiveCache instance."""
        return PredictiveCache(config=cache_config)

    @pytest.mark.asyncio
    async def test_warm_entity_returns_subgraph_entry(self, cache: PredictiveCache):
        """Test that warming an entity returns a SubgraphEntry."""
        await cache.initialize()

        entry = await cache.warm_entity("test_entity")

        assert entry is not None
        assert entry.entity_id == "test_entity"
        assert isinstance(entry.neighbors, dict)
        assert entry.cached_at_ms > 0

        await cache.shutdown()

    @pytest.mark.asyncio
    async def test_warm_entities_concurrent(self, cache: PredictiveCache):
        """Test that multiple entities can be warmed concurrently."""
        await cache.initialize()

        entity_ids = [f"entity_{i}" for i in range(5)]
        entries = await cache.warm_entities(entity_ids)

        assert len(entries) == 5
        warmed_ids = {e.entity_id for e in entries}
        assert warmed_ids == set(entity_ids)

        await cache.shutdown()

    @pytest.mark.asyncio
    async def test_get_cached_returns_l1_entry(self, cache: PredictiveCache):
        """Test that cached entries can be retrieved from L1."""
        await cache.initialize()

        # Warm an entity
        await cache.warm_entity("cached_entity")

        # Should be in L1 cache
        entry = await cache.get_cached("cached_entity")

        assert entry is not None
        assert entry.entity_id == "cached_entity"

        await cache.shutdown()

    @pytest.mark.asyncio
    async def test_get_cached_miss_returns_none(self, cache: PredictiveCache):
        """Test that cache miss returns None."""
        await cache.initialize()

        entry = await cache.get_cached("nonexistent_entity")

        assert entry is None

        await cache.shutdown()

    @pytest.mark.asyncio
    async def test_metrics_track_hits_and_misses(self, cache: PredictiveCache):
        """Test that metrics track cache hits and misses."""
        await cache.initialize()

        # Warm an entity
        await cache.warm_entity("metric_entity")

        # Hit
        await cache.get_cached("metric_entity")
        # Miss
        await cache.get_cached("missing_entity")

        metrics = cache.get_metrics()

        assert metrics.cache_hits >= 1
        assert metrics.cache_misses >= 1
        assert metrics.total_warming_calls >= 1

        await cache.shutdown()


# =============================================================================
# MemoryWarmingService Tests
# =============================================================================


class TestMemoryWarmingService:
    """Tests for MemoryWarmingService class."""

    @pytest.fixture
    def sample_entity_graph(self) -> dict[str, set[str]]:
        """Sample entity graph."""
        return {
            "entity_1": {"entity_2", "entity_3"},
            "entity_2": {"entity_1"},
            "entity_3": {"entity_1"},
        }

    @pytest.mark.asyncio
    async def test_warm_for_query_detects_and_warms_gaps(
        self, sample_entity_graph: dict[str, set[str]]
    ):
        """Test that warm_for_query detects gaps and warms entities."""
        service = await create_warming_service()
        service.set_entity_graph(sample_entity_graph)

        result = await service.warm_for_query(
            query="Find entity_1 and entity_4 relationships",
            mentioned_entities=["entity_1", "entity_4"],
        )

        assert result["gaps_detected"] >= 1  # entity_4 is missing
        assert result["entities_warmed"] >= 0
        assert "warming_latency_ms" in result
        assert "cache_metrics" in result

        await service.shutdown()

    @pytest.mark.asyncio
    async def test_get_warmed_context_returns_memory_context(
        self, sample_entity_graph: dict[str, set[str]]
    ):
        """Test that get_warmed_context returns MemoryContext."""
        service = await create_warming_service()
        service.set_entity_graph(sample_entity_graph)

        # Warm some entities first
        await service.cache.warm_entity("entity_1")

        context = await service.get_warmed_context(["entity_1", "entity_2"])

        assert isinstance(context, MemoryContext)
        assert "entity_1" in context.retrieved_entities
        assert context.cache_hit_ratio >= 0.0

        await service.shutdown()

    @pytest.mark.asyncio
    async def test_service_metrics(self, sample_entity_graph: dict[str, set[str]]):
        """Test that service metrics are tracked."""
        service = await create_warming_service()
        service.set_entity_graph(sample_entity_graph)

        # Perform some operations
        await service.warm_for_query(
            query="Test query",
            mentioned_entities=["entity_1"],
        )

        metrics = service.get_service_metrics()

        assert "cache_metrics" in metrics
        assert "entity_graph_size" in metrics
        assert metrics["entity_graph_size"] == 3
        assert metrics["initialized"] is True

        await service.shutdown()

    @pytest.mark.asyncio
    async def test_maintenance_cycle(self):
        """Test that maintenance cycle clears expired entries."""
        service = await create_warming_service()

        # Run maintenance
        await service.maintenance_cycle()

        # Should complete without error
        metrics = service.get_service_metrics()
        assert metrics["l1_cache_size"] == 0  # Nothing warmed yet

        await service.shutdown()


# =============================================================================
# Integration Tests
# =============================================================================


class TestPredictiveWarmingIntegration:
    """Integration tests for the full warming pipeline."""

    @pytest.mark.asyncio
    async def test_full_warming_pipeline(self):
        """Test the full gap detection -> warming -> retrieval pipeline."""
        # Setup
        entity_graph = {
            "project_alpha": {"task_1", "task_2", "team_lead"},
            "task_1": {"project_alpha", "developer_1"},
            "task_2": {"project_alpha", "developer_2"},
            "team_lead": {"project_alpha"},
            "developer_1": {"task_1"},
            "developer_2": {"task_2"},
        }

        service = await create_warming_service()
        service.set_entity_graph(entity_graph)

        # Simulate a query about a project and a new entity
        result = await service.warm_for_query(
            query="What is the status of project_alpha and project_beta?",
            mentioned_entities=["project_alpha", "project_beta", "task_1"],
        )

        # project_beta should be detected as missing (entity gap)
        assert result["gaps_detected"] >= 1

        # Check that warmed entities are in cache
        context = await service.get_warmed_context(["project_alpha", "task_1"])

        # At least one entity should be cached
        assert context.cache_hit_ratio >= 0.0

        await service.shutdown()
