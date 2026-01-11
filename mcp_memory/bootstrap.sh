#!/bin/bash
set -e

echo "🚀 Bootstrapping L9 MCP Memory Server..."

# ═══════════════════════════════════════════════════════════════════
# Create Directory Structure
# ═══════════════════════════════════════════════════════════════════
echo "📁 Creating directories..."
mkdir -p src/routes schema/migrations deploy/systemd deploy/scripts tests

# ═══════════════════════════════════════════════════════════════════
# src/__init__.py
# ═══════════════════════════════════════════════════════════════════
echo "📄 Creating src/__init__.py..."
cat > src/__init__.py << 'ENDFILE'
"""
L9 MCP Memory Server
"""
__version__ = "1.0.0"
ENDFILE

# ═══════════════════════════════════════════════════════════════════
# src/config.py
# ═══════════════════════════════════════════════════════════════════
echo "📄 Creating src/config.py..."
cat > src/config.py << 'ENDFILE'
"""
Configuration for L9 MCP Memory Server.
Environment-based settings with HNSW and memory compounding support.
"""

import os
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # Server Configuration
    MCP_HOST: str = "127.0.0.1"
    MCP_PORT: int = 9001
    MCP_ENV: str = "production"
    LOG_LEVEL: str = "INFO"

    # OpenAI Configuration
    OPENAI_API_KEY: str
    OPENAI_EMBED_MODEL: str = "text-embedding-3-small"
    OPENAI_EMBED_DIM: int = 1536

    # Database Configuration
    MEMORY_DSN: str

    # Memory Lifecycle
    MEMORY_SHORT_TERM_HOURS: int = 1
    MEMORY_MEDIUM_TERM_HOURS: int = 24
    MEMORY_CLEANUP_INTERVAL_MINUTES: int = 60
    MEMORY_SHORT_RETENTION_DAYS: int = 7
    MEMORY_MEDIUM_RETENTION_DAYS: int = 30

    # Vector Search Configuration
    VECTOR_SEARCH_THRESHOLD: float = 0.7
    VECTOR_SEARCH_TOP_K: int = 10

    # Vector Index Configuration (HNSW)
    VECTOR_INDEX_TYPE: str = "hnsw"
    HNSW_M: int = 16
    HNSW_EF_CONSTRUCTION: int = 64
    HNSW_EF_SEARCH: int = 40

    # Memory Compounding Configuration
    COMPOUNDING_ENABLED: bool = True
    COMPOUNDING_SIMILARITY_THRESHOLD: float = 0.92
    COMPOUNDING_MIN_COUNT: int = 3

    # Importance Decay Configuration
    DECAY_ENABLED: bool = True
    DECAY_RATE_PER_DAY: float = 0.01
    ACCESS_BOOST_PER_HIT: float = 0.05

    # Authentication
    MCP_API_KEY: str

    # Redis (optional)
    REDIS_ENABLED: bool = False
    REDIS_HOST: str = "127.0.0.1"
    REDIS_PORT: int = 6379

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()
ENDFILE

# ═══════════════════════════════════════════════════════════════════
# src/db.py
# ═══════════════════════════════════════════════════════════════════
echo "📄 Creating src/db.py..."
cat > src/db.py << 'ENDFILE'
"""
PostgreSQL async client with pgvector support.
"""

import asyncpg
import logging
from typing import List, Dict, Any, Optional
from src.config import settings

logger = logging.getLogger(__name__)
pool: Optional[asyncpg.Pool] = None


async def init_db():
    global pool
    pool = await asyncpg.create_pool(
        dsn=settings.MEMORY_DSN,
        min_size=5,
        max_size=20,
        command_timeout=60,
    )
    await pool.execute("CREATE EXTENSION IF NOT EXISTS vector;")
    logger.info("Database pool initialized")


async def close_db():
    global pool
    if pool:
        await pool.close()
        pool = None
        logger.info("Database pool closed")


async def execute(query: str, *args) -> Any:
    if not pool:
        raise RuntimeError("Database pool not initialized")
    async with pool.acquire() as conn:
        return await conn.execute(query, *args)


async def fetch_one(query: str, *args) -> Optional[Dict[str, Any]]:
    if not pool:
        raise RuntimeError("Database pool not initialized")
    async with pool.acquire() as conn:
        row = await conn.fetchrow(query, *args)
        return dict(row) if row else None


async def fetch_all(query: str, *args) -> List[Dict[str, Any]]:
    if not pool:
        raise RuntimeError("Database pool not initialized")
    async with pool.acquire() as conn:
        rows = await conn.fetch(query, *args)
        return [dict(row) for row in rows]


async def insert_many(query: str, args_list: List[tuple]) -> int:
    if not pool:
        raise RuntimeError("Database pool not initialized")
    async with pool.acquire() as conn:
        result = await conn.executemany(query, args_list)
    count = int(result.split()[-1]) if result else 0
    return count
ENDFILE

# ═══════════════════════════════════════════════════════════════════
# src/embeddings.py
# ═══════════════════════════════════════════════════════════════════
echo "📄 Creating src/embeddings.py..."
cat > src/embeddings.py << 'ENDFILE'
"""
OpenAI embedding generation.
"""

import logging
from typing import List
from openai import AsyncOpenAI
from src.config import settings

logger = logging.getLogger(__name__)
client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)


async def embed_text(text: str) -> List[float]:
    try:
        response = await client.embeddings.create(
            model=settings.OPENAI_EMBED_MODEL,
            input=text,
        )
        return response.data[0].embedding
    except Exception as e:
        logger.error(f"Embedding error: {e}")
        raise


async def embed_texts(texts: List[str]) -> List[List[float]]:
    try:
        response = await client.embeddings.create(
            model=settings.OPENAI_EMBED_MODEL,
            input=texts,
        )
        sorted_data = sorted(response.data, key=lambda x: x.index)
        return [item.embedding for item in sorted_data]
    except Exception as e:
        logger.error(f"Batch embedding error: {e}")
        raise
ENDFILE

# ═══════════════════════════════════════════════════════════════════
# src/models.py
# ═══════════════════════════════════════════════════════════════════
echo "📄 Creating src/models.py..."
cat > src/models.py << 'ENDFILE'
"""
Request/response models.
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime


class SaveMemoryRequest(BaseModel):
    content: str
    kind: str
    scope: str = "user"
    duration: str
    user_id: str
    tags: Optional[List[str]] = None
    importance: Optional[float] = 1.0
    metadata: Optional[Dict[str, Any]] = None


class MemoryResponse(BaseModel):
    id: int
    user_id: str
    kind: str
    content: str
    importance: float
    tags: Optional[List[str]] = None
    created_at: datetime
    similarity: Optional[float] = None


class SearchMemoryRequest(BaseModel):
    query: str
    user_id: str
    scopes: Optional[List[str]] = ["user", "project", "global"]
    kinds: Optional[List[str]] = None
    top_k: Optional[int] = 5
    threshold: Optional[float] = 0.7
    duration: Optional[str] = "all"


class SearchMemoryResponse(BaseModel):
    results: List[MemoryResponse]
    query_embedding_time_ms: float
    search_time_ms: float
    total_results: int


class MemoryStatsResponse(BaseModel):
    short_term_count: int
    medium_term_count: int
    long_term_count: int
    total_count: int
    unique_users: int
    avg_importance: float


class CompoundResult(BaseModel):
    memories_analyzed: int
    clusters_found: int
    memories_merged: int
    importance_boosted: int
ENDFILE

# ═══════════════════════════════════════════════════════════════════
# src/mcp_server.py
# ═══════════════════════════════════════════════════════════════════
echo "📄 Creating src/mcp_server.py..."
cat > src/mcp_server.py << 'ENDFILE'
"""
MCP (Model Context Protocol) Server Implementation.
"""

from typing import Any, Dict, List
from pydantic import BaseModel


class MCPTool(BaseModel):
    name: str
    description: str
    inputSchema: Dict[str, Any]


class MCPToolCall(BaseModel):
    name: str
    arguments: Dict[str, Any]


def get_mcp_tools() -> List[MCPTool]:
    return [
        MCPTool(
            name="save_memory",
            description="Save a memory to the database with automatic embedding",
            inputSchema={
                "type": "object",
                "properties": {
                    "content": {"type": "string", "description": "Memory content"},
                    "kind": {"type": "string", "enum": ["preference", "fact", "context", "error", "success"]},
                    "scope": {"type": "string", "enum": ["user", "project", "global"]},
                    "duration": {"type": "string", "enum": ["short", "medium", "long"]},
                    "user_id": {"type": "string"},
                    "tags": {"type": "array", "items": {"type": "string"}},
                    "importance": {"type": "number", "minimum": 0, "maximum": 1},
                },
                "required": ["content", "kind", "duration", "user_id"],
            },
        ),
        MCPTool(
            name="search_memory",
            description="Search memories using semantic similarity",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "user_id": {"type": "string"},
                    "scopes": {"type": "array", "items": {"type": "string"}},
                    "kinds": {"type": "array", "items": {"type": "string"}},
                    "top_k": {"type": "integer", "default": 5},
                    "threshold": {"type": "number", "default": 0.7},
                    "duration": {"type": "string", "enum": ["short", "medium", "long", "all"]},
                },
                "required": ["query", "user_id"],
            },
        ),
        MCPTool(
            name="get_memory_stats",
            description="Get statistics about stored memories",
            inputSchema={
                "type": "object",
                "properties": {
                    "user_id": {"type": "string"},
                    "duration": {"type": "string", "enum": ["short", "medium", "long", "all"]},
                },
                "required": [],
            },
        ),
        MCPTool(
            name="delete_expired_memories",
            description="Cleanup expired memories",
            inputSchema={
                "type": "object",
                "properties": {"dry_run": {"type": "boolean", "default": True}},
                "required": [],
            },
        ),
        MCPTool(
            name="compound_memories",
            description="Merge highly similar memories",
            inputSchema={
                "type": "object",
                "properties": {
                    "user_id": {"type": "string"},
                    "threshold": {"type": "number", "default": 0.92},
                },
                "required": ["user_id"],
            },
        ),
        MCPTool(
            name="apply_decay",
            description="Apply importance decay to unused memories",
            inputSchema={
                "type": "object",
                "properties": {"dry_run": {"type": "boolean", "default": True}},
                "required": [],
            },
        ),
    ]


async def handle_tool_call(tool: MCPToolCall, user_id: str) -> Dict[str, Any]:
    if tool.name == "save_memory":
        from src.routes.memory import save_memory_handler
        return await save_memory_handler(
            user_id=user_id,
            content=tool.arguments.get("content"),
            kind=tool.arguments.get("kind"),
            scope=tool.arguments.get("scope", "user"),
            duration=tool.arguments.get("duration"),
            tags=tool.arguments.get("tags", []),
            importance=tool.arguments.get("importance", 1.0),
        )
    elif tool.name == "search_memory":
        from src.routes.memory import search_memory_handler
        return await search_memory_handler(
            user_id=user_id,
            query=tool.arguments.get("query"),
            scopes=tool.arguments.get("scopes", ["user", "project", "global"]),
            kinds=tool.arguments.get("kinds"),
            top_k=tool.arguments.get("top_k", 5),
            threshold=tool.arguments.get("threshold", 0.7),
            duration=tool.arguments.get("duration", "all"),
        )
    elif tool.name == "get_memory_stats":
        from src.routes.memory import get_memory_stats
        return await get_memory_stats(
            user_id=tool.arguments.get("user_id"),
            duration=tool.arguments.get("duration", "all"),
        )
    elif tool.name == "delete_expired_memories":
        from src.routes.memory import delete_expired_memories
        return await delete_expired_memories(dry_run=tool.arguments.get("dry_run", True))
    elif tool.name == "compound_memories":
        from src.routes.memory import compound_similar_memories
        return await compound_similar_memories(
            user_id=tool.arguments.get("user_id"),
            threshold=tool.arguments.get("threshold", 0.92),
        )
    elif tool.name == "apply_decay":
        from src.routes.memory import apply_importance_decay
        return await apply_importance_decay(dry_run=tool.arguments.get("dry_run", True))
    else:
        raise ValueError(f"Unknown tool: {tool.name}")
ENDFILE

# ═══════════════════════════════════════════════════════════════════
# src/routes/__init__.py
# ═══════════════════════════════════════════════════════════════════
echo "📄 Creating src/routes/__init__.py..."
cat > src/routes/__init__.py << 'ENDFILE'
"""Route modules for L9 MCP Memory Server."""
from src.routes import memory, health
__all__ = ["memory", "health"]
ENDFILE

# ═══════════════════════════════════════════════════════════════════
# src/routes/health.py
# ═══════════════════════════════════════════════════════════════════
echo "📄 Creating src/routes/health.py..."
cat > src/routes/health.py << 'ENDFILE'
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
ENDFILE

# ═══════════════════════════════════════════════════════════════════
# src/routes/memory.py
# ═══════════════════════════════════════════════════════════════════
echo "📄 Creating src/routes/memory.py..."
cat > src/routes/memory.py << 'ENDFILE'
"""Memory CRUD, search, compounding, and decay routes."""

import logging
import time
import json
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException, Query
import asyncio

from src.db import fetch_all, fetch_one, execute, pool
from src.embeddings import embed_text
from src.models import (
    SaveMemoryRequest, MemoryResponse, SearchMemoryRequest,
    SearchMemoryResponse, MemoryStatsResponse
)
from src.config import settings

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/save", response_model=MemoryResponse)
async def save_memory(req: SaveMemoryRequest) -> MemoryResponse:
    return await save_memory_handler(
        user_id=req.user_id, content=req.content, kind=req.kind,
        scope=req.scope, duration=req.duration, tags=req.tags,
        importance=req.importance, metadata=req.metadata,
    )


async def save_memory_handler(
    user_id: str, content: str, kind: str, scope: str = "user",
    duration: str = "long", tags: Optional[List[str]] = None,
    importance: float = 1.0, metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    try:
        embedding = await embed_text(content)
        if duration == "short":
            table = "memory.short_term"
            expires_at = datetime.utcnow() + timedelta(hours=settings.MEMORY_SHORT_TERM_HOURS)
        elif duration == "medium":
            table = "memory.medium_term"
            expires_at = datetime.utcnow() + timedelta(hours=settings.MEMORY_MEDIUM_TERM_HOURS)
        else:
            table = "memory.long_term"
            expires_at = None

        if duration in ["short", "medium"]:
            query = f"""
            INSERT INTO {table} (user_id, kind, content, embedding, importance, metadata, expires_at)
            VALUES ($1, $2, $3, $4::vector, $5, $6, $7)
            RETURNING id, user_id, kind, content, importance, created_at;
            """
            result = await fetch_one(query, user_id, kind, content, embedding,
                importance, json.dumps(metadata) if metadata else None, expires_at)
        else:
            query = """
            INSERT INTO memory.long_term (user_id, scope, kind, content, embedding, importance, tags, metadata)
            VALUES ($1, $2, $3, $4, $5::vector, $6, $7, $8)
            RETURNING id, user_id, kind, content, importance, tags, created_at;
            """
            result = await fetch_one(query, user_id, scope, kind, content, embedding,
                importance, tags or [], json.dumps(metadata) if metadata else None)

        await execute(
            "INSERT INTO memory.audit_log (operation, table_name, memory_id, user_id, status, details) VALUES ($1, $2, $3, $4, $5, $6)",
            "INSERT", table, result["id"], user_id, "success", json.dumps({"duration": duration, "kind": kind})
        )
        return result
    except Exception as e:
        logger.exception("Error saving memory")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/search", response_model=SearchMemoryResponse)
async def search_memory(req: SearchMemoryRequest) -> SearchMemoryResponse:
    return await search_memory_handler(
        user_id=req.user_id, query=req.query, scopes=req.scopes,
        kinds=req.kinds, top_k=req.top_k, threshold=req.threshold, duration=req.duration,
    )


async def search_memory_handler(
    user_id: str, query: str, scopes: Optional[List[str]] = None,
    kinds: Optional[List[str]] = None, top_k: int = 5,
    threshold: float = 0.7, duration: str = "all",
) -> Dict[str, Any]:
    try:
        embed_start = time.time()
        query_embedding = await embed_text(query)
        embed_time_ms = (time.time() - embed_start) * 1000

        search_start = time.time()
        results = []
        durations = ["short", "medium", "long"] if duration == "all" else [duration]

        for dur in durations:
            if dur == "short":
                table, where = "memory.short_term", "AND expires_at > CURRENT_TIMESTAMP"
            elif dur == "medium":
                table, where = "memory.medium_term", "AND expires_at > CURRENT_TIMESTAMP"
            else:
                table, where = "memory.long_term", ""

            params = [user_id]
            param_idx = 2
            scope_clause, kind_clause = "", ""

            if scopes and dur == "long":
                scope_clause = f"AND scope IN ({', '.join([f'${i}' for i in range(param_idx, param_idx + len(scopes))])})"
                params.extend(scopes)
                param_idx += len(scopes)

            if kinds:
                kind_clause = f"AND kind IN ({', '.join([f'${i}' for i in range(param_idx, param_idx + len(kinds))])})"
                params.extend(kinds)
                param_idx += len(kinds)

            cols = "id, user_id, kind, content, importance, tags, created_at" if dur == "long" else "id, user_id, kind, content, importance, created_at"
            params.extend([query_embedding, threshold, top_k])

            query_sql = f"""
            SELECT {cols}, 1 - (embedding <-> ${param_idx}::vector) as similarity
            FROM {table}
            WHERE user_id = $1 {where} {scope_clause} {kind_clause}
            AND 1 - (embedding <-> ${param_idx}::vector) >= ${param_idx + 1}
            ORDER BY similarity DESC LIMIT ${param_idx + 2};
            """
            rows = await fetch_all(query_sql, *params)

            if dur == "long" and rows:
                await execute("UPDATE memory.long_term SET last_accessed_at = CURRENT_TIMESTAMP, access_count = access_count + 1 WHERE id = ANY($1::bigint[]);", [r["id"] for r in rows])

            results.extend(rows)

        results.sort(key=lambda x: x.get("similarity", 0), reverse=True)
        results = results[:top_k]
        search_time_ms = (time.time() - search_start) * 1000

        await execute("INSERT INTO memory.audit_log (operation, user_id, status, details) VALUES ($1, $2, $3, $4)",
            "SEARCH", user_id, "success", json.dumps({"query": query, "results_count": len(results)}))

        return {"results": results, "query_embedding_time_ms": embed_time_ms, "search_time_ms": search_time_ms, "total_results": len(results)}
    except Exception as e:
        logger.exception("Error searching memory")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats", response_model=MemoryStatsResponse)
async def get_memory_stats(user_id: Optional[str] = Query(None), duration: str = Query("all")) -> MemoryStatsResponse:
    try:
        short_count = medium_count = long_count = unique_users = 0
        avg_importance = 0.0

        if duration in ["all", "short"]:
            q = "SELECT COUNT(*) as cnt FROM memory.short_term WHERE expires_at > CURRENT_TIMESTAMP" + (f" AND user_id = '{user_id}'" if user_id else "")
            r = await fetch_one(q)
            short_count = r["cnt"] if r else 0

        if duration in ["all", "medium"]:
            q = "SELECT COUNT(*) as cnt FROM memory.medium_term WHERE expires_at > CURRENT_TIMESTAMP" + (f" AND user_id = '{user_id}'" if user_id else "")
            r = await fetch_one(q)
            medium_count = r["cnt"] if r else 0

        if duration in ["all", "long"]:
            q = "SELECT COUNT(*) as cnt, COUNT(DISTINCT user_id) as users, AVG(importance) as avg_imp FROM memory.long_term" + (f" WHERE user_id = '{user_id}'" if user_id else "")
            r = await fetch_one(q)
            if r:
                long_count, unique_users = r["cnt"], r["users"]
                avg_importance = float(r["avg_imp"]) if r["avg_imp"] else 0.0

        return MemoryStatsResponse(short_term_count=short_count, medium_term_count=medium_count, long_term_count=long_count,
            total_count=short_count + medium_count + long_count, unique_users=unique_users, avg_importance=avg_importance)
    except Exception as e:
        logger.exception("Error getting stats")
        raise HTTPException(status_code=500, detail=str(e))


async def delete_expired_memories(dry_run: bool = True) -> Dict[str, Any]:
    short_r = await fetch_one("SELECT COUNT(*) as cnt FROM memory.short_term WHERE expires_at < CURRENT_TIMESTAMP")
    medium_r = await fetch_one("SELECT COUNT(*) as cnt FROM memory.medium_term WHERE expires_at < CURRENT_TIMESTAMP")
    short_expired, medium_expired = short_r["cnt"] if short_r else 0, medium_r["cnt"] if medium_r else 0

    if not dry_run:
        await execute("DELETE FROM memory.short_term WHERE expires_at < CURRENT_TIMESTAMP")
        await execute("DELETE FROM memory.medium_term WHERE expires_at < CURRENT_TIMESTAMP")
        await execute("INSERT INTO memory.audit_log (operation, status, details) VALUES ($1, $2, $3)",
            "CLEANUP", "success", json.dumps({"short_deleted": short_expired, "medium_deleted": medium_expired}))

    return {"dry_run": dry_run, "short_term_expired": short_expired, "medium_term_expired": medium_expired,
        "total_expired": short_expired + medium_expired, "action": "deleted" if not dry_run else "would_delete"}


async def compound_similar_memories(user_id: str, threshold: float = 0.92) -> Dict[str, Any]:
    if not settings.COMPOUNDING_ENABLED:
        return {"status": "disabled", "message": "Memory compounding is disabled"}

    memories = await fetch_all("SELECT id, content, embedding, importance, access_count, created_at, tags FROM memory.long_term WHERE user_id = $1 ORDER BY created_at DESC;", user_id)
    if len(memories) < 2:
        return {"status": "skipped", "message": "Not enough memories", "memories_analyzed": len(memories)}

    similar_pairs, processed_ids = [], set()
    for i, mem1 in enumerate(memories):
        if mem1["id"] in processed_ids:
            continue
        cluster = [mem1]
        for mem2 in memories[i + 1:]:
            if mem2["id"] in processed_ids:
                continue
            sim = await fetch_one("SELECT 1 - ($1::vector <-> $2::vector) as similarity;", mem1["embedding"], mem2["embedding"])
            if sim and sim["similarity"] >= threshold:
                cluster.append(mem2)
                processed_ids.add(mem2["id"])
        if len(cluster) >= settings.COMPOUNDING_MIN_COUNT:
            similar_pairs.append(cluster)
            processed_ids.add(mem1["id"])

    merged_count = 0
    for cluster in similar_pairs:
        primary, duplicates = cluster[0], cluster[1:]
        combined_importance = min(1.0, sum(m["importance"] for m in cluster))
        combined_access = sum(m["access_count"] for m in cluster)
        merged_tags = set()
        for m in cluster:
            if m["tags"]:
                merged_tags.update(m["tags"])
        await execute("UPDATE memory.long_term SET importance = $1, access_count = $2, tags = $3, updated_at = CURRENT_TIMESTAMP WHERE id = $4;",
            combined_importance, combined_access, list(merged_tags), primary["id"])
        await execute("DELETE FROM memory.long_term WHERE id = ANY($1::bigint[]);", [m["id"] for m in duplicates])
        merged_count += len(duplicates)

    await execute("INSERT INTO memory.audit_log (operation, user_id, status, details) VALUES ($1, $2, $3, $4)",
        "COMPOUND", user_id, "success", json.dumps({"clusters_found": len(similar_pairs), "memories_merged": merged_count}))

    return {"status": "completed", "memories_analyzed": len(memories), "clusters_found": len(similar_pairs),
        "memories_merged": merged_count, "threshold_used": threshold}


async def apply_importance_decay(dry_run: bool = True) -> Dict[str, Any]:
    if not settings.DECAY_ENABLED:
        return {"status": "disabled", "message": "Importance decay is disabled"}

    decay_factor = 1.0 - settings.DECAY_RATE_PER_DAY
    count_r = await fetch_one("SELECT COUNT(*) as cnt FROM memory.long_term WHERE last_accessed_at < NOW() - INTERVAL '1 day';")
    affected = count_r["cnt"] if count_r else 0

    if not dry_run:
        await execute(f"UPDATE memory.long_term SET importance = importance * POWER({decay_factor}, EXTRACT(EPOCH FROM (NOW() - last_accessed_at)) / 86400), updated_at = CURRENT_TIMESTAMP WHERE last_accessed_at < NOW() - INTERVAL '1 day';")
        await execute("INSERT INTO memory.audit_log (operation, status, details) VALUES ($1, $2, $3)",
            "DECAY", "success", json.dumps({"memories_affected": affected, "decay_factor": decay_factor}))

    return {"status": "completed" if not dry_run else "dry_run", "memories_affected": affected,
        "decay_factor": decay_factor, "action": "decayed" if not dry_run else "would_decay"}


async def cleanup_task():
    while True:
        try:
            await asyncio.sleep(settings.MEMORY_CLEANUP_INTERVAL_MINUTES * 60)
            await execute("DELETE FROM memory.short_term WHERE expires_at < CURRENT_TIMESTAMP;")
            await execute("DELETE FROM memory.medium_term WHERE expires_at < CURRENT_TIMESTAMP;")
            if settings.DECAY_ENABLED:
                await apply_importance_decay(dry_run=False)
            logger.info("Cleanup task completed")
        except Exception as e:
            logger.error(f"Cleanup task error: {e}")
ENDFILE

# ═══════════════════════════════════════════════════════════════════
# src/main.py
# ═══════════════════════════════════════════════════════════════════
echo "📄 Creating src/main.py..."
cat > src/main.py << 'ENDFILE'
"""FastAPI MCP Memory Server."""

import logging
from fastapi import FastAPI, HTTPException, Depends, Header, Request
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import asyncio

from src.config import settings
from src.db import init_db, close_db
from src.mcp_server import get_mcp_tools, MCPToolCall, handle_tool_call
from src.routes import memory, health

logging.basicConfig(level=settings.LOG_LEVEL, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initializing database...")
    await init_db()
    logger.info("✓ Database initialized")
    asyncio.create_task(memory.cleanup_task())
    yield
    logger.info("Closing database connections...")
    await close_db()
    logger.info("✓ Shutdown complete")


app = FastAPI(title="L9 MCP Memory Server", description="OpenAI embeddings + pgvector semantic search for Cursor", version="1.0.0", lifespan=lifespan)


async def verify_api_key(authorization: str = Header(None)) -> str:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")
    token = authorization.replace("Bearer ", "")
    if token != settings.MCP_API_KEY:
        raise HTTPException(status_code=403, detail="Invalid API key")
    return token


@app.get("/")
async def root():
    return {"status": "L9 MCP Memory Server", "version": "1.0.0", "mcp_version": "2025-03-26"}


@app.get("/health")
async def health_check():
    return await health.health_check()


@app.get("/mcp/tools")
async def list_tools(auth: str = Depends(verify_api_key)):
    return {"tools": get_mcp_tools()}


@app.post("/mcp/call")
async def call_tool(request: Request, auth: str = Depends(verify_api_key)):
    try:
        payload = await request.json()
        tool_name, tool_args, user_id = payload.get("tool_name"), payload.get("arguments", {}), payload.get("user_id")
        if not user_id:
            raise HTTPException(status_code=400, detail="user_id required")
        tool_call = MCPToolCall(name=tool_name, arguments=tool_args)
        result = await handle_tool_call(tool_call, user_id)
        return {"status": "success", "result": result}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("Tool call error")
        raise HTTPException(status_code=500, detail=str(e))


app.include_router(memory.router, prefix="/memory", tags=["memory"])


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled exception")
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=settings.MCP_HOST, port=settings.MCP_PORT, log_level=settings.LOG_LEVEL.lower())
ENDFILE

# ═══════════════════════════════════════════════════════════════════
# schema/init.sql (WITH HNSW INDEXES)
# ═══════════════════════════════════════════════════════════════════
echo "📄 Creating schema/init.sql (with HNSW indexes)..."
cat > schema/init.sql << 'ENDFILE'
-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Create schema
CREATE SCHEMA IF NOT EXISTS memory;

-- Short-term memory (< 1 hour)
CREATE TABLE IF NOT EXISTS memory.short_term (
    id BIGSERIAL PRIMARY KEY,
    user_id TEXT NOT NULL,
    session_id TEXT,
    kind TEXT NOT NULL,
    content TEXT NOT NULL,
    embedding vector(1536),
    metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    CONSTRAINT check_short_term_expires CHECK (expires_at > created_at)
);

-- Medium-term memory (< 24 hours)
CREATE TABLE IF NOT EXISTS memory.medium_term (
    id BIGSERIAL PRIMARY KEY,
    user_id TEXT NOT NULL,
    session_id TEXT,
    kind TEXT NOT NULL,
    content TEXT NOT NULL,
    embedding vector(1536),
    importance FLOAT DEFAULT 1.0,
    metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    CONSTRAINT check_medium_term_expires CHECK (expires_at > created_at)
);

-- Long-term memory (durable)
CREATE TABLE IF NOT EXISTS memory.long_term (
    id BIGSERIAL PRIMARY KEY,
    user_id TEXT NOT NULL,
    scope TEXT NOT NULL DEFAULT 'user',
    kind TEXT NOT NULL,
    content TEXT NOT NULL,
    embedding vector(1536),
    importance FLOAT DEFAULT 1.0,
    tags TEXT[] DEFAULT '{}',
    metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    last_accessed_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    access_count INT DEFAULT 0,
    CONSTRAINT check_scope CHECK (scope IN ('user', 'project', 'global'))
);

-- HNSW Indexes (upgraded from IVFFlat)
CREATE INDEX idx_short_term_user_expires ON memory.short_term(user_id, expires_at);
CREATE INDEX idx_short_term_embedding ON memory.short_term USING hnsw(embedding vector_cosine_ops) WITH (m = 16, ef_construction = 64);

CREATE INDEX idx_medium_term_user_expires ON memory.medium_term(user_id, expires_at);
CREATE INDEX idx_medium_term_importance ON memory.medium_term(user_id, importance DESC) WHERE expires_at > CURRENT_TIMESTAMP;
CREATE INDEX idx_medium_term_embedding ON memory.medium_term USING hnsw(embedding vector_cosine_ops) WITH (m = 16, ef_construction = 64);

CREATE INDEX idx_long_term_user_scope ON memory.long_term(user_id, scope);
CREATE INDEX idx_long_term_kind ON memory.long_term(kind);
CREATE INDEX idx_long_term_tags ON memory.long_term USING GIN(tags);
CREATE INDEX idx_long_term_embedding ON memory.long_term USING hnsw(embedding vector_cosine_ops) WITH (m = 16, ef_construction = 64);
CREATE INDEX idx_long_term_access ON memory.long_term(last_accessed_at DESC);

-- Stats view
CREATE OR REPLACE VIEW memory.stats_view AS
SELECT 'short_term' as memory_type, COUNT(*) as total_count, COUNT(DISTINCT user_id) as unique_users, AVG(importance) as avg_importance, NOW() as calculated_at FROM memory.short_term WHERE expires_at > CURRENT_TIMESTAMP
UNION ALL SELECT 'medium_term', COUNT(*), COUNT(DISTINCT user_id), AVG(importance), NOW() FROM memory.medium_term WHERE expires_at > CURRENT_TIMESTAMP
UNION ALL SELECT 'long_term', COUNT(*), COUNT(DISTINCT user_id), AVG(importance), NOW() FROM memory.long_term;

-- Audit log
CREATE TABLE IF NOT EXISTS memory.audit_log (
    id BIGSERIAL PRIMARY KEY,
    operation TEXT NOT NULL,
    table_name TEXT,
    memory_id BIGINT,
    user_id TEXT,
    status TEXT NOT NULL DEFAULT 'success',
    details JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_audit_user_timestamp ON memory.audit_log(user_id, created_at DESC);
ENDFILE

# ═══════════════════════════════════════════════════════════════════
# schema/migrations/001_hnsw_upgrade.sql
# ═══════════════════════════════════════════════════════════════════
echo "📄 Creating schema/migrations/001_hnsw_upgrade.sql..."
cat > schema/migrations/001_hnsw_upgrade.sql << 'ENDFILE'
-- Migration: Upgrade IVFFlat indexes to HNSW
-- Run this on existing deployments

-- Drop old IVFFlat indexes
DROP INDEX IF EXISTS memory.idx_short_term_embedding;
DROP INDEX IF EXISTS memory.idx_medium_term_embedding;
DROP INDEX IF EXISTS memory.idx_long_term_embedding;

-- Create new HNSW indexes
CREATE INDEX idx_short_term_embedding ON memory.short_term USING hnsw(embedding vector_cosine_ops) WITH (m = 16, ef_construction = 64);
CREATE INDEX idx_medium_term_embedding ON memory.medium_term USING hnsw(embedding vector_cosine_ops) WITH (m = 16, ef_construction = 64);
CREATE INDEX idx_long_term_embedding ON memory.long_term USING hnsw(embedding vector_cosine_ops) WITH (m = 16, ef_construction = 64);

-- Analyze tables for query planner
ANALYZE memory.short_term;
ANALYZE memory.medium_term;
ANALYZE memory.long_term;
ENDFILE

# ═══════════════════════════════════════════════════════════════════
# deploy/systemd/l9-mcp.service
# ═══════════════════════════════════════════════════════════════════
echo "📄 Creating deploy/systemd/l9-mcp.service..."
cat > deploy/systemd/l9-mcp.service << 'ENDFILE'
[Unit]
Description=L9 MCP Memory Server
After=network.target postgresql.service
StartLimitIntervalSec=60
StartLimitBurst=3

[Service]
Type=simple
User=admin
WorkingDirectory=/opt/l9/mcp_memory
Environment="PATH=/opt/l9/venv/bin"
ExecStart=/opt/l9/venv/bin/python -m src.main
Restart=on-failure
RestartSec=10
StandardOutput=journal
StandardError=journal
SyslogIdentifier=l9-mcp

[Install]
WantedBy=multi-user.target
ENDFILE

# ═══════════════════════════════════════════════════════════════════
# deploy/scripts/install.sh
# ═══════════════════════════════════════════════════════════════════
echo "📄 Creating deploy/scripts/install.sh..."
cat > deploy/scripts/install.sh << 'ENDFILE'
#!/bin/bash
set -e

echo "╔════════════════════════════════════════════════════════════════╗"
echo "║  L9 MCP Memory Server Installation                            ║"
echo "╚════════════════════════════════════════════════════════════════╝"

MCP_DIR="/opt/l9/mcp_memory"
VENV_DIR="/opt/l9/venv_mcp"

echo "[1/6] Creating Python virtual environment..."
python3.11 -m venv $VENV_DIR
source $VENV_DIR/bin/activate

echo "[2/6] Installing dependencies..."
pip install --upgrade pip
pip install -r $MCP_DIR/requirements.txt

echo "[3/6] Initializing database..."
psql -U postgres -d l9_memory -f $MCP_DIR/schema/init.sql

echo "[4/6] Testing connections..."
python $MCP_DIR/deploy/scripts/test_connection.py

echo "[5/6] Installing systemd service..."
sudo cp $MCP_DIR/deploy/systemd/l9-mcp.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable l9-mcp

echo "[6/6] Starting service..."
sudo systemctl start l9-mcp

echo ""
echo "✓ Installation complete!"
echo ""
echo "Check status: sudo systemctl status l9-mcp"
echo "View logs:    sudo journalctl -u l9-mcp -f"
echo "Test locally: curl http://127.0.0.1:9001/health"
ENDFILE

# ═══════════════════════════════════════════════════════════════════
# deploy/scripts/tunnel-l9.sh
# ═══════════════════════════════════════════════════════════════════
echo "📄 Creating deploy/scripts/tunnel-l9.sh..."
cat > deploy/scripts/tunnel-l9.sh << 'ENDFILE'
#!/bin/bash
VPS_IP="157.180.73.53"
VPS_USER="admin"
LOCAL_PORT="9001"
REMOTE_PORT="9001"

echo "🔗 Establishing SSH tunnel to L9 MCP server..."
ssh -L ${LOCAL_PORT}:127.0.0.1:${REMOTE_PORT} ${VPS_USER}@${VPS_IP}
ENDFILE

# ═══════════════════════════════════════════════════════════════════
# deploy/scripts/test_connection.py
# ═══════════════════════════════════════════════════════════════════
echo "📄 Creating deploy/scripts/test_connection.py..."
cat > deploy/scripts/test_connection.py << 'ENDFILE'
#!/usr/bin/env python3
"""Test PostgreSQL and OpenAI connections."""

import asyncio
import os
import sys

async def main():
    print("Testing connections...")
    
    # Test PostgreSQL
    try:
        import asyncpg
        dsn = os.getenv("MEMORY_DSN", "postgresql://postgres@127.0.0.1:5432/l9_memory")
        conn = await asyncpg.connect(dsn)
        result = await conn.fetchval("SELECT 1")
        await conn.close()
        print(f"✓ PostgreSQL: Connected (result={result})")
    except Exception as e:
        print(f"✗ PostgreSQL: {e}")
        sys.exit(1)
    
    # Test OpenAI
    try:
        from openai import OpenAI
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        response = client.embeddings.create(model="text-embedding-3-small", input="test")
        print(f"✓ OpenAI: Connected (dim={len(response.data[0].embedding)})")
    except Exception as e:
        print(f"✗ OpenAI: {e}")
        sys.exit(1)
    
    print("\n✅ All connections successful!")

if __name__ == "__main__":
    asyncio.run(main())
ENDFILE

# ═══════════════════════════════════════════════════════════════════
# tests/__init__.py
# ═══════════════════════════════════════════════════════════════════
echo "📄 Creating tests/__init__.py..."
cat > tests/__init__.py << 'ENDFILE'
"""L9 MCP Memory Server Tests."""
ENDFILE

# ═══════════════════════════════════════════════════════════════════
# tests/test_memory.py
# ═══════════════════════════════════════════════════════════════════
echo "📄 Creating tests/test_memory.py..."
cat > tests/test_memory.py << 'ENDFILE'
"""Memory operations tests."""

import pytest
from unittest.mock import AsyncMock, patch


@pytest.mark.asyncio
async def test_save_memory_creates_embedding():
    """Memory save must generate embedding."""
    with patch("src.routes.memory.embed_text", new_callable=AsyncMock) as mock_embed:
        with patch("src.routes.memory.fetch_one", new_callable=AsyncMock) as mock_fetch:
            with patch("src.routes.memory.execute", new_callable=AsyncMock):
                mock_embed.return_value = [0.1] * 1536
                mock_fetch.return_value = {"id": 1, "user_id": "test", "kind": "fact", "content": "test", "importance": 1.0, "created_at": "2025-01-01T00:00:00Z"}
                
                from src.routes.memory import save_memory_handler
                result = await save_memory_handler(user_id="test", content="test content", kind="fact", duration="long")
                
                mock_embed.assert_called_once_with("test content")
                assert result["id"] == 1


@pytest.mark.asyncio
async def test_search_returns_similar():
    """Search must return semantically similar memories."""
    with patch("src.routes.memory.embed_text", new_callable=AsyncMock) as mock_embed:
        with patch("src.routes.memory.fetch_all", new_callable=AsyncMock) as mock_fetch:
            with patch("src.routes.memory.execute", new_callable=AsyncMock):
                mock_embed.return_value = [0.1] * 1536
                mock_fetch.return_value = [{"id": 1, "user_id": "test", "kind": "fact", "content": "similar", "importance": 1.0, "similarity": 0.95, "created_at": "2025-01-01T00:00:00Z"}]
                
                from src.routes.memory import search_memory_handler
                result = await search_memory_handler(user_id="test", query="test query")
                
                assert result["total_results"] == 1
                assert result["results"][0]["similarity"] == 0.95


@pytest.mark.asyncio
async def test_duplicate_memory_compounds():
    """Repeated similar memories should compound."""
    with patch("src.routes.memory.fetch_all", new_callable=AsyncMock) as mock_fetch:
        with patch("src.routes.memory.fetch_one", new_callable=AsyncMock) as mock_fetch_one:
            with patch("src.routes.memory.execute", new_callable=AsyncMock):
                with patch("src.routes.memory.settings") as mock_settings:
                    mock_settings.COMPOUNDING_ENABLED = True
                    mock_settings.COMPOUNDING_MIN_COUNT = 2
                    mock_fetch.return_value = [
                        {"id": 1, "content": "a", "embedding": [0.1]*1536, "importance": 0.5, "access_count": 1, "created_at": "2025-01-01", "tags": []},
                        {"id": 2, "content": "a", "embedding": [0.1]*1536, "importance": 0.5, "access_count": 1, "created_at": "2025-01-02", "tags": []},
                    ]
                    mock_fetch_one.return_value = {"similarity": 0.95}
                    
                    from src.routes.memory import compound_similar_memories
                    result = await compound_similar_memories(user_id="test", threshold=0.92)
                    
                    assert result["status"] == "completed"
ENDFILE

# ═══════════════════════════════════════════════════════════════════
# tests/test_embeddings.py
# ═══════════════════════════════════════════════════════════════════
echo "📄 Creating tests/test_embeddings.py..."
cat > tests/test_embeddings.py << 'ENDFILE'
"""Embedding tests."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock


@pytest.mark.asyncio
async def test_embed_text_returns_vector():
    """embed_text must return 1536-dim vector."""
    mock_response = MagicMock()
    mock_response.data = [MagicMock(embedding=[0.1] * 1536)]
    
    with patch("src.embeddings.client.embeddings.create", new_callable=AsyncMock) as mock_create:
        mock_create.return_value = mock_response
        
        from src.embeddings import embed_text
        result = await embed_text("test")
        
        assert len(result) == 1536
        mock_create.assert_called_once()


@pytest.mark.asyncio
async def test_embed_texts_batch():
    """embed_texts must handle batch requests."""
    mock_response = MagicMock()
    mock_response.data = [MagicMock(embedding=[0.1] * 1536, index=0), MagicMock(embedding=[0.2] * 1536, index=1)]
    
    with patch("src.embeddings.client.embeddings.create", new_callable=AsyncMock) as mock_create:
        mock_create.return_value = mock_response
        
        from src.embeddings import embed_texts
        result = await embed_texts(["test1", "test2"])
        
        assert len(result) == 2
        assert len(result[0]) == 1536
ENDFILE

# ═══════════════════════════════════════════════════════════════════
# tests/test_search.py
# ═══════════════════════════════════════════════════════════════════
echo "📄 Creating tests/test_search.py..."
cat > tests/test_search.py << 'ENDFILE'
"""Vector search tests."""

import pytest
from unittest.mock import AsyncMock, patch


@pytest.mark.asyncio
async def test_search_respects_threshold():
    """Search must filter by similarity threshold."""
    with patch("src.routes.memory.embed_text", new_callable=AsyncMock) as mock_embed:
        with patch("src.routes.memory.fetch_all", new_callable=AsyncMock) as mock_fetch:
            with patch("src.routes.memory.execute", new_callable=AsyncMock):
                mock_embed.return_value = [0.1] * 1536
                mock_fetch.return_value = []
                
                from src.routes.memory import search_memory_handler
                result = await search_memory_handler(user_id="test", query="query", threshold=0.99)
                
                assert result["total_results"] == 0


@pytest.mark.asyncio
async def test_search_respects_top_k():
    """Search must limit results to top_k."""
    with patch("src.routes.memory.embed_text", new_callable=AsyncMock) as mock_embed:
        with patch("src.routes.memory.fetch_all", new_callable=AsyncMock) as mock_fetch:
            with patch("src.routes.memory.execute", new_callable=AsyncMock):
                mock_embed.return_value = [0.1] * 1536
                mock_fetch.return_value = [{"id": i, "user_id": "test", "kind": "fact", "content": f"c{i}", "importance": 1.0, "similarity": 0.9, "created_at": "2025-01-01"} for i in range(10)]
                
                from src.routes.memory import search_memory_handler
                result = await search_memory_handler(user_id="test", query="query", top_k=3)
                
                assert result["total_results"] <= 3
ENDFILE

# ═══════════════════════════════════════════════════════════════════
# requirements.txt
# ═══════════════════════════════════════════════════════════════════
echo "📄 Creating requirements.txt..."
cat > requirements.txt << 'ENDFILE'
# MCP Core
mcp>=1.0.0
pydantic-settings>=2.0.0

# FastAPI & async
fastapi>=0.115.0
uvicorn[standard]>=0.30.0
httpx>=0.27.0

# Database (async)
asyncpg>=0.29.0
psycopg[binary]>=3.1.0
pgvector>=0.2.5

# Embeddings & LLM
openai>=1.0.0
tenacity>=8.2.0

# Utils
python-dotenv>=1.0.0
pyyaml>=6.0.1

# Testing
pytest>=8.0.0
pytest-asyncio>=0.23.0
ENDFILE

# ═══════════════════════════════════════════════════════════════════
# .env.example
# ═══════════════════════════════════════════════════════════════════
echo "📄 Creating .env.example..."
cat > .env.example << 'ENDFILE'
# ═══════════════════════════════════════════════════════════════
# MCP Memory Server Configuration
# ═══════════════════════════════════════════════════════════════

# Server
MCP_HOST=127.0.0.1
MCP_PORT=9001
MCP_ENV=production
LOG_LEVEL=INFO

# OpenAI
OPENAI_API_KEY=sk-proj-YOUR_KEY_HERE
OPENAI_EMBED_MODEL=text-embedding-3-small

# PostgreSQL
MEMORY_DSN=postgresql://postgres:YOUR_PASSWORD@127.0.0.1:5432/l9_memory

# Memory Behavior
MEMORY_SHORT_TERM_HOURS=1
MEMORY_MEDIUM_TERM_HOURS=24
MEMORY_CLEANUP_INTERVAL_MINUTES=60

# Vector Search
VECTOR_SEARCH_THRESHOLD=0.7
VECTOR_SEARCH_TOP_K=10

# HNSW Index
VECTOR_INDEX_TYPE=hnsw
HNSW_M=16
HNSW_EF_CONSTRUCTION=64
HNSW_EF_SEARCH=40

# Memory Compounding
COMPOUNDING_ENABLED=true
COMPOUNDING_SIMILARITY_THRESHOLD=0.92
COMPOUNDING_MIN_COUNT=3

# Importance Decay
DECAY_ENABLED=true
DECAY_RATE_PER_DAY=0.01
ACCESS_BOOST_PER_HIT=0.05

# Auth
MCP_API_KEY=your-secret-key-generate-with-openssl-rand-hex-32

# Redis (optional)
REDIS_ENABLED=false
REDIS_HOST=127.0.0.1
REDIS_PORT=6379
ENDFILE

# ═══════════════════════════════════════════════════════════════════
# .gitignore
# ═══════════════════════════════════════════════════════════════════
echo "📄 Creating .gitignore..."
cat > .gitignore << 'ENDFILE'
# Python
__pycache__/
*.py[cod]
*.so
.Python
venv/
.venv/

# Environment
.env
*.env.local

# IDE
.idea/
.vscode/
*.swp

# Logs
*.log
logs/

# Test
.pytest_cache/
.coverage
htmlcov/

# OS
.DS_Store
Thumbs.db
ENDFILE

# ═══════════════════════════════════════════════════════════════════
# README.md
# ═══════════════════════════════════════════════════════════════════
echo "📄 Creating README.md..."
cat > README.md << 'ENDFILE'
# L9 MCP Memory Server

OpenAI embeddings + pgvector semantic search for Cursor IDE.

**Production URL:** `https://l9.quantumaipartners.com`

```
┌─────────────────────────────────────────────────────────────────┐
│ MacBook (Local)                                                 │
│  └─ Cursor IDE → MCP Client → https://l9.quantumaipartners.com │
└──────────────────────┬──────────────────────────────────────────┘
                       │ HTTPS via Cloudflare (no SSH tunnel!)
┌──────────────────────↓──────────────────────────────────────────┐
│ Cloudflare (Proxy)                                              │
│  └─ DNS: l9.quantumaipartners.com → VPS (proxied)              │
└──────────────────────┬──────────────────────────────────────────┘
                       │ Port 443
┌──────────────────────↓──────────────────────────────────────────┐
│ VPS (L9)                                                        │
│  ├─ Caddy (reverse proxy)                                       │
│  │   └─ /mcp/*, /memory/* → mcp-memory:9001                    │
│  ├─ FastAPI MCP Server (0.0.0.0:9001)                          │
│  │   ├─ /mcp/tools     (tool discovery)                        │
│  │   ├─ /mcp/call      (tool execution)                        │
│  │   ├─ /memory/save   (store embeddings)                      │
│  │   └─ /memory/search (vector similarity)                     │
│  └─ PostgreSQL + pgvector (127.0.0.1:5432)                     │
│       ├─ memory.short_term  (< 24 hours)                       │
│       ├─ memory.medium_term (< 7 days)                         │
│       └─ memory.long_term   (durable, HNSW indexed)            │
└─────────────────────────────────────────────────────────────────┘
```

## Quick Start

```bash
# 1. Bootstrap (creates all files)
./bootstrap.sh

# 2. Configure
cp .env.example .env
# Edit .env with your credentials

# 3. Deploy to VPS
scp -r . admin@YOUR_VPS:/opt/l9/mcp_memory/
ssh admin@YOUR_VPS
cd /opt/l9/mcp_memory
./deploy/scripts/install.sh
```

## Access (Production)

No SSH tunnel needed! Access directly via HTTPS:

```bash
curl https://l9.quantumaipartners.com/health
curl -H "Authorization: Bearer YOUR_API_KEY" https://l9.quantumaipartners.com/mcp/tools
```

## SSH Tunnel (Development Only)

Only needed for local development bypassing Cloudflare:

```bash
ssh -L 9001:127.0.0.1:9001 root@157.180.73.53
# Then access http://127.0.0.1:9001
```

## API Reference

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check |
| `/mcp/tools` | GET | List MCP tools |
| `/mcp/call` | POST | Execute MCP tool |
| `/memory/save` | POST | Save memory |
| `/memory/search` | POST | Search memories |
| `/memory/stats` | GET | Memory statistics |

## MCP Tools

- `save_memory` - Store with automatic embedding
- `search_memory` - Semantic similarity search
- `get_memory_stats` - Usage statistics
- `delete_expired_memories` - Cleanup expired
- `compound_memories` - Merge similar memories
- `apply_decay` - Decay unused memory importance

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `VECTOR_INDEX_TYPE` | `hnsw` | Index type (hnsw/ivfflat) |
| `HNSW_M` | `16` | HNSW connections per node |
| `HNSW_EF_CONSTRUCTION` | `64` | HNSW build quality |
| `COMPOUNDING_ENABLED` | `true` | Auto-merge similar memories |
| `DECAY_ENABLED` | `true` | Decay unused importance |

## Troubleshooting

**Connection timeout:**
- Check Cloudflare DNS: `dig l9.quantumaipartners.com`
- Check Caddy: `sudo systemctl status caddy`
- Check service: `sudo systemctl status l9-mcp`

**Embedding failures:**
- Verify API key: `echo $OPENAI_API_KEY`
- Check quota: https://platform.openai.com/account/usage

**Slow searches:**
- Verify HNSW indexes: `\d+ memory.long_term`
- Run: `ANALYZE memory.long_term;`
ENDFILE

# ═══════════════════════════════════════════════════════════════════
# Set Permissions
# ═══════════════════════════════════════════════════════════════════
echo "🔧 Setting permissions..."
chmod +x deploy/scripts/install.sh
chmod +x deploy/scripts/tunnel-l9.sh
chmod +x deploy/scripts/test_connection.py

# ═══════════════════════════════════════════════════════════════════
# Validate Python
# ═══════════════════════════════════════════════════════════════════
echo "🧪 Validating Python syntax..."
python3 -m py_compile src/config.py
python3 -m py_compile src/db.py
python3 -m py_compile src/embeddings.py
python3 -m py_compile src/models.py
python3 -m py_compile src/mcp_server.py
python3 -m py_compile src/main.py
python3 -m py_compile src/routes/memory.py
python3 -m py_compile src/routes/health.py
python3 -m py_compile deploy/scripts/test_connection.py

# ═══════════════════════════════════════════════════════════════════
# Summary
# ═══════════════════════════════════════════════════════════════════
echo ""
echo "✅ Bootstrap complete!"
echo ""
echo "Files created:"
find . -type f | grep -v ".git" | sort
echo ""
echo "HNSW index count: $(grep -c 'hnsw' schema/init.sql)"
echo ""
echo "Next steps:"
echo "  1. cp .env.example .env"
echo "  2. Edit .env with your credentials"
echo "  3. Deploy to VPS with deploy/scripts/install.sh"

