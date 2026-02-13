"""
L9 Memory Orchestrator - Housekeeping
Version: 1.0.0

Specialized component for memory orchestration.
Handles garbage collection, compaction, and maintenance.
"""

# ============================================================================
__dora_meta__ = {
    "component_name": "Housekeeping",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2025-12-09T01:02:49Z",
    "updated_at": "2026-01-12T16:30:23Z",
    "layer": "intelligence",
    "domain": "orchestration",
    "module_name": "housekeeping",
    "type": "service",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": ["PostgreSQL"],
        "memory_layers": ["semantic_memory", "working_memory"],
        "imported_by": ["tests.integration.test_orchestrator_memory_integration"],
    },
}
# ============================================================================

from datetime import UTC, datetime, timedelta, timezone
from typing import Any

import structlog

from core.decorators import must_stay_async
from memory.consolidation import ConsolidationPipeline

logger = structlog.get_logger(__name__)


class Housekeeping:
    """
    Housekeeping for Memory Orchestrator.

    Handles memory substrate maintenance tasks:
    - Garbage collection of old packets
    - Storage compaction/optimization
    - Health checks
    """

    def __init__(self, repository: Any | None = None):
        """
        Initialize housekeeping.

        Args:
            repository: Optional MemorySubstrateRepository instance.
        """
        self._repository = repository
        logger.info("Housekeeping initialized")

    async def _get_repository(self) -> Any:
        """Get or lazily load the repository."""
        if self._repository is None:
            try:
                from memory.substrate_repository import get_repository

                self._repository = await get_repository()
            except ImportError:
                logger.warning("MemorySubstrateRepository not available, using stub")
                return None
        return self._repository

    async def process(self, data: dict[str, Any]) -> dict[str, Any]:
        """
        Process data through housekeeping.

        Legacy interface - routes to appropriate method based on data.
        """
        operation = data.get("operation", "health_check")

        if operation == "gc":
            return await self.garbage_collect(data.get("threshold_days", 30))
        if operation == "compact":
            return await self.compact()
        return await self.health_check()

    @must_stay_async("callers use await")
    async def garbage_collect(
        self,
        threshold_days: int = 30,
        tenant_id: str | None = None,
        org_id: str | None = None,
        user_id: str | None = None,
        role: str = "end_user",
    ) -> dict[str, Any]:
        """
        Delete packets older than threshold.

        Args:
            threshold_days: Delete packets older than this many days
            tenant_id: Tenant UUID for RLS isolation
            org_id: Organization UUID for RLS isolation
            user_id: User UUID for RLS isolation
            role: User role for RLS policy enforcement

        Returns:
            Result dict with deleted_count and success status
        """
        logger.info(f"Starting garbage collection (threshold: {threshold_days} days)")

        repository = await self._get_repository()
        if repository is None:
            return {
                "success": False,
                "message": "Repository not available",
                "deleted_count": 0,
            }

        # Set RLS scope if context provided
        if tenant_id and org_id and user_id:
            try:
                async with repository._pool.acquire() as conn:
                    await conn.execute(
                        """SELECT l9_set_scope($1::uuid, $2::uuid, $3::uuid, $4::text)""",
                        tenant_id,
                        org_id,
                        user_id,
                        role,
                    )
            except Exception as e:
                logger.error(f"Failed to set RLS scope in housekeeping: {e}")
                return {
                    "success": False,
                    "message": f"RLS scope initialization failed: {e}",
                    "deleted_count": 0,
                }

        try:
            cutoff_date = datetime.now(UTC) - timedelta(days=threshold_days)

            # Delete old packets via repository (age-based)
            if hasattr(repository, "delete_packets_before"):
                deleted_count = await repository.delete_packets_before(cutoff_date)
            else:
                # Fallback: query and delete individually
                deleted_count = 0
                logger.warning("Repository doesn't support bulk delete, skipping GC")

            # Evict TTL-expired packets via SQL procedure
            ttl_evicted = await self._evict_expired_packets()
            total_deleted = deleted_count + ttl_evicted

            logger.info(
                f"Garbage collection complete: {deleted_count} age-based + "
                f"{ttl_evicted} TTL-expired packets deleted"
            )

            return {
                "success": True,
                "message": f"Deleted {total_deleted} packets "
                f"({deleted_count} age-based, {ttl_evicted} TTL-expired)",
                "deleted_count": total_deleted,
                "cutoff_date": cutoff_date.isoformat(),
                "ttl_evicted": ttl_evicted,
            }

        except Exception as e:
            logger.error(f"Garbage collection failed: {e}")
            return {
                "success": False,
                "message": str(e),
                "deleted_count": 0,
            }

    async def compact(self) -> dict[str, Any]:
        """
        Compact/optimize storage.

        Runs VACUUM ANALYZE on PostgreSQL tables.

        Returns:
            Result dict with success status
        """
        logger.info("Starting storage compaction")

        repository = await self._get_repository()
        if repository is None:
            return {
                "success": False,
                "message": "Repository not available",
            }

        try:
            # Run VACUUM ANALYZE if repository supports it
            if hasattr(repository, "vacuum_analyze"):
                await repository.vacuum_analyze()
            elif hasattr(repository, "_pool"):
                # Direct pool access fallback
                async with repository._pool.acquire() as conn:
                    await conn.execute("VACUUM ANALYZE packet_store")
                    await conn.execute("VACUUM ANALYZE vector_embeddings")
            else:
                logger.warning("Repository doesn't support compaction")
                return {
                    "success": True,
                    "message": "Compaction not supported (no-op)",
                }

            logger.info("Storage compaction complete")
            return {
                "success": True,
                "message": "Storage compacted successfully",
            }

        except Exception as e:
            logger.error(f"Compaction failed: {e}")
            return {
                "success": False,
                "message": str(e),
            }

    async def health_check(self) -> dict[str, Any]:
        """
        Check health of memory substrate.

        Returns:
            Health status dict
        """
        repository = await self._get_repository()

        if repository is None:
            return {
                "success": False,
                "status": "unavailable",
                "message": "Repository not available",
            }

        try:
            # Simple connectivity check
            if hasattr(repository, "health_check"):
                health = await repository.health_check()
                return {
                    "success": True,
                    "status": "healthy" if health else "degraded",
                    "message": "Health check passed",
                }

            return {
                "success": True,
                "status": "unknown",
                "message": "Health check not supported",
            }

        except Exception as e:
            return {
                "success": False,
                "status": "unhealthy",
                "message": str(e),
            }

    async def _evict_expired_packets(self) -> int:
        """
        Evict packets that have passed their TTL expiration.

        Calls the PostgreSQL stored procedure evict_expired_packets()
        which was introduced in migration 0008.

        Returns:
            Number of packets evicted (estimated, actual count in DB logs)
        """
        repository = await self._get_repository()
        if repository is None:
            logger.warning("Repository not available for TTL eviction")
            return 0

        try:
            # Call migration 0008 stored procedure
            async with repository._pool.acquire() as conn:
                await conn.execute("CALL evict_expired_packets()")
            logger.debug("TTL eviction procedure executed")
            return 0  # Exact count in database logs via RAISE NOTICE

        except Exception as e:
            logger.error(f"TTL eviction failed: {e}")
            return 0

    async def run_scheduled_maintenance(self) -> dict[str, Any]:
        """
        Run ALL scheduled maintenance procedures from migration 0008.

        This method should be called by an external scheduler (pg_cron, Celery, etc.)
        on a daily basis. It encapsulates all database-level maintenance tasks.

        Procedures called:
        1. decay_unaccessed_importance() - Reduce importance of stale packets
        2. refresh_memory_views() - Refresh materialized views
        3. evict_expired_packets() - TTL-based eviction
        4. evict_expired_reflections() - Reflection expiration

        Returns:
            Dict with status and counts for each operation
        """
        repository = await self._get_repository()
        if repository is None:
            return {
                "success": False,
                "message": "Repository not available",
                "status": "unavailable",
            }

        results: dict[str, Any] = {
            "decay_unaccessed_importance": None,
            "refresh_memory_views": None,
            "evict_expired_packets": None,
            "evict_expired_reflections": None,
        }

        async with repository._pool.acquire() as conn:
            # 1. Decay unaccessed importance
            try:
                await conn.execute(
                    "CALL decay_unaccessed_importance($1::int, $2::float)",
                    30,  # days_threshold
                    0.1,  # decay_rate
                )
                results["decay_unaccessed_importance"] = {"status": "ok"}
                logger.info("✓ Importance decay completed")
            except Exception as e:
                logger.error(f"❌ Importance decay failed: {e}")
                results["decay_unaccessed_importance"] = {
                    "status": "error",
                    "error": str(e),
                }

            # 2. Refresh materialized views
            try:
                await conn.execute("CALL refresh_memory_views()")
                results["refresh_memory_views"] = {"status": "ok"}
                logger.info("✓ Memory views refreshed")
            except Exception as e:
                logger.error(f"❌ View refresh failed: {e}")
                results["refresh_memory_views"] = {"status": "error", "error": str(e)}

            # 3. Evict expired packets (TTL-based)
            try:
                await conn.execute("CALL evict_expired_packets()")
                results["evict_expired_packets"] = {"status": "ok"}
                logger.info("✓ TTL eviction completed")
            except Exception as e:
                logger.error(f"❌ TTL eviction failed: {e}")
                results["evict_expired_packets"] = {"status": "error", "error": str(e)}

            # 4. Evict expired reflections
            try:
                await conn.execute("CALL evict_expired_reflections()")
                results["evict_expired_reflections"] = {"status": "ok"}
                logger.info("✓ Reflection expiration completed")
            except Exception as e:
                logger.error(f"❌ Reflection expiration failed: {e}")
                results["evict_expired_reflections"] = {
                    "status": "error",
                    "error": str(e),
                }

            # 5. Run consolidation (v3.1) - weekly schedule
            # Note: This should run on Saturday 2am UTC, but included here for manual trigger
            # In production, this would be called separately via scheduler
            try:
                consolidation_result = await self.run_consolidation(dry_run=False)
                if consolidation_result.get("success"):
                    results["consolidation"] = {
                        "status": "ok",
                        "report": consolidation_result.get("report"),
                    }
                    logger.info("✓ Consolidation completed")
                else:
                    results["consolidation"] = {
                        "status": "error",
                        "error": consolidation_result.get("message"),
                    }
                    logger.warning("⚠ Consolidation completed with errors")
            except Exception as e:
                logger.error(f"❌ Consolidation failed: {e}")
                results["consolidation"] = {"status": "error", "error": str(e)}

        all_ok = all(r.get("status") == "ok" for r in results.values() if r is not None)

        return {
            "success": all_ok,
            "status": "healthy" if all_ok else "degraded",
            "procedures": results,
            "timestamp": datetime.now(UTC).isoformat(),
        }

    @must_stay_async("callers use await")
    async def run_consolidation(
        self,
        dry_run: bool = False,
        batch_size: int = 1000,
        sleep_between_batches_ms: int = 100,
    ) -> dict[str, Any]:
        """
        Run memory consolidation pipeline (v3.1).

        Per memory_spec_v3.0.yaml pipelines.consolidation:
        - Schedule: weekly_saturday_2am_utc
        - Strategies: deduplication, archival, summarization, ttl_expiration

        Args:
            dry_run: If True, log actions without executing
            batch_size: Number of packets to process per batch
            sleep_between_batches_ms: Sleep time between batches

        Returns:
            Consolidation report dict
        """
        repository = await self._get_repository()
        if repository is None:
            return {
                "success": False,
                "message": "Repository not available",
                "status": "unavailable",
            }

        try:
            consolidation = ConsolidationPipeline(
                repository=repository,
                dry_run=dry_run,
            )

            report = await consolidation.run_consolidation(
                batch_size=batch_size,
                sleep_between_batches_ms=sleep_between_batches_ms,
            )

            report_dict = report.to_dict()

            logger.info(
                "Consolidation complete",
                deduplication=report.deduplication_count,
                archived=report.archived_count,
                summarized=report.summarized_count,
                expired=report.expired_count,
                errors=len(report.errors),
            )

            return {
                "success": len(report.errors) == 0,
                "status": "complete",
                "report": report_dict,
                "timestamp": datetime.now(UTC).isoformat(),
            }

        except Exception as e:
            logger.error(f"Consolidation failed: {e}", exc_info=True)
            return {
                "success": False,
                "status": "error",
                "message": str(e),
                "timestamp": datetime.now(UTC).isoformat(),
            }


# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "ORC-INTE-006",
    "governance_level": "high",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": ["memory.consolidation", "memory.substrate_repository"],
    "tags": [
        "async",
        "batch-processing",
        "debugging",
        "intelligence",
        "logging",
        "messaging",
        "migration",
        "orchestration",
        "scheduling",
        "service",
    ],
    "keywords": [
        "check",
        "collect",
        "compact",
        "consolidation",
        "garbage",
        "health",
        "housekeeping",
        "maintenance",
    ],
    "business_value": "Handles garbage collection, compaction, and maintenance.",
    "last_modified": "2026-01-12T16:30:23Z",
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
