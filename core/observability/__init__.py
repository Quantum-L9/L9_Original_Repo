"""
L9 Observability Module - Production-ready auto-tracing and metrics.

This module provides:
- Distributed tracing with W3C Trace Context standard
- Automatic instrumentation via decorators
- Failure detection and recovery
- Context window management strategies
- Multi-backend span export (console, file, substrate, Datadog, Honeycomb)
- SRE metrics and agent KPIs
- Sampling and cardinality management

Quick start:

    from core.observability.service import initialize_observability
    from core.observability.l9_integration import (
        instrument_agent_executor,
        instrument_tool_registry,
        instrument_governance_engine,
        instrument_memory_substrate,
    )

    # Initialize at app startup
    observability = await initialize_observability(substrate_service=substrate_svc)

    # Instrument L9 services (one-time)
    await instrument_agent_executor(executor_service)
    await instrument_tool_registry(tool_registry)
    await instrument_governance_engine(governance_engine)
    await instrument_memory_substrate(substrate_service)

    # All subsequent calls are automatically traced!
"""

from .aggregation import KPITracker, MetricsAggregator
from .circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerConfig,
    CircuitBreakerState,
    CircuitOpenError,
)
from .config import ObservabilitySettings, load_config
from .context_strategies import (
    AdaptiveStrategySelector,
    ContextStrategy,
    HierarchicalSummarizationStrategy,
    HybridStrategy,
    NaiveTruncationStrategy,
    RAGStrategy,
    RecencyBiasedWindowStrategy,
)
from .exporters import (
    AsyncSpanExporter,
    CompositeExporter,
    ConsoleExporter,
    JSONFileExporter,
    SpanExporter,
    SubstrateExporter,
)
from .failures import (
    FailureDetector,
    RecoveryAction,
    RecoveryExecutor,
    get_recovery_actions,
)
from .instrumentation import (
    trace_governance_check,
    trace_llm_call,
    trace_span,
    trace_tool_call,
)
from .jaeger_exporter import (
    JaegerExporter,
    get_jaeger_exporter,
    initialize_jaeger_exporter,
)
from .l9_integration import (
    instrument_agent_executor,
    instrument_aios_runtime,
    instrument_governance_engine,
    instrument_memory_substrate,
    instrument_tool_registry,
)
from .models import (
    AgentKPI,
    AgentTrajectorySpan,
    ContextAssemblySpan,
    FailureClass,
    FailureSignal,
    GovernanceCheckSpan,
    LLMGenerationSpan,
    RAGRetrievalSpan,
    RemediationAction,
    Span,
    SpanKind,
    SpanStatus,
    SREMetric,
    ToolCallSpan,
    TraceContext,
)
from .observability_context import (
    get_correlation_id,
    get_span_id,
    get_trace_context,
    get_trace_id,
    observability_context,
    set_correlation_id,
    set_trace_context_from_headers,
    set_trace_id,
    span,
)
from .prometheus_exporter import (
    ObservabilityPrometheusExporter,
    get_exporter,
    initialize_exporter,
)
from .service import ObservabilityService, initialize_observability

__version__ = "1.0.0"
__all__ = [
    # Config
    "ObservabilitySettings",
    "load_config",
    # Models
    "TraceContext",
    "Span",
    "LLMGenerationSpan",
    "ToolCallSpan",
    "ContextAssemblySpan",
    "RAGRetrievalSpan",
    "GovernanceCheckSpan",
    "AgentTrajectorySpan",
    "FailureSignal",
    "RemediationAction",
    "SREMetric",
    "AgentKPI",
    "SpanKind",
    "SpanStatus",
    "FailureClass",
    # Instrumentation
    "trace_span",
    "trace_llm_call",
    "trace_tool_call",
    "trace_governance_check",
    # Service
    "ObservabilityService",
    "initialize_observability",
    # Exporters
    "SpanExporter",
    "AsyncSpanExporter",
    "ConsoleExporter",
    "JSONFileExporter",
    "SubstrateExporter",
    "CompositeExporter",
    # Aggregation
    "MetricsAggregator",
    "KPITracker",
    # Context Strategies
    "ContextStrategy",
    "NaiveTruncationStrategy",
    "RecencyBiasedWindowStrategy",
    "HierarchicalSummarizationStrategy",
    "RAGStrategy",
    "HybridStrategy",
    "AdaptiveStrategySelector",
    # Failures & Recovery
    "FailureDetector",
    "RecoveryExecutor",
    "RecoveryAction",
    "get_recovery_actions",
    # Circuit Breaker
    "CircuitBreaker",
    "CircuitBreakerConfig",
    "CircuitBreakerState",
    "CircuitOpenError",
    # L9 Integration
    "instrument_agent_executor",
    "instrument_tool_registry",
    "instrument_governance_engine",
    "instrument_memory_substrate",
    "instrument_aios_runtime",
    # Prometheus Exporter
    "ObservabilityPrometheusExporter",
    "initialize_exporter",
    "get_exporter",
    # Jaeger Exporter
    "JaegerExporter",
    "initialize_jaeger_exporter",
    "get_jaeger_exporter",
    # Observability Context (W3C Trace Context)
    "observability_context",
    "span",
    "get_trace_id",
    "get_span_id",
    "get_correlation_id",
    "get_trace_context",
    "set_trace_id",
    "set_correlation_id",
    "set_trace_context_from_headers",
]
