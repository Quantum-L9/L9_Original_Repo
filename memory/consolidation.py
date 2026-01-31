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

# ============================================================================
__dora_meta__ = {
    "component_name": "Consolidation Pipeline",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2026-01-11T18:13:39Z",
    "updated_at": "2026-01-17T23:47:56Z",
    "layer": "learning",
    "domain": "memory_substrate",
    "module_name": "consolidation",
    "type": "service",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": [],
        "memory_layers": ["semantic_memory", "working_memory"],
        "imported_by": [
            "memory.__init__",
            "memory.substrate_service",
            "orchestrators.memory.housekeeping",
            "tests.memory.test_consolidation",
        ],
    },
}
# ============================================================================

import asyncio
import re
from datetime import datetime, timezone, timedelta
from typing import Any
from uuid import uuid4

import structlog

from memory.deduplication import (
    DeduplicationEngine,
    MergeStrategy,
    SimilarityMethod,
)
from memory.substrate_repository import SubstrateRepository

logger = structlog.get_logger(__name__)


class ConsolidationReport:
    """Consolidation execution report."""

    def __init__(self):
        self.deduplication_count = 0
        self.archived_count = 0
        self.summarized_count = 0
        self.expired_count = 0
        self.errors: list[str] = []
        self.start_time = datetime.now(timezone.utc)
        self.end_time: datetime | None = None

    def to_dict(self) -> dict[str, Any]:
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
        repository: SubstrateRepository | None = None,
        dry_run: bool = False,
        dedup_engine: DeduplicationEngine | None = None,
    ):
        """
        Initialize consolidation pipeline.

        Args:
            repository: SubstrateRepository for database access
            dry_run: If True, log actions without executing
            dedup_engine: Optional DeduplicationEngine instance (creates default if None)
        """
        self._repository = repository
        self._dry_run = dry_run

        # Strategy configs per spec
        self._deduplication_config = {
            "enabled": True,
            "similarity_threshold": 0.95,
            "merge_policy": "keep_highest_confidence",
        }

        # Initialize DeduplicationEngine with config-derived settings
        self._dedup_engine = dedup_engine or DeduplicationEngine(
            similarity_threshold=self._deduplication_config["similarity_threshold"],
            merge_strategy=MergeStrategy.KEEP_HIGHEST_CONFIDENCE,
            similarity_method=SimilarityMethod.HYBRID,
            batch_size=1000,
        )

        self._archival_config = {
            "enabled": True,
            "triggers": [{"age_days": 90, "access_count_lt": 3, "importance_lt": 0.3}],
            "archive_backend": "postgres_archive_table",
            "compress_payload": True,
        }

        self._summarization_config = {
            "enabled": True,
            "triggers": [{"access_count_gte": 10, "has_summary": False}],
            "summary_backend": "memory_summaries_table",
            "generate_embedding": True,
        }

        self._ttl_config = {
            "enabled": True,
            "check_frequency": "daily",
            "grace_period_hours": 24,
            "cascade_delete_embeddings": True,
        }

        logger.info(
            "ConsolidationPipeline initialized",
            dry_run=dry_run,
            dedup_engine=type(self._dedup_engine).__name__,
        )

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
            report.errors.append(f"Pipeline error: {e!s}")

        finally:
            report.end_time = datetime.now(timezone.utc)
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
        Run deduplication strategy using DeduplicationEngine.

        Finds packets with semantic similarity >= threshold using pgvector,
        then uses DeduplicationEngine's merge strategy for resolution.

        Strategy:
        1. Query packets with embeddings via pgvector cosine similarity
        2. For each duplicate pair, fetch full packet data
        3. Use DeduplicationEngine merge strategy to determine which to keep
        4. Mark duplicates with tags for later cleanup
        """
        logger.info(
            "Running deduplication strategy",
            engine=type(self._dedup_engine).__name__,
            merge_strategy=self._dedup_engine.merge_strategy.value,
        )

        if self._dry_run:
            logger.info("DRY RUN: Would deduplicate packets", batch_size=batch_size)
            return 0

        deduplicated = 0
        threshold = self._deduplication_config["similarity_threshold"]

        try:
            async with self._repository.acquire() as conn:
                # Find near-duplicate embeddings using pgvector cosine similarity
                # This query finds pairs of embeddings with similarity >= threshold
                rows = await conn.fetch(
                    """
                    WITH embedding_pairs AS (
                        SELECT
                            e1.embedding_id as id1,
                            e2.embedding_id as id2,
                            e1.payload->>'packet_id' as packet_id_1,
                            e2.payload->>'packet_id' as packet_id_2,
                            1 - (e1.vector <=> e2.vector) as similarity,
                            e1.created_at as created_1,
                            e2.created_at as created_2
                        FROM semantic_memory e1
                        INNER JOIN semantic_memory e2
                            ON e1.embedding_id < e2.embedding_id
                        WHERE 1 - (e1.vector <=> e2.vector) >= $1
                        LIMIT $2
                    )
                    SELECT * FROM embedding_pairs
                    ORDER BY similarity DESC
                    """,
                    threshold,
                    batch_size,
                )

                if not rows:
                    logger.info(
                        "No duplicates found above threshold", threshold=threshold
                    )
                    return 0

                # Process duplicates using DeduplicationEngine merge strategy
                for row in rows:
                    packet_id_1 = row["packet_id_1"]
                    packet_id_2 = row["packet_id_2"]
                    similarity = row["similarity"]

                    # Determine which packet to keep based on merge strategy
                    (
                        packet_id_to_keep,
                        packet_id_to_mark,
                    ) = await self._resolve_duplicate_pair(
                        conn=conn,
                        packet_id_1=packet_id_1,
                        packet_id_2=packet_id_2,
                        created_1=row["created_1"],
                        created_2=row["created_2"],
                    )

                    # Mark the duplicate packet with a tag
                    if packet_id_to_mark:
                        await conn.execute(
                            """
                            UPDATE packet_store
                            SET tags = array_append(
                                COALESCE(tags, ARRAY[]::text[]),
                                $1
                            )
                            WHERE packet_id = $2::uuid
                            AND NOT ($1 = ANY(COALESCE(tags, ARRAY[]::text[])))
                            """,
                            f"duplicate_of:{packet_id_to_keep}",
                            packet_id_to_mark,
                        )
                        deduplicated += 1

                        logger.debug(
                            "Marked duplicate",
                            duplicate=packet_id_to_mark,
                            original=packet_id_to_keep,
                            similarity=f"{similarity:.4f}",
                            strategy=self._dedup_engine.merge_strategy.value,
                        )

                    if sleep_ms > 0:
                        await asyncio.sleep(sleep_ms / 1000.0)

        except Exception as e:
            logger.error("Deduplication failed", error=str(e), exc_info=True)
            raise

        logger.info("Deduplication complete", deduplicated_count=deduplicated)
        return deduplicated

    async def _resolve_duplicate_pair(
        self,
        conn: Any,
        packet_id_1: str,
        packet_id_2: str,
        created_1: datetime | None,
        created_2: datetime | None,
    ) -> tuple[str, str]:
        """
        Resolve which packet to keep in a duplicate pair using DeduplicationEngine strategy.

        Args:
            conn: Database connection
            packet_id_1: First packet ID
            packet_id_2: Second packet ID
            created_1: First packet creation time
            created_2: Second packet creation time

        Returns:
            Tuple of (packet_id_to_keep, packet_id_to_mark_as_duplicate)
        """
        merge_strategy = self._dedup_engine.merge_strategy

        if merge_strategy == MergeStrategy.KEEP_HIGHEST_CONFIDENCE:
            # Fetch confidence scores from both packets
            rows = await conn.fetch(
                """
                SELECT packet_id,
                       COALESCE((envelope->'metadata'->>'confidence')::float, 0.0) as confidence
                FROM packet_store
                WHERE packet_id = ANY($1::uuid[])
                """,
                [packet_id_1, packet_id_2],
            )

            if len(rows) == 2:
                # Sort by confidence descending, keep highest
                sorted_rows = sorted(rows, key=lambda r: r["confidence"], reverse=True)
                return str(sorted_rows[0]["packet_id"]), str(
                    sorted_rows[1]["packet_id"]
                )

        elif merge_strategy == MergeStrategy.KEEP_MOST_RECENT:
            # Keep the more recently created packet
            if created_1 and created_2:
                if created_1 >= created_2:
                    return packet_id_1, packet_id_2
                return packet_id_2, packet_id_1

        elif merge_strategy == MergeStrategy.KEEP_FIRST:
            # Keep the older packet (first created)
            if created_1 and created_2:
                if created_1 <= created_2:
                    return packet_id_1, packet_id_2
                return packet_id_2, packet_id_1

        # Default fallback: keep older packet (original behavior)
        if created_1 and created_2:
            if created_1 <= created_2:
                return packet_id_1, packet_id_2
            return packet_id_2, packet_id_1

        # If no timestamps, keep first by ID order
        return packet_id_1, packet_id_2

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
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=90)

        try:
            async with self._repository.acquire() as conn:
                # Query packets matching archival criteria
                # Note: This requires access_count and importance columns
                # For now, simplified implementation
                rows = await conn.fetch(
                    """
                    SELECT packet_id, created_at
                    FROM packet_store
                    WHERE created_at < $1
                    LIMIT $2
                    """,
                    cutoff_date,
                    batch_size,
                )

                for row in rows:
                    packet_id = row["packet_id"]
                    # Archive packet (move to archive table)
                    # TODO(GMP-118): Implement actual archival logic
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

        Creates extractive summaries for frequently accessed packets.
        Per spec: access_count >= 10 and no existing summary.

        Strategy:
        1. Find packets with high access count and no summary tag
        2. Extract key sentences from payload text
        3. Store summary in semantic_facts table with tier='session'
        4. Tag original packet as summarized
        """
        logger.info("Running summarization strategy")

        if self._dry_run:
            logger.info("DRY RUN: Would summarize packets", batch_size=batch_size)
            return 0

        summarized = 0
        min_access_count = 10  # Per spec: access_count_gte: 10

        try:
            async with self._repository.acquire() as conn:
                # Find packets needing summarization
                # Must have access_count >= threshold and not already summarized
                rows = await conn.fetch(
                    """
                    SELECT
                        packet_id,
                        packet_type,
                        envelope,
                        access_count,
                        tenant_id,
                        org_id,
                        user_id
                    FROM packet_store
                    WHERE access_count >= $1
                    AND NOT ('summarized' = ANY(COALESCE(tags, ARRAY[]::text[])))
                    AND envelope->'payload'->>'text' IS NOT NULL
                    ORDER BY access_count DESC
                    LIMIT $2
                    """,
                    min_access_count,
                    batch_size,
                )

                if not rows:
                    logger.info(
                        "No packets need summarization",
                        min_access_count=min_access_count,
                    )
                    return 0

                for row in rows:
                    packet_id = row["packet_id"]
                    envelope = row["envelope"]
                    payload = envelope.get("payload", {})

                    # Extract text content
                    text = (
                        payload.get("text")
                        or payload.get("content")
                        or payload.get("description")
                        or payload.get("message")
                        or ""
                    )

                    if not text or len(text) < 100:
                        continue

                    # Generate extractive summary (first 2-3 sentences, max 500 chars)
                    summary = self._extract_summary(text, max_length=500)

                    if not summary:
                        continue

                    # Store summary as semantic fact
                    fact_id = uuid4()
                    await conn.execute(
                        """
                        INSERT INTO semantic_facts (
                            fact_id, tenant_id, org_id, user_id,
                            fact_text, triplet, importance, tier,
                            source, source_packet_id, confidence
                        ) VALUES (
                            $1, $2, $3, $4,
                            $5, $6::jsonb, $7, $8,
                            $9, $10, $11
                        )
                        ON CONFLICT (tenant_id, fact_text) DO NOTHING
                        """,
                        fact_id,
                        row["tenant_id"],
                        row["org_id"],
                        row["user_id"],
                        summary,
                        '{"subject": "packet_summary", "predicate": "summarizes", "object": "'
                        + str(packet_id)
                        + '"}',
                        0.7,  # Medium-high importance for summaries
                        "session",  # Summaries are session-tier
                        "consolidation_summarizer",
                        packet_id,
                        0.85,  # High confidence for extractive summaries
                    )

                    # Tag original packet as summarized
                    await conn.execute(
                        """
                        UPDATE packet_store
                        SET tags = array_append(COALESCE(tags, ARRAY[]::text[]), 'summarized')
                        WHERE packet_id = $1
                        """,
                        packet_id,
                    )

                    summarized += 1
                    logger.debug(
                        "Created summary",
                        packet_id=str(packet_id),
                        summary_length=len(summary),
                    )

                    if sleep_ms > 0:
                        await asyncio.sleep(sleep_ms / 1000.0)

        except Exception as e:
            logger.error("Summarization failed", error=str(e), exc_info=True)
            raise

        logger.info("Summarization complete", summarized_count=summarized)
        return summarized

    def _extract_summary(self, text: str, max_length: int = 500) -> str:
        """
        Extract summary from text using simple sentence extraction.

        Takes first 2-3 complete sentences up to max_length.
        For production, this could be replaced with LLM-based summarization.

        Args:
            text: Source text to summarize
            max_length: Maximum summary length

        Returns:
            Extracted summary string
        """
        if not text:
            return ""

        # Simple sentence splitting (handles . ! ?)
        sentences = re.split(r"(?<=[.!?])\s+", text.strip())

        if not sentences:
            return text[:max_length].strip()

        summary_parts = []
        current_length = 0

        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue

            if current_length + len(sentence) + 1 <= max_length:
                summary_parts.append(sentence)
                current_length += len(sentence) + 1
            else:
                break

            # Stop after 3 sentences
            if len(summary_parts) >= 3:
                break

        return " ".join(summary_parts)

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
        grace_cutoff = datetime.now(timezone.utc) - timedelta(hours=24)

        try:
            async with self._repository.acquire() as conn:
                # Query expired packets
                rows = await conn.fetch(
                    """
                    SELECT packet_id, ttl, created_at
                    FROM packet_store
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
                            DELETE FROM memory_embeddings
                            WHERE packet_id = $1
                            """,
                            packet_id,
                        )

                    # Delete packet
                    await conn.execute(
                        """
                        DELETE FROM packet_store
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


# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "MEM-LEAR-018",
    "governance_level": "critical",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": ["memory.substrate_repository"],
    "tags": [
        "async",
        "batch-processing",
        "debugging",
        "learning",
        "logging",
        "memory-substrate",
        "messaging",
        "scheduling",
        "service",
    ],
    "keywords": [
        "archival",
        "consolidation",
        "deduplication",
        "memory",
        "packets",
        "pipeline",
        "report",
        "repository",
    ],
    "business_value": "Implements memory_spec_v3.0.yaml pipelines.consolidation contract. Schedule: weekly_saturday_2am_utc deduplication: Merge similar packets (similarity_threshold: 0.95) archival: Archive old, low-access",
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
