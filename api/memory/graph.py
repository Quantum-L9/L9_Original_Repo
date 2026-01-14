"""
L9 Memory API - Graph Router (Neo4j)
Version: 1.0.0

REST API endpoints for Neo4j graph operations.
Used by cursor_memory_client.py for graph-enhanced context.
"""

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from pydantic import BaseModel
from api.auth import verify_api_key
from typing import Optional, Any
import structlog

logger = structlog.get_logger(__name__)

router = APIRouter()

# Lazy import Neo4j client
_neo4j_client = None


async def get_neo4j():
    """Get Neo4j client singleton."""
    global _neo4j_client
    if _neo4j_client is None:
        try:
            from memory.graph_client import get_neo4j_client
            _neo4j_client = await get_neo4j_client()
        except ImportError:
            logger.warning("Neo4j client not available")
            return None
    return _neo4j_client


# ============================================================================
# Request/Response Models
# ============================================================================


class EntityRequest(BaseModel):
    """Request model for entity operations."""
    entity_type: str
    entity_id: str
    properties: dict = {}


class RelationshipRequest(BaseModel):
    """Request model for relationship operations."""
    from_type: str
    from_id: str
    to_type: str
    to_id: str
    rel_type: str
    properties: Optional[dict] = None


class QueryRequest(BaseModel):
    """Request model for Cypher queries."""
    query: str
    parameters: Optional[dict] = None


class GraphResponse(BaseModel):
    """Standard graph response."""
    success: bool
    data: Any = None
    error: Optional[str] = None


# ============================================================================
# Health & Status
# ============================================================================


@router.get("/health")
async def graph_health(
    authorization: str = Header(None),
    _: bool = Depends(verify_api_key),
):
    """Check Neo4j connection health."""
    client = await get_neo4j()
    if client is None or not client.is_available():
        return {
            "status": "unavailable",
            "connected": False,
            "message": "Neo4j not connected or not configured",
        }
    return {
        "status": "healthy",
        "connected": True,
        "message": "Neo4j connected",
    }


# ============================================================================
# Entity Operations
# ============================================================================


@router.post("/entity", response_model=GraphResponse)
async def create_entity(
    request: EntityRequest,
    authorization: str = Header(None),
    _: bool = Depends(verify_api_key),
):
    """Create or merge an entity node."""
    client = await get_neo4j()
    if client is None or not client.is_available():
        raise HTTPException(status_code=503, detail="Neo4j not available")
    
    try:
        result = await client.create_entity(
            entity_type=request.entity_type,
            entity_id=request.entity_id,
            properties=request.properties,
        )
        return GraphResponse(success=True, data={"entity_id": result})
    except Exception as e:
        logger.error(f"Create entity failed: {e}", exc_info=True)
        return GraphResponse(success=False, error=str(e))


@router.get("/entity/{entity_type}/{entity_id}", response_model=GraphResponse)
async def get_entity(
    entity_type: str,
    entity_id: str,
    authorization: str = Header(None),
    _: bool = Depends(verify_api_key),
):
    """Get an entity by type and ID."""
    client = await get_neo4j()
    if client is None or not client.is_available():
        raise HTTPException(status_code=503, detail="Neo4j not available")
    
    try:
        result = await client.get_entity(entity_type, entity_id)
        if result is None:
            return GraphResponse(success=False, error="Entity not found")
        return GraphResponse(success=True, data=result)
    except Exception as e:
        logger.error(f"Get entity failed: {e}", exc_info=True)
        return GraphResponse(success=False, error=str(e))


@router.delete("/entity/{entity_type}/{entity_id}", response_model=GraphResponse)
async def delete_entity(
    entity_type: str,
    entity_id: str,
    authorization: str = Header(None),
    _: bool = Depends(verify_api_key),
):
    """Delete an entity and its relationships."""
    client = await get_neo4j()
    if client is None or not client.is_available():
        raise HTTPException(status_code=503, detail="Neo4j not available")
    
    try:
        result = await client.delete_entity(entity_type, entity_id)
        return GraphResponse(success=result)
    except Exception as e:
        logger.error(f"Delete entity failed: {e}", exc_info=True)
        return GraphResponse(success=False, error=str(e))


# ============================================================================
# Relationship Operations
# ============================================================================


@router.post("/relationship", response_model=GraphResponse)
async def create_relationship(
    request: RelationshipRequest,
    authorization: str = Header(None),
    _: bool = Depends(verify_api_key),
):
    """Create a relationship between two entities."""
    client = await get_neo4j()
    if client is None or not client.is_available():
        raise HTTPException(status_code=503, detail="Neo4j not available")
    
    try:
        result = await client.create_relationship(
            from_type=request.from_type,
            from_id=request.from_id,
            to_type=request.to_type,
            to_id=request.to_id,
            rel_type=request.rel_type,
            properties=request.properties,
        )
        return GraphResponse(success=result)
    except Exception as e:
        logger.error(f"Create relationship failed: {e}", exc_info=True)
        return GraphResponse(success=False, error=str(e))


@router.get("/relationships/{entity_type}/{entity_id}", response_model=GraphResponse)
async def get_relationships(
    entity_type: str,
    entity_id: str,
    rel_type: Optional[str] = Query(None),
    direction: str = Query("both", pattern="^(outgoing|incoming|both)$"),
    authorization: str = Header(None),
    _: bool = Depends(verify_api_key),
):
    """Get relationships for an entity."""
    client = await get_neo4j()
    if client is None or not client.is_available():
        raise HTTPException(status_code=503, detail="Neo4j not available")
    
    try:
        result = await client.get_relationships(
            entity_type=entity_type,
            entity_id=entity_id,
            rel_type=rel_type,
            direction=direction,
        )
        return GraphResponse(success=True, data=result)
    except Exception as e:
        logger.error(f"Get relationships failed: {e}", exc_info=True)
        return GraphResponse(success=False, error=str(e))


# ============================================================================
# Query Operations
# ============================================================================


@router.post("/query", response_model=GraphResponse)
async def run_query(
    request: QueryRequest,
    authorization: str = Header(None),
    _: bool = Depends(verify_api_key),
):
    """Run a custom Cypher query (read-only recommended)."""
    client = await get_neo4j()
    if client is None or not client.is_available():
        raise HTTPException(status_code=503, detail="Neo4j not available")
    
    try:
        result = await client.run_query(
            query=request.query,
            parameters=request.parameters,
        )
        return GraphResponse(success=True, data=result)
    except Exception as e:
        logger.error(f"Query failed: {e}", exc_info=True)
        return GraphResponse(success=False, error=str(e))


# ============================================================================
# Cursor-Specific Endpoints (Optimized for cursor_memory_client.py)
# ============================================================================


@router.get("/context/{domain}")
async def get_domain_context(
    domain: str,
    limit: int = Query(10, ge=1, le=100),
    authorization: str = Header(None),
    _: bool = Depends(verify_api_key),
):
    """
    Get graph context for a domain (memory, agents, tools, etc.).
    
    Returns entities and relationships relevant to the domain.
    Used by cursor_memory_client.py for graph-enhanced context injection.
    """
    client = await get_neo4j()
    if client is None or not client.is_available():
        return {
            "domain": domain,
            "available": False,
            "entities": [],
            "relationships": [],
            "message": "Neo4j not available",
        }
    
    try:
        # Query for domain-related entities
        query = """
        MATCH (n)
        WHERE n.domain = $domain OR n.name CONTAINS $domain OR labels(n)[0] CONTAINS $domain
        RETURN n, labels(n) as labels
        LIMIT $limit
        """
        entities = await client.run_query(query, {"domain": domain, "limit": limit})
        
        # Query for relationships involving domain entities
        rel_query = """
        MATCH (a)-[r]->(b)
        WHERE a.domain = $domain OR b.domain = $domain
        RETURN type(r) as rel_type, a.id as from_id, b.id as to_id
        LIMIT $limit
        """
        relationships = await client.run_query(rel_query, {"domain": domain, "limit": limit})
        
        return {
            "domain": domain,
            "available": True,
            "entities": entities,
            "relationships": relationships,
            "count": len(entities),
        }
    except Exception as e:
        logger.error(f"Get domain context failed: {e}", exc_info=True)
        return {
            "domain": domain,
            "available": False,
            "entities": [],
            "relationships": [],
            "error": str(e),
        }


@router.get("/session-graph/{session_id}")
async def get_session_graph(
    session_id: str,
    authorization: str = Header(None),
    _: bool = Depends(verify_api_key),
):
    """
    Get graph of entities related to a session.
    
    Used for session-to-session persistence via graph relationships.
    """
    client = await get_neo4j()
    if client is None or not client.is_available():
        return {
            "session_id": session_id,
            "available": False,
            "nodes": [],
            "edges": [],
        }
    
    try:
        # Find session and related entities
        query = """
        MATCH (s:Session {id: $session_id})-[r]-(related)
        RETURN s, r, related
        LIMIT 50
        """
        result = await client.run_query(query, {"session_id": session_id})
        
        return {
            "session_id": session_id,
            "available": True,
            "result": result,
        }
    except Exception as e:
        logger.error(f"Get session graph failed: {e}", exc_info=True)
        return {
            "session_id": session_id,
            "available": False,
            "error": str(e),
        }
