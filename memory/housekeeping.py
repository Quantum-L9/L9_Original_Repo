"""
L9 Memory Substrate - Housekeeping Engine
Version: 1.1.0

Implements automated memory hygiene operations:
- TTL eviction for expired packets
- Tag-based garbage collection
- Orphan packet cleanup (parentless, dangling references)
- Artifact orphan cleanup

All operations are async-safe and use logging (no print statements).
"""

from __future__ import annotations

from core.decorators import must_stay_async
from core.singleton_auto_registry import register_singleton

# ============================================================================
__dora_meta__ = {
    "component_name": "Housekeeping Engine",
    "module_version": "1.1.0",
    "created_by": "Igor Beylin",
    "created_at": "2025-12-09T01:02:49Z",
    "updated_at": "2026-01-13T15:36:11Z",
    "layer": "learning",
    "domain": "memory_substrate",
    "module_name": "housekeeping",
    "type": "service",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": [],
        "memory_layers": ["semantic_memory"],
        "imported_by": [
            "api.memory.router",
            "api.server",
            "core.singleton_registry",
            "memory.__init__",
        ],
    },
}
# ============================================================================

from datetime import UTC, datetime, timedelta
from functools import lru_cache
from typing import TYPE_CHECKING, Any

import structlog

if TYPE_CHECKING:
    from memory.substrate_repository import SubstrateRepository

logger = structlog.get_logger(__name__)


class HousekeepingEngine:
    """
    Memory housekeeping engine for garbage collection and hygiene.

    Provides async methods for cleaning up expired, orphaned,
    and unreferenced memory artifacts.
    """

    def __init__(self, repository: SubstrateRepository | None = None):
        """
        Initialize housekeeping engine.

        Args:
            repository: SubstrateRepository instance (injected)
        """
        self._repository = repository
        self._last_run: datetime | None = None
        self._stats: dict[str, int] = {
            "ttl_evicted": 0,
            "orphans_cleaned": 0,
            "tags_gc": 0,
            "artifacts_cleaned": 0,
        }
        logger.info("HousekeepingEngine initialized")

    def set_repository(self, repository: SubstrateRepository) -> None:
        """Set or update the repository reference."""
        self._repository = repository

    @property
    def stats(self) -> dict[str, int]:
        """Return current housekeeping statistics."""
        return self._stats.copy()

    @must_stay_async("callers use await")
    async def run_full_gc(self) -> dict[str, Any]:
        """
        Run full garbage collection cycle.

        Executes all housekeeping operations in order:
        1. TTL eviction
        2. Orphan packet cleanup
        3. Parentless packet cleanup
        4. Artifact orphan cleanup
        5. Tag garbage collection

        Returns:
            Summary dict with counts of cleaned items
        """
        logger.info("Starting full garbage collection cycle")

        if self._repository is None:
            logger.warning("No repository set, skipping GC")
            return {"status": "skipped", "reason": "no_repository"}

        results = {
            "ttl_evicted": 0,
            "orphans_cleaned": 0,
            "parentless_cleaned": 0,
            "artifacts_cleaned": 0,
            "tags_gc": 0,
            "errors": [],
        }

        # TTL eviction
        try:
            count = await self.evict_expired_ttl()
            results["ttl_evicted"] = count
        except Exception as e:
            logger.error(f"TTL eviction failed: {e}")
            results["errors"].append(f"ttl_eviction: {e!s}")

        # Orphan cleanup
        try:
            count = await self.cleanup_orphan_packets()
            results["orphans_cleaned"] = count
        except Exception as e:
            logger.error(f"Orphan cleanup failed: {e}")
            results["errors"].append(f"orphan_cleanup: {e!s}")

        # Parentless cleanup
        try:
            count = await self.cleanup_parentless_packets()
            results["parentless_cleaned"] = count
        except Exception as e:
            logger.error(f"Parentless cleanup failed: {e}")
            results["errors"].append(f"parentless_cleanup: {e!s}")

        # Artifact cleanup
        try:
            count = await self.cleanup_orphan_artifacts()
            results["artifacts_cleaned"] = count
        except Exception as e:
            logger.error(f"Artifact cleanup failed: {e}")
            results["errors"].append(f"artifact_cleanup: {e!s}")

        # Tag GC
        try:
            count = await self.gc_unused_tags()
            results["tags_gc"] = count
        except Exception as e:
            logger.error(f"Tag GC failed: {e}")
            results["errors"].append(f"tag_gc: {e!s}")

        # Update stats
        self._stats["ttl_evicted"] += results["ttl_evicted"]
        self._stats["orphans_cleaned"] += (
            results["orphans_cleaned"] + results["parentless_cleaned"]
        )
        self._stats["tags_gc"] += results["tags_gc"]
        self._stats["artifacts_cleaned"] += results["artifacts_cleaned"]
        self._last_run = datetime.now(UTC)

        total_cleaned = sum(v for k, v in results.items() if isinstance(v, int))
        logger.info(f"GC cycle complete: {total_cleaned} items cleaned")

        return {
            "status": "ok" if not results["errors"] else "partial",
            "cleaned": results,
            "timestamp": datetime.now(UTC).isoformat(),
        }

    async def evict_expired_ttl(self) -> int:
        """
        Evict packets with expired TTL.

        Deletes packets where ttl < now().

        Returns:
            Count of evicted packets
        """
        logger.debug("Running TTL eviction")

        async with self._repository.acquire() as conn:
            # Delete expired packets
            result = await conn.execute("""
                DELETE FROM packet_store
                WHERE ttl IS NOT NULL AND ttl < NOW()
                """)

            # Parse count from result
            count = int(result.split()[-1]) if result else 0

            if count > 0:
                logger.info(f"TTL eviction: removed {count} expired packets")

            return count

    async def cleanup_orphan_packets(self) -> int:
        """
        Clean up orphan packets with invalid references.

        Identifies packets referencing non-existent parent packets
        and either removes them or clears their parent references.

        Returns:
            Count of cleaned packets
        """
        logger.debug("Running orphan packet cleanup")

        async with self._repository.acquire() as conn:
            # Find packets with parent_ids referencing non-existent packets
            # Clear orphan references rather than deleting packets
            result = await conn.execute("""
                UPDATE packet_store p
                SET parent_ids = ARRAY(
                    SELECT unnest(p.parent_ids)
                    INTERSECT
                    SELECT packet_id FROM packet_store
                )
                WHERE parent_ids IS NOT NULL
                AND array_length(parent_ids, 1) > 0
                AND EXISTS (
                    SELECT 1 FROM unnest(p.parent_ids) AS parent_id
                    WHERE parent_id NOT IN (SELECT packet_id FROM packet_store)
                )
                """)

            count = int(result.split()[-1]) if result else 0

            if count > 0:
                logger.info(
                    f"Orphan cleanup: fixed {count} packets with invalid parent refs"
                )

            return count

    @must_stay_async("callers use await")
    async def cleanup_parentless_packets(
        self,
        max_age_hours: int = 72,
        exclude_types: list[str] | None = None,
    ) -> int:
        """
        Clean up old parentless packets that appear abandoned.

        Removes packets that:
        - Have no parent_ids
        - Are older than max_age_hours
        - Are not root packets (packet_type not in exclude_types)

        Args:
            max_age_hours: Age threshold in hours
            exclude_types: Packet types to exclude (roots)

        Returns:
            Count of cleaned packets
        """
        logger.debug(f"Running parentless cleanup (max_age={max_age_hours}h)")

        exclude_types = exclude_types or ["root", "session_start", "thread_start"]

        async with self._repository.acquire() as conn:
            cutoff = datetime.now(UTC) - timedelta(hours=max_age_hours)

            result = await conn.execute(
                """
                DELETE FROM packet_store
                WHERE (parent_ids IS NULL OR array_length(parent_ids, 1) = 0)
                AND timestamp < $1
                AND packet_type != ALL($2)
                AND thread_id IS NULL
                """,
                cutoff,
                exclude_types,
            )

            count = int(result.split()[-1]) if result else 0

            if count > 0:
                logger.info(f"Parentless cleanup: removed {count} abandoned packets")

            return count

    async def cleanup_orphan_artifacts(self) -> int:
        """
        Clean up orphan artifacts (embeddings, events) with no source packet.

        Removes:
        - Semantic embeddings with no matching packet
        - Memory events with invalid packet references

        Returns:
            Count of cleaned artifacts
        """
        logger.debug("Running artifact orphan cleanup")

        total_cleaned = 0

        async with self._repository.acquire() as conn:
            # Clean orphan semantic embeddings
            result = await conn.execute("""
                DELETE FROM semantic_memory sm
                WHERE EXISTS (
                    SELECT 1 FROM jsonb_extract_path_text(sm.payload::jsonb, 'packet_id') AS pid
                    WHERE pid IS NOT NULL
                    AND pid::uuid NOT IN (SELECT packet_id FROM packet_store)
                )
                """)
            embed_count = int(result.split()[-1]) if result else 0
            total_cleaned += embed_count

            # Clean orphan memory events
            result = await conn.execute("""
                DELETE FROM agent_memory_events
                WHERE packet_id IS NOT NULL
                AND packet_id NOT IN (SELECT packet_id FROM packet_store)
                """)
            event_count = int(result.split()[-1]) if result else 0
            total_cleaned += event_count

            # Clean orphan knowledge facts
            result = await conn.execute("""
                DELETE FROM knowledge_facts
                WHERE source_packet IS NOT NULL
                AND source_packet NOT IN (SELECT packet_id FROM packet_store)
                """)
            fact_count = int(result.split()[-1]) if result else 0
            total_cleaned += fact_count

        if total_cleaned > 0:
            logger.info(f"Artifact cleanup: removed {total_cleaned} orphan artifacts")

        return total_cleaned

    async def gc_unused_tags(self, min_usage: int = 1) -> int:
        """
        Garbage collect unused or low-usage tags.

        Removes tags that appear on fewer than min_usage packets.

        Args:
            min_usage: Minimum usage count to keep a tag

        Returns:
            Count of tags removed from packets
        """
        logger.debug(f"Running tag GC (min_usage={min_usage})")

        async with self._repository.acquire() as conn:
            # Get tag usage counts
            rows = await conn.fetch(
                """
                SELECT tag, COUNT(*) as usage
                FROM packet_store, UNNEST(tags) AS tag
                GROUP BY tag
                HAVING COUNT(*) < $1
                """,
                min_usage,
            )

            if not rows:
                return 0

            low_usage_tags = [r["tag"] for r in rows]

            # Remove low-usage tags from packets
            result = await conn.execute(
                """
                UPDATE packet_store
                SET tags = array_remove(tags, ANY($1))
                WHERE tags && $1
                """,
                low_usage_tags,
            )

            count = int(result.split()[-1]) if result else 0

            if count > 0:
                logger.info(
                    f"Tag GC: cleaned {len(low_usage_tags)} low-usage tags from {count} packets"
                )

            return count

    async def get_gc_stats(self) -> dict[str, Any]:
        """
        Get garbage collection statistics.

        Returns:
            Dict with GC stats and counts of cleanable items
        """
        if self._repository is None:
            return {"status": "no_repository"}

        async with self._repository.acquire() as conn:
            # Count expired TTL packets
            expired_ttl = await conn.fetchval(
                "SELECT COUNT(*) FROM packet_store WHERE ttl IS NOT NULL AND ttl < NOW()"
            )

            # Count orphan references
            orphan_refs = await conn.fetchval("""
                SELECT COUNT(*) FROM packet_store p
                WHERE parent_ids IS NOT NULL
                AND array_length(parent_ids, 1) > 0
                AND EXISTS (
                    SELECT 1 FROM unnest(p.parent_ids) AS parent_id
                    WHERE parent_id NOT IN (SELECT packet_id FROM packet_store)
                )
                """)

            # Count total packets
            total_packets = await conn.fetchval("SELECT COUNT(*) FROM packet_store")

            # Count total embeddings
            total_embeddings = await conn.fetchval(
                "SELECT COUNT(*) FROM semantic_memory"
            )

        return {
            "last_run": self._last_run.isoformat() if self._last_run else None,
            "lifetime_stats": self._stats,
            "pending": {
                "expired_ttl": expired_ttl or 0,
                "orphan_refs": orphan_refs or 0,
            },
            "totals": {
                "packets": total_packets or 0,
                "embeddings": total_embeddings or 0,
            },
        }


# =============================================================================
# Singleton / Factory
# =============================================================================


@lru_cache(maxsize=1)
@register_singleton(
    name="housekeeping_engine",
    lifecycle="lazy",
    description="Memory housekeeping engine for cleanup and optimization",
)
def get_housekeeping_engine() -> HousekeepingEngine:
    """Get or create the housekeeping engine singleton. CACHED."""
    return HousekeepingEngine()


def init_housekeeping_engine(repository: SubstrateRepository) -> HousekeepingEngine:
    """Initialize the housekeeping engine with a repository."""
    engine = get_housekeeping_engine()
    engine.set_repository(repository)
    return engine


# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "MEM-LEAR-028",
    "governance_level": "critical",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": [
        "async",
        "caching",
        "debugging",
        "engine",
        "event-driven",
        "learning",
        "logging",
        "memory-substrate",
        "serialization",
        "service",
    ],
    "keywords": [
        "artifacts",
        "cleanup",
        "engine",
        "evict",
        "expired",
        "full",
        "housekeeping",
        "memory",
    ],
    "business_value": "TTL eviction for expired packets Tag-based garbage collection Orphan packet cleanup (parentless, dangling references) Artifact orphan cleanup All operations are async-safe and use logging (no print st",
    "last_modified": "2026-01-13T15:36:11Z",
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
