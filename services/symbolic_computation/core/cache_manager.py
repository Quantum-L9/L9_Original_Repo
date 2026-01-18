"""
SymPy Cache Manager
====================

Multi-tier caching for expression results and compiled functions.
Uses both LRU cache (fast, in-memory) and Redis (persistent, shared).

Version: 6.0.0
"""

from __future__ import annotations

# ============================================================================
__dora_meta__ = {
    "component_name": "Cache Manager",
    "module_version": "6.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2026-01-02T15:15:57Z",
    "updated_at": "2026-01-17T23:47:56Z",
    "layer": "operations",
    "domain": "symbolic_computation",
    "module_name": "cache_manager",
    "type": "service",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": ["Redis"],
        "memory_layers": [],
        "imported_by": ["services.symbolic_computation.api.routes", "services.symbolic_computation.core.__init__", "services.symbolic_computation.tools.symbolic_tool", "tests.services.symbolic_computation.test_integration"],
    },
}
# ============================================================================

import hashlib
import pickle
from typing import Any, Callable, Dict, Optional

import structlog

from services.symbolic_computation.config import SymbolicComputationConfig, get_config
from core.decorators import must_stay_async

logger = structlog.get_logger(__name__)


class CacheManager:
    """
    Multi-tier cache manager for symbolic computation results.

    Provides:
    - L1 Cache: LRU in-memory cache for hot expressions
    - L2 Cache: Redis-backed persistent cache for result sharing

    Cache key format:
    - Expressions: {keyspace}:{expr_hash}:{backend}
    - Compiled: {keyspace}:compiled:{expr_hash}

    Example:
        cache = CacheManager()
        await cache.cache_expression("x**2", "numpy", 4.0)
        result = await cache.get_cached_result("x**2", "numpy")
        print(result)  # 4.0
    """

    def __init__(
        self,
        config: Optional[SymbolicComputationConfig] = None,
        redis_client: Optional[Any] = None,
    ):
        """
        Initialize the cache manager.

        Args:
            config: Configuration instance (uses global if not provided)
            redis_client: Optional Redis client for L2 cache
        """
        self.config = config or get_config()
        self.redis_client = redis_client
        self.logger = logger.bind(component="cache_manager")

        # L1: In-memory LRU cache
        self._result_cache: Dict[str, Any] = {}
        self._compiled_cache: Dict[str, Callable] = {}

        # Stats
        self._hits = 0
        self._misses = 0

        self.logger.info(
            "cache_manager_initialized",
            cache_size=self.config.cache_size,
            redis_enabled=redis_client is not None,
        )

    async def cache_expression(
        self,
        expr: str,
        backend: str,
        result: Any,
    ) -> bool:
        """
        Cache an expression evaluation result.

        Args:
            expr: Original expression string
            backend: Backend used for evaluation
            result: Computed result to cache

        Returns:
            True if cached successfully
        """
        expr_hash = self._hash_expression(expr)
        cache_key = self.config.get_redis_key(expr_hash, backend)

        try:
            # L1: In-memory cache
            self._cache_l1_result(cache_key, result)

            # L2: Redis cache
            if self.redis_client:
                await self._cache_l2_result(cache_key, result)

            self.logger.debug(
                "expression_cached",
                expr_hash=expr_hash,
                backend=backend,
            )
            return True

        except Exception as e:
            self.logger.error(
                "cache_expression_failed",
                error=str(e),
                expr_hash=expr_hash,
            )
            return False

    async def get_cached_result(
        self,
        expr: str,
        backend: str,
    ) -> Optional[Any]:
        """
        Retrieve cached expression result.

        Args:
            expr: Original expression string
            backend: Backend used for evaluation

        Returns:
            Cached result if found, None otherwise
        """
        expr_hash = self._hash_expression(expr)
        cache_key = self.config.get_redis_key(expr_hash, backend)

        # L1: Check in-memory cache first
        if cache_key in self._result_cache:
            self._hits += 1
            self.logger.debug("cache_l1_hit", expr_hash=expr_hash)
            return self._result_cache[cache_key]

        # L2: Check Redis cache
        if self.redis_client:
            result = await self._get_l2_result(cache_key)
            if result is not None:
                self._hits += 1
                # Promote to L1
                self._cache_l1_result(cache_key, result)
                self.logger.debug("cache_l2_hit", expr_hash=expr_hash)
                return result

        self._misses += 1
        self.logger.debug("cache_miss", expr_hash=expr_hash)
        return None

    @must_stay_async("callers use await")
    async def cache_compiled_function(
        self,
        expr: str,
        func: Callable,
    ) -> bool:
        """
        Cache a compiled expression function.

        Note: Compiled functions are only cached in L1 (in-memory)
        since lambdas/callables can't be easily serialized.

        Args:
            expr: Original expression string
            func: Compiled callable function

        Returns:
            True if cached successfully
        """
        expr_hash = self._hash_expression(expr)
        cache_key = self.config.get_compiled_key(expr_hash)

        try:
            # Enforce cache size limit
            if len(self._compiled_cache) >= self.config.cache_size:
                # Remove oldest entry (simple FIFO)
                oldest = next(iter(self._compiled_cache))
                del self._compiled_cache[oldest]

            self._compiled_cache[cache_key] = func

            self.logger.debug(
                "compiled_function_cached",
                expr_hash=expr_hash,
            )
            return True

        except Exception as e:
            self.logger.error(
                "cache_compiled_failed",
                error=str(e),
            )
            return False

    def get_cached_compiled(self, expr: str) -> Optional[Callable]:
        """
        Retrieve cached compiled function.

        Args:
            expr: Original expression string

        Returns:
            Cached compiled function if found, None otherwise
        """
        expr_hash = self._hash_expression(expr)
        cache_key = self.config.get_compiled_key(expr_hash)

        return self._compiled_cache.get(cache_key)

    def _cache_l1_result(self, key: str, value: Any) -> None:
        """Cache result in L1 (in-memory) with size limit."""
        if len(self._result_cache) >= self.config.cache_size:
            # Remove oldest entry
            oldest = next(iter(self._result_cache))
            del self._result_cache[oldest]

        self._result_cache[key] = value

    async def _cache_l2_result(self, key: str, value: Any) -> None:
        """Cache result in L2 (Redis)."""
        try:
            serialized = pickle.dumps(value)
            await self.redis_client.setex(
                key,
                self.config.redis_cache_ttl,
                serialized,
            )
        except Exception as e:
            self.logger.warning(
                "redis_cache_failed",
                error=str(e),
            )

    async def _get_l2_result(self, key: str) -> Optional[Any]:
        """Retrieve result from L2 (Redis)."""
        try:
            serialized = await self.redis_client.get(key)
            if serialized:
                return pickle.loads(serialized)
            return None
        except Exception as e:
            self.logger.warning(
                "redis_get_failed",
                error=str(e),
            )
            return None

    def _hash_expression(self, expr: str) -> str:
        """Generate hash for expression."""
        return hashlib.sha256(expr.encode()).hexdigest()[:16]

    def clear(self) -> None:
        """Clear all caches."""
        self._result_cache.clear()
        self._compiled_cache.clear()
        self._hits = 0
        self._misses = 0
        self.logger.info("caches_cleared")

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        total = self._hits + self._misses
        hit_rate = (self._hits / total * 100) if total > 0 else 0.0

        return {
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": round(hit_rate, 2),
            "l1_result_size": len(self._result_cache),
            "l1_compiled_size": len(self._compiled_cache),
            "max_size": self.config.cache_size,
        }

# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "SER-OPER-025",
    "governance_level": "medium",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": ["core.decorators"],
    "tags": ["async", "caching", "debugging", "logging", "operations", "security", "service", "symbolic-computation"],
    "keywords": ["cache", "cached", "clear", "compiled", "expression", "function", "manager", "memory"],
    "business_value": "Implements CacheManager for cache manager functionality",
    "last_modified": "2026-01-17T23:47:56Z",
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
