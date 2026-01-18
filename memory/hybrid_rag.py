"""
L9 Memory - Hybrid RAG Pipeline (Vector-Graph Bridge)
=====================================================

The "killer feature" — combines vector search (pgvector) with
graph enrichment (Neo4j) for comprehensive retrieval.

Workflow:
1. Vector search finds semantically similar documents
2. Graph bridge extracts entity IDs from results
3. Neo4j enriches with related entities and relationships
4. Combined results provide both similarity AND context

This prevents the "losing the big picture" problem where agents
find relevant docs but miss important relationships.

Version: 1.0.0
"""

from __future__ import annotations

# ============================================================================
__dora_meta__ = {
    "component_name": "Hybrid RAG Pipeline (Vector-Graph Bridge)",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2026-01-12T21:19:05Z",
    "updated_at": "2026-01-17T23:47:56Z",
    "layer": "learning",
    "domain": "data_models",
    "module_name": "hybrid_rag",
    "type": "dataclass",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": ["Neo4j", "OpenAI API"],
        "memory_layers": ["semantic_memory", "working_memory"],
        "imported_by": ["memory.__init__", "tests.memory.test_hybrid_rag"],
    },
}
# ============================================================================

import structlog
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional
from uuid import UUID
from core.decorators import must_stay_async

logger = structlog.get_logger(__name__)


# =============================================================================
# Models
# =============================================================================


class EnrichmentStrategy(str, Enum):
    """Strategies for graph enrichment."""

    NONE = "none"  # No enrichment, vector results only
    DIRECT = "direct"  # Direct relationships only (1-hop)
    EXTENDED = "extended"  # Extended neighborhood (2-hop)
    CAUSAL = "causal"  # Follow causal chains (TRIGGERED relationships)
    FULL = "full"  # All enrichment strategies combined


@dataclass
class VectorHit:
    """A single vector search result."""

    packet_id: UUID
    content: str
    similarity: float
    kind: Optional[str] = None
    source_id: Optional[str] = None
    thread_id: Optional[str] = None
    metadata: dict[str, Any] = field(default_factory=dict)

    # Extracted entities (populated by entity extractor)
    extracted_entities: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class GraphEnrichment:
    """Graph enrichment for a vector hit."""

    source_packet_id: UUID

    # Related entities from Neo4j
    related_entities: list[dict[str, Any]] = field(default_factory=list)

    # Relationship paths
    relationship_paths: list[dict[str, Any]] = field(default_factory=list)

    # Causal chain (for events)
    causal_chain: list[dict[str, Any]] = field(default_factory=list)

    # Summary
    entity_count: int = 0
    relationship_count: int = 0


@dataclass
class HybridResult:
    """Combined result from vector search + graph enrichment."""

    # Original vector hit
    vector_hit: VectorHit

    # Graph enrichment
    enrichment: Optional[GraphEnrichment] = None

    # Combined relevance score (vector similarity + graph centrality)
    combined_score: float = 0.0

    # Ranking factors
    ranking_factors: dict[str, float] = field(default_factory=dict)


@dataclass
class HybridSearchResult:
    """Complete result set from hybrid RAG."""

    query: str
    results: list[HybridResult]

    # Timing
    vector_search_ms: float = 0.0
    entity_extraction_ms: float = 0.0
    graph_enrichment_ms: float = 0.0
    total_ms: float = 0.0

    # Statistics
    vector_hits_count: int = 0
    enriched_count: int = 0
    total_entities_found: int = 0
    total_relationships_found: int = 0


# =============================================================================
# Entity Extractor
# =============================================================================


class EntityExtractor:
    """
    Extracts entity references from text for graph lookup.

    Uses simple heuristics + optional LLM for entity extraction.
    """

    def __init__(self, use_llm: bool = False, llm_client: Optional[Any] = None):
        """
        Initialize entity extractor.

        Args:
            use_llm: Whether to use LLM for extraction
            llm_client: OpenAI client (required if use_llm=True)
        """
        self._use_llm = use_llm
        self._llm_client = llm_client

    async def extract_entities(
        self,
        text: str,
        context: Optional[dict[str, Any]] = None,
    ) -> list[dict[str, Any]]:
        """
        Extract entity references from text.

        Args:
            text: Text to extract from
            context: Optional context (packet metadata, etc.)

        Returns:
            List of entity dicts: {type, id, name, confidence}
        """
        entities = []

        # 1. Extract from metadata if available
        if context:
            # Agent ID
            if "agent_id" in context:
                entities.append(
                    {
                        "type": "Agent",
                        "id": context["agent_id"],
                        "name": context["agent_id"],
                        "confidence": 1.0,
                        "source": "metadata",
                    }
                )

            # Source ID (often user or system)
            if "source_id" in context:
                source = context["source_id"]
                entity_type = "User" if source.startswith("user:") else "System"
                entities.append(
                    {
                        "type": entity_type,
                        "id": source,
                        "name": source,
                        "confidence": 1.0,
                        "source": "metadata",
                    }
                )

            # Thread ID
            if "thread_id" in context:
                entities.append(
                    {
                        "type": "Thread",
                        "id": context["thread_id"],
                        "name": f"Thread:{context['thread_id'][:8]}",
                        "confidence": 1.0,
                        "source": "metadata",
                    }
                )

        # 2. Simple heuristic extraction (pattern matching)
        entities.extend(self._extract_by_patterns(text))

        # 3. LLM extraction if enabled
        if self._use_llm and self._llm_client:
            llm_entities = await self._extract_with_llm(text)
            entities.extend(llm_entities)

        # Deduplicate by (type, id)
        seen = set()
        unique_entities = []
        for entity in entities:
            key = (entity["type"], entity["id"])
            if key not in seen:
                seen.add(key)
                unique_entities.append(entity)

        return unique_entities

    def _extract_by_patterns(self, text: str) -> list[dict[str, Any]]:
        """Extract entities using regex patterns."""
        import re

        entities = []

        # UUID pattern (common for IDs)
        uuid_pattern = (
            r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b"
        )
        for match in re.finditer(uuid_pattern, text, re.IGNORECASE):
            entities.append(
                {
                    "type": "Entity",
                    "id": match.group(),
                    "name": f"Entity:{match.group()[:8]}",
                    "confidence": 0.7,
                    "source": "pattern",
                }
            )

        # Slack user pattern
        slack_user_pattern = r"<@([A-Z0-9]+)>"
        for match in re.finditer(slack_user_pattern, text):
            entities.append(
                {
                    "type": "User",
                    "id": f"slack:{match.group(1)}",
                    "name": f"Slack User {match.group(1)}",
                    "confidence": 0.9,
                    "source": "pattern",
                }
            )

        # GMP reference pattern
        gmp_pattern = r"GMP-(\d+)"
        for match in re.finditer(gmp_pattern, text, re.IGNORECASE):
            entities.append(
                {
                    "type": "GMP",
                    "id": f"gmp-{match.group(1)}",
                    "name": f"GMP-{match.group(1)}",
                    "confidence": 0.95,
                    "source": "pattern",
                }
            )

        # File path pattern
        file_pattern = r"(?:/[\w.-]+)+\.(?:py|ts|js|yaml|yml|json|md)"
        for match in re.finditer(file_pattern, text):
            entities.append(
                {
                    "type": "File",
                    "id": match.group(),
                    "name": match.group().split("/")[-1],
                    "confidence": 0.8,
                    "source": "pattern",
                }
            )

        return entities

    async def _extract_with_llm(self, text: str) -> list[dict[str, Any]]:
        """Extract entities using LLM."""
        if not self._llm_client:
            return []

        try:
            response = await self._llm_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": """Extract named entities from the text. Return JSON array:
[{"type": "Person|Organization|Tool|Concept|Event", "id": "unique_id", "name": "display_name", "confidence": 0.0-1.0}]
Only extract clearly identifiable entities. Be conservative.""",
                    },
                    {"role": "user", "content": text[:2000]},  # Limit input
                ],
                temperature=0.1,
                response_format={"type": "json_object"},
            )

            import json

            content = response.choices[0].message.content or "{}"
            result = json.loads(content)
            entities = result.get("entities", [])

            # Add source marker
            for entity in entities:
                entity["source"] = "llm"

            return entities
        except Exception as e:
            logger.warning(f"LLM entity extraction failed: {e}")
            return []


# =============================================================================
# Graph Enricher
# =============================================================================


class GraphEnricher:
    """
    Enriches vector search results with graph context from Neo4j.
    """

    def __init__(self, neo4j_client: Any):
        """
        Initialize with Neo4j client.

        Args:
            neo4j_client: Neo4jClient from memory.graph_client
        """
        self._neo4j = neo4j_client

    async def enrich(
        self,
        entities: list[dict[str, Any]],
        strategy: EnrichmentStrategy = EnrichmentStrategy.DIRECT,
        max_related: int = 10,
    ) -> GraphEnrichment:
        """
        Enrich entities with graph context.

        Args:
            entities: Extracted entities from vector hit
            strategy: Enrichment strategy
            max_related: Maximum related entities per source

        Returns:
            GraphEnrichment with related entities and paths
        """
        if not self._neo4j or not self._neo4j.is_available():
            return GraphEnrichment(
                source_packet_id=UUID("00000000-0000-0000-0000-000000000000"),
            )

        related_entities: list[dict[str, Any]] = []
        relationship_paths: list[dict[str, Any]] = []
        causal_chain: list[dict[str, Any]] = []

        for entity in entities:
            entity_type = entity.get("type", "Entity")
            entity_id = entity.get("id")

            if not entity_id:
                continue

            # Strategy: DIRECT - Get 1-hop neighbors
            if strategy in (
                EnrichmentStrategy.DIRECT,
                EnrichmentStrategy.EXTENDED,
                EnrichmentStrategy.FULL,
            ):
                neighbors = await self._get_direct_neighbors(
                    entity_type, entity_id, max_related
                )
                related_entities.extend(neighbors)

            # Strategy: EXTENDED - Get 2-hop neighborhood
            if strategy in (EnrichmentStrategy.EXTENDED, EnrichmentStrategy.FULL):
                extended = await self._get_extended_neighborhood(
                    entity_type, entity_id, max_related
                )
                related_entities.extend(extended)

            # Strategy: CAUSAL - Follow TRIGGERED chains
            if strategy in (EnrichmentStrategy.CAUSAL, EnrichmentStrategy.FULL):
                if entity_type == "Event":
                    chain = await self._get_causal_chain(entity_id)
                    causal_chain.extend(chain)

        # Deduplicate related entities
        seen_ids = set()
        unique_related = []
        for entity in related_entities:
            eid = entity.get("id")
            if eid and eid not in seen_ids:
                seen_ids.add(eid)
                unique_related.append(entity)

        return GraphEnrichment(
            source_packet_id=UUID(
                "00000000-0000-0000-0000-000000000000"
            ),  # Set by caller
            related_entities=unique_related[: max_related * 2],
            relationship_paths=relationship_paths,
            causal_chain=causal_chain,
            entity_count=len(unique_related),
            relationship_count=len(relationship_paths),
        )

    async def _get_direct_neighbors(
        self,
        entity_type: str,
        entity_id: str,
        limit: int,
    ) -> list[dict[str, Any]]:
        """Get direct (1-hop) neighbors."""
        # Sanitize entity_type for Cypher
        safe_type = entity_type.replace("`", "").replace(":", "")

        query = f"""
        MATCH (n:`{safe_type}` {{id: $entity_id}})-[r]-(neighbor)
        RETURN DISTINCT 
            neighbor.id as id,
            labels(neighbor)[0] as type,
            neighbor.name as name,
            type(r) as relationship
        LIMIT $limit
        """

        try:
            results = await self._neo4j.run_query(
                query,
                {"entity_id": entity_id, "limit": limit},
            )
            return [
                {
                    "id": r["id"],
                    "type": r["type"],
                    "name": r.get("name") or r["id"],
                    "relationship": r["relationship"],
                    "hop_distance": 1,
                }
                for r in results
                if r.get("id")
            ]
        except Exception as e:
            logger.debug(f"Direct neighbor query failed: {e}")
            return []

    async def _get_extended_neighborhood(
        self,
        entity_type: str,
        entity_id: str,
        limit: int,
    ) -> list[dict[str, Any]]:
        """Get extended (2-hop) neighborhood."""
        safe_type = entity_type.replace("`", "").replace(":", "")

        query = f"""
        MATCH (n:`{safe_type}` {{id: $entity_id}})-[*2]-(neighbor)
        WHERE neighbor.id <> $entity_id
        RETURN DISTINCT 
            neighbor.id as id,
            labels(neighbor)[0] as type,
            neighbor.name as name
        LIMIT $limit
        """

        try:
            results = await self._neo4j.run_query(
                query,
                {"entity_id": entity_id, "limit": limit},
            )
            return [
                {
                    "id": r["id"],
                    "type": r["type"],
                    "name": r.get("name") or r["id"],
                    "hop_distance": 2,
                }
                for r in results
                if r.get("id")
            ]
        except Exception as e:
            logger.debug(f"Extended neighborhood query failed: {e}")
            return []

    async def _get_causal_chain(self, event_id: str) -> list[dict[str, Any]]:
        """Get causal chain for an event."""
        query = """
        MATCH (root:Event {id: $event_id})
        MATCH path = (root)-[:TRIGGERED*0..5]->(descendant:Event)
        RETURN 
            descendant.id as id,
            descendant.event_type as event_type,
            descendant.timestamp as timestamp,
            length(path) as depth
        ORDER BY length(path)
        LIMIT 20
        """

        try:
            results = await self._neo4j.run_query(query, {"event_id": event_id})
            return [
                {
                    "id": r["id"],
                    "type": "Event",
                    "event_type": r.get("event_type"),
                    "timestamp": r.get("timestamp"),
                    "causal_depth": r.get("depth", 0),
                }
                for r in results
            ]
        except Exception as e:
            logger.debug(f"Causal chain query failed: {e}")
            return []


# =============================================================================
# Hybrid RAG Pipeline
# =============================================================================


class HybridRAGPipeline:
    """
    Hybrid RAG Pipeline combining vector search + graph enrichment.

    Usage:
        pipeline = HybridRAGPipeline(
            semantic_service=semantic_svc,
            neo4j_client=neo4j,
        )

        results = await pipeline.search(
            query="How do we handle authentication?",
            strategy=EnrichmentStrategy.EXTENDED,
            limit=10,
        )

        # Results include:
        # - Original vector hits (semantic similarity)
        # - Related entities from graph
        # - Causal chains for events
        # - Combined relevance scores
    """

    def __init__(
        self,
        semantic_service: Any,  # SemanticService from memory.substrate_semantic
        neo4j_client: Any,  # Neo4jClient from memory.graph_client
        entity_extractor: Optional[EntityExtractor] = None,
        graph_enricher: Optional[GraphEnricher] = None,
    ):
        """
        Initialize hybrid RAG pipeline.

        Args:
            semantic_service: SemanticService for vector search
            neo4j_client: Neo4jClient for graph enrichment
            entity_extractor: Custom entity extractor (optional)
            graph_enricher: Custom graph enricher (optional)
        """
        self._semantic = semantic_service
        self._neo4j = neo4j_client
        self._entity_extractor = entity_extractor or EntityExtractor()
        self._graph_enricher = graph_enricher or GraphEnricher(neo4j_client)

        logger.info("HybridRAGPipeline initialized")

    async def search(
        self,
        query: str,
        limit: int = 10,
        min_similarity: float = 0.5,
        strategy: EnrichmentStrategy = EnrichmentStrategy.DIRECT,
        enrich_top_n: int = 5,
    ) -> HybridSearchResult:
        """
        Execute hybrid search: vector + graph enrichment.

        Args:
            query: Search query
            limit: Maximum results
            min_similarity: Minimum similarity threshold
            strategy: Graph enrichment strategy
            enrich_top_n: Number of top results to enrich (saves Neo4j calls)

        Returns:
            HybridSearchResult with enriched results
        """
        import time

        start_time = time.time()

        # 1. Vector search
        vector_start = time.time()
        vector_hits = await self._vector_search(query, limit, min_similarity)
        vector_ms = (time.time() - vector_start) * 1000

        # 2. Entity extraction
        extract_start = time.time()
        for hit in vector_hits[:enrich_top_n]:
            context = {
                "source_id": hit.source_id,
                "thread_id": hit.thread_id,
                "kind": hit.kind,
            }
            hit.extracted_entities = await self._entity_extractor.extract_entities(
                hit.content,
                context,
            )
        extract_ms = (time.time() - extract_start) * 1000

        # 3. Graph enrichment
        enrich_start = time.time()
        hybrid_results: list[HybridResult] = []
        total_entities = 0
        total_relationships = 0

        for i, hit in enumerate(vector_hits):
            enrichment = None

            if (
                i < enrich_top_n
                and hit.extracted_entities
                and strategy != EnrichmentStrategy.NONE
            ):
                enrichment = await self._graph_enricher.enrich(
                    hit.extracted_entities,
                    strategy=strategy,
                )
                enrichment.source_packet_id = hit.packet_id
                total_entities += enrichment.entity_count
                total_relationships += enrichment.relationship_count

            # Calculate combined score
            combined_score, ranking_factors = self._calculate_combined_score(
                hit, enrichment
            )

            hybrid_results.append(
                HybridResult(
                    vector_hit=hit,
                    enrichment=enrichment,
                    combined_score=combined_score,
                    ranking_factors=ranking_factors,
                )
            )

        enrich_ms = (time.time() - enrich_start) * 1000

        # 4. Re-rank by combined score
        hybrid_results.sort(key=lambda r: r.combined_score, reverse=True)

        total_ms = (time.time() - start_time) * 1000

        return HybridSearchResult(
            query=query,
            results=hybrid_results,
            vector_search_ms=vector_ms,
            entity_extraction_ms=extract_ms,
            graph_enrichment_ms=enrich_ms,
            total_ms=total_ms,
            vector_hits_count=len(vector_hits),
            enriched_count=min(enrich_top_n, len(vector_hits)),
            total_entities_found=total_entities,
            total_relationships_found=total_relationships,
        )

    async def _vector_search(
        self,
        query: str,
        limit: int,
        min_similarity: float,
    ) -> list[VectorHit]:
        """Execute vector search via semantic service."""
        try:
            # Use semantic service search
            results = await self._semantic.search(
                query=query,
                limit=limit,
                min_similarity=min_similarity,
            )

            return [
                VectorHit(
                    packet_id=UUID(str(r.packet_id))
                    if hasattr(r, "packet_id")
                    else UUID("00000000-0000-0000-0000-000000000000"),
                    content=r.content if hasattr(r, "content") else str(r),
                    similarity=r.similarity if hasattr(r, "similarity") else 0.0,
                    kind=r.kind if hasattr(r, "kind") else None,
                    source_id=r.source_id if hasattr(r, "source_id") else None,
                    thread_id=r.thread_id if hasattr(r, "thread_id") else None,
                    metadata=r.metadata if hasattr(r, "metadata") else {},
                )
                for r in results
            ]
        except Exception as e:
            logger.error(f"Vector search failed: {e}")
            return []

    def _calculate_combined_score(
        self,
        hit: VectorHit,
        enrichment: Optional[GraphEnrichment],
    ) -> tuple[float, dict[str, float]]:
        """
        Calculate combined relevance score.

        Combines:
        - Vector similarity (primary signal)
        - Graph centrality (number of connections)
        - Entity diversity (variety of related entities)
        """
        factors = {
            "vector_similarity": hit.similarity,
            "graph_centrality": 0.0,
            "entity_diversity": 0.0,
        }

        if enrichment:
            # Graph centrality: normalized count of relationships
            max_relationships = 20  # Normalization factor
            factors["graph_centrality"] = min(
                enrichment.relationship_count / max_relationships, 1.0
            )

            # Entity diversity: variety of entity types
            if enrichment.related_entities:
                unique_types = len(
                    set(e.get("type") for e in enrichment.related_entities)
                )
                factors["entity_diversity"] = min(
                    unique_types / 5, 1.0
                )  # Normalize to 5 types

        # Weighted combination
        weights = {
            "vector_similarity": 0.6,  # Primary signal
            "graph_centrality": 0.25,  # Context richness
            "entity_diversity": 0.15,  # Variety bonus
        }

        combined = sum(factors[k] * weights[k] for k in factors)

        return combined, factors


# =============================================================================
# Convenience Functions
# =============================================================================


_pipeline: Optional[HybridRAGPipeline] = None


@must_stay_async("callers use await")
async def get_hybrid_rag_pipeline(
    semantic_service: Any,
    neo4j_client: Any,
) -> HybridRAGPipeline:
    """
    Get or create singleton hybrid RAG pipeline.

    Args:
        semantic_service: SemanticService instance
        neo4j_client: Neo4jClient instance

    Returns:
        HybridRAGPipeline instance
    """
    global _pipeline

    if _pipeline is None:
        _pipeline = HybridRAGPipeline(semantic_service, neo4j_client)

    return _pipeline


async def hybrid_search(
    semantic_service: Any,
    neo4j_client: Any,
    query: str,
    limit: int = 10,
    strategy: EnrichmentStrategy = EnrichmentStrategy.DIRECT,
) -> HybridSearchResult:
    """
    Convenience function for hybrid search.

    Args:
        semantic_service: SemanticService
        neo4j_client: Neo4jClient
        query: Search query
        limit: Maximum results
        strategy: Enrichment strategy

    Returns:
        HybridSearchResult
    """
    pipeline = await get_hybrid_rag_pipeline(semantic_service, neo4j_client)
    return await pipeline.search(query, limit=limit, strategy=strategy)


__all__ = [
    "EnrichmentStrategy",
    "VectorHit",
    "GraphEnrichment",
    "HybridResult",
    "HybridSearchResult",
    "EntityExtractor",
    "GraphEnricher",
    "HybridRAGPipeline",
    "get_hybrid_rag_pipeline",
    "hybrid_search",
]

# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "MEM-LEAR-024",
    "governance_level": "high",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": ["core.decorators"],
    "tags": ["async", "auth", "data-models", "dataclass", "debugging", "event-driven", "graph-db", "learning", "logging", "messaging"],
    "keywords": ["(vector", "bridge", "bridge)", "enrich", "enricher", "enrichment", "entities", "entity"],
    "business_value": "The "killer feature" — combines vector search (pgvector) with graph enrichment (Neo4j) for comprehensive retrieval. 1. Vector search finds semantically similar documents 2. Graph bridge extracts entit",
    "last_modified": "2026-01-17T23:47:56Z",
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
