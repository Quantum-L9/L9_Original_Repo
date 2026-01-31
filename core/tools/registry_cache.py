"""
L9 Core Tools - Registry Caching Layer
=======================================

High-performance caching layer for tool registry lookups.

Implements Phase 0 Plan 8: Tool Registry Caching Layer

Key responsibilities:
- Cache tool definitions for fast lookup
- Invalidate cache on tool updates
- Support cache warming strategies
- Provide cache hit/miss metrics
- LRU eviction for memory management

This module does NOT:
- Replace tool_registry.py (augments it with caching)
- Store tool implementations (only metadata)
- Handle tool execution (that's AgentExecutorService)

Version: 1.0.0
GMP: refactor-phase0-plan8
"""

from __future__ import annotations

# ============================================================================
# DORA HEADER META
# ============================================================================
__dora_meta__ = {
    "component_id": "TOOL-REG-CACHE-001",
    "component_name": "ToolRegistryCache",
    "module_version": "1.0.0",
    "created_at": "2026-01-21T00:00:00Z",
    "created_by": "L9_Refactoring_Phase0",
    "layer": "foundation",
    "domain": "tools",
    "type": "service",
    "status": "active",
    "governance_level": "standard",
    "compliance_required": False,
    "audit_trail": False,
    "purpose": "High-performance caching layer for tool registry lookups",
    "dependencies": [
        "core.tools.tool_registry",
    ],
}
# ============================================================================

from collections import OrderedDict
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from enum import Enum
from typing import Any

import structlog

logger = structlog.get_logger(__name__)


# =============================================================================
# Cache Configuration
# =============================================================================


class CacheStrategy(str, Enum):
    """Cache eviction strategies."""

    LRU = "lru"  # Least Recently Used
    LFU = "lfu"  # Least Frequently Used
    TTL = "ttl"  # Time To Live
    FIFO = "fifo"  # First In First Out


@dataclass
class CacheConfig:
    """
    Configuration for tool registry cache.

    Attributes:
        max_size: Maximum number of cached entries
        strategy: Cache eviction strategy
        ttl_seconds: Time-to-live for cached entries (TTL strategy)
        enable_metrics: Enable cache hit/miss metrics
        warm_on_startup: Warm cache on initialization
    """

    max_size: int = 1000
    strategy: CacheStrategy = CacheStrategy.LRU
    ttl_seconds: int = 3600  # 1 hour
    enable_metrics: bool = True
    warm_on_startup: bool = True


# =============================================================================
# Cache Entry
# =============================================================================


@dataclass
class CacheEntry:
    """
    Cached tool registry entry.

    Attributes:
        key: Cache key
        value: Cached value (tool definition)
        created_at: Entry creation timestamp
        last_accessed_at: Last access timestamp
        access_count: Number of accesses
        ttl_expires_at: TTL expiration timestamp
    """

    key: str
    value: Any
    created_at: datetime = field(default_factory=datetime.utcnow)
    last_accessed_at: datetime = field(default_factory=datetime.utcnow)
    access_count: int = 0
    ttl_expires_at: datetime | None = None

    def is_expired(self) -> bool:
        """Check if entry is expired (TTL)."""
        if self.ttl_expires_at is None:
            return False
        return datetime.now(timezone.utc) > self.ttl_expires_at

    def touch(self) -> None:
        """Update access metadata."""
        self.last_accessed_at = datetime.now(timezone.utc)
        self.access_count += 1


# =============================================================================
# Cache Metrics
# =============================================================================


@dataclass
class CacheMetrics:
    """
    Cache performance metrics.

    Attributes:
        hits: Number of cache hits
        misses: Number of cache misses
        evictions: Number of evictions
        size: Current cache size
        max_size: Maximum cache size
    """

    hits: int = 0
    misses: int = 0
    evictions: int = 0
    size: int = 0
    max_size: int = 0

    def get_hit_rate(self) -> float:
        """Calculate cache hit rate."""
        total = self.hits + self.misses
        if total == 0:
            return 0.0
        return self.hits / total

    def to_dict(self) -> dict[str, Any]:
        """Export as dict."""
        return {
            "hits": self.hits,
            "misses": self.misses,
            "evictions": self.evictions,
            "size": self.size,
            "max_size": self.max_size,
            "hit_rate": round(self.get_hit_rate(), 4),
        }


# =============================================================================
# Tool Registry Cache
# =============================================================================


class ToolRegistryCache:
    """
    High-performance caching layer for tool registry.

    Provides fast lookup of tool definitions with configurable
    eviction strategies and metrics.
    """

    def __init__(self, config: CacheConfig | None = None):
        """
        Initialize tool registry cache.

        Args:
            config: Cache configuration
        """
        self.config = config or CacheConfig()

        # Cache storage (OrderedDict for LRU)
        self._cache: OrderedDict[str, CacheEntry] = OrderedDict()

        # Metrics
        self._metrics = CacheMetrics(max_size=self.config.max_size)

        logger.info(
            "ToolRegistryCache initialized",
            max_size=self.config.max_size,
            strategy=self.config.strategy.value,
            ttl_seconds=self.config.ttl_seconds,
        )

    def get(self, key: str) -> Any | None:
        """
        Get value from cache.

        Args:
            key: Cache key

        Returns:
            Cached value or None if not found/expired
        """
        entry = self._cache.get(key)

        if entry is None:
            # Cache miss
            if self.config.enable_metrics:
                self._metrics.misses += 1

            logger.debug("tool_registry_cache.miss", key=key)
            return None

        # Check TTL expiration
        if entry.is_expired():
            # Remove expired entry
            del self._cache[key]
            self._metrics.size -= 1

            if self.config.enable_metrics:
                self._metrics.misses += 1

            logger.debug("tool_registry_cache.expired", key=key)
            return None

        # Cache hit
        entry.touch()

        # Move to end for LRU
        if self.config.strategy == CacheStrategy.LRU:
            self._cache.move_to_end(key)

        if self.config.enable_metrics:
            self._metrics.hits += 1

        logger.debug(
            "tool_registry_cache.hit",
            key=key,
            access_count=entry.access_count,
        )

        return entry.value

    def set(self, key: str, value: Any) -> None:
        """
        Set value in cache.

        Args:
            key: Cache key
            value: Value to cache
        """
        # Check if key already exists
        if key in self._cache:
            # Update existing entry
            entry = self._cache[key]
            entry.value = value
            entry.touch()

            # Move to end for LRU
            if self.config.strategy == CacheStrategy.LRU:
                self._cache.move_to_end(key)

            logger.debug("tool_registry_cache.updated", key=key)
            return

        # Check if cache is full
        if len(self._cache) >= self.config.max_size:
            self._evict()

        # Create new entry
        ttl_expires_at = None
        if self.config.strategy == CacheStrategy.TTL:
            ttl_expires_at = datetime.now(timezone.utc) + timedelta(
                seconds=self.config.ttl_seconds
            )

        entry = CacheEntry(
            key=key,
            value=value,
            ttl_expires_at=ttl_expires_at,
        )

        self._cache[key] = entry
        self._metrics.size += 1

        logger.debug("tool_registry_cache.set", key=key)

    def invalidate(self, key: str) -> bool:
        """
        Invalidate cache entry.

        Args:
            key: Cache key to invalidate

        Returns:
            True if entry was found and removed
        """
        if key in self._cache:
            del self._cache[key]
            self._metrics.size -= 1

            logger.debug("tool_registry_cache.invalidated", key=key)
            return True

        return False

    def invalidate_all(self) -> int:
        """
        Invalidate all cache entries.

        Returns:
            Number of entries invalidated
        """
        count = len(self._cache)
        self._cache.clear()
        self._metrics.size = 0

        logger.info("tool_registry_cache.invalidated_all", count=count)
        return count

    def _evict(self) -> None:
        """Evict entry based on configured strategy."""
        if not self._cache:
            return

        if self.config.strategy == CacheStrategy.LRU:
            # Remove least recently used (first item)
            key, _ = self._cache.popitem(last=False)

        elif self.config.strategy == CacheStrategy.LFU:
            # Remove least frequently used
            key = min(self._cache.keys(), key=lambda k: self._cache[k].access_count)
            del self._cache[key]

        elif self.config.strategy == CacheStrategy.TTL:
            # Remove expired entries first, then oldest
            expired_keys = [k for k, entry in self._cache.items() if entry.is_expired()]

            if expired_keys:
                key = expired_keys[0]
                del self._cache[key]
            else:
                # Remove oldest entry
                key, _ = self._cache.popitem(last=False)

        elif self.config.strategy == CacheStrategy.FIFO:
            # Remove first in (first item)
            key, _ = self._cache.popitem(last=False)

        else:
            # Default to LRU
            key, _ = self._cache.popitem(last=False)

        self._metrics.size -= 1
        self._metrics.evictions += 1

        logger.debug(
            "tool_registry_cache.evicted",
            key=key,
            strategy=self.config.strategy.value,
        )

    def get_metrics(self) -> CacheMetrics:
        """
        Get cache metrics.

        Returns:
            Current cache metrics
        """
        self._metrics.size = len(self._cache)
        return self._metrics

    def warm_cache(self, loader: Callable[[], dict[str, Any]]) -> int:
        """
        Warm cache with initial data.

        Args:
            loader: Function that returns dict of {key: value} to cache

        Returns:
            Number of entries loaded
        """
        logger.info("tool_registry_cache.warming_started")

        try:
            data = loader()

            for key, value in data.items():
                self.set(key, value)

            logger.info(
                "tool_registry_cache.warming_complete",
                entries_loaded=len(data),
            )

            return len(data)

        except Exception as e:
            logger.error(
                "tool_registry_cache.warming_failed",
                error=str(e),
            )
            return 0


# =============================================================================
# Cached Tool Registry Wrapper
# =============================================================================


class CachedToolRegistry:
    """
    Wrapper for tool registry with caching.

    Provides transparent caching layer over tool registry.
    """

    def __init__(
        self,
        registry: Any,  # ToolRegistry instance
        cache_config: CacheConfig | None = None,
    ):
        """
        Initialize cached tool registry.

        Args:
            registry: Underlying tool registry
            cache_config: Cache configuration
        """
        self._registry = registry
        self._cache = ToolRegistryCache(cache_config)

        # Warm cache if configured
        if self._cache.config.warm_on_startup:
            self._warm_cache()

        logger.info("CachedToolRegistry initialized")

    def get_tool(self, tool_id: str) -> dict[str, Any] | None:
        """
        Get tool definition with caching.

        Args:
            tool_id: Tool identifier

        Returns:
            Tool definition or None if not found
        """
        # Check cache first
        cached_tool = self._cache.get(tool_id)
        if cached_tool is not None:
            return cached_tool

        # Cache miss - fetch from registry
        tool = self._registry.get_tool(tool_id)

        if tool is not None:
            # Cache the result
            self._cache.set(tool_id, tool)

        return tool

    def list_tools(self) -> list[dict[str, Any]]:
        """
        List all tools.

        Note: This bypasses cache and always fetches from registry.

        Returns:
            List of tool definitions
        """
        return self._registry.list_tools()

    def register_tool(self, tool_id: str, tool_def: dict[str, Any]) -> None:
        """
        Register tool and invalidate cache.

        Args:
            tool_id: Tool identifier
            tool_def: Tool definition
        """
        self._registry.register_tool(tool_id, tool_def)

        # Invalidate cache entry
        self._cache.invalidate(tool_id)

        logger.debug("cached_tool_registry.registered", tool_id=tool_id)

    def unregister_tool(self, tool_id: str) -> bool:
        """
        Unregister tool and invalidate cache.

        Args:
            tool_id: Tool identifier

        Returns:
            True if tool was found and removed
        """
        result = self._registry.unregister_tool(tool_id)

        # Invalidate cache entry
        self._cache.invalidate(tool_id)

        logger.debug("cached_tool_registry.unregistered", tool_id=tool_id)

        return result

    def invalidate_cache(self, tool_id: str | None = None) -> int:
        """
        Invalidate cache entries.

        Args:
            tool_id: Optional specific tool to invalidate (None = all)

        Returns:
            Number of entries invalidated
        """
        if tool_id is not None:
            return 1 if self._cache.invalidate(tool_id) else 0
        return self._cache.invalidate_all()

    def get_cache_metrics(self) -> dict[str, Any]:
        """
        Get cache metrics.

        Returns:
            Cache metrics dict
        """
        return self._cache.get_metrics().to_dict()

    def _warm_cache(self) -> None:
        """Warm cache with all tools from registry."""

        def loader() -> dict[str, Any]:
            tools = self._registry.list_tools()
            return {tool["tool_id"]: tool for tool in tools}

        self._cache.warm_cache(loader)


# =============================================================================
# Module Exports
# =============================================================================

__all__ = [
    "CacheConfig",
    "CacheEntry",
    "CacheMetrics",
    "CacheStrategy",
    "CachedToolRegistry",
    "ToolRegistryCache",
]

# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "COR-FOUN-028",
    "governance_level": "critical",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": [
        "caching",
        "data-models",
        "dataclass",
        "debugging",
        "foundation",
        "logging",
        "metrics",
    ],
    "keywords": [
        "all",
        "cache",
        "cached",
        "caching",
        "entry",
        "expired",
        "hit",
        "invalidate",
    ],
    "business_value": "Implements Phase 0 Plan 8: Tool Registry Caching Layer",
    "last_modified": "2026-01-24T13:02:52Z",
    "modified_by": "L9_Codegen_Engine",
    "change_summary": "Initial generation with DORA compliance",
}
# ============================================================================
# L9 DORA BLOCK - AUTO-UPDATED - DO NOT EDIT
# Runtime execution trace - updated automatically on every execution
# ============================================================================
__l9_trace__ = {
    "trace_id": "",
    "task": "",
    "timestamp": "",
    "patterns_used": [],
    "graph": {"nodes": [], "edges": []},
    "inputs": {},
    "outputs": {},
    "metrics": {"confidence": "", "errors_detected": [], "stability_score": ""},
}
# ============================================================================
# END L9 DORA BLOCK
# ============================================================================
