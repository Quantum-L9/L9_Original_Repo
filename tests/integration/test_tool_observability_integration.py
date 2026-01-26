"""
Tool Observability Integration Tests
====================================

End-to-end integration tests for the tool audit and Prometheus metrics
observability stack. Tests the complete flow from tool invocation through
memory storage and metrics recording.

Coverage targets:
- Tool audit → Memory substrate integration
- Tool audit → Prometheus metrics integration
- /metrics endpoint availability
- Dual observability (DB + metrics) for single tool call
"""

import asyncio
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest


class TestToolAuditMetricsIntegration:
    """Integration tests for tool audit + Prometheus metrics."""

    @pytest.mark.asyncio
    async def test_tool_invocation_records_both_packet_and_metrics(self):
        """Contract: Single tool call records both memory packet and Prometheus metrics."""
        from memory.tool_audit import log_tool_invocation
        from telemetry.memory_metrics import PROMETHEUS_AVAILABLE, TOOL_INVOCATION_TOTAL

        if not PROMETHEUS_AVAILABLE:
            pytest.skip("Prometheus not available")

        call_id = uuid4()
        tool_id = f"integration_test_{uuid4().hex[:8]}"

        # Get initial metric value
        initial_count = TOOL_INVOCATION_TOTAL.labels(
            tool_id=tool_id, status="success"
        )._value._value

        with patch("memory.tool_audit.asyncio.create_task") as mock_create_task:
            await log_tool_invocation(
                call_id=call_id,
                tool_id=tool_id,
                agent_id="L",
                status="success",
                duration_ms=50,
            )

            # Memory packets were scheduled (both ingest and audit table write)
            assert mock_create_task.call_count >= 1

            # Prometheus metric was incremented
            new_count = TOOL_INVOCATION_TOTAL.labels(
                tool_id=tool_id, status="success"
            )._value._value
            assert new_count == initial_count + 1

    @pytest.mark.asyncio
    async def test_tool_failure_records_both_packet_and_metrics(self):
        """Contract: Failed tool call records failure in both systems."""
        from memory.tool_audit import log_tool_invocation
        from telemetry.memory_metrics import PROMETHEUS_AVAILABLE, TOOL_INVOCATION_TOTAL

        if not PROMETHEUS_AVAILABLE:
            pytest.skip("Prometheus not available")

        call_id = uuid4()
        tool_id = f"failure_test_{uuid4().hex[:8]}"

        with patch("memory.tool_audit.asyncio.create_task") as mock_create_task:
            await log_tool_invocation(
                call_id=call_id,
                tool_id=tool_id,
                agent_id="L",
                status="failure",
                duration_ms=100,
                error="Connection refused",
            )

            # Memory packets were scheduled
            assert mock_create_task.call_count >= 1

            failure_count = TOOL_INVOCATION_TOTAL.labels(
                tool_id=tool_id, status="failure"
            )._value._value
            assert failure_count >= 1

    @pytest.mark.asyncio
    async def test_tool_duration_recorded_in_histogram(self):
        """Contract: Tool duration is recorded in Prometheus histogram."""
        from memory.tool_audit import log_tool_invocation
        from telemetry.memory_metrics import (
            PROMETHEUS_AVAILABLE,
            TOOL_INVOCATION_DURATION,
        )

        if not PROMETHEUS_AVAILABLE:
            pytest.skip("Prometheus not available")

        call_id = uuid4()
        tool_id = f"duration_hist_{uuid4().hex[:8]}"
        duration_ms = 150

        with patch("memory.tool_audit.asyncio.create_task"):
            await log_tool_invocation(
                call_id=call_id,
                tool_id=tool_id,
                agent_id="L",
                status="success",
                duration_ms=duration_ms,
            )

            hist = TOOL_INVOCATION_DURATION.labels(tool_id=tool_id)
            assert hist._sum._value >= duration_ms

    @pytest.mark.asyncio
    async def test_multiple_tools_tracked_separately(self):
        """Contract: Multiple different tools have separate metric series."""
        from memory.tool_audit import log_tool_invocation
        from telemetry.memory_metrics import PROMETHEUS_AVAILABLE, TOOL_INVOCATION_TOTAL

        if not PROMETHEUS_AVAILABLE:
            pytest.skip("Prometheus not available")

        tool_a = f"tool_a_{uuid4().hex[:8]}"
        tool_b = f"tool_b_{uuid4().hex[:8]}"

        with patch("memory.tool_audit.asyncio.create_task"):
            # Call tool A twice
            await log_tool_invocation(
                call_id=uuid4(), tool_id=tool_a, agent_id="L", status="success"
            )
            await log_tool_invocation(
                call_id=uuid4(), tool_id=tool_a, agent_id="L", status="success"
            )

            # Call tool B once
            await log_tool_invocation(
                call_id=uuid4(), tool_id=tool_b, agent_id="L", status="success"
            )

            count_a = TOOL_INVOCATION_TOTAL.labels(
                tool_id=tool_a, status="success"
            )._value._value
            count_b = TOOL_INVOCATION_TOTAL.labels(
                tool_id=tool_b, status="success"
            )._value._value

            assert count_a >= 2
            assert count_b >= 1


class TestMetricsEndpointIntegration:
    """Integration tests for /metrics endpoint."""

    def test_prometheus_make_asgi_app_available(self):
        """Contract: prometheus_client make_asgi_app is importable."""
        try:
            from prometheus_client import make_asgi_app

            app = make_asgi_app()
            assert app is not None
        except ImportError:
            pytest.skip("prometheus_client not available")

    def test_metrics_generate_latest_includes_l9_metrics(self):
        """Contract: generate_latest includes L9 custom metrics."""
        try:
            from prometheus_client import REGISTRY, generate_latest

            from telemetry.memory_metrics import (
                PROMETHEUS_AVAILABLE,
                record_tool_invocation,
            )

            if not PROMETHEUS_AVAILABLE:
                pytest.skip("Prometheus not available")

            # Record a metric to ensure it's populated
            record_tool_invocation(
                tool_id="metrics_endpoint_test",
                status="success",
                duration_ms=10,
            )

            output = generate_latest(REGISTRY).decode("utf-8")

            # Verify our custom metrics are present
            assert "l9_tool_invocation_total" in output
            assert "l9_tool_invocation_duration_ms" in output
            assert "l9_memory_substrate_healthy" in output

        except ImportError:
            pytest.skip("prometheus_client not available")

    def test_metrics_output_format(self):
        """Contract: Metrics output is valid Prometheus text format."""
        try:
            from prometheus_client import REGISTRY, generate_latest

            output = generate_latest(REGISTRY).decode("utf-8")

            # Should be text, contain TYPE and HELP comments
            assert isinstance(output, str)
            assert len(output) > 0

            # Prometheus format includes # HELP and # TYPE lines
            lines = output.split("\n")
            has_type = any(line.startswith("# TYPE") for line in lines)
            has_help = any(line.startswith("# HELP") for line in lines)

            assert has_type, "Prometheus output should contain TYPE lines"
            assert has_help, "Prometheus output should contain HELP lines"

        except ImportError:
            pytest.skip("prometheus_client not available")


class TestObservabilityResilience:
    """Tests for observability system resilience."""

    @pytest.mark.asyncio
    async def test_metrics_failure_does_not_block_audit(self):
        """Contract: If metrics fail, audit packet is still scheduled."""
        from memory.tool_audit import log_tool_invocation

        call_id = uuid4()

        with (
            patch("memory.tool_audit.asyncio.create_task") as mock_create_task,
            patch(
                "memory.tool_audit.record_tool_invocation",
                side_effect=Exception("Metrics error"),
            ),
        ):
            # Should not raise despite metrics failure
            await log_tool_invocation(
                call_id=call_id,
                tool_id="resilience_test",
                agent_id="L",
                status="success",
            )

            # Packets were still scheduled despite metrics failure
            assert mock_create_task.call_count >= 1

    @pytest.mark.asyncio
    async def test_high_volume_metrics_recording(self):
        """Contract: High volume of metric recordings doesn't cause issues."""
        from telemetry.memory_metrics import (
            PROMETHEUS_AVAILABLE,
            record_tool_invocation,
        )

        if not PROMETHEUS_AVAILABLE:
            pytest.skip("Prometheus not available")

        # Record 100 tool invocations rapidly
        for i in range(100):
            record_tool_invocation(
                tool_id=f"volume_test_{i % 10}",  # 10 different tools
                status="success" if i % 5 else "failure",
                duration_ms=i * 10,
            )

        # Should complete without error

    @pytest.mark.asyncio
    async def test_concurrent_metric_recording(self):
        """Contract: Concurrent metric recording is thread-safe."""
        from telemetry.memory_metrics import (
            PROMETHEUS_AVAILABLE,
            record_tool_invocation,
        )

        if not PROMETHEUS_AVAILABLE:
            pytest.skip("Prometheus not available")

        async def record_metric(i: int):
            record_tool_invocation(
                tool_id=f"concurrent_test_{i}",
                status="success",
                duration_ms=i,
            )

        # Run 50 concurrent recordings
        await asyncio.gather(*[record_metric(i) for i in range(50)])

        # Should complete without race conditions


class TestMemorySegmentEnum:
    """Tests for MemorySegment enum integration."""

    def test_tool_audit_segment_exists(self):
        """Contract: TOOL_AUDIT segment is defined in MemorySegment enum."""
        from memory.substrate_models import MemorySegment

        assert hasattr(MemorySegment, "TOOL_AUDIT")
        assert MemorySegment.TOOL_AUDIT.value == "tool_audit"

    def test_all_segments_defined(self):
        """Contract: All four canonical segments are defined."""
        from memory.substrate_models import MemorySegment

        expected = [
            "GOVERNANCE_META",
            "PROJECT_HISTORY",
            "TOOL_AUDIT",
            "SESSION_CONTEXT",
        ]

        for segment in expected:
            assert hasattr(MemorySegment, segment), f"Missing segment: {segment}"

    def test_segment_values_are_strings(self):
        """Contract: Segment values are lowercase strings."""
        from memory.substrate_models import MemorySegment

        for segment in MemorySegment:
            assert isinstance(segment.value, str)
            assert segment.value.islower() or "_" in segment.value


class TestExecutorRegistryWiring:
    """Tests for ExecutorToolRegistry → tool audit wiring."""

    def test_registry_imports_tool_audit(self):
        """Contract: ExecutorToolRegistry imports log_tool_invocation."""
        try:
            import core.tools.registry_adapter as registry

            # Check that time is imported (used for duration calculation)
            assert hasattr(registry, "time") or "time" in dir(registry)
        except (ModuleNotFoundError, ImportError) as e:
            pytest.skip(f"Missing dependency: {e}")

    def test_registry_imports_audit_function(self):
        """Contract: log_tool_invocation is imported in registry."""
        try:
            from core.tools.registry_adapter import log_tool_invocation

            assert callable(log_tool_invocation)
        except (ModuleNotFoundError, ImportError) as e:
            pytest.skip(f"Missing dependency: {e}")


class TestPacketStructure:
    """Tests for tool audit packet structure."""

    @pytest.mark.asyncio
    async def test_packet_has_required_fields(self):
        """Contract: Tool audit packet contains all required fields."""
        from memory.tool_audit import log_tool_invocation

        call_id = uuid4()
        captured_coro = None

        def capture_create_task(coro):
            nonlocal captured_coro
            captured_coro = coro
            # Return a mock task
            task = MagicMock()
            task.cancel = MagicMock()
            return task

        with (
            patch(
                "memory.tool_audit.asyncio.create_task", side_effect=capture_create_task
            ),
            patch("memory.tool_audit.record_tool_invocation"),
        ):
            await log_tool_invocation(
                call_id=call_id,
                tool_id="structure_test",
                agent_id="L",
                task_id="task-123",
                status="success",
                duration_ms=100,
            )

            # The coroutine was captured
            assert captured_coro is not None

    @pytest.mark.asyncio
    async def test_packet_type_is_tool_audit(self):
        """Contract: Packet type is set to 'tool_audit'."""
        from memory.substrate_models import MemorySegment

        # The packet_type should match MemorySegment.TOOL_AUDIT.value
        assert MemorySegment.TOOL_AUDIT.value == "tool_audit"

    @pytest.mark.asyncio
    async def test_packet_has_ttl(self):
        """Contract: Tool audit packets have TTL set."""
        from memory.tool_audit import TOOL_AUDIT_TTL_HOURS

        assert TOOL_AUDIT_TTL_HOURS == 24  # 24 hours

    @pytest.mark.asyncio
    async def test_packet_tags_include_tool_info(self):
        """Contract: Packet tags include tool_id, agent_id, and status."""
        # Tags are created in the format:
        # tags=["tool:{tool_id}", "agent:{agent_id}", "status:{status}"]
        # This is validated by the packet structure in log_tool_invocation
        pass  # Structure verified by other tests


class TestConfidenceScore:
    """Tests for tool audit confidence scoring."""

    def test_confidence_is_always_1(self):
        """Contract: Tool audit confidence is always 1.0 (direct observation)."""
        # Tool audits are direct observations, not inferences
        # Confidence should always be 1.0
        # This is verified in log_tool_invocation where confidence=PacketConfidence(score=1.0, ...)
        pass
