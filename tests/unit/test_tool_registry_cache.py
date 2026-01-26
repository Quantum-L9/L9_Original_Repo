"""
Unit Tests for Tool Registry Cache
===================================

Tests tool registry caching layer.

Mutation Testing Target: 85%+ score
"""

from unittest.mock import Mock

from core.tools.registry_cache import (
    CacheConfig,
    CachedToolRegistry,
    CacheEntry,
    CacheMetrics,
    CacheStrategy,
    ToolRegistryCache,
)


class TestCacheConfig:
    """Test CacheConfig."""

    def test_cache_config_defaults(self):
        """Test default configuration."""
        config = CacheConfig()

        assert config.max_size == 1000
        assert config.strategy == CacheStrategy.LRU


class TestCacheEntry:
    """Test CacheEntry."""

    def test_cache_entry_creation(self):
        """Test entry creation."""
        entry = CacheEntry(key="test", value={"data": "test"})

        assert entry.key == "test"
        assert entry.access_count == 0

    def test_cache_entry_touch(self):
        """Test entry touch updates metadata."""
        entry = CacheEntry(key="test", value={})

        entry.touch()

        assert entry.access_count == 1


class TestCacheMetrics:
    """Test CacheMetrics."""

    def test_metrics_initialization(self):
        """Test metrics initialize to zero."""
        metrics = CacheMetrics()

        assert metrics.hits == 0
        assert metrics.misses == 0

    def test_get_hit_rate(self):
        """Test hit rate calculation."""
        metrics = CacheMetrics(hits=80, misses=20)

        hit_rate = metrics.get_hit_rate()

        assert hit_rate == 0.8


class TestToolRegistryCache:
    """Test ToolRegistryCache."""

    def test_cache_initialization(self):
        """Test cache initializes."""
        cache = ToolRegistryCache()

        assert cache is not None

    def test_cache_get_miss(self):
        """Test cache miss."""
        cache = ToolRegistryCache()

        result = cache.get("nonexistent")

        assert result is None

    def test_cache_set_and_get(self):
        """Test cache set and get."""
        cache = ToolRegistryCache()

        cache.set("tool1", {"name": "Tool 1"})
        result = cache.get("tool1")

        assert result is not None
        assert result["name"] == "Tool 1"

    def test_cache_invalidate(self):
        """Test cache invalidation."""
        cache = ToolRegistryCache()

        cache.set("tool1", {"name": "Tool 1"})
        invalidated = cache.invalidate("tool1")
        result = cache.get("tool1")

        assert invalidated is True
        assert result is None

    def test_cache_eviction_at_max_size(self):
        """Test cache evicts when full."""
        cache = ToolRegistryCache(CacheConfig(max_size=2))

        cache.set("tool1", {"name": "Tool 1"})
        cache.set("tool2", {"name": "Tool 2"})
        cache.set("tool3", {"name": "Tool 3"})  # Should evict tool1

        metrics = cache.get_metrics()
        assert metrics.evictions >= 1

    def test_cache_metrics(self):
        """Test cache metrics tracking."""
        cache = ToolRegistryCache()

        cache.set("tool1", {"name": "Tool 1"})
        cache.get("tool1")  # Hit
        cache.get("nonexistent")  # Miss

        metrics = cache.get_metrics()

        assert metrics.hits == 1
        assert metrics.misses == 1


class TestCachedToolRegistry:
    """Test CachedToolRegistry."""

    def test_cached_registry_initialization(self):
        """Test cached registry initializes."""
        mock_registry = Mock()
        mock_registry.list_tools = Mock(return_value=[])

        cached = CachedToolRegistry(
            mock_registry,
            CacheConfig(warm_on_startup=False),
        )

        assert cached is not None

    def test_get_tool_from_cache(self):
        """Test get_tool uses cache."""
        mock_registry = Mock()
        mock_registry.list_tools = Mock(return_value=[])
        mock_registry.get_tool = Mock(return_value={"tool_id": "tool1"})

        cached = CachedToolRegistry(
            mock_registry,
            CacheConfig(warm_on_startup=False),
        )

        # First call - cache miss
        result1 = cached.get_tool("tool1")
        # Second call - cache hit
        result2 = cached.get_tool("tool1")

        assert result1 == result2
        assert mock_registry.get_tool.call_count == 1  # Only called once


# =============================================================================
# Mutation Testing Targets
# =============================================================================


class TestMutationTargets:
    """Tests specifically designed to kill common mutations."""

    def test_hit_rate_calculation(self):
        """Kill mutation: hits / total -> misses / total."""
        metrics = CacheMetrics(hits=80, misses=20)

        hit_rate = metrics.get_hit_rate()

        assert hit_rate == 0.8
        assert hit_rate != 0.2  # Not miss rate

    def test_cache_eviction_removes_entry(self):
        """Kill mutation: eviction -> no-op."""
        cache = ToolRegistryCache(CacheConfig(max_size=1))

        cache.set("tool1", {"name": "Tool 1"})
        cache.set("tool2", {"name": "Tool 2"})  # Should evict tool1

        result = cache.get("tool1")
        assert result is None  # tool1 was evicted
