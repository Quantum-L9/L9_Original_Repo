"""
L9 Core Abstractions - Protocol Definitions
============================================

Frontier-grade protocol definitions for all L9 subsystems following
Dependency Inversion Principle (DIP).

**Top Frontier AI Lab Quality** - Production-ready abstractions enabling
dependency injection, testing, and hot-swappable implementations.

Modules:
- kernel_protocols: Kernel loading, validation, and activation
- memory_protocols: Memory storage, retrieval, and ingestion
- observability_protocols: Tracing, metrics, and logging
- agent_protocols: Agent lifecycle, tools, and orchestration

Version: 1.0.0
GMP: di-dip-phase1-abstractions
Author: Top Frontier AI Lab
"""

from __future__ import annotations

# ============================================================================
__dora_meta__ = {
    "component_name": "Protocol Definitions",
    "module_version": "1.0.0",
    "created_by": "cryptoxdog",
    "created_at": "2026-01-20T14:10:12Z",
    "updated_at": "2026-01-31T22:21:48Z",
    "layer": "foundation",
    "domain": "core",
    "module_name": "__init__",
    "type": "utility",
    "status": "production",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": ["Neo4j"],
        "memory_layers": ["semantic_memory"],
        "imported_by": [],
    },
}
# ============================================================================

# Agent protocols
from core.protocols.agent_protocols import (
    ActivatableAgent,
    AgentContext,
    AgentOrchestrator,
    AgentRegistry,
    AgentState,
    StateManager,
    ToolExecutor,
)
from core.protocols.connection_protocols import (
    ConnectionPoolProtocol,
    ConnectionProtocol,
    ConnectionState,
    PooledConnection,
    StandardConnectionPool,
)

# Resilience protocols (GMP-125) - error handling, validation, connection, retry, rate limiting
from core.protocols.error_handling_protocols import (
    ErrorCategory,
    ErrorContext,
    ErrorHandlingProtocol,
    ErrorSeverity,
    StandardErrorHandler,
    with_error_handling,
)

# Kernel protocols
from core.protocols.kernel_protocols import (
    IntegrityVerifier,
    KernelActivator,
    KernelAwareAgent,
    KernelDiscovery,
    KernelStateManager,
    KernelValidator,
)

# Memory protocols
from core.protocols.memory_protocols import (
    CacheClient,
    GraphClient,
    IngestionPipeline,
    MemoryRepository,
    RetrievalStrategy,
    VectorStore,
)

# Observability protocols
from core.protocols.observability_protocols import (
    HealthChecker,
    LogExporter,
    MetricsCollector,
    ObservabilityService,
    SpanEmitter,
    SpanKind,
    SpanStatus,
    TraceContext,
)
from core.protocols.rate_limiting_protocols import (
    RateLimitExceededError,
    RateLimitingProtocol,
    RateLimitPolicy,
    RateLimitStrategy,
    StandardRateLimiter,
    rate_limited,
)
from core.protocols.retry_protocols import (
    BackoffStrategy,
    RetryPolicy,
    RetryProtocol,
    StandardRetryHandler,
    with_retry,
)

# High-level service protocols (PR #49 / GMP-114)
from core.protocols.service_protocols import (
    CacheService,
    GovernanceService,
    LLMService,
    MemoryService,
    ToolRegistry,
    WorldModelService,
)

# Substrate protocols (PR #52 / GMP-116) - lower-level memory substrate abstractions
from core.protocols.substrate_protocols import (
    DAGProtocol,
    EmbeddingProviderProtocol,
    SemanticServiceProtocol,
    SubstrateRepositoryProtocol,
)
from core.protocols.validation_protocols import (
    StandardValidator,
    ValidationError,
    ValidationProtocol,
    ValidationResult,
    ValidationSeverity,
    validate_input,
)

__all__ = [
    # Agent protocols
    "ActivatableAgent",
    "AgentContext",
    "AgentOrchestrator",
    "AgentRegistry",
    "AgentState",
    "BackoffStrategy",
    # Memory protocols
    "CacheClient",
    "ConnectionPoolProtocol",
    # Connection protocols (GMP-125)
    "ConnectionProtocol",
    "ConnectionState",
    "DAGProtocol",
    "EmbeddingProviderProtocol",
    "ErrorCategory",
    "ErrorContext",
    # Error handling protocols (GMP-125)
    "CacheService",
    "ErrorHandlingProtocol",
    "ErrorSeverity",
    "GovernanceService",
    "GraphClient",
    "HealthChecker",
    "IngestionPipeline",
    "IntegrityVerifier",
    "KernelActivator",
    "KernelAwareAgent",
    "KernelDiscovery",
    "KernelStateManager",
    # Kernel protocols
    "KernelValidator",
    "LLMService",
    "LogExporter",
    "MemoryRepository",
    # High-level service protocols (PR #49 / GMP-114)
    "MemoryService",
    "MetricsCollector",
    "ToolRegistry",
    "ObservabilityService",
    "PooledConnection",
    "RateLimitExceededError",
    "RateLimitPolicy",
    "RateLimitStrategy",
    # Rate limiting protocols (GMP-125)
    "RateLimitingProtocol",
    "RetrievalStrategy",
    "RetryPolicy",
    # Retry protocols (GMP-125)
    "RetryProtocol",
    "SemanticServiceProtocol",
    # Observability protocols
    "SpanEmitter",
    "SpanKind",
    "SpanStatus",
    "StandardConnectionPool",
    "StandardErrorHandler",
    "StandardRateLimiter",
    "StandardRetryHandler",
    "StandardValidator",
    "StateManager",
    # Substrate protocols (PR #52 / GMP-116)
    "SubstrateRepositoryProtocol",
    "ToolExecutor",
    "TraceContext",
    "ValidationError",
    # Validation protocols (GMP-125)
    "ValidationProtocol",
    "ValidationResult",
    "ValidationSeverity",
    "VectorStore",
    "rate_limited",
    "validate_input",
    "with_error_handling",
    "with_retry",
    "WorldModelService",
]

__version__ = "1.0.0"
# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "COR-FOUN-208",
    "governance_level": "critical",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [
        "core.protocols.agent_protocols",
        "core.protocols.connection_protocols",
        "core.protocols.error_handling_protocols",
        "core.protocols.kernel_protocols",
        "core.protocols.memory_protocols",
    ],
    "tags": [
        "auth",
        "caching",
        "core",
        "foundation",
        "metrics",
        "testing",
        "tracing",
        "utility",
    ],
    "keywords": [
        "abstractions",
        "agent",
        "definitions",
        "dependency",
        "frontier",
        "kernel",
        "memory",
        "protocol",
    ],
    "business_value": "Utility module for   init  ",
    "last_modified": "2026-01-31T22:21:48Z",
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
