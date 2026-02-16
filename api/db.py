from __future__ import annotations

# ============================================================================
__dora_meta__ = {
    "component_name": "Db",
    "module_version": "2.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2025-12-09T01:02:49Z",
    "updated_at": "2026-01-28T12:00:00Z",
    "layer": "operations",
    "domain": "api_gateway",
    "module_name": "db",
    "type": "utility",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": ["PostgreSQL"],
        "memory_layers": ["semantic_memory"],
        "imported_by": ["api.server", "api.server_memory"],
    },
}
# ============================================================================

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


# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "API-OPER-001",
    "governance_level": "medium",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": ["api-gateway", "operations", "utility"],
    "keywords": ["embedding", "insert"],
    "business_value": "Utility module for db",
    "last_modified": "2026-01-07T13:35:57Z",
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
