"""
L9 World Model Runtime
======================

Central semantic state store for the L9 system.
Maintains entities, attributes, and relationships derived from memory insights.

Components:
- Engine: Core world model operations
- State: In-memory entity/relation storage
- Repository: PostgreSQL persistence layer
- Service: High-level API with insight integration
- Nodes: LangGraph-compatible nodes

Specification Sources:
- WorldModelOS.yaml
- world_model_layer.yaml
- PlasticRecycling_World Model-Blueprint.md
- reasoning kernel 01–05

Compatibility:
- L9 core schemas
- L9 memory substrate (PacketEnvelope v1.0.1)
- LangGraph nodes
- Reasoning kernel integration
- Future LongRAG support

Version: 1.0.0 (production)
"""

# Core components
from world_model.engine import WorldModelEngine, get_world_model_engine
from world_model.state import WorldModelState, Entity, Relation
from world_model.causal_graph import CausalGraph
from world_model.registry import WorldModelRegistry
from world_model.loader import WorldModelLoader
from world_model.updater import WorldModelUpdater
from world_model.query_engine import QueryEngine, QueryContext
from world_model.interfaces import (
    IWorldModelEngine,
    IWorldModelState,
    IWorldModelUpdater,
)

# Database persistence (v1.0.0+)
from world_model.repository import (
    WorldModelRepository,
    WorldModelEntityRow,
    WorldModelUpdateRow,
    WorldModelSnapshotRow,
    get_world_model_repository,
)

# Service layer (v1.0.0+)
from world_model.service import (
    WorldModelService,
    get_world_model_service,
)

# Service API layer (v2.0.0+)
from world_model.world_model_service import (
    WorldModelServiceAPI,
    get_world_model_service_api,
    reset_world_model_service_api,
    WorldContext,
    ConstraintSet,
    PatternMatch,
    HeuristicMatch,
)

# LangGraph nodes (v1.0.0+)
from world_model.nodes import (
    update_world_model_node,
    world_model_service_update_node,
    world_model_snapshot_node,
    world_model_query_node,
    WorldModelGraphState,
    WorldModelNodeState,
)

# IR Engine integration (v2.0.0+)
from world_model.runtime import (
    WorldModelRuntime,
    RuntimeConfig,
    RuntimeMode,
    UpdateRecord,
    RuntimeStats,
    PacketSource,
    MemorySubstratePacketSource,
    QueryPattern,
    SimulationVariant,
)
from world_model.knowledge_ingestor import (
    KnowledgeIngestor,
    IngestorConfig,
    IngestResult,
    SourceType,
    ExtractedFact,
    NormalizedPattern,
    NormalizedHeuristic,
)
from world_model.causal_mapper import (
    CausalMapper,
    CausalNode,
    CausalEdge,
    CausalPath,
    CausalQuery,
    CausalQueryResult,
    CausalRelationType,
    CausalStrength,
    # v1.2.0 additions
    Decision,
    Outcome,
    CausalLink,
)
from world_model.reflection_memory import (
    ReflectionMemory,
    Reflection,
    ReflectionType,
    ReflectionPriority,
    Pattern,
    Improvement,
    # v1.2.0 additions
    TaskReflection,
)

# Async singleton (v1.2.0)
from world_model.engine import (
    init_world_model_engine,
    reset_world_model_engine,
)

__all__ = [
    # Core
    "WorldModelEngine",
    "get_world_model_engine",
    "init_world_model_engine",
    "reset_world_model_engine",
    "WorldModelState",
    "Entity",
    "Relation",
    "CausalGraph",
    "WorldModelRegistry",
    "WorldModelLoader",
    "WorldModelUpdater",
    "QueryEngine",
    "QueryContext",
    # Interfaces
    "IWorldModelEngine",
    "IWorldModelState",
    "IWorldModelUpdater",
    # Repository
    "WorldModelRepository",
    "WorldModelEntityRow",
    "WorldModelUpdateRow",
    "WorldModelSnapshotRow",
    "get_world_model_repository",
    # Service
    "WorldModelService",
    "get_world_model_service",
    # Service API (v2.0.0+)
    "WorldModelServiceAPI",
    "get_world_model_service_api",
    "reset_world_model_service_api",
    "WorldContext",
    "ConstraintSet",
    "PatternMatch",
    "HeuristicMatch",
    # LangGraph Nodes
    "update_world_model_node",
    "world_model_service_update_node",
    "world_model_snapshot_node",
    "world_model_query_node",
    "WorldModelGraphState",
    "WorldModelNodeState",
    # Runtime (v2.0.0+)
    "WorldModelRuntime",
    "RuntimeConfig",
    "RuntimeMode",
    "UpdateRecord",
    "RuntimeStats",
    "PacketSource",
    "MemorySubstratePacketSource",
    "QueryPattern",
    "SimulationVariant",
    # Knowledge Ingestor (v2.0.0+)
    "KnowledgeIngestor",
    "IngestorConfig",
    "IngestResult",
    "SourceType",
    "ExtractedFact",
    "NormalizedPattern",
    "NormalizedHeuristic",
    # Causal Mapper (v2.0.0+)
    "CausalMapper",
    "CausalNode",
    "CausalEdge",
    "CausalPath",
    "CausalQuery",
    "CausalQueryResult",
    "CausalRelationType",
    "CausalStrength",
    "Decision",
    "Outcome",
    "CausalLink",
    # Reflection Memory (v2.0.0+)
    "ReflectionMemory",
    "Reflection",
    "ReflectionType",
    "ReflectionPriority",
    "Pattern",
    "Improvement",
    "TaskReflection",
]

__version__ = "2.0.0"
