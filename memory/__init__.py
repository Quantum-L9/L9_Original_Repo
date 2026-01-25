"""
L9 Memory Substrate Module
Version: 1.1.0

Hybrid memory + structured reasoning substrate for L9 and PlasticOS.
Uses Postgres + pgvector + LangGraph.

v1.1.0: Added insight extraction, knowledge facts, world model integration,
        housekeeping engine, ingestion pipeline, retrieval pipeline.
"""

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

# Consolidation Pipeline (GMP-85 + Stage 2)
from memory.consolidation import ConsolidationPipeline, ConsolidationReport

# Deduplication Engine (GMP-125: Wired into ConsolidationPipeline)
from memory.deduplication import (
    DeduplicationEngine,
    DeduplicationReport as DeduplicationEngineReport,
    DuplicateGroup,
    MergeStrategy,
    SimilarityMethod,
)

# Cypher Templates (GMP-55: Parameterized queries)
from memory.cypher_templates import (
    CypherTemplate,
    CypherTemplateCategory,
    CypherTemplateLibrary,
    execute_template,
    get_template_library,
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

# Task Completion Hook (GMP-80-A7)
from memory.ingestion import (
    IngestionPipeline,
    get_ingestion_pipeline,
    init_ingestion_pipeline,
    on_task_completion,
)
from memory.insight_extraction import (
    InsightExtractionPipeline,
    get_insight_pipeline,
    init_insight_pipeline,
)
from memory.neo4j_strategy_memory import (
    Neo4jStrategyMemoryService,
    StrategyMemoryConfig,
    create_neo4j_strategy_memory,
)

# Neural Decay Scheduler (Stage 2: SUPER-PROMPT)
from memory.neural_decay_scheduler import DecayConfig, DecayResult, NeuralDecayScheduler
from memory.predictive_cache import PredictiveCache

# Retention Engine (GMP-74: Checkpoint lifecycle management)
from memory.retention_engine import RetentionEngine, RetentionPolicy, RetentionResult
from memory.retrieval import (
    RetrievalPipeline,
    get_retrieval_pipeline,
    init_retrieval_pipeline,
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
    # Models (always available)
    "PacketEnvelope",
    "PacketEnvelopeIn",
    "PacketWriteResult",
    "StructuredReasoningBlock",
    "SemanticSearchRequest",
    "SemanticSearchResult",
    "SemanticHit",
    "SubstrateState",
    # v1.1.0+ Models
    "KnowledgeFact",
    "KnowledgeFactRow",
    "ExtractedInsight",
    # v1.1.0+ Pipelines
    "HousekeepingEngine",
    "get_housekeeping_engine",
    "init_housekeeping_engine",
    "IngestionPipeline",
    "get_ingestion_pipeline",
    "init_ingestion_pipeline",
    "RetrievalPipeline",
    "get_retrieval_pipeline",
    "init_retrieval_pipeline",
    "InsightExtractionPipeline",
    "get_insight_pipeline",
    "init_insight_pipeline",
    # Audit Utilities (GMP-58, v2.0)
    "AuditReport",
    "has_injection_markers",
    "detect_injection_markers",
    "prepare_packet_for_ingest",
    "detect_pii_types",
    "redact_pii",
    "normalize_text",
    "normalize_payload",
    # Strategy Memory (Phase 0-1: GMP-102)
    "IStrategyMemoryService",
    "StrategyMemoryService",
    "StrategyCandidate",
    "StrategyRetrievalRequest",
    "StrategyFeedback",
    "Neo4jStrategyMemoryService",
    "StrategyMemoryConfig",
    "create_neo4j_strategy_memory",
    # Cypher Templates (GMP-55)
    "CypherTemplate",
    "CypherTemplateCategory",
    "CypherTemplateLibrary",
    "get_template_library",
    "execute_template",
    # Schema Introspection (GMP-55)
    "SchemaIntrospector",
    "PostgresIntrospector",
    "Neo4jIntrospector",
    "get_schema_introspector",
    # Hybrid RAG (GMP-55)
    "EnrichmentStrategy",
    "HybridRAGPipeline",
    "HybridSearchResult",
    "get_hybrid_rag_pipeline",
    "hybrid_search",
    # Cross-DB Saga Pattern (GMP-56)
    "Saga",
    "SagaBuilder",
    "SagaContext",
    "SagaExecutor",
    "SagaResult",
    "SagaStep",
    "SagaStepStatus",
    "SagaStatus",
    "DatabaseType",
    "get_saga_executor",
    "SagaPatterns",
    "create_fetch_and_enrich_saga",
    "create_entity_enrichment_saga",
    "create_timeline_correlation_saga",
    "get_saga_patterns",
    "fetch_and_enrich",
    # Semantic Tool Router (GMP-57)
    "ToolRouter",
    "ToolEmbedding",
    "ToolMatch",
    "ToolSearchResult",
    "get_tool_router",
    "init_tool_router",
    "find_tools",
    # Conversational Graph Memory (GMP-58)
    "ConversationGraphMemory",
    "GraphMessage",
    "GraphSession",
    "ConversationContext",
    "MessageRole",
    "TopicExtractor",
    "get_graph_memory",
    "store_message",
    "query_history",
    # Retention Engine (GMP-74)
    "RetentionEngine",
    "RetentionPolicy",
    "RetentionResult",
    # Cross-Substrate Alignment (GMP-78)
    "AlignmentReport",
    "SubstrateAlignmentChecker",
    # Checkpoint Validator + Metrics (GMP-PERSIST)
    "CheckpointValidator",
    "SchemaVersion",
    "CheckpointMetrics",
    "get_checkpoint_metrics",
    "CHECKPOINT_PROMETHEUS_AVAILABLE",
    # Governance Gate (GMP-68)
    "MemoryGovernanceContext",
    "build_governance_context",
    "governance_context",
    "require_governance_context",
    "ensure_governance_context",
    "enforce_packet_governance",
    "build_scope_project_filter",
    # Consolidation Pipeline (GMP-85 + Stage 2)
    "ConsolidationPipeline",
    "ConsolidationReport",
    # Hierarchical Summarizer (Stage 2)
    "HierarchicalSummarizer",
    "SummaryTier",
    "SummaryConfig",
    "SummaryResult",
    # Neural Decay Scheduler (Stage 2)
    "NeuralDecayScheduler",
    "DecayConfig",
    "DecayResult",
    # Active Memory Encoding (GMP-80-A7)
    "ActiveMemoryEncoder",
    "TaskOutcome",
    "EncodingResult",
    "LearningExtractor",
    "ExtractedLearning",
    "get_active_encoder",
    "init_active_encoder",
    # Importance Manager (GMP-80-A7)
    "ImportanceManager",
    "ImportanceConfig",
    "ImportanceUpdate",
    "get_importance_manager",
    "init_importance_manager",
    # Task Completion Hook (GMP-80-A7)
    "on_task_completion",
    # Stage 5: Predictive Memory Warming (GMP-STAGE5)
    "GapSeverity",
    "KnowledgeGap",
    "AttentionConfig",
    "SubgraphEntry",
    "CacheMetrics",
    "ReasoningPhase",
    "ActionProposal",
    "ThinkingOutput",
    "MemoryContext",
    "PredictiveCacheConfig",
    "GapDetector",
    "PredictiveCache",
    "MemoryWarmingService",
    "create_warming_service",
    # NOTE: These are available via direct import to avoid circular deps:
    # from memory.service_adapter import MemoryServiceAdapter
    # from memory.substrate_repository import SubstrateRepository, ...
    # from memory.substrate_dag import SubstrateDAG, ...
    # from memory.substrate_service import MemorySubstrateService, ...
    # from memory.substrate_semantic import SemanticService, ...
]

__version__ = "1.1.0"
