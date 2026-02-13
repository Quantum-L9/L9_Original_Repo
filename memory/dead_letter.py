"""
L9 Memory Substrate - Dead Letter Queue
Version: 1.0.0

Redis Stream-based dead letter queue for failed packet ingestion.
Supports: enqueue, peek, replay, acknowledge, depth queries.

GMP-88: Core Resilience for SubstrateDagOrchestrator
"""

from __future__ import annotations

# ============================================================================
__dora_meta__ = {
    "component_name": "Dead Letter Queue",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2026-01-17T14:57:53Z",
    "updated_at": "2026-01-17T23:47:56Z",
    "layer": "learning",
    "domain": "memory_substrate",
    "module_name": "dead_letter",
    "type": "dataclass",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": ["Redis"],
        "memory_layers": [],
        "imported_by": [
            "memory.substrate_dag_wrapper",
            "tests.memory.test_dag_orchestrator_resilience",
        ],
    },
}
# ============================================================================

import json
from dataclasses import dataclass
from datetime import UTC, datetime, timezone
from typing import Any

import structlog

logger = structlog.get_logger(__name__)

STREAM_KEY = "l9:memory:dlq"
CONSUMER_GROUP = "dlq_processors"


@dataclass
class DeadLetterEntry:
    """Entry in the dead letter queue."""

    entry_id: str  # Redis stream ID
    packet_id: str
    packet_type: str
    payload: dict[str, Any]
    error_message: str
    error_type: str
    attempts: int
    failed_at: str
    original_envelope: dict[str, Any]


class DeadLetterQueue:
    """
    Redis Stream-based dead letter queue for failed packets.

    Packets that fail after retry exhaustion are stored here for:
    - Manual investigation
    - Replay after fix
    - Audit trail
    """

    def __init__(self, redis_client, stream_key: str = STREAM_KEY):
        """
        Initialize DLQ.

        Args:
            redis_client: Redis client instance (async)
            stream_key: Redis stream key for DLQ
        """
        self._redis = redis_client
        self._stream_key = stream_key
        logger.info("DeadLetterQueue initialized", stream_key=stream_key)

    async def enqueue(
        self,
        envelope: dict[str, Any],
        error: Exception | str,
        attempts: int,
    ) -> str:
        """
        Add failed packet to dead letter queue.

        Args:
            envelope: Original envelope as dict
            error: Exception or error string
            attempts: Number of attempts made

        Returns:
            Redis stream entry ID
        """
        packet_id = envelope.get("packet_id", "unknown")

        entry = {
            "packet_id": str(packet_id),
            "packet_type": envelope.get("packet_type", "unknown"),
            "payload": json.dumps(envelope.get("payload", {})),
            "error_message": str(error),
            "error_type": (
                type(error).__name__ if isinstance(error, Exception) else "string"
            ),
            "attempts": str(attempts),
            "failed_at": datetime.now(UTC).isoformat(),
            "original_envelope": json.dumps(envelope),
        }

        entry_id = await self._redis.xadd(self._stream_key, entry)

        logger.warning(
            "Packet added to dead letter queue",
            packet_id=packet_id,
            entry_id=entry_id,
            error=str(error)[:200],
            attempts=attempts,
        )

        return entry_id

    async def depth(self) -> int:
        """Return number of entries in DLQ."""
        return await self._redis.xlen(self._stream_key)

    async def peek(self, count: int = 10) -> list[DeadLetterEntry]:
        """
        Peek at oldest entries without removing.

        Args:
            count: Maximum entries to return

        Returns:
            List of DeadLetterEntry objects
        """
        entries = await self._redis.xrange(self._stream_key, count=count)
        return [self._parse_entry(eid, data) for eid, data in entries]

    async def acknowledge(self, entry_id: str) -> bool:
        """
        Remove entry after successful replay.

        Args:
            entry_id: Redis stream entry ID

        Returns:
            True if entry was deleted
        """
        deleted = await self._redis.xdel(self._stream_key, entry_id)
        if deleted > 0:
            logger.info("DLQ entry acknowledged and removed", entry_id=entry_id)
        return deleted > 0

    async def get_entry(self, entry_id: str) -> DeadLetterEntry | None:
        """
        Get specific entry by ID.

        Args:
            entry_id: Redis stream entry ID

        Returns:
            DeadLetterEntry if found, None otherwise
        """
        entries = await self._redis.xrange(self._stream_key, min=entry_id, max=entry_id)
        if entries:
            eid, data = entries[0]
            return self._parse_entry(eid, data)
        return None

    def _parse_entry(self, entry_id: str, data: dict) -> DeadLetterEntry:
        """Parse Redis stream entry to DeadLetterEntry."""
        return DeadLetterEntry(
            entry_id=entry_id,
            packet_id=data.get("packet_id", ""),
            packet_type=data.get("packet_type", ""),
            payload=json.loads(data.get("payload", "{}")),
            error_message=data.get("error_message", ""),
            error_type=data.get("error_type", ""),
            attempts=int(data.get("attempts", 0)),
            failed_at=data.get("failed_at", ""),
            original_envelope=json.loads(data.get("original_envelope", "{}")),
        )


# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "MEM-LEAR-046",
    "governance_level": "critical",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": [
        "async",
        "dataclass",
        "learning",
        "logging",
        "memory-substrate",
        "messaging",
        "queue",
        "serialization",
        "streaming",
    ],
    "keywords": [
        "acknowledge",
        "dead",
        "depth",
        "enqueue",
        "entry",
        "letter",
        "memory",
        "peek",
    ],
    "business_value": "Provides dead letter components including DeadLetterEntry, DeadLetterQueue",
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
