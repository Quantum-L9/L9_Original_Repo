"""
L9 Runtime - Rate Limiter
==========================

Production rate limiter with Redis backend and in-memory fallback.

Provides sliding window rate limiting for API calls, tool usage, etc.

Version: 1.0.0
"""

from __future__ import annotations

# ============================================================================
__dora_meta__ = {
    "component_name": "Rate Limiter",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2025-12-21T00:00:34Z",
    "updated_at": "2026-01-07T13:35:58Z",
    "layer": "operations",
    "domain": "runtime_operations",
    "module_name": "rate_limiter",
    "type": "service",
    "status": "production",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": ["Neo4j", "Redis"],
        "memory_layers": [],
        "imported_by": ["api.server", "runtime.__init__"],
    },
}
# ============================================================================

from collections import defaultdict
from datetime import datetime, timedelta

import structlog

logger = structlog.get_logger(__name__)

# Try to import Redis client
try:
    from runtime.redis_client import get_redis_client

    _has_redis_client = True
except ImportError:
    _has_redis_client = False
    logger.debug("Redis client not available - using in-memory rate limiting only")


class RateLimiter:
    """
    Production rate limiter with Redis backend and in-memory fallback.

    Uses sliding window algorithm for accurate rate limiting.
    """

    def __init__(self, window_seconds: int = 60, use_redis: bool = True) -> None:
        """
        Initialize rate limiter.

        Args:
            window_seconds: Size of sliding window in seconds (default: 60)
            use_redis: Whether to attempt Redis connection (default: True)
        """
        self._window_seconds = window_seconds
        self._use_redis = use_redis and _has_redis_client
        self._redis_client = None
        self._redis_available = False

        # In-memory fallback
        self._calls: dict[str, list[datetime]] = defaultdict(list)

        if self._use_redis:
            logger.info(
                f"RateLimiter initialized with Redis support (window: {window_seconds}s)"
            )
        else:
            logger.info(
                f"RateLimiter initialized (in-memory, window: {window_seconds}s)"
            )

    async def _ensure_redis(self) -> bool:
        """Ensure Redis client is connected."""
        if not self._use_redis:
            return False

        if self._redis_client is None:
            self._redis_client = await get_redis_client()
            self._redis_available = (
                self._redis_client is not None and self._redis_client.is_available()
            )

            if self._redis_available:
                logger.info("RateLimiter: Redis backend active")
            else:
                logger.info("RateLimiter: Redis unavailable, using in-memory fallback")

        return self._redis_available

    async def check_and_increment(self, key: str, limit: int) -> bool:
        """
        Check if under rate limit and increment if so.

        Args:
            key: Rate limit key (e.g., "rate_limit:google:now")
            limit: Maximum calls per window

        Returns:
            True if allowed (and increments), False if rate limited
        """
        # Try Redis first
        if await self._ensure_redis():
            try:
                redis_key = f"rate_limit:{key}"
                current = await self._redis_client.get_rate_limit(redis_key)

                if current >= limit:
                    logger.debug(f"Rate limit exceeded for {key}: {current}/{limit}")
                    # Log to Neo4j (async, non-blocking)
                    import asyncio

                    asyncio.create_task(
                        self._log_rate_limit_event(key, limit, exceeded=True)
                    )
                    return False

                # Increment
                new_count = await self._redis_client.increment_rate_limit(
                    redis_key,
                    ttl=self._window_seconds,
                )
                logger.debug(f"Rate limit incremented for {key}: {new_count}/{limit}")
                return True
            except Exception as e:
                logger.warning(
                    f"Redis rate limit check failed, falling back to in-memory: {e}"
                )

        # Fallback to in-memory
        now = datetime.utcnow()
        cutoff = now - timedelta(seconds=self._window_seconds)

        # Prune old calls
        self._calls[key] = [t for t in self._calls[key] if t > cutoff]

        # Check limit
        if len(self._calls[key]) >= limit:
            logger.debug(
                f"Rate limit exceeded for {key}: {len(self._calls[key])}/{limit}"
            )
            # Log to Neo4j (async, non-blocking)
            import asyncio

            asyncio.create_task(self._log_rate_limit_event(key, limit, exceeded=True))
            return False

        # Record call
        self._calls[key].append(now)
        logger.debug(
            f"Rate limit incremented for {key}: {len(self._calls[key])}/{limit}"
        )
        return True

    async def get_remaining(self, key: str, limit: int) -> int:
        """
        Get remaining calls in current window.

        Args:
            key: Rate limit key
            limit: Maximum calls per window

        Returns:
            Remaining calls
        """
        # Try Redis first
        if await self._ensure_redis():
            try:
                redis_key = f"rate_limit:{key}"
                current = await self._redis_client.get_rate_limit(redis_key)
                return max(0, limit - current)
            except Exception:
                pass

        # Fallback to in-memory
        now = datetime.utcnow()
        cutoff = now - timedelta(seconds=self._window_seconds)
        current = len([t for t in self._calls[key] if t > cutoff])
        return max(0, limit - current)

    async def get_usage(self, key: str) -> int:
        """
        Get current usage count.

        Args:
            key: Rate limit key

        Returns:
            Current count
        """
        # Try Redis first
        if await self._ensure_redis():
            try:
                redis_key = f"rate_limit:{key}"
                return await self._redis_client.get_rate_limit(redis_key)
            except Exception:
                pass

        # Fallback to in-memory
        now = datetime.utcnow()
        cutoff = now - timedelta(seconds=self._window_seconds)
        return len([t for t in self._calls[key] if t > cutoff])

    async def reset(self, key: str | None = None) -> None:
        """
        Reset rate limits for a key or all keys.

        Args:
            key: Key to reset (None = reset all)
        """
        # Try Redis first
        if await self._ensure_redis():
            try:
                if key:
                    redis_key = f"rate_limit:{key}"
                    await self._redis_client.delete(redis_key)
                else:
                    # Delete all rate limit keys
                    keys = await self._redis_client.keys("rate_limit:*")
                    for k in keys:
                        await self._redis_client.delete(k)
                return
            except Exception:
                pass

        # Fallback to in-memory
        if key:
            self._calls[key] = []
        else:
            self._calls.clear()

    async def _log_rate_limit_event(self, key: str, limit: int, exceeded: bool) -> None:
        """
        Log rate limit event to Neo4j for monitoring and analysis.

        Creates:
        - Event node for the rate limit check
        - Endpoint entity
        - Relationship showing which endpoint was checked

        This enables queries like:
        - "Show all rate limit violations in the last hour"
        - "Which endpoints are most rate-limited?"
        """
        try:
            from memory.graph_client import get_neo4j_client
        except ImportError:
            return

        neo4j = await get_neo4j_client()
        if not neo4j:
            return

        try:
            from uuid import uuid4

            event_id = f"rate_limit:{uuid4()}"

            # Parse endpoint from key (format: "rate_limit:endpoint:user" or just "endpoint")
            parts = key.split(":")
            endpoint = parts[0] if parts else key
            user_id = parts[1] if len(parts) > 1 else None

            await neo4j.create_event(
                event_id=event_id,
                event_type="rate_limit",
                timestamp=datetime.utcnow().isoformat(),
                properties={
                    "key": key,
                    "endpoint": endpoint,
                    "limit": limit,
                    "exceeded": exceeded,
                    "user_id": user_id,
                    "window_seconds": self._window_seconds,
                },
            )

            # Create endpoint entity and link
            await neo4j.create_entity(
                entity_type="Endpoint",
                entity_id=endpoint,
                properties={"path": endpoint},
            )
            await neo4j.create_relationship(
                from_type="Event",
                from_id=event_id,
                to_type="Endpoint",
                to_id=endpoint,
                rel_type="CHECKED",
            )

            # Link to user if available
            if user_id:
                await neo4j.create_entity(
                    entity_type="User",
                    entity_id=user_id,
                    properties={"id": user_id},
                )
                await neo4j.create_relationship(
                    from_type="Event",
                    from_id=event_id,
                    to_type="User",
                    to_id=user_id,
                    rel_type="BY_USER",
                )

            logger.debug(f"Logged rate limit event to Neo4j: {event_id}")

        except Exception as e:
            logger.debug(f"Failed to log rate limit event to Neo4j: {e}")


__all__ = ["RateLimiter"]

# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "RUN-OPER-006",
    "governance_level": "medium",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": ["memory.graph_client", "runtime.redis_client"],
    "tags": [
        "api",
        "async",
        "cache",
        "debugging",
        "event-driven",
        "logging",
        "monitoring",
        "operations",
        "runtime-operations",
        "service",
    ],
    "keywords": [
        "check",
        "increment",
        "limiter",
        "memory",
        "rate",
        "remaining",
        "reset",
        "usage",
    ],
    "business_value": "Provides sliding window rate limiting for API calls, tool usage, etc. Version: 1.0.0",
    "last_modified": "2026-01-07T13:35:58Z",
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
