# ADR 0050: Tool Registry Cache

## Status

Proposed

## Pattern

Add an **in-memory TTL cache** for tool definitions in the ToolRegistry. Cache hits avoid database queries, providing ~10x faster tool lookups during plan execution.

## Context

L9's ToolRegistry queries the database on every `get_tool()` call. During plan execution with many tool calls, this creates significant overhead. A TTL-based cache:

- Reduces database load
- Speeds up tool lookups
- Provides cache metrics for monitoring

**Source:** Perplexity Refactor Analysis (2026-01-20)

## Files

### New Files to Create

- `core/tools/registry_cache.py` - TTL cache implementation

### Files to Modify

- `core/tools/registry_adapter.py` - Use cache in `get_tool()`
- `api/routes/tools.py` - Add cache invalidation endpoint

## Import Block

```python
from core.tools.registry_cache import (
    ToolRegistryCache,
    get_tool_cache,
    CacheEntry,
)
```

## Minimal Implementation

```python
# core/tools/registry_cache.py
"""TTL-based cache for tool definitions."""

import time
import threading
import logging
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class CacheEntry:
    """Single cache entry with TTL."""

    def __init__(self, value: Any, ttl_seconds: float):
        self.value = value
        self.created_at = time.time()
        self.ttl_seconds = ttl_seconds

    def is_expired(self) -> bool:
        """Check if entry has expired."""
        return (time.time() - self.created_at) > self.ttl_seconds


class ToolRegistryCache:
    """
    In-memory TTL cache for tool definitions.

    Features:
    - Thread-safe operations
    - Configurable TTL (default 5 minutes)
    - Manual and automatic invalidation
    - Cache metrics (hit rate, evictions)

    Pattern: Frontend cache with DB fallback
    """

    def __init__(self, ttl_seconds: float = 300):
        """
        Initialize cache.

        Args:
            ttl_seconds: Cache TTL (default 5 minutes)
        """
        self._cache: Dict[str, CacheEntry] = {}
        self._ttl_seconds = ttl_seconds
        self._lock = threading.RLock()

        # Metrics
        self._hits = 0
        self._misses = 0
        self._evictions = 0

    def get(self, tool_name: str) -> Optional[Any]:
        """
        Get cached tool definition.

        Returns:
            Tool definition or None if miss/expired
        """
        with self._lock:
            if tool_name not in self._cache:
                self._misses += 1
                logger.debug(f"Cache miss: {tool_name}")
                return None

            entry = self._cache[tool_name]

            if entry.is_expired():
                del self._cache[tool_name]
                self._evictions += 1
                self._misses += 1
                logger.debug(f"Cache expired: {tool_name}")
                return None

            self._hits += 1
            logger.debug(f"Cache hit: {tool_name}")
            return entry.value

    def put(self, tool_name: str, tool_definition: Any) -> None:
        """
        Store tool definition in cache.

        Args:
            tool_name: Cache key
            tool_definition: Tool definition to cache
        """
        with self._lock:
            self._cache[tool_name] = CacheEntry(
                value=tool_definition,
                ttl_seconds=self._ttl_seconds,
            )
            logger.debug(f"Cached: {tool_name} (ttl={self._ttl_seconds}s)")

    def invalidate(self, tool_name: Optional[str] = None) -> int:
        """
        Invalidate cache entry or entire cache.

        Args:
            tool_name: Specific tool to invalidate, or None for all

        Returns:
            Number of entries invalidated
        """
        with self._lock:
            if tool_name is None:
                count = len(self._cache)
                self._cache.clear()
                logger.info(f"Cache cleared: {count} entries")
                return count

            if tool_name in self._cache:
                del self._cache[tool_name]
                logger.info(f"Cache invalidated: {tool_name}")
                return 1

            return 0

    def get_metrics(self) -> Dict[str, Any]:
        """
        Get cache metrics.

        Returns:
            Dict with hit_rate, hits, misses, evictions, cache_size
        """
        with self._lock:
            total = self._hits + self._misses
            hit_rate = (self._hits / total * 100) if total > 0 else 0.0

            return {
                "hit_rate_percent": round(hit_rate, 2),
                "hits": self._hits,
                "misses": self._misses,
                "evictions": self._evictions,
                "cache_size": len(self._cache),
                "ttl_seconds": self._ttl_seconds,
            }

    def cleanup_expired(self) -> int:
        """
        Remove all expired entries.

        Returns:
            Number of entries removed
        """
        with self._lock:
            expired = [
                name for name, entry in self._cache.items()
                if entry.is_expired()
            ]

            for name in expired:
                del self._cache[name]

            self._evictions += len(expired)

            if expired:
                logger.info(f"Cleaned up {len(expired)} expired entries")

            return len(expired)


# Global singleton
_tool_cache: Optional[ToolRegistryCache] = None


def get_tool_cache(ttl_seconds: float = 300) -> ToolRegistryCache:
    """Get or create global tool cache."""
    global _tool_cache
    if _tool_cache is None:
        _tool_cache = ToolRegistryCache(ttl_seconds=ttl_seconds)
    return _tool_cache
```

## Usage Example

```python
# core/tools/registry_adapter.py — using cache

from core.tools.registry_cache import get_tool_cache


class ToolRegistry:
    """Tool registry with caching."""

    def __init__(self, db_client, cache_ttl: float = 300):
        self._db = db_client
        self._cache = get_tool_cache(ttl_seconds=cache_ttl)

    async def get_tool(self, tool_name: str):
        """Get tool definition with cache."""

        # 1. Check cache first
        cached = self._cache.get(tool_name)
        if cached is not None:
            return cached

        # 2. Cache miss — query database
        tool = await self._db.fetch_one(
            "SELECT * FROM tools WHERE name = $1",
            tool_name,
        )

        # 3. Populate cache
        if tool:
            self._cache.put(tool_name, tool)

        return tool


# api/routes/tools.py — cache management endpoints

from fastapi import APIRouter
from core.tools.registry_cache import get_tool_cache

router = APIRouter(prefix="/tools/cache", tags=["tools"])


@router.get("/metrics")
async def get_cache_metrics():
    """Get tool cache metrics."""
    cache = get_tool_cache()
    return cache.get_metrics()


@router.post("/invalidate")
async def invalidate_cache(tool_name: str = None):
    """Invalidate tool cache."""
    cache = get_tool_cache()
    count = cache.invalidate(tool_name)
    return {"invalidated": count, "tool_name": tool_name}


@router.post("/cleanup")
async def cleanup_expired():
    """Remove expired cache entries."""
    cache = get_tool_cache()
    count = cache.cleanup_expired()
    return {"cleaned_up": count}
```

## Anti-Pattern Example

```python
# ❌ WRONG — No caching, DB hit every time
class ToolRegistry:
    async def get_tool(self, tool_name: str):
        # Always queries database
        return await self._db.fetch_one(
            "SELECT * FROM tools WHERE name = $1",
            tool_name,
        )

# During plan execution with 50 tool calls:
# 50 database queries = slow!

# ✅ CORRECT — Cache with TTL
class ToolRegistry:
    async def get_tool(self, tool_name: str):
        cached = self._cache.get(tool_name)
        if cached:
            return cached  # Fast!

        tool = await self._db.fetch_one(...)
        self._cache.put(tool_name, tool)
        return tool

# During plan execution with 50 tool calls:
# 1 DB query + 49 cache hits = fast!
```

## Rules

1. Cache MUST be thread-safe (use locking)
2. TTL MUST be configurable (default 5 minutes)
3. Cache MUST support manual invalidation
4. Metrics MUST be exposed (hit rate, evictions)
5. Cache MUST NOT store None values (use absence to indicate miss)
6. Global singleton MUST be used for cache consistency
7. Invalidation endpoint MUST exist for admin operations

## AI Guidance

**DO:**

- Use cache for all `get_tool()` calls
- Invalidate cache when tools are updated
- Monitor hit rate (target > 80%)
- Use global singleton for cache

**DO NOT:**

- Cache indefinitely (always use TTL)
- Skip cache for "important" lookups
- Create multiple cache instances
- Forget to invalidate on tool updates

## Related ADRs

- [ADR-0027: LRU Cache Pattern](./0027-lru-cache-pattern.md) - Related caching pattern
- [ADR-0017: Tool Definition Schema](./0017-tool-definition-schema.md) - What's being cached
- [ADR-0022: Registry Pattern](./0022-registry-pattern.md) - Registry caching
