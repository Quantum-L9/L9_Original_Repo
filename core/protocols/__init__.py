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
    GovernanceService,
    LLMService,
    MemoryService,
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
]

__version__ = "1.0.0"
