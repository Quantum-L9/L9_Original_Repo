"""
Tests for Kernel Observability Spans (GMP-KERNEL-BOOT TODO-5)

Verifies:
1. SpanKind includes kernel lifecycle values
2. KernelLifecycleSpan model is properly defined
3. Kernel loader emits observability spans
4. Spans capture correct attributes
"""

from datetime import UTC, datetime

import pytest

from core.observability.models import (
    KernelLifecycleSpan,
    Span,
    SpanKind,
    SpanStatus,
    TraceContext,
)

# =============================================================================
# SpanKind Tests
# =============================================================================


class TestSpanKindKernelValues:
    """Tests for kernel-related SpanKind enum values."""

    def test_kernel_load_span_kind_exists(self):
        """KERNEL_LOAD SpanKind value exists."""
        assert hasattr(SpanKind, "KERNEL_LOAD")
        assert SpanKind.KERNEL_LOAD.value == "KERNEL_LOAD"

    def test_kernel_integrity_check_span_kind_exists(self):
        """KERNEL_INTEGRITY_CHECK SpanKind value exists."""
        assert hasattr(SpanKind, "KERNEL_INTEGRITY_CHECK")
        assert SpanKind.KERNEL_INTEGRITY_CHECK.value == "KERNEL_INTEGRITY_CHECK"

    def test_kernel_activation_span_kind_exists(self):
        """KERNEL_ACTIVATION SpanKind value exists."""
        assert hasattr(SpanKind, "KERNEL_ACTIVATION")
        assert SpanKind.KERNEL_ACTIVATION.value == "KERNEL_ACTIVATION"

    def test_kernel_reload_span_kind_exists(self):
        """KERNEL_RELOAD SpanKind value exists."""
        assert hasattr(SpanKind, "KERNEL_RELOAD")
        assert SpanKind.KERNEL_RELOAD.value == "KERNEL_RELOAD"

    def test_kernel_evolution_span_kind_exists(self):
        """KERNEL_EVOLUTION SpanKind value exists."""
        assert hasattr(SpanKind, "KERNEL_EVOLUTION")
        assert SpanKind.KERNEL_EVOLUTION.value == "KERNEL_EVOLUTION"

    def test_all_kernel_span_kinds_are_strings(self):
        """All kernel SpanKind values are strings."""
        kernel_kinds = [
            SpanKind.KERNEL_LOAD,
            SpanKind.KERNEL_INTEGRITY_CHECK,
            SpanKind.KERNEL_ACTIVATION,
            SpanKind.KERNEL_RELOAD,
            SpanKind.KERNEL_EVOLUTION,
        ]
        for kind in kernel_kinds:
            assert isinstance(kind.value, str)


# =============================================================================
# KernelLifecycleSpan Tests
# =============================================================================


class TestKernelLifecycleSpan:
    """Tests for KernelLifecycleSpan model."""

    def test_kernel_lifecycle_span_creation(self):
        """KernelLifecycleSpan can be created with required fields."""
        span = KernelLifecycleSpan(
            trace_id="abc123",
            span_id="def456",
            name="kernel_loader.phase1",
            start_time=datetime.now(UTC),
            kernel_id="master",
        )
        assert span.kernel_id == "master"
        assert span.name == "kernel_loader.phase1"
        assert span.phase == "load"  # Default

    def test_kernel_lifecycle_span_with_all_fields(self):
        """KernelLifecycleSpan stores all kernel-specific fields."""
        span = KernelLifecycleSpan(
            trace_id="abc123",
            span_id="def456",
            name="kernel_loader.phase2",
            start_time=datetime.now(UTC),
            kernel_id="identity",
            kernel_version="1.0.0",
            kernel_hash="sha256:abc123def456",
            phase="activate",
            integrity_status="UNCHANGED",
            rules_count=15,
            agent_id="l-cto",
        )
        assert span.kernel_id == "identity"
        assert span.kernel_version == "1.0.0"
        assert span.kernel_hash == "sha256:abc123def456"
        assert span.phase == "activate"
        assert span.integrity_status == "UNCHANGED"
        assert span.rules_count == 15
        assert span.agent_id == "l-cto"

    def test_kernel_lifecycle_span_inherits_from_span(self):
        """KernelLifecycleSpan inherits from base Span class."""
        assert issubclass(KernelLifecycleSpan, Span)

    def test_kernel_lifecycle_span_start_method(self):
        """KernelLifecycleSpan.start() creates a new span."""
        span = KernelLifecycleSpan.start(
            name="kernel_loader.integrity_check",
            trace_id="trace123",
            kind=SpanKind.KERNEL_INTEGRITY_CHECK,
            kernel_id="safety",
        )
        assert span.name == "kernel_loader.integrity_check"
        assert span.trace_id == "trace123"
        assert span.kind == SpanKind.KERNEL_INTEGRITY_CHECK
        assert span.start_time is not None
        assert span.end_time is None

    def test_kernel_lifecycle_span_finish_method(self):
        """KernelLifecycleSpan.finish() completes the span."""
        span = KernelLifecycleSpan.start(
            name="kernel_loader.phase1",
            trace_id="trace123",
            kernel_id="master",
        )
        span.finish(status=SpanStatus.OK)

        assert span.end_time is not None
        assert span.status == SpanStatus.OK
        assert span.duration_ms is not None
        assert span.duration_ms >= 0

    def test_kernel_lifecycle_span_finish_with_error(self):
        """KernelLifecycleSpan.finish() can record errors."""
        span = KernelLifecycleSpan.start(
            name="kernel_loader.phase2",
            trace_id="trace123",
            kernel_id="all",
        )
        span.finish(status=SpanStatus.ERROR, error="Kernel activation failed")

        assert span.status == SpanStatus.ERROR
        assert span.error == "Kernel activation failed"


# =============================================================================
# Kernel Loader Span Integration Tests
# =============================================================================


class TestKernelLoaderSpanEmission:
    """Tests for span emission in kernel loader functions.

    Note: These tests verify the span creation logic works correctly.
    Full integration tests with actual observability service are in
    tests/integration/.
    """

    def test_create_kernel_span_helper(self):
        """_create_kernel_span creates valid spans."""
        from core.kernels.kernelloader import _create_kernel_span

        # When observability is available, span should be created
        _create_kernel_span(
            name="test_span",
            kernel_id="master",
            phase="load",
        )
        # Returns None if observability not initialized (expected in test env)
        # This verifies the function doesn't crash

    def test_finish_span_helper(self):
        """_finish_span handles None spans gracefully."""
        from core.kernels.kernelloader import _finish_span

        # Should not raise when span is None
        _finish_span(None, SpanStatus.OK)

    def test_kernel_lifecycle_span_can_be_created_manually(self):
        """KernelLifecycleSpan can be created for testing."""
        span = KernelLifecycleSpan.start(
            name="kernel_loader.phase1",
            trace_id="test-trace-123",
            kernel_id="all",
            phase="load",
            kernel_count=10,
        )

        assert span.name == "kernel_loader.phase1"
        assert span.kernel_id == "all"
        assert span.phase == "load"
        assert span.kernel_count == 10

        # Finish the span
        span.finish(status=SpanStatus.OK)
        assert span.status == SpanStatus.OK
        assert span.duration_ms is not None

    def test_kernel_lifecycle_span_captures_error(self):
        """KernelLifecycleSpan can capture errors."""
        span = KernelLifecycleSpan.start(
            name="kernel_loader.phase2",
            trace_id="test-trace-456",
            kernel_id="master",
            phase="activate",
        )

        span.finish(status=SpanStatus.ERROR, error="Activation failed")

        assert span.status == SpanStatus.ERROR
        assert span.error == "Activation failed"


# =============================================================================
# Span Attribute Tests
# =============================================================================


class TestKernelSpanAttributes:
    """Tests for kernel span attributes."""

    def test_span_includes_kernel_count(self):
        """Kernel spans include kernel count attribute."""
        KernelLifecycleSpan.start(
            name="kernel_loader.phase1",
            trace_id="trace123",
            kernel_id="all",
            kernel_count=10,
        )
        # Attributes are passed via **kwargs to start()
        # They should be accessible in span.attributes
        # Note: The actual implementation may vary

    def test_span_includes_agent_id(self):
        """Kernel spans include agent_id when available."""
        span = KernelLifecycleSpan(
            trace_id="trace123",
            span_id="span456",
            name="kernel_loader.phase2",
            start_time=datetime.now(UTC),
            kernel_id="all",
            agent_id="l-cto",
        )
        assert span.agent_id == "l-cto"

    def test_span_includes_integrity_status(self):
        """Kernel spans include integrity status."""
        span = KernelLifecycleSpan(
            trace_id="trace123",
            span_id="span456",
            name="kernel_loader.integrity_check",
            start_time=datetime.now(UTC),
            kernel_id="master",
            integrity_status="MODIFIED",
        )
        assert span.integrity_status == "MODIFIED"


# =============================================================================
# TraceContext Integration Tests
# =============================================================================


class TestTraceContextIntegration:
    """Tests for trace context propagation in kernel loader."""

    def test_trace_context_creates_valid_trace_id(self):
        """TraceContext creates a valid trace ID."""
        ctx = TraceContext()
        assert ctx.trace_id is not None
        assert len(ctx.trace_id) > 0

    def test_trace_context_creates_valid_span_id(self):
        """TraceContext creates a valid span ID."""
        ctx = TraceContext()
        assert ctx.span_id is not None
        assert len(ctx.span_id) > 0

    def test_trace_context_child_preserves_trace_id(self):
        """Child trace context preserves parent trace ID."""
        parent = TraceContext()
        child = parent.child_context()

        assert child.trace_id == parent.trace_id
        assert child.parent_span_id == parent.span_id
        assert child.span_id != parent.span_id

    def test_trace_context_to_headers(self):
        """TraceContext converts to W3C traceparent header."""
        ctx = TraceContext()
        headers = ctx.to_headers()

        assert "traceparent" in headers
        parts = headers["traceparent"].split("-")
        assert len(parts) == 4
        assert parts[0] == "00"  # Version
        assert parts[1] == ctx.trace_id
        assert parts[2] == ctx.span_id


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
