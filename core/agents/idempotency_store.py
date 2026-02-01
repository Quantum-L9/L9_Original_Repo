"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Agent Executor - Substrate-Backed Idempotency (GMP Phase 0 Enhancement)
Purpose: Prevent duplicate task execution across restarts using Redis
Author: L9 Engineering
Date: 2026-01-29
Risk: T2 (internal enhancement, preserves public API)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Enhancement: Idempotency cache now persists in Redis substrate instead of
in-memory dict. This prevents duplicate task execution after server restarts.

Public API unchanged - existing PacketEnvelope semantics preserved.
"""

from __future__ import annotations

import structlog
import hashlib
import json
from datetime import timedelta
from typing import TYPE_CHECKING, Optional, Dict, Any, Protocol

from core.schemas.packet_envelope import PacketEnvelope

if TYPE_CHECKING:
    from redis.asyncio import Redis


class SubstrateServiceProtocol(Protocol):
    """Protocol for substrate service providing Redis access."""

    async def get_redis_client(self) -> Redis:
        """Get async Redis client."""
        ...


logger = structlog.get_logger(__name__)


class IdempotencyStore:
    """
    Substrate-backed idempotency tracker for agent task execution.

    Uses Redis with TTL-based expiration to prevent unbounded growth.
    Idempotency keys are SHA256 hashes of task content for uniqueness.

    TTL Strategy:
    - Default: 24 hours (tasks older than this can re-execute)
    - Configurable via IDEMPOTENCY_TTL_HOURS env var
    - Production recommendation: 7 days for long-running workflows
    """

    # Redis key prefix for namespacing
    KEY_PREFIX = "l9:idempotency:"

    # Default TTL: 24 hours
    DEFAULT_TTL = timedelta(hours=24)

    def __init__(
        self, substrate: SubstrateServiceProtocol, ttl: Optional[timedelta] = None
    ):
        """
        Initialize idempotency store.

        Args:
            substrate: L9 substrate service with Redis access
            ttl: Time-to-live for idempotency entries (default: 24h)
        """
        self.substrate = substrate
        self.ttl = ttl or self.DEFAULT_TTL
        self._redis = None  # Lazy-loaded

    async def _get_redis(self):
        """Lazy-load Redis client from substrate."""
        if self._redis is None:
            self._redis = await self.substrate.get_redis_client()
        return self._redis

    def _compute_key(self, packet: PacketEnvelope) -> str:
        """
        Compute idempotency key from packet content.

        Key is SHA256 hash of:
        - packet.packet_type
        - packet.payload (JSON serialized)
        - packet.provenance.source_agent (if present)

        This ensures identical tasks from same agent are deduplicated.

        Args:
            packet: Task packet

        Returns:
            Redis key string (prefixed)
        """
        # Serialize packet content deterministically
        source_agent = None
        if packet.provenance and packet.provenance.source_agent:
            source_agent = packet.provenance.source_agent

        content = {
            "packet_type": packet.packet_type,
            "payload": packet.payload,
            "source_agent": source_agent,
        }
        content_bytes = json.dumps(content, sort_keys=True, default=str).encode("utf-8")

        # Compute SHA256 hash
        hash_digest = hashlib.sha256(content_bytes).hexdigest()

        # Return prefixed key
        return f"{self.KEY_PREFIX}{hash_digest}"

    async def mark_executed(
        self, packet: PacketEnvelope, result: Dict[str, Any]
    ) -> None:
        """
        Mark task as executed with result.

        Stores execution timestamp and result summary in Redis with TTL.

        Args:
            packet: Task packet
            result: Execution result metadata
        """
        try:
            redis = await self._get_redis()
            key = self._compute_key(packet)

            # Store execution record with TTL
            record = {
                "executed_at": result.get("timestamp"),
                "status": result.get("status", "success"),
                "packet_id": str(packet.packet_id),
            }

            await redis.setex(key, self.ttl, json.dumps(record))

            logger.debug(f"Marked task as executed: {key} (TTL: {self.ttl})")

        except Exception as e:
            # Non-critical error - log but don't fail execution
            logger.warning(f"Failed to mark task as executed: {e}")

    async def check_executed(self, packet: PacketEnvelope) -> bool:
        """
        Check if task has already been executed.

        Args:
            packet: Task packet

        Returns:
            True if task was previously executed (within TTL window), False otherwise
        """
        try:
            redis = await self._get_redis()
            key = self._compute_key(packet)

            # Check if key exists in Redis
            exists = await redis.exists(key)

            if exists:
                logger.info(f"Task already executed (idempotent): {key}")
                return True

            return False

        except Exception as e:
            # Non-critical error - assume not executed to be safe
            logger.warning(f"Idempotency check failed, assuming not executed: {e}")
            return False

    async def get_execution_record(
        self, packet: PacketEnvelope
    ) -> Optional[Dict[str, Any]]:
        """
        Retrieve execution record for previously executed task.

        Args:
            packet: Task packet

        Returns:
            Execution record dict if found, None otherwise
        """
        try:
            redis = await self._get_redis()
            key = self._compute_key(packet)

            record_json = await redis.get(key)

            if record_json:
                return json.loads(record_json)

            return None

        except Exception as e:
            logger.warning(f"Failed to retrieve execution record: {e}")
            return None

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # Key-based methods for AgentTask integration
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    async def check_executed_by_key(self, dedupe_key: str) -> bool:
        """
        Check if task has already been executed using a pre-computed key.

        Args:
            dedupe_key: Pre-computed idempotency key (e.g., from AgentTask.get_dedupe_key())

        Returns:
            True if task was previously executed (within TTL window), False otherwise
        """
        try:
            redis = await self._get_redis()
            key = f"{self.KEY_PREFIX}{dedupe_key}"

            exists = await redis.exists(key)

            if exists:
                logger.info(f"Task already executed (idempotent): {key}")
                return True

            return False

        except Exception as e:
            logger.warning(f"Idempotency check failed, assuming not executed: {e}")
            return False

    async def mark_executed_by_key(
        self, dedupe_key: str, result: Dict[str, Any]
    ) -> None:
        """
        Mark task as executed using a pre-computed key.

        Args:
            dedupe_key: Pre-computed idempotency key
            result: Execution result metadata
        """
        try:
            redis = await self._get_redis()
            key = f"{self.KEY_PREFIX}{dedupe_key}"

            record = {
                "executed_at": result.get("timestamp"),
                "status": result.get("status", "success"),
                "task_id": result.get("task_id"),
            }

            await redis.setex(key, self.ttl, json.dumps(record))

            logger.debug(f"Marked task as executed: {key} (TTL: {self.ttl})")

        except Exception as e:
            logger.warning(f"Failed to mark task as executed: {e}")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Integration point: Replace in-memory cache in AgentExecutorService
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# BEFORE (in-memory, cleared on restart):
# self._idempotency_cache: Dict[str, Any] = {}

# AFTER (substrate-backed, persists across restarts):
# self._idempotency_store = IdempotencyStore(substrate_service)

# Usage in execute_task method:
#
# async def execute_task(self, packet: PacketEnvelope) -> Dict[str, Any]:
#     # Check idempotency
#     if await self._idempotency_store.check_executed(packet):
#         existing_record = await self._idempotency_store.get_execution_record(packet)
#         logger.info(f"Skipping duplicate task: {packet.packet_id}")
#         return existing_record or {"status": "skipped", "reason": "duplicate"}
#
#     # Execute task
#     result = await self._execute_internal(packet)
#
#     # Mark as executed
#     await self._idempotency_store.mark_executed(packet, result)
#
#     return result
