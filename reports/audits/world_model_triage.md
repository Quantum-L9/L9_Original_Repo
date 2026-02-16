# Dead Code Triage: `world_model`

**Date:** 2026-02-14 05:43 UTC

## Symbol Classification

**USED** (15): `CausalMapper`, `CausalNode`, `Decision`, `Entity`, `Improvement`, `MemorySubstratePacketSource`, `Outcome`, `Pattern`, `Reflection`, `RuntimeConfig`, `UpdateRecord`, `WorldModelEngine`, `WorldModelRuntime`, `WorldModelService`, `get_world_model_service`
**INTERNAL_ONLY** (27): `CausalEdge`, `CausalGraph`, `CausalQuery`, `IWorldModelState`, `IWorldModelUpdater`, `IngestResult`, `KnowledgeIngestor`, `QueryContext`, `QueryEngine`, `ReflectionMemory`, `ReflectionPriority`, `ReflectionType`, `Relation`, `SourceType`, `WorldModelGraphState`, `WorldModelLoader`, `WorldModelNodeState`, `WorldModelRegistry`, `WorldModelRepository`, `WorldModelState`
  ... and 7 more
**ZERO_REF** (28): `CausalLink`, `CausalPath`, `CausalQueryResult`, `CausalRelationType`, `CausalStrength`, `ConstraintSet`, `ExtractedFact`, `HeuristicMatch`, `IWorldModelEngine`, `IngestorConfig`, `NormalizedHeuristic`, `NormalizedPattern`, `PacketSource`, `PatternMatch`, `QueryPattern`, `RuntimeMode`, `RuntimeStats`, `SimulationVariant`, `TaskReflection`, `WorldContext`
  ... and 8 more

## File Classification

**WIRED** (5):
- `world_model/causal_mapper.py`
- `world_model/engine.py`
- `world_model/repository.py`
- `world_model/runtime.py`
- `world_model/service.py`
**INTERNAL_ONLY** (9):
- `world_model/causal_graph.py`
- `world_model/interfaces.py`
- `world_model/knowledge_ingestor.py`
- `world_model/loader.py`
- `world_model/query_engine.py`
- `world_model/reflection_memory.py`
- `world_model/registry.py`
- `world_model/state.py`
- `world_model/updater.py`
**ASPIRATIONAL** (2):
- `world_model/seed_loader.py`
- `world_model/world_model_service.py`

## Recommended Actions

### Remove 27 internal-only symbols from `__all__`
These are used within the package but not externally. Remove from `__all__` to reduce API surface noise.

### Review 28 zero-reference symbols
These have no references anywhere (not even internal). Either wire them or remove from `__all__`.
