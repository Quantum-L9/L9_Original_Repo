# CORE KERNELS & MEMORY SUPERPACK

**Risk Tier:** T3 (High-Impact) | **Auto-Generated**

---

## Purpose

Map kernel runtime contracts, memory pipeline, substrate protocols, and type system.

---

## Kernel Runtime Architecture

```
7-Phase Bootstrap (immutable sequence):
Phase 1: Load config & credentials
Phase 2: Initialize memory substrates (PostgreSQL + Redis + Neo4j)
Phase 3: Wire kernel runtime (ExecutorComposer)
Phase 4: Load governance engine
Phase 5: Load dynamic tools registry
Phase 6: Bind orchestrators (session + background)
Phase 7: Start listener (HTTP/WebSocket)
```

## Memory Pipeline (Canonical Path)

```
Entry: Orchestrator → PacketEnvelope
  ↓
write_packet() ← CANONICAL PATH (all writes must go here)
  ├─ ingest_packet() [LLM context, metadata extraction]
  ├─ emit_packet() [dag node creation]
  └─ Substrate adapters (PostgreSQL, Redis, Neo4j)
  ↓
Exit: DAG node stored, memory service notified
```

## Memory Modules (AST Scanned)

| Module | Classes | Functions | Async | LOC |
|--------|---------|-----------|-------|-----|
| `memory.__init__` | 0 | 0 |  | 457 |
| `memory.active_encoder` | 5 | 2 |  | 749 |
| `memory.agent_persistence` | 2 | 0 |  | 683 |
| `memory.audit_utils` | 1 | 12 |  | 642 |
| `memory.blob_store` | 2 | 3 |  | 404 |
| `memory.checkpoint.__init__` | 0 | 0 |  | 14 |
| `memory.checkpoint.cursor_checkpoint_manager` | 1 | 0 |  | 221 |
| `memory.checkpoint.postgres_saver` | 2 | 0 |  | 505 |
| `memory.checkpoint_manager` | 1 | 0 |  | 89 |
| `memory.checkpoint_metrics` | 1 | 3 |  | 503 |
| `memory.checkpoint_validator` | 2 | 0 |  | 291 |
| `memory.consolidation` | 2 | 0 |  | 769 |
| `memory.context_builder` | 3 | 2 |  | 495 |
| `memory.cross_encoder_reranker` | 3 | 3 |  | 425 |
| `memory.cypher_templates` | 3 | 3 | ✓ | 677 |
| `memory.dead_letter` | 2 | 0 |  | 245 |
| `memory.dead_letter_queue` | 2 | 0 |  | 366 |
| `memory.deduplication` | 5 | 0 |  | 578 |
| `memory.enrichment_dag` | 5 | 1 |  | 736 |
| `memory.execution_plan_snapshot` | 5 | 1 |  | 529 |
| `memory.extractor.__init__` | 0 | 0 |  | 21 |
| `memory.extractor.agent_config_extractor` | 1 | 0 |  | 303 |
| `memory.extractor.base_extractor` | 1 | 0 |  | 131 |
| `memory.extractor.code_extractor` | 1 | 0 |  | 221 |
| `memory.extractor.ingestion.__init__` | 0 | 0 |  | 1 |
| `memory.extractor.memory_extractor` | 1 | 0 |  | 213 |
| `memory.extractor.module_schema_extractor` | 1 | 0 |  | 156 |
| `memory.gap_detector` | 1 | 0 |  | 469 |
| `memory.governance_gate` | 1 | 12 | ✓ | 389 |
| `memory.governance_hooks` | 10 | 1 |  | 629 |
| `memory.governance_patterns` | 2 | 1 |  | 223 |
| `memory.graph_client` | 1 | 2 | ✓ | 977 |
| `memory.graph_memory` | 7 | 3 | ✓ | 918 |
| `memory.graph_search_cache` | 2 | 4 | ✓ | 317 |
| `memory.hierarchical_summarizer` | 4 | 0 |  | 577 |
| `memory.housekeeping` | 1 | 2 |  | 513 |
| `memory.hybrid_rag` | 8 | 2 | ✓ | 899 |
| `memory.identity_tier` | 4 | 2 |  | 626 |
| `memory.importance_manager` | 4 | 2 |  | 633 |
| `memory.index_syncer` | 1 | 0 |  | 132 |
| `memory.ingestion` | 1 | 4 | ✓ | 1057 |
| `memory.insight_extraction` | 1 | 2 |  | 552 |
| `memory.migration_runner` | 1 | 2 | ✓ | 283 |
| `memory.neo4j_strategy_memory` | 2 | 1 |  | 814 |
| `memory.neural_decay_scheduler` | 3 | 0 |  | 597 |
| `memory.packet_serializer` | 0 | 5 |  | 119 |
| `memory.predictive_cache` | 1 | 0 |  | 648 |
| `memory.query_cache` | 1 | 2 |  | 349 |
| `memory.query_classifier` | 1 | 1 |  | 374 |
| `memory.reasoning_replay` | 2 | 0 |  | 485 |
| `memory.retention_engine` | 3 | 0 |  | 378 |
| `memory.retrieval` | 1 | 5 | ✓ | 1444 |
| `memory.retrieval_ranking` | 3 | 2 |  | 531 |
| `memory.retrieval_strategy` | 5 | 2 |  | 958 |
| `memory.saga` | 10 | 1 | ✓ | 799 |
| `memory.saga_patterns` | 1 | 11 | ✓ | 811 |
| `memory.schema_introspection` | 9 | 1 | ✓ | 772 |
| `memory.semantic_search` | 1 | 1 | ✓ | 171 |
| `memory.service_adapter` | 1 | 1 |  | 275 |
| `memory.slack_ingest` | 0 | 13 | ✓ | 1812 |
| `memory.smoke_test` | 0 | 2 | ✓ | 204 |
| `memory.state_manager` | 1 | 0 |  | 468 |
| `memory.strategymemory` | 5 | 0 |  | 420 |
| `memory.substrate_alignment` | 2 | 0 |  | 268 |
| `memory.substrate_dag` | 2 | 16 | ✓ | 1421 |
| `memory.substrate_dag_wrapper` | 2 | 0 |  | 299 |
| `memory.substrate_models` | 15 | 0 |  | 572 |
| `memory.substrate_repository` | 1 | 5 | ✓ | 2517 |
| `memory.substrate_repository_batch_helpers` | 1 | 1 | ✓ | 465 |
| `memory.substrate_repository_cached` | 1 | 0 |  | 277 |
| `memory.substrate_semantic` | 4 | 2 | ✓ | 715 |
| `memory.substrate_service` | 1 | 4 | ✓ | 1401 |
| `memory.timeline_service` | 1 | 0 |  | 117 |
| `memory.tool_audit` | 0 | 4 | ✓ | 370 |
| `memory.tool_router` | 4 | 3 | ✓ | 738 |
| `memory.validators.__init__` | 0 | 0 |  | 6 |
| `memory.validators.packet_validator` | 2 | 0 |  | 338 |
| `memory.vector_search_config` | 1 | 2 |  | 111 |
| `memory.warming_models` | 10 | 0 |  | 230 |
| `memory.warming_service` | 1 | 1 | ✓ | 503 |
| `world_model.__init__` | 0 | 0 |  | 164 |
| `world_model._pack_staging.loader` | 1 | 0 |  | 448 |
| `world_model._pack_staging.neo4j_substrate` | 2 | 0 |  | 570 |
| `world_model._pack_staging.orchestrator` | 2 | 0 |  | 543 |
| `world_model._pack_staging.postgres_substrate` | 2 | 0 |  | 629 |
| `world_model._pack_staging.query_engine` | 2 | 0 |  | 516 |
| `world_model._pack_staging.redis_substrate` | 2 | 0 |  | 516 |
| `world_model._pack_staging.registry` | 1 | 0 |  | 377 |
| `world_model._pack_staging.state` | 1 | 0 |  | 385 |
| `world_model._pack_staging.test_integration` | 5 | 0 |  | 423 |
| `world_model._pack_staging.updater` | 3 | 0 |  | 424 |
| `world_model.causal_graph` | 3 | 0 |  | 730 |
| `world_model.causal_mapper` | 11 | 0 |  | 1600 |
| `world_model.engine` | 1 | 3 | ✓ | 885 |
| `world_model.interfaces` | 5 | 0 |  | 305 |
| `world_model.knowledge_ingestor` | 7 | 0 |  | 1857 |
| `world_model.loader` | 1 | 0 |  | 650 |
| `world_model.nodes.__init__` | 0 | 0 |  | 45 |
| `world_model.nodes.service_nodes` | 1 | 4 | ✓ | 417 |
| `world_model.nodes.update_world_model_node` | 1 | 2 | ✓ | 262 |
| `world_model.query_engine` | 2 | 0 |  | 602 |
| `world_model.reflection_memory` | 7 | 0 |  | 1354 |
| `world_model.registry` | 3 | 0 |  | 501 |
| `world_model.repository` | 4 | 4 | ✓ | 955 |
| `world_model.runtime` | 9 | 2 | ✓ | 2100 |
| `world_model.seed_loader` | 1 | 1 | ✓ | 863 |
| `world_model.service` | 1 | 2 | ✓ | 728 |
| `world_model.state` | 3 | 0 |  | 564 |
| `world_model.updater` | 3 | 0 |  | 821 |
| `world_model.world_model_service` | 5 | 2 |  | 1017 |

**Total:** 110 modules, 63646 LOC, 30 async

## Pydantic Models (BaseModel subclasses)

- `memory.warming_models.AttentionConfig`
- `memory.warming_models.SubgraphEntry`
- `memory.warming_models.CacheMetrics`
- `memory.warming_models.PredictiveCacheConfig`
- `memory.substrate_models.StructuredReasoningBlock`
- `memory.substrate_models.SubstrateState`
- `memory.substrate_models.AgentMemoryEventRow`
- `memory.substrate_models.SemanticMemoryRow`
- `memory.substrate_models.ReasoningTraceRow`
- `memory.substrate_models.PacketStoreRow`
- `memory.substrate_models.GraphCheckpointRow`
- `memory.substrate_models.KnowledgeFact`
- `memory.substrate_models.KnowledgeFactRow`
- `memory.substrate_models.ExtractedInsight`
- `memory.substrate_models.EnrichmentResult`
- `memory.substrate_models.SemanticFactRow`
- `memory.substrate_models.EpisodicEventRow`
- `memory.substrate_models.EpisodicSemanticLinkRow`
- `memory.strategymemory.StrategyCandidate`
- `memory.strategymemory.StrategyRetrievalRequest`
- `memory.strategymemory.StrategyFeedback`
- `memory.graph_search_cache.GraphSearchContext`
- `memory.graph_search_cache.GraphSearchResult`
- `memory.governance_patterns.GovernancePattern`
- `memory.semantic_search.SearchHit`

## Key Services

- `memory.timeline_service.TimelineService`
  - `__init__()`
  - `get_recent_events()`
  - `get_timeline_json()`
- `memory.strategymemory.IStrategyMemoryService`
  - `retrieve_strategies()`
  - `record_new_strategy()`
  - `update_strategy_outcome()`
- `memory.strategymemory.StrategyMemoryService`
  - `__init__()`
  - `retrieve_strategies()`
  - `record_new_strategy()`
- `memory.substrate_service.MemorySubstrateService`
  - `__init__()`
  - `_require_rls_context()`
  - `set_session_scope()`
- `memory.substrate_repository_cached.CachedSubstrateRepository`
  - `__init__()`
  - `_cache()`
  - `get_packet()`
- `memory.neo4j_strategy_memory.Neo4jStrategyMemoryService`
  - `__init__()`
  - `retrieve_strategies()`
  - `record_new_strategy()`
- `memory.substrate_semantic.SemanticService`
  - `__init__()`
  - `embed_and_store()`
  - `generate_embedding()`
- `memory.identity_tier.IdentityTierService`
  - `__init__()`
  - `set_repository()`
  - `create_identity_fact()`
- `memory.warming_service.MemoryWarmingService`
  - `__init__()`
  - `initialize()`
  - `warm_for_query()`
- `memory.substrate_repository.SubstrateRepository`
  - `__init__()`
  - `connect()`
  - `disconnect()`
- `memory.agent_persistence.AgentPersistenceService`
  - `__init__()`
  - `set_service()`
  - `set_repository()`
- `memory.service_adapter.MemoryServiceAdapter`
  - `__init__()`
  - `store()`
  - `retrieve()`
- `world_model.service.WorldModelService`
  - `__init__()`
  - `get_entity()`
  - `list_entities()`
- `world_model.world_model_service.WorldModelServiceAPI`
  - `__init__()`
  - `initialize()`
  - `get_context()`
- `world_model.repository.WorldModelRepository`
  - `__init__()`
  - `_ensure_scope()`
  - `set_session_scope()`

## Change Checklist

Before modifying memory modules:

1. [ ] Verify all writes go through `write_packet()`
2. [ ] Test with all substrate adapters
3. [ ] Update memory integration tests
4. [ ] Verify 7-phase bootstrap sequence unchanged

---

*Auto-generated by `tools/superpack_reports/` | Regenerate: `make superpacks`*
