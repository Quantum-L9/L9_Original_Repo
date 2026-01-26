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

from world_model.causal_graph import CausalGraph
from world_model.causal_mapper import (  # v1.2.0 additions
    CausalEdge,
    CausalLink,
    CausalMapper,
    CausalNode,
    CausalPath,
    CausalQuery,
    CausalQueryResult,
    CausalRelationType,
    CausalStrength,
    Decision,
    Outcome,
)

# Async singleton (v1.2.0)
# Core components
from world_model.engine import (
    WorldModelEngine,
    get_world_model_engine,
    init_world_model_engine,
    reset_world_model_engine,
)
from world_model.interfaces import (
    IWorldModelEngine,
    IWorldModelState,
    IWorldModelUpdater,
)
from world_model.knowledge_ingestor import (
    ExtractedFact,
    IngestorConfig,
    IngestResult,
    KnowledgeIngestor,
    NormalizedHeuristic,
    NormalizedPattern,
    SourceType,
)
from world_model.loader import WorldModelLoader

# LangGraph nodes (v1.0.0+)
from world_model.nodes import (
    WorldModelGraphState,
    WorldModelNodeState,
    update_world_model_node,
    world_model_query_node,
    world_model_service_update_node,
    world_model_snapshot_node,
)
from world_model.query_engine import QueryContext, QueryEngine
from world_model.reflection_memory import (  # v1.2.0 additions
    Improvement,
    Pattern,
    Reflection,
    ReflectionMemory,
    ReflectionPriority,
    ReflectionType,
    TaskReflection,
)
from world_model.registry import WorldModelRegistry

# Database persistence (v1.0.0+)
from world_model.repository import (
    WorldModelEntityRow,
    WorldModelRepository,
    WorldModelSnapshotRow,
    WorldModelUpdateRow,
    get_world_model_repository,
)

# IR Engine integration (v2.0.0+)
from world_model.runtime import (
    MemorySubstratePacketSource,
    PacketSource,
    QueryPattern,
    RuntimeConfig,
    RuntimeMode,
    RuntimeStats,
    SimulationVariant,
    UpdateRecord,
    WorldModelRuntime,
)

# Service layer (v1.0.0+)
from world_model.service import WorldModelService, get_world_model_service
from world_model.state import Entity, Relation, WorldModelState
from world_model.updater import WorldModelUpdater

# Service API layer (v2.0.0+)
from world_model.world_model_service import (
    ConstraintSet,
    HeuristicMatch,
    PatternMatch,
    WorldContext,
    WorldModelServiceAPI,
    get_world_model_service_api,
    reset_world_model_service_api,
)

__all__ = [
    "CausalEdge",
    "CausalGraph",
    "CausalLink",
    # Causal Mapper (v2.0.0+)
    "CausalMapper",
    "CausalNode",
    "CausalPath",
    "CausalQuery",
    "CausalQueryResult",
    "CausalRelationType",
    "CausalStrength",
    "ConstraintSet",
    "Decision",
    "Entity",
    "ExtractedFact",
    "HeuristicMatch",
    # Interfaces
    "IWorldModelEngine",
    "IWorldModelState",
    "IWorldModelUpdater",
    "Improvement",
    "IngestResult",
    "IngestorConfig",
    # Knowledge Ingestor (v2.0.0+)
    "KnowledgeIngestor",
    "MemorySubstratePacketSource",
    "NormalizedHeuristic",
    "NormalizedPattern",
    "Outcome",
    "PacketSource",
    "Pattern",
    "PatternMatch",
    "QueryContext",
    "QueryEngine",
    "QueryPattern",
    "Reflection",
    # Reflection Memory (v2.0.0+)
    "ReflectionMemory",
    "ReflectionPriority",
    "ReflectionType",
    "Relation",
    "RuntimeConfig",
    "RuntimeMode",
    "RuntimeStats",
    "SimulationVariant",
    "SourceType",
    "TaskReflection",
    "UpdateRecord",
    "WorldContext",
    # Core
    "WorldModelEngine",
    "WorldModelEntityRow",
    "WorldModelGraphState",
    "WorldModelLoader",
    "WorldModelNodeState",
    "WorldModelRegistry",
    # Repository
    "WorldModelRepository",
    # Runtime (v2.0.0+)
    "WorldModelRuntime",
    # Service
    "WorldModelService",
    # Service API (v2.0.0+)
    "WorldModelServiceAPI",
    "WorldModelSnapshotRow",
    "WorldModelState",
    "WorldModelUpdateRow",
    "WorldModelUpdater",
    "get_world_model_engine",
    "get_world_model_repository",
    "get_world_model_service",
    "get_world_model_service_api",
    "init_world_model_engine",
    "reset_world_model_engine",
    "reset_world_model_service_api",
    # LangGraph Nodes
    "update_world_model_node",
    "world_model_query_node",
    "world_model_service_update_node",
    "world_model_snapshot_node",
]

__version__ = "2.0.0"
