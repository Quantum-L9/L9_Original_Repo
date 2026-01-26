"""
L9 Graph Search Cache
Version: 1.0.0

Neo4j graph search with Redis-backed caching and schema-version-aware invalidation.
Implements Decision 8 from design clarifications.
"""

from __future__ import annotations

# ============================================================================
__dora_meta__ = {
    "component_name": "Graph Search Cache",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2026-01-11T18:13:39Z",
    "updated_at": "2026-01-14T15:03:00Z",
    "layer": "learning",
    "domain": "data_models",
    "module_name": "graph_search_cache",
    "type": "schema",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": ["Neo4j", "Redis"],
        "memory_layers": [],
        "imported_by": [
            "config.cursor_langgraph_config",
            "tests.integration.test_cursor_langgraph_integration",
        ],
    },
}
# ============================================================================

import hashlib
import json
import random
from datetime import datetime
from typing import Any, Dict, List, Literal, Optional

import structlog
from pydantic import BaseModel, Field

from memory.graph_client import Neo4jClient
from runtime.redis_client import RedisClient

logger = structlog.get_logger(__name__)


# =============================================================================
# Models
# =============================================================================


class GraphSearchContext(BaseModel):
    """Context for graph search operations."""

    agent_id: Optional[str] = Field(None, description="Agent identifier")
    project_id: str = Field(..., description="Project identifier")
    freshness_level: Literal["strict", "normal", "relaxed"] = Field(
        default="normal", description="Freshness requirement"
    )


class GraphSearchResult(BaseModel):
    """Graph search result with caching metadata."""

    results: List[Dict[str, Any]] = Field(..., description="Search results")
    created_at: datetime = Field(
        default_factory=datetime.utcnow, description="Result creation time"
    )
    schema_version: str = Field(..., description="Schema version hash")
    ttl: int = Field(..., description="Time-to-live in seconds")


# =============================================================================
# Schema Version Computation
# =============================================================================


def compute_graph_schema_version() -> str:
    """
    Compute GRAPH_CACHE_SCHEMA_VERSION from query builder + world model schema.

    Per Decision 8: hash of graph_search_query_builder.py + core.worldmodel.l9schema
    """
    try:
        # Try to import graph query builder
        from core.graph.query.graph_search_query_builder import \
            GRAPH_CACHE_SCHEMA_VERSION

        query_hash = GRAPH_CACHE_SCHEMA_VERSION
    except ImportError:
        # Fallback: hash DSL structure
        dsl_structure = {
            "sessions_for_agent": "MATCH (s:Session)-[:PARTICIPATED_IN]->(a:Agent {id: $agent_id}) RETURN s",
            "entities_by_type": "MATCH (e:Entity {type: $entity_type}) RETURN e",
        }
        query_hash = hashlib.sha256(
            json.dumps(dsl_structure, sort_keys=True).encode()
        ).hexdigest()[:16]

    try:
        # Try to import world model schema version
        from core.worldmodel.l9schema import \
            WORLD_MODEL_SCHEMA_VERSION

        world_model_hash = WORLD_MODEL_SCHEMA_VERSION
    except (ImportError, AttributeError):
        # Fallback: use default
        world_model_hash = "1.0"

    # Combine hashes
    combined = f"{query_hash}:{world_model_hash}"
    schema_version = hashlib.sha256(combined.encode()).hexdigest()[:32]

    return schema_version


GRAPH_CACHE_SCHEMA_VERSION = compute_graph_schema_version()


# =============================================================================
# Cache Functions
# =============================================================================


def _compute_query_hash(query: str, params: Dict[str, Any]) -> str:
    """Compute hash for query + params."""
    combined = json.dumps({"query": query, "params": params}, sort_keys=True)
    return hashlib.sha256(combined.encode()).hexdigest()[:16]


def _compute_ttl(ctx: GraphSearchContext, is_governance: bool = False) -> int:
    """
    Compute TTL with jitter.

    Args:
        ctx: Graph search context
        is_governance: Whether this is a governance query

    Returns:
        TTL in seconds with ±10% jitter
    """
    if is_governance:
        base_ttl = random.randint(60, 120)
    else:
        base_ttl = random.randint(300, 600)

    # Add ±10% jitter
    jitter = int(base_ttl * 0.1)
    ttl = base_ttl + random.randint(-jitter, jitter)

    return max(ttl, 10)  # Minimum 10 seconds


async def cached_graph_search(
    query: str,
    params: Dict[str, Any],
    ctx: GraphSearchContext,
    redis_client: Optional[RedisClient] = None,
    neo4j_client: Optional[Neo4jClient] = None,
) -> GraphSearchResult:
    """
    Execute graph search with Redis caching and schema version invalidation.

    Args:
        query: Cypher query string
        params: Query parameters
        ctx: Graph search context
        redis_client: Redis client (creates if None)
        neo4j_client: Neo4j client (uses get_neo4j_client if None)

    Returns:
        GraphSearchResult with results and metadata
    """
    logger.info("Graph search", query=query[:50], project_id=ctx.project_id)

    # Compute cache key
    query_hash = _compute_query_hash(query, params)
    cache_key = (
        f"graph_search:{ctx.project_id}:{ctx.agent_id or 'default'}:{query_hash}"
    )

    # Check cache
    if redis_client:
        try:
            cached = await redis_client.get(cache_key)
            if cached:
                cached_data = json.loads(cached)

                # Check schema version
                cached_version = cached_data.get("schema_version")
                if cached_version == GRAPH_CACHE_SCHEMA_VERSION:
                    logger.info("Cache hit", cache_key=cache_key)
                    return GraphSearchResult(
                        results=cached_data["results"],
                        created_at=datetime.fromisoformat(cached_data["created_at"]),
                        schema_version=cached_version,
                        ttl=cached_data["ttl"],
                    )
                else:
                    logger.info(
                        "Cache miss (schema version mismatch)",
                        cached_version=cached_version,
                        current_version=GRAPH_CACHE_SCHEMA_VERSION,
                    )
        except Exception as e:
            logger.warning("Cache read failed", error=str(e))

    # Cache miss: execute Neo4j query
    if neo4j_client is None:
        from memory.graph_client import get_neo4j_client

        neo4j_client = await get_neo4j_client()

    if not neo4j_client or not neo4j_client.is_available():
        logger.error("Neo4j not available")
        return GraphSearchResult(
            results=[],
            schema_version=GRAPH_CACHE_SCHEMA_VERSION,
            ttl=0,
        )

    try:
        # Execute query
        results = []
        session = neo4j_client.session()
        try:
            result = await session.run(query, params)
            async for record in result:
                results.append(dict(record))
        finally:
            await session.close()

        logger.info("Graph query executed", results_count=len(results))
    except Exception as e:
        logger.error("Graph query failed", error=str(e))
        results = []

    # Determine TTL
    is_governance = "governance" in query.lower() or "approval" in query.lower()
    ttl = _compute_ttl(ctx, is_governance=is_governance)

    # Create result
    search_result = GraphSearchResult(
        results=results,
        schema_version=GRAPH_CACHE_SCHEMA_VERSION,
        ttl=ttl,
    )

    # Cache result
    if redis_client:
        try:
            cache_data = {
                "results": results,
                "created_at": search_result.created_at.isoformat(),
                "schema_version": GRAPH_CACHE_SCHEMA_VERSION,
                "ttl": ttl,
            }
            await redis_client.set(cache_key, json.dumps(cache_data), ttl=ttl)
            logger.info("Result cached", cache_key=cache_key, ttl=ttl)
        except Exception as e:
            logger.warning("Cache write failed", error=str(e))

    return search_result


# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "MEM-LEAR-040",
    "governance_level": "high",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [
        "core.graph.query.graph_search_query_builder",
        "core.worldmodel.l9schema",
        "memory.graph_client",
        "runtime.redis_client",
    ],
    "tags": [
        "async",
        "cache",
        "data-models",
        "graph-db",
        "learning",
        "logging",
        "pydantic",
        "schema",
        "security",
        "serialization",
    ],
    "keywords": ["cache", "cached", "compute", "graph", "schema", "search", "version"],
    "business_value": "Implements Decision 8 from design clarifications.",
    "last_modified": "2026-01-14T15:03:00Z",
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
