"""
L9 Memory - Frontier Memory Pipeline Integration Tests
Version: 3.1.0

Integration tests for the GMP-80 frontier memory retrieval architecture:
- GMP-80-A5: Identity Tier (IdentityTierService, HierarchicalContextBuilder)
- GMP-80-A6: Strategy-Based Retrieval (StrategyBasedRetriever, MultiFactorRanker)
- GMP-80-A7: Active Memory Management (ActiveMemoryEncoder, ImportanceManager)

These tests verify the complete pipeline without requiring a live database.
"""

import pytest
from datetime import datetime, timedelta
from uuid import uuid4


# =============================================================================
# GMP-80-A5: Identity Tier Tests
# =============================================================================


class TestIdentityTier:
    """Tests for Identity Tier service (GMP-80-A5)."""

    def test_identity_fact_dataclass(self):
        """Test IdentityFact dataclass creation."""
        from memory.identity_tier import IdentityFact

        fact = IdentityFact(
            fact_id=uuid4(),
            fact_text="User prefers async/await over threads",
            category="preference",
            source="manual",
            importance=0.9,
            confidence=0.95,
            tags=["coding_style", "python"],
        )

        assert fact.fact_text == "User prefers async/await over threads"
        assert fact.category == "preference"
        assert fact.importance == 0.9
        assert fact.confidence == 0.95
        assert "coding_style" in fact.tags

    def test_identity_tier_service_initialization(self):
        """Test IdentityTierService can be instantiated."""
        from memory.identity_tier import IdentityTierService, IDENTITY_MIN_IMPORTANCE

        service = IdentityTierService()
        assert service is not None
        # Check module constant instead of instance attribute
        assert IDENTITY_MIN_IMPORTANCE == 0.8

    def test_hierarchical_context_builder_initialization(self):
        """Test HierarchicalContextBuilder can be instantiated."""
        from memory.context_builder import HierarchicalContextBuilder

        builder = HierarchicalContextBuilder()
        assert builder is not None

    def test_memory_tier_precedence(self):
        """Test MemoryTier precedence values (higher = more important)."""
        from memory.context_builder import MemoryTier

        # Higher precedence = more important
        assert MemoryTier.IDENTITY.precedence == 4  # Highest
        assert MemoryTier.PROJECT.precedence == 3
        assert MemoryTier.SESSION.precedence == 2
        assert MemoryTier.GENERAL.precedence == 1  # Lowest

    def test_memory_tier_ordering(self):
        """Test MemoryTier ordering by precedence."""
        from memory.context_builder import MemoryTier

        tiers = [
            MemoryTier.GENERAL,
            MemoryTier.SESSION,
            MemoryTier.PROJECT,
            MemoryTier.IDENTITY,
        ]
        sorted_tiers = sorted(tiers, key=lambda t: t.precedence, reverse=True)

        assert sorted_tiers[0] == MemoryTier.IDENTITY
        assert sorted_tiers[3] == MemoryTier.GENERAL


# =============================================================================
# GMP-80-A6: Strategy-Based Retrieval Tests
# =============================================================================


class TestRetrievalStrategy:
    """Tests for Strategy-Based Retrieval (GMP-80-A6)."""

    def test_retrieval_strategy_enum(self):
        """Test RetrievalStrategy enum values."""
        from memory.retrieval_strategy import RetrievalStrategy

        assert RetrievalStrategy.CORE_IDENTITY.value == "core_identity"
        assert RetrievalStrategy.PROJECT_CONTEXT.value == "project_context"
        assert RetrievalStrategy.TEMPORAL_RECALL.value == "temporal_recall"
        assert RetrievalStrategy.ASSOCIATION.value == "association"
        assert RetrievalStrategy.UNCERTAINTY_FILL.value == "uncertainty_fill"
        assert RetrievalStrategy.SEMANTIC_SEARCH.value == "semantic_search"

    def test_strategy_context_dataclass(self):
        """Test StrategyContext dataclass creation."""
        from memory.retrieval_strategy import StrategyContext

        ctx = StrategyContext(
            query="What are my preferences?",
            query_pattern="entity_lookup",
            project_id="proj-123",
            agent_uncertainty=0.3,
            entities=["preferences", "coding"],
        )

        assert ctx.query == "What are my preferences?"
        assert ctx.project_id == "proj-123"
        assert ctx.agent_uncertainty == 0.3
        assert "preferences" in ctx.entities

    def test_strategy_determiner_identity_keywords(self):
        """Test StrategyDeterminer detects identity keywords."""
        from memory.retrieval_strategy import (
            StrategyDeterminer,
            StrategyContext,
            RetrievalStrategy,
        )

        determiner = StrategyDeterminer()

        # Test identity keyword detection
        ctx = StrategyContext(query="What are my preferences for code style?")
        strategy, reason = determiner.determine_strategy(ctx)

        assert strategy == RetrievalStrategy.CORE_IDENTITY
        assert "identity" in reason.lower() or "preference" in reason.lower()

    def test_strategy_determiner_temporal_keywords(self):
        """Test StrategyDeterminer detects temporal keywords."""
        from memory.retrieval_strategy import (
            StrategyDeterminer,
            StrategyContext,
            RetrievalStrategy,
        )

        determiner = StrategyDeterminer()

        ctx = StrategyContext(query="What happened yesterday?")
        strategy, reason = determiner.determine_strategy(ctx)

        assert strategy == RetrievalStrategy.TEMPORAL_RECALL

    def test_strategy_determiner_high_uncertainty(self):
        """Test StrategyDeterminer triggers uncertainty_fill for high uncertainty."""
        from memory.retrieval_strategy import (
            StrategyDeterminer,
            StrategyContext,
            RetrievalStrategy,
        )

        determiner = StrategyDeterminer()

        ctx = StrategyContext(
            query="What is the API endpoint?",
            agent_uncertainty=0.8,  # High uncertainty
        )
        strategy, reason = determiner.determine_strategy(ctx)

        assert strategy == RetrievalStrategy.UNCERTAINTY_FILL
        assert "uncertainty" in reason.lower()

    def test_strategy_based_retriever_initialization(self):
        """Test StrategyBasedRetriever can be instantiated."""
        from memory.retrieval_strategy import StrategyBasedRetriever

        retriever = StrategyBasedRetriever()
        assert retriever is not None


class TestMultiFactorRanking:
    """Tests for Multi-Factor Ranking (GMP-80-A6)."""

    def test_ranking_weights_default(self):
        """Test default RankingWeights sum to 1.0."""
        from memory.retrieval_ranking import RankingWeights

        weights = RankingWeights()
        total = (
            weights.similarity
            + weights.recency
            + weights.importance
            + weights.frequency
            + weights.uncertainty
        )
        assert 0.99 <= total <= 1.01

    def test_ranking_weights_presets(self):
        """Test weight presets exist and are valid."""
        from memory.retrieval_ranking import WEIGHT_PRESETS

        assert "balanced" in WEIGHT_PRESETS
        assert "recency_focused" in WEIGHT_PRESETS
        assert "importance_focused" in WEIGHT_PRESETS
        assert "similarity_focused" in WEIGHT_PRESETS
        assert "uncertainty_aware" in WEIGHT_PRESETS

    def test_ranking_item_dataclass(self):
        """Test RankingItem dataclass creation."""
        from memory.retrieval_ranking import RankingItem

        item = RankingItem(
            item_id="fact-123",
            item_type="fact",
            content="Test fact content",
            similarity_score=0.85,
            importance=0.7,
            access_count=5,
        )

        assert item.item_id == "fact-123"
        assert item.similarity_score == 0.85
        assert item.importance == 0.7

    def test_multi_factor_ranker_initialization(self):
        """Test MultiFactorRanker can be instantiated."""
        from memory.retrieval_ranking import MultiFactorRanker

        ranker = MultiFactorRanker()
        assert ranker is not None

    def test_multi_factor_ranker_rank_empty(self):
        """Test MultiFactorRanker handles empty list."""
        from memory.retrieval_ranking import MultiFactorRanker

        ranker = MultiFactorRanker()
        result = ranker.rank([])
        assert result == []

    def test_multi_factor_ranker_rank_items(self):
        """Test MultiFactorRanker ranks items correctly."""
        from memory.retrieval_ranking import MultiFactorRanker, RankingItem

        ranker = MultiFactorRanker()

        items = [
            RankingItem(item_id="low", similarity_score=0.3, importance=0.3),
            RankingItem(item_id="high", similarity_score=0.9, importance=0.9),
            RankingItem(item_id="mid", similarity_score=0.6, importance=0.6),
        ]

        ranked = ranker.rank(items)

        # High should be first
        assert ranked[0].item_id == "high"
        assert ranked[0].final_score > ranked[1].final_score
        assert ranked[1].final_score > ranked[2].final_score

    def test_multi_factor_ranker_explain(self):
        """Test MultiFactorRanker can explain ranking."""
        from memory.retrieval_ranking import MultiFactorRanker, RankingItem

        ranker = MultiFactorRanker()
        item = RankingItem(
            item_id="test",
            similarity_score=0.8,
            importance=0.7,
        )

        # Rank first to compute scores
        ranker.rank([item])

        explanation = ranker.explain_ranking(item)
        assert "factor_contributions" in explanation
        assert "similarity" in explanation["factor_contributions"]
        assert "importance" in explanation["factor_contributions"]


class TestQueryClassifierStrategy:
    """Tests for QueryClassifier strategy determination (GMP-80-A6)."""

    def test_determine_retrieval_strategy_identity(self):
        """Test determine_retrieval_strategy for identity queries."""
        from memory.query_classifier import get_query_classifier

        classifier = get_query_classifier()
        strategy, reason = classifier.determine_retrieval_strategy(
            "What are my coding preferences?"
        )

        assert strategy == "core_identity"

    def test_determine_retrieval_strategy_temporal(self):
        """Test determine_retrieval_strategy for temporal queries."""
        from memory.query_classifier import get_query_classifier

        classifier = get_query_classifier()
        strategy, reason = classifier.determine_retrieval_strategy(
            "What happened last week?"
        )

        assert strategy == "temporal_recall"

    def test_determine_retrieval_strategy_with_context(self):
        """Test determine_retrieval_strategy with context."""
        from memory.query_classifier import get_query_classifier

        classifier = get_query_classifier()
        strategy, reason = classifier.determine_retrieval_strategy(
            "What is the project scope?",
            context={"project_id": "proj-123"},
        )

        assert strategy == "project_context"


# =============================================================================
# GMP-80-A7: Active Memory Management Tests
# =============================================================================


class TestActiveEncoder:
    """Tests for Active Memory Encoder (GMP-80-A7)."""

    def test_task_outcome_dataclass(self):
        """Test TaskOutcome dataclass creation."""
        from memory.active_encoder import TaskOutcome

        outcome = TaskOutcome(
            task_id=uuid4(),
            task_type="code_review",
            description="Review PR #123",
            outcome_text="Found 3 issues, suggested fixes",
            success=True,
            learnings=["User prefers explicit type hints"],
            entities_involved=["PR-123", "type-hints"],
            impact_score=0.7,
        )

        assert outcome.task_type == "code_review"
        assert outcome.success is True
        assert len(outcome.learnings) == 1
        assert outcome.impact_score == 0.7

    def test_extracted_learning_dataclass(self):
        """Test ExtractedLearning dataclass creation."""
        from memory.active_encoder import ExtractedLearning

        learning = ExtractedLearning(
            fact_text="User prefers explicit type hints",
            learning_type="preference",
            confidence=0.8,
            importance=0.7,
            tier="project",
            tags=["coding_style"],
        )

        assert learning.learning_type == "preference"
        assert learning.tier == "project"

    def test_learning_extractor_initialization(self):
        """Test LearningExtractor can be instantiated."""
        from memory.active_encoder import LearningExtractor

        extractor = LearningExtractor()
        assert extractor is not None

    def test_learning_extractor_extract_from_outcome(self):
        """Test LearningExtractor extracts from TaskOutcome."""
        from memory.active_encoder import LearningExtractor, TaskOutcome

        extractor = LearningExtractor()

        outcome = TaskOutcome(
            task_type="code_review",
            learnings=[
                "User prefers async/await",
                "Should use type hints next time",
            ],
            impact_score=0.6,
        )

        learnings = extractor.extract_learnings(outcome)

        assert len(learnings) >= 2
        # Check that preference pattern is detected
        pref_learning = next((l for l in learnings if "async" in l.fact_text), None)
        assert pref_learning is not None
        assert pref_learning.learning_type == "preference"

        # Check that correction pattern is detected
        corr_learning = next((l for l in learnings if "next time" in l.fact_text), None)
        assert corr_learning is not None
        assert corr_learning.learning_type == "correction"

    def test_active_encoder_initialization(self):
        """Test ActiveMemoryEncoder can be instantiated."""
        from memory.active_encoder import ActiveMemoryEncoder

        encoder = ActiveMemoryEncoder()
        assert encoder is not None

    def test_encoding_result_dataclass(self):
        """Test EncodingResult dataclass creation."""
        from memory.active_encoder import EncodingResult

        result = EncodingResult(
            facts_created=2,
            facts_updated=1,
            episodes_created=1,
            links_created=3,
        )

        assert result.facts_created == 2
        assert result.facts_updated == 1
        assert result.episodes_created == 1
        assert result.links_created == 3


class TestImportanceManager:
    """Tests for Importance Manager (GMP-80-A7)."""

    def test_importance_config_defaults(self):
        """Test ImportanceConfig default values."""
        from memory.importance_manager import ImportanceConfig

        config = ImportanceConfig()

        assert config.elevation_increment == 0.1
        assert config.elevation_cap == 0.95
        assert config.decay_half_life_days == 30.0
        assert config.decay_floor == 0.1
        assert "identity" in config.decay_exempt_tiers

    def test_importance_manager_initialization(self):
        """Test ImportanceManager can be instantiated."""
        from memory.importance_manager import ImportanceManager

        manager = ImportanceManager()
        assert manager is not None

    def test_importance_update_dataclass(self):
        """Test ImportanceUpdate dataclass creation."""
        from memory.importance_manager import ImportanceUpdate

        update = ImportanceUpdate(
            fact_id=uuid4(),
            old_importance=0.5,
            new_importance=0.6,
            reason="access:retrieval",
        )

        assert update.old_importance == 0.5
        assert update.new_importance == 0.6
        assert "retrieval" in update.reason

    def test_importance_manager_calculate_decay(self):
        """Test ImportanceManager decay calculation."""
        from memory.importance_manager import ImportanceManager

        manager = ImportanceManager()

        # 30 days ago = half-life, so importance should halve
        now = datetime.utcnow()
        thirty_days_ago = now - timedelta(days=30)

        decayed = manager._calculate_decay(1.0, thirty_days_ago, now)
        # Should be approximately 0.5 (half of 1.0)
        assert 0.45 <= decayed <= 0.55

    def test_importance_manager_calculate_decay_floor(self):
        """Test ImportanceManager respects decay floor."""
        from memory.importance_manager import ImportanceManager

        manager = ImportanceManager()

        # Very old access = should hit floor
        now = datetime.utcnow()
        ancient = now - timedelta(days=365)

        decayed = manager._calculate_decay(0.5, ancient, now)
        assert decayed == manager._config.decay_floor


# =============================================================================
# Integration Tests
# =============================================================================


class TestPipelineIntegration:
    """Integration tests for the complete GMP-80 pipeline."""

    def test_on_task_completion_import(self):
        """Test on_task_completion can be imported."""
        from memory.ingestion import on_task_completion

        assert callable(on_task_completion)

    def test_full_memory_exports(self):
        """Test all GMP-80 exports are available via direct import."""
        # GMP-80-A5 (direct import - not in main __init__.py)
        from memory.identity_tier import IdentityTierService
        from memory.context_builder import HierarchicalContextBuilder

        # GMP-80-A6 (direct import)
        from memory.retrieval_strategy import (
            RetrievalStrategy,
            StrategyBasedRetriever,
        )
        from memory.retrieval_ranking import MultiFactorRanker

        # GMP-80-A7 (exported in __init__.py)
        from memory import (
            ActiveMemoryEncoder,
            ImportanceManager,
        )

        # All imports successful
        assert IdentityTierService is not None
        assert HierarchicalContextBuilder is not None
        assert RetrievalStrategy is not None
        assert StrategyBasedRetriever is not None
        assert MultiFactorRanker is not None
        assert ActiveMemoryEncoder is not None
        assert ImportanceManager is not None

    def test_singleton_factories(self):
        """Test singleton factory functions return same instance."""
        from memory.retrieval_strategy import get_strategy_retriever
        from memory.retrieval_ranking import get_multi_factor_ranker
        from memory.active_encoder import get_active_encoder
        from memory.importance_manager import get_importance_manager

        # Each call should return the same singleton
        retriever1 = get_strategy_retriever()
        retriever2 = get_strategy_retriever()
        assert retriever1 is retriever2

        ranker1 = get_multi_factor_ranker()
        ranker2 = get_multi_factor_ranker()
        assert ranker1 is ranker2

        encoder1 = get_active_encoder()
        encoder2 = get_active_encoder()
        assert encoder1 is encoder2

        manager1 = get_importance_manager()
        manager2 = get_importance_manager()
        assert manager1 is manager2


# =============================================================================
# Pytest Configuration
# =============================================================================


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
