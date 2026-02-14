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

# ============================================================================
__dora_meta__ = {
    "component_name": "  Init  ",
    "module_version": "1.0.0 (production)",
    "created_by": "Igor Beylin",
    "created_at": "2025-12-09T01:02:49Z",
    "updated_at": "2026-01-31T22:21:54Z",
    "layer": "learning",
    "domain": "world_model",
    "module_name": "__init__",
    "type": "utility",
    "status": "production",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": ["PostgreSQL"],
        "memory_layers": ["semantic_memory", "working_memory"],
        "imported_by": [],
    },
}
# ============================================================================

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
    "CausalLink",
    # Causal Mapper (v2.0.0+)
    "CausalMapper",
    "CausalNode",
    "CausalPath",
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
    "Improvement",
    "IngestorConfig",
    # Knowledge Ingestor (v2.0.0+)
    "MemorySubstratePacketSource",
    "NormalizedHeuristic",
    "NormalizedPattern",
    "Outcome",
    "PacketSource",
    "Pattern",
    "PatternMatch",
    "QueryPattern",
    "Reflection",
    # Reflection Memory (v2.0.0+)
    "RuntimeConfig",
    "RuntimeMode",
    "RuntimeStats",
    "SimulationVariant",
    "TaskReflection",
    "UpdateRecord",
    "WorldContext",
    # Core
    "WorldModelEngine",
    "WorldModelEntityRow",
    "WorldModelRepository",
    # Runtime (v2.0.0+)
    "WorldModelRuntime",
    # Service
    "WorldModelService",
    # Service API (v2.0.0+)
    "WorldModelServiceAPI",
    "WorldModelSnapshotRow",
    "WorldModelUpdateRow",
    "get_world_model_service",
    "get_world_model_service_api",
    "init_world_model_engine",
    "reset_world_model_engine",
    "reset_world_model_service_api",
    # LangGraph Nodes
]

__version__ = "2.0.0"
# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "WOR-LEAR-010",
    "governance_level": "high",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": ["api", "learning", "utility", "world-model"],
    "keywords": [
        "core",
        "integration",
        "kernel",
        "langgraph",
        "memory",
        "model",
        "nodes",
        "reasoning",
    ],
    "business_value": "Utility module for   init  ",
    "last_modified": "2026-01-31T22:21:54Z",
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
