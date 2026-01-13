"""
L9 Cursor Semantic Search Wrapper
Version: 1.0.0

Thin async wrapper over existing semanticmemory / pgvector integration,
tailored for Cursor use cases.
"""

from __future__ import annotations

import structlog
from typing import List, Optional
from uuid import UUID
from pydantic import BaseModel, Field

from memory.substrate_service import MemorySubstrateService
from core.schemas.packet_envelope_v2 import SemanticHit, SemanticSearchRequest

logger = structlog.get_logger(__name__)


# =============================================================================
# Models
# =============================================================================


class SearchHit(BaseModel):
    """Search hit result for Cursor."""
    
    packet_id: UUID = Field(..., description="Packet ID")
    similarity_score: float = Field(..., description="Similarity score (0-1)")
    packet_type: Optional[str] = Field(None, description="Packet type")
    scope: Optional[str] = Field(None, description="Scope (developer, global)")
    tags: Optional[List[str]] = Field(None, description="Tags")
    payload: dict = Field(default_factory=dict, description="Packet payload")


# =============================================================================
# Search Function
# =============================================================================


async def semantic_search(
    query: str,
    agent_id: str,
    project_id: str,
    top_k: int = 10,
    substrate_service: Optional[MemorySubstrateService] = None,
) -> List[SearchHit]:
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
        raise ValueError("substrate_service must be provided or initialized via init_service()")
    
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

