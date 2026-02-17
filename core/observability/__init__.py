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
    observability = await initialize_observability(substrate_service=substrate_service)

    # Instrument L9 services (one-time)
    await instrument_agent_executor(executor_service)
    await instrument_tool_registry(tool_registry)
    await instrument_governance_engine(governance_engine)
    await instrument_memory_substrate(substrate_service)

    # All subsequent calls are automatically traced!
"""

# ============================================================================
__dora_meta__ = {
    "component_name": "Production-ready auto-tracing and metrics.",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2026-01-06T15:07:54Z",
    "updated_at": "2026-01-31T22:21:47Z",
    "layer": "foundation",
    "domain": "core",
    "module_name": "__init__",
    "type": "engine",
    "status": "production",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": [],
        "memory_layers": ["working_memory"],
        "imported_by": [],
    },
}
# ============================================================================

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
    "AdaptiveStrategySelector",
    "AgentKPI",
    "AgentTrajectorySpan",
    "AsyncSpanExporter",
    # Circuit Breaker
    "CircuitBreaker",
    "CircuitBreakerConfig",
    "CircuitBreakerState",
    "CircuitOpenError",
    "CompositeExporter",
    "ConsoleExporter",
    "ContextAssemblySpan",
    # Context Strategies
    "ContextStrategy",
    "FailureClass",
    # Failures & Recovery
    "FailureDetector",
    "FailureSignal",
    "GovernanceCheckSpan",
    "HierarchicalSummarizationStrategy",
    "HybridStrategy",
    "JSONFileExporter",
    # Jaeger Exporter
    "JaegerExporter",
    "KPITracker",
    "LLMGenerationSpan",
    # Aggregation
    "MetricsAggregator",
    "NaiveTruncationStrategy",
    # Prometheus Exporter
    "ObservabilityPrometheusExporter",
    # Service
    "ObservabilityService",
    # Config
    "ObservabilitySettings",
    "RAGRetrievalSpan",
    "RAGStrategy",
    "RecencyBiasedWindowStrategy",
    "RecoveryAction",
    "RecoveryExecutor",
    "RemediationAction",
    "SREMetric",
    "Span",
    # Exporters
    "SpanExporter",
    "SpanKind",
    "SpanStatus",
    "SubstrateExporter",
    "ToolCallSpan",
    # Models
    "TraceContext",
    "get_correlation_id",
    "get_exporter",
    "get_jaeger_exporter",
    "get_recovery_actions",
    "get_span_id",
    "get_trace_context",
    "get_trace_id",
    "initialize_exporter",
    "initialize_jaeger_exporter",
    "initialize_observability",
    # L9 Integration
    "instrument_agent_executor",
    "instrument_aios_runtime",
    "instrument_governance_engine",
    "instrument_memory_substrate",
    "instrument_tool_registry",
    "load_config",
    # Observability Context (W3C Trace Context)
    "observability_context",
    "set_correlation_id",
    "set_trace_context_from_headers",
    "set_trace_id",
    "span",
    "trace_governance_check",
    "trace_llm_call",
    # Instrumentation
    "trace_span",
    "trace_tool_call",
]
# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "COR-FOUN-111",
    "governance_level": "critical",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": ["core", "engine", "foundation", "metrics", "tracing"],
    "keywords": [
        "agent",
        "auto",
        "await",
        "core",
        "detection",
        "management",
        "metrics",
        "metrics.",
    ],
    "business_value": "Distributed tracing with W3C Trace Context standard Automatic instrumentation via decorators Failure detection and recovery Context window management strategies Multi-backend span export (console, fil",
    "last_modified": "2026-01-31T22:21:47Z",
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
