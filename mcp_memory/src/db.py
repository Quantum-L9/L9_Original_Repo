"""
PostgreSQL async client with pgvector support.
"""


import json
from typing import Any

import asyncpg
import structlog

from memory.governance_gate import require_governance_context
from src.config import settings

logger = structlog.get_logger(__name__)
pool: asyncpg.Pool | None = None


async def _init_connection(conn: asyncpg.Connection) -> None:
    """Initialize connection with JSON codec for JSONB columns."""
    await conn.set_type_codec(
        "jsonb", encoder=json.dumps, decoder=json.loads, schema="pg_catalog"
    )
    await conn.set_type_codec(
        "json", encoder=json.dumps, decoder=json.loads, schema="pg_catalog"
    )


async def init_db():
    """
    Initializes the PostgreSQL async connection pool with pgvector support for the database client.



    Raises:
        asyncpg.PostgresError: If connection or extension setup fails.
    """
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
    """Performs cleanup of the PostgreSQL connection pool used in async database operations."""
    global pool
    if pool:
        await pool.close()
        pool = None
        logger.info("Database pool closed")


async def execute(
    query: str,
    *args,
    db_pool: asyncpg.Pool | None = None,
) -> Any:
    """Execute a query. Accepts optional db_pool for dependency injection."""
    _pool = db_pool or pool
    if not _pool:
        raise RuntimeError("Database pool not initialized")
    require_governance_context("mcp_memory.execute")
    async with _pool.acquire() as conn:
        return await conn.execute(query, *args)


async def fetch_one(
    query: str,
    *args,
    db_pool: asyncpg.Pool | None = None,
) -> dict[str, Any] | None:
    """Fetch one row. Accepts optional db_pool for dependency injection."""
    _pool = db_pool or pool
    if not _pool:
        raise RuntimeError("Database pool not initialized")
    require_governance_context("mcp_memory.fetch_one")
    async with _pool.acquire() as conn:
        row = await conn.fetchrow(query, *args)
        return dict(row) if row else None


async def fetch_all(
    query: str,
    *args,
    db_pool: asyncpg.Pool | None = None,
) -> list[dict[str, Any]]:
    """Fetch all rows. Accepts optional db_pool for dependency injection."""
    _pool = db_pool or pool
    if not _pool:
        raise RuntimeError("Database pool not initialized")
    require_governance_context("mcp_memory.fetch_all")
    async with _pool.acquire() as conn:
        rows = await conn.fetch(query, *args)
        return [dict(row) for row in rows]


async def insert_many(
    query: str,
    args_list: list[tuple],
    db_pool: asyncpg.Pool | None = None,
) -> int:
    """Insert many rows. Accepts optional db_pool for dependency injection."""
    _pool = db_pool or pool
    if not _pool:
        raise RuntimeError("Database pool not initialized")
    require_governance_context("mcp_memory.insert_many")
    async with _pool.acquire() as conn:
        result = await conn.executemany(query, args_list)
    return int(result.split()[-1]) if result else 0


# Runtime execution trace - updated automatically on every execution
