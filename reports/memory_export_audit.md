# Memory Module Export Audit

**Date:** 2026-02-14  
**Scope:** Every symbol imported in `memory/__init__.py` vs every symbol in `__all__`.  
**Goal:** Prove whether "every other major memory capability is re-exported from memory."

---

## 1. Re-export check: Imported in `__init__.py` but NOT in `__all__`

These are **memory capabilities that are imported** (so they are part of the memory package surface) **but not re-exported** in `__all__`. Users who do `from memory import X` will not see them; they must use `from memory.deduplication import ...`.

| Symbol | Source module | In __all__? | Consumer (wired?) |
|--------|---------------|-------------|-------------------|
| **DeduplicationEngine** | memory.deduplication | ✅ Yes (added 2026-02-14) | ✅ consolidation.py, tests/unit/test_deduplication.py |
| **DuplicateGroup** | memory.deduplication | ✅ Yes (added 2026-02-14) | ✅ deduplication.py, consolidation.py, test_deduplication.py |
| **MergeStrategy** | memory.deduplication | ✅ Yes (added 2026-02-14) | ✅ consolidation.py, deduplication.py, test_deduplication.py |
| **SimilarityMethod** | memory.deduplication | ✅ Yes (added 2026-02-14) | ✅ consolidation.py, deduplication.py, test_deduplication.py |
| **DeduplicationEngineReport** | memory.deduplication (alias) | ✅ Yes (added 2026-02-14) | ✅ deduplication.py (return type) |

**Conclusion:** One major capability — **Deduplication** (GMP-125, wired into ConsolidationPipeline) — had **5 symbols imported but not in `__all__`**. So the claim "every other major memory capability is re-exported" was **false** before adding VectorSearchConfig and before adding the deduplication symbols. **Fixed 2026-02-14:** All five symbols were added to `__all__`.

---

## 2. Re-export check: All other memory submodules

For every other `from memory.<submodule> import ...` in `__init__.py`, the imported names were cross-checked against `__all__`. Result:

| Submodule | Imported names | All in __all__? |
|-----------|----------------|-----------------|
| core.schemas | PacketEnvelope, PacketEnvelopeIn, PacketWriteResult, SemanticHit, SemanticSearchRequest, SemanticSearchResult | ✅ Yes |
| memory.active_encoder | ActiveMemoryEncoder, EncodingResult, ExtractedLearning, LearningExtractor, TaskOutcome, get_active_encoder, init_active_encoder | ✅ Yes |
| memory.audit_utils | AuditReport, detect_*, has_*, normalize_*, prepare_*, redact_* | ✅ Yes |
| memory.checkpoint_metrics | CHECKPOINT_PROMETHEUS_AVAILABLE, CheckpointMetrics, get_checkpoint_metrics | ✅ Yes |
| memory.checkpoint_validator | CheckpointValidator, SchemaVersion | ✅ Yes |
| memory.consolidation | ConsolidationPipeline, ConsolidationReport | ✅ Yes |
| memory.cypher_templates | CypherTemplate, CypherTemplateCategory, CypherTemplateLibrary, execute_template, get_template_library | ✅ Yes |
| memory.deduplication | DeduplicationEngine, DuplicateGroup, MergeStrategy, SimilarityMethod, DeduplicationEngineReport | ✅ Yes (added 2026-02-14) |
| memory.enrichment_dag | EnrichmentConfig, EnrichmentDAG, EnrichmentResult, EnrichmentStatus, EnrichmentTier | ✅ Yes |
| memory.gap_detector | GapDetector | ✅ Yes |
| memory.governance_gate | MemoryGovernanceContext, build_*, enforce_*, ensure_*, governance_context, require_* | ✅ Yes |
| memory.graph_memory | ConversationContext, ConversationGraphMemory, GraphMessage, GraphSession, MessageRole, TopicExtractor, get_graph_memory, query_history, store_message | ✅ Yes |
| memory.hierarchical_summarizer | HierarchicalSummarizer, SummaryConfig, SummaryResult, SummaryTier | ✅ Yes |
| memory.housekeeping | HousekeepingEngine, get_housekeeping_engine, init_housekeeping_engine | ✅ Yes |
| memory.hybrid_rag | EnrichmentStrategy, HybridRAGPipeline, HybridSearchResult, get_hybrid_rag_pipeline, hybrid_search | ✅ Yes |
| memory.importance_manager | ImportanceConfig, ImportanceManager, ImportanceUpdate, get_*, init_* | ✅ Yes |
| memory.ingestion | IngestionPipeline, get_ingestion_pipeline, init_ingestion_pipeline, on_task_completion | ✅ Yes |
| memory.insight_extraction | InsightExtractionPipeline, get_insight_pipeline, init_insight_pipeline | ✅ Yes |
| memory.neo4j_strategy_memory | Neo4jStrategyMemoryService, StrategyMemoryConfig, create_neo4j_strategy_memory | ✅ Yes |
| memory.neural_decay_scheduler | DecayConfig, DecayResult, NeuralDecayScheduler | ✅ Yes |
| memory.predictive_cache | PredictiveCache | ✅ Yes |
| memory.retention_engine | RetentionEngine, RetentionPolicy, RetentionResult | ✅ Yes |
| memory.retention_refcount | PacketRefCount, ReferenceCountingService | ✅ Yes |
| memory.retrieval | RetrievalPipeline, get_retrieval_pipeline, init_retrieval_pipeline | ✅ Yes |
| memory.vector_search_config | VectorSearchConfig, get_vector_config | ✅ Yes (after 2026-02-14 fix) |
| memory.saga | DatabaseType, Saga, SagaBuilder, SagaContext, SagaExecutor, SagaResult, SagaStatus, SagaStep, SagaStepStatus, get_saga_executor | ✅ Yes |
| memory.saga_patterns | SagaPatterns, create_entity_enrichment_saga, create_fetch_and_enrich_saga, create_timeline_correlation_saga, fetch_and_enrich, get_saga_patterns | ✅ Yes |
| memory.schema_introspection | Neo4jIntrospector, PostgresIntrospector, SchemaIntrospector, get_schema_introspector | ✅ Yes |
| memory.strategymemory | IStrategyMemoryService, StrategyCandidate, StrategyFeedback, StrategyMemoryService, StrategyRetrievalRequest | ✅ Yes |
| memory.substrate_alignment | AlignmentReport, SubstrateAlignmentChecker | ✅ Yes |
| memory.substrate_models | ExtractedInsight, KnowledgeFact, KnowledgeFactRow, StructuredReasoningBlock, SubstrateState | ✅ Yes |
| memory.tool_router | ToolEmbedding, ToolMatch, ToolRouter, ToolSearchResult, find_tools, get_tool_router, init_tool_router | ✅ Yes |
| memory.warming_models | ActionProposal, AttentionConfig, CacheMetrics, GapSeverity, KnowledgeGap, MemoryContext, PredictiveCacheConfig, ReasoningPhase, SubgraphEntry, ThinkingOutput | ✅ Yes |
| memory.warming_service | MemoryWarmingService, create_warming_service | ✅ Yes |

---

## 3. Intentionally not re-exported (documented in __init__.py)

These are **not** imported in `memory/__init__.py` to avoid circular dependencies; the comment says "Import directly when needed":

- memory.service_adapter: MemoryServiceAdapter  
- memory.substrate_repository: SubstrateRepository, get_repository, init_repository, close_repository  
- memory.substrate_dag: SubstrateDAG, SubstrateGraphState, run_substrate_flow, build_substrate_graph  
- memory.substrate_service: MemorySubstrateService, create_substrate_service, get_service, init_service, close_service  
- memory.substrate_semantic: EmbeddingProvider, OpenAIEmbeddingProvider, StubEmbeddingProvider, SemanticService, create_embedding_provider, embed_text  
- memory.graph_client: get_neo4j_client  
- memory.identity_tier: IdentityTierService  
- memory.context_builder: HierarchicalContextBuilder  

So these are **not** "memory capabilities re-exported from memory" by design; they are **not** part of this inconsistency.

---

## 4. Proof summary

| Claim | Result |
|-------|--------|
| "Every other major memory capability is re-exported from memory" | **True after fix.** Deduplication (5 symbols) was the only gap; they were added to `__all__` on 2026-02-14. |
| "VectorSearchConfig was the only one not re-exported" | **False.** Deduplication was also not re-exported; both are now fixed. |
| All other submodules that are eagerly imported | **True.** Every such submodule’s imported names now appear in `__all__`. |

**Done (2026-02-14):** Added `DeduplicationEngine`, `DeduplicationEngineReport`, `DuplicateGroup`, `MergeStrategy`, and `SimilarityMethod` to `memory/__all__`.
