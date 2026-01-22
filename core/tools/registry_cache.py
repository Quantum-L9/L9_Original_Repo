"""
L9 Core Tools - Tool Registry Cache with Adaptive TTL
======================================================

TTL-based cache for tool definitions with adaptive TTL based on access frequency.

**Features**:
- Thread-safe operations
- Adaptive TTL (hot/warm/cold tools)
- Manual and automatic invalidation
- Cache metrics (hit rate, evictions, access counts)

**Adaptive TTL Logic**:
- HOT tools (>100 accesses) → 1 hour TTL
- WARM tools (>10 accesses) → 10 min TTL
- COLD tools (<10 accesses) → 5 min TTL (default)

**Pattern**: Frontend cache with DB fallback

Version: 1.0.0 (Base + Adaptive TTL)
"""

from __future__ import annotations

# ============================================================================
__dora_meta__ = {
    "component_name": "Tool Registry Cache",
    "module_version": "1.0.0 (Base + Adaptive TTL)",
    "created_by": "Manus AI",
    "created_at": "2026-01-21T18:30:00Z",
    "updated_at": "2026-01-21T18:30:00Z",
    "layer": "foundation",
    "domain": "tool_registry",
    "module_name": "registry_cache",
    "type": "cache",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": [],
        "memory_layers": [],
        "imported_by": ["core.tools.registry_adapter"],
    },
}
# ============================================================================

import time
import threading
import logging
from typing import Any, Dict, Optional
from enum import Enum

logger = logging.getLogger(__name__)


class CacheTier(str, Enum):
    """Cache tier based on access frequency"""
    HOT = "hot"      # >100 accesses → 1 hour TTL
    WARM = "warm"    # >10 accesses → 10 min TTL
    COLD = "cold"    # <10 accesses → 5 min TTL (default)


class CacheEntry:
    """
    Single cache entry with TTL.
    
    Attributes:
        value: Cached tool definition
        created_at: Timestamp when entry was created
        ttl_seconds: Time-to-live in seconds
    """
    
    def __init__(self, value: Any, ttl_seconds: float):
        self.value = value
        self.created_at = time.time()
        self.ttl_seconds = ttl_seconds
    
    def is_expired(self) -> bool:
        """Check if entry has expired."""
        return (time.time() - self.created_at) > self.ttl_seconds


class ToolRegistryCache:
    """
    In-memory TTL cache for tool definitions with adaptive TTL.
    
    Features:
    - Thread-safe operations
    - Adaptive TTL based on access frequency
    - Manual and automatic invalidation
    - Cache metrics (hit rate, evictions, access counts)
    
    Adaptive TTL Logic:
    - HOT tools (>100 accesses) → 1 hour TTL
    - WARM tools (>10 accesses) → 10 min TTL
    - COLD tools (<10 accesses) → 5 min TTL (default)
    
    Pattern: Frontend cache with DB fallback
    
    Usage:
        cache = ToolRegistryCache()
        
        # Get with adaptive TTL
        tool = cache.get("memory_search")
        if tool is None:
            tool = await db.fetch_tool("memory_search")
            cache.put("memory_search", tool)
        
        # Check metrics
        metrics = cache.get_metrics()
        print(f"Hit rate: {metrics['hit_rate_percent']}%")
    """
    
    def __init__(
        self,
        default_ttl_seconds: float = 300,
        enable_adaptive_ttl: bool = True
    ):
        """
        Initialize cache.
        
        Args:
            default_ttl_seconds: Default cache TTL (5 minutes)
            enable_adaptive_ttl: Enable adaptive TTL based on access frequency
        """
        self._cache: Dict[str, CacheEntry] = {}
        self._default_ttl_seconds = default_ttl_seconds
        self._enable_adaptive_ttl = enable_adaptive_ttl
        self._lock = threading.RLock()
        
        # Access tracking for adaptive TTL
        self._access_counts: Dict[str, int] = {}
        
        # TTL map for adaptive tiers
        self._ttl_map = {
            CacheTier.HOT: 3600,    # 1 hour
            CacheTier.WARM: 600,    # 10 minutes
            CacheTier.COLD: 300     # 5 minutes (default)
        }
        
        # Metrics
        self._hits = 0
        self._misses = 0
        self._evictions = 0
        
        logger.info(
            "ToolRegistryCache initialized",
            default_ttl=default_ttl_seconds,
            adaptive_ttl=enable_adaptive_ttl
        )
    
    def _get_tier(self, tool_name: str) -> CacheTier:
        """
        Determine cache tier based on access count.
        
        Args:
            tool_name: Tool name
        
        Returns:
            CacheTier (HOT, WARM, or COLD)
        """
        count = self._access_counts.get(tool_name, 0)
        
        if count > 100:
            return CacheTier.HOT
        elif count > 10:
            return CacheTier.WARM
        else:
            return CacheTier.COLD
    
    def _get_ttl(self, tool_name: str) -> float:
        """
        Get TTL for tool based on access frequency.
        
        Args:
            tool_name: Tool name
        
        Returns:
            TTL in seconds
        """
        if not self._enable_adaptive_ttl:
            return self._default_ttl_seconds
        
        tier = self._get_tier(tool_name)
        return self._ttl_map[tier]
    
    def _record_access(self, tool_name: str) -> None:
        """
        Record tool access for adaptive TTL.
        
        Args:
            tool_name: Tool name
        """
        if not self._enable_adaptive_ttl:
            return
        
        self._access_counts[tool_name] = self._access_counts.get(tool_name, 0) + 1
    
    def get(self, tool_name: str) -> Optional[Any]:
        """
        Get cached tool definition.
        
        Args:
            tool_name: Tool name
        
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
            
            # Record access for adaptive TTL
            self._record_access(tool_name)
            
            self._hits += 1
            
            # Log tier info if adaptive TTL enabled
            if self._enable_adaptive_ttl:
                tier = self._get_tier(tool_name)
                access_count = self._access_counts.get(tool_name, 0)
                logger.debug(
                    f"Cache hit: {tool_name} (tier={tier.value}, "
                    f"accesses={access_count}, ttl={entry.ttl_seconds}s)"
                )
            else:
                logger.debug(f"Cache hit: {tool_name}")
            
            return entry.value
    
    def put(self, tool_name: str, tool_definition: Any) -> None:
        """
        Store tool definition in cache with adaptive TTL.
        
        Args:
            tool_name: Cache key
            tool_definition: Tool definition to cache
        """
        with self._lock:
            # Get adaptive TTL
            ttl = self._get_ttl(tool_name)
            
            self._cache[tool_name] = CacheEntry(
                value=tool_definition,
                ttl_seconds=ttl,
            )
            
            # Log tier info if adaptive TTL enabled
            if self._enable_adaptive_ttl:
                tier = self._get_tier(tool_name)
                access_count = self._access_counts.get(tool_name, 0)
                logger.debug(
                    f"Cached: {tool_name} (tier={tier.value}, "
                    f"accesses={access_count}, ttl={ttl}s)"
                )
            else:
                logger.debug(f"Cached: {tool_name} (ttl={ttl}s)")
    
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
                
                # Reset access counts if adaptive TTL enabled
                if self._enable_adaptive_ttl:
                    self._access_counts.clear()
                
                logger.info(f"Cache cleared: {count} entries")
                return count
            
            if tool_name in self._cache:
                del self._cache[tool_name]
                
                # Reset access count if adaptive TTL enabled
                if self._enable_adaptive_ttl and tool_name in self._access_counts:
                    del self._access_counts[tool_name]
                
                logger.info(f"Cache invalidated: {tool_name}")
                return 1
            
            return 0
    
    def get_metrics(self) -> Dict[str, Any]:
        """
        Get cache metrics.
        
        Returns:
            Dict with hit_rate, hits, misses, evictions, cache_size, tier_distribution
        """
        with self._lock:
            total = self._hits + self._misses
            hit_rate = (self._hits / total * 100) if total > 0 else 0.0
            
            metrics = {
                "hit_rate_percent": round(hit_rate, 2),
                "hits": self._hits,
                "misses": self._misses,
                "evictions": self._evictions,
                "cache_size": len(self._cache),
                "default_ttl_seconds": self._default_ttl_seconds,
                "adaptive_ttl_enabled": self._enable_adaptive_ttl,
            }
            
            # Add tier distribution if adaptive TTL enabled
            if self._enable_adaptive_ttl:
                tier_counts = {
                    CacheTier.HOT.value: 0,
                    CacheTier.WARM.value: 0,
                    CacheTier.COLD.value: 0,
                }
                
                for tool_name in self._cache.keys():
                    tier = self._get_tier(tool_name)
                    tier_counts[tier.value] += 1
                
                metrics["tier_distribution"] = tier_counts
                metrics["total_access_counts"] = sum(self._access_counts.values())
                
                # Top 10 most accessed tools
                top_tools = sorted(
                    self._access_counts.items(),
                    key=lambda x: x[1],
                    reverse=True
                )[:10]
                
                metrics["top_10_tools"] = [
                    {"tool": name, "accesses": count, "tier": self._get_tier(name).value}
                    for name, count in top_tools
                ]
            
            return metrics
    
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
    
    def reset_metrics(self) -> None:
        """Reset cache metrics (hits, misses, evictions)."""
        with self._lock:
            self._hits = 0
            self._misses = 0
            self._evictions = 0
            logger.info("Cache metrics reset")


# Global singleton
_tool_cache: Optional[ToolRegistryCache] = None


def get_tool_cache(
    default_ttl_seconds: float = 300,
    enable_adaptive_ttl: bool = True
) -> ToolRegistryCache:
    """
    Get or create global tool cache.
    
    Args:
        default_ttl_seconds: Default cache TTL (5 minutes)
        enable_adaptive_ttl: Enable adaptive TTL based on access frequency
    
    Returns:
        Global ToolRegistryCache instance
    """
    global _tool_cache
    if _tool_cache is None:
        _tool_cache = ToolRegistryCache(
            default_ttl_seconds=default_ttl_seconds,
            enable_adaptive_ttl=enable_adaptive_ttl
        )
    return _tool_cache
