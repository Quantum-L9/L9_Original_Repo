"""
Redis Cache & Queue Tools
=========================

Tools for Redis cache operations, task queue management, and rate limiting.
Migrated from runtime/l_tools.py for domain separation (GMP-122).

This module contains 13 Redis-related tools:
- Cache operations: get, set, keys, delete
- Queue operations: enqueue_task, dequeue_task, queue_size
- Task context: get_task_context, set_task_context
- Rate limiting: get/set/increment/decrement_rate_limit

Version: 1.0.0
"""

from __future__ import annotations

# ============================================================================
__dora_meta__ = {
    "component_name": "Redis Tools",
    "module_version": "1.0.0",
    "created_by": "GMP-122",
    "created_at": "2026-01-24T00:00:00Z",
    "updated_at": "2026-01-24T00:00:00Z",
    "layer": "runtime",
    "domain": "tools",
    "module_name": "redis_tools",
    "type": "tools",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": ["Redis"],
        "memory_layers": ["working_memory"],
        "imported_by": ["runtime.tool_packages"],
    },
}
# ============================================================================

from typing import Any

import structlog

from runtime.tool_registry import register_tool

logger = structlog.get_logger(__name__)


# =============================================================================
# CACHE OPERATIONS
# =============================================================================


@register_tool(
    category="redis", priority=10, description="Get a value from Redis cache"
)
async def redis_get(
    key: str,
    **kwargs: Any,
) -> dict[str, Any]:
    """
    Get a value from Redis cache.

    Args:
        key: Redis key to retrieve

    Returns:
        Dict with value or null if not found
    """
    try:
        from runtime.redis_client import get_redis_client

        redis = await get_redis_client()
        if not redis or not redis.is_available():
            return {
                "error": "Redis not available",
                "status": "error",
            }

        value = await redis.get(key)

        logger.info(f"Redis GET: {key}")

        return {
            "key": key,
            "value": value,
            "exists": value is not None,
            "status": "success",
        }
    except Exception as e:
        logger.error(f"Redis GET failed: {e}")
        return {"error": str(e), "status": "error"}


@register_tool(category="redis", priority=10, description="Set a value in Redis cache")
async def redis_set(
    key: str,
    value: str,
    ttl_seconds: int | None = None,
    **kwargs: Any,
) -> dict[str, Any]:
    """
    Set a value in Redis cache.

    Args:
        key: Redis key
        value: Value to store (string)
        ttl_seconds: Optional TTL in seconds (None = no expiry)

    Returns:
        Dict with status
    """
    try:
        from runtime.redis_client import get_redis_client

        redis = await get_redis_client()
        if not redis or not redis.is_available():
            return {
                "error": "Redis not available",
                "status": "error",
            }

        await redis.set(key, value, ex=ttl_seconds)

        logger.info(f"Redis SET: {key} (ttl={ttl_seconds})")

        return {
            "key": key,
            "ttl_seconds": ttl_seconds,
            "status": "success",
        }
    except Exception as e:
        logger.error(f"Redis SET failed: {e}")
        return {"error": str(e), "status": "error"}


@register_tool(
    category="redis", priority=10, description="List Redis keys matching a pattern"
)
async def redis_keys(
    pattern: str = "*",
    **kwargs: Any,
) -> dict[str, Any]:
    """
    List Redis keys matching a pattern.

    Args:
        pattern: Key pattern (e.g., "agent:*", "task:*")

    Returns:
        Dict with list of matching keys
    """
    try:
        from runtime.redis_client import get_redis_client

        redis = await get_redis_client()
        if not redis or not redis.is_available():
            return {
                "error": "Redis not available",
                "status": "error",
            }

        keys = await redis.keys(pattern)

        logger.info(f"Redis KEYS: {pattern} -> {len(keys)} matches")

        return {
            "pattern": pattern,
            "keys": keys,
            "count": len(keys),
            "status": "success",
        }
    except Exception as e:
        logger.error(f"Redis KEYS failed: {e}")
        return {"error": str(e), "status": "error"}


@register_tool(category="redis", priority=10, description="Delete a key from Redis")
async def redis_delete(
    key: str,
    **kwargs: Any,
) -> dict[str, Any]:
    """
    Delete a key from Redis.

    Args:
        key: The key to delete

    Returns:
        Dict with deletion result
    """
    try:
        from runtime.redis_client import get_redis_client

        redis = await get_redis_client()
        if not redis or not redis.is_available():
            return {"error": "Redis not available", "status": "error"}

        success = await redis.delete(key)

        logger.info(f"Redis DELETE: {key} -> {success}")
        return {"key": key, "deleted": success, "status": "success"}
    except Exception as e:
        logger.error(f"Redis DELETE failed: {e}")
        return {"error": str(e), "status": "error"}


# =============================================================================
# QUEUE OPERATIONS
# =============================================================================


@register_tool(
    category="redis", priority=10, description="Enqueue a task to Redis queue"
)
async def redis_enqueue_task(
    queue_name: str,
    task_data: dict[str, Any],
    priority: int = 0,
    **kwargs: Any,
) -> dict[str, Any]:
    """
    Enqueue a task to Redis queue.

    Args:
        queue_name: Name of the task queue
        task_data: Task payload
        priority: Task priority (higher = more important)

    Returns:
        Dict with task ID
    """
    try:
        from runtime.redis_client import get_redis_client

        redis = await get_redis_client()
        if not redis or not redis.is_available():
            return {"error": "Redis not available", "status": "error"}

        task_id = await redis.enqueue_task(queue_name, task_data, priority)

        logger.info(f"Redis ENQUEUE: queue={queue_name} task_id={task_id}")
        return {"queue": queue_name, "task_id": task_id, "status": "success"}
    except Exception as e:
        logger.error(f"Redis ENQUEUE failed: {e}")
        return {"error": str(e), "status": "error"}


@register_tool(
    category="redis",
    priority=10,
    description="Dequeue highest priority task from Redis queue",
)
async def redis_dequeue_task(
    queue_name: str,
    **kwargs: Any,
) -> dict[str, Any]:
    """
    Dequeue highest priority task from Redis queue.

    Args:
        queue_name: Name of the task queue

    Returns:
        Dict with task data or None if queue empty
    """
    try:
        from runtime.redis_client import get_redis_client

        redis = await get_redis_client()
        if not redis or not redis.is_available():
            return {"error": "Redis not available", "status": "error"}

        task = await redis.dequeue_task(queue_name)

        logger.info(f"Redis DEQUEUE: queue={queue_name} found={task is not None}")
        return {"queue": queue_name, "task": task, "status": "success"}
    except Exception as e:
        logger.error(f"Redis DEQUEUE failed: {e}")
        return {"error": str(e), "status": "error"}


@register_tool(
    category="redis", priority=10, description="Get the size of a Redis task queue"
)
async def redis_queue_size(
    queue_name: str,
    **kwargs: Any,
) -> dict[str, Any]:
    """
    Get the size of a Redis task queue.

    Args:
        queue_name: Name of the task queue

    Returns:
        Dict with queue size
    """
    try:
        from runtime.redis_client import get_redis_client

        redis = await get_redis_client()
        if not redis or not redis.is_available():
            return {"error": "Redis not available", "status": "error"}

        size = await redis.queue_size(queue_name)

        logger.info(f"Redis QUEUE_SIZE: queue={queue_name} size={size}")
        return {"queue": queue_name, "size": size, "status": "success"}
    except Exception as e:
        logger.error(f"Redis QUEUE_SIZE failed: {e}")
        return {"error": str(e), "status": "error"}


# =============================================================================
# TASK CONTEXT
# =============================================================================


@register_tool(
    category="redis", priority=10, description="Get cached task context from Redis"
)
async def redis_get_task_context(
    task_id: str,
    **kwargs: Any,
) -> dict[str, Any]:
    """
    Get cached task context from Redis.

    Args:
        task_id: Task identifier

    Returns:
        Dict with task context
    """
    try:
        from runtime.redis_client import get_redis_client

        redis = await get_redis_client()
        if not redis or not redis.is_available():
            return {"error": "Redis not available", "status": "error"}

        context = await redis.get_task_context(task_id)

        logger.info(f"Redis GET_TASK_CONTEXT: task={task_id} found={bool(context)}")
        return {"task_id": task_id, "context": context, "status": "success"}
    except Exception as e:
        logger.error(f"Redis GET_TASK_CONTEXT failed: {e}")
        return {"error": str(e), "status": "error"}


@register_tool(
    category="redis", priority=10, description="Set task context in Redis cache"
)
async def redis_set_task_context(
    task_id: str,
    context: dict[str, Any],
    ttl_seconds: int = 3600,
    **kwargs: Any,
) -> dict[str, Any]:
    """
    Set task context in Redis cache.

    Args:
        task_id: Task identifier
        context: Context data to cache
        ttl_seconds: Time-to-live in seconds

    Returns:
        Dict with success status
    """
    try:
        from runtime.redis_client import get_redis_client

        redis = await get_redis_client()
        if not redis or not redis.is_available():
            return {"error": "Redis not available", "status": "error"}

        success = await redis.set_task_context(task_id, context, ttl_seconds)

        logger.info(f"Redis SET_TASK_CONTEXT: task={task_id} ttl={ttl_seconds}")
        return {"task_id": task_id, "set": success, "status": "success"}
    except Exception as e:
        logger.error(f"Redis SET_TASK_CONTEXT failed: {e}")
        return {"error": str(e), "status": "error"}


# =============================================================================
# RATE LIMITING
# =============================================================================


@register_tool(
    category="redis", priority=10, description="Get current rate limit count for a key"
)
async def redis_get_rate_limit(
    key: str,
    **kwargs: Any,
) -> dict[str, Any]:
    """
    Get current rate limit count for a key.

    Args:
        key: Rate limit key (e.g., "api:user:123")

    Returns:
        Dict with current count
    """
    try:
        from runtime.redis_client import get_redis_client

        client = await get_redis_client()
        count = await client.get_rate_limit(key)

        return {
            "status": "success",
            "key": key,
            "count": count,
        }
    except Exception as e:
        logger.error(f"Redis get rate limit failed: {e}")
        return {"error": str(e), "status": "error"}


@register_tool(
    category="redis", priority=10, description="Set rate limit count with TTL"
)
async def redis_set_rate_limit(
    key: str,
    count: int,
    ttl_seconds: int = 60,
    **kwargs: Any,
) -> dict[str, Any]:
    """
    Set rate limit count with TTL.

    Args:
        key: Rate limit key
        count: Count value to set
        ttl_seconds: Time-to-live in seconds (default 60)

    Returns:
        Dict with set result
    """
    try:
        from runtime.redis_client import get_redis_client

        client = await get_redis_client()
        await client.set_rate_limit(key, count, ttl_seconds)

        logger.info(f"Rate limit set: {key}={count} TTL={ttl_seconds}s")
        return {
            "status": "success",
            "key": key,
            "count": count,
            "ttl_seconds": ttl_seconds,
        }
    except Exception as e:
        logger.error(f"Redis set rate limit failed: {e}")
        return {"error": str(e), "status": "error"}


@register_tool(
    category="redis", priority=10, description="Increment rate limit counter"
)
async def redis_increment_rate_limit(
    key: str,
    amount: int = 1,
    **kwargs: Any,
) -> dict[str, Any]:
    """
    Increment rate limit counter.

    Args:
        key: Rate limit key
        amount: Amount to increment (default 1)

    Returns:
        Dict with new count
    """
    try:
        from runtime.redis_client import get_redis_client

        client = await get_redis_client()
        new_count = await client.increment_rate_limit(key, amount)

        return {
            "status": "success",
            "key": key,
            "new_count": new_count,
            "incremented_by": amount,
        }
    except Exception as e:
        logger.error(f"Redis increment rate limit failed: {e}")
        return {"error": str(e), "status": "error"}


@register_tool(
    category="redis", priority=10, description="Decrement rate limit counter"
)
async def redis_decrement_rate_limit(
    key: str,
    amount: int = 1,
    **kwargs: Any,
) -> dict[str, Any]:
    """
    Decrement rate limit counter.

    Args:
        key: Rate limit key
        amount: Amount to decrement (default 1)

    Returns:
        Dict with new count
    """
    try:
        from runtime.redis_client import get_redis_client

        client = await get_redis_client()
        new_count = await client.decrement_rate_limit(key, amount)

        return {
            "status": "success",
            "key": key,
            "new_count": new_count,
            "decremented_by": amount,
        }
    except Exception as e:
        logger.error(f"Redis decrement rate limit failed: {e}")
        return {"error": str(e), "status": "error"}


# =============================================================================
# DORA FOOTER META - AUTO-GENERATED
# =============================================================================
__dora_footer__ = {
    "component_id": "RUN-REDIS-TOOLS-001",
    "governance_level": "standard",
    "security_reviewed": False,
    "performance_tested": False,
    "last_audit": "2026-01-24T00:00:00Z",
}
# =============================================================================
