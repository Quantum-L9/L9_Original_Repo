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

__all__ = [
    # Kernel protocols
    "KernelValidator",
    "KernelDiscovery",
    "IntegrityVerifier",
    "KernelActivator",
    "KernelStateManager",
    "KernelAwareAgent",
    # Memory protocols
    "CacheClient",
    "GraphClient",
    "VectorStore",
    "MemoryRepository",
    "IngestionPipeline",
    "RetrievalStrategy",
    # Observability protocols
    "SpanEmitter",
    "MetricsCollector",
    "TraceContext",
    "LogExporter",
    "HealthChecker",
    "ObservabilityService",
    "SpanKind",
    "SpanStatus",
    # Agent protocols
    "ActivatableAgent",
    "ToolExecutor",
    "StateManager",
    "AgentOrchestrator",
    "AgentRegistry",
    "AgentContext",
    "AgentState",
    # High-level service protocols (PR #49 / GMP-114)
    "MemoryService",
    "LLMService",
    "GovernanceService",
    # Substrate protocols (PR #52 / GMP-116)
    "SubstrateRepositoryProtocol",
    "EmbeddingProviderProtocol",
    "SemanticServiceProtocol",
    "DAGProtocol",
]

__version__ = "1.0.0"
