"""
L9 Memory Substrate Module
Version: 1.1.0

Hybrid memory + structured reasoning substrate for L9 and PlasticOS.
Uses Postgres + pgvector + LangGraph.

v1.1.0: Added insight extraction, knowledge facts, world model integration,
        housekeeping engine, ingestion pipeline, retrieval pipeline.
"""

# ============================================================================
__dora_meta__ = {
    "component_name": "  Init  ",
    "module_version": "1.1.0",
    "created_by": "Igor Beylin",
    "created_at": "2025-12-09T01:02:49Z",
    "updated_at": "2026-01-31T22:21:48Z",
    "layer": "learning",
    "domain": "memory_substrate",
    "module_name": "__init__",
    "type": "utility",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": ["Neo4j", "OpenAI API"],
        "memory_layers": ["semantic_memory", "working_memory"],
        "imported_by": [],
    },
}
# ============================================================================

from core.schemas import (
    PacketEnvelope,
    PacketEnvelopeIn,
    PacketWriteResult,
    SemanticHit,
    SemanticSearchRequest,
    SemanticSearchResult,
)

# Expose graph_client for lazy import compatibility
# (required for pytest to resolve `from memory.graph_client import ...`)
from memory import graph_client as graph_client

# Active Memory Encoding (GMP-80-A7)
from memory.active_encoder import (
    ActiveMemoryEncoder,
    EncodingResult,
    ExtractedLearning,
    LearningExtractor,
    TaskOutcome,
    get_active_encoder,
    init_active_encoder,
)

# Audit Utilities (GMP-58: Security hardening, v2.0: PII + normalization)
from memory.audit_utils import (  # PII detection (v2.0); Normalization (v2.0)
    AuditReport,
    detect_injection_markers,
    detect_pii_types,
    has_injection_markers,
    normalize_payload,
    normalize_text,
    prepare_packet_for_ingest,
    redact_pii,
)

# Checkpoint Metrics (GMP-PERSIST: Prometheus observability)
from memory.checkpoint_metrics import (
    PROMETHEUS_AVAILABLE as CHECKPOINT_PROMETHEUS_AVAILABLE,
)
from memory.checkpoint_metrics import CheckpointMetrics
from memory.checkpoint_metrics import get_metrics as get_checkpoint_metrics

# Checkpoint Validator (GMP-PERSIST: Integrity validation)
from memory.checkpoint_validator import CheckpointValidator, SchemaVersion

# Memory Pipeline v1 (Phase 1: DeepMind-style pipeline router)
from memory.chunk_view import Chunk, ChunkConfig, ChunkView

# Consolidation Pipeline (GMP-85 + Stage 2)
from memory.consolidation import ConsolidationPipeline, ConsolidationReport

# Cypher Templates (GMP-55: Parameterized queries)
from memory.cypher_templates import (
    CypherTemplate,
    CypherTemplateCategory,
    CypherTemplateLibrary,
    execute_template,
    get_template_library,
)

# Deduplication Engine (GMP-125: Wired into ConsolidationPipeline)
from memory.deduplication import (
    DeduplicationEngine,
    DuplicateGroup,
    MergeStrategy,
    SimilarityMethod,
)
from memory.deduplication import (
    DeduplicationReport as DeduplicationEngineReport,
)

# DEPRECATED: EnrichmentDAG superseded by SubstrateDAG (substrate_dag.py)
# Kept for backward compat with substrate_service.py during transition.
from memory.enrichment_dag import (
    EnrichmentConfig,  # deprecated 2.0.0
    EnrichmentDAG,  # deprecated 2.0.0
    EnrichmentResult,  # deprecated 2.0.0
    EnrichmentStatus,  # deprecated 2.0.0
    EnrichmentTier,  # deprecated 2.0.0
)
from memory.gap_detector import GapDetector

# Governance Gate (GMP-68)
# Governance Gate (single enforcement layer)
from memory.governance_gate import (
    MemoryGovernanceContext,
    build_governance_context,
    build_scope_project_filter,
    enforce_packet_governance,
    ensure_governance_context,
    governance_context,
    require_governance_context,
)

# Conversational Graph Memory (GMP-58)
from memory.graph_memory import (
    ConversationContext,
    ConversationGraphMemory,
    GraphMessage,
    GraphSession,
    MessageRole,
    TopicExtractor,
    get_graph_memory,
    query_history,
    store_message,
)

# Hierarchical Summarizer (Stage 2: SUPER-PROMPT)
from memory.hierarchical_summarizer import (
    HierarchicalSummarizer,
    SummaryConfig,
    SummaryResult,
    SummaryTier,
)

# v1.1.0+ Pipelines
from memory.housekeeping import (
    HousekeepingEngine,
    get_housekeeping_engine,
    init_housekeeping_engine,
)

# Hybrid RAG (GMP-55: Vector-Graph Bridge)
from memory.hybrid_rag import (
    EnrichmentStrategy,
    HybridRAGPipeline,
    HybridSearchResult,
    get_hybrid_rag_pipeline,
    hybrid_search,
)

# Importance Manager (GMP-80-A7)
from memory.importance_manager import (
    ImportanceConfig,
    ImportanceManager,
    ImportanceUpdate,
    get_importance_manager,
    init_importance_manager,
)
from memory.importance_recipe import (
    ImportanceInputs,
    compute_importance,
)
from memory.importance_recipe import ImportanceUpdate as ImportanceRecipeUpdate

# Task Completion Hook (GMP-80-A7) + deprecated IngestionPipeline re-exports
# DEPRECATED: IngestionPipeline, get_ingestion_pipeline, init_ingestion_pipeline
# Use ingest_packet() instead. Kept for backward compat with test fixtures.
from memory.ingestion import (
    IngestionPipeline,  # deprecated 2.0.0
    get_ingestion_pipeline,  # deprecated 2.0.0
    init_ingestion_pipeline,  # deprecated 2.0.0
    on_task_completion,
)

# DEPRECATED: InsightExtractionPipeline superseded by extract_insights_node
# in substrate_dag.py + EntityExtractionService in entity_extraction.py
from memory.insight_extraction import (
    InsightExtractionPipeline,  # deprecated 2.0.0
    get_insight_pipeline,  # deprecated 2.0.0
    init_insight_pipeline,  # deprecated 2.0.0
)
from memory.llm_memory_ops import (
    ConsolidateResult,
    DistillResult,
    LLMMemoryOps,
    SummarizeResult,
)
from memory.neo4j_strategy_memory import (
    Neo4jStrategyMemoryService,
    StrategyMemoryConfig,
    create_neo4j_strategy_memory,
)

# Neural Decay Scheduler (Stage 2: SUPER-PROMPT)
from memory.neural_decay_scheduler import DecayConfig, DecayResult, NeuralDecayScheduler
from memory.pipeline_router import (
    CallerContext,
    ContextSection,
    LLMConfig,
    MemoryTier,
    PipelineRouter,
    RouterResult,
    TierRetrievalConfig,
)
from memory.predictive_cache import PredictiveCache
from memory.procedural_synthesis import (
    HeuristicCandidate,
    ProceduralSynthesizer,
    SynthesisReport,
)
from memory.query_rewriter import QueryRewriter, RewriteResult
from memory.ranking_extensions import (
    ExtendedRankingItem,
    ExtendedWeights,
    rank_extended,
)

# Retention Engine (GMP-74: Checkpoint lifecycle management)
from memory.retention_engine import RetentionEngine, RetentionPolicy, RetentionResult

# Reference Counting Service (Phase 0 Hardening)
from memory.retention_refcount import PacketRefCount, ReferenceCountingService
from memory.retrieval import (
    RetrievalPipeline,
    get_retrieval_pipeline,
    init_retrieval_pipeline,
)
from memory.retrieval_multiquery import (
    MultiQueryResult,
    ProvenancedHit,
    retrieve_multiquery,
)

# Cross-DB Saga Pattern (GMP-56)
from memory.saga import (
    DatabaseType,
    Saga,
    SagaBuilder,
    SagaContext,
    SagaExecutor,
    SagaResult,
    SagaStatus,
    SagaStep,
    SagaStepStatus,
    get_saga_executor,
)
from memory.saga_patterns import (
    SagaPatterns,
    create_entity_enrichment_saga,
    create_fetch_and_enrich_saga,
    create_timeline_correlation_saga,
    fetch_and_enrich,
    get_saga_patterns,
)

# Schema Introspection (GMP-55: Dynamic schema discovery)
from memory.schema_introspection import (
    Neo4jIntrospector,
    PostgresIntrospector,
    SchemaIntrospector,
    get_schema_introspector,
)

# Strategy Memory (Phase 0-1: GMP-102)
from memory.strategymemory import (
    IStrategyMemoryService,
    StrategyCandidate,
    StrategyFeedback,
    StrategyMemoryService,
    StrategyRetrievalRequest,
)

# Cross-Substrate Alignment (GMP-78)
from memory.substrate_alignment import AlignmentReport, SubstrateAlignmentChecker
from memory.substrate_models import (
    ExtractedInsight,
    KnowledgeFact,
    KnowledgeFactRow,
    StructuredReasoningBlock,
    SubstrateState,
)

# Semantic Tool Router (GMP-57)
from memory.tool_router import (
    ToolEmbedding,
    ToolMatch,
    ToolRouter,
    ToolSearchResult,
    find_tools,
    get_tool_router,
    init_tool_router,
)
from memory.vector_search_config import VectorSearchConfig, get_vector_config

# Stage 5: Predictive Memory Warming (GMP-STAGE5)
from memory.warming_models import (
    ActionProposal,
    AttentionConfig,
    CacheMetrics,
    GapSeverity,
    KnowledgeGap,
    MemoryContext,
    PredictiveCacheConfig,
    ReasoningPhase,
    SubgraphEntry,
    ThinkingOutput,
)
from memory.warming_service import MemoryWarmingService, create_warming_service

# NOTE: Avoid eager imports here to prevent circular dependencies.
# MemoryServiceAdapter requires core.protocols which creates circular import.
# Import directly: from memory.service_adapter import MemoryServiceAdapter
# These modules can be imported directly when needed:
#   from memory.substrate_repository import SubstrateRepository, ...
#   from memory.substrate_dag import SubstrateDAG, ...
#   from memory.substrate_service import MemorySubstrateService, ...
#   from memory.substrate_semantic import SemanticService, ...
#   from memory.graph_client import get_neo4j_client, ...
#   from memory.identity_tier import IdentityTierService, ...
#   from memory.context_builder import HierarchicalContextBuilder, ...


# from memory.substrate_repository import (
#     SubstrateRepository,
#     get_repository,
#     init_repository,
#     close_repository,
# )

# from memory.substrate_semantic import (
#     EmbeddingProvider,
#     OpenAIEmbeddingProvider,
#     StubEmbeddingProvider,
#     SemanticService,
#     create_embedding_provider,
#     embed_text,
# )

# from memory.substrate_dag import (
#     SubstrateDAG,
#     SubstrateGraphState,
#     run_substrate_flow,
#     build_substrate_graph,
# )

# from memory.substrate_service import (
#     MemorySubstrateService,
#     create_substrate_service,
#     get_service,
#     init_service,
#     close_service,
# )


__all__ = [
    "CHECKPOINT_PROMETHEUS_AVAILABLE",
    "ActionProposal",
    "ActiveMemoryEncoder",
    "AlignmentReport",
    "AttentionConfig",
    "AuditReport",
    "CacheMetrics",
    "CallerContext",
    "CheckpointMetrics",
    "Chunk",
    "ChunkConfig",
    "ChunkView",
    "ConsolidateResult",
    "ConsolidationPipeline",
    "ConsolidationReport",
    "ConversationContext",
    "ConversationGraphMemory",
    "CypherTemplate",
    "CypherTemplateCategory",
    "CypherTemplateLibrary",
    "DatabaseType",
    "DecayConfig",
    "DecayResult",
    "DeduplicationEngine",
    "DeduplicationEngineReport",
    "DistillResult",
    "DuplicateGroup",
    "EncodingResult",
    "EnrichmentConfig",
    "EnrichmentDAG",
    "EnrichmentResult",
    "EnrichmentStatus",
    "EnrichmentStrategy",
    "EnrichmentTier",
    "ExtendedRankingItem",
    "ExtendedWeights",
    "ExtractedInsight",
    "ExtractedLearning",
    "GapDetector",
    "GapSeverity",
    "GraphMessage",
    "GraphSession",
    "HeuristicCandidate",
    "HierarchicalSummarizer",
    "HousekeepingEngine",
    "HybridRAGPipeline",
    "HybridSearchResult",
    "IStrategyMemoryService",
    "ImportanceConfig",
    "ImportanceInputs",
    "ImportanceManager",
    "ImportanceRecipeUpdate",
    "ImportanceUpdate",
    "IngestionPipeline",
    "KnowledgeFact",
    "KnowledgeFactRow",
    "LLMConfig",
    "LLMMemoryOps",
    "LearningExtractor",
    "MemoryContext",
    "MemoryGovernanceContext",
    "MemoryTier",
    "MemoryWarmingService",
    "MergeStrategy",
    "MessageRole",
    "MultiQueryResult",
    "Neo4jIntrospector",
    "Neo4jStrategyMemoryService",
    "NeuralDecayScheduler",
    "PacketEnvelope",
    "PacketEnvelopeIn",
    "PacketRefCount",
    "PacketWriteResult",
    "PipelineRouter",
    "PostgresIntrospector",
    "PredictiveCache",
    "PredictiveCacheConfig",
    "ProceduralSynthesizer",
    "ProvenancedHit",
    "QueryRewriter",
    "ReasoningPhase",
    "ReferenceCountingService",
    "RetentionEngine",
    "RetentionPolicy",
    "RetentionResult",
    "RetrievalPipeline",
    "RewriteResult",
    "RouterResult",
    "Saga",
    "SagaBuilder",
    "SagaContext",
    "SagaExecutor",
    "SagaPatterns",
    "SagaResult",
    "SagaStatus",
    "SagaStep",
    "SagaStepStatus",
    "SchemaIntrospector",
    "SchemaVersion",
    "SemanticHit",
    "SemanticSearchRequest",
    "SemanticSearchResult",
    "SimilarityMethod",
    "StrategyCandidate",
    "StrategyFeedback",
    "StrategyMemoryConfig",
    "StrategyMemoryService",
    "StrategyRetrievalRequest",
    "StructuredReasoningBlock",
    "SubgraphEntry",
    "SubstrateAlignmentChecker",
    "SubstrateState",
    "SummarizeResult",
    "SummaryConfig",
    "SummaryResult",
    "SummaryTier",
    "SynthesisReport",
    "TaskOutcome",
    "ThinkingOutput",
    "TierRetrievalConfig",
    "ToolEmbedding",
    "ToolMatch",
    "ToolRouter",
    "ToolSearchResult",
    "TopicExtractor",
    "VectorSearchConfig",
    "build_governance_context",
    "build_scope_project_filter",
    "compute_importance",
    "create_entity_enrichment_saga",
    "create_fetch_and_enrich_saga",
    "create_neo4j_strategy_memory",
    "create_timeline_correlation_saga",
    "create_warming_service",
    "detect_injection_markers",
    "detect_pii_types",
    "enforce_packet_governance",
    "ensure_governance_context",
    "execute_template",
    "fetch_and_enrich",
    "find_tools",
    "get_active_encoder",
    "get_checkpoint_metrics",
    "get_graph_memory",
    "get_housekeeping_engine",
    "get_hybrid_rag_pipeline",
    "get_importance_manager",
    "get_ingestion_pipeline",
    "get_retrieval_pipeline",
    "get_schema_introspector",
    "get_template_library",
    "get_tool_router",
    "governance_context",
    "has_injection_markers",
    "hybrid_search",
    "init_active_encoder",
    "init_housekeeping_engine",
    "init_importance_manager",
    "init_ingestion_pipeline",
    "init_retrieval_pipeline",
    "init_tool_router",
    "normalize_payload",
    "normalize_text",
    "on_task_completion",
    "prepare_packet_for_ingest",
    "query_history",
    "rank_extended",
    "redact_pii",
    "require_governance_context",
    "retrieve_multiquery",
    "store_message",
]

__version__ = "1.1.0"
# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "MEM-LEAR-028",
    "governance_level": "critical",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [
        "core.schemas",
        "memory.active_encoder",
        "memory.audit_utils",
        "memory.checkpoint_metrics",
        "memory.checkpoint_validator",
    ],
    "tags": [
        "caching",
        "event-driven",
        "learning",
        "memory-substrate",
        "messaging",
        "metrics",
        "scheduling",
        "testing",
        "utility",
    ],
    "keywords": ["memory", "module", "pipeline", "substrate"],
    "business_value": "Utility module for   init  ",
    "last_modified": "2026-01-31T22:21:48Z",
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
