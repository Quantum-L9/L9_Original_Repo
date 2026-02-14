# L9 Component Export Audit — Consolidated Report

**Generated:** 2026-02-14 05:49 UTC

## Summary

| Package | Files | `__all__` | Imports | Broken | Missing | Status |
|---------|------:|----------:|--------:|-------:|--------:|--------|
| `SDK` | 1 | 21 | 18 | 3 | 0 | FAIL |
| `adapters` | 0 | 1 | 0 | 1 | 0 | WARN (all, no imports) |
| `agents` | 6 | 15 | 16 | 0 | 1 | FAIL |
| `api` | 19 | 0 | 0 | 0 | 0 | FLAG (should have API) |
| `bootstrap` | 1 | 0 | 0 | - | - | EMPTY |
| `ci` | 20 | 0 | 0 | 0 | 0 | FLAG (should have API) |
| `clients` | 2 | 3 | 3 | 0 | 0 | OK |
| `collaborative_cells` | 6 | 8 | 8 | 0 | 0 | OK |
| `config` | 10 | 13 | 13 | 0 | 0 | OK |
| `core` | 10 | 0 | 0 | 0 | 0 | FLAG (should have API) |
| `domain_tensor_bridge` | 22 | 10 | 0 | 3 | 0 | WARN (all, no imports) |
| `email_agent` | 8 | 7 | 9 | 0 | 2 | FAIL |
| `governance` | 1 | 3 | 3 | 0 | 0 | OK |
| `graph_adapter` | 1 | 1 | 1 | 0 | 0 | OK |
| `ir_engine` | 12 | 50 | 52 | 0 | 2 | FAIL |
| `mac_agent` | 4 | 5 | 0 | 0 | 0 | WARN (all, no imports) |
| `memory` | 72 | 144 | 147 | 0 | 8 | FAIL |
| `memory_cache` | 3 | 9 | 9 | 0 | 0 | OK |
| `motifs` | 3 | 7 | 0 | 0 | 0 | WARN (all, no imports) |
| `orchestration` | 11 | 38 | 43 | 0 | 5 | FAIL |
| `orchestrators` | 2 | 11 | 0 | 0 | 0 | WARN (all, no imports) |
| `private` | 0 | 0 | 0 | - | - | EMPTY |
| `runtime` | 33 | 52 | 52 | 0 | 0 | OK |
| `scripts` | 26 | 0 | 0 | 0 | 0 | FLAG (should have API) |
| `services` | 7 | 0 | 0 | 0 | 0 | FLAG (should have API) |
| `simulation` | 3 | 10 | 10 | 0 | 0 | OK |
| `telemetry` | 3 | 0 | 0 | - | - | EMPTY |
| `tests` | 21 | 0 | 0 | 0 | 0 | FLAG (should have API) |
| `tools` | 3 | 0 | 0 | - | - | EMPTY |
| `workers` | 5 | 13 | 15 | 0 | 2 | FAIL |
| `workflows` | 10 | 5 | 18 | 0 | 13 | FAIL |
| `world_model` | 16 | 44 | 70 | 0 | 26 | FAIL |

**Totals:** 11 OK, 11 FAIL, 6 flagged, 4 skipped

## Details — Packages with Gaps

### `SDK` — 3 broken, 0 missing

**In `__all__` but not imported (broken):**
- `L9`
- `close_l9`
- `get_l9`

### `adapters` — 1 broken, 0 missing

**In `__all__` but not imported (broken):**
- `tensorglobe_bridge`

### `agents` — 0 broken, 1 missing

**Imported but not in `__all__` (missing):**
- `CoderAgentB`

### `domain_tensor_bridge` — 3 broken, 0 missing

**In `__all__` but not imported (broken):**
- `__footer_meta__`
- `__l9_trace__`
- `__version__`

### `email_agent` — 0 broken, 2 missing

**Imported but not in `__all__` (missing):**
- `create_flow`
- `exchange_code_for_tokens`

### `ir_engine` — 0 broken, 2 missing

**Imported but not in `__all__` (missing):**
- `GenerationTarget`
- `MetaContractValidationError`

### `memory` — 0 broken, 8 missing

**Imported but not in `__all__` (missing):**
- `CheckpointValidator`
- `InsightExtractionPipeline`
- `KnowledgeGap`
- `get_insight_pipeline`
- `get_saga_executor`
- `get_saga_patterns`
- `get_vector_config`
- `init_insight_pipeline`

### `orchestration` — 0 broken, 5 missing

**Imported but not in `__all__` (missing):**
- `CellOrchestrator`
- `KernelConfig`
- `OrchestratorKernel`
- `RoutingDecision`
- `UnifiedController`

### `workers` — 0 broken, 2 missing

**Imported but not in `__all__` (missing):**
- `RemediationEngineRequest`
- `ViolationPatternsRequest`

### `workflows` — 0 broken, 13 missing

**Imported but not in `__all__` (missing):**
- `ExtractionPattern`
- `FileMapping`
- `GateType`
- `SessionDAG`
- `SessionEdge`
- `SessionNode`
- `ValidationCheck`
- `WorkflowState`
- `_dags`
- `get_session_dag`
- `list_session_dags`
- `register_session_dag`
- `session_dag_registry`

### `world_model` — 0 broken, 26 missing

**Imported but not in `__all__` (missing):**
- `CausalEdge`
- `CausalGraph`
- `CausalQuery`
- `IWorldModelState`
- `IWorldModelUpdater`
- `IngestResult`
- `KnowledgeIngestor`
- `QueryContext`
- `QueryEngine`
- `ReflectionMemory`
- `ReflectionPriority`
- `ReflectionType`
- `Relation`
- `SourceType`
- `WorldModelGraphState`
- `WorldModelLoader`
- `WorldModelNodeState`
- `WorldModelRegistry`
- `WorldModelState`
- `WorldModelUpdater`
- `get_world_model_engine`
- `get_world_model_repository`
- `update_world_model_node`
- `world_model_query_node`
- `world_model_service_update_node`
- `world_model_snapshot_node`
