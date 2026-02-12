"""
Slack Thread Context Cache (Redis)
===================================

Redis-backed cache for Slack thread conversation context.
Eliminates per-message PostgreSQL queries and fixes the write-read
race condition where message N+1 cannot see message N's context.

Key pattern: slack:thread:{thread_uuid}:context
TTL: 1800s (30 minutes) — covers active conversation window

Architecture:
    - Read-through: check Redis → miss → query PostgreSQL → populate Redis
    - Write-ahead: append inbound message to cache BEFORE agent routing
    - Write-through: append packet summary after substrate write
    - Graceful fallback: Redis unavailable → PostgreSQL-only (current behavior)

Version: 1.0.0
"""

from __future__ import annotations

# ============================================================================
__dora_meta__ = {
    "component_name": "Slack Thread Context Cache",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2026-02-12T21:38:00Z",
    "updated_at": "2026-02-12T21:38:00Z",
    "layer": "operations",
    "domain": "memory_substrate",
    "module_name": "slack_thread_cache",
    "type": "service",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": ["Redis"],
        "memory_layers": ["working_memory"],
        "imported_by": [
            "memory.slack_ingest",
        ],
    },
}
# ============================================================================

import json
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

import structlog

if TYPE_CHECKING:
    from runtime.redis_client import RedisClient

logger = structlog.get_logger(__name__)

# Default TTL: 30 minutes (covers active conversation window)
DEFAULT_THREAD_CACHE_TTL = 1800

# Maximum packets to store per thread (bounded to prevent memory bloat)
MAX_CACHED_PACKETS_PER_THREAD = 25


__all__ = [
    "SlackThreadCacheService",
]


class SlackThreadCacheService:
    """
    Redis-backed cache for Slack thread conversation context.

    Provides:
    - get_thread_context(): read-through cache for thread packets
    - set_thread_context(): populate cache from PostgreSQL results
    - append_to_thread(): write-ahead/write-through packet append
    - invalidate_thread(): explicit cache clear

    All operations gracefully degrade to no-op if Redis is unavailable.
    """

    def __init__(
        self,
        redis_client: RedisClient,
        ttl_seconds: int = DEFAULT_THREAD_CACHE_TTL,
    ) -> None:
        self._redis = redis_client
        self._ttl = ttl_seconds

    def _key(self, thread_uuid: str) -> str:
        """Build deterministic Redis key for a thread."""
        return f"slack:thread:{thread_uuid}:context"

    async def get_thread_context(
        self,
        thread_uuid: str,
    ) -> dict[str, Any] | None:
        """
        Retrieve cached thread context from Redis.

        Returns:
            Cached context dict if found, None on cache miss or Redis unavailable.
        """
        if not self._redis.is_available():
            return None

        try:
            raw = await self._redis.get(self._key(thread_uuid), raw=True)
            if raw is None:
                logger.debug(
                    "slack_thread_cache_miss",
                    thread_uuid=thread_uuid,
                )
                return None

            context = json.loads(raw)
            logger.debug(
                "slack_thread_cache_hit",
                thread_uuid=thread_uuid,
                packet_count=len(context.get("packets", [])),
            )
            return context

        except (json.JSONDecodeError, TypeError) as e:
            logger.warning(
                "slack_thread_cache_corrupt",
                thread_uuid=thread_uuid,
                error=str(e),
            )
            # Invalidate corrupted entry
            await self.invalidate_thread(thread_uuid)
            return None
        except Exception as e:
            logger.warning(
                "slack_thread_cache_get_error",
                thread_uuid=thread_uuid,
                error=str(e),
            )
            return None

    async def set_thread_context(
        self,
        thread_uuid: str,
        context: dict[str, Any],
    ) -> bool:
        """
        Populate cache with thread context (from PostgreSQL query result).

        Called after a cache miss + successful PostgreSQL fetch.

        Args:
            thread_uuid: Thread identifier.
            context: Context dict (must contain "packets" key).

        Returns:
            True if cached, False on failure or Redis unavailable.
        """
        if not self._redis.is_available():
            return False

        try:
            # Add cache metadata
            context["_cached_at"] = datetime.now(tz=UTC).isoformat()
            context["_ttl_seconds"] = self._ttl

            serialized = json.dumps(context, default=str)
            result = await self._redis.set(
                self._key(thread_uuid),
                serialized,
                ttl=self._ttl,
                raw=True,
            )
            logger.debug(
                "slack_thread_cache_set",
                thread_uuid=thread_uuid,
                packet_count=len(context.get("packets", [])),
            )
            return result

        except Exception as e:
            logger.warning(
                "slack_thread_cache_set_error",
                thread_uuid=thread_uuid,
                error=str(e),
            )
            return False

    async def append_to_thread(
        self,
        thread_uuid: str,
        packet_summary: dict[str, Any],
    ) -> bool:
        """
        Append a packet summary to the cached thread context.

        Used for:
        - Write-ahead: append inbound message before agent routing
        - Write-through: append stored packet after substrate write

        This fixes the race condition where message N+1 arrives before
        message N has been ingested into PostgreSQL.

        Args:
            thread_uuid: Thread identifier.
            packet_summary: Dict with at minimum {"text": ..., "user_id": ..., "ts": ...}.

        Returns:
            True if appended, False on failure or Redis unavailable.
        """
        if not self._redis.is_available():
            return False

        try:
            # Get current cached context
            current = await self.get_thread_context(thread_uuid)

            if current is None:
                # No existing cache — create new entry with this packet
                current = {"packets": []}

            packets = current.get("packets", [])

            # Add timestamp to packet summary
            packet_summary["_appended_at"] = datetime.now(tz=UTC).isoformat()
            packets.append(packet_summary)

            # Enforce bounded size (keep most recent)
            if len(packets) > MAX_CACHED_PACKETS_PER_THREAD:
                packets = packets[-MAX_CACHED_PACKETS_PER_THREAD:]

            current["packets"] = packets
            result = await self.set_thread_context(thread_uuid, current)

            logger.debug(
                "slack_thread_cache_append",
                thread_uuid=thread_uuid,
                total_packets=len(packets),
            )
            return result

        except Exception as e:
            logger.warning(
                "slack_thread_cache_append_error",
                thread_uuid=thread_uuid,
                error=str(e),
            )
            return False

    async def invalidate_thread(
        self,
        thread_uuid: str,
    ) -> bool:
        """
        Explicitly clear cached context for a thread.

        Used for:
        - Corrupted cache entries
        - Thread error threshold exceeded

        Args:
            thread_uuid: Thread identifier.

        Returns:
            True if deleted, False if not found or Redis unavailable.
        """
        if not self._redis.is_available():
            return False

        try:
            result = await self._redis.delete(self._key(thread_uuid))
            logger.debug(
                "slack_thread_cache_invalidated",
                thread_uuid=thread_uuid,
            )
            return result

        except Exception as e:
            logger.warning(
                "slack_thread_cache_invalidate_error",
                thread_uuid=thread_uuid,
                error=str(e),
            )
            return False


# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "MEM-OPER-003",
    "governance_level": "medium",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": ["runtime.redis_client"],
    "tags": [
        "async",
        "cache",
        "caching",
        "memory-substrate",
        "operations",
        "service",
    ],
    "keywords": [
        "append",
        "cache",
        "context",
        "invalidate",
        "slack",
        "thread",
    ],
    "business_value": "Eliminates per-message PostgreSQL queries for Slack thread context and fixes write-read race condition",
    "last_modified": "2026-02-12T21:38:00Z",
    "modified_by": "L9_Codegen_Engine",
    "change_summary": "Initial creation — Redis cache for Slack thread context",
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
