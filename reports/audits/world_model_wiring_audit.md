# Package Wiring Audit: world_model

**Date:** 2026-02-14 05:36 UTC

## Level B: File Wiring — `world_model`

Files checked: 16
- WIRED: 4
- PARTIAL: 11
- ORPHAN: 0
- ENTRYPOINT: 1
- TEST_ONLY: 0

| File | Ext Consumers | Test Consumers | Test File | Re-exported | Status |
|------|-------------:|---------------:|-----------|-------------|--------|
| `world_model/causal_graph.py` | 0 | 0 | - | Y | PARTIAL |
| `world_model/causal_mapper.py` | 2 | 0 | - | Y | OK |
| `world_model/engine.py` | 1 | 0 | - | Y | OK |
| `world_model/interfaces.py` | 0 | 0 | - | Y | PARTIAL |
| `world_model/knowledge_ingestor.py` | 0 | 0 | - | Y | PARTIAL |
| `world_model/loader.py` | 0 | 0 | - | Y | PARTIAL |
| `world_model/query_engine.py` | 0 | 0 | - | Y | PARTIAL |
| `world_model/reflection_memory.py` | 0 | 0 | - | Y | PARTIAL |
| `world_model/registry.py` | 0 | 0 | - | Y | PARTIAL |
| `world_model/repository.py` | 0 | 3 | Y | Y | PARTIAL |
| `world_model/runtime.py` | 1 | 2 | - | Y | OK |
| `world_model/seed_loader.py` | 0 | 0 | - | - | ENTRY |
| `world_model/service.py` | 7 | 0 | - | Y | OK |
| `world_model/state.py` | 0 | 0 | - | Y | PARTIAL |
| `world_model/updater.py` | 0 | 0 | - | Y | PARTIAL |
| `world_model/world_model_service.py` | 0 | 0 | - | Y | PARTIAL |

## Level C: API Instantiation — `world_model`

API Status: **HAS_API**
Symbols checked: 70
- USED: 15
- TEST_ONLY: 1
- UNUSED: 54

| Symbol | Ext | Test | Status |
|--------|----:|-----:|--------|
| `CausalEdge` | 0 | 0 | UNUSED |
| `CausalGraph` | 0 | 0 | UNUSED |
| `CausalLink` | 0 | 0 | UNUSED |
| `CausalPath` | 0 | 0 | UNUSED |
| `CausalQuery` | 0 | 0 | UNUSED |
| `CausalQueryResult` | 0 | 0 | UNUSED |
| `CausalRelationType` | 0 | 0 | UNUSED |
| `CausalStrength` | 0 | 0 | UNUSED |
| `ConstraintSet` | 0 | 0 | UNUSED |
| `ExtractedFact` | 0 | 0 | UNUSED |
| `HeuristicMatch` | 0 | 0 | UNUSED |
| `IWorldModelEngine` | 0 | 0 | UNUSED |
| `IWorldModelState` | 0 | 0 | UNUSED |
| `IWorldModelUpdater` | 0 | 0 | UNUSED |
| `IngestResult` | 0 | 0 | UNUSED |
| `IngestorConfig` | 0 | 0 | UNUSED |
| `KnowledgeIngestor` | 0 | 0 | UNUSED |
| `NormalizedHeuristic` | 0 | 0 | UNUSED |
| `NormalizedPattern` | 0 | 0 | UNUSED |
| `PacketSource` | 0 | 0 | UNUSED |
| `PatternMatch` | 0 | 0 | UNUSED |
| `QueryContext` | 0 | 0 | UNUSED |
| `QueryEngine` | 0 | 0 | UNUSED |
| `QueryPattern` | 0 | 0 | UNUSED |
| `ReflectionMemory` | 0 | 0 | UNUSED |
| `ReflectionPriority` | 0 | 0 | UNUSED |
| `ReflectionType` | 0 | 0 | UNUSED |
| `Relation` | 0 | 0 | UNUSED |
| `RuntimeMode` | 0 | 0 | UNUSED |
| `RuntimeStats` | 0 | 0 | UNUSED |
| `SimulationVariant` | 0 | 0 | UNUSED |
| `SourceType` | 0 | 0 | UNUSED |
| `TaskReflection` | 0 | 0 | UNUSED |
| `WorldContext` | 0 | 0 | UNUSED |
| `WorldModelEntityRow` | 0 | 0 | UNUSED |
| `WorldModelGraphState` | 0 | 0 | UNUSED |
| `WorldModelLoader` | 0 | 0 | UNUSED |
| `WorldModelNodeState` | 0 | 0 | UNUSED |
| `WorldModelRegistry` | 0 | 0 | UNUSED |
| `WorldModelRepository` | 0 | 3 | TEST_ONLY |
| `WorldModelServiceAPI` | 0 | 0 | UNUSED |
| `WorldModelSnapshotRow` | 0 | 0 | UNUSED |
| `WorldModelState` | 0 | 0 | UNUSED |
| `WorldModelUpdateRow` | 0 | 0 | UNUSED |
| `WorldModelUpdater` | 0 | 0 | UNUSED |
| `get_world_model_engine` | 0 | 0 | UNUSED |
| `get_world_model_repository` | 0 | 0 | UNUSED |
| `get_world_model_service_api` | 0 | 0 | UNUSED |
| `init_world_model_engine` | 0 | 0 | UNUSED |
| `reset_world_model_engine` | 0 | 0 | UNUSED |
| `reset_world_model_service_api` | 0 | 0 | UNUSED |
| `update_world_model_node` | 0 | 0 | UNUSED |
| `world_model_query_node` | 0 | 0 | UNUSED |
| `world_model_service_update_node` | 0 | 0 | UNUSED |
| `world_model_snapshot_node` | 0 | 0 | UNUSED |

**API-pattern symbols NOT in `__all__`:**
- `create_runtime_with_substrate`
- `get_or_create_runtime`
- `get_pool`
