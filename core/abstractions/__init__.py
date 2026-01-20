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

# Kernel protocols
from core.abstractions.kernel_protocols import (
    IntegrityVerifier,
    KernelActivator,
    KernelAwareAgent,
    KernelDiscovery,
    KernelProtocols,
    KernelStateManager,
    KernelValidator,
)

# Memory protocols
from core.abstractions.memory_protocols import (
    CacheClient,
    GraphClient,
    IngestionPipeline,
    MemoryProtocols,
    MemoryRepository,
    RetrievalStrategy,
    VectorStore,
)

# Observability protocols
from core.abstractions.observability_protocols import (
    HealthChecker,
    LogExporter,
    MetricsCollector,
    ObservabilityProtocols,
    ObservabilityService,
    SpanEmitter,
    SpanKind,
    SpanStatus,
    TraceContext,
)

# Agent protocols
from core.abstractions.agent_protocols import (
    ActivatableAgent,
    AgentContext,
    AgentOrchestrator,
    AgentProtocols,
    AgentRegistry,
    AgentState,
    StateManager,
    ToolExecutor,
)

__all__ = [
    # Kernel protocols
    "KernelValidator",
    "KernelDiscovery",
    "IntegrityVerifier",
    "KernelActivator",
    "KernelStateManager",
    "KernelAwareAgent",
    "KernelProtocols",
    # Memory protocols
    "CacheClient",
    "GraphClient",
    "VectorStore",
    "MemoryRepository",
    "IngestionPipeline",
    "RetrievalStrategy",
    "MemoryProtocols",
    # Observability protocols
    "SpanEmitter",
    "MetricsCollector",
    "TraceContext",
    "LogExporter",
    "HealthChecker",
    "ObservabilityService",
    "SpanKind",
    "SpanStatus",
    "ObservabilityProtocols",
    # Agent protocols
    "ActivatableAgent",
    "ToolExecutor",
    "StateManager",
    "AgentOrchestrator",
    "AgentRegistry",
    "AgentContext",
    "AgentState",
    "AgentProtocols",
]

__version__ = "1.0.0"
