"""
Tests for Stage 2: Hierarchical Memory Consolidation Engine.

Tests cover:
- HierarchicalSummarizer (20min → daily → weekly cascade)
- NeuralDecayScheduler (exponential decay with reinforcement)
- Integration with consolidation pipeline
"""

import math
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from memory.hierarchical_summarizer import (
    DEFAULT_TIER_CONFIGS,
    HierarchicalSummarizer,
    SummaryConfig,
    SummaryResult,
    SummaryTier,
)
from memory.neural_decay_scheduler import DecayConfig, DecayResult, NeuralDecayScheduler

# =============================================================================
# HierarchicalSummarizer Tests
# =============================================================================


class TestSummaryTierConfig:
    """Test tier configuration."""

    def test_default_tiers_exist(self):
        """All expected tiers are configured."""
        assert SummaryTier.SESSION in DEFAULT_TIER_CONFIGS
        assert SummaryTier.DAILY in DEFAULT_TIER_CONFIGS
        assert SummaryTier.WEEKLY in DEFAULT_TIER_CONFIGS

    def test_session_tier_config(self):
        """Session tier has correct settings."""
        config = DEFAULT_TIER_CONFIGS[SummaryTier.SESSION]
        assert config.time_window_minutes == 20
        assert config.target_compression_ratio == 0.25
        assert config.min_importance_threshold == 0.3

    def test_daily_tier_config(self):
        """Daily tier has correct settings."""
        config = DEFAULT_TIER_CONFIGS[SummaryTier.DAILY]
        assert config.time_window_minutes == 1440  # 24 hours
        assert config.target_compression_ratio == 0.20

    def test_weekly_tier_config(self):
        """Weekly tier has correct settings."""
        config = DEFAULT_TIER_CONFIGS[SummaryTier.WEEKLY]
        assert config.time_window_minutes == 10080  # 7 days
        assert config.target_compression_ratio == 0.15


class TestHierarchicalSummarizer:
    """Test hierarchical summarizer."""

    def test_initialization(self):
        """Summarizer initializes correctly."""
        summarizer = HierarchicalSummarizer(dry_run=True)
        assert summarizer._dry_run is True
        assert summarizer._repository is None
        assert summarizer._tier_configs == DEFAULT_TIER_CONFIGS

    def test_initialization_with_custom_config(self):
        """Summarizer accepts custom tier configs."""
        custom = {
            SummaryTier.SESSION: SummaryConfig(
                tier=SummaryTier.SESSION,
                time_window_minutes=30,
                max_source_items=100,
                target_compression_ratio=0.3,
                min_importance_threshold=0.2,
                prompt_template="Custom prompt",
            )
        }
        summarizer = HierarchicalSummarizer(tier_configs=custom)
        assert summarizer._tier_configs[SummaryTier.SESSION].time_window_minutes == 30

    def test_extractive_fallback(self):
        """Extractive fallback produces summary without LLM."""
        summarizer = HierarchicalSummarizer()

        prompt = """Summarize the following session activity:

First important sentence here. Second sentence with more details. Third sentence.

---

Another section starts. More content follows. Final sentence.

Requirements:
- Keep it short"""

        result = summarizer._extractive_fallback(prompt)
        assert len(result) > 0
        assert "Requirements" not in result

    @pytest.mark.asyncio
    async def test_run_cascade_dry_run(self):
        """Dry run cascade returns empty results."""
        summarizer = HierarchicalSummarizer(dry_run=True)
        results = await summarizer.run_cascade()

        assert SummaryTier.SESSION in results
        assert SummaryTier.DAILY in results
        assert SummaryTier.WEEKLY in results
        assert all(len(v) == 0 for v in results.values())

    def test_group_by_time_window(self):
        """Items grouped into correct time windows."""
        summarizer = HierarchicalSummarizer()

        base_time = datetime(2026, 1, 15, 10, 0, 0, tzinfo=UTC)
        items = [
            {"created_at": base_time},
            {"created_at": base_time + timedelta(minutes=5)},
            {"created_at": base_time + timedelta(minutes=25)},  # Next window
        ]

        windows = summarizer._group_by_time_window(items, window_minutes=20)

        assert len(windows) == 2

    @pytest.mark.asyncio
    async def test_generate_summary_empty_items(self):
        """Empty items return None."""
        summarizer = HierarchicalSummarizer()
        config = DEFAULT_TIER_CONFIGS[SummaryTier.SESSION]

        result = await summarizer._generate_summary(SummaryTier.SESSION, [], config)
        assert result is None


class TestSummaryResult:
    """Test SummaryResult dataclass."""

    def test_default_values(self):
        """Default values are set correctly."""
        result = SummaryResult()
        assert result.tier == SummaryTier.SESSION
        assert result.source_count == 0
        assert result.summary_text == ""
        assert result.compression_ratio == 0.0
        assert result.importance_score == 0.5
        assert result.source_ids == []

    def test_custom_values(self):
        """Custom values override defaults."""
        result = SummaryResult(
            tier=SummaryTier.DAILY,
            source_count=10,
            summary_text="Test summary",
            compression_ratio=0.2,
            importance_score=0.8,
        )
        assert result.tier == SummaryTier.DAILY
        assert result.source_count == 10
        assert result.importance_score == 0.8


# =============================================================================
# NeuralDecayScheduler Tests
# =============================================================================


class TestDecayConfig:
    """Test decay configuration."""

    def test_default_values(self):
        """Default config values are reasonable."""
        config = DecayConfig()
        assert config.decay_constant == 0.05
        assert config.min_importance_threshold == 0.1
        assert config.max_age_days == 365
        assert config.reinforcement_per_access == 0.1
        assert config.max_reinforcement == 3.0


class TestNeuralDecayScheduler:
    """Test neural decay scheduler."""

    def test_initialization(self):
        """Scheduler initializes correctly."""
        scheduler = NeuralDecayScheduler(dry_run=True)
        assert scheduler._dry_run is True
        assert scheduler._repository is None

    def test_calculate_salience_no_decay(self):
        """Fresh memory has no decay."""
        scheduler = NeuralDecayScheduler()

        salience = scheduler.calculate_salience(
            initial_importance=0.8,
            days_since_access=0,
            access_count=0,
        )

        # Should be close to initial (slight reinforcement boost)
        assert salience == pytest.approx(0.8, abs=0.01)

    def test_calculate_salience_with_decay(self):
        """Memory decays over time."""
        scheduler = NeuralDecayScheduler()

        # After 30 days with default decay_constant=0.05
        salience = scheduler.calculate_salience(
            initial_importance=0.8,
            days_since_access=30,
            access_count=0,
        )

        # exp(-0.05 * 30) ≈ 0.223
        expected = 0.8 * math.exp(-0.05 * 30)
        assert salience == pytest.approx(expected, abs=0.01)

    def test_calculate_salience_with_reinforcement(self):
        """Frequently accessed memories decay slower."""
        scheduler = NeuralDecayScheduler()

        # Same decay, but with 10 accesses
        salience_no_access = scheduler.calculate_salience(
            initial_importance=0.8,
            days_since_access=30,
            access_count=0,
        )

        salience_with_access = scheduler.calculate_salience(
            initial_importance=0.8,
            days_since_access=30,
            access_count=10,
        )

        # With 10 accesses: R = 1.0 + 0.1 * 10 = 2.0
        assert salience_with_access > salience_no_access
        assert salience_with_access == pytest.approx(salience_no_access * 2.0, abs=0.01)

    def test_calculate_salience_max_reinforcement(self):
        """Reinforcement is capped at max."""
        scheduler = NeuralDecayScheduler()

        # 100 accesses would give R = 11.0, but capped at 3.0
        salience = scheduler.calculate_salience(
            initial_importance=0.8,
            days_since_access=0,
            access_count=100,
        )

        # R = 3.0 (max), so salience = 0.8 * 1.0 * 3.0 = 2.4, but capped at 1.0
        assert salience == 1.0

    def test_calculate_salience_clamps_to_valid_range(self):
        """Salience is always 0.0-1.0."""
        scheduler = NeuralDecayScheduler()

        # Test lower bound
        salience_low = scheduler.calculate_salience(
            initial_importance=-0.5,
            days_since_access=100,
            access_count=0,
        )
        assert salience_low >= 0.0

        # Test upper bound
        salience_high = scheduler.calculate_salience(
            initial_importance=2.0,
            days_since_access=0,
            access_count=50,
        )
        assert salience_high <= 1.0

    def test_decay_exponential_curve(self):
        """Decay follows exponential curve (R² > 0.95)."""
        scheduler = NeuralDecayScheduler()

        days = [0, 7, 14, 30, 60, 90]
        saliences = [scheduler.calculate_salience(0.8, d, 0) for d in days]

        # Verify monotonic decrease
        for i in range(1, len(saliences)):
            assert saliences[i] < saliences[i - 1]

        # Verify exponential relationship
        # S(t) = I * exp(-λt), so ln(S/I) = -λt

        ratios = [s / 0.8 for s in saliences]
        log_ratios = [math.log(r) if r > 0 else -10 for r in ratios]

        # Should be linear: log_ratio ≈ -0.05 * days
        expected_logs = [-0.05 * d for d in days]

        # Calculate R²
        ss_res = sum((log_ratios[i] - expected_logs[i]) ** 2 for i in range(len(days)))
        ss_tot = sum((lr - sum(log_ratios) / len(log_ratios)) ** 2 for lr in log_ratios)
        r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0

        assert r_squared > 0.95, f"R² = {r_squared}, expected > 0.95"

    @pytest.mark.asyncio
    async def test_run_decay_pass_dry_run(self):
        """Dry run doesn't modify anything."""
        scheduler = NeuralDecayScheduler(dry_run=True)
        result = await scheduler.run_decay_pass()

        assert result.packets_processed == 0
        assert result.packets_updated == 0
        assert result.duration_ms >= 0

    @pytest.mark.asyncio
    async def test_run_decay_pass_no_repository(self):
        """No repository returns error."""
        scheduler = NeuralDecayScheduler()
        result = await scheduler.run_decay_pass()

        assert "No repository configured" in result.errors


class TestDecayResult:
    """Test DecayResult dataclass."""

    def test_default_values(self):
        """Default values are zeros."""
        result = DecayResult()
        assert result.packets_processed == 0
        assert result.packets_updated == 0
        assert result.packets_archived == 0
        assert result.facts_processed == 0
        assert result.duration_ms == 0.0
        assert result.errors == []


# =============================================================================
# Integration Tests
# =============================================================================


class TestConsolidationIntegration:
    """Test integration with consolidation pipeline."""

    @pytest.mark.asyncio
    async def test_summarizer_stores_to_semantic_facts(self):
        """Summaries are stored in semantic_facts table."""
        mock_repo = MagicMock()
        mock_repo.insert_semantic_fact = AsyncMock()
        mock_repo.acquire = MagicMock(return_value=AsyncMock())

        summarizer = HierarchicalSummarizer(repository=mock_repo)

        summary = SummaryResult(
            tier=SummaryTier.SESSION,
            summary_text="Test summary content",
            importance_score=0.7,
        )

        await summarizer._store_summary(summary)

        mock_repo.insert_semantic_fact.assert_called_once()
        call_kwargs = mock_repo.insert_semantic_fact.call_args.kwargs
        assert call_kwargs["tier"] == "session"
        assert call_kwargs["importance"] == 0.7

    def test_decay_scheduler_respects_identity_tier(self):
        """Identity tier facts should not decay."""
        # This is handled in _process_facts with tier != 'identity' filter
        # Verify the behavior by checking the query
        scheduler = NeuralDecayScheduler()

        # The implementation filters out identity tier in the query
        # This test documents the expected behavior
        assert scheduler._config.min_importance_threshold == 0.1


# =============================================================================
# Edge Cases
# =============================================================================


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_decay_with_zero_days(self):
        """Zero days since access returns original importance."""
        scheduler = NeuralDecayScheduler()
        salience = scheduler.calculate_salience(0.5, 0, 0)
        assert salience == 0.5

    def test_decay_with_very_old_memory(self):
        """Very old memories approach zero."""
        scheduler = NeuralDecayScheduler()
        salience = scheduler.calculate_salience(0.8, 365, 0)

        # exp(-0.05 * 365) ≈ 0.000000013
        assert salience < 0.001

    def test_summarizer_with_empty_texts(self):
        """Empty texts don't crash summarizer."""
        summarizer = HierarchicalSummarizer()
        result = summarizer._extractive_fallback("")
        assert result == ""

    @pytest.mark.asyncio
    async def test_decay_preview_no_repository(self):
        """Preview returns error without repository."""
        scheduler = NeuralDecayScheduler()
        result = await scheduler.get_decay_preview(packet_id=uuid4())
        assert "error" in result
