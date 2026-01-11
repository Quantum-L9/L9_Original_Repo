"""Health check endpoint."""

from fastapi import APIRouter
from src.db import pool
from src.config import settings

router = APIRouter()


@router.get("/health")
async def health_check():
    db_ok = pool is not None
    db_connected = False
    if db_ok:
        try:
            async with pool.acquire() as conn:
                await conn.fetchval("SELECT 1")
                db_connected = True
        except Exception:
            db_connected = False

    return {
        "status": "healthy" if db_connected else "unhealthy",
        "database": "connected" if db_connected else "disconnected",
        "mcp_version": "2025-03-26",
        "index_type": settings.VECTOR_INDEX_TYPE,
        "compounding_enabled": settings.COMPOUNDING_ENABLED,
        "decay_enabled": settings.DECAY_ENABLED,
    }
