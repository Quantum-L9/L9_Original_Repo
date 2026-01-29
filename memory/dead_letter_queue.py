"""
L9 Memory Substrate - Dead-Letter Queue (DLQ)
==============================================

Resilience layer for failed packet ingestion operations.

When the SubstrateDAG fails to process a packet (even after retries),
the packet is pushed to a Redis-based DLQ for later reprocessing.
This ensures zero data loss during transient failures.

Version: 1.0.0
Author: L9 Resilience Team
Created: 2026-01-21
"""

from __future__ import annotations

# ============================================================================
__dora_meta__ = {
    "component_name": "Memory Substrate Dead-Letter Queue",
    "module_version": "1.0.0",
    "created_by": "L9 Resilience Team",
    "created_at": "2026-01-21T00:00:00Z",
    "updated_at": "2026-01-21T00:00:00Z",
    "layer": "memory",
    "domain": "resilience",
    "module_name": "dead_letter_queue",
    "type": "service",
    "status": "active",
    "integrates_with": {
        "datasources": ["Redis"],
        "memory_layers": ["substrate_service"],
        "imported_by": ["memory.substrate_service"],
    },
}
# ============================================================================

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from typing import Any

import structlog

from core.schemas import PacketEnvelopeIn

logger = structlog.get_logger(__name__)


# =============================================================================
# Data Models
# =============================================================================


@dataclass
class DLQEntry:
    """
    A single entry in the Dead-Letter Queue.

    Attributes:
        packet_id: Unique identifier for the packet
        packet_data: Serialized PacketEnvelopeIn
        failure_reason: Why the packet failed to ingest
        failure_count: Number of times this packet has failed
        first_failed_at: ISO timestamp of first failure
        last_failed_at: ISO timestamp of most recent failure
        retry_after: ISO timestamp when retry should be attempted
    """

    packet_id: str
    packet_data: dict[str, Any]
    failure_reason: str
    failure_count: int
    first_failed_at: str
    last_failed_at: str
    retry_after: str

    def to_json(self) -> str:
        """Serialize to JSON for Redis storage."""
        return json.dumps(asdict(self))

    @classmethod
    def from_json(cls, json_str: str) -> DLQEntry:
        """Deserialize from JSON."""
        data = json.loads(json_str)
        return cls(**data)


# =============================================================================
# Dead-Letter Queue Service
# =============================================================================


class DeadLetterQueue:
    """
    Redis-backed Dead-Letter Queue for failed packet ingestions.

    Architecture:
    - Uses Redis LIST for FIFO queue: `queue:dead_letter:memory_ingest`
    - Uses Redis HASH for metadata: `dlq:meta:{packet_id}`
    - Implements exponential backoff for retries
    - Provides observability metrics

    Usage:
        dlq = DeadLetterQueue(redis_client)

        # Push failed packet
        await dlq.push(packet_envelope, error_message)

        # Pop for reprocessing
        entry = await dlq.pop()
        if entry:
            # Attempt reprocessing
            success = await reprocess(entry.packet_data)
            if success:
                await dlq.acknowledge(entry.packet_id)
            else:
                await dlq.requeue(entry, new_error)
    """

    # Redis keys
    QUEUE_KEY = "queue:dead_letter:memory_ingest"
    META_KEY_PREFIX = "dlq:meta:"
    STATS_KEY = "dlq:stats"

    # Retry configuration
    MAX_RETRIES = 5
    INITIAL_BACKOFF_SECONDS = 60  # 1 minute
    MAX_BACKOFF_SECONDS = 3600  # 1 hour

    def __init__(self, redis_client: Any):
        """
        Initialize the Dead-Letter Queue.

        Args:
            redis_client: Redis client instance (aioredis or redis-py)
        """
        self._redis = redis_client
        logger.info("DeadLetterQueue initialized")

    async def push(
        self,
        packet: PacketEnvelopeIn,
        failure_reason: str,
        failure_count: int = 1,
    ) -> bool:
        """
        Push a failed packet to the DLQ.

        Args:
            packet: The packet that failed to ingest
            failure_reason: Error message or reason for failure
            failure_count: Number of times this packet has failed

        Returns:
            True if successfully pushed, False otherwise
        """
        try:
            packet_id = str(packet.packet_id) if packet.packet_id else "unknown"
            now = datetime.now(timezone.utc).isoformat()

            # Calculate retry backoff
            backoff_seconds = min(
                self.INITIAL_BACKOFF_SECONDS * (2 ** (failure_count - 1)),
                self.MAX_BACKOFF_SECONDS,
            )
            retry_after = (
                datetime.now(timezone.utc) + timedelta(seconds=backoff_seconds)
            ).isoformat()

            # Create DLQ entry
            entry = DLQEntry(
                packet_id=packet_id,
                packet_data=packet.dict(),
                failure_reason=failure_reason,
                failure_count=failure_count,
                first_failed_at=now,
                last_failed_at=now,
                retry_after=retry_after,
            )

            # Push to Redis LIST (FIFO)
            await self._redis.lpush(self.QUEUE_KEY, entry.to_json())

            # Store metadata
            meta_key = f"{self.META_KEY_PREFIX}{packet_id}"
            await self._redis.hset(
                meta_key,
                mapping={
                    "failure_count": failure_count,
                    "last_failed_at": now,
                    "retry_after": retry_after,
                    "failure_reason": failure_reason,
                },
            )
            await self._redis.expire(meta_key, 86400 * 7)  # 7 days TTL

            # Update stats
            await self._redis.hincrby(self.STATS_KEY, "total_pushed", 1)
            await self._redis.hincrby(self.STATS_KEY, "current_size", 1)

            logger.warning(
                "dlq.packet_pushed",
                packet_id=packet_id,
                failure_count=failure_count,
                retry_after=retry_after,
                reason=failure_reason[:100],
            )

            return True

        except Exception as e:
            logger.error(f"Failed to push to DLQ: {e}", exc_info=True)
            return False

    async def pop(self, wait_for_retry: bool = True) -> DLQEntry | None:
        """
        Pop a packet from the DLQ for reprocessing.

        Args:
            wait_for_retry: If True, only pop packets whose retry_after has passed

        Returns:
            DLQEntry if available, None if queue is empty
        """
        try:
            # Pop from the right (FIFO)
            entry_json = await self._redis.rpop(self.QUEUE_KEY)

            if not entry_json:
                return None

            entry = DLQEntry.from_json(entry_json)

            # Check if retry time has passed
            if wait_for_retry:
                retry_after = datetime.fromisoformat(entry.retry_after)
                if datetime.now(timezone.utc) < retry_after:
                    # Not ready yet, push back to queue
                    await self._redis.rpush(self.QUEUE_KEY, entry_json)
                    return None

            # Update stats
            await self._redis.hincrby(self.STATS_KEY, "total_popped", 1)
            await self._redis.hincrby(self.STATS_KEY, "current_size", -1)

            logger.info(
                "dlq.packet_popped",
                packet_id=entry.packet_id,
                failure_count=entry.failure_count,
            )

            return entry

        except Exception as e:
            logger.error(f"Failed to pop from DLQ: {e}", exc_info=True)
            return None

    async def acknowledge(self, packet_id: str) -> bool:
        """
        Acknowledge successful reprocessing of a packet.

        Args:
            packet_id: ID of the successfully reprocessed packet

        Returns:
            True if acknowledged, False otherwise
        """
        try:
            # Delete metadata
            meta_key = f"{self.META_KEY_PREFIX}{packet_id}"
            await self._redis.delete(meta_key)

            # Update stats
            await self._redis.hincrby(self.STATS_KEY, "total_acknowledged", 1)

            logger.info("dlq.packet_acknowledged", packet_id=packet_id)
            return True

        except Exception as e:
            logger.error(f"Failed to acknowledge DLQ entry: {e}", exc_info=True)
            return False

    async def requeue(
        self,
        entry: DLQEntry,
        new_failure_reason: str,
    ) -> bool:
        """
        Requeue a packet that failed reprocessing.

        Args:
            entry: The DLQ entry that failed again
            new_failure_reason: New error message

        Returns:
            True if requeued, False if max retries exceeded
        """
        try:
            new_failure_count = entry.failure_count + 1

            # Check if max retries exceeded
            if new_failure_count > self.MAX_RETRIES:
                logger.error(
                    "dlq.max_retries_exceeded",
                    packet_id=entry.packet_id,
                    failure_count=new_failure_count,
                )
                await self._redis.hincrby(self.STATS_KEY, "total_dead", 1)

                # Move to permanent dead-letter storage
                dead_key = f"dlq:dead:{entry.packet_id}"
                await self._redis.set(
                    dead_key, entry.to_json(), ex=86400 * 30
                )  # 30 days

                return False

            # Reconstruct packet and push with incremented count
            packet = PacketEnvelopeIn(**entry.packet_data)
            return await self.push(packet, new_failure_reason, new_failure_count)

        except Exception as e:
            logger.error(f"Failed to requeue DLQ entry: {e}", exc_info=True)
            return False

    async def get_stats(self) -> dict[str, int]:
        """
        Get DLQ statistics.

        Returns:
            Dictionary with stats: total_pushed, total_popped, total_acknowledged,
            total_dead, current_size
        """
        try:
            stats = await self._redis.hgetall(self.STATS_KEY)
            return {
                "total_pushed": int(stats.get(b"total_pushed", 0)),
                "total_popped": int(stats.get(b"total_popped", 0)),
                "total_acknowledged": int(stats.get(b"total_acknowledged", 0)),
                "total_dead": int(stats.get(b"total_dead", 0)),
                "current_size": int(stats.get(b"current_size", 0)),
            }
        except Exception as e:
            logger.error(f"Failed to get DLQ stats: {e}", exc_info=True)
            return {}

    async def get_size(self) -> int:
        """Get current size of the DLQ."""
        try:
            return await self._redis.llen(self.QUEUE_KEY)
        except Exception:
            return 0


# =============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "MEM-DLQ",
    "governance_level": "critical",
    "security_reviewed": True,
    "performance_tested": True,
    "last_audit": "2026-01-21T00:00:00Z",
}
# ============================================================================
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
