from __future__ import annotations


import os

import asyncpg

# Get DSN from environment - NEVER hardcode localhost in Docker!
# Inside containers, use service DNS (l9-postgres:5432)
# Outside containers, use host networking or published ports
MEMORY_DSN = os.getenv(
    "MEMORY_DSN",
    os.getenv(
        "DATABASE_URL", "postgresql://postgres:postgres@l9-postgres:5432/l9_memory"
    ),
)


async def init_db() -> None:
    """Initialize database schema (async, uses asyncpg)."""
    conn = await asyncpg.connect(MEMORY_DSN)
    try:
        await conn.execute("CREATE SCHEMA IF NOT EXISTS memory;")
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS memory.embeddings (
                id SERIAL PRIMARY KEY,
                source TEXT,
                content TEXT,
                vector VECTOR(1536)
            );
        """)
    finally:
        await conn.close()


async def insert_embedding(
    source: str, content: str, vector: list | None = None
) -> None:
    """Insert embedding into database (async, uses asyncpg).

    DEPRECATED: Use MemorySubstrateService.write_packet() instead.
    This function bypasses PacketEnvelope governance.
    """
    # MEMORY_BYPASS_ALLOWED: Legacy-utility-deprecated-pending-removal
    conn = await asyncpg.connect(MEMORY_DSN)
    try:
        await conn.execute(
            """
            INSERT INTO memory.embeddings (source, content, vector)
            VALUES ($1, $2, $3);
            """,
            source,
            content,
            vector,
        )
    finally:
        await conn.close()


# Runtime execution trace - updated automatically on every execution
