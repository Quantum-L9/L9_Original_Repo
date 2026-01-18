"""
L9 Runtime - Redis Client
==========================

Production Redis client for L9 with graceful fallback.

Provides:
- Redis connection management
- Task queue backend
- Rate limiting backend
- Session state storage

Version: 1.0.0
"""

from __future__ import annotations

# ============================================================================
__dora_meta__ = {
    "component_name": "Redis Client",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2025-12-21T00:00:34Z",
    "updated_at": "2026-01-17T23:47:56Z",
    "layer": "operations",
    "domain": "runtime_operations",
    "module_name": "redis_client",
    "type": "client",
    "status": "production",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": ["Redis"],
        "memory_layers": [],
        "imported_by": ["api.e2e_slack_audit", "api.memory.cache", "api.server", "ci.check_dependency_patterns", "core.agents.bootstrap.phase_2_instantiate", "core.agents.executor", "core.singleton_registry", "mcp_memory.tests.test_all_layers", "memory.graph_search_cache", "memory.predictive_cache"],
    },
}
# ============================================================================

import json
import structlog
import os
from typing import Any, Optional

logger = structlog.get_logger(__name__)

# L's tenant ID for key prefixing - SEPARATE from Cursor's
# L uses:      L9_TENANT_ID = 'l-cto' (here)
# Cursor uses: CURSOR_TENANT_ID = 'cursor-ide' (agents/cursor/cursor_memory_kernel.py)
# This prevents session state cross-contamination when Igor talks to both simultaneously
DEFAULT_TENANT_ID = os.getenv("L9_TENANT_ID", "l-cto")

from core.decorators import must_stay_async

# Try to import Redis
try:
    import redis.asyncio as aioredis

    _has_redis = True
except ImportError:
    _has_redis = False
    logger.warning("Redis not available - install with: pip install redis>=5.0.0")


class RedisClient:
    """
    Production Redis client with connection pooling.

    Gracefully falls back to None if Redis is unavailable.
    """

    def __init__(
        self,
        host: Optional[str] = None,
        port: Optional[int] = None,
        db: int = 0,
        password: Optional[str] = None,
        decode_responses: bool = True,
    ):
        """
        Initialize Redis client.

        Args:
            host: Redis host (default: REDIS_HOST env or 'localhost')
            port: Redis port (default: REDIS_PORT env or 6379)
            db: Redis database number (default: 0)
            password: Redis password (optional)
            decode_responses: Decode responses as strings (default: True)
        """
        if not _has_redis:
            self._client = None
            self._available = False
            logger.warning("Redis not available - operations will fail gracefully")
            return

        self._host = host or os.getenv("REDIS_HOST", "localhost")
        self._port = port or int(os.getenv("REDIS_PORT", "6379"))
        self._db = db
        self._password = password or os.getenv("REDIS_PASSWORD")
        self._decode_responses = decode_responses
        self._client: Optional[aioredis.Redis] = None
        self._available = False

    async def connect(self) -> bool:
        """
        Connect to Redis server.

        Returns:
            True if connected, False if unavailable
        """
        if not _has_redis:
            return False

        if self._client is not None:
            return self._available

        try:
            self._client = aioredis.Redis(
                host=self._host,
                port=self._port,
                db=self._db,
                password=self._password,
                decode_responses=self._decode_responses,
                socket_connect_timeout=2,
                socket_timeout=2,
                retry_on_timeout=True,
            )

            # Test connection
            await self._client.ping()
            self._available = True
            logger.info(f"Redis connected: {self._host}:{self._port}/{self._db}")
            return True
        except Exception as e:
            logger.warning(f"Redis connection failed: {e} - falling back to in-memory")
            self._client = None
            self._available = False
            return False

    async def disconnect(self) -> None:
        """Close Redis connection."""
        if self._client:
            try:
                await self._client.close()
                logger.info("Redis disconnected")
            except Exception as e:
                logger.warning(f"Error disconnecting Redis: {e}")
            finally:
                self._client = None
                self._available = False

    def is_available(self) -> bool:
        """Check if Redis is available."""
        return self._available and self._client is not None

    def _prefixed_key(self, key: str, tenant_id: Optional[str] = None) -> str:
        """
        Create a tenant-prefixed key for multi-tenant isolation.

        Args:
            key: Original key (e.g., "tasks", "session:123")
            tenant_id: Tenant ID (default: DEFAULT_TENANT_ID)

        Returns:
            Prefixed key (e.g., "l9-shared:tasks", "l9-shared:session:123")
        """
        tid = tenant_id or DEFAULT_TENANT_ID
        # Avoid double-prefixing if key already has tenant prefix
        if key.startswith(f"{tid}:"):
            return key
        return f"{tid}:{key}"

    # =========================================================================
    # Task Queue Operations
    # =========================================================================

    async def enqueue_task(
        self,
        queue_name: str,
        task_data: dict[str, Any],
        priority: int = 5,
    ) -> Optional[str]:
        """
        Enqueue a task in Redis sorted set (priority queue).

        Args:
            queue_name: Queue name (e.g., "l9:tasks")
            task_data: Task data dict
            priority: Priority (lower = higher priority)

        Returns:
            Task ID or None if Redis unavailable
        """
        if not self.is_available():
            return None

        try:
            import uuid

            task_id = str(uuid.uuid4())
            task_data["task_id"] = task_id
            task_data["priority"] = priority

            # Store task data (with tenant prefix)
            prefixed_queue = self._prefixed_key(queue_name)
            task_key = f"{prefixed_queue}:task:{task_id}"
            await self._client.setex(
                task_key,
                3600,  # 1 hour TTL
                json.dumps(task_data),
            )

            # Add to priority queue (sorted set)
            await self._client.zadd(
                f"{prefixed_queue}:queue",
                {task_id: priority},
            )

            logger.debug(
                f"Enqueued task {task_id} to {prefixed_queue} with priority {priority}"
            )
            return task_id
        except Exception as e:
            logger.error(f"Redis enqueue failed: {e}")
            return None

    async def dequeue_task(self, queue_name: str) -> Optional[dict[str, Any]]:
        """
        Dequeue highest priority task from Redis.

        Args:
            queue_name: Queue name

        Returns:
            Task data dict or None if queue empty or Redis unavailable
        """
        if not self.is_available():
            return None

        try:
            # Get highest priority task (lowest score) - with tenant prefix
            prefixed_queue = self._prefixed_key(queue_name)
            result = await self._client.zpopmin(f"{prefixed_queue}:queue", count=1)

            if not result:
                return None

            task_id, _ = result[0]
            task_key = f"{prefixed_queue}:task:{task_id}"

            # Get task data
            task_data_str = await self._client.get(task_key)
            if not task_data_str:
                return None

            # Delete task data
            await self._client.delete(task_key)

            task_data = json.loads(task_data_str)
            logger.debug(f"Dequeued task {task_id} from {queue_name}")
            return task_data
        except Exception as e:
            logger.error(f"Redis dequeue failed: {e}")
            return None

    async def queue_size(self, queue_name: str) -> int:
        """Get queue size."""
        if not self.is_available():
            return 0

        try:
            prefixed_queue = self._prefixed_key(queue_name)
            return await self._client.zcard(f"{prefixed_queue}:queue")
        except Exception as e:
            logger.error(f"Redis queue_size failed: {e}")
            return 0

    # =========================================================================
    # Rate Limiting Operations
    # =========================================================================

    async def get_rate_limit(self, key: str) -> int:
        """
        Get current rate limit count.

        Args:
            key: Rate limit key (e.g., "rate_limit:google:now")

        Returns:
            Current count or 0 if unavailable
        """
        if not self.is_available():
            return 0

        try:
            prefixed = self._prefixed_key(key)
            value = await self._client.get(prefixed)
            return int(value) if value else 0
        except Exception as e:
            logger.error(f"Redis get_rate_limit failed: {e}")
            return 0

    async def set_rate_limit(self, key: str, value: int, ttl: int = 60) -> bool:
        """
        Set rate limit count with TTL.

        Args:
            key: Rate limit key
            value: Count value
            ttl: Time to live in seconds (default: 60)

        Returns:
            True if set, False if unavailable
        """
        if not self.is_available():
            return False

        try:
            prefixed = self._prefixed_key(key)
            await self._client.setex(prefixed, ttl, value)
            return True
        except Exception as e:
            logger.error(f"Redis set_rate_limit failed: {e}")
            return False

    async def increment_rate_limit(self, key: str, ttl: int = 60) -> int:
        """
        Increment rate limit counter.

        Args:
            key: Rate limit key
            ttl: Time to live in seconds (default: 60)

        Returns:
            New count or 0 if unavailable
        """
        if not self.is_available():
            return 0

        try:
            prefixed = self._prefixed_key(key)
            count = await self._client.incr(prefixed)
            if count == 1:  # First increment, set TTL
                await self._client.expire(prefixed, ttl)
            return count
        except Exception as e:
            logger.error(f"Redis increment_rate_limit failed: {e}")
            return 0

    async def get_task_context(self, task_id: str) -> dict:
        """
        Retrieve cached task state from Redis.

        Args:
            task_id: Task identifier

        Returns:
            Context dict or empty dict if not found
        """
        if not self.is_available():
            return {}

        try:
            context_key = self._prefixed_key(f"task_context:{task_id}")
            context_str = await self._client.get(context_key)
            if context_str:
                return json.loads(context_str)
            return {}
        except Exception as e:
            logger.error(f"Redis get_task_context failed: {e}")
            return {}

    async def set_task_context(
        self, task_id: str, context: dict, ttl: int = 3600
    ) -> bool:
        """
        Cache task context in Redis.

        Args:
            task_id: Task identifier
            context: Context dict to cache
            ttl: Time to live in seconds (default: 3600 = 1 hour)

        Returns:
            True if cached, False otherwise
        """
        if not self.is_available():
            return False

        try:
            context_key = self._prefixed_key(f"task_context:{task_id}")
            await self._client.setex(context_key, ttl, json.dumps(context))
            return True
        except Exception as e:
            logger.error(f"Redis set_task_context failed: {e}")
            return False

    async def decrement_rate_limit(self, key: str) -> int:
        """Decrement rate limit counter."""
        if not self.is_available():
            return 0

        try:
            prefixed = self._prefixed_key(key)
            return await self._client.decr(prefixed)
        except Exception as e:
            logger.error(f"Redis decrement_rate_limit failed: {e}")
            return 0

    # =========================================================================
    # Generic Key-Value Operations (all tenant-prefixed by default)
    # =========================================================================

    async def get(self, key: str, raw: bool = False) -> Optional[str]:
        """
        Get value by key.

        Args:
            key: Key to get
            raw: If True, use key as-is (no tenant prefix)
        """
        if not self.is_available():
            return None

        try:
            prefixed = key if raw else self._prefixed_key(key)
            return await self._client.get(prefixed)
        except Exception as e:
            logger.error(f"Redis get failed: {e}")
            return None

    async def set(
        self, key: str, value: str, ttl: Optional[int] = None, raw: bool = False
    ) -> bool:
        """
        Set key-value with optional TTL.

        Args:
            key: Key to set
            value: Value to set
            ttl: Optional TTL in seconds
            raw: If True, use key as-is (no tenant prefix)
        """
        if not self.is_available():
            return False

        try:
            prefixed = key if raw else self._prefixed_key(key)
            if ttl:
                await self._client.setex(prefixed, ttl, value)
            else:
                await self._client.set(prefixed, value)
            return True
        except Exception as e:
            logger.error(f"Redis set failed: {e}")
            return False

    async def delete(self, key: str, raw: bool = False) -> bool:
        """
        Delete key.

        Args:
            key: Key to delete
            raw: If True, use key as-is (no tenant prefix)
        """
        if not self.is_available():
            return False

        try:
            prefixed = key if raw else self._prefixed_key(key)
            await self._client.delete(prefixed)
            return True
        except Exception as e:
            logger.error(f"Redis delete failed: {e}")
            return False

    @must_stay_async("callers use await")
    async def keys(self, pattern: str, raw: bool = False) -> list[str]:
        """
        Get keys matching pattern.

        Args:
            pattern: Pattern to match
            raw: If True, use pattern as-is (no tenant prefix)
        """
        if not self.is_available():
            return []

        try:
            prefixed = pattern if raw else self._prefixed_key(pattern)
            return [key async for key in self._client.scan_iter(match=prefixed)]
        except Exception as e:
            logger.error(f"Redis keys failed: {e}")
            return []


# =============================================================================
# Singleton Factory
# =============================================================================

_redis_client: Optional[RedisClient] = None


async def get_redis_client() -> Optional[RedisClient]:
    """
    Get or create singleton Redis client.

    Returns:
        RedisClient instance or None if unavailable
    """
    global _redis_client

    if _redis_client is None:
        _redis_client = RedisClient()
        await _redis_client.connect()

    return _redis_client if _redis_client.is_available() else None


async def close_redis_client() -> None:
    """Close singleton Redis client."""
    global _redis_client
    if _redis_client:
        await _redis_client.disconnect()
        _redis_client = None


__all__ = ["RedisClient", "get_redis_client", "close_redis_client"]

# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "RUN-OPER-008",
    "governance_level": "medium",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": ["core.decorators"],
    "tags": ["async", "cache", "caching", "client", "debugging", "event-driven", "logging", "operations", "queue", "runtime-operations"],
    "keywords": ["available", "backend", "client", "close", "connect", "decrement", "delete", "dequeue"],
    "business_value": "Redis connection management Task queue backend Rate limiting backend Session state storage Version: 1.0.0",
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
