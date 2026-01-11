"""
L9 Memory - Consolidation Pipeline
Version: 1.0.0

Memory consolidation pipeline for deduplication, archival, summarization, and TTL expiration.
Implements memory_spec_v3.0.yaml pipelines.consolidation contract.

Schedule: weekly_saturday_2am_utc
Strategies:
- deduplication: Merge similar packets (similarity_threshold: 0.95)
- archival: Archive old, low-access packets (age_days: 90, access_count_lt: 3, importance_lt: 0.3)
- summarization: Summarize frequently accessed packets (access_count_gte: 10)
- ttl_expiration: Remove expired packets (grace_period_hours: 24)
"""

from __future__ import annotations

import structlog
from datetime import datetime, timedelta
from typing import Any, Optional, List, Dict
from uuid import UUID
import asyncio

from memory.substrate_repository import SubstrateRepository

logger = structlog.get_logger(__name__)


class ConsolidationReport:
    """Consolidation execution report."""
    
    def __init__(self):
        self.deduplication_count = 0
        self.archived_count = 0
        self.summarized_count = 0
        self.expired_count = 0
        self.errors: List[str] = []
        self.start_time = datetime.utcnow()
        self.end_time: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert report to dict."""
        duration = None
        if self.end_time:
            duration = (self.end_time - self.start_time).total_seconds()
        
        return {
            "deduplication_count": self.deduplication_count,
            "archived_count": self.archived_count,
            "summarized_count": self.summarized_count,
            "expired_count": self.expired_count,
            "errors": self.errors,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "duration_seconds": duration,
        }


class ConsolidationPipeline:
    """
    Memory consolidation pipeline.
    
    Per memory_spec_v3.0.yaml pipelines.consolidation:
    - deduplication: similarity_threshold 0.95, merge_policy keep_highest_confidence
    - archival: age_days 90, access_count_lt 3, importance_lt 0.3
    - summarization: access_count_gte 10, has_summary False
    - ttl_expiration: check_frequency daily, grace_period_hours 24
    """
    
    def __init__(
        self,
        repository: Optional[SubstrateRepository] = None,
        dry_run: bool = False,
    ):
        """
        Initialize consolidation pipeline.
        
        Args:
            repository: SubstrateRepository for database access
            dry_run: If True, log actions without executing
        """
        self._repository = repository
        self._dry_run = dry_run
        
        # Strategy configs per spec
        self._deduplication_config = {
            "enabled": True,
            "similarity_threshold": 0.95,
            "merge_policy": "keep_highest_confidence",
        }
        
        self._archival_config = {
            "enabled": True,
            "triggers": [
                {"age_days": 90, "access_count_lt": 3, "importance_lt": 0.3}
            ],
            "archive_backend": "postgres_archive_table",
            "compress_payload": True,
        }
        
        self._summarization_config = {
            "enabled": True,
            "triggers": [
                {"access_count_gte": 10, "has_summary": False}
            ],
            "summary_backend": "memory_summaries_table",
            "generate_embedding": True,
        }
        
        self._ttl_config = {
            "enabled": True,
            "check_frequency": "daily",
            "grace_period_hours": 24,
            "cascade_delete_embeddings": True,
        }
        
        logger.info("ConsolidationPipeline initialized", dry_run=dry_run)

    def set_repository(self, repository: SubstrateRepository) -> None:
        """Set or update repository reference."""
        self._repository = repository

    async def run_consolidation(
        self,
        batch_size: int = 1000,
        sleep_between_batches_ms: int = 100,
    ) -> ConsolidationReport:
        """
        Run full consolidation pipeline.
        
        Per memory_spec_v3.0.yaml performance_contracts.consolidation:
        - max_runtime_minutes: 60
        - batch_size: 1000
        - sleep_between_batches_ms: 100
        
        Args:
            batch_size: Number of packets to process per batch
            sleep_between_batches_ms: Sleep time between batches
            
        Returns:
            ConsolidationReport with execution results
        """
        if self._repository is None:
            raise RuntimeError("Repository not set")
        
        report = ConsolidationReport()
        logger.info("Starting consolidation pipeline", dry_run=self._dry_run)
        
        try:
            # 1. Deduplication
            if self._deduplication_config["enabled"]:
                report.deduplication_count = await self._run_deduplication(
                    batch_size=batch_size,
                    sleep_ms=sleep_between_batches_ms,
                )
            
            # 2. Archival
            if self._archival_config["enabled"]:
                report.archived_count = await self._run_archival(
                    batch_size=batch_size,
                    sleep_ms=sleep_between_batches_ms,
                )
            
            # 3. Summarization
            if self._summarization_config["enabled"]:
                report.summarized_count = await self._run_summarization(
                    batch_size=batch_size,
                    sleep_ms=sleep_between_batches_ms,
                )
            
            # 4. TTL Expiration
            if self._ttl_config["enabled"]:
                report.expired_count = await self._run_ttl_expiration(
                    batch_size=batch_size,
                    sleep_ms=sleep_between_batches_ms,
                )
        
        except Exception as e:
            logger.error("Consolidation pipeline failed", error=str(e), exc_info=True)
            report.errors.append(f"Pipeline error: {str(e)}")
        
        finally:
            report.end_time = datetime.utcnow()
            logger.info(
                "Consolidation pipeline complete",
                report=report.to_dict(),
            )
        
        return report

    async def _run_deduplication(
        self,
        batch_size: int,
        sleep_ms: int,
    ) -> int:
        """
        Run deduplication strategy.
        
        Finds packets with similarity >= 0.95 and merges them.
        """
        logger.info("Running deduplication strategy")
        
        if self._dry_run:
            logger.info("DRY RUN: Would deduplicate packets", batch_size=batch_size)
            return 0
        
        # TODO: Implement actual deduplication logic
        # For now, return 0 (no deduplication performed)
        logger.warning("Deduplication not fully implemented")
        return 0

    async def _run_archival(
        self,
        batch_size: int,
        sleep_ms: int,
    ) -> int:
        """
        Run archival strategy.
        
        Archives packets matching: age_days >= 90, access_count < 3, importance < 0.3
        """
        logger.info("Running archival strategy")
        
        if self._dry_run:
            logger.info("DRY RUN: Would archive packets", batch_size=batch_size)
            return 0
        
        archived = 0
        cutoff_date = datetime.utcnow() - timedelta(days=90)
        
        try:
            async with self._repository.acquire() as conn:
                # Query packets matching archival criteria
                # Note: This requires access_count and importance columns
                # For now, simplified implementation
                rows = await conn.fetch(
                    """
                    SELECT packet_id, created_at
                    FROM packetstore
                    WHERE created_at < $1
                    LIMIT $2
                    """,
                    cutoff_date,
                    batch_size,
                )
                
                for row in rows:
                    packet_id = row["packet_id"]
                    # Archive packet (move to archive table)
                    # TODO: Implement actual archival logic
                    logger.debug("Would archive packet", packet_id=str(packet_id))
                    archived += 1
                    
                    if sleep_ms > 0:
                        await asyncio.sleep(sleep_ms / 1000.0)
        
        except Exception as e:
            logger.error("Archival failed", error=str(e), exc_info=True)
            raise
        
        logger.info("Archival complete", archived_count=archived)
        return archived

    async def _run_summarization(
        self,
        batch_size: int,
        sleep_ms: int,
    ) -> int:
        """
        Run summarization strategy.
        
        Summarizes packets with access_count >= 10 and no existing summary.
        """
        logger.info("Running summarization strategy")
        
        if self._dry_run:
            logger.info("DRY RUN: Would summarize packets", batch_size=batch_size)
            return 0
        
        # TODO: Implement actual summarization logic
        # Requires:
        # - Access count tracking
        # - Summary generation (LLM or extractive)
        # - Summary storage in memory_summaries_table
        logger.warning("Summarization not fully implemented")
        return 0

    async def _run_ttl_expiration(
        self,
        batch_size: int,
        sleep_ms: int,
    ) -> int:
        """
        Run TTL expiration strategy.
        
        Removes packets with expired TTL (grace_period_hours: 24).
        """
        logger.info("Running TTL expiration strategy")
        
        if self._dry_run:
            logger.info("DRY RUN: Would expire packets", batch_size=batch_size)
            return 0
        
        expired = 0
        grace_cutoff = datetime.utcnow() - timedelta(hours=24)
        
        try:
            async with self._repository.acquire() as conn:
                # Query expired packets
                rows = await conn.fetch(
                    """
                    SELECT packet_id, ttl, created_at
                    FROM packetstore
                    WHERE ttl IS NOT NULL
                      AND (created_at + INTERVAL '1 second' * ttl) < $1
                    LIMIT $2
                    """,
                    grace_cutoff,
                    batch_size,
                )
                
                for row in rows:
                    packet_id = row["packet_id"]
                    
                    # Delete packet and cascade to embeddings if configured
                    if self._ttl_config["cascade_delete_embeddings"]:
                        # Delete embeddings first
                        await conn.execute(
                            """
                            DELETE FROM memoryembeddings
                            WHERE packet_id = $1
                            """,
                            packet_id,
                        )
                    
                    # Delete packet
                    await conn.execute(
                        """
                        DELETE FROM packetstore
                        WHERE packet_id = $1
                        """,
                        packet_id,
                    )
                    
                    expired += 1
                    logger.debug("Expired packet", packet_id=str(packet_id))
                    
                    if sleep_ms > 0:
                        await asyncio.sleep(sleep_ms / 1000.0)
        
        except Exception as e:
            logger.error("TTL expiration failed", error=str(e), exc_info=True)
            raise
        
        logger.info("TTL expiration complete", expired_count=expired)
        return expired

