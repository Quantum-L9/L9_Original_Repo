"""
L9 Memory - Pre-built Saga Patterns
===================================

Ready-to-use saga patterns for common cross-DB operations.

Patterns:
1. VectorToGraphSaga — Vector search → Entity extraction → Graph enrichment
2. EntityEnrichmentSaga — Entity lookup → Relationship discovery → Context assembly
3. TimelineCorrelationSaga — Event timeline → Causal chain → Impact analysis
4. FetchAndEnrichSaga — The "canonical" saga from TODO #5

Version: 1.0.0
"""

from __future__ import annotations

# ============================================================================
__dora_meta__ = {
    "component_name": "Pre-built Saga Patterns",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2026-01-13T18:30:12Z",
    "updated_at": "2026-01-17T23:47:56Z",
    "layer": "learning",
    "domain": "memory_substrate",
    "module_name": "saga_patterns",
    "type": "service",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": ["Neo4j", "PostgreSQL"],
        "memory_layers": ["semantic_memory"],
        "imported_by": [
            "memory.__init__",
            "memory.substrate_service",
            "tests.memory.test_saga",
        ],
    },
}
# ============================================================================

from typing import Any

import structlog

from core.decorators import must_stay_async
from memory.saga import (
    DatabaseType,
    Saga,
    SagaBuilder,
    SagaContext,
    SagaExecutor,
    SagaResult,
    get_saga_executor,
)

logger = structlog.get_logger(__name__)


# =============================================================================
# Step Functions
# =============================================================================


async def _vector_search_step(
    context: SagaContext,
    semantic: Any = None,
    **kwargs,
) -> list[dict[str, Any]]:
    """
    Step 1: Vector search in Postgres.

    Searches for semantically similar content.
    """
    query = context.input_data.get("query", "")
    limit = context.input_data.get("limit", 10)
    min_similarity = context.input_data.get("min_similarity", 0.5)

    if not semantic:
        logger.warning("Semantic service not available, returning empty results")
        return []

    try:
        results = await semantic.search(
            query=query,
            top_k=limit,
        )
        filtered_results = [
            r
            for r in results
            if (
                (
                    r.get("similarity")
                    if isinstance(r, dict)
                    else getattr(r, "similarity", None)
                )
                or (
                    r.get("score", 0.0)
                    if isinstance(r, dict)
                    else getattr(r, "score", 0.0)
                )
            )
            >= min_similarity
        ]

        # Convert to dicts
        hits = []
        for r in filtered_results:
            hit = {
                "packet_id": str(r.get("packet_id"))
                if isinstance(r, dict) and r.get("packet_id")
                else (str(r.packet_id) if hasattr(r, "packet_id") else None),
                "content": (r.get("content") if isinstance(r, dict) else r.content)
                if (isinstance(r, dict) or hasattr(r, "content"))
                else str(r),
                "similarity": (
                    r.get("similarity") if isinstance(r, dict) else r.similarity
                )
                if (isinstance(r, dict) or hasattr(r, "similarity"))
                else (r.get("score", 0.0) if isinstance(r, dict) else 0.0),
                "kind": r.get("kind")
                if isinstance(r, dict)
                else (r.kind if hasattr(r, "kind") else None),
                "source_id": r.get("source_id")
                if isinstance(r, dict)
                else (r.source_id if hasattr(r, "source_id") else None),
                "thread_id": r.get("thread_id")
                if isinstance(r, dict)
                else (r.thread_id if hasattr(r, "thread_id") else None),
            }
            hits.append(hit)

        logger.debug(f"Vector search returned {len(hits)} hits")
        return hits

    except Exception as e:
        logger.error(f"Vector search failed: {e}")
        raise


@must_stay_async("callers use await")
async def _extract_entities_step(
    context: SagaContext,
    **kwargs,
) -> list[dict[str, Any]]:
    """
    Step 2: Extract entity IDs from vector search results.

    Uses pattern matching and metadata extraction.
    """
    import re

    vector_results = context.get_step_output("vector_search") or []
    entities: list[dict[str, Any]] = []

    for hit in vector_results:
        content = hit.get("content", "")

        # Extract from metadata
        if hit.get("source_id"):
            source = hit["source_id"]
            entity_type = (
                "User"
                if source.startswith("user:")
                else "Agent"
                if source.startswith("agent:")
                else "System"
            )
            entities.append(
                {
                    "type": entity_type,
                    "id": source,
                    "source": "metadata",
                    "from_packet": hit.get("packet_id"),
                }
            )

        if hit.get("thread_id"):
            entities.append(
                {
                    "type": "Thread",
                    "id": hit["thread_id"],
                    "source": "metadata",
                    "from_packet": hit.get("packet_id"),
                }
            )

        # Extract UUIDs from content
        uuid_pattern = (
            r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b"
        )
        for match in re.finditer(uuid_pattern, content, re.IGNORECASE):
            entities.append(
                {
                    "type": "Entity",
                    "id": match.group(),
                    "source": "content",
                    "from_packet": hit.get("packet_id"),
                }
            )

        # Extract GMP references
        gmp_pattern = r"GMP-(\d+)"
        for match in re.finditer(gmp_pattern, content, re.IGNORECASE):
            entities.append(
                {
                    "type": "GMP",
                    "id": f"gmp-{match.group(1)}",
                    "source": "content",
                    "from_packet": hit.get("packet_id"),
                }
            )

        # Extract file paths
        file_pattern = r"(?:/[\w.-]+)+\.(?:py|ts|js|yaml|yml|json|md)"
        for match in re.finditer(file_pattern, content):
            entities.append(
                {
                    "type": "File",
                    "id": match.group(),
                    "source": "content",
                    "from_packet": hit.get("packet_id"),
                }
            )

    # Deduplicate by (type, id)
    seen = set()
    unique_entities = []
    for entity in entities:
        key = (entity["type"], entity["id"])
        if key not in seen:
            seen.add(key)
            unique_entities.append(entity)

    # Add to context for downstream steps
    context.add_entities(unique_entities)

    logger.debug(f"Extracted {len(unique_entities)} unique entities")
    return unique_entities


@must_stay_async("callers use await")
async def _graph_enrich_step(
    context: SagaContext,
    neo4j: Any = None,
    **kwargs,
) -> dict[str, Any]:
    """
    Step 3: Enrich entities with Neo4j graph data.

    Finds related entities and relationships.
    """
    entities = context.entities

    if not neo4j or not neo4j.is_available():
        logger.warning("Neo4j not available, skipping enrichment")
        return {"related_entities": [], "relationships": []}

    related_entities: list[dict[str, Any]] = []
    relationships: list[dict[str, Any]] = []

    for entity in entities[:20]:  # Limit to avoid too many queries
        entity_type = entity.get("type", "Entity")
        entity_id = entity.get("id")

        if not entity_id:
            continue

        # Sanitize type for Cypher
        safe_type = entity_type.replace("`", "").replace(":", "")

        # Query for neighbors
        try:
            query = f"""
            MATCH (n:`{safe_type}` {{id: $entity_id}})-[r]-(neighbor)
            RETURN DISTINCT
                neighbor.id as neighbor_id,
                labels(neighbor)[0] as neighbor_type,
                neighbor.name as neighbor_name,
                type(r) as relationship
            LIMIT 5
            """

            results = await neo4j.run_query(
                query,
                {"entity_id": entity_id},
            )

            for r in results:
                if r.get("neighbor_id"):
                    related_entities.append(
                        {
                            "id": r["neighbor_id"],
                            "type": r.get("neighbor_type", "Unknown"),
                            "name": r.get("neighbor_name"),
                            "related_to": entity_id,
                        }
                    )

                    relationships.append(
                        {
                            "from": entity_id,
                            "from_type": entity_type,
                            "to": r["neighbor_id"],
                            "to_type": r.get("neighbor_type", "Unknown"),
                            "relationship": r.get("relationship"),
                        }
                    )

        except Exception as e:
            logger.debug(f"Graph query failed for {entity_type}:{entity_id}: {e}")

    # Add to context
    context.add_relationships(relationships)

    logger.debug(
        f"Found {len(related_entities)} related entities, {len(relationships)} relationships"
    )

    return {
        "related_entities": related_entities,
        "relationships": relationships,
    }


@must_stay_async("callers use await")
async def _assemble_result_step(
    context: SagaContext,
    **kwargs,
) -> dict[str, Any]:
    """
    Step 4: Assemble final result from all steps.
    """
    vector_results = context.get_step_output("vector_search") or []
    extracted_entities = context.get_step_output("extract_entities") or []
    graph_data = context.get_step_output("graph_enrich") or {}

    return {
        "vector_hits": vector_results,
        "extracted_entities": extracted_entities,
        "related_entities": graph_data.get("related_entities", []),
        "relationships": graph_data.get("relationships", []),
        "statistics": {
            "vector_hits_count": len(vector_results),
            "entities_extracted": len(extracted_entities),
            "related_entities_found": len(graph_data.get("related_entities", [])),
            "relationships_found": len(graph_data.get("relationships", [])),
        },
    }


# =============================================================================
# Timeline Steps
# =============================================================================


@must_stay_async("callers use await")
async def _fetch_events_step(
    context: SagaContext,
    neo4j: Any = None,
    **kwargs,
) -> list[dict[str, Any]]:
    """Fetch events from Neo4j timeline."""
    start_time = context.input_data.get("start_time")
    end_time = context.input_data.get("end_time")
    event_type = context.input_data.get("event_type")
    limit = context.input_data.get("limit", 50)

    if not neo4j or not neo4j.is_available():
        return []

    conditions = []
    params: dict[str, Any] = {"limit": limit}

    if start_time:
        conditions.append("e.timestamp >= $start_time")
        params["start_time"] = start_time
    if end_time:
        conditions.append("e.timestamp <= $end_time")
        params["end_time"] = end_time
    if event_type:
        conditions.append("e.event_type = $event_type")
        params["event_type"] = event_type

    where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

    query = f"""
    MATCH (e:Event)
    {where_clause}
    RETURN e.id as id, e.event_type as event_type, e.timestamp as timestamp,
           properties(e) as properties
    ORDER BY e.timestamp DESC
    LIMIT $limit
    """

    try:
        results = await neo4j.run_query(query, params)
        events = [
            {
                "id": r["id"],
                "event_type": r.get("event_type"),
                "timestamp": r.get("timestamp"),
                "properties": r.get("properties", {}),
            }
            for r in results
        ]

        # Add events as entities
        for event in events:
            context.add_entities(
                [
                    {
                        "type": "Event",
                        "id": event["id"],
                        "event_type": event.get("event_type"),
                    }
                ]
            )

        return events
    except Exception as e:
        logger.error(f"Event fetch failed: {e}")
        return []


@must_stay_async("callers use await")
async def _trace_causal_chain_step(
    context: SagaContext,
    neo4j: Any = None,
    **kwargs,
) -> list[dict[str, Any]]:
    """Trace causal chains from events."""
    events = context.get_step_output("fetch_events") or []

    if not neo4j or not neo4j.is_available() or not events:
        return []

    causal_chains: list[dict[str, Any]] = []

    for event in events[:10]:  # Limit root events
        event_id = event.get("id")
        if not event_id:
            continue

        query = """
        MATCH (root:Event {id: $event_id})
        MATCH path = (root)-[:TRIGGERED*0..5]->(descendant:Event)
        RETURN
            root.id as root_id,
            [node in nodes(path) | {
                id: node.id,
                event_type: node.event_type,
                timestamp: node.timestamp
            }] as chain
        LIMIT 10
        """

        try:
            results = await neo4j.run_query(query, {"event_id": event_id})
            for r in results:
                if r.get("chain"):
                    causal_chains.append(
                        {
                            "root_event": event_id,
                            "chain": r["chain"],
                            "chain_length": len(r["chain"]),
                        }
                    )
        except Exception as e:
            logger.debug(f"Causal chain trace failed for {event_id}: {e}")

    return causal_chains


# =============================================================================
# Pre-built Sagas
# =============================================================================


def create_fetch_and_enrich_saga() -> Saga:
    """
    Create the canonical "fetch_and_enrich" saga from TODO #5.

    Flow:
    1. Vector search in Postgres
    2. Extract entity IDs
    3. Neo4j graph enrichment
    4. Combined result

    Usage:
        saga = create_fetch_and_enrich_saga()
        result = await executor.execute(saga, input_data={"query": "..."})
    """
    return (
        SagaBuilder("fetch_and_enrich")
        .add_step(
            name="vector_search",
            database=DatabaseType.POSTGRES,
            description="Search for semantically similar content",
            execute_fn=_vector_search_step,
            max_retries=1,
        )
        .add_step(
            name="extract_entities",
            database=DatabaseType.MEMORY,
            description="Extract entity IDs from search results",
            execute_fn=_extract_entities_step,
        )
        .add_step(
            name="graph_enrich",
            database=DatabaseType.NEO4J,
            description="Enrich entities with graph relationships",
            execute_fn=_graph_enrich_step,
            required=False,  # Continue even if Neo4j unavailable
        )
        .add_step(
            name="assemble_result",
            database=DatabaseType.MEMORY,
            description="Assemble final combined result",
            execute_fn=_assemble_result_step,
        )
        .build()
    )


def create_entity_enrichment_saga() -> Saga:
    """
    Create entity enrichment saga.

    For when you already have entity IDs and want graph context.

    Input: {"entity_ids": ["id1", "id2"], "entity_type": "User"}
    """

    @must_stay_async("callers use await")
    async def lookup_entities(context: SagaContext, neo4j: Any = None, **kwargs):
        """
        Performs entity lookup within a saga context using Neo4j; returns a list of entities or an empty list if Neo4j is unavailable.

        Args:
            context: SagaContext containing input data for entity retrieval.
            neo4j: Neo4j database client used for querying entities.
            **kwargs: Additional keyword arguments for customization.

        Returns:
            List of retrieved entities or an empty list if Neo4j is unavailable.
        """
        entity_ids = context.input_data.get("entity_ids", [])
        entity_type = context.input_data.get("entity_type", "Entity")

        if not neo4j or not neo4j.is_available():
            return []

        safe_type = entity_type.replace("`", "").replace(":", "")

        query = f"""
        UNWIND $ids as entity_id
        MATCH (n:`{safe_type}` {{id: entity_id}})
        RETURN n.id as id, properties(n) as properties
        """

        try:
            results = await neo4j.run_query(query, {"ids": entity_ids})
            entities = []
            for r in results:
                entity = {"id": r["id"], "type": entity_type, **r.get("properties", {})}
                entities.append(entity)
                context.add_entities([{"type": entity_type, "id": r["id"]}])
            return entities
        except Exception as e:
            logger.error(f"Entity lookup failed: {e}")
            return []

    return (
        SagaBuilder("entity_enrichment")
        .add_step(
            name="lookup_entities",
            database=DatabaseType.NEO4J,
            description="Lookup entities by ID",
            execute_fn=lookup_entities,
        )
        .add_step(
            name="graph_enrich",
            database=DatabaseType.NEO4J,
            description="Enrich with graph relationships",
            execute_fn=_graph_enrich_step,
        )
        .build()
    )


def create_timeline_correlation_saga() -> Saga:
    """
    Create timeline correlation saga.

    For analyzing event sequences and causal chains.

    Input: {"start_time": "...", "end_time": "...", "event_type": "..."}
    """
    return (
        SagaBuilder("timeline_correlation")
        .add_step(
            name="fetch_events",
            database=DatabaseType.NEO4J,
            description="Fetch events in time range",
            execute_fn=_fetch_events_step,
        )
        .add_step(
            name="trace_causal_chains",
            database=DatabaseType.NEO4J,
            description="Trace causal chains from events",
            execute_fn=_trace_causal_chain_step,
        )
        .build()
    )


# =============================================================================
# High-Level API
# =============================================================================


class SagaPatterns:
    """
    High-level API for executing pre-built sagas.

    Usage:
        patterns = SagaPatterns(executor)

        # Fetch and enrich
        result = await patterns.fetch_and_enrich(
            query="How does authentication work?",
            limit=10,
        )

        # Entity enrichment
        result = await patterns.enrich_entities(
            entity_ids=["user-1", "user-2"],
            entity_type="User",
        )

        # Timeline correlation
        result = await patterns.correlate_timeline(
            start_time="2026-01-01T00:00:00Z",
            end_time="2026-01-12T23:59:59Z",
        )
    """

    def __init__(self, executor: SagaExecutor):
        """
        Initializes SagaPatterns with a SagaExecutor to manage pre-built saga workflows for cross-DB operations.

        Args:
            executor: SagaExecutor instance responsible for executing saga steps and managing workflow state.
        """
        self._executor = executor
        self._sagas = {
            "fetch_and_enrich": create_fetch_and_enrich_saga(),
            "entity_enrichment": create_entity_enrichment_saga(),
            "timeline_correlation": create_timeline_correlation_saga(),
        }

    @must_stay_async("callers use await")
    async def fetch_and_enrich(
        self,
        query: str,
        limit: int = 10,
        min_similarity: float = 0.5,
    ) -> SagaResult:
        """
        Execute the canonical fetch_and_enrich saga.

        1. Vector search for query
        2. Extract entity IDs
        3. Enrich with graph relationships
        4. Return combined result

        Args:
            query: Search query
            limit: Max vector results
            min_similarity: Minimum similarity threshold

        Returns:
            SagaResult with combined vector + graph data
        """
        return await self._executor.execute(
            self._sagas["fetch_and_enrich"],
            input_data={
                "query": query,
                "limit": limit,
                "min_similarity": min_similarity,
            },
        )

    async def enrich_entities(
        self,
        entity_ids: list[str],
        entity_type: str = "Entity",
    ) -> SagaResult:
        """
        Enrich known entities with graph context.

        Args:
            entity_ids: List of entity IDs to enrich
            entity_type: Node label type

        Returns:
            SagaResult with entity data and relationships
        """
        return await self._executor.execute(
            self._sagas["entity_enrichment"],
            input_data={
                "entity_ids": entity_ids,
                "entity_type": entity_type,
            },
        )

    async def correlate_timeline(
        self,
        start_time: str | None = None,
        end_time: str | None = None,
        event_type: str | None = None,
        limit: int = 50,
    ) -> SagaResult:
        """
        Correlate events in a timeline with causal chains.

        Args:
            start_time: ISO timestamp start
            end_time: ISO timestamp end
            event_type: Filter by event type
            limit: Max events

        Returns:
            SagaResult with events and causal chains
        """
        return await self._executor.execute(
            self._sagas["timeline_correlation"],
            input_data={
                "start_time": start_time,
                "end_time": end_time,
                "event_type": event_type,
                "limit": limit,
            },
        )


# =============================================================================
# Convenience Functions
# =============================================================================


_patterns: SagaPatterns | None = None


async def get_saga_patterns(
    executor: SagaExecutor | None = None,
    postgres_pool: Any | None = None,
    neo4j_client: Any | None = None,
    semantic_service: Any | None = None,
) -> SagaPatterns:
    """Get or create singleton saga patterns."""
    global _patterns

    if _patterns is None:
        if executor is None:
            executor = await get_saga_executor(
                postgres_pool=postgres_pool,
                neo4j_client=neo4j_client,
                semantic_service=semantic_service,
            )
        _patterns = SagaPatterns(executor)

    return _patterns


@must_stay_async("callers use await")
async def fetch_and_enrich(
    query: str,
    postgres_pool: Any | None = None,
    neo4j_client: Any | None = None,
    semantic_service: Any | None = None,
    limit: int = 10,
) -> SagaResult:
    """
    Convenience function for fetch_and_enrich saga.

    This is THE canonical implementation of TODO #5.

    Args:
        query: Search query
        postgres_pool: asyncpg pool
        neo4j_client: Neo4jClient
        semantic_service: SemanticService
        limit: Max results

    Returns:
        SagaResult with vector search + graph enrichment
    """
    patterns = await get_saga_patterns(
        postgres_pool=postgres_pool,
        neo4j_client=neo4j_client,
        semantic_service=semantic_service,
    )
    return await patterns.fetch_and_enrich(query, limit=limit)


__all__ = [
    # High-level API
    "SagaPatterns",
    "create_entity_enrichment_saga",
    # Sagas
    "create_fetch_and_enrich_saga",
    "create_timeline_correlation_saga",
    # Convenience
    "fetch_and_enrich",
    "get_saga_patterns",
]

# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "MEM-LEAR-019",
    "governance_level": "critical",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": ["core.decorators", "memory.saga"],
    "tags": [
        "api",
        "async",
        "auth",
        "debugging",
        "event-driven",
        "graph-db",
        "learning",
        "logging",
        "memory-substrate",
        "service",
    ],
    "keywords": [
        "analysis",
        "built",
        "correlate",
        "correlation",
        "create",
        "enrich",
        "enrichment",
        "entities",
    ],
    "business_value": "Implements SagaPatterns for saga patterns functionality",
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
