"""
Tests for Query Caching and Vector Search Optimization

Tests both query caching functionality and vector search performance improvements.

Author: L9 Platform Team
Date: 2026-01-17
"""

import asyncio
import os

import pytest

from core.decorators import must_stay_async
from memory.query_cache import QueryCache, reset_cache
from memory.vector_search_config import VectorSearchConfig


class TestQueryCache:
    """Test query caching functionality."""

    def setup_method(self):
        """Reset cache before each test."""
        reset_cache()

    @pytest.mark.asyncio
    @must_stay_async("callers use await")
    async def test_ttl_cache_basic(self):
        """Test basic TTL caching."""
        cache = QueryCache()
        call_count = 0

        @cache.ttl(ttl=60)
        async def expensive_operation(value: int):
            nonlocal call_count
            call_count += 1
            await asyncio.sleep(0.01)  # Simulate slow operation
            return value * 2

        # First call - cache miss
        result1 = await expensive_operation(5)
        assert result1 == 10
        assert call_count == 1

        # Second call - cache hit
        result2 = await expensive_operation(5)
        assert result2 == 10
        assert call_count == 1  # Not called again

        # Different argument - cache miss
        result3 = await expensive_operation(10)
        assert result3 == 20
        assert call_count == 2

    @pytest.mark.asyncio
    @must_stay_async("callers use await")
    async def test_lru_cache_basic(self):
        """Test basic LRU caching.

        NOTE: QueryCache.lru(maxsize=N) does not create a per-decorator cache;
        it uses the shared lru_cache from __init__. Set lru_maxsize on the
        QueryCache constructor to control eviction behavior.
        """
        cache = QueryCache(lru_maxsize=2)
        call_count = 0

        @cache.lru()
        async def get_data(key: str):
            nonlocal call_count
            call_count += 1
            return f"data_{key}"

        # Fill cache
        await get_data("a")
        await get_data("b")
        assert call_count == 2

        # Cache hits
        await get_data("a")
        await get_data("b")
        assert call_count == 2

        # Evict "a" (LRU)
        await get_data("c")
        assert call_count == 3

        # "a" evicted, cache miss
        await get_data("a")
        assert call_count == 4

    @pytest.mark.asyncio
    @must_stay_async("callers use await")
    async def test_cache_stats(self):
        """Test cache statistics."""
        cache = QueryCache()

        @cache.ttl(ttl=60)
        async def operation(x: int):
            return x * 2

        # Generate some hits and misses
        await operation(1)  # miss
        await operation(1)  # hit
        await operation(2)  # miss
        await operation(2)  # hit

        stats = cache.get_stats()
        assert stats["ttl"]["hits"] == 2
        assert stats["ttl"]["misses"] == 2
        assert stats["ttl"]["hit_rate"] == 0.5

    @pytest.mark.asyncio
    @must_stay_async("callers use await")
    async def test_cache_invalidation(self):
        """Test cache invalidation."""
        cache = QueryCache()
        call_count = 0

        @cache.lru()
        async def get_user(user_id: str):
            nonlocal call_count
            call_count += 1
            return {"id": user_id, "name": "Test"}

        # Cache data
        await get_user("user_1")
        await get_user("user_1")
        assert call_count == 1  # Cached

        # Invalidate cache
        cache.invalidate(pattern="get_user")

        # Cache miss after invalidation
        await get_user("user_1")
        assert call_count == 2

    @pytest.mark.asyncio
    @must_stay_async("callers use await")
    async def test_cache_disabled(self):
        """Test caching can be disabled."""
        cache = QueryCache(enabled=False)
        call_count = 0

        @cache.ttl(ttl=60)
        async def operation(x: int):
            nonlocal call_count
            call_count += 1
            return x * 2

        # All calls execute (no caching)
        await operation(1)
        await operation(1)
        await operation(1)
        assert call_count == 3


class TestVectorSearchConfig:
    """Test vector search configuration."""

    def test_config_initialization(self):
        """Test configuration initialization."""
        config = VectorSearchConfig(ef_search=40)
        assert config.ef_search == 40
        assert not config.enable_seqscan

    def test_config_validation(self):
        """Test configuration validation."""
        with pytest.raises(ValueError):
            VectorSearchConfig(ef_search=0)  # Too low

        with pytest.raises(ValueError):
            VectorSearchConfig(ef_search=1001)  # Too high

    def test_config_presets(self):
        """Test configuration presets."""
        fast = VectorSearchConfig.fast()
        assert fast.ef_search == 20

        balanced = VectorSearchConfig.balanced()
        assert balanced.ef_search == 40

        high_recall = VectorSearchConfig.high_recall()
        assert high_recall.ef_search == 100


class TestCachingPerformance:
    """Test caching performance improvements."""

    @pytest.mark.asyncio
    @must_stay_async("callers use await")
    async def test_cache_speedup(self):
        """Test that caching provides significant speedup."""
        import time

        cache = QueryCache()

        @cache.ttl(ttl=60)
        async def slow_operation(x: int):
            await asyncio.sleep(0.1)  # 100ms operation
            return x * 2

        # First call (uncached)
        start = time.time()
        result1 = await slow_operation(5)
        uncached_time = time.time() - start

        # Second call (cached)
        start = time.time()
        result2 = await slow_operation(5)
        cached_time = time.time() - start

        assert result1 == result2
        assert cached_time < uncached_time / 10  # At least 10x faster

    @pytest.mark.asyncio
    @must_stay_async("callers use await")
    async def test_cache_memory_efficiency(self):
        """Test cache memory limits."""
        cache = QueryCache(lru_maxsize=10)

        @cache.lru(maxsize=10)
        async def get_item(i: int):
            return f"item_{i}"

        # Fill cache beyond limit
        for i in range(20):
            await get_item(i)

        stats = cache.get_stats()
        assert stats["lru"]["size"] <= 10  # Cache size limited


# Integration test (requires database)
@pytest.mark.integration
@pytest.mark.skipif(
    not os.getenv("TEST_DATABASE_URL"),
    reason="Requires TEST_DATABASE_URL (integration test — set to a reachable PostgreSQL URL)",
)
class TestVectorSearchIntegration:
    """Integration tests for vector search optimization."""

    @pytest.mark.asyncio
    @must_stay_async("callers use await")
    async def test_vector_search_with_optimization(self):
        """Test vector search with optimization applied."""
        # This test requires a real database connection
        pytest.skip("Requires database connection — placeholder for integration test")

    @pytest.mark.asyncio
    @must_stay_async("callers use await")
    async def test_vector_search_performance(self):
        """Test vector search performance improvement."""
        # This test requires a real database with data
        pytest.skip(
            "Requires database with test data — placeholder for integration test"
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
