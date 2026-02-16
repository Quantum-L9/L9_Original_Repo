"""
L9 Cursor Semantic Search Wrapper
Version: 1.0.0

Thin async wrapper over existing semanticmemory / pgvector integration,
tailored for Cursor use cases.
"""

from __future__ import annotations

from core.decorators import must_stay_async

# ============================================================================
__dora_meta__ = {
    "component_name": "Semantic Search",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2026-01-11T18:13:39Z",
    "updated_at": "2026-01-14T15:03:00Z",
    "layer": "learning",
    "domain": "data_models",
    "module_name": "semantic_search",
    "type": "schema",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": [],
        "memory_layers": ["semantic_memory", "working_memory"],
        "imported_by": ["tests.integration.test_cursor_langgraph_integration"],
    },
}
# ============================================================================

from typing import TYPE_CHECKING
from uuid import UUID

import structlog
from pydantic import BaseModel, Field

from core.schemas import SemanticSearchRequest

if TYPE_CHECKING:
    from memory.substrate_service import MemorySubstrateService

logger = structlog.get_logger(__name__)


# =============================================================================
# Models
# =============================================================================


class SearchHit(BaseModel):
    """Search hit result for Cursor."""

    packet_id: UUID = Field(..., description="Packet ID")
    similarity_score: float = Field(..., description="Similarity score (0-1)")
    packet_type: str | None = Field(None, description="Packet type")
    scope: str | None = Field(None, description="Scope (developer, global)")
    tags: list[str] | None = Field(None, description="Tags")
    payload: dict = Field(default_factory=dict, description="Packet payload")


# =============================================================================
# Search Function
# =============================================================================


@must_stay_async("callers use await")
async def semantic_search(
    query: str,
    agent_id: str,
    project_id: str,
    top_k: int = 10,
    substrate_service: MemorySubstrateService | None = None,
) -> list[SearchHit]:
    """
    Semantic search wrapper for Cursor.

    Args:
        query: Search query string
        agent_id: Agent identifier
        project_id: Project identifier (for filtering if needed)
        top_k: Number of results to return
        substrate_service: MemorySubstrateService instance (creates if None)

    Returns:
        List of SearchHit objects
    """
    logger.info("Semantic search", query=query[:50], agent_id=agent_id, top_k=top_k)

    # Get substrate service if not provided
    if substrate_service is None:
        # Service must be initialized before use
        # For now, raise error to require explicit service injection
        raise ValueError(
            "substrate_service must be provided or initialized via init_service()"
        )

    # Build search request
    request = SemanticSearchRequest(
        query=query,
        top_k=top_k,
        agent_id=agent_id,
        min_score=0.5,  # Default minimum similarity
    )

    # Execute search
    result = await substrate_service.semantic_search(request)

    # Map SemanticHit to SearchHit
    hits = []
    for hit in result.hits:
        # Extract packet_id from payload or embedding_id
        packet_id = hit.payload.get("packet_id") or hit.embedding_id

        # Extract metadata
        packet_type = hit.payload.get("packet_type")
        scope = hit.payload.get("scope")
        tags = hit.payload.get("tags", [])

        search_hit = SearchHit(
            packet_id=UUID(packet_id) if isinstance(packet_id, str) else packet_id,
            similarity_score=hit.score,
            packet_type=packet_type,
            scope=scope,
            tags=tags if isinstance(tags, list) else [],
            payload=hit.payload,
        )
        hits.append(search_hit)

    logger.info("Semantic search completed", hits_count=len(hits))
    return hits


# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "MEM-LEAR-049",
    "governance_level": "high",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": ["core.schemas", "memory.substrate_service"],
    "tags": [
        "async",
        "data-models",
        "learning",
        "logging",
        "pydantic",
        "schema",
        "validation",
    ],
    "keywords": ["cursor", "hit", "search", "semantic", "wrapper"],
    "business_value": "Implements SearchHit for semantic search functionality",
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
