# Dead Code Triage: `memory`

**Date:** 2026-02-14 05:43 UTC

## Symbol Classification

**USED** (47): `AuditReport`, `CacheMetrics`, `ConsolidationPipeline`, `DecayResult`, `DeduplicationEngine`, `EncodingResult`, `EnrichmentDAG`, `EnrichmentResult`, `ExtractedInsight`, `GapDetector`, `HierarchicalSummarizer`, `HousekeepingEngine`, `IStrategyMemoryService`, `IngestionPipeline`, `KnowledgeFact`, `KnowledgeFactRow`, `MemoryGovernanceContext`, `MemoryWarmingService`, `Neo4jStrategyMemoryService`, `NeuralDecayScheduler`
  ... and 27 more
**INTERNAL_ONLY** (35): `CheckpointValidator`, `ConsolidationReport`, `DatabaseType`, `EnrichmentConfig`, `EnrichmentStatus`, `EnrichmentStrategy`, `EnrichmentTier`, `GapSeverity`, `HybridRAGPipeline`, `InsightExtractionPipeline`, `KnowledgeGap`, `MemoryContext`, `MergeStrategy`, `PredictiveCache`, `PredictiveCacheConfig`, `ReferenceCountingService`, `RetentionEngine`, `RetrievalPipeline`, `SagaBuilder`, `SagaContext`
  ... and 15 more
**TEST_ONLY** (47): `ActiveMemoryEncoder`, `ConversationContext`, `ConversationGraphMemory`, `CypherTemplate`, `CypherTemplateCategory`, `CypherTemplateLibrary`, `DecayConfig`, `DuplicateGroup`, `ExtractedLearning`, `GraphMessage`, `HybridSearchResult`, `ImportanceConfig`, `ImportanceManager`, `ImportanceUpdate`, `LearningExtractor`, `MessageRole`, `PacketRefCount`, `SagaStatus`, `SagaStepStatus`, `StrategyMemoryService`
  ... and 27 more
**ZERO_REF** (23): `ActionProposal`, `AlignmentReport`, `AttentionConfig`, `CHECKPOINT_PROMETHEUS_AVAILABLE`, `CheckpointMetrics`, `DeduplicationEngineReport`, `GraphSession`, `Neo4jIntrospector`, `PostgresIntrospector`, `ReasoningPhase`, `RetentionResult`, `SagaStep`, `SchemaIntrospector`, `SchemaVersion`, `StrategyMemoryConfig`, `ThinkingOutput`, `find_tools`, `get_checkpoint_metrics`, `get_ingestion_pipeline`, `get_schema_introspector`
  ... and 3 more

## File Classification

**WIRED** (59):
- `memory/active_encoder.py`
- `memory/agent_persistence.py`
- `memory/audit_utils.py`
- `memory/checkpoint_metrics.py`
- `memory/consolidation.py`
- `memory/context_builder.py`
- `memory/cypher_templates.py`
- `memory/dead_letter.py`
- `memory/deduplication.py`
- `memory/enrichment_dag.py`
- `memory/execution_plan_snapshot.py`
- `memory/gap_detector.py`
- `memory/governance_gate.py`
- `memory/governance_hooks.py`
- `memory/governance_patterns.py`
- `memory/graph_client.py`
- `memory/graph_memory.py`
- `memory/graph_search_cache.py`
- `memory/hierarchical_summarizer.py`
- `memory/housekeeping.py`
- `memory/hybrid_rag.py`
- `memory/identity_tier.py`
- `memory/importance_manager.py`
- `memory/ingestion.py`
- `memory/migration_runner.py`
- `memory/neo4j_strategy_memory.py`
- `memory/neural_decay_scheduler.py`
- `memory/packet_serializer.py`
- `memory/predictive_cache.py`
- `memory/query_cache.py`
- `memory/query_classifier.py`
- `memory/reasoning_replay.py`
- `memory/retention_engine.py`
- `memory/retention_refcount.py`
- `memory/retrieval.py`
- `memory/retrieval_ranking.py`
- `memory/retrieval_strategy.py`
- `memory/saga.py`
- `memory/saga_patterns.py`
- `memory/semantic_search.py`
- `memory/service_adapter.py`
- `memory/slack_ingest.py`
- `memory/state_manager.py`
- `memory/strategymemory.py`
- `memory/substrate_alignment.py`
- `memory/substrate_dag.py`
- `memory/substrate_dag_wrapper.py`
- `memory/substrate_models.py`
- `memory/substrate_repository.py`
- `memory/substrate_repository_batch_helpers.py`
- `memory/substrate_semantic.py`
- `memory/substrate_service.py`
- `memory/timeline_service.py`
- `memory/tool_audit.py`
- `memory/tool_router.py`
- `memory/tools.py`
- `memory/vector_search_config.py`
- `memory/warming_models.py`
- `memory/warming_service.py`
**INTERNAL_ONLY** (1):
- `memory/checkpoint_validator.py`
**WIP** (8):
- `memory/blob_store.py`
- `memory/cross_encoder_reranker.py`
- `memory/dead_letter_queue.py`
- `memory/entity_extraction.py`
- `memory/schema_introspection.py`
- `memory/substrate_repository_cached.py`
- `memory/text_utils.py`
- `memory/working_memory_adapter.py`
**ASPIRATIONAL** (4):
- `memory/checkpoint_manager.py`
- `memory/index_syncer.py`
- `memory/insight_extraction.py`
- `memory/smoke_test.py`

## Recommended Actions

### Remove 35 internal-only symbols from `__all__`
These are used within the package but not externally. Remove from `__all__` to reduce API surface noise.

### Review 23 zero-reference symbols
These have no references anywhere (not even internal). Either wire them or remove from `__all__`.

### Wire 8 WIP files
Recently created but not yet integrated.
