"""
PostgreSQL async client with pgvector support.
"""

import asyncpg
import json
import structlog
from typing import List, Dict, Any, Optional
from src.config import settings
from memory.governance_gate import require_governance_context

logger = structlog.get_logger(__name__)
pool: Optional[asyncpg.Pool] = None


async def _init_connection(conn: asyncpg.Connection) -> None:
    """Initialize connection with JSON codec for JSONB columns."""
    await conn.set_type_codec(
        'jsonb',
        encoder=json.dumps,
        decoder=json.loads,
        schema='pg_catalog'
    )
    await conn.set_type_codec(
        'json',
        encoder=json.dumps,
        decoder=json.loads,
        schema='pg_catalog'
    )


async def init_db():
    global pool
    pool = await asyncpg.create_pool(
        dsn=settings.MEMORY_DSN,
        min_size=5,
        max_size=20,
        command_timeout=60,
        init=_init_connection,  # Register JSON codecs on each connection
    )
    await pool.execute("CREATE EXTENSION IF NOT EXISTS vector;")
    logger.info("Database pool initialized with JSON codecs")


async def close_db():
    global pool
    if pool:
        await pool.close()
        pool = None
        logger.info("Database pool closed")


async def execute(query: str, *args) -> Any:
    if not pool:
        raise RuntimeError("Database pool not initialized")
    require_governance_context("mcp_memory.execute")
    async with pool.acquire() as conn:
        return await conn.execute(query, *args)


async def fetch_one(query: str, *args) -> Optional[Dict[str, Any]]:
    if not pool:
        raise RuntimeError("Database pool not initialized")
    require_governance_context("mcp_memory.fetch_one")
    async with pool.acquire() as conn:
        row = await conn.fetchrow(query, *args)
        return dict(row) if row else None


async def fetch_all(query: str, *args) -> List[Dict[str, Any]]:
    if not pool:
        raise RuntimeError("Database pool not initialized")
    require_governance_context("mcp_memory.fetch_all")
    async with pool.acquire() as conn:
        rows = await conn.fetch(query, *args)
        return [dict(row) for row in rows]


async def insert_many(query: str, args_list: List[tuple]) -> int:
    if not pool:
        raise RuntimeError("Database pool not initialized")
    require_governance_context("mcp_memory.insert_many")
    async with pool.acquire() as conn:
        result = await conn.executemany(query, args_list)
    count = int(result.split()[-1]) if result else 0
    return count
