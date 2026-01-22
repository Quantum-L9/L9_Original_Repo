"""
Memory Metrics Tests
====================

Comprehensive tests for telemetry/memory_metrics.py.
Tests Prometheus metric recording, graceful degradation,
and all metric types (Counter, Histogram, Gauge).

Coverage targets:
- init_metrics()
- record_memory_write()
- record_memory_search()
- record_tool_invocation()
- set_memory_substrate_health()
- update_packet_store_size()
- Graceful degradation when prometheus_client unavailable
"""

import pytest


class TestPrometheusAvailability:
    """Tests for prometheus_client availability detection."""

    def test_prometheus_available_flag_exists(self):
        """Contract: PROMETHEUS_AVAILABLE flag is defined."""
        from telemetry.memory_metrics import PROMETHEUS_AVAILABLE

        assert isinstance(PROMETHEUS_AVAILABLE, bool)

    def test_prometheus_available_when_installed(self):
        """Contract: PROMETHEUS_AVAILABLE is True when prometheus_client is installed."""
        from telemetry.memory_metrics import PROMETHEUS_AVAILABLE

        # We installed prometheus_client, so it should be True
        assert PROMETHEUS_AVAILABLE is True


class TestInitMetrics:
    """Tests for init_metrics initialization function."""

    def test_init_metrics_returns_true_when_available(self):
        """Contract: init_metrics returns True when Prometheus is available."""
        from telemetry.memory_metrics import PROMETHEUS_AVAILABLE, init_metrics

        if PROMETHEUS_AVAILABLE:
            result = init_metrics()
            assert result is True

    def test_init_metrics_sets_initial_health(self):
        """Contract: init_metrics sets initial substrate health to healthy."""
        from telemetry.memory_metrics import (MEMORY_SUBSTRATE_HEALTHY,
                                              init_metrics)

        init_metrics()
        # Gauge should be set to 1 (healthy)
        # We can verify by checking the gauge's internal state
        # Note: This accesses internal prometheus_client implementation
        assert MEMORY_SUBSTRATE_HEALTHY._value._value == 1.0

    def test_init_metrics_idempotent(self):
        """Contract: init_metrics can be called multiple times safely."""
        from telemetry.memory_metrics import init_metrics

        result1 = init_metrics()
        result2 = init_metrics()
        result3 = init_metrics()

        assert result1 == result2 == result3


class TestRecordMemoryWrite:
    """Tests for record_memory_write function."""

    def test_record_memory_write_increments_counter(self):
        """Contract: record_memory_write increments the write counter."""
        from telemetry.memory_metrics import (MEMORY_WRITE_TOTAL,
                                              PROMETHEUS_AVAILABLE,
                                              record_memory_write)

        if not PROMETHEUS_AVAILABLE:
            pytest.skip("Prometheus not available")

        # Get initial value
        initial = MEMORY_WRITE_TOTAL.labels(
            segment="tool_audit", status="ok"
        )._value._value

        record_memory_write(segment="tool_audit", status="ok")

        # Verify increment
        new_value = MEMORY_WRITE_TOTAL.labels(
            segment="tool_audit", status="ok"
        )._value._value
        assert new_value == initial + 1

    def test_record_memory_write_with_duration(self):
        """Contract: record_memory_write records duration when provided."""
        from telemetry.memory_metrics import (PROMETHEUS_AVAILABLE,
                                              record_memory_write)

        if not PROMETHEUS_AVAILABLE:
            pytest.skip("Prometheus not available")

        # Should not raise
        record_memory_write(
            segment="project_history",
            status="ok",
            duration_seconds=0.5,
        )

    def test_record_memory_write_different_segments(self):
        """Contract: Different segments are tracked separately."""
        from telemetry.memory_metrics import (MEMORY_WRITE_TOTAL,
                                              PROMETHEUS_AVAILABLE,
                                              record_memory_write)

        if not PROMETHEUS_AVAILABLE:
            pytest.skip("Prometheus not available")

        # Record to different segments
        record_memory_write(segment="governance_meta", status="ok")
        record_memory_write(segment="session_context", status="ok")

        # Both should be tracked
        gov_val = MEMORY_WRITE_TOTAL.labels(
            segment="governance_meta", status="ok"
        )._value._value
        session_val = MEMORY_WRITE_TOTAL.labels(
            segment="session_context", status="ok"
        )._value._value

        assert gov_val >= 1
        assert session_val >= 1

    def test_record_memory_write_different_statuses(self):
        """Contract: Different statuses are tracked separately."""
        from telemetry.memory_metrics import (MEMORY_WRITE_TOTAL,
                                              PROMETHEUS_AVAILABLE,
                                              record_memory_write)

        if not PROMETHEUS_AVAILABLE:
            pytest.skip("Prometheus not available")

        record_memory_write(segment="test_segment", status="ok")
        record_memory_write(segment="test_segment", status="partial")
        record_memory_write(segment="test_segment", status="error")

        # All three statuses tracked
        ok_val = MEMORY_WRITE_TOTAL.labels(
            segment="test_segment", status="ok"
        )._value._value
        partial_val = MEMORY_WRITE_TOTAL.labels(
            segment="test_segment", status="partial"
        )._value._value
        error_val = MEMORY_WRITE_TOTAL.labels(
            segment="test_segment", status="error"
        )._value._value

        assert ok_val >= 1
        assert partial_val >= 1
        assert error_val >= 1

    def test_record_memory_write_never_raises(self):
        """Contract: record_memory_write never raises exceptions."""
        from telemetry.memory_metrics import record_memory_write

        # Even with bizarre inputs, should not raise
        record_memory_write(segment="", status="")
        record_memory_write(segment="x" * 1000, status="weird_status")


class TestRecordMemorySearch:
    """Tests for record_memory_search function."""

    def test_record_memory_search_increments_counter(self):
        """Contract: record_memory_search increments the search counter."""
        from telemetry.memory_metrics import (MEMORY_SEARCH_TOTAL,
                                              PROMETHEUS_AVAILABLE,
                                              record_memory_search)

        if not PROMETHEUS_AVAILABLE:
            pytest.skip("Prometheus not available")

        initial = MEMORY_SEARCH_TOTAL.labels(
            segment="project_history", search_type="semantic"
        )._value._value

        record_memory_search(
            segment="project_history", hit_count=5, search_type="semantic"
        )

        new_value = MEMORY_SEARCH_TOTAL.labels(
            segment="project_history", search_type="semantic"
        )._value._value
        assert new_value == initial + 1

    def test_record_memory_search_records_hits(self):
        """Contract: record_memory_search records hit count histogram."""
        from telemetry.memory_metrics import (MEMORY_SEARCH_HITS,
                                              PROMETHEUS_AVAILABLE,
                                              record_memory_search)

        if not PROMETHEUS_AVAILABLE:
            pytest.skip("Prometheus not available")

        record_memory_search(segment="tool_audit", hit_count=10)

        # Histogram should have recorded observation
        # Check sum includes our value
        hist = MEMORY_SEARCH_HITS.labels(segment="tool_audit")
        assert hist._sum._value >= 10

    def test_record_memory_search_different_types(self):
        """Contract: Different search types are tracked."""
        from telemetry.memory_metrics import (MEMORY_SEARCH_TOTAL,
                                              PROMETHEUS_AVAILABLE,
                                              record_memory_search)

        if not PROMETHEUS_AVAILABLE:
            pytest.skip("Prometheus not available")

        record_memory_search(segment="test", search_type="semantic")
        record_memory_search(segment="test", search_type="exact")
        record_memory_search(segment="test", search_type="hybrid")

        semantic = MEMORY_SEARCH_TOTAL.labels(
            segment="test", search_type="semantic"
        )._value._value
        exact = MEMORY_SEARCH_TOTAL.labels(
            segment="test", search_type="exact"
        )._value._value
        hybrid = MEMORY_SEARCH_TOTAL.labels(
            segment="test", search_type="hybrid"
        )._value._value

        assert semantic >= 1
        assert exact >= 1
        assert hybrid >= 1

    def test_record_memory_search_zero_hits(self):
        """Contract: Zero hits is valid and recorded."""
        from telemetry.memory_metrics import (PROMETHEUS_AVAILABLE,
                                              record_memory_search)

        if not PROMETHEUS_AVAILABLE:
            pytest.skip("Prometheus not available")

        # Should not raise
        record_memory_search(segment="empty_search", hit_count=0)

    def test_record_memory_search_never_raises(self):
        """Contract: record_memory_search never raises exceptions."""
        from telemetry.memory_metrics import record_memory_search

        record_memory_search(segment="", hit_count=-1)  # Invalid but shouldn't crash


class TestRecordToolInvocation:
    """Tests for record_tool_invocation function."""

    def test_record_tool_invocation_increments_counter(self):
        """Contract: record_tool_invocation increments the invocation counter."""
        from telemetry.memory_metrics import (PROMETHEUS_AVAILABLE,
                                              TOOL_INVOCATION_TOTAL,
                                              record_tool_invocation)

        if not PROMETHEUS_AVAILABLE:
            pytest.skip("Prometheus not available")

        initial = TOOL_INVOCATION_TOTAL.labels(
            tool_id="test_tool_counter", status="success"
        )._value._value

        record_tool_invocation(
            tool_id="test_tool_counter", status="success", duration_ms=100
        )

        new_value = TOOL_INVOCATION_TOTAL.labels(
            tool_id="test_tool_counter", status="success"
        )._value._value
        assert new_value == initial + 1

    def test_record_tool_invocation_records_duration(self):
        """Contract: record_tool_invocation records duration histogram."""
        from telemetry.memory_metrics import (PROMETHEUS_AVAILABLE,
                                              TOOL_INVOCATION_DURATION,
                                              record_tool_invocation)

        if not PROMETHEUS_AVAILABLE:
            pytest.skip("Prometheus not available")

        record_tool_invocation(
            tool_id="duration_test", status="success", duration_ms=250
        )

        hist = TOOL_INVOCATION_DURATION.labels(tool_id="duration_test")
        assert hist._sum._value >= 250

    def test_record_tool_invocation_different_statuses(self):
        """Contract: Different statuses are tracked separately."""
        from telemetry.memory_metrics import (PROMETHEUS_AVAILABLE,
                                              TOOL_INVOCATION_TOTAL,
                                              record_tool_invocation)

        if not PROMETHEUS_AVAILABLE:
            pytest.skip("Prometheus not available")

        record_tool_invocation(tool_id="status_test", status="success", duration_ms=10)
        record_tool_invocation(tool_id="status_test", status="failure", duration_ms=10)
        record_tool_invocation(tool_id="status_test", status="denied", duration_ms=10)
        record_tool_invocation(tool_id="status_test", status="timeout", duration_ms=10)

        success = TOOL_INVOCATION_TOTAL.labels(
            tool_id="status_test", status="success"
        )._value._value
        failure = TOOL_INVOCATION_TOTAL.labels(
            tool_id="status_test", status="failure"
        )._value._value
        denied = TOOL_INVOCATION_TOTAL.labels(
            tool_id="status_test", status="denied"
        )._value._value
        timeout = TOOL_INVOCATION_TOTAL.labels(
            tool_id="status_test", status="timeout"
        )._value._value

        assert success >= 1
        assert failure >= 1
        assert denied >= 1
        assert timeout >= 1

    def test_record_tool_invocation_zero_duration(self):
        """Contract: Zero duration is valid (e.g., for denied calls)."""
        from telemetry.memory_metrics import (PROMETHEUS_AVAILABLE,
                                              record_tool_invocation)

        if not PROMETHEUS_AVAILABLE:
            pytest.skip("Prometheus not available")

        # Should not raise
        record_tool_invocation(tool_id="zero_duration", status="denied", duration_ms=0)

    def test_record_tool_invocation_high_duration(self):
        """Contract: High duration values are recorded correctly."""
        from telemetry.memory_metrics import (PROMETHEUS_AVAILABLE,
                                              TOOL_INVOCATION_DURATION,
                                              record_tool_invocation)

        if not PROMETHEUS_AVAILABLE:
            pytest.skip("Prometheus not available")

        # 5 minutes in ms
        record_tool_invocation(
            tool_id="slow_tool", status="success", duration_ms=300000
        )

        hist = TOOL_INVOCATION_DURATION.labels(tool_id="slow_tool")
        assert hist._sum._value >= 300000

    def test_record_tool_invocation_never_raises(self):
        """Contract: record_tool_invocation never raises exceptions."""
        from telemetry.memory_metrics import record_tool_invocation

        # Even with bizarre inputs
        record_tool_invocation(tool_id="", status="", duration_ms=-1)


class TestSetMemorySubstrateHealth:
    """Tests for set_memory_substrate_health function."""

    def test_set_health_to_healthy(self):
        """Contract: Setting health to True sets gauge to 1."""
        from telemetry.memory_metrics import (MEMORY_SUBSTRATE_HEALTHY,
                                              PROMETHEUS_AVAILABLE,
                                              set_memory_substrate_health)

        if not PROMETHEUS_AVAILABLE:
            pytest.skip("Prometheus not available")

        set_memory_substrate_health(True)
        assert MEMORY_SUBSTRATE_HEALTHY._value._value == 1.0

    def test_set_health_to_unhealthy(self):
        """Contract: Setting health to False sets gauge to 0."""
        from telemetry.memory_metrics import (MEMORY_SUBSTRATE_HEALTHY,
                                              PROMETHEUS_AVAILABLE,
                                              set_memory_substrate_health)

        if not PROMETHEUS_AVAILABLE:
            pytest.skip("Prometheus not available")

        set_memory_substrate_health(False)
        assert MEMORY_SUBSTRATE_HEALTHY._value._value == 0.0

        # Reset to healthy for other tests
        set_memory_substrate_health(True)

    def test_set_health_toggle(self):
        """Contract: Health can be toggled between healthy and unhealthy."""
        from telemetry.memory_metrics import (MEMORY_SUBSTRATE_HEALTHY,
                                              PROMETHEUS_AVAILABLE,
                                              set_memory_substrate_health)

        if not PROMETHEUS_AVAILABLE:
            pytest.skip("Prometheus not available")

        set_memory_substrate_health(True)
        assert MEMORY_SUBSTRATE_HEALTHY._value._value == 1.0

        set_memory_substrate_health(False)
        assert MEMORY_SUBSTRATE_HEALTHY._value._value == 0.0

        set_memory_substrate_health(True)
        assert MEMORY_SUBSTRATE_HEALTHY._value._value == 1.0

    def test_set_health_never_raises(self):
        """Contract: set_memory_substrate_health never raises."""
        from telemetry.memory_metrics import set_memory_substrate_health

        # Should not raise with any boolean
        set_memory_substrate_health(True)
        set_memory_substrate_health(False)


class TestUpdatePacketStoreSize:
    """Tests for update_packet_store_size function."""

    def test_update_packet_store_size_sets_gauge(self):
        """Contract: update_packet_store_size sets the gauge value."""
        from telemetry.memory_metrics import (PACKET_STORE_SIZE,
                                              PROMETHEUS_AVAILABLE,
                                              update_packet_store_size)

        if not PROMETHEUS_AVAILABLE:
            pytest.skip("Prometheus not available")

        update_packet_store_size(segment="tool_audit", count=1000)

        gauge = PACKET_STORE_SIZE.labels(segment="tool_audit")
        assert gauge._value._value == 1000

    def test_update_packet_store_size_different_segments(self):
        """Contract: Different segments have independent gauge values."""
        from telemetry.memory_metrics import (PACKET_STORE_SIZE,
                                              PROMETHEUS_AVAILABLE,
                                              update_packet_store_size)

        if not PROMETHEUS_AVAILABLE:
            pytest.skip("Prometheus not available")

        update_packet_store_size(segment="governance_meta", count=50)
        update_packet_store_size(segment="project_history", count=500)
        update_packet_store_size(segment="session_context", count=200)

        gov = PACKET_STORE_SIZE.labels(segment="governance_meta")._value._value
        proj = PACKET_STORE_SIZE.labels(segment="project_history")._value._value
        session = PACKET_STORE_SIZE.labels(segment="session_context")._value._value

        assert gov == 50
        assert proj == 500
        assert session == 200

    def test_update_packet_store_size_overwrites(self):
        """Contract: Gauge value is overwritten, not accumulated."""
        from telemetry.memory_metrics import (PACKET_STORE_SIZE,
                                              PROMETHEUS_AVAILABLE,
                                              update_packet_store_size)

        if not PROMETHEUS_AVAILABLE:
            pytest.skip("Prometheus not available")

        update_packet_store_size(segment="overwrite_test", count=100)
        update_packet_store_size(segment="overwrite_test", count=50)

        gauge = PACKET_STORE_SIZE.labels(segment="overwrite_test")
        assert gauge._value._value == 50  # Overwritten, not accumulated

    def test_update_packet_store_size_zero(self):
        """Contract: Zero count is valid."""
        from telemetry.memory_metrics import (PACKET_STORE_SIZE,
                                              PROMETHEUS_AVAILABLE,
                                              update_packet_store_size)

        if not PROMETHEUS_AVAILABLE:
            pytest.skip("Prometheus not available")

        update_packet_store_size(segment="empty_segment", count=0)

        gauge = PACKET_STORE_SIZE.labels(segment="empty_segment")
        assert gauge._value._value == 0

    def test_update_packet_store_size_never_raises(self):
        """Contract: update_packet_store_size never raises."""
        from telemetry.memory_metrics import update_packet_store_size

        update_packet_store_size(segment="", count=-1)  # Invalid but shouldn't crash


class TestPublicAPI:
    """Tests for public API exports."""

    def test_all_exports(self):
        """Contract: __all__ contains expected exports."""
        from telemetry.memory_metrics import __all__

        expected = [
            "PROMETHEUS_AVAILABLE",
            "record_memory_write",
            "record_memory_search",
            "record_tool_invocation",
            "set_memory_substrate_health",
            "update_packet_store_size",
            "init_metrics",
        ]

        for item in expected:
            assert item in __all__, f"Missing export: {item}"

    def test_exports_are_callable(self):
        """Contract: All function exports are callable."""
        from telemetry.memory_metrics import (init_metrics,
                                              record_memory_search,
                                              record_memory_write,
                                              record_tool_invocation,
                                              set_memory_substrate_health,
                                              update_packet_store_size)

        assert callable(record_memory_write)
        assert callable(record_memory_search)
        assert callable(record_tool_invocation)
        assert callable(set_memory_substrate_health)
        assert callable(update_packet_store_size)
        assert callable(init_metrics)


class TestGracefulDegradation:
    """Tests for graceful degradation when prometheus_client unavailable."""

    def test_functions_handle_prometheus_unavailable(self):
        """Contract: All recording functions handle PROMETHEUS_AVAILABLE=False."""
        # These functions should have early returns when prometheus unavailable
        # We test this by mocking PROMETHEUS_AVAILABLE

        import telemetry.memory_metrics as metrics

        # Store original
        original = metrics.PROMETHEUS_AVAILABLE

        try:
            # Mock as unavailable
            metrics.PROMETHEUS_AVAILABLE = False

            # All these should return without error
            metrics.record_memory_write(segment="test", status="ok")
            metrics.record_memory_search(segment="test", hit_count=5)
            metrics.record_tool_invocation(
                tool_id="test", status="success", duration_ms=10
            )
            metrics.set_memory_substrate_health(True)
            metrics.update_packet_store_size(segment="test", count=100)
            result = metrics.init_metrics()

            # init_metrics should return False when unavailable
            assert result is False

        finally:
            # Restore
            metrics.PROMETHEUS_AVAILABLE = original


class TestMetricLabels:
    """Tests for metric label handling."""

    def test_tool_invocation_labels(self):
        """Contract: Tool invocation metrics use correct labels."""
        from telemetry.memory_metrics import (PROMETHEUS_AVAILABLE,
                                              TOOL_INVOCATION_TOTAL)

        if not PROMETHEUS_AVAILABLE:
            pytest.skip("Prometheus not available")

        # Verify label names
        assert "tool_id" in TOOL_INVOCATION_TOTAL._labelnames
        assert "status" in TOOL_INVOCATION_TOTAL._labelnames

    def test_memory_write_labels(self):
        """Contract: Memory write metrics use correct labels."""
        from telemetry.memory_metrics import (MEMORY_WRITE_TOTAL,
                                              PROMETHEUS_AVAILABLE)

        if not PROMETHEUS_AVAILABLE:
            pytest.skip("Prometheus not available")

        assert "segment" in MEMORY_WRITE_TOTAL._labelnames
        assert "status" in MEMORY_WRITE_TOTAL._labelnames

    def test_memory_search_labels(self):
        """Contract: Memory search metrics use correct labels."""
        from telemetry.memory_metrics import (MEMORY_SEARCH_TOTAL,
                                              PROMETHEUS_AVAILABLE)

        if not PROMETHEUS_AVAILABLE:
            pytest.skip("Prometheus not available")

        assert "segment" in MEMORY_SEARCH_TOTAL._labelnames
        assert "search_type" in MEMORY_SEARCH_TOTAL._labelnames


class TestHistogramBuckets:
    """Tests for histogram bucket configurations."""

    def test_tool_invocation_duration_buckets(self):
        """Contract: Tool invocation histogram has appropriate ms buckets."""
        from telemetry.memory_metrics import (PROMETHEUS_AVAILABLE,
                                              TOOL_INVOCATION_DURATION)

        if not PROMETHEUS_AVAILABLE:
            pytest.skip("Prometheus not available")

        # Should have buckets suitable for millisecond latencies
        buckets = TOOL_INVOCATION_DURATION._upper_bounds
        assert 100 in buckets  # 100ms
        assert 1000 in buckets  # 1 second
        assert 10000 in buckets  # 10 seconds

    def test_memory_write_duration_buckets(self):
        """Contract: Memory write histogram has appropriate second buckets."""
        from telemetry.memory_metrics import (MEMORY_WRITE_DURATION,
                                              PROMETHEUS_AVAILABLE)

        if not PROMETHEUS_AVAILABLE:
            pytest.skip("Prometheus not available")

        buckets = MEMORY_WRITE_DURATION._upper_bounds
        assert 0.1 in buckets  # 100ms
        assert 1.0 in buckets  # 1 second

    def test_memory_search_hits_buckets(self):
        """Contract: Memory search hits histogram has count buckets."""
        from telemetry.memory_metrics import (MEMORY_SEARCH_HITS,
                                              PROMETHEUS_AVAILABLE)

        if not PROMETHEUS_AVAILABLE:
            pytest.skip("Prometheus not available")

        buckets = MEMORY_SEARCH_HITS._upper_bounds
        assert 1 in buckets
        assert 10 in buckets
        assert 100 in buckets
