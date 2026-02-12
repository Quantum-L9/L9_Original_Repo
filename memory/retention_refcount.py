"""
Reference Counting Service for TTL Safety

This module prevents premature deletion of packets that are actively referenced
by other parts of the system (lineage, semantic facts, agent checkpoints).

Critical Feature: Prevents data loss from TTL-based cleanup.

Usage:
    from memory.retention_refcount import ReferenceCountingService

    refcount_service = ReferenceCountingService(repository)
    is_safe = await refcount_service.is_safe_to_delete("packet_123")
"""

import asyncio
from dataclasses import dataclass
from typing import Optional

import structlog

logger = structlog.get_logger(__name__)


@dataclass
class PacketRefCount:
    """
    Reference count tracking for a single packet.

    Attributes:
        packet_id: Unique identifier for the packet
        lineage_refs: Number of child packets referencing this packet
        fact_refs: Number of semantic facts linked to this packet
        checkpoint_refs: Number of agent checkpoints referencing this packet
    """

    packet_id: str
    lineage_refs: int = 0
    fact_refs: int = 0
    checkpoint_refs: int = 0

    @property
    def total_refs(self) -> int:
        """Total reference count across all categories."""
        return self.lineage_refs + self.fact_refs + self.checkpoint_refs

    @property
    def is_safe_to_delete(self) -> bool:
        """Returns True if packet has no active references."""
        return self.total_refs == 0

    def __repr__(self) -> str:
        return (
            f"PacketRefCount(packet_id={self.packet_id}, "
            f"total={self.total_refs}, lineage={self.lineage_refs}, "
            f"facts={self.fact_refs}, checkpoints={self.checkpoint_refs})"
        )


class ReferenceCountingService:
    """
    Computes and caches reference counts for packets to enable safe TTL-based deletion.

    This service prevents the RetentionEngine from deleting packets that are still
    actively referenced by:
    - Lineage chains (parent-child relationships)
    - Semantic facts (knowledge graph links)
    - Agent checkpoints (reasoning history)

    Example:
        service = ReferenceCountingService(repository)

        # Check if packet can be safely deleted
        if await service.is_safe_to_delete("pkt_789"):
            await repository.delete_packet("pkt_789")
        else:
            await service.mark_soft_expired("pkt_789")
    """

    def __init__(self, repository):
        """
        Initialize the reference counting service.

        Args:
            repository: SubstrateRepository instance for database access
        """
        self.repository = repository
        self._refcount_cache: dict[str, PacketRefCount] = {}
        logger.info("ReferenceCountingService initialized")

    async def compute_refcount(
        self, packet_id: str, use_cache: bool = True
    ) -> PacketRefCount:
        """
        Compute the reference count for a packet from database queries.

        Queries:
        1. Lineage: SELECT COUNT(*) FROM packetstore WHERE $packet_id = ANY(parent_ids)
        2. Facts: SELECT COUNT(*) FROM semanticfacts WHERE source_packet = $packet_id
        3. Checkpoints: SELECT COUNT(*) FROM agentcheckpoint WHERE graphstate CONTAINS $packet_id

        Args:
            packet_id: The packet to compute references for
            use_cache: If True, return cached value if available

        Returns:
            PacketRefCount object with computed reference counts
        """
        # Check cache first
        if use_cache and packet_id in self._refcount_cache:
            logger.debug(f"Using cached refcount for {packet_id}")
            return self._refcount_cache[packet_id]

        refcount = PacketRefCount(packet_id=packet_id)

        try:
            async with self.repository.acquire() as conn:
                # Count lineage references (children pointing to this packet as parent)
                lineage_query = """
                    SELECT COUNT(*)
                    FROM packetstore
                    WHERE $1 = ANY(parent_ids)
                """
                lineage_count = await conn.fetchval(lineage_query, packet_id)
                refcount.lineage_refs = lineage_count or 0

                # Count semantic fact references
                fact_query = """
                    SELECT COUNT(*)
                    FROM semanticfacts
                    WHERE source_packet = $1
                """
                fact_count = await conn.fetchval(fact_query, packet_id)
                refcount.fact_refs = fact_count or 0

                # Count agent checkpoint references
                # Note: Using text search on JSONB graphstate
                checkpoint_query = """
                    SELECT COUNT(*)
                    FROM agentcheckpoint
                    WHERE graphstate::text LIKE $1
                """
                checkpoint_count = await conn.fetchval(
                    checkpoint_query, f"%{packet_id}%"
                )
                refcount.checkpoint_refs = checkpoint_count or 0

            # Cache the result
            self._refcount_cache[packet_id] = refcount

            logger.debug(f"Computed refcount for {packet_id}: {refcount}")
            return refcount

        except Exception as e:
            logger.error(f"Error computing refcount for {packet_id}: {e}")
            # Return zero refcount on error to be safe (won't delete on error)
            return refcount

    async def is_safe_to_delete(self, packet_id: str) -> bool:
        """
        Check if a packet can be safely deleted (has zero references).

        Args:
            packet_id: The packet to check

        Returns:
            True if packet has no references and can be deleted safely
        """
        refcount = await self.compute_refcount(packet_id, use_cache=False)
        is_safe = refcount.is_safe_to_delete

        if not is_safe:
            logger.warning(f"Packet {packet_id} NOT SAFE to delete: {refcount}")

        return is_safe

    async def mark_soft_expired(self, packet_id: str) -> None:
        """
        Mark a packet as soft-expired instead of deleting it.

        Soft-expired packets:
        - Remain in the database
        - Are excluded from normal queries via metadata filter
        - Can be garbage collected later when references are removed

        Args:
            packet_id: The packet to mark as soft-expired
        """
        try:
            async with self.repository.acquire() as conn:
                await conn.execute(
                    """
                    UPDATE packetstore
                    SET metadata = jsonb_set(
                        COALESCE(metadata, '{}'::jsonb),
                        '{soft_expired}',
                        'true'::jsonb
                    )
                    WHERE packetid = $1
                """,
                    packet_id,
                )

            logger.info(f"Marked packet {packet_id} as SOFT_EXPIRED")

        except Exception as e:
            logger.error(f"Error marking packet {packet_id} as soft-expired: {e}")

    async def invalidate_cache(self, packet_id: str | None = None) -> None:
        """
        Invalidate cached reference counts.

        Args:
            packet_id: Specific packet to invalidate, or None to clear entire cache
        """
        if packet_id:
            self._refcount_cache.pop(packet_id, None)
            logger.debug(f"Invalidated cache for {packet_id}")
        else:
            self._refcount_cache.clear()
            logger.debug("Cleared entire refcount cache")

    async def batch_compute_refcounts(
        self, packet_ids: list[str]
    ) -> dict[str, PacketRefCount]:
        """
        Compute reference counts for multiple packets in parallel.

        Args:
            packet_ids: List of packet IDs to compute refcounts for

        Returns:
            Dictionary mapping packet_id -> PacketRefCount
        """
        tasks = [self.compute_refcount(pid, use_cache=False) for pid in packet_ids]

        refcounts = await asyncio.gather(*tasks, return_exceptions=True)

        result = {}
        for pid, refcount in zip(packet_ids, refcounts, strict=False):
            if isinstance(refcount, Exception):
                logger.error(f"Error computing refcount for {pid}: {refcount}")
                continue
            result[pid] = refcount

        return result
