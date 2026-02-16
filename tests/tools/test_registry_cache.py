"""
Unit Tests – Tool Registry Cache
==================================

Tests for core/tools/registry_cache.py.

Covers:
- CacheEntry: expiration, touch()
- CacheMetrics: hit rate calculation
- ToolRegistryCache: get, set, invalidate, eviction strategies (LRU, LFU, TTL, FIFO)
- CachedToolRegistry: transparent caching wrapper, cache warming, invalidation on register/unregister
- Cache warm_cache with loader function

Version: 1.0.0
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from core.tools.registry_cache import (
    CacheConfig,
    CachedToolRegistry,
    CacheEntry,
    CacheMetrics,
    CacheStrategy,
    ToolRegistryCache,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def lru_cache() -> ToolRegistryCache:
    """LRU cache with max_size=3."""
    config = CacheConfig(max_size=3, strategy=CacheStrategy.LRU, enable_metrics=True)
    return ToolRegistryCache(config)


@pytest.fixture
def ttl_cache() -> ToolRegistryCache:
    """TTL cache with 1-second TTL for fast expiry tests."""
    config = CacheConfig(
        max_size=10,
        strategy=CacheStrategy.TTL,
        ttl_seconds=1,
        enable_metrics=True,
    )
    return ToolRegistryCache(config)


@pytest.fixture
def lfu_cache() -> ToolRegistryCache:
    """LFU cache with max_size=3."""
    config = CacheConfig(max_size=3, strategy=CacheStrategy.LFU, enable_metrics=True)
    return ToolRegistryCache(config)


@pytest.fixture
def fifo_cache() -> ToolRegistryCache:
    """FIFO cache with max_size=3."""
    config = CacheConfig(max_size=3, strategy=CacheStrategy.FIFO, enable_metrics=True)
    return ToolRegistryCache(config)


# ---------------------------------------------------------------------------
# CacheEntry
# ---------------------------------------------------------------------------


class TestCacheEntry:
    """Tests for CacheEntry dataclass."""

    def test_not_expired_without_ttl(self) -> None:
        entry = CacheEntry(key="k", value="v")
        assert entry.is_expired() is False

    def test_expired_with_past_ttl(self) -> None:
        entry = CacheEntry(
            key="k",
            value="v",
            ttl_expires_at=datetime.now(UTC) - timedelta(seconds=10),
        )
        assert entry.is_expired() is True

    def test_not_expired_with_future_ttl(self) -> None:
        entry = CacheEntry(
            key="k",
            value="v",
            ttl_expires_at=datetime.now(UTC) + timedelta(hours=1),
        )
        assert entry.is_expired() is False

    def test_touch_increments_access_count(self) -> None:
        entry = CacheEntry(key="k", value="v")
        assert entry.access_count == 0
        entry.touch()
        assert entry.access_count == 1
        entry.touch()
        assert entry.access_count == 2


# ---------------------------------------------------------------------------
# CacheMetrics
# ---------------------------------------------------------------------------


class TestCacheMetrics:
    """Tests for CacheMetrics calculations."""

    def test_hit_rate_zero_when_empty(self) -> None:
        m = CacheMetrics()
        assert m.get_hit_rate() == 0.0

    def test_hit_rate_calculation(self) -> None:
        m = CacheMetrics(hits=75, misses=25)
        assert m.get_hit_rate() == pytest.approx(0.75)

    def test_to_dict_keys(self) -> None:
        m = CacheMetrics(hits=10, misses=5, evictions=2, size=8, max_size=100)
        d = m.to_dict()
        assert set(d.keys()) == {
            "hits",
            "misses",
            "evictions",
            "size",
            "max_size",
            "hit_rate",
        }
        assert d["hit_rate"] == pytest.approx(0.6667, abs=0.001)


# ---------------------------------------------------------------------------
# ToolRegistryCache – Basic Operations
# ---------------------------------------------------------------------------


class TestCacheBasicOps:
    """Tests for get, set, invalidate basics."""

    def test_set_and_get(self, lru_cache: ToolRegistryCache) -> None:
        lru_cache.set("tool_a", {"name": "tool_a"})
        assert lru_cache.get("tool_a") == {"name": "tool_a"}

    def test_get_miss_returns_none(self, lru_cache: ToolRegistryCache) -> None:
        assert lru_cache.get("nonexistent") is None

    def test_set_updates_existing(self, lru_cache: ToolRegistryCache) -> None:
        lru_cache.set("tool_a", {"v": 1})
        lru_cache.set("tool_a", {"v": 2})
        assert lru_cache.get("tool_a") == {"v": 2}

    def test_invalidate_removes_entry(self, lru_cache: ToolRegistryCache) -> None:
        lru_cache.set("tool_a", "val")
        assert lru_cache.invalidate("tool_a") is True
        assert lru_cache.get("tool_a") is None

    def test_invalidate_nonexistent_returns_false(
        self, lru_cache: ToolRegistryCache
    ) -> None:
        assert lru_cache.invalidate("ghost") is False

    def test_invalidate_all(self, lru_cache: ToolRegistryCache) -> None:
        lru_cache.set("a", 1)
        lru_cache.set("b", 2)
        count = lru_cache.invalidate_all()
        assert count == 2
        assert lru_cache.get("a") is None
        assert lru_cache.get("b") is None


# ---------------------------------------------------------------------------
# ToolRegistryCache – Metrics
# ---------------------------------------------------------------------------


class TestCacheMetricsTracking:
    """Tests for hit/miss metric tracking."""

    def test_hit_increments(self, lru_cache: ToolRegistryCache) -> None:
        lru_cache.set("k", "v")
        lru_cache.get("k")
        lru_cache.get("k")
        m = lru_cache.get_metrics()
        assert m.hits == 2

    def test_miss_increments(self, lru_cache: ToolRegistryCache) -> None:
        lru_cache.get("missing1")
        lru_cache.get("missing2")
        m = lru_cache.get_metrics()
        assert m.misses == 2

    def test_metrics_size_tracks(self, lru_cache: ToolRegistryCache) -> None:
        lru_cache.set("a", 1)
        lru_cache.set("b", 2)
        m = lru_cache.get_metrics()
        assert m.size == 2


# ---------------------------------------------------------------------------
# ToolRegistryCache – LRU Eviction
# ---------------------------------------------------------------------------


class TestLRUEviction:
    """Tests for LRU eviction strategy."""

    def test_evicts_least_recently_used(self, lru_cache: ToolRegistryCache) -> None:
        lru_cache.set("a", 1)
        lru_cache.set("b", 2)
        lru_cache.set("c", 3)
        # Access 'a' to make it recently used
        lru_cache.get("a")
        # Insert 'd' – should evict 'b' (least recently used)
        lru_cache.set("d", 4)
        assert lru_cache.get("b") is None
        assert lru_cache.get("a") == 1
        assert lru_cache.get("d") == 4

    def test_eviction_metric_increments(self, lru_cache: ToolRegistryCache) -> None:
        lru_cache.set("a", 1)
        lru_cache.set("b", 2)
        lru_cache.set("c", 3)
        lru_cache.set("d", 4)  # Triggers eviction
        m = lru_cache.get_metrics()
        assert m.evictions == 1


# ---------------------------------------------------------------------------
# ToolRegistryCache – LFU Eviction
# ---------------------------------------------------------------------------


class TestLFUEviction:
    """Tests for LFU eviction strategy."""

    def test_evicts_least_frequently_used(self, lfu_cache: ToolRegistryCache) -> None:
        lfu_cache.set("a", 1)
        lfu_cache.set("b", 2)
        lfu_cache.set("c", 3)
        # Access 'a' and 'c' multiple times
        lfu_cache.get("a")
        lfu_cache.get("a")
        lfu_cache.get("c")
        # Insert 'd' – should evict 'b' (least frequently used: 0 additional accesses)
        lfu_cache.set("d", 4)
        assert lfu_cache.get("b") is None
        assert lfu_cache.get("a") == 1


# ---------------------------------------------------------------------------
# ToolRegistryCache – TTL Expiry
# ---------------------------------------------------------------------------


class TestTTLExpiry:
    """Tests for TTL-based expiration."""

    def test_expired_entry_returns_none(self) -> None:
        config = CacheConfig(max_size=10, strategy=CacheStrategy.TTL, ttl_seconds=0)
        cache = ToolRegistryCache(config)
        cache.set("k", "v")
        # Entry expires immediately (ttl=0 means expires_at ≈ now)
        import time

        time.sleep(0.01)
        assert cache.get("k") is None

    def test_non_expired_entry_returns_value(
        self, ttl_cache: ToolRegistryCache
    ) -> None:
        ttl_cache.set("k", "v")
        # ttl is 1 second, so reading immediately should work
        assert ttl_cache.get("k") == "v"


# ---------------------------------------------------------------------------
# ToolRegistryCache – FIFO Eviction
# ---------------------------------------------------------------------------


class TestFIFOEviction:
    """Tests for FIFO eviction strategy."""

    def test_evicts_first_inserted(self, fifo_cache: ToolRegistryCache) -> None:
        fifo_cache.set("first", 1)
        fifo_cache.set("second", 2)
        fifo_cache.set("third", 3)
        fifo_cache.set("fourth", 4)  # Triggers eviction
        assert fifo_cache.get("first") is None
        assert fifo_cache.get("second") == 2


# ---------------------------------------------------------------------------
# ToolRegistryCache – warm_cache
# ---------------------------------------------------------------------------


class TestCacheWarming:
    """Tests for cache warming via loader function."""

    def test_warm_populates_cache(self, lru_cache: ToolRegistryCache) -> None:
        def loader():
            return {"t1": {"name": "t1"}, "t2": {"name": "t2"}}

        count = lru_cache.warm_cache(loader)
        assert count == 2
        assert lru_cache.get("t1") == {"name": "t1"}

    def test_warm_returns_zero_on_error(self, lru_cache: ToolRegistryCache) -> None:
        def bad_loader():
            raise RuntimeError("DB unavailable")

        count = lru_cache.warm_cache(bad_loader)
        assert count == 0


# ---------------------------------------------------------------------------
# CachedToolRegistry Wrapper
# ---------------------------------------------------------------------------


class TestCachedToolRegistry:
    """Tests for the transparent caching wrapper."""

    def test_get_tool_caches_on_miss(self) -> None:
        mock_registry = MagicMock()
        mock_registry.list_tools.return_value = []
        mock_registry.get_tool.return_value = {"id": "search", "params": {}}

        cached = CachedToolRegistry(
            registry=mock_registry,
            cache_config=CacheConfig(warm_on_startup=False),
        )

        # First call: cache miss → fetches from registry
        result = cached.get_tool("search")
        assert result == {"id": "search", "params": {}}
        mock_registry.get_tool.assert_called_once_with("search")

        # Second call: cache hit → does NOT call registry again
        mock_registry.get_tool.reset_mock()
        result2 = cached.get_tool("search")
        assert result2 == {"id": "search", "params": {}}
        mock_registry.get_tool.assert_not_called()

    def test_get_tool_returns_none_for_unknown(self) -> None:
        mock_registry = MagicMock()
        mock_registry.list_tools.return_value = []
        mock_registry.get_tool.return_value = None

        cached = CachedToolRegistry(
            registry=mock_registry,
            cache_config=CacheConfig(warm_on_startup=False),
        )
        assert cached.get_tool("ghost") is None

    @pytest.mark.asyncio
    async def test_register_tool_invalidates_cache(self) -> None:
        mock_registry = MagicMock()
        mock_registry.list_tools.return_value = []

        cached = CachedToolRegistry(
            registry=mock_registry,
            cache_config=CacheConfig(warm_on_startup=False),
        )

        # Pre-populate cache
        cached._cache.set("old_tool", {"old": True})
        assert cached._cache.get("old_tool") is not None

        with patch(
            "core.tools.registry_cache.invalidate_all_tool_caches",
            new_callable=AsyncMock,
        ):
            await cached.register_tool("old_tool", {"new": True})

        # Cache entry for old_tool should be invalidated
        assert cached._cache.get("old_tool") is None

    @pytest.mark.asyncio
    async def test_unregister_tool_invalidates_cache(self) -> None:
        mock_registry = MagicMock()
        mock_registry.list_tools.return_value = []
        mock_registry.unregister_tool.return_value = True

        cached = CachedToolRegistry(
            registry=mock_registry,
            cache_config=CacheConfig(warm_on_startup=False),
        )

        cached._cache.set("doomed", {"x": 1})

        with patch(
            "core.tools.registry_cache.invalidate_all_tool_caches",
            new_callable=AsyncMock,
        ):
            result = await cached.unregister_tool("doomed")

        assert result is True
        assert cached._cache.get("doomed") is None

    def test_invalidate_cache_specific_key(self) -> None:
        mock_registry = MagicMock()
        mock_registry.list_tools.return_value = []

        cached = CachedToolRegistry(
            registry=mock_registry,
            cache_config=CacheConfig(warm_on_startup=False),
        )
        cached._cache.set("a", 1)
        cached._cache.set("b", 2)

        count = cached.invalidate_cache(tool_id="a")
        assert count == 1
        assert cached._cache.get("a") is None
        assert cached._cache.get("b") == 2

    def test_invalidate_cache_all(self) -> None:
        mock_registry = MagicMock()
        mock_registry.list_tools.return_value = []

        cached = CachedToolRegistry(
            registry=mock_registry,
            cache_config=CacheConfig(warm_on_startup=False),
        )
        cached._cache.set("a", 1)
        cached._cache.set("b", 2)

        count = cached.invalidate_cache(tool_id=None)
        assert count == 2

    def test_get_cache_metrics(self) -> None:
        mock_registry = MagicMock()
        mock_registry.list_tools.return_value = []

        cached = CachedToolRegistry(
            registry=mock_registry,
            cache_config=CacheConfig(warm_on_startup=False),
        )
        cached._cache.set("k", "v")
        cached._cache.get("k")
        cached._cache.get("miss")

        metrics = cached.get_cache_metrics()
        assert "hits" in metrics
        assert "misses" in metrics
        assert "hit_rate" in metrics
