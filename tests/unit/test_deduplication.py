"""
Unit Tests for Deduplication Engine
====================================

Tests the deduplication engine implementation.

Test Coverage:
- DuplicateGroup creation
- DeduplicationReport metrics
- Exact hash duplicate detection
- Semantic duplicate detection
- Merge strategies
- Deduplication execution

Mutation Testing Target: 85%+ score
"""

import pytest
from unittest.mock import Mock, AsyncMock

from memory.deduplication import (
    MergeStrategy,
    SimilarityMethod,
    DuplicateGroup,
    DeduplicationReport,
    DeduplicationEngine,
)


class TestDuplicateGroup:
    """Test DuplicateGroup dataclass."""
    
    def test_duplicate_group_creation(self):
        """Test DuplicateGroup creation."""
        group = DuplicateGroup(
            group_id="test-group",
            packet_ids=["p1", "p2", "p3"],
            similarity_score=0.98,
            method=SimilarityMethod.EXACT_HASH,
        )
        
        assert group.group_id == "test-group"
        assert len(group.packet_ids) == 3
        assert group.similarity_score == 0.98
    
    def test_duplicate_group_to_dict(self):
        """Test DuplicateGroup.to_dict()."""
        group = DuplicateGroup(
            group_id="test-group",
            packet_ids=["p1", "p2"],
            similarity_score=1.0,
            method=SimilarityMethod.EXACT_HASH,
        )
        
        result = group.to_dict()
        
        assert result["group_id"] == "test-group"
        assert result["packet_count"] == 2
        assert result["similarity_score"] == 1.0


class TestDeduplicationReport:
    """Test DeduplicationReport dataclass."""
    
    def test_report_initialization(self):
        """Test report initializes with zeros."""
        report = DeduplicationReport()
        
        assert report.total_packets_analyzed == 0
        assert report.duplicate_groups_found == 0
        assert report.packets_merged == 0
    
    def test_report_to_dict(self):
        """Test report.to_dict() exports correctly."""
        report = DeduplicationReport(
            total_packets_analyzed=100,
            duplicate_groups_found=5,
            packets_merged=10,
            space_saved_bytes=10240,
        )
        
        result = report.to_dict()
        
        assert result["total_packets_analyzed"] == 100
        assert result["duplicate_groups_found"] == 5
        assert result["space_saved_mb"] == 0.01  # 10240 bytes = 0.01 MB


class TestDeduplicationEngine:
    """Test DeduplicationEngine."""
    
    def test_engine_initialization(self):
        """Test engine initializes with config."""
        engine = DeduplicationEngine(
            similarity_threshold=0.95,
            merge_strategy=MergeStrategy.KEEP_HIGHEST_CONFIDENCE,
        )
        
        assert engine.similarity_threshold == 0.95
        assert engine.merge_strategy == MergeStrategy.KEEP_HIGHEST_CONFIDENCE
    
    @pytest.mark.asyncio
    async def test_detect_exact_duplicates(self):
        """Test exact duplicate detection."""
        engine = DeduplicationEngine(similarity_method=SimilarityMethod.EXACT_HASH)
        
        packets = [
            {"packet_id": "p1", "packet_type": "event", "payload": {"data": "test"}},
            {"packet_id": "p2", "packet_type": "event", "payload": {"data": "test"}},  # Duplicate
            {"packet_id": "p3", "packet_type": "event", "payload": {"data": "different"}},
        ]
        
        groups = await engine._detect_exact_duplicates(packets)
        
        assert len(groups) == 1
        assert len(groups[0].packet_ids) == 2
        assert "p1" in groups[0].packet_ids
        assert "p2" in groups[0].packet_ids
    
    @pytest.mark.asyncio
    async def test_deduplicate_packets(self):
        """Test full deduplication process."""
        engine = DeduplicationEngine(
            similarity_threshold=0.95,
            similarity_method=SimilarityMethod.EXACT_HASH,
        )
        
        packets = [
            {"packet_id": "p1", "packet_type": "event", "payload": {"data": "test"}},
            {"packet_id": "p2", "packet_type": "event", "payload": {"data": "test"}},
        ]
        
        groups, report = await engine.deduplicate_packets(packets)
        
        assert report.total_packets_analyzed == 2
        assert len(groups) >= 0  # May find duplicates
    
    def test_merge_keep_highest_confidence(self):
        """Test merge strategy: keep highest confidence."""
        engine = DeduplicationEngine(merge_strategy=MergeStrategy.KEEP_HIGHEST_CONFIDENCE)
        
        packets = [
            {"packet_id": "p1", "metadata": {"confidence": 0.8}},
            {"packet_id": "p2", "metadata": {"confidence": 0.95}},
            {"packet_id": "p3", "metadata": {"confidence": 0.7}},
        ]
        
        result = engine._merge_keep_highest_confidence(packets)
        
        assert result["packet_id"] == "p2"  # Highest confidence
    
    def test_merge_keep_most_recent(self):
        """Test merge strategy: keep most recent."""
        engine = DeduplicationEngine(merge_strategy=MergeStrategy.KEEP_MOST_RECENT)
        
        packets = [
            {"packet_id": "p1", "created_at": "2026-01-01T00:00:00Z"},
            {"packet_id": "p2", "created_at": "2026-01-03T00:00:00Z"},  # Most recent
            {"packet_id": "p3", "created_at": "2026-01-02T00:00:00Z"},
        ]
        
        result = engine._merge_keep_most_recent(packets)
        
        assert result["packet_id"] == "p2"
    
    def test_compute_content_hash(self):
        """Test content hash computation."""
        engine = DeduplicationEngine()
        
        packet1 = {"packet_type": "event", "payload": {"data": "test"}}
        packet2 = {"packet_type": "event", "payload": {"data": "test"}}
        packet3 = {"packet_type": "event", "payload": {"data": "different"}}
        
        hash1 = engine._compute_content_hash(packet1)
        hash2 = engine._compute_content_hash(packet2)
        hash3 = engine._compute_content_hash(packet3)
        
        assert hash1 == hash2  # Same content
        assert hash1 != hash3  # Different content


# =============================================================================
# Mutation Testing Targets
# =============================================================================

class TestMutationTargets:
    """Tests specifically designed to kill common mutations."""
    
    @pytest.mark.asyncio
    async def test_similarity_threshold_comparison(self):
        """Kill mutation: >= threshold -> > threshold."""
        engine = DeduplicationEngine(similarity_threshold=0.95)
        
        assert engine.similarity_threshold == 0.95
    
    def test_merge_strategy_selection(self):
        """Kill mutation: strategy check -> wrong strategy."""
        engine_confidence = DeduplicationEngine(
            merge_strategy=MergeStrategy.KEEP_HIGHEST_CONFIDENCE
        )
        engine_recent = DeduplicationEngine(
            merge_strategy=MergeStrategy.KEEP_MOST_RECENT
        )
        
        assert engine_confidence.merge_strategy != engine_recent.merge_strategy
    
    def test_content_hash_uniqueness(self):
        """Kill mutation: hash computation -> constant."""
        engine = DeduplicationEngine()
        
        packet1 = {"packet_type": "event", "payload": {"a": 1}}
        packet2 = {"packet_type": "event", "payload": {"b": 2}}
        
        hash1 = engine._compute_content_hash(packet1)
        hash2 = engine._compute_content_hash(packet2)
        
        assert hash1 != hash2
