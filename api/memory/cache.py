"""
L9 Memory API - Cache Router (Redis)
Version: 1.0.0

REST API endpoints for Redis cache operations.
Used by cursor_memory_client.py for session context and fast lookups.
"""

# ============================================================================
__dora_meta__ = {
    "component_name": "Cache Router (Redis)",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2026-01-07T22:46:10Z",
    "updated_at": "2026-01-14T15:03:00Z",
    "layer": "operations",
    "domain": "api_gateway",
    "module_name": "cache",
    "type": "router",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [
            "GET /health",
            "GET /get/{key}",
            "POST /set",
            "DELETE /delete/{key}",
            "GET /keys/{pattern}",
            "POST /session/context",
            "GET /session/context/{session_id}",
            "GET /session/list",
            "GET /rate-limit/{key}",
            "POST /rate-limit/{key}/increment",
        ],
        "datasources": ["Redis"],
        "memory_layers": ["working_memory"],
        "imported_by": ["api.server", "mcp_memory.src.mcp_server"],
    },
}
# ============================================================================

import json
from typing import Any

import structlog
from fastapi import APIRouter, Depends, Header, HTTPException, Query
from pydantic import BaseModel

from api.auth import verify_api_key
from api.routes.registry import router_registry

logger = structlog.get_logger(__name__)

router = APIRouter()

# Auto-register with RouterRegistry
router_registry.register(
    router=router,
    prefix="/api/v1/memory/cache",
    tags=["memory-cache", "redis"],
    module_id="memory_cache",
    display_name="Memory Cache API (Redis)",
    dependencies=["redis_client"],
)

# Lazy import Redis client
import asyncio

_redis_client = None
_redis_client_lock = asyncio.Lock()


async def get_redis():
    """Get Redis client singleton (thread-safe)."""
    global _redis_client
    if _redis_client is None:
        async with _redis_client_lock:
            if _redis_client is None:
                try:
                    from runtime.redis_client import get_redis_client

                    _redis_client = await get_redis_client()
                except ImportError:
                    logger.warning("Redis client not available")
                    return None
    return _redis_client


# ============================================================================
# Request/Response Models
# ============================================================================


class CacheSetRequest(BaseModel):
    """Request model for cache set operations."""

    key: str
    value: Any
    ttl: int | None = None  # seconds


class CacheResponse(BaseModel):
    """Standard cache response."""

    success: bool
    data: Any = None
    error: str | None = None


class SessionContextRequest(BaseModel):
    """Request model for session context."""

    session_id: str
    context: dict
    ttl: int = 86400  # 24 hours default


# ============================================================================
# Health & Status
# ============================================================================


@router.get("/health")
async def cache_health(
    authorization: str = Header(None),
    _: bool = Depends(verify_api_key),
):
    """Check Redis connection health."""
    client = await get_redis()
    if client is None or not client.is_available():
        return {
            "status": "unavailable",
            "connected": False,
            "message": "Redis not connected or not configured",
        }
    return {
        "status": "healthy",
        "connected": True,
        "message": "Redis connected",
    }


# ============================================================================
# Generic Cache Operations
# ============================================================================


@router.get("/get/{key}", response_model=CacheResponse)
async def cache_get(
    key: str,
    authorization: str = Header(None),
    _: bool = Depends(verify_api_key),
):
    """Get value from cache."""
    client = await get_redis()
    if client is None or not client.is_available():
        raise HTTPException(status_code=503, detail="Redis not available")

    try:
        value = await client.get(key)
        if value is None:
            return CacheResponse(success=False, error="Key not found")

        # Try to parse as JSON
        try:
            parsed = json.loads(value)
            return CacheResponse(success=True, data=parsed)
        except json.JSONDecodeError:
            return CacheResponse(success=True, data=value)
    except Exception as e:
        logger.error(f"Cache get failed: {e}", exc_info=True)
        return CacheResponse(success=False, error=str(e))


@router.post("/set", response_model=CacheResponse)
async def cache_set(
    request: CacheSetRequest,
    authorization: str = Header(None),
    _: bool = Depends(verify_api_key),
):
    """Set value in cache."""
    client = await get_redis()
    if client is None or not client.is_available():
        raise HTTPException(status_code=503, detail="Redis not available")

    try:
        # Serialize value to JSON if not string
        if isinstance(request.value, str):
            value = request.value
        else:
            value = json.dumps(request.value)

        result = await client.set(request.key, value, ttl=request.ttl)
        return CacheResponse(success=result)
    except Exception as e:
        logger.error(f"Cache set failed: {e}", exc_info=True)
        return CacheResponse(success=False, error=str(e))


@router.delete("/delete/{key}", response_model=CacheResponse)
async def cache_delete(
    key: str,
    authorization: str = Header(None),
    _: bool = Depends(verify_api_key),
):
    """Delete key from cache."""
    client = await get_redis()
    if client is None or not client.is_available():
        raise HTTPException(status_code=503, detail="Redis not available")

    try:
        result = await client.delete(key)
        return CacheResponse(success=result)
    except Exception as e:
        logger.error(f"Cache delete failed: {e}", exc_info=True)
        return CacheResponse(success=False, error=str(e))


@router.get("/keys/{pattern}", response_model=CacheResponse)
async def cache_keys(
    pattern: str,
    authorization: str = Header(None),
    _: bool = Depends(verify_api_key),
):
    """Get keys matching pattern."""
    client = await get_redis()
    if client is None or not client.is_available():
        raise HTTPException(status_code=503, detail="Redis not available")

    try:
        keys = await client.keys(pattern)
        return CacheResponse(success=True, data=keys)
    except Exception as e:
        logger.error(f"Cache keys failed: {e}", exc_info=True)
        return CacheResponse(success=False, error=str(e))


# ============================================================================
# Session Context Operations (Cursor-specific)
# ============================================================================


@router.post("/session/context", response_model=CacheResponse)
async def set_session_context(
    request: SessionContextRequest,
    authorization: str = Header(None),
    _: bool = Depends(verify_api_key),
):
    """
    Store session context for Cursor.

    Used by cursor_memory_client.py for fast session state retrieval.
    """
    client = await get_redis()
    if client is None or not client.is_available():
        raise HTTPException(status_code=503, detail="Redis not available")

    try:
        key = f"cursor:session:{request.session_id}:context"
        value = json.dumps(request.context)
        result = await client.set(key, value, ttl=request.ttl)
        return CacheResponse(success=result, data={"key": key})
    except Exception as e:
        logger.error(f"Set session context failed: {e}", exc_info=True)
        return CacheResponse(success=False, error=str(e))


@router.get("/session/context/{session_id}", response_model=CacheResponse)
async def get_session_context(
    session_id: str,
    authorization: str = Header(None),
    _: bool = Depends(verify_api_key),
):
    """
    Get session context for Cursor.

    Returns fast-access session state from Redis.
    """
    client = await get_redis()
    if client is None or not client.is_available():
        return CacheResponse(
            success=False,
            error="Redis not available",
            data={"fallback": True},
        )

    try:
        key = f"cursor:session:{session_id}:context"
        value = await client.get(key)

        if value is None:
            return CacheResponse(success=False, error="Session context not found")

        context = json.loads(value)
        return CacheResponse(success=True, data=context)
    except Exception as e:
        logger.error(f"Get session context failed: {e}", exc_info=True)
        return CacheResponse(success=False, error=str(e))


@router.get("/session/list", response_model=CacheResponse)
async def list_sessions(
    limit: int = Query(20, ge=1, le=100),
    authorization: str = Header(None),
    _: bool = Depends(verify_api_key),
):
    """
    List recent Cursor sessions.

    Returns session IDs with context stored in Redis.
    """
    client = await get_redis()
    if client is None or not client.is_available():
        return CacheResponse(success=False, error="Redis not available")

    try:
        keys = await client.keys("cursor:session:*:context")

        # Extract session IDs from keys
        sessions = []
        for key in keys[:limit]:
            parts = key.split(":")
            if len(parts) >= 3:
                sessions.append(parts[2])

        return CacheResponse(
            success=True, data={"sessions": sessions, "count": len(sessions)}
        )
    except Exception as e:
        logger.error(f"List sessions failed: {e}", exc_info=True)
        return CacheResponse(success=False, error=str(e))


# ============================================================================
# Rate Limiting (Cursor-specific)
# ============================================================================


@router.get("/rate-limit/{key}")
async def get_rate_limit(
    key: str,
    authorization: str = Header(None),
    _: bool = Depends(verify_api_key),
):
    """Get current rate limit count."""
    client = await get_redis()
    if client is None or not client.is_available():
        return {"key": key, "count": 0, "available": False}

    try:
        count = await client.get_rate_limit(key)
        return {"key": key, "count": count, "available": True}
    except Exception as e:
        logger.error(f"Get rate limit failed: {e}", exc_info=True)
        return {"key": key, "count": 0, "error": str(e)}


@router.post("/rate-limit/{key}/increment")
async def increment_rate_limit(
    key: str,
    ttl: int = Query(60, ge=1, le=3600),
    authorization: str = Header(None),
    _: bool = Depends(verify_api_key),
):
    """Increment rate limit counter."""
    client = await get_redis()
    if client is None or not client.is_available():
        raise HTTPException(status_code=503, detail="Redis not available")

    try:
        count = await client.increment_rate_limit(key, ttl=ttl)
        return {"key": key, "count": count, "ttl": ttl}
    except Exception as e:
        logger.error(f"Increment rate limit failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e)) from e


# ============================================================================
# Task Context (for reasoning traces)
# ============================================================================


@router.post("/task/context/{task_id}", response_model=CacheResponse)
async def set_task_context(
    task_id: str,
    context: dict,
    ttl: int = Query(3600, ge=60, le=86400),
    authorization: str = Header(None),
    _: bool = Depends(verify_api_key),
):
    """Store task context for reasoning continuity."""
    client = await get_redis()
    if client is None or not client.is_available():
        raise HTTPException(status_code=503, detail="Redis not available")

    try:
        result = await client.set_task_context(task_id, context, ttl=ttl)
        return CacheResponse(success=result)
    except Exception as e:
        logger.error(f"Set task context failed: {e}", exc_info=True)
        return CacheResponse(success=False, error=str(e))


@router.get("/task/context/{task_id}", response_model=CacheResponse)
async def get_task_context(
    task_id: str,
    authorization: str = Header(None),
    _: bool = Depends(verify_api_key),
):
    """Get task context for reasoning continuity."""
    client = await get_redis()
    if client is None or not client.is_available():
        return CacheResponse(success=False, error="Redis not available")

    try:
        context = await client.get_task_context(task_id)
        if not context:
            return CacheResponse(success=False, error="Task context not found")
        return CacheResponse(success=True, data=context)
    except Exception as e:
        logger.error(f"Get task context failed: {e}", exc_info=True)
        return CacheResponse(success=False, error=str(e))


# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "API-OPER-012",
    "governance_level": "medium",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": ["api.auth", "runtime.redis_client"],
    "tags": [
        "api",
        "api-gateway",
        "async",
        "auth",
        "cache",
        "caching",
        "endpoint",
        "logging",
        "messaging",
        "operations",
    ],
    "keywords": [
        "(redis)",
        "cache",
        "delete",
        "health",
        "increment",
        "limit",
        "memory",
        "rate",
    ],
    "business_value": "Provides cache components including CacheSetRequest, CacheResponse, SessionContextRequest",
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
