The MCP memory server is not present as code in the L9 repo yet; you only have the implementation spec in `L9-MCP-IMPL.md`.  To keep this deterministic and compatible with your existing layout, the cleanest drop‑in is a **standalone MCP memory server package** under a new top-level directory in the L9 repo, mirroring the `/opt/l9/mcp/memory` structure described in the spec.[1][2]

Below is the full code and file layout for Option A, exactly as you asked: you can save these files into your L9 repo, commit, then rsync/clone to the VPS and run the install script.

***

## Directory and file layout

Create a top-level folder in your L9 repo:

- `mcp-memory/`
  - `__init__.py`
  - `main.py`
  - `mcpserver.py`
  - `db.py`
  - `embeddings.py`
  - `models.py`
  - `config.py`
  - `routes/`
    - `__init__.py`
    - `memory.py`
    - `health.py`
  - `schema/`
    - `init.sql`
  - `scripts/`
    - `migrate_db.py`
    - `test_connection.py`
    - `install.sh`
  - `requirements-mcp.txt`
  - `.env.example`
  - `systemd-l9-mcp.service`
  - `README.md`

This mirrors the doc’s `opt/l9/mcp/memory` plan but as `mcp-memory` inside the repo.[2]

You can later deploy to `/opt/l9/mcp/memory` on the VPS by copying this directory and running `scripts/install.sh`.[2]

***

## `mcp-memory/__init__.py`

```python
"""
L9 MCP Memory Server package.

This package exposes a standalone FastAPI application that implements
an MCP-compatible memory server backed by PostgreSQL + pgvector.
"""
```

***

## `mcp-memory/config.py`

```python
import os
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Server
    MCP_HOST: str = "127.0.0.1"
    MCP_PORT: int = 9001
    MCP_ENV: str = "production"
    LOG_LEVEL: str = "INFO"

    # OpenAI
    OPENAI_API_KEY: str
    OPENAI_EMBED_MODEL: str = "text-embedding-3-small"
    OPENAI_EMBED_DIM: int = 1536

    # PostgreSQL (same Postgres instance L9 uses, but l9memory DB)
    MEMORY_DSN: str

    # Memory lifecycle
    MEMORY_SHORTTERM_HOURS: int = 1
    MEMORY_MEDIUMTERM_HOURS: int = 24
    MEMORY_CLEANUP_INTERVAL_MINUTES: int = 60
    MEMORY_SHORT_RETENTION_DAYS: int = 7
    MEMORY_MEDIUM_RETENTION_DAYS: int = 30

    # Vector search
    VECTOR_SEARCH_THRESHOLD: float = 0.7
    VECTOR_SEARCH_TOP_K: int = 10

    # MCP auth
    MCP_API_KEY: str

    # Optional Redis embedding cache (not used yet; for future)
    REDIS_ENABLED: bool = False
    REDIS_HOST: str = "127.0.0.1"
    REDIS_PORT: int = 6379

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()
```

Matches the spec’s settings fields.[2]

***

## `mcp-memory/db.py`

```python
import logging
from typing import Any, Dict, List, Optional

import asyncpg

from .config import settings

logger = logging.getLogger(__name__)

_pool: Optional[asyncpg.Pool] = None


async def init_db() -> None:
    """
    Initialize global asyncpg connection pool and ensure pgvector extension exists.
    """
    global _pool
    if _pool is not None:
        return

    _pool = await asyncpg.create_pool(
        dsn=settings.MEMORY_DSN,
        min_size=5,
        max_size=20,
        command_timeout=60,
    )

    async with _pool.acquire() as conn:
        await conn.execute("CREATE EXTENSION IF NOT EXISTS vector;")

    logger.info("Database connection pool initialized for MCP memory server")


async def close_db() -> None:
    """
    Close the global connection pool.
    """
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None
        logger.info("Database connection pool closed")


async def execute(query: str, *args: Any) -> str:
    """
    Execute a statement and return command status string.
    """
    if _pool is None:
        raise RuntimeError("Database pool not initialized")

    async with _pool.acquire() as conn:
        return await conn.execute(query, *args)


async def fetch_one(query: str, *args: Any) -> Optional[Dict[str, Any]]:
    """
    Fetch a single row as a dict.
    """
    if _pool is None:
        raise RuntimeError("Database pool not initialized")

    async with _pool.acquire() as conn:
        row = await conn.fetchrow(query, *args)
        return dict(row) if row is not None else None


async def fetch_all(query: str, *args: Any) -> List[Dict[str, Any]]:
    """
    Fetch all rows as list of dicts.
    """
    if _pool is None:
        raise RuntimeError("Database pool not initialized")

    async with _pool.acquire() as conn:
        rows = await conn.fetch(query, *args)
        return [dict(r) for r in rows]


async def insert_many(query: str, args_list: List[tuple]) -> int:
    """
    Insert multiple rows using executemany, return affected row count.
    """
    if _pool is None:
        raise RuntimeError("Database pool not initialized")

    async with _pool.acquire() as conn:
        # asyncpg executemany returns None; we approximate by len(args_list)
        await conn.executemany(query, args_list)
        return len(args_list)
```

Matches the async client described.[2]

***

## `mcp-memory/embeddings.py`

```python
import logging
from typing import List

from openai import AsyncOpenAI

from .config import settings

logger = logging.getLogger(__name__)

_client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)


async def embed_text(text: str) -> List[float]:
    """
    Generate a single embedding for the given text.
    """
    try:
        resp = await _client.embeddings.create(
            model=settings.OPENAI_EMBED_MODEL,
            input=text,
        )
        return resp.data[0].embedding
    except Exception as exc:
        logger.error("Embedding error: %s", exc, exc_info=True)
        raise


async def embed_texts(texts: List[str]) -> List[List[float]]:
    """
    Generate embeddings for a list of texts, preserving order.
    """
    try:
        resp = await _client.embeddings.create(
            model=settings.OPENAI_EMBED_MODEL,
            input=texts,
        )
        sorted_data = sorted(resp.data, key=lambda x: x.index)
        return [item.embedding for item in sorted_data]
    except Exception as exc:
        logger.error("Batch embedding error: %s", exc, exc_info=True)
        raise
```

As in the spec.[2]

***

## `mcp-memory/models.py`

```python
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class SaveMemoryRequest(BaseModel):
    content: str
    kind: str  # preference, fact, context, error, success
    scope: str = "user"  # user, project, global
    duration: str  # short, medium, long
    userid: str
    tags: Optional[List[str]] = None
    importance: Optional[float] = 1.0
    metadata: Optional[Dict[str, Any]] = None


class MemoryResponse(BaseModel):
    id: int
    userid: str
    kind: str
    content: str
    importance: float
    tags: Optional[List[str]] = None
    created_at: datetime
    similarity: Optional[float] = None


class SearchMemoryRequest(BaseModel):
    query: str
    userid: str
    scopes: Optional[List[str]] = ["user", "project", "global"]
    kinds: Optional[List[str]] = None
    topk: Optional[int] = 5
    threshold: Optional[float] = 0.7
    duration: Optional[str] = "all"  # short, medium, long, all


class SearchMemoryResponse(BaseModel):
    results: List[MemoryResponse]
    query_embedding_time_ms: float
    search_time_ms: float
    total_results: int


class MemoryStatsResponse(BaseModel):
    shortterm_count: int
    mediumterm_count: int
    longterm_count: int
    total_count: int
    unique_users: int
    avg_importance: float
```

Mirror of the Pydantic schemas.[2]

***

## `mcp-memory/mcpserver.py`

```python
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
    """
    Define all tools exposed over MCP to Cursor.
    """
    return [
        MCPTool(
            name="saveMemory",
            description="Save a memory to the database with automatic embedding and categorization",
            inputSchema={
                "type": "object",
                "properties": {
                    "content": {
                        "type": "string",
                        "description": "The memory content to store",
                    },
                    "kind": {
                        "type": "string",
                        "enum": ["preference", "fact", "context", "error", "success"],
                        "description": "Type of memory",
                    },
                    "scope": {
                        "type": "string",
                        "enum": ["user", "project", "global"],
                        "description": "Memory scope",
                    },
                    "duration": {
                        "type": "string",
                        "enum": ["short", "medium", "long"],
                        "description": "Memory duration: short=1h, medium=24h, long=durable",
                    },
                    "userid": {
                        "type": "string",
                        "description": "User identifier",
                    },
                    "tags": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Optional tags",
                    },
                    "importance": {
                        "type": "number",
                        "minimum": 0,
                        "maximum": 1,
                        "description": "Importance weight 0–1",
                    },
                    "metadata": {
                        "type": "object",
                        "description": "Optional metadata",
                    },
                },
                "required": ["content", "kind", "duration", "userid"],
            },
        ),
        MCPTool(
            name="searchMemory",
            description="Search memories using semantic similarity vector search",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query to embed",
                    },
                    "userid": {
                        "type": "string",
                        "description": "User identifier for scoping search",
                    },
                    "scopes": {
                        "type": "array",
                        "items": {"type": "string"},
                        "default": ["user", "project", "global"],
                        "description": "Memory scopes to search",
                    },
                    "kinds": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Filter by memory kinds",
                    },
                    "topk": {
                        "type": "integer",
                        "default": 5,
                        "minimum": 1,
                        "maximum": 50,
                        "description": "Number of results",
                    },
                    "threshold": {
                        "type": "number",
                        "default": 0.7,
                        "description": "Similarity threshold 0–1",
                    },
                    "duration": {
                        "type": "string",
                        "enum": ["short", "medium", "long", "all"],
                        "default": "all",
                        "description": "Which memory tables to search",
                    },
                },
                "required": ["query", "userid"],
            },
        ),
        MCPTool(
            name="getMemoryStats",
            description="Get statistics about stored memories",
            inputSchema={
                "type": "object",
                "properties": {
                    "userid": {
                        "type": "string",
                        "description": "User identifier (optional; omit for global stats)",
                    },
                    "duration": {
                        "type": "string",
                        "enum": ["short", "medium", "long", "all"],
                        "default": "all",
                    },
                },
                "required": [],
            },
        ),
        MCPTool(
            name="deleteExpiredMemories",
            description="Cleanup expired short and medium-term memories (admin only)",
            inputSchema={
                "type": "object",
                "properties": {
                    "dryrun": {
                        "type": "boolean",
                        "default": True,
                        "description": "If true, only report what would be deleted",
                    }
                },
                "required": [],
            },
        ),
    ]


async def handle_tool_call(tool: MCPToolCall, userid: str) -> Dict[str, Any]:
    """
    Route MCP tool calls to appropriate handlers.
    """
    from .routes.memory import (
        save_memory,
        search_memory,
        get_memory_stats,
        delete_expired_memories,
    )

    if tool.name == "saveMemory":
        return await save_memory(
            userid=userid,
            content=tool.arguments.get("content", ""),
            kind=tool.arguments.get("kind", "context"),
            scope=tool.arguments.get("scope", "user"),
            duration=tool.arguments.get("duration", "long"),
            tags=tool.arguments.get("tags"),
            importance=tool.arguments.get("importance", 1.0),
            metadata=tool.arguments.get("metadata"),
        )
    if tool.name == "searchMemory":
        return await search_memory(
            userid=userid,
            query=tool.arguments.get("query", ""),
            scopes=tool.arguments.get("scopes") or ["user", "project", "global"],
            kinds=tool.arguments.get("kinds"),
            topk=tool.arguments.get("topk", 5),
            threshold=tool.arguments.get("threshold", 0.7),
            duration=tool.arguments.get("duration", "all"),
        )
    if tool.name == "getMemoryStats":
        return await get_memory_stats(
            userid=tool.arguments.get("userid"),
            duration=tool.arguments.get("duration", "all"),
        )
    if tool.name == "deleteExpiredMemories":
        return await delete_expired_memories(
            dryrun=tool.arguments.get("dryrun", True),
        )
    raise ValueError(f"Unknown tool {tool.name}")
```

This is the MCP interface.[2]

***

## `mcp-memory/routes/__init__.py`

```python
from fastapi import APIRouter

from .memory import router as memory_router
from .health import router as health_router

router = APIRouter()
router.include_router(memory_router, prefix="/memory", tags=["memory"])
router.include_router(health_router, prefix="", tags=["health"])
```

***

## `mcp-memory/routes/health.py`

```python
from fastapi import APIRouter

from ..config import settings
from ..db import _pool

router = APIRouter()


@router.get("/health")
async def healthcheck() -> dict:
    db_ok = _pool is not None
    return {
        "status": "healthy" if db_ok else "unhealthy",
        "database": "connected" if db_ok else "disconnected",
        "mcp_version": "2025-03-26",
        "embed_model": settings.OPENAI_EMBED_MODEL,
    }
```

Based on spec’s health endpoint.[2]

***

## `mcp-memory/routes/memory.py`

```python
import asyncio
import logging
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException

from ..config import settings
from ..db import execute, fetch_all, fetch_one
from ..embeddings import embed_text
from ..models import (
    MemoryResponse,
    MemoryStatsResponse,
    SaveMemoryRequest,
    SearchMemoryRequest,
    SearchMemoryResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/save", response_model=MemoryResponse)
async def save_memory_endpoint(req: SaveMemoryRequest) -> MemoryResponse:
    return await _save_memory(req)


async def save_memory(
    userid: str,
    content: str,
    kind: str,
    scope: str,
    duration: str,
    tags: Optional[List[str]],
    importance: float,
    metadata: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Internal helper used by MCP tool path.
    """
    req = SaveMemoryRequest(
        userid=userid,
        content=content,
        kind=kind,
        scope=scope,
        duration=duration,
        tags=tags,
        importance=importance,
        metadata=metadata,
    )
    resp = await _save_memory(req)
    return resp.dict()


async def _save_memory(req: SaveMemoryRequest) -> MemoryResponse:
    try:
        embedding = await embed_text(req.content)

        if req.duration == "short":
            table = "memory.shortterm"
            expires_at = datetime.utcnow() + timedelta(hours=settings.MEMORY_SHORTTERM_HOURS)
            query = (
                f"INSERT INTO {table} "
                "(userid, kind, content, embedding, importance, metadata, expiresat) "
                "VALUES ($1, $2, $3, $4::vector, $5, $6, $7) "
                "RETURNING id, userid, kind, content, importance, (metadata::text) AS metadatatext, createdat"
            )
            row = await fetch_one(
                query,
                req.userid,
                req.kind,
                req.content,
                embedding,
                req.importance or 1.0,
                req.metadata,
                expires_at,
            )
            if row is None:
                raise RuntimeError("Insert failed for short-term memory")

            await execute(
                "INSERT INTO memory.auditlog (operation, tablename, memoryid, userid, status, details) "
                "VALUES ($1, $2, $3, $4, $5, $6)",
                "INSERT",
                table,
                row["id"],
                req.userid,
                "success",
                {"duration": req.duration, "kind": req.kind},
            )

            return MemoryResponse(
                id=row["id"],
                userid=row["userid"],
                kind=row["kind"],
                content=row["content"],
                importance=row["importance"],
                tags=None,
                created_at=row["createdat"],
            )

        if req.duration == "medium":
            table = "memory.mediumterm"
            expires_at = datetime.utcnow() + timedelta(hours=settings.MEMORY_MEDIUMTERM_HOURS)
            query = (
                f"INSERT INTO {table} "
                "(userid, kind, content, embedding, importance, metadata, expiresat) "
                "VALUES ($1, $2, $3, $4::vector, $5, $6, $7) "
                "RETURNING id, userid, kind, content, importance, (metadata::text) AS metadatatext, createdat"
            )
            row = await fetch_one(
                query,
                req.userid,
                req.kind,
                req.content,
                embedding,
                req.importance or 1.0,
                req.metadata,
                expires_at,
            )
            if row is None:
                raise RuntimeError("Insert failed for medium-term memory")

            await execute(
                "INSERT INTO memory.auditlog (operation, tablename, memoryid, userid, status, details) "
                "VALUES ($1, $2, $3, $4, $5, $6)",
                "INSERT",
                table,
                row["id"],
                req.userid,
                "success",
                {"duration": req.duration, "kind": req.kind},
            )

            return MemoryResponse(
                id=row["id"],
                userid=row["userid"],
                kind=row["kind"],
                content=row["content"],
                importance=row["importance"],
                tags=None,
                created_at=row["createdat"],
            )

        if req.duration == "long":
            table = "memory.longterm"
            query = (
                "INSERT INTO memory.longterm "
                "(userid, scope, kind, content, embedding, importance, tags, metadata) "
                "VALUES ($1, $2, $3, $4, $5::vector, $6, $7, $8) "
                "RETURNING id, userid, kind, content, importance, tags, createdat"
            )
            row = await fetch_one(
                query,
                req.userid,
                req.scope,
                req.kind,
                req.content,
                embedding,
                req.importance or 1.0,
                req.tags,
                req.metadata,
            )
            if row is None:
                raise RuntimeError("Insert failed for long-term memory")

            await execute(
                "INSERT INTO memory.auditlog (operation, tablename, memoryid, userid, status, details) "
                "VALUES ($1, $2, $3, $4, $5, $6)",
                "INSERT",
                table,
                row["id"],
                req.userid,
                "success",
                {"duration": req.duration, "kind": req.kind},
            )

            return MemoryResponse(
                id=row["id"],
                userid=row["userid"],
                kind=row["kind"],
                content=row["content"],
                importance=row["importance"],
                tags=row["tags"],
                created_at=row["createdat"],
            )

        raise ValueError(f"Invalid duration {req.duration}")
    except Exception as exc:
        logger.exception("Error saving memory")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/search", response_model=SearchMemoryResponse)
async def search_memory_endpoint(req: SearchMemoryRequest) -> SearchMemoryResponse:
    return await _search_memory(req)


async def search_memory(
    userid: str,
    query: str,
    scopes: Optional[List[str]],
    kinds: Optional[List[str]],
    topk: int,
    threshold: float,
    duration: str,
) -> Dict[str, Any]:
    req = SearchMemoryRequest(
        userid=userid,
        query=query,
        scopes=scopes,
        kinds=kinds,
        topk=topk,
        threshold=threshold,
        duration=duration,
    )
    resp = await _search_memory(req)
    return resp.dict()


async def _search_memory(req: SearchMemoryRequest) -> SearchMemoryResponse:
    start_time = time.time()
    try:
        embed_start = time.time()
        query_embedding = await embed_text(req.query)
        embed_time_ms = (time.time() - embed_start) * 1000.0

        results: List[Dict[str, Any]] = []
        durations: List[str] = ["short", "medium", "long"] if req.duration == "all" else [req.duration]

        for d in durations:
            if d == "short":
                table = "memory.shortterm"
                where_clauses = ["userid = $1", "expiresat > CURRENT_TIMESTAMP"]
                params: List[Any] = [req.userid]
            elif d == "medium":
                table = "memory.mediumterm"
                where_clauses = ["userid = $1", "expiresat > CURRENT_TIMESTAMP"]
                params = [req.userid]
            else:
                table = "memory.longterm"
                where_clauses = ["userid = $1"]
                params = [req.userid]

            if d == "long" and req.scopes:
                idx_start = len(params) + 1
                placeholders = ", ".join(f"${i}" for i in range(idx_start, idx_start + len(req.scopes)))
                where_clauses.append(f"scope IN ({placeholders})")
                params.extend(req.scopes)

            if req.kinds:
                idx_start = len(params) + 1
                placeholders = ", ".join(f"${i}" for i in range(idx_start, idx_start + len(req.kinds)))
                where_clauses.append(f"kind IN ({placeholders})")
                params.extend(req.kinds)

            sim_param_idx = len(params) + 1
            threshold_idx = sim_param_idx + 1
            limit_idx = threshold_idx + 1

            where_clauses.append(f"1 - (embedding <=> ${sim_param_idx}::vector) >= ${threshold_idx}")
            params.extend([query_embedding, req.threshold or settings.VECTOR_SEARCH_THRESHOLD, req.topk or settings.VECTOR_SEARCH_TOP_K])

            where_sql = " AND ".join(where_clauses)
            query_sql = (
                f"SELECT id, userid, kind, content, importance, "
                f"1 - (embedding <=> ${sim_param_idx}::vector) AS similarity, "
                f"(metadata::text) AS metadatatext, createdat "
                f"FROM {table} "
                f"WHERE {where_sql} "
                f"ORDER BY similarity DESC "
                f"LIMIT ${limit_idx}"
            )
            params.append(req.topk or settings.VECTOR_SEARCH_TOP_K)

            rows = await fetch_all(query_sql, *params)
            results.extend(rows)

        results.sort(key=lambda x: x.get("similarity") or 0.0, reverse=True)
        results = results[: (req.topk or settings.VECTOR_SEARCH_TOP_K)]
        search_time_ms = (time.time() - start_time) * 1000.0

        memory_results = [
            MemoryResponse(
                id=r["id"],
                userid=r["userid"],
                kind=r["kind"],
                content=r["content"],
                importance=r["importance"],
                tags=None,
                created_at=r["createdat"],
                similarity=r.get("similarity"),
            )
            for r in results
        ]

        await execute(
            "INSERT INTO memory.auditlog (operation, userid, status, details) "
            "VALUES ($1, $2, $3, $4)",
            "SEARCH",
            req.userid,
            "success",
            {"query": req.query, "results_count": len(memory_results)},
        )

        return SearchMemoryResponse(
            results=memory_results,
            query_embedding_time_ms=embed_time_ms,
            search_time_ms=search_time_ms,
            total_results=len(memory_results),
        )
    except Exception as exc:
        logger.exception("Error searching memory")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/stats", response_model=MemoryStatsResponse)
async def stats_endpoint(userid: Optional[str] = None, duration: str = "all") -> MemoryStatsResponse:
    return await _get_memory_stats(userid, duration)


async def get_memory_stats(userid: Optional[str], duration: str) -> Dict[str, Any]:
    resp = await _get_memory_stats(userid, duration)
    return resp.dict()


async def _get_memory_stats(userid: Optional[str], duration: str) -> MemoryStatsResponse:
    where_user = "" if userid is None else "WHERE userid = $1"
    params: List[Any] = [] if userid is None else [userid]

    short_sql = f"SELECT COUNT(*) AS c, COALESCE(AVG(importance), 0) AS avgimp FROM memory.shortterm {where_user}"
    medium_sql = f"SELECT COUNT(*) AS c, COALESCE(AVG(importance), 0) AS avgimp FROM memory.mediumterm {where_user}"
    long_sql = f"SELECT COUNT(*) AS c, COALESCE(AVG(importance), 0) AS avgimp FROM memory.longterm {where_user}"
    unique_sql = "SELECT COUNT(DISTINCT userid) AS u FROM memory.longterm"

    short_row = await fetch_one(short_sql, *params) or {"c": 0, "avgimp": 0.0}
    medium_row = await fetch_one(medium_sql, *params) or {"c": 0, "avgimp": 0.0}
    long_row = await fetch_one(long_sql, *params) or {"c": 0, "avgimp": 0.0}
    unique_row = await fetch_one(unique_sql) or {"u": 0}

    total_count = short_row["c"] + medium_row["c"] + long_row["c"]
    avg_importance = (
        (short_row["avgimp"] + medium_row["avgimp"] + long_row["avgimp"]) / 3.0 if total_count > 0 else 0.0
    )

    return MemoryStatsResponse(
        shortterm_count=short_row["c"],
        mediumterm_count=medium_row["c"],
        longterm_count=long_row["c"],
        total_count=total_count,
        unique_users=unique_row["u"],
        avg_importance=avg_importance,
    )


async def delete_expired_memories(dryrun: bool = True) -> Dict[str, Any]:
    """
    Delete expired rows from shortterm and mediumterm.
    """
    if dryrun:
        short_sql = "SELECT COUNT(*) AS c FROM memory.shortterm WHERE expiresat <= CURRENT_TIMESTAMP"
        medium_sql = "SELECT COUNT(*) AS c FROM memory.mediumterm WHERE expiresat <= CURRENT_TIMESTAMP"
        short_row = await fetch_one(short_sql) or {"c": 0}
        medium_row = await fetch_one(medium_sql) or {"c": 0}
        return {
            "shortterm_expired": short_row["c"],
            "mediumterm_expired": medium_row["c"],
            "dryrun": True,
        }

    short_deleted = await execute("DELETE FROM memory.shortterm WHERE expiresat <= CURRENT_TIMESTAMP")
    medium_deleted = await execute("DELETE FROM memory.mediumterm WHERE expiresat <= CURRENT_TIMESTAMP")
    return {
        "shortterm_deleted": short_deleted,
        "mediumterm_deleted": medium_deleted,
        "dryrun": False,
    }


async def cleanup_task() -> None:
    """
    Background cleanup loop; started at app startup.
    """
    while True:
        try:
            interval_seconds = settings.MEMORY_CLEANUP_INTERVAL_MINUTES * 60
            await asyncio.sleep(interval_seconds)
            await execute("DELETE FROM memory.shortterm WHERE expiresat <= CURRENT_TIMESTAMP")
            await execute("DELETE FROM memory.mediumterm WHERE expiresat <= CURRENT_TIMESTAMP")
            logger.info("Cleanup task completed")
        except Exception as exc:
            logger.error("Cleanup task error: %s", exc, exc_info=True)
```

Closely follows the spec’s logic.[2]

***

## `mcp-memory/schema/init.sql`

```sql
-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Create schema
CREATE SCHEMA IF NOT EXISTS memory;

-- Short-term memory (1 hour, aggressive cleanup)
CREATE TABLE IF NOT EXISTS memory.shortterm (
    id         BIGSERIAL PRIMARY KEY,
    userid     TEXT NOT NULL,
    sessionid  TEXT,
    kind       TEXT NOT NULL,
    content    TEXT NOT NULL,
    embedding  vector(1536),
    metadata   JSONB,
    createdat  TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    expiresat  TIMESTAMPTZ NOT NULL,
    CONSTRAINT check_shortterm_expires CHECK (expiresat > createdat)
);

-- Medium-term memory (24 hours)
CREATE TABLE IF NOT EXISTS memory.mediumterm (
    id         BIGSERIAL PRIMARY KEY,
    userid     TEXT NOT NULL,
    sessionid  TEXT,
    kind       TEXT NOT NULL,
    content    TEXT NOT NULL,
    embedding  vector(1536),
    importance FLOAT DEFAULT 1.0,
    metadata   JSONB,
    createdat  TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    expiresat  TIMESTAMPTZ NOT NULL,
    CONSTRAINT check_mediumterm_expires CHECK (expiresat > createdat)
);

-- Long-term memory (durable, searchable)
CREATE TABLE IF NOT EXISTS memory.longterm (
    id             BIGSERIAL PRIMARY KEY,
    userid         TEXT NOT NULL,
    scope          TEXT NOT NULL DEFAULT 'user', -- user, project, global
    kind           TEXT NOT NULL,                -- preference, fact, context, error, success
    content        TEXT NOT NULL,
    embedding      vector(1536),
    importance     FLOAT DEFAULT 1.0,
    tags           TEXT DEFAULT '',
    metadata       JSONB,
    createdat      TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updatedat      TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    lastaccessedat TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    accesscount    INT DEFAULT 0,
    CONSTRAINT check_scope CHECK (scope IN ('user', 'project', 'global'))
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_shortterm_user_expires
    ON memory.shortterm (userid, expiresat);

CREATE INDEX IF NOT EXISTS idx_shortterm_embedding
    ON memory.shortterm
    USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 100);

CREATE INDEX IF NOT EXISTS idx_mediumterm_user_expires
    ON memory.mediumterm (userid, expiresat);

CREATE INDEX IF NOT EXISTS idx_mediumterm_importance
    ON memory.mediumterm (userid, importance DESC)
    WHERE expiresat > CURRENT_TIMESTAMP;

CREATE INDEX IF NOT EXISTS idx_mediumterm_embedding
    ON memory.mediumterm
    USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 100);

CREATE INDEX IF NOT EXISTS idx_longterm_user_scope
    ON memory.longterm (userid, scope);

CREATE INDEX IF NOT EXISTS idx_longterm_kind
    ON memory.longterm (kind);

CREATE INDEX IF NOT EXISTS idx_longterm_tags
    ON memory.longterm
    USING GIN (tags);

CREATE INDEX IF NOT EXISTS idx_longterm_embedding
    ON memory.longterm
    USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 100);

CREATE INDEX IF NOT EXISTS idx_longterm_access
    ON memory.longterm (lastaccessedat DESC);

-- Materialized-like stats view
CREATE OR REPLACE VIEW memory.statsview AS
SELECT
    'shortterm' AS memorytype,
    COUNT(*) AS totalcount,
    COUNT(DISTINCT userid) AS uniqueusers,
    COALESCE(AVG(importance), 0) AS avgimportance,
    NOW() AS calculatedat
FROM memory.shortterm
WHERE expiresat > CURRENT_TIMESTAMP
UNION ALL
SELECT
    'mediumterm' AS memorytype,
    COUNT(*),
    COUNT(DISTINCT userid),
    COALESCE(AVG(importance), 0),
    NOW()
FROM memory.mediumterm
WHERE expiresat > CURRENT_TIMESTAMP
UNION ALL
SELECT
    'longterm' AS memorytype,
    COUNT(*),
    COUNT(DISTINCT userid),
    COALESCE(AVG(importance), 0),
    NOW()
FROM memory.longterm;

-- Audit table for memory operations
CREATE TABLE IF NOT EXISTS memory.auditlog (
    id        BIGSERIAL PRIMARY KEY,
    operation TEXT NOT NULL, -- INSERT, UPDATE, DELETE, SEARCH
    tablename TEXT NOT NULL,
    memoryid  BIGINT,
    userid    TEXT,
    status    TEXT NOT NULL DEFAULT 'success',
    details   JSONB,
    createdat TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_audit_user_timestamp
    ON memory.auditlog (userid, createdat DESC);
```

Direct from the spec.[2]

***

## `mcp-memory/main.py`

```python
import asyncio
import logging

from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.responses import JSONResponse

from .config import settings
from .db import close_db, init_db
from .mcpserver import MCPToolCall, get_mcp_tools, handle_tool_call
from .routes import router as routes_router

logging.basicConfig(
    level=settings.LOG_LEVEL,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


async def verify_api_key(authorization: str = Header(None)) -> str:
    """
    Verify MCP_API_KEY from Authorization header.
    Format: Authorization: Bearer <key>
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")
    token = authorization.replace("Bearer ", "", 1).strip()
    if token != settings.MCP_API_KEY:
        raise HTTPException(status_code=403, detail="Invalid API key")
    return token


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initializing MCP memory server database...")
    await init_db()
    logger.info("Database initialized; starting cleanup task")
    from .routes.memory import cleanup_task

    asyncio.create_task(cleanup_task())
    yield
    logger.info("Shutting down MCP memory server...")
    await close_db()
    logger.info("Shutdown complete")


app = FastAPI(
    title="L9 MCP Memory Server",
    description="OpenAI embeddings + pgvector semantic search for Cursor",
    version="1.0.0",
    lifespan=lifespan,
)


# Root + health from routes
app.include_router(routes_router)


@app.get("/mcptools")
async def list_tools(auth: str = Depends(verify_api_key)):
    """
    List all available MCP tools (Cursor discovery).
    """
    tools = get_mcp_tools()
    return tools


@app.post("/mcpcall")
async def call_tool(request: Request, auth: str = Depends(verify_api_key)):
    """
    Invoke an MCP tool.
    """
    try:
        payload = await request.json()
        tool_name = payload.get("toolName") or payload.get("toolname")
        tool_args = payload.get("arguments") or {}
        userid = payload.get("userid")
        if not userid:
            raise HTTPException(status_code=400, detail="userid required")

        tool_call = MCPToolCall(name=tool_name, arguments=tool_args)
        result = await handle_tool_call(tool_call, userid)
        return {"status": "success", "result": result}
    except HTTPException:
        raise
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Tool call error")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled exception")
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "mcp-memory.main:app",
        host=settings.MCP_HOST,
        port=settings.MCP_PORT,
        log_level=settings.LOG_LEVEL.lower(),
        reload=False,
    )
```

Implements the described MCP FastAPI app.[2]

***

## `mcp-memory/scripts/migrate_db.py`

```python
import asyncio
from pathlib import Path

from ..db import execute, init_db, close_db


async def main() -> None:
    base = Path(__file__).resolve().parents[1]
    schema_path = base / "schema" / "init.sql"
    sql = schema_path.read_text(encoding="utf-8")
    await init_db()
    # asyncpg cannot execute multiple statements in one call; split on ';'
    statements = [s.strip() for s in sql.split(";") if s.strip()]
    for stmt in statements:
        await execute(stmt)
    await close_db()


if __name__ == "__main__":
    asyncio.run(main())
```

***

## `mcp-memory/scripts/test_connection.py`

```python
import asyncio

from ..config import settings
from ..db import init_db, close_db
from ..embeddings import embed_text


async def main() -> None:
    print("Testing DB connection using DSN:", settings.MEMORY_DSN)
    await init_db()
    print("DB connection OK")
    emb = await embed_text("Test embedding from MCP memory server")
    print("Embedding length:", len(emb))
    await close_db()
    print("All tests passed")


if __name__ == "__main__":
    asyncio.run(main())
```

***

## `mcp-memory/scripts/install.sh`

```bash
#!/usr/bin/env bash
set -euo pipefail

echo
echo "L9 MCP Memory Server Installation"
echo

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BASE_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

MCP_DIR="${BASE_DIR}"
VENV_DIR="/opt/l9/venv-mcp"
TARGET_DIR="/opt/l9/mcp/memory"

echo "1/6 Creating target directory ${TARGET_DIR}..."
sudo mkdir -p "${TARGET_DIR}"
sudo chown -R "$(whoami)":"$(whoami)" "${TARGET_DIR}"

echo "2/6 Copying MCP server code to ${TARGET_DIR}..."
rsync -a --delete "${MCP_DIR}/" "${TARGET_DIR}/"

echo "3/6 Creating Python virtual environment at ${VENV_DIR}..."
python3.11 -m venv "${VENV_DIR}"
# shellcheck disable=SC1090
source "${VENV_DIR}/bin/activate"

echo "4/6 Installing dependencies..."
pip install --upgrade pip
pip install -r "${TARGET_DIR}/requirements-mcp.txt"

echo "5/6 Running database schema init..."
python "${TARGET_DIR}/scripts/migrate_db.py"

echo "6/6 Installing systemd service..."
sudo cp "${TARGET_DIR}/systemd-l9-mcp.service" "/etc/systemd/system/l9-mcp.service"
sudo systemctl daemon-reload
sudo systemctl enable l9-mcp
sudo systemctl restart l9-mcp

echo
echo "Installation complete!"
echo "Check status: sudo systemctl status l9-mcp"
echo "View logs:    sudo journalctl -u l9-mcp -f"
echo "Test locally on VPS: curl http://127.0.0.1:9001/health"
```

***

## `mcp-memory/requirements-mcp.txt`

```text
fastapi==0.115.0
uvicorn[standard]==0.30.0
httpx==0.27.0
asyncpg==0.29.0
psycopg[binary]==3.1.0
pgvector==0.2.5
openai==1.0.0
tenacity==8.2.0
pydantic==2.9.0
pydantic-settings==2.0.0
python-dotenv==1.0.0
pyyaml==6.0.1
```

Based on the spec’s dependency list.[2]

***

## `mcp-memory/.env.example`

```env
# MCP Memory Server Configuration

# Server
MCP_HOST=127.0.0.1
MCP_PORT=9001
MCP_ENV=production
LOG_LEVEL=INFO

# OpenAI
OPENAI_API_KEY=sk-proj-YOURKEYHERE
OPENAI_EMBED_MODEL=text-embedding-3-small

# PostgreSQL - must point at same Postgres as L9 OS, l9memory DB
MEMORY_DSN=postgresql://postgres:YOURPASSWORD@127.0.0.1:5432/l9memory

# Memory behavior
MEMORY_SHORTTERM_HOURS=1
MEMORY_MEDIUMTERM_HOURS=24
MEMORY_CLEANUP_INTERVAL_MINUTES=60
MEMORY_SHORT_RETENTION_DAYS=7
MEMORY_MEDIUM_RETENTION_DAYS=30

# Vector search
VECTOR_SEARCH_THRESHOLD=0.7
VECTOR_SEARCH_TOP_K=10

# MCP client auth
MCP_API_KEY=generate-with-openssl-rand-hex-32

# Optional Redis cache
REDIS_ENABLED=false
REDIS_HOST=127.0.0.1
REDIS_PORT=6379
```

Matches the example in the spec.[2]

***

## `mcp-memory/systemd-l9-mcp.service`

```ini
[Unit]
Description=L9 MCP Memory Server
After=network.target postgresql.service
StartLimitIntervalSec=60
StartLimitBurst=3

[Service]
Type=simple
User=admin
WorkingDirectory=/opt/l9/mcp/memory
Environment=PATH=/opt/l9/venv-mcp/bin
ExecStart=/opt/l9/venv-mcp/bin/python -m mcp-memory.main
Restart=on-failure
RestartSec=10
StandardOutput=journal
StandardError=journal
SyslogIdentifier=l9-mcp

[Install]
WantedBy=multi-user.target
```

Aligned with `l9-mcp.service` described.[2]

***

## `mcp-memory/README.md` (minimal)

```markdown
# L9 MCP Memory Server

Standalone FastAPI + pgvector memory server for Cursor MCP clients, backed by the same PostgreSQL `l9memory` database that L9 OS uses.

## Layout

- `main.py` – FastAPI app and MCP endpoints (`/mcptools`, `/mcpcall`).
- `mcpserver.py` – MCP tool definitions and dispatcher.
- `db.py` – asyncpg connection pool and helpers.
- `embeddings.py` – OpenAI embedding helpers.
- `models.py` – Pydantic schemas for memory save/search/stats.
- `config.py` – Environment-based configuration.
- `routes/memory.py` – HTTP memory CRUD/search, cleanup task.
- `routes/health.py` – Health endpoint.
- `schema/init.sql` – `memory.*` tables, indexes, audit log.
- `scripts/migrate_db.py` – Run schema init.
- `scripts/test_connection.py` – Sanity check for DB + embeddings.
- `scripts/install.sh` – Copy to `/opt/l9/mcp/memory`, create venv, install deps, run schema, install systemd.
- `systemd-l9-mcp.service` – Systemd unit definition.
- `requirements-mcp.txt` – Python dependencies.
- `.env.example` – Configuration template.

## Quick start (local)

1. `cd mcp-memory`
2. `cp .env.example .env` and fill `OPENAI_API_KEY` and `MEMORY_DSN`.
3. `python3.11 -m venv venv && source venv/bin/activate`
4. `pip install -r requirements-mcp.txt`
5. `python scripts/migrate_db.py`
6. `uvicorn mcp-memory.main:app --host 127.0.0.1 --port 9001`

Health: `curl http://127.0.0.1:9001/health`
Tools: `curl -H "Authorization: Bearer $MCP_API_KEY" http://127.0.0.1:9001/mcptools`
```

***

## How this fits Option A

- Once you drop `mcp-memory/` in your L9 repo and deploy to `/opt/l9/mcp/memory` via `scripts/install.sh`, you will have the MCP server described in `L9-MCP-IMPL.md` running against the same Postgres `l9memory` DB your L9 OS uses.[1][2]
- C (Cursor) can then use an MCP config pointing at `http://127.0.0.1:9001` over SSH, with `MCP_API_KEY` from `.env`, and pass whatever `userid` you want for C’s memory namespace.[2]

To make it downloadable as an artifact, save this exact structure and files into your repo, then archive `mcp-memory/` as a zip or let Cursor’s file panel download that folder.
