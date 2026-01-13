"""
L9 Memory Substrate Module
Version: 1.1.0

Hybrid memory + structured reasoning substrate for L9 and PlasticOS.
Uses Postgres + pgvector + LangGraph.

v1.1.0: Added insight extraction, knowledge facts, world model integration,
        housekeeping engine, ingestion pipeline, retrieval pipeline.
"""

from memory.substrate_models import (
    PacketEnvelope,
    PacketEnvelopeIn,
    PacketWriteResult,
    StructuredReasoningBlock,
    SemanticSearchRequest,
    SemanticSearchResult,
    SemanticHit,
    SubstrateState,
    # v1.1.0+ additions
    KnowledgeFact,
    KnowledgeFactRow,
    ExtractedInsight,
)

# NOTE: Avoid eager imports here to prevent circular dependencies.
# These modules can be imported directly when needed:
#   from memory.substrate_repository import SubstrateRepository, ...
#   from memory.substrate_graph import SubstrateDAG, ...
#   from memory.substrate_service import MemorySubstrateService, ...
#   from memory.substrate_semantic import SemanticService, ...

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

# from memory.substrate_graph import (
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

# v1.1.0+ Pipelines
from memory.housekeeping import (
    HousekeepingEngine,
    get_housekeeping_engine,
    init_housekeeping_engine,
)

from memory.ingestion import (
    IngestionPipeline,
    get_ingestion_pipeline,
    init_ingestion_pipeline,
)

from memory.retrieval import (
    RetrievalPipeline,
    get_retrieval_pipeline,
    init_retrieval_pipeline,
)

from memory.insight_extraction import (
    InsightExtractionPipeline,
    get_insight_pipeline,
    init_insight_pipeline,
)

# Strategy Memory (Phase 0)
from memory.strategymemory import (
    IStrategyMemoryService,
    StrategyMemoryService,
    StrategyCandidate,
    StrategyRetrievalRequest,
    StrategyFeedback,
)

# Cypher Templates (GMP-55: Parameterized queries)
from memory.cypher_templates import (
    CypherTemplate,
    CypherTemplateCategory,
    CypherTemplateLibrary,
    get_template_library,
    execute_template,
)

# Schema Introspection (GMP-55: Dynamic schema discovery)
from memory.schema_introspection import (
    SchemaIntrospector,
    PostgresIntrospector,
    Neo4jIntrospector,
    get_schema_introspector,
)

# Hybrid RAG (GMP-55: Vector-Graph Bridge)
from memory.hybrid_rag import (
    EnrichmentStrategy,
    HybridRAGPipeline,
    HybridSearchResult,
    get_hybrid_rag_pipeline,
    hybrid_search,
)

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
    # Strategy Memory
    "IStrategyMemoryService",
    "StrategyMemoryService",
    "StrategyCandidate",
    "StrategyRetrievalRequest",
    "StrategyFeedback",
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
    # NOTE: These are available via direct import to avoid circular deps:
    # from memory.substrate_repository import SubstrateRepository, ...
    # from memory.substrate_graph import SubstrateDAG, ...
    # from memory.substrate_service import MemorySubstrateService, ...
    # from memory.substrate_semantic import SemanticService, ...
]

__version__ = "1.1.0"
