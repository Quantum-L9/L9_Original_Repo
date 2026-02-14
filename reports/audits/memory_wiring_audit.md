# Package Wiring Audit: memory

**Date:** 2026-02-14 05:36 UTC

## Level B: File Wiring — `memory`

Files checked: 72
- WIRED: 19
- PARTIAL: 32
- ORPHAN: 9
- ENTRYPOINT: 1
- TEST_ONLY: 11

| File | Ext Consumers | Test Consumers | Test File | Re-exported | Status |
|------|-------------:|---------------:|-----------|-------------|--------|
| `memory/active_encoder.py` | 0 | 1 | - | Y | PARTIAL |
| `memory/agent_persistence.py` | 4 | 1 | Y | - | PARTIAL |
| `memory/audit_utils.py` | 0 | 3 | - | Y | PARTIAL |
| `memory/blob_store.py` | 0 | 0 | - | - | ORPHAN |
| `memory/checkpoint_manager.py` | 0 | 0 | - | - | ORPHAN |
| `memory/checkpoint_metrics.py` | 1 | 1 | Y | Y | OK |
| `memory/checkpoint_validator.py` | 0 | 0 | - | Y | PARTIAL |
| `memory/consolidation.py` | 1 | 3 | Y | Y | OK |
| `memory/context_builder.py` | 0 | 1 | - | Y | PARTIAL |
| `memory/cross_encoder_reranker.py` | 0 | 0 | - | - | ORPHAN |
| `memory/cypher_templates.py` | 0 | 1 | Y | Y | PARTIAL |
| `memory/dead_letter.py` | 2 | 1 | - | - | PARTIAL |
| `memory/dead_letter_queue.py` | 0 | 0 | - | - | ORPHAN |
| `memory/deduplication.py` | 0 | 1 | - | Y | PARTIAL |
| `memory/enrichment_dag.py` | 0 | 1 | Y | Y | PARTIAL |
| `memory/entity_extraction.py` | 0 | 0 | - | - | ORPHAN |
| `memory/execution_plan_snapshot.py` | 0 | 1 | - | - | TEST |
| `memory/gap_detector.py` | 0 | 1 | - | Y | PARTIAL |
| `memory/governance_gate.py` | 13 | 9 | - | Y | OK |
| `memory/governance_hooks.py` | 0 | 1 | - | - | TEST |
| `memory/governance_patterns.py` | 1 | 0 | - | - | PARTIAL |
| `memory/graph_client.py` | 24 | 4 | - | Y | OK |
| `memory/graph_memory.py` | 0 | 1 | Y | Y | PARTIAL |
| `memory/graph_search_cache.py` | 1 | 1 | - | - | PARTIAL |
| `memory/hierarchical_summarizer.py` | 1 | 1 | - | Y | OK |
| `memory/housekeeping.py` | 2 | 0 | - | Y | OK |
| `memory/hybrid_rag.py` | 0 | 2 | Y | Y | PARTIAL |
| `memory/identity_tier.py` | 0 | 1 | - | Y | PARTIAL |
| `memory/importance_manager.py` | 0 | 1 | - | Y | PARTIAL |
| `memory/index_syncer.py` | 0 | 0 | - | - | ORPHAN |
| `memory/ingestion.py` | 10 | 6 | Y | Y | OK |
| `memory/insight_extraction.py` | 0 | 0 | - | Y | PARTIAL |
| `memory/migration_runner.py` | 3 | 0 | - | - | PARTIAL |
| `memory/neo4j_strategy_memory.py` | 2 | 2 | - | Y | OK |
| `memory/neural_decay_scheduler.py` | 1 | 1 | - | Y | OK |
| `memory/packet_serializer.py` | 0 | 1 | - | - | TEST |
| `memory/predictive_cache.py` | 0 | 1 | - | Y | PARTIAL |
| `memory/query_cache.py` | 1 | 1 | Y | - | PARTIAL |
| `memory/query_classifier.py` | 0 | 2 | Y | - | TEST |
| `memory/reasoning_replay.py` | 0 | 1 | Y | - | TEST |
| `memory/retention_engine.py` | 0 | 1 | - | Y | PARTIAL |
| `memory/retention_refcount.py` | 0 | 2 | Y | Y | PARTIAL |
| `memory/retrieval.py` | 2 | 3 | Y | Y | OK |
| `memory/retrieval_ranking.py` | 0 | 1 | - | - | TEST |
| `memory/retrieval_strategy.py` | 0 | 1 | - | - | TEST |
| `memory/saga.py` | 1 | 2 | Y | Y | OK |
| `memory/saga_patterns.py` | 0 | 2 | - | Y | PARTIAL |
| `memory/schema_introspection.py` | 0 | 0 | - | Y | PARTIAL |
| `memory/semantic_search.py` | 0 | 1 | - | - | TEST |
| `memory/service_adapter.py` | 1 | 1 | - | Y | OK |
| `memory/slack_ingest.py` | 2 | 3 | - | - | PARTIAL |
| `memory/smoke_test.py` | 0 | 0 | - | - | ENTRY |
| `memory/state_manager.py` | 1 | 0 | - | - | PARTIAL |
| `memory/strategymemory.py` | 1 | 2 | - | Y | OK |
| `memory/substrate_alignment.py` | 0 | 1 | Y | Y | PARTIAL |
| `memory/substrate_dag.py` | 3 | 11 | Y | Y | OK |
| `memory/substrate_dag_wrapper.py` | 2 | 2 | - | - | PARTIAL |
| `memory/substrate_models.py` | 3 | 4 | - | Y | OK |
| `memory/substrate_repository.py` | 12 | 5 | - | Y | OK |
| `memory/substrate_repository_batch_helpers.py` | 0 | 1 | - | - | TEST |
| `memory/substrate_repository_cached.py` | 0 | 0 | - | - | ORPHAN |
| `memory/substrate_semantic.py` | 1 | 4 | Y | Y | OK |
| `memory/substrate_service.py` | 53 | 17 | Y | Y | OK |
| `memory/text_utils.py` | 0 | 0 | - | - | ORPHAN |
| `memory/timeline_service.py` | 1 | 0 | - | - | PARTIAL |
| `memory/tool_audit.py` | 0 | 2 | Y | - | TEST |
| `memory/tool_router.py` | 0 | 1 | Y | Y | PARTIAL |
| `memory/tools.py` | 0 | 1 | - | - | TEST |
| `memory/vector_search_config.py` | 0 | 1 | - | Y | PARTIAL |
| `memory/warming_models.py` | 0 | 1 | - | Y | PARTIAL |
| `memory/warming_service.py` | 2 | 1 | - | Y | OK |
| `memory/working_memory_adapter.py` | 0 | 0 | - | - | ORPHAN |

## Level C: API Instantiation — `memory`

API Status: **HAS_API**
Symbols checked: 152
- USED: 47
- TEST_ONLY: 74
- UNUSED: 31

| Symbol | Ext | Test | Status |
|--------|----:|-----:|--------|
| `ActionProposal` | 0 | 0 | UNUSED |
| `ActiveMemoryEncoder` | 0 | 1 | TEST_ONLY |
| `AlignmentReport` | 0 | 0 | UNUSED |
| `AttentionConfig` | 0 | 0 | UNUSED |
| `CHECKPOINT_PROMETHEUS_AVAILABLE` | 0 | 0 | UNUSED |
| `CheckpointMetrics` | 0 | 0 | UNUSED |
| `CheckpointValidator` | 0 | 0 | UNUSED |
| `ConsolidationReport` | 0 | 1 | TEST_ONLY |
| `ConversationContext` | 0 | 1 | TEST_ONLY |
| `ConversationGraphMemory` | 0 | 1 | TEST_ONLY |
| `CypherTemplate` | 0 | 1 | TEST_ONLY |
| `CypherTemplateCategory` | 0 | 1 | TEST_ONLY |
| `CypherTemplateLibrary` | 0 | 1 | TEST_ONLY |
| `DatabaseType` | 0 | 1 | TEST_ONLY |
| `DecayConfig` | 0 | 1 | TEST_ONLY |
| `DeduplicationEngineReport` | 0 | 0 | UNUSED |
| `DuplicateGroup` | 0 | 1 | TEST_ONLY |
| `EnrichmentConfig` | 0 | 1 | TEST_ONLY |
| `EnrichmentStatus` | 0 | 1 | TEST_ONLY |
| `EnrichmentStrategy` | 0 | 1 | TEST_ONLY |
| `EnrichmentTier` | 0 | 1 | TEST_ONLY |
| `ExtractedLearning` | 0 | 1 | TEST_ONLY |
| `GapSeverity` | 0 | 1 | TEST_ONLY |
| `GraphMessage` | 0 | 1 | TEST_ONLY |
| `GraphSession` | 0 | 0 | UNUSED |
| `HybridRAGPipeline` | 0 | 2 | TEST_ONLY |
| `HybridSearchResult` | 0 | 1 | TEST_ONLY |
| `ImportanceConfig` | 0 | 1 | TEST_ONLY |
| `ImportanceManager` | 0 | 1 | TEST_ONLY |
| `ImportanceUpdate` | 0 | 1 | TEST_ONLY |
| `InsightExtractionPipeline` | 0 | 0 | UNUSED |
| `KnowledgeGap` | 0 | 0 | UNUSED |
| `LearningExtractor` | 0 | 1 | TEST_ONLY |
| `MemoryContext` | 0 | 1 | TEST_ONLY |
| `MergeStrategy` | 0 | 1 | TEST_ONLY |
| `MessageRole` | 0 | 1 | TEST_ONLY |
| `Neo4jIntrospector` | 0 | 0 | UNUSED |
| `PacketRefCount` | 0 | 1 | TEST_ONLY |
| `PostgresIntrospector` | 0 | 0 | UNUSED |
| `PredictiveCache` | 0 | 1 | TEST_ONLY |
| `PredictiveCacheConfig` | 0 | 1 | TEST_ONLY |
| `ReasoningPhase` | 0 | 0 | UNUSED |
| `ReferenceCountingService` | 0 | 2 | TEST_ONLY |
| `RetentionEngine` | 0 | 1 | TEST_ONLY |
| `RetentionResult` | 0 | 0 | UNUSED |
| `RetrievalPipeline` | 0 | 1 | TEST_ONLY |
| `SagaBuilder` | 0 | 1 | TEST_ONLY |
| `SagaContext` | 0 | 2 | TEST_ONLY |
| `SagaExecutor` | 0 | 2 | TEST_ONLY |
| `SagaPatterns` | 0 | 1 | TEST_ONLY |
| `SagaStatus` | 0 | 1 | TEST_ONLY |
| `SagaStep` | 0 | 0 | UNUSED |
| `SagaStepStatus` | 0 | 1 | TEST_ONLY |
| `SchemaIntrospector` | 0 | 0 | UNUSED |
| `SchemaVersion` | 0 | 0 | UNUSED |
| `SimilarityMethod` | 0 | 1 | TEST_ONLY |
| `StrategyMemoryConfig` | 0 | 0 | UNUSED |
| `StrategyMemoryService` | 0 | 1 | TEST_ONLY |
| `SubgraphEntry` | 0 | 1 | TEST_ONLY |
| `SubstrateAlignmentChecker` | 0 | 1 | TEST_ONLY |
| `SummaryConfig` | 0 | 1 | TEST_ONLY |
| `SummaryResult` | 0 | 1 | TEST_ONLY |
| `SummaryTier` | 0 | 1 | TEST_ONLY |
| `TaskOutcome` | 0 | 1 | TEST_ONLY |
| `ThinkingOutput` | 0 | 0 | UNUSED |
| `ToolEmbedding` | 0 | 1 | TEST_ONLY |
| `ToolMatch` | 0 | 1 | TEST_ONLY |
| `ToolRouter` | 0 | 1 | TEST_ONLY |
| `TopicExtractor` | 0 | 1 | TEST_ONLY |
| `VectorSearchConfig` | 0 | 1 | TEST_ONLY |
| `create_entity_enrichment_saga` | 0 | 1 | TEST_ONLY |
| `create_fetch_and_enrich_saga` | 0 | 1 | TEST_ONLY |
| `create_neo4j_strategy_memory` | 0 | 1 | TEST_ONLY |
| `create_timeline_correlation_saga` | 0 | 1 | TEST_ONLY |
| `detect_injection_markers` | 0 | 2 | TEST_ONLY |
| `detect_pii_types` | 0 | 3 | TEST_ONLY |
| `enforce_packet_governance` | 0 | 1 | TEST_ONLY |
| `execute_template` | 0 | 1 | TEST_ONLY |
| `find_tools` | 0 | 0 | UNUSED |
| `get_active_encoder` | 0 | 1 | TEST_ONLY |
| `get_checkpoint_metrics` | 0 | 0 | UNUSED |
| `get_graph_memory` | 0 | 1 | TEST_ONLY |
| `get_hybrid_rag_pipeline` | 0 | 1 | TEST_ONLY |
| `get_importance_manager` | 0 | 1 | TEST_ONLY |
| `get_ingestion_pipeline` | 0 | 0 | UNUSED |
| `get_insight_pipeline` | 0 | 0 | UNUSED |
| `get_saga_executor` | 0 | 0 | UNUSED |
| `get_saga_patterns` | 0 | 0 | UNUSED |
| `get_schema_introspector` | 0 | 0 | UNUSED |
| `get_template_library` | 0 | 1 | TEST_ONLY |
| `get_tool_router` | 0 | 1 | TEST_ONLY |
| `get_vector_config` | 0 | 0 | UNUSED |
| `has_injection_markers` | 0 | 1 | TEST_ONLY |
| `init_active_encoder` | 0 | 0 | UNUSED |
| `init_importance_manager` | 0 | 0 | UNUSED |
| `init_ingestion_pipeline` | 0 | 0 | UNUSED |
| `init_insight_pipeline` | 0 | 0 | UNUSED |
| `init_retrieval_pipeline` | 0 | 1 | TEST_ONLY |
| `init_tool_router` | 0 | 1 | TEST_ONLY |
| `normalize_payload` | 0 | 2 | TEST_ONLY |
| `normalize_text` | 0 | 3 | TEST_ONLY |
| `prepare_packet_for_ingest` | 0 | 3 | TEST_ONLY |
| `query_history` | 0 | 1 | TEST_ONLY |
| `redact_pii` | 0 | 2 | TEST_ONLY |
| `store_message` | 0 | 1 | TEST_ONLY |

**API-pattern symbols NOT in `__all__`:**
- `AgentPersistenceService`
- `CrossEncoderConfig`
- `EntityExtractionService`
- `GovernanceHookRegistry`
- `IdentityTierService`
- `MemorySubstrateService`
- `ReasoningReplayPipeline`
- `SemanticService`
- `TimelineService`
- `create_embedding_provider`
- `create_ranker_with_preset`
- `create_reranker_with_model`
- `create_substrate_service`
- `get_blob_store`
- `get_cache`
- `get_context_builder`
- `get_cross_encoder_reranker`
- `get_dlq`
- `get_dlq_async`
- `get_governance_patterns`
- `get_hook_registry`
- `get_identity_tier_service`
- `get_memory_substrate_service`
- `get_metrics`
- `get_multi_factor_ranker`
- `get_neo4j_client`
- `get_packets_with_metadata`
- `get_pool_stats_dict`
- `get_query_classifier`
- `get_repository`
- `get_service`
- `get_snapshot_manager`
- `get_strategy_retriever`
- `get_substrate_repository`
- `get_substrate_service`
- `get_template_cached`
