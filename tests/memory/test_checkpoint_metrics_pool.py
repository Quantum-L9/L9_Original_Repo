"""
Tests for checkpoint pool metrics (GMP-105 Batch 2).

Tests for:
- CHECKPOINT_POOL_* Prometheus gauges
- record_pool_stats() function
- get_pool_stats_dict() function
"""

import pytest
from unittest.mock import patch

from memory.checkpoint_metrics import (
    record_pool_stats,
    get_pool_stats_dict,
    CHECKPOINT_POOL_SIZE,
    CHECKPOINT_POOL_AVAILABLE,
    CHECKPOINT_POOL_WAITING,
    PROMETHEUS_AVAILABLE,
)


# ============================================================================
# Pool Stats Recording Tests
# ============================================================================


class TestRecordPoolStats:
    """Test record_pool_stats function."""

    def test_record_all_stats(self):
        """Test recording all pool stats."""
        # Should not raise
        record_pool_stats(
            pool_size=10,
            pool_available=7,
            requests_waiting=2,
        )

    def test_record_partial_stats(self):
        """Test recording partial pool stats (unknown values as -1)."""
        # Should not raise, -1 values should be skipped
        record_pool_stats(
            pool_size=10,
            pool_available=-1,  # Unknown
            requests_waiting=0,
        )

    def test_record_defaults(self):
        """Test recording with default values."""
        # All defaults are -1, should not update any gauges
        record_pool_stats()

    def test_record_zero_values(self):
        """Test recording zero values (valid pool state)."""
        record_pool_stats(
            pool_size=0,
            pool_available=0,
            requests_waiting=0,
        )


class TestGetPoolStatsDict:
    """Test get_pool_stats_dict function."""

    def test_returns_dict(self):
        """Test that function returns a dict."""
        result = get_pool_stats_dict()
        assert isinstance(result, dict)

    def test_contains_required_keys(self):
        """Test that result contains required keys."""
        result = get_pool_stats_dict()
        assert "pool_size" in result
        assert "pool_available" in result
        assert "requests_waiting" in result
        assert "prometheus_available" in result

    def test_prometheus_available_flag(self):
        """Test prometheus_available matches module constant."""
        result = get_pool_stats_dict()
        assert result["prometheus_available"] == PROMETHEUS_AVAILABLE


# ============================================================================
# Prometheus Gauge Tests
# ============================================================================


class TestPrometheusGauges:
    """Test Prometheus gauge definitions."""

    def test_gauges_exist(self):
        """Test that pool gauges are defined."""
        assert CHECKPOINT_POOL_SIZE is not None
        assert CHECKPOINT_POOL_AVAILABLE is not None
        assert CHECKPOINT_POOL_WAITING is not None

    @pytest.mark.skipif(
        not PROMETHEUS_AVAILABLE,
        reason="prometheus_client not installed",
    )
    def test_gauges_are_prometheus_gauges(self):
        """Test that gauges are actual Prometheus Gauge instances."""
        from prometheus_client import Gauge as PrometheusGauge

        assert isinstance(CHECKPOINT_POOL_SIZE, PrometheusGauge)
        assert isinstance(CHECKPOINT_POOL_AVAILABLE, PrometheusGauge)
        assert isinstance(CHECKPOINT_POOL_WAITING, PrometheusGauge)


# ============================================================================
# Module Exports Tests
# ============================================================================


class TestModuleExports:
    """Test module exports are correct."""

    def test_exports_include_pool_stats_function(self):
        """Test that record_pool_stats is exported."""
        from memory import checkpoint_metrics

        assert hasattr(checkpoint_metrics, "record_pool_stats")
        assert hasattr(checkpoint_metrics, "get_pool_stats_dict")

    def test_exports_include_pool_gauges(self):
        """Test that pool gauges are exported."""
        from memory import checkpoint_metrics

        assert hasattr(checkpoint_metrics, "CHECKPOINT_POOL_SIZE")
        assert hasattr(checkpoint_metrics, "CHECKPOINT_POOL_AVAILABLE")
        assert hasattr(checkpoint_metrics, "CHECKPOINT_POOL_WAITING")

    def test_all_list_updated(self):
        """Test that __all__ includes new exports."""
        from memory.checkpoint_metrics import __all__

        assert "record_pool_stats" in __all__
        assert "get_pool_stats_dict" in __all__
        assert "CHECKPOINT_POOL_SIZE" in __all__
        assert "CHECKPOINT_POOL_AVAILABLE" in __all__
        assert "CHECKPOINT_POOL_WAITING" in __all__


# ============================================================================
# Integration Tests
# ============================================================================


class TestPoolStatsIntegration:
    """Integration tests for pool stats workflow."""

    def test_record_then_get_workflow(self):
        """Test recording stats then getting dict (basic workflow)."""
        # Record some stats
        record_pool_stats(pool_size=10, pool_available=5, requests_waiting=1)

        # Get stats dict (note: Prometheus doesn't have native "get" for gauges)
        result = get_pool_stats_dict()

        # Dict should be valid (values indicate checking Prometheus)
        assert result["prometheus_available"] == PROMETHEUS_AVAILABLE

    def test_logging_called(self):
        """Test that logging is called on record."""
        with patch("memory.checkpoint_metrics.logger") as mock_logger:
            record_pool_stats(pool_size=10, pool_available=8, requests_waiting=0)
            mock_logger.debug.assert_called_once()
