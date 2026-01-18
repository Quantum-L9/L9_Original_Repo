"""
PostgreSQL async client with pgvector support.
"""

# ============================================================================
__dora_meta__ = {
    "component_name": "Db",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2026-01-11T18:13:39Z",
    "updated_at": "2026-01-17T23:47:56Z",
    "layer": "integration",
    "domain": "mcp_integration",
    "module_name": "db",
    "type": "service",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": ["PostgreSQL"],
        "memory_layers": ["semantic_memory"],
        "imported_by": [],
    },
}
# ============================================================================

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
        "jsonb", encoder=json.dumps, decoder=json.loads, schema="pg_catalog"
    )
    await conn.set_type_codec(
        "json", encoder=json.dumps, decoder=json.loads, schema="pg_catalog"
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

# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "MCP-INTE-001",
    "governance_level": "medium",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": ["memory.governance_gate"],
    "tags": ["async", "integration", "logging", "mcp-integration", "postgres", "serialization", "service"],
    "keywords": ["all", "close", "execute", "fetch", "insert", "many", "one"],
    "business_value": "Utility module for db",
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
