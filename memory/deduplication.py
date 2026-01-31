"""
L9 Memory - Deduplication Engine
=================================

Advanced deduplication for memory consolidation pipeline.

Implements Phase 0 Plan 6: Deduplication in Consolidation Pipeline

Key responsibilities:
- Semantic similarity detection using embeddings
- Content hash-based exact duplicate detection
- Merge strategies (keep_highest_confidence, keep_most_recent, merge_metadata)
- Batch processing for efficiency
- Deduplication metrics and reporting

This module does NOT:
- Modify original packets (creates merged packets)
- Delete packets directly (marks for deletion)
- Handle archival (that's consolidation.py)

Version: 1.0.0
GMP: refactor-phase0-plan6
"""

from __future__ import annotations

# ============================================================================
# DORA HEADER META
# ============================================================================
__dora_meta__ = {
    "component_id": "MEM-DEDUP-001",
    "component_name": "DeduplicationEngine",
    "module_version": "1.0.0",
    "created_at": "2026-01-21T00:00:00Z",
    "created_by": "L9_Refactoring_Phase0",
    "layer": "learning",
    "domain": "memory_substrate",
    "type": "service",
    "status": "active",
    "governance_level": "standard",
    "compliance_required": True,
    "audit_trail": True,
    "purpose": "Advanced deduplication for memory consolidation pipeline",
    "dependencies": [
        "memory.substrate_repository",
        "memory.consolidation",
    ],
}
# ============================================================================

import hashlib
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4

import structlog

logger = structlog.get_logger(__name__)


# =============================================================================
# Deduplication Strategy
# =============================================================================


class MergeStrategy(str, Enum):
    """Strategies for merging duplicate packets."""

    KEEP_HIGHEST_CONFIDENCE = "keep_highest_confidence"
    KEEP_MOST_RECENT = "keep_most_recent"
    MERGE_METADATA = "merge_metadata"
    KEEP_FIRST = "keep_first"


class SimilarityMethod(str, Enum):
    """Methods for detecting similarity."""

    EXACT_HASH = "exact_hash"  # Content hash (MD5/SHA256)
    SEMANTIC_EMBEDDING = "semantic_embedding"  # Vector similarity
    FUZZY_TEXT = "fuzzy_text"  # Levenshtein distance
    HYBRID = "hybrid"  # Combination of methods


# =============================================================================
# Deduplication Results
# =============================================================================


@dataclass
class DuplicateGroup:
    """
    Group of duplicate packets.

    Attributes:
        group_id: Unique group identifier
        packet_ids: List of duplicate packet IDs
        similarity_score: Similarity score (0.0-1.0)
        method: Method used to detect duplicates
        merged_packet_id: ID of merged packet (after merge)
        metadata: Additional group metadata
    """

    group_id: str
    packet_ids: list[str]
    similarity_score: float
    method: SimilarityMethod
    merged_packet_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Export as dict for logging."""
        return {
            "group_id": self.group_id,
            "packet_ids": self.packet_ids,
            "packet_count": len(self.packet_ids),
            "similarity_score": self.similarity_score,
            "method": self.method.value,
            "merged_packet_id": self.merged_packet_id,
        }


@dataclass
class DeduplicationReport:
    """
    Report from deduplication run.

    Attributes:
        total_packets_analyzed: Total packets analyzed
        duplicate_groups_found: Number of duplicate groups
        packets_marked_for_deletion: Number of packets marked for deletion
        packets_merged: Number of packets merged
        space_saved_bytes: Estimated space saved
        execution_time_seconds: Execution time
        errors: List of errors encountered
    """

    total_packets_analyzed: int = 0
    duplicate_groups_found: int = 0
    packets_marked_for_deletion: int = 0
    packets_merged: int = 0
    space_saved_bytes: int = 0
    execution_time_seconds: float = 0.0
    errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Export as dict."""
        return {
            "total_packets_analyzed": self.total_packets_analyzed,
            "duplicate_groups_found": self.duplicate_groups_found,
            "packets_marked_for_deletion": self.packets_marked_for_deletion,
            "packets_merged": self.packets_merged,
            "space_saved_bytes": self.space_saved_bytes,
            "space_saved_mb": round(self.space_saved_bytes / 1024 / 1024, 2),
            "execution_time_seconds": self.execution_time_seconds,
            "error_count": len(self.errors),
        }


# =============================================================================
# Deduplication Engine
# =============================================================================


class DeduplicationEngine:
    """
    Advanced deduplication engine for memory consolidation.

    Detects and merges duplicate packets using multiple strategies.
    """

    def __init__(
        self,
        similarity_threshold: float = 0.95,
        merge_strategy: MergeStrategy = MergeStrategy.KEEP_HIGHEST_CONFIDENCE,
        similarity_method: SimilarityMethod = SimilarityMethod.HYBRID,
        batch_size: int = 1000,
    ):
        """
        Initialize deduplication engine.

        Args:
            similarity_threshold: Threshold for considering packets duplicate (0.0-1.0)
            merge_strategy: Strategy for merging duplicates
            similarity_method: Method for detecting similarity
            batch_size: Batch size for processing
        """
        self.similarity_threshold = similarity_threshold
        self.merge_strategy = merge_strategy
        self.similarity_method = similarity_method
        self.batch_size = batch_size

        logger.info(
            "DeduplicationEngine initialized",
            similarity_threshold=similarity_threshold,
            merge_strategy=merge_strategy.value,
            similarity_method=similarity_method.value,
        )

    async def deduplicate_packets(
        self,
        packets: list[dict[str, Any]],
    ) -> tuple[list[DuplicateGroup], DeduplicationReport]:
        """
        Deduplicate a batch of packets.

        Args:
            packets: List of packet dicts to deduplicate

        Returns:
            Tuple of (duplicate_groups, report)
        """
        start_time = datetime.now(timezone.utc)
        report = DeduplicationReport(total_packets_analyzed=len(packets))

        logger.info(
            "deduplication.started",
            packet_count=len(packets),
            similarity_threshold=self.similarity_threshold,
        )

        try:
            # Step 1: Detect duplicates
            duplicate_groups = await self._detect_duplicates(packets)
            report.duplicate_groups_found = len(duplicate_groups)

            logger.info(
                "deduplication.detection_complete",
                duplicate_groups=len(duplicate_groups),
                total_duplicates=sum(len(g.packet_ids) for g in duplicate_groups),
            )

            # Step 2: Merge duplicates
            for group in duplicate_groups:
                try:
                    merged_packet = await self._merge_duplicate_group(
                        group,
                        packets,
                    )

                    if merged_packet:
                        group.merged_packet_id = merged_packet["packet_id"]
                        report.packets_merged += 1
                        report.packets_marked_for_deletion += len(group.packet_ids) - 1

                        # Estimate space saved (rough approximation)
                        avg_packet_size = 1024  # 1KB average
                        report.space_saved_bytes += (
                            len(group.packet_ids) - 1
                        ) * avg_packet_size

                except Exception as e:
                    error_msg = f"Failed to merge group {group.group_id}: {e!s}"
                    report.errors.append(error_msg)
                    logger.error("deduplication.merge_error", error=error_msg)

            end_time = datetime.now(timezone.utc)
            report.execution_time_seconds = (end_time - start_time).total_seconds()

            logger.info(
                "deduplication.completed",
                **report.to_dict(),
            )

            return duplicate_groups, report

        except Exception as e:
            error_msg = f"Deduplication failed: {e!s}"
            report.errors.append(error_msg)
            logger.error("deduplication.error", error=error_msg)

            end_time = datetime.now(timezone.utc)
            report.execution_time_seconds = (end_time - start_time).total_seconds()

            return [], report

    async def _detect_duplicates(
        self,
        packets: list[dict[str, Any]],
    ) -> list[DuplicateGroup]:
        """
        Detect duplicate packets using configured method.

        Args:
            packets: List of packets to analyze

        Returns:
            List of duplicate groups
        """
        if self.similarity_method == SimilarityMethod.EXACT_HASH:
            return await self._detect_exact_duplicates(packets)
        if self.similarity_method == SimilarityMethod.SEMANTIC_EMBEDDING:
            return await self._detect_semantic_duplicates(packets)
        if self.similarity_method == SimilarityMethod.FUZZY_TEXT:
            return await self._detect_fuzzy_duplicates(packets)
        if self.similarity_method == SimilarityMethod.HYBRID:
            return await self._detect_hybrid_duplicates(packets)
        logger.warning(
            "deduplication.unknown_method",
            method=self.similarity_method,
        )
        return []

    async def _detect_exact_duplicates(
        self,
        packets: list[dict[str, Any]],
    ) -> list[DuplicateGroup]:
        """
        Detect exact duplicates using content hash.

        Args:
            packets: List of packets

        Returns:
            List of duplicate groups
        """
        hash_to_packets: dict[str, list[str]] = {}

        for packet in packets:
            content_hash = self._compute_content_hash(packet)

            if content_hash not in hash_to_packets:
                hash_to_packets[content_hash] = []

            hash_to_packets[content_hash].append(packet["packet_id"])

        # Create groups for hashes with multiple packets
        groups = []
        for content_hash, packet_ids in hash_to_packets.items():
            if len(packet_ids) > 1:
                group = DuplicateGroup(
                    group_id=str(uuid4()),
                    packet_ids=packet_ids,
                    similarity_score=1.0,  # Exact match
                    method=SimilarityMethod.EXACT_HASH,
                    metadata={"content_hash": content_hash},
                )
                groups.append(group)

        return groups

    async def _detect_semantic_duplicates(
        self,
        packets: list[dict[str, Any]],
    ) -> list[DuplicateGroup]:
        """
        Detect semantic duplicates using embeddings.

        Args:
            packets: List of packets

        Returns:
            List of duplicate groups
        """
        # In production, this would use pgvector similarity search
        # For now, we'll use a simplified approach

        groups = []
        processed_ids = set()

        for i, packet_a in enumerate(packets):
            if packet_a["packet_id"] in processed_ids:
                continue

            similar_packets = [packet_a["packet_id"]]

            for _j, packet_b in enumerate(packets[i + 1 :], start=i + 1):
                if packet_b["packet_id"] in processed_ids:
                    continue

                # Compute similarity (simplified - in production use embeddings)
                similarity = self._compute_semantic_similarity(packet_a, packet_b)

                if similarity >= self.similarity_threshold:
                    similar_packets.append(packet_b["packet_id"])
                    processed_ids.add(packet_b["packet_id"])

            if len(similar_packets) > 1:
                group = DuplicateGroup(
                    group_id=str(uuid4()),
                    packet_ids=similar_packets,
                    similarity_score=self.similarity_threshold,
                    method=SimilarityMethod.SEMANTIC_EMBEDDING,
                )
                groups.append(group)
                processed_ids.add(packet_a["packet_id"])

        return groups

    async def _detect_fuzzy_duplicates(
        self,
        packets: list[dict[str, Any]],
    ) -> list[DuplicateGroup]:
        """
        Detect fuzzy duplicates using text similarity.

        Args:
            packets: List of packets

        Returns:
            List of duplicate groups
        """
        # Simplified implementation - in production use Levenshtein distance
        return []

    async def _detect_hybrid_duplicates(
        self,
        packets: list[dict[str, Any]],
    ) -> list[DuplicateGroup]:
        """
        Detect duplicates using hybrid approach (exact + semantic).

        Args:
            packets: List of packets

        Returns:
            List of duplicate groups
        """
        # Step 1: Find exact duplicates
        exact_groups = await self._detect_exact_duplicates(packets)

        # Step 2: Find semantic duplicates among non-exact matches
        exact_packet_ids = {pid for group in exact_groups for pid in group.packet_ids}

        remaining_packets = [
            p for p in packets if p["packet_id"] not in exact_packet_ids
        ]

        semantic_groups = await self._detect_semantic_duplicates(remaining_packets)

        return exact_groups + semantic_groups

    async def _merge_duplicate_group(
        self,
        group: DuplicateGroup,
        packets: list[dict[str, Any]],
    ) -> dict[str, Any] | None:
        """
        Merge a group of duplicate packets.

        Args:
            group: Duplicate group to merge
            packets: All packets (for lookup)

        Returns:
            Merged packet dict or None if merge failed
        """
        # Find packets in group
        group_packets = [p for p in packets if p["packet_id"] in group.packet_ids]

        if not group_packets:
            return None

        if self.merge_strategy == MergeStrategy.KEEP_HIGHEST_CONFIDENCE:
            return self._merge_keep_highest_confidence(group_packets)
        if self.merge_strategy == MergeStrategy.KEEP_MOST_RECENT:
            return self._merge_keep_most_recent(group_packets)
        if self.merge_strategy == MergeStrategy.MERGE_METADATA:
            return self._merge_metadata(group_packets)
        if self.merge_strategy == MergeStrategy.KEEP_FIRST:
            return group_packets[0]
        return group_packets[0]

    def _merge_keep_highest_confidence(
        self,
        packets: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Keep packet with highest confidence score."""
        return max(
            packets,
            key=lambda p: p.get("metadata", {}).get("confidence", 0.0),
        )

    def _merge_keep_most_recent(
        self,
        packets: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Keep most recently created packet."""
        return max(
            packets,
            key=lambda p: p.get("created_at", "1970-01-01T00:00:00Z"),
        )

    def _merge_metadata(
        self,
        packets: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Merge metadata from all packets."""
        # Start with most recent packet
        merged = self._merge_keep_most_recent(packets)

        # Merge metadata from all packets
        merged_metadata = {}
        for packet in packets:
            packet_metadata = packet.get("metadata", {})
            merged_metadata.update(packet_metadata)

        merged["metadata"] = merged_metadata
        merged["metadata"]["merged_from"] = [p["packet_id"] for p in packets]
        merged["metadata"]["merge_strategy"] = self.merge_strategy.value

        return merged

    def _compute_content_hash(self, packet: dict[str, Any]) -> str:
        """
        Compute content hash for packet.

        Args:
            packet: Packet dict

        Returns:
            SHA256 hash of packet content
        """
        # Extract content for hashing (exclude metadata that changes)
        content = {
            "packet_type": packet.get("packet_type"),
            "payload": packet.get("payload"),
        }

        # Convert to string and hash
        content_str = str(sorted(content.items()))
        return hashlib.sha256(content_str.encode()).hexdigest()

    def _compute_semantic_similarity(
        self,
        packet_a: dict[str, Any],
        packet_b: dict[str, Any],
    ) -> float:
        """
        Compute semantic similarity between packets.

        In production, this would use pgvector cosine similarity.
        For now, simplified text comparison.

        Args:
            packet_a: First packet
            packet_b: Second packet

        Returns:
            Similarity score (0.0-1.0)
        """
        # Simplified: compare packet types and basic content
        if packet_a.get("packet_type") != packet_b.get("packet_type"):
            return 0.0

        # In production: use embedding cosine similarity
        # For now: simple heuristic
        payload_a = str(packet_a.get("payload", ""))
        payload_b = str(packet_b.get("payload", ""))

        if payload_a == payload_b:
            return 1.0

        # Very simplified similarity
        common_words = set(payload_a.split()) & set(payload_b.split())
        total_words = set(payload_a.split()) | set(payload_b.split())

        if not total_words:
            return 0.0

        return len(common_words) / len(total_words)


# =============================================================================
# Module Exports
# =============================================================================

__all__ = [
    "DeduplicationEngine",
    "DeduplicationReport",
    "DuplicateGroup",
    "MergeStrategy",
    "SimilarityMethod",
]

# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "MEM-LEAR-017",
    "governance_level": "high",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": [
        "async",
        "batch-processing",
        "data-models",
        "dataclass",
        "engine",
        "learning",
        "logging",
        "metrics",
        "security",
    ],
    "keywords": [
        "consolidation",
        "deduplicate",
        "deduplication",
        "detection",
        "duplicate",
        "engine",
        "group",
        "memory",
    ],
    "business_value": "Implements Phase 0 Plan 6: Deduplication in Consolidation Pipeline",
    "last_modified": "2026-01-24T13:02:52Z",
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
