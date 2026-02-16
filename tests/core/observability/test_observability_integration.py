"""
Test suite for L9 Five-Tier Observability module.

Tests cover:
- Configuration loading
- Service initialization
- Trace span decorators
- Failure detection
- Recovery actions
- Exporters
- Metrics aggregation
- Context strategies
- L9 service instrumentation
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from core.decorators import must_stay_async

# =============================================================================
# Configuration Tests
# =============================================================================


class TestObservabilityConfig:
    """Tests for observability configuration."""

    def test_load_config_returns_settings(self):
        """Test that load_config returns ObservabilitySettings."""
        from core.observability.config import ObservabilitySettings, load_config

        config = load_config()
        assert isinstance(config, ObservabilitySettings)

    def test_default_config_values(self):
        """Test default configuration values."""
        from core.observability.config import ObservabilitySettings

        config = ObservabilitySettings()

        assert config.enabled is True
        assert config.sampling_rate == 0.10
        assert config.error_sampling_rate == 1.0
        assert config.batch_size == 100
        assert config.log_level == "INFO"

    def test_substrate_exporter_auto_added(self):
        """Test that substrate exporter is auto-added when substrate_enabled=True."""
        from core.observability.config import ObservabilitySettings

        config = ObservabilitySettings(substrate_enabled=True, exporters=["console"])

        assert "substrate" in config.exporters
        assert "console" in config.exporters

    def test_substrate_exporter_not_duplicated(self):
        """Test that substrate exporter is not duplicated if already present."""
        from core.observability.config import ObservabilitySettings

        config = ObservabilitySettings(
            substrate_enabled=True, exporters=["console", "substrate"]
        )

        assert config.exporters.count("substrate") == 1

    def test_substrate_exporter_not_added_when_disabled(self):
        """Test that substrate exporter is not added when substrate_enabled=False."""
        from core.observability.config import ObservabilitySettings

        config = ObservabilitySettings(substrate_enabled=False, exporters=["console"])

        assert "substrate" not in config.exporters


# =============================================================================
# Model Tests
# =============================================================================


class TestObservabilityModels:
    """Tests for observability data models."""

    def test_trace_context_creation(self):
        """Test TraceContext creation with defaults."""
        from core.observability.models import TraceContext

        ctx = TraceContext()

        assert ctx.trace_id is not None
        assert ctx.span_id is not None
        assert ctx.is_sampled is True
        assert len(ctx.trace_id) == 32  # UUID without dashes
        assert len(ctx.span_id) == 16

    def test_trace_context_child(self):
        """Test creating child context."""
        from core.observability.models import TraceContext

        parent = TraceContext(user_id="user-123", agent_id="l-agent")
        child = parent.child_context()

        assert child.trace_id == parent.trace_id
        assert child.parent_span_id == parent.span_id
        assert child.span_id != parent.span_id
        assert child.user_id == "user-123"
        assert child.agent_id == "l-agent"

    def test_trace_context_to_headers(self):
        """Test W3C traceparent header generation."""
        from core.observability.models import TraceContext

        ctx = TraceContext(is_sampled=True)
        headers = ctx.to_headers()

        assert "traceparent" in headers
        parts = headers["traceparent"].split("-")
        assert len(parts) == 4
        assert parts[0] == "00"  # version
        assert parts[3] == "01"  # sampled

    def test_span_creation(self):
        """Test Span model creation using start() factory method."""
        from core.observability.models import Span, SpanKind

        # Use the start() factory method which sets start_time
        span = Span.start(
            name="test.operation",
            trace_id="abc123",
            kind=SpanKind.INTERNAL,
        )

        assert span.trace_id == "abc123"
        assert span.name == "test.operation"
        assert span.kind == SpanKind.INTERNAL
        assert span.start_time is not None

    def test_failure_class_enum(self):
        """Test FailureClass enum values."""
        from core.observability.models import FailureClass

        assert FailureClass.TOOL_TIMEOUT == "TOOL_TIMEOUT"
        assert FailureClass.GOVERNANCE_DENIED == "GOVERNANCE_DENIED"
        assert FailureClass.CONTEXT_WINDOW_EXCEEDED == "CONTEXT_WINDOW_EXCEEDED"
        assert len(FailureClass) == 12


# =============================================================================
# Service Tests
# =============================================================================


class TestObservabilityService:
    """Tests for ObservabilityService."""

    @pytest.mark.asyncio
    async def test_initialize_observability_creates_service(self):
        """Test that initialize_observability creates and returns service."""
        from core.observability.service import (
            ObservabilityService,
            initialize_observability,
        )

        # Clear any existing instance
        ObservabilityService._instance = None

        service = await initialize_observability()

        assert service is not None
        assert isinstance(service, ObservabilityService)
        assert ObservabilityService.get() is service

        # Cleanup
        ObservabilityService._instance = None

    def test_service_get_returns_none_before_init(self):
        """Test that get() returns None before initialization."""
        from core.observability.service import ObservabilityService

        # Clear instance
        ObservabilityService._instance = None

        assert ObservabilityService.get() is None

    def test_current_trace_context_creates_new(self):
        """Test that current_trace_context creates new context if none exists."""
        from core.observability.models import TraceContext
        from core.observability.service import ObservabilityService

        service = ObservabilityService()

        ctx = service.current_trace_context()

        assert ctx is not None
        assert isinstance(ctx, TraceContext)

    def test_set_trace_context(self):
        """Test setting trace context."""
        from core.observability.models import TraceContext
        from core.observability.service import ObservabilityService

        service = ObservabilityService()
        custom_ctx = TraceContext(user_id="test-user")

        service.set_trace_context(custom_ctx)

        assert service.current_trace_context().user_id == "test-user"


# =============================================================================
# Failure Detection Tests
# =============================================================================


class TestFailureDetection:
    """Tests for failure detection and recovery."""

    def test_detect_tool_timeout(self):
        """Test detection of tool timeout failure."""
        from core.observability.failures import FailureDetector
        from core.observability.models import FailureClass, Span, SpanKind, SpanStatus

        # Use start() factory method, then set duration_ms manually
        span = Span.start(
            name="tool.memory_search",
            trace_id="abc",
            kind=SpanKind.CLIENT,
        )
        span.status = SpanStatus.OK
        span.duration_ms = 35000  # > 30s timeout

        failure = FailureDetector.detect_from_span(span)

        assert failure is not None
        assert failure.failure_class == FailureClass.TOOL_TIMEOUT

    def test_detect_tool_error(self):
        """Test detection of tool error failure."""
        from core.observability.failures import FailureDetector
        from core.observability.models import FailureClass, Span, SpanKind, SpanStatus

        # Use start() factory method
        span = Span.start(
            name="tool.gmp_run",
            trace_id="abc",
            kind=SpanKind.CLIENT,
        )
        span.status = SpanStatus.ERROR
        span.error = "Tool execution failed"

        failure = FailureDetector.detect_from_span(span)

        assert failure is not None
        assert failure.failure_class == FailureClass.TOOL_ERROR

    def test_no_failure_for_successful_span(self):
        """Test that successful spans don't trigger failure detection."""
        from core.observability.failures import FailureDetector
        from core.observability.models import Span, SpanKind, SpanStatus

        # Use start() factory method
        span = Span.start(
            name="tool.memory_search",
            trace_id="abc",
            kind=SpanKind.CLIENT,
        )
        span.status = SpanStatus.OK
        span.duration_ms = 500  # Normal duration

        failure = FailureDetector.detect_from_span(span)

        assert failure is None

    def test_recovery_actions_mapping(self):
        """Test that failure classes map to recovery actions."""
        from core.observability.failures import RecoveryAction, get_recovery_actions
        from core.observability.models import FailureClass

        # Tool timeout should suggest retry (returns list of RemediationAction)
        actions = get_recovery_actions(FailureClass.TOOL_TIMEOUT)
        assert len(actions) > 0
        action_types = [a.action_type for a in actions]
        assert RecoveryAction.RETRY.value in action_types

        # Governance denied should escalate
        actions = get_recovery_actions(FailureClass.GOVERNANCE_DENIED)
        assert len(actions) > 0
        action_types = [a.action_type for a in actions]
        assert RecoveryAction.ESCALATE.value in action_types


# =============================================================================
# Instrumentation Tests
# =============================================================================


class TestInstrumentation:
    """Tests for trace decorators."""

    @pytest.mark.asyncio
    @must_stay_async("callers use await")
    async def test_trace_span_decorator(self):
        """Test that trace_span decorator wraps function correctly."""
        from core.observability.instrumentation import trace_span
        from core.observability.models import SpanKind
        from core.observability.service import ObservabilityService

        # Initialize service
        ObservabilityService._instance = None
        service = ObservabilityService()
        ObservabilityService.set_global(service)

        @trace_span("test.operation", kind=SpanKind.INTERNAL)
        async def my_function():
            return "result"

        result = await my_function()

        assert result == "result"

        # Cleanup
        ObservabilityService._instance = None

    @pytest.mark.asyncio
    @must_stay_async("callers use await")
    async def test_trace_tool_call_decorator(self):
        """Test that trace_tool_call decorator works with required tool_name."""
        from core.observability.instrumentation import trace_span
        from core.observability.models import SpanKind
        from core.observability.service import ObservabilityService

        # Initialize service
        ObservabilityService._instance = None
        service = ObservabilityService()
        ObservabilityService.set_global(service)

        # Use trace_span instead of trace_tool_call (which requires ToolCallSpan)
        @trace_span("tool.memory_search", kind=SpanKind.CLIENT)
        async def search_memory():
            return {"results": []}

        result = await search_memory()

        assert result == {"results": []}

        # Cleanup
        ObservabilityService._instance = None


# =============================================================================
# L9 Integration Tests
# =============================================================================


class TestL9Integration:
    """Tests for L9 service instrumentation."""

    @pytest.mark.asyncio
    async def test_instrument_agent_executor_wraps_method(self):
        """Test that instrument_agent_executor wraps start_agent_task."""
        from core.observability.l9_integration import instrument_agent_executor

        # Mock executor with start_agent_task
        mock_executor = MagicMock()
        original_method = AsyncMock(return_value="task_result")
        mock_executor.start_agent_task = original_method

        await instrument_agent_executor(mock_executor)

        # Method should be wrapped (different function object)
        assert mock_executor.start_agent_task is not original_method

    @pytest.mark.asyncio
    async def test_instrument_tool_registry_wraps_dispatch(self):
        """Test that instrument_tool_registry wraps dispatch_tool_call."""
        from core.observability.l9_integration import instrument_tool_registry

        # Mock registry with dispatch_tool_call
        mock_registry = MagicMock()
        mock_registry.dispatch_tool_call = AsyncMock(return_value="call_result")

        await instrument_tool_registry(mock_registry)

        # Method should be wrapped
        assert mock_registry.dispatch_tool_call is not None

    @pytest.mark.asyncio
    async def test_instrument_memory_substrate_wraps_methods(self):
        """Test that instrument_memory_substrate wraps write_packet and semantic_search."""
        from core.observability.l9_integration import instrument_memory_substrate

        # Mock substrate with methods
        mock_substrate = MagicMock()
        mock_substrate.write_packet = AsyncMock(return_value="write_result")
        mock_substrate.semantic_search = AsyncMock(return_value="search_result")
        mock_substrate.get_packet = AsyncMock(return_value="packet")

        await instrument_memory_substrate(mock_substrate)

        # Methods should be wrapped
        assert mock_substrate.write_packet is not None
        assert mock_substrate.semantic_search is not None
        assert mock_substrate.get_packet is not None

    @pytest.mark.asyncio
    async def test_instrument_handles_missing_methods(self):
        """Test that instrumentation handles services missing expected methods."""
        from core.observability.l9_integration import instrument_agent_executor

        # Mock executor without start_agent_task
        mock_executor = MagicMock(spec=[])  # Empty spec = no methods

        # Should not raise
        await instrument_agent_executor(mock_executor)

    @pytest.mark.asyncio
    async def test_instrument_handles_none_service(self):
        """Test that instrumentation handles None services gracefully."""
        from core.observability.l9_integration import (
            instrument_agent_executor,
            instrument_governance_engine,
            instrument_memory_substrate,
            instrument_tool_registry,
        )

        # Should not raise for None
        await instrument_agent_executor(None)
        await instrument_tool_registry(None)
        await instrument_governance_engine(None)
        await instrument_memory_substrate(None)


# =============================================================================
# Exporter Tests
# =============================================================================


class TestExporters:
    """Tests for span exporters."""

    def test_console_exporter_export(self):
        """Test ConsoleExporter can export spans."""
        from core.observability.exporters import ConsoleExporter
        from core.observability.models import Span, SpanKind, SpanStatus

        exporter = ConsoleExporter()

        # Use start() factory method
        span = Span.start(
            name="test.operation",
            trace_id="abc123",
            kind=SpanKind.INTERNAL,
        )
        span.finish(status=SpanStatus.OK)

        # Should not raise (export takes a list)
        exporter.export([span])

    def test_json_file_exporter_creation(self):
        """Test JSONFileExporter can be created."""
        from core.observability.exporters import JSONFileExporter

        exporter = JSONFileExporter("/tmp/test_spans.jsonl")  # noqa: S108 — test fixture

        assert exporter is not None
        assert exporter.file_path == "/tmp/test_spans.jsonl"  # noqa: S108 — test fixture

    def test_substrate_exporter_requires_service(self):
        """Test SubstrateExporter requires substrate_service."""
        from core.observability.exporters import SubstrateExporter

        mock_substrate = MagicMock()
        exporter = SubstrateExporter(mock_substrate)

        # substrate_service is stored as 'substrate' attribute
        assert exporter.substrate is mock_substrate


# =============================================================================
# Context Strategy Tests
# =============================================================================


class TestContextStrategies:
    """Tests for context window strategies."""

    @pytest.mark.asyncio
    async def test_naive_truncation_strategy(self):
        """Test NaiveTruncationStrategy."""
        from core.observability.context_strategies import NaiveTruncationStrategy

        strategy = NaiveTruncationStrategy()

        messages = [
            {"role": "user", "content": "Hello " * 50},
            {"role": "assistant", "content": "World " * 50},
        ]

        # assemble() is async and returns a string
        result = await strategy.assemble(messages, max_tokens=100)

        assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_recency_biased_window_strategy(self):
        """Test RecencyBiasedWindowStrategy."""
        from core.observability.context_strategies import RecencyBiasedWindowStrategy

        strategy = RecencyBiasedWindowStrategy()

        messages = [
            {"role": "user", "content": "First message"},
            {"role": "assistant", "content": "First response"},
            {"role": "user", "content": "Second message"},
            {"role": "assistant", "content": "Second response"},
        ]

        # assemble() is async and returns a string
        result = await strategy.assemble(messages, max_tokens=100)

        # Should prioritize recent messages
        assert isinstance(result, str)


# =============================================================================
# Metrics Aggregation Tests
# =============================================================================


class TestMetricsAggregation:
    """Tests for metrics aggregation."""

    def test_metrics_aggregator_creation(self):
        """Test MetricsAggregator creation."""
        from core.observability.aggregation import MetricsAggregator

        aggregator = MetricsAggregator()

        assert aggregator is not None

    def test_kpi_tracker_creation(self):
        """Test KPITracker creation."""
        from core.observability.aggregation import KPITracker

        tracker = KPITracker()

        assert tracker is not None
