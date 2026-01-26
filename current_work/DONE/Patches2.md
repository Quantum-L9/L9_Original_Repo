mcp_memory/src/__init__.py
mcp_memory/src/__init__.py
+4
-0

"""
L9 MCP Memory Server.

Semantic memory service for Cursor IDE integration.
Provides MCP (Model Context Protocol) tools for saving, querying,
and managing context memories via OpenAI embeddings + pgvector.

Created: 2025-12-27
Modified: 2026-01-01
Author: L9 Team
"""

from src.rate_limiter import RateLimiter

__version__ = "1.0.0"

__all__ = ["RateLimiter"]
mcp_memory/src/main.py
mcp_memory/src/main.py
+35
-44

"""FastAPI MCP Memory Server."""

import structlog
import time
from collections import defaultdict
from fastapi import FastAPI, HTTPException, Depends, Header, Request
from fastapi.responses import JSONResponse
from pydantic import ValidationError
import asyncpg
from contextlib import asynccontextmanager
import asyncio

from src.config import settings
from src.db import init_db, close_db
from src.mcp_server import get_mcp_tools, MCPToolCall, handle_tool_call
from src.routes import memory_unified as memory, health
from src.rate_limiter import RateLimiter

# Configure structlog
# Use structlog log levels (no need for logging module)
log_level_map = {
    "DEBUG": 10,
    "INFO": 20,
    "WARNING": 30,
    "ERROR": 40,
    "CRITICAL": 50,
}
log_level = log_level_map.get(settings.LOG_LEVEL.upper(), 20)  # Default to INFO (20)
structlog.configure(
    wrapper_class=structlog.make_filtering_bound_logger(log_level),
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer(),
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger(__name__)

# =============================================================================
# Rate Limiting (in-memory, per-IP)
# =============================================================================
RATE_LIMIT_REQUESTS = 60  # Max requests per window
RATE_LIMIT_WINDOW = 60  # Window in seconds (1 minute)
FAILED_AUTH_LIMIT = 5  # Max failed auth attempts before block
FAILED_AUTH_BLOCK_SECONDS = 300  # Block for 5 minutes after too many failures

# Track requests per IP: {ip: [(timestamp, success), ...]}
request_log: dict = defaultdict(list)
# Track failed auth attempts: {ip: [timestamp, ...]}
failed_auth_log: dict = defaultdict(list)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initializing database...")
    await init_db()
    logger.info("✓ Database initialized")

    # Initialize L9 Memory Substrate Service (uses same pipeline as L agent)
    logger.info("Initializing L9 Memory Substrate Service...")
    try:
        from memory.substrate_service import init_service
        import os

        database_url = settings.MEMORY_DSN or os.getenv("DATABASE_URL")
        if not database_url:
            logger.warning(
                "MEMORY_DSN not set. MCP memory will use direct DB access. "
                "Set MEMORY_DSN to enable full DAG pipeline (graph sync, fact extraction, etc.)"
            )
        else:
            substrate_service = await init_service(
                database_url=database_url,
                embedding_provider_type=os.getenv("EMBEDDING_PROVIDER", "openai"),
                embedding_model=os.getenv("EMBEDDING_MODEL", "text-embedding-3-large"),
                openai_api_key=settings.OPENAI_API_KEY or os.getenv("OPENAI_API_KEY"),
            )
            # Store in app state for route handlers
            app.state.substrate_service = substrate_service
            logger.info("✓ L9 Memory Substrate Service initialized (full DAG pipeline enabled)")
    except Exception as e:
        logger.warning(
            f"Failed to initialize Memory Substrate Service: {e}. "
            "MCP memory will fall back to direct DB access."
        )
        app.state.substrate_service = None

    app.state.rate_limiter = RateLimiter(
        request_limit=RATE_LIMIT_REQUESTS,
        request_window_seconds=RATE_LIMIT_WINDOW,
        failed_auth_limit=FAILED_AUTH_LIMIT,
        failed_auth_block_seconds=FAILED_AUTH_BLOCK_SECONDS,
    )

    asyncio.create_task(memory.cleanup_task())  # Background cleanup task
    yield
    logger.info("Closing database connections...")
    await close_db()

    # Close memory service if initialized
    if hasattr(app.state, "substrate_service") and app.state.substrate_service:
        from memory.substrate_service import close_service
        await close_service()

    logger.info("✓ Shutdown complete")


app = FastAPI(
    title="L9 MCP Memory Server",
    description="OpenAI embeddings + pgvector semantic search for Cursor",
    version="1.0.0",
    lifespan=lifespan,
)


def get_client_ip(request: Request) -> str:
    """Get client IP, respecting X-Forwarded-For for proxies."""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def check_rate_limit(ip: str) -> None:
    """Check if IP has exceeded rate limit. Raises 429 if so."""
    now = time.time()
    cutoff = now - RATE_LIMIT_WINDOW

    # Clean old entries
    request_log[ip] = [(ts, ok) for ts, ok in request_log[ip] if ts > cutoff]

    if len(request_log[ip]) >= RATE_LIMIT_REQUESTS:
        logger.warning(f"Rate limit exceeded for IP: {ip}")
        raise HTTPException(status_code=429, detail="Rate limit exceeded. Try again later.")


def check_auth_block(ip: str) -> None:
    """Check if IP is blocked due to failed auth attempts."""
    now = time.time()
    cutoff = now - FAILED_AUTH_BLOCK_SECONDS

    # Clean old entries
    failed_auth_log[ip] = [ts for ts in failed_auth_log[ip] if ts > cutoff]

    if len(failed_auth_log[ip]) >= FAILED_AUTH_LIMIT:
        logger.warning(f"IP blocked due to failed auth attempts: {ip}")
        raise HTTPException(status_code=403, detail="Too many failed attempts. Blocked temporarily.")


def record_failed_auth(ip: str) -> None:
    """Record a failed authentication attempt."""
    failed_auth_log[ip].append(time.time())
    logger.warning(f"Failed auth attempt from IP: {ip} (total: {len(failed_auth_log[ip])})")


class CallerIdentity:
    """Caller identity determined from API key.

    See: mcp_memory/memory-setup-instructions.md for governance spec.
    - L: L-CTO kernel (full read/write/delete for shared userid)
    - C: Cursor IDE (read all, write/delete own memories only)
    """
    def __init__(self, caller_id: str, user_id: str):
        self.caller_id = caller_id  # "L" or "C"
        self.user_id = user_id      # Shared userid
        self.is_l = caller_id == "L"
        self.is_c = caller_id == "C"

    @property
    def creator(self) -> str:
        """Metadata creator value for this caller."""
        return "L-CTO" if self.is_l else "Cursor-IDE"

    @property
    def source(self) -> str:
        """Metadata source value for this caller."""
        return "l9-kernel" if self.is_l else "cursor-ide"


async def verify_api_key(request: Request, authorization: str = Header(None)) -> CallerIdentity:
    """Verify API key and return caller identity with rate limiting and brute-force protection.

    Returns CallerIdentity with:
    - caller_id: "L" or "C"
    - user_id: Shared userid (L_CTO_USER_ID)
    - creator/source: For metadata enforcement
    """
    ip = get_client_ip(request)

    rate_limiter = getattr(request.app.state, "rate_limiter", None)
    if rate_limiter is None:
        rate_limiter = RateLimiter(
            request_limit=RATE_LIMIT_REQUESTS,
            request_window_seconds=RATE_LIMIT_WINDOW,
            failed_auth_limit=FAILED_AUTH_LIMIT,
            failed_auth_block_seconds=FAILED_AUTH_BLOCK_SECONDS,
        )
        request.app.state.rate_limiter = rate_limiter

    # Check if IP is blocked
    check_auth_block(ip)

    if await rate_limiter.is_auth_blocked(ip):
        logger.warning(f"IP blocked due to failed auth attempts: {ip}")
        raise HTTPException(status_code=403, detail="Too many failed attempts. Blocked temporarily.")

    # Check rate limit
    check_rate_limit(ip)

    if await rate_limiter.is_rate_limited(ip):
        logger.warning(f"Rate limit exceeded for IP: {ip}")
        raise HTTPException(status_code=429, detail="Rate limit exceeded. Try again later.")

    # Record this request
    request_log[ip].append((time.time(), True))
    await rate_limiter.record_request(ip, now=time.time())

    if not authorization or not authorization.startswith("Bearer "):
        record_failed_auth(ip)
        await rate_limiter.record_failed_auth(ip, now=time.time())
        snapshot = await rate_limiter.snapshot(ip)
        logger.warning(
            "Failed auth attempt from IP",
            ip=ip,
            failed_auth_count=snapshot.failed_auth_count,
            version=snapshot.version,
        )
        raise HTTPException(
            status_code=401, detail="Missing or invalid Authorization header"
        )
    token = authorization.replace("Bearer ", "")

    # Determine caller from API key (with legacy fallback support)
    from src.config import get_api_key_l, get_api_key_c

    api_key_l = get_api_key_l()
    api_key_c = get_api_key_c()

    # Primary keys first
    if api_key_l and token == api_key_l:
        return CallerIdentity(caller_id="L", user_id=settings.L_CTO_USER_ID)
    elif api_key_c and token == api_key_c:
        return CallerIdentity(caller_id="C", user_id=settings.L_CTO_USER_ID)
    # Legacy fallback: MCP_API_KEY / MCPL9MEMORYKEY → shared identity (defaults to L)
    elif settings.MCP_API_KEY and token == settings.MCP_API_KEY:
        return CallerIdentity(caller_id="L", user_id=settings.L_CTO_USER_ID)  # Legacy → L
    elif settings.MCPL9MEMORYKEY and token == settings.MCPL9MEMORYKEY:
        return CallerIdentity(caller_id="L", user_id=settings.L_CTO_USER_ID)  # Legacy → L
    else:
        record_failed_auth(ip)
        raise HTTPException(status_code=403, detail="Invalid API key")

mcp_memory/src/models.py
mcp_memory/src/models.py
+1
-0

@@ -15,50 +15,51 @@ class SaveMemoryRequest(BaseModel):
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
    track_access: Optional[bool] = False


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


mcp_memory/src/rate_limiter.py
mcp_memory/src/rate_limiter.py
New
+142
-0

"""Async-safe, versioned rate limiter for in-memory request tracking."""

from __future__ import annotations

import asyncio
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Deque, Dict, Optional


@dataclass
class RateLimitBucket:
    """Mutable bucket for a single IP, tracked with a version counter."""

    request_timestamps: Deque[float] = field(default_factory=deque)
    failed_auth_timestamps: Deque[float] = field(default_factory=deque)
    version: int = 0


@dataclass(frozen=True)
class RateLimitSnapshot:
    """Immutable snapshot for audit/testing."""

    request_count: int
    failed_auth_count: int
    version: int


class RateLimiter:
    """Async-safe in-memory rate limiter with versioned buckets."""

    def __init__(
        self,
        request_limit: int,
        request_window_seconds: int,
        failed_auth_limit: int,
        failed_auth_block_seconds: int,
    ) -> None:
        self._request_limit = request_limit
        self._request_window_seconds = request_window_seconds
        self._failed_auth_limit = failed_auth_limit
        self._failed_auth_block_seconds = failed_auth_block_seconds
        self._lock = asyncio.Lock()
        self._buckets: Dict[str, RateLimitBucket] = {}

    async def is_rate_limited(self, ip: str, now: Optional[float] = None) -> bool:
        """Return True if the IP has exceeded the request limit."""
        current_time = now if now is not None else time.time()
        async with self._lock:
            bucket = self._get_bucket(ip)
            self._prune(bucket, current_time, self._request_window_seconds, "request")
            return len(bucket.request_timestamps) >= self._request_limit

    async def is_auth_blocked(self, ip: str, now: Optional[float] = None) -> bool:
        """Return True if the IP has exceeded failed auth attempts."""
        current_time = now if now is not None else time.time()
        async with self._lock:
            bucket = self._get_bucket(ip)
            self._prune(
                bucket,
                current_time,
                self._failed_auth_block_seconds,
                "failed_auth",
            )
            return len(bucket.failed_auth_timestamps) >= self._failed_auth_limit

    async def record_request(self, ip: str, now: Optional[float] = None) -> int:
        """Record a request for the IP and return the new bucket version."""
        current_time = now if now is not None else time.time()
        async with self._lock:
            bucket = self._get_bucket(ip)
            self._prune(bucket, current_time, self._request_window_seconds, "request")
            expected_version = bucket.version
            self._assert_version(bucket, expected_version)
            bucket.request_timestamps.append(current_time)
            bucket.version += 1
            return bucket.version

    async def record_failed_auth(self, ip: str, now: Optional[float] = None) -> int:
        """Record a failed auth attempt and return the new bucket version."""
        current_time = now if now is not None else time.time()
        async with self._lock:
            bucket = self._get_bucket(ip)
            self._prune(
                bucket,
                current_time,
                self._failed_auth_block_seconds,
                "failed_auth",
            )
            expected_version = bucket.version
            self._assert_version(bucket, expected_version)
            bucket.failed_auth_timestamps.append(current_time)
            bucket.version += 1
            return bucket.version

    async def snapshot(self, ip: str) -> RateLimitSnapshot:
        """Return a snapshot of the bucket for audits/tests."""
        async with self._lock:
            bucket = self._get_bucket(ip)
            return RateLimitSnapshot(
                request_count=len(bucket.request_timestamps),
                failed_auth_count=len(bucket.failed_auth_timestamps),
                version=bucket.version,
            )

    def _get_bucket(self, ip: str) -> RateLimitBucket:
        bucket = self._buckets.get(ip)
        if bucket is None:
            bucket = RateLimitBucket()
            self._buckets[ip] = bucket
        return bucket

    def _prune(
        self,
        bucket: RateLimitBucket,
        now: float,
        window_seconds: int,
        bucket_type: str,
    ) -> None:
        cutoff = now - window_seconds
        timestamps = (
            bucket.request_timestamps
            if bucket_type == "request"
            else bucket.failed_auth_timestamps
        )
        expected_version = bucket.version
        removed_any = False
        while timestamps and timestamps[0] <= cutoff:
            timestamps.popleft()
            removed_any = True
        if removed_any:
            self._assert_version(bucket, expected_version)
            bucket.version += 1

    @staticmethod
    def _assert_version(bucket: RateLimitBucket, expected_version: int) -> None:
        if bucket.version != expected_version:
            raise RuntimeError(
                "Rate limiter bucket version mismatch; "
                "concurrent mutation detected."
            )
mcp_memory/src/routes/memory.py
mcp_memory/src/routes/memory.py
+3
-1

@@ -129,61 +129,63 @@ async def save_memory_handler(
            "success",
            json.dumps({
                "duration": duration,
                "kind": kind,
                "caller": caller_id,
                "creator": creator,
                "source": source,
            }),
        )
        return result
    except Exception as e:
        logger.exception("Error saving memory")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/search", response_model=SearchMemoryResponse)
async def search_memory(req: SearchMemoryRequest) -> SearchMemoryResponse:
    return await search_memory_handler(
        user_id=req.user_id,
        query=req.query,
        scopes=req.scopes,
        kinds=req.kinds,
        top_k=req.top_k,
        threshold=req.threshold,
        duration=req.duration,
        track_access=req.track_access,
    )


async def search_memory_handler(
    user_id: str,
    query: str,
    scopes: Optional[List[str]] = None,
    kinds: Optional[List[str]] = None,
    top_k: int = 5,
    threshold: float = 0.7,
    duration: str = "all",
    track_access: bool = False,
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
                table, where = (
                    "memory.medium_term",
                    "AND expires_at > CURRENT_TIMESTAMP",
                )
            else:
                table, where = "memory.long_term", ""

            params = [user_id]
            param_idx = 2
            scope_clause, kind_clause = "", ""

@@ -191,51 +193,51 @@ async def search_memory_handler(
                scope_clause = f"AND scope IN ({', '.join([f'${i}' for i in range(param_idx, param_idx + len(scopes))])})"
                params.extend(scopes)
                param_idx += len(scopes)

            if kinds:
                kind_clause = f"AND kind IN ({', '.join([f'${i}' for i in range(param_idx, param_idx + len(kinds))])})"
                params.extend(kinds)
                param_idx += len(kinds)

            cols = (
                "id, user_id, kind, content, importance, tags, created_at"
                if dur == "long"
                else "id, user_id, kind, content, importance, created_at"
            )
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
            if track_access and dur == "long" and rows:
                await execute(
                    "UPDATE memory.long_term SET last_accessed_at = CURRENT_TIMESTAMP, access_count = access_count + 1 WHERE id = ANY($1::bigint[]);",
                    [r["id"] for r in rows],
                )

            results.extend(rows)

        results.sort(key=lambda x: x.get("similarity", 0), reverse=True)
        results = results[:top_k]
        search_time_ms = (time.time() - search_start) * 1000

        await execute(
            "INSERT INTO memory.audit_log (operation, user_id, status, details) VALUES ($1, $2, $3, $4)",
            "SEARCH",
            user_id,
            "success",
            json.dumps({"query": query, "results_count": len(results)}),
        )

        return {
            "results": results,
            "query_embedding_time_ms": embed_time_ms,
            "search_time_ms": search_time_ms,
            "total_results": len(results),
        }
mcp_memory/src/routes/memory_unified.py
mcp_memory/src/routes/memory_unified.py
+4
-3

@@ -427,50 +427,51 @@ async def _save_via_direct_db(
    )

    return {
        "packet_id": str(packet_id),
        "embedding_id": str(embedding_result["embedding_id"]),
        "user_id": user_id,
        "kind": kind,
        "scope": scope,
        "content": content[:100] + "..." if len(content) > 100 else content,
        "importance": importance,
        "created_at": timestamp.isoformat(),
        "embed_time_ms": embed_time_ms,
        "pipeline": "direct_db",  # Indicates fallback path was used
    }


async def search_memory_handler(
    user_id: str,
    query: str,
    scopes: Optional[List[str]] = None,  # MCP scopes: ['developer', 'global'] for Cursor
    kinds: Optional[List[str]] = None,
    top_k: int = 5,
    threshold: float = 0.7,
    duration: str = "all",
    caller_id: str = "unknown",  # Perplexity: for audit logging
    track_access: bool = False,
) -> Dict[str, Any]:
    """
    Search unified L9 substrate using memory_embeddings with packet_store join.

    Uses vector similarity search on memory_embeddings, then joins to packet_store
    for full envelope data and scope filtering.
    """
    try:
        embed_start = time.time()
        query_embedding = await embed_text(query)
        embed_time_ms = (time.time() - embed_start) * 1000

        # Convert embedding vector to string format for pgvector
        # pgvector expects format: '[1.0,2.0,3.0]'
        query_embedding_str = f"[{','.join(str(v) for v in query_embedding)}]"

        # Map MCP scopes to DB scopes
        db_scopes = [map_mcp_scope_to_db_scope(s) for s in (scopes or ["developer", "global"])]

        search_start = time.time()

        # Build WHERE clause for scope filtering
        scope_filter = ""
        params = [query_embedding_str, threshold, top_k]
        param_idx = 4
@@ -511,52 +512,52 @@ async def search_memory_handler(
        search_query = f"""
        SELECT
            ps.packet_id,
            ps.packet_type,
            ps.envelope,
            ps.scope as db_scope,
            ps.timestamp,
            ps.importance_score,
            ps.tags,
            me.embedding_id,
            me.chunk_text,
            1 - (me.vector <-> $1::vector) as similarity
        FROM memory_embeddings me
        INNER JOIN packet_store ps ON me.packet_id = ps.packet_id
        WHERE me.embedding_type = 'content'
        {scope_filter}  -- Perplexity: SQL-level scope enforcement
        {kind_filter}
        {duration_filter}
        AND 1 - (me.vector <-> $1::vector) >= $2
        ORDER BY similarity DESC
        LIMIT $3;
        """

        rows = await fetch_all(search_query, *params)

        # Update access tracking
        if rows:
        # Update access tracking (explicit opt-in)
        if track_access and rows:
            packet_ids = [r["packet_id"] for r in rows]
            await execute(
                """
                UPDATE packet_store
                SET access_count = access_count + 1,
                    last_accessed = CURRENT_TIMESTAMP
                WHERE packet_id = ANY($1::uuid[]);
                """,
                packet_ids,
            )

        # Format results
        results = []
        for row in rows:
            envelope = row["envelope"]
            # Defensive: Handle case where envelope is returned as string (missing JSON codec)
            if isinstance(envelope, str):
                try:
                    envelope = json.loads(envelope)
                except json.JSONDecodeError:
                    envelope = {}
            payload = envelope.get("payload", {}) if isinstance(envelope, dict) else {}
            mcp_scope = map_db_scope_to_mcp_scope(row["db_scope"])

            results.append({
@@ -614,50 +615,51 @@ async def save_memory_route(
        content=req["content"],
        kind=req["kind"],
        scope=req.get("scope", "developer"),
        duration=req.get("duration", "long"),
        tags=req.get("tags", []),
        importance=req.get("importance", 1.0),
        metadata=req.get("metadata"),
        caller_id=req.get("caller_id", "unknown"),
        creator=req.get("creator", "unknown"),
        source=req.get("source", "unknown"),
        substrate_service=substrate_service,
    )


@router.post("/search")
async def search_memory_route(req: Dict[str, Any]) -> Dict[str, Any]:
    """REST endpoint for searching memory."""
    return await search_memory_handler(
        user_id=req.get("user_id", settings.L_CTO_USER_ID),
        query=req["query"],
        scopes=req.get("scopes", ["developer", "global"]),
        kinds=req.get("kinds"),
        top_k=req.get("top_k", 5),
        threshold=req.get("threshold", 0.7),
        duration=req.get("duration", "all"),
        track_access=req.get("track_access", False),
    )


# =============================================================================
# Stats and Maintenance Handlers
# =============================================================================

@router.get("/stats")
async def get_memory_stats(
    user_id: Optional[str] = Query(None),
    duration: str = Query("all")
) -> Dict[str, Any]:
    """
    Get memory statistics from unified substrate.

    Queries packet_store instead of deprecated memory.* tables.
    """
    try:
        # Use user_id from metadata.envelope->>'metadata'->>'user_id' or filter by scope
        user_filter = ""
        params = []
        param_idx = 1

        if user_id:
            # Filter by envelope metadata (user_id is in envelope JSONB)
@@ -1443,26 +1445,25 @@ async def save_memory_with_confidence(
            kind=kind,
            scope=scope,
            duration=duration,
            tags=all_tags,
            importance=effective_importance,
            metadata=metadata,
            caller_id=caller_id,
            creator=creator,
            source=source,
        )

        # Log relationships if provided
        if related_memory_ids:
            for related_id in related_memory_ids:
                # Store relationship in envelope metadata (could also use separate table)
                logger.debug(
                    "Memory relationship logged",
                    packet_id=result["packet_id"],
                    related_to=related_id,
                )

        return result
    except Exception as e:
        logger.exception("Error saving memory with confidence")
        raise HTTPException(status_code=500, detail=str(e))

mcp_memory/tests/test_rate_limiter.py
mcp_memory/tests/test_rate_limiter.py
New
+40
-0

import pytest

from src.rate_limiter import RateLimiter


@pytest.mark.asyncio
async def test_rate_limit_blocks_after_limit() -> None:
    limiter = RateLimiter(
        request_limit=2,
        request_window_seconds=60,
        failed_auth_limit=3,
        failed_auth_block_seconds=300,
    )
    now = 1000.0
    ip = "127.0.0.1"

    assert await limiter.is_rate_limited(ip, now=now) is False
    await limiter.record_request(ip, now=now)
    assert await limiter.is_rate_limited(ip, now=now) is False
    await limiter.record_request(ip, now=now + 1)
    assert await limiter.is_rate_limited(ip, now=now + 1) is True


@pytest.mark.asyncio
async def test_failed_auth_block_expires() -> None:
    limiter = RateLimiter(
        request_limit=10,
        request_window_seconds=60,
        failed_auth_limit=2,
        failed_auth_block_seconds=30,
    )
    now = 2000.0
    ip = "10.0.0.1"

    await limiter.record_failed_auth(ip, now=now)
    assert await limiter.is_auth_blocked(ip, now=now) is False
    await limiter.record_failed_auth(ip, now=now + 1)
    assert await limiter.is_auth_blocked(ip, now=now + 1) is True

    assert await limiter.is_auth_blocked(ip, now=now + 40) is False
memory/ingestion.py
memory/ingestion.py
+27
-21

"""
L9 Memory Substrate - Ingestion Pipeline
Version: 1.1.0

Real PacketEnvelope ingestion with:
- Validation
- Embedding generation via substrate_semantic
- Structured packet storage
- Vector storage
- Artifact handling
- Lineage tracking
- Tag assignment

All operations are async-safe with proper logging.
"""

from __future__ import annotations

import structlog
from functools import lru_cache
from typing import Optional, TYPE_CHECKING
from typing import Any, Optional, TYPE_CHECKING
from uuid import uuid4

if TYPE_CHECKING:
    import asyncpg
    from memory.substrate_dag import SubstrateDAG

from core.schemas import PacketEnvelope, PacketEnvelopeIn, PacketWriteResult
from memory.substrate_service import MemorySubstrateService
from memory.graph_client import get_neo4j_client
from memory.validators.packet_validator import PacketValidator, PacketValidationError
from memory.audit_utils import prepare_packet_for_ingest

logger = structlog.get_logger(__name__)


class IngestionPipeline:
    """
    PacketEnvelope ingestion pipeline.

    Handles the full lifecycle of packet ingestion:
    1. Validation
    2. Content embedding
    3. Structured storage
    4. Vector storage
    5. Lineage updates
@@ -164,83 +164,90 @@ class IngestionPipeline:

        written_tables = []
        errors = []

        # Validate
        validation_errors = self._validate_packet(packet_in)
        if validation_errors:
            return PacketWriteResult(
                packet_id=packet_in.packet_id or uuid4(),
                written_tables=[],
                status="error",
                error_message="; ".join(validation_errors),
            )

        # Convert to envelope
        envelope = packet_in.to_envelope()

        # Auto-generate tags if enabled
        if should_tag:
            auto_tags = self._generate_tags(envelope)
            # Use model_copy() since PacketEnvelope is frozen (immutable)
            envelope = envelope.model_copy(
                update={"tags": list(set(envelope.tags + auto_tags))}
            )

        embedding_payload = None
        if should_embed and self._semantic_service:
            try:
                embedding_payload = await self._prepare_embedding(envelope)
            except Exception as e:
                logger.error(f"Failed to generate embedding vector: {e}")
                errors.append(f"embedding: {str(e)}")

        # Core writes in transaction (atomic)
        # Wrap packet_store and agent_memory_events in transaction for atomicity
        if self._repository:
            try:
                async with self._repository.transaction() as conn:
                    # Store structured packet (uses transaction connection)
                    await self._store_packet_with_connection(envelope, conn)
                    written_tables.append("packet_store")

                    # Store memory event (uses same transaction connection)
                    await self._store_memory_event_with_connection(envelope, conn)
                    written_tables.append("agent_memory_events")

                    if embedding_payload:
                        vector, payload, agent_id = embedding_payload
                        await self._repository.insert_semantic_embedding(
                            vector=vector,
                            payload=payload,
                            agent_id=agent_id,
                        )
                        written_tables.append("semantic_memory")

                    # Transaction commits here (or rolls back on exception)
            except Exception as e:
                logger.error(f"Transaction failed for core writes: {e}")
                errors.append(f"transaction: {str(e)}")
                # Transaction auto-rolls back on exception
        else:
            # Fallback if repository not available (should not happen)
            logger.warning("Repository not available for transactional writes")
            errors.append("repository: not available")

        # Generate and store embedding
        if should_embed and self._semantic_service:
            try:
                embedded = await self._embed_content(envelope)
                if embedded:
                    written_tables.append("semantic_memory")
            except Exception as e:
                logger.error(f"Failed to embed content: {e}")
                errors.append(f"embedding: {str(e)}")

        # Store artifacts
        try:
            artifact_count = await self._store_artifacts(envelope)
            if artifact_count > 0:
                written_tables.append("artifacts")
        except Exception as e:
            logger.error(f"Failed to store artifacts: {e}")
            errors.append(f"artifacts: {str(e)}")

        # Update lineage
        try:
            await self._update_lineage(envelope)
        except Exception as e:
            logger.error(f"Failed to update lineage: {e}")
            errors.append(f"lineage: {str(e)}")

        # Sync to Neo4j knowledge graph (non-blocking, best-effort)
        try:
            await self._sync_to_graph(envelope)
            written_tables.append("neo4j_graph")
        except Exception as e:
            logger.warning(f"Neo4j graph sync failed (non-critical): {e}")
            # Don't add to errors - Neo4j is optional enhancement

        status = "ok" if not errors else "partial" if written_tables else "error"
@@ -466,96 +473,95 @@ class IngestionPipeline:
            event_type=envelope.packet_type,
            content=envelope.payload,
            packet_id=envelope.packet_id,
            timestamp=envelope.timestamp,
        )

    async def _store_memory_event_with_connection(
        self, envelope: PacketEnvelope, conn: "asyncpg.Connection"
    ) -> None:
        """Store memory event using provided connection (for transactions)."""
        if self._repository is None:
            return

        agent_id = envelope.metadata.agent if envelope.metadata else "default"

        # Use repository's insert_memory_event which will detect RLS connection from context
        # The connection is stored in context variable by transaction()
        await self._repository.insert_memory_event(
            agent_id=agent_id or "default",
            event_type=envelope.packet_type,
            content=envelope.payload,
            packet_id=envelope.packet_id,
            timestamp=envelope.timestamp,
        )

    async def _embed_content(self, envelope: PacketEnvelope) -> bool:
    async def _prepare_embedding(
        self, envelope: PacketEnvelope
    ) -> Optional[tuple[list[float], dict[str, Any], Optional[str]]]:
        """
        Generate and store embedding for packet content.
        Generate embedding vector and payload for packet content.

        Returns True if embedding was created.
        Returns (vector, payload, agent_id) if embedding is created.
        """
        if self._semantic_service is None:
            return False
            return None

        # Determine text to embed
        payload = envelope.payload
        text_to_embed = (
            payload.get("text")
            or payload.get("content")
            or payload.get("description")
            or payload.get("summary")
            or payload.get("message")
        )

        if not text_to_embed:
            # Skip packets without embeddable text
            return False
            return None

        if not isinstance(text_to_embed, str):
            text_to_embed = str(text_to_embed)

        # Minimum text length
        if len(text_to_embed) < 10:
            return False
            return None

        # Generate and store embedding
        agent_id = envelope.metadata.agent if envelope.metadata else None

        await self._semantic_service.embed_and_store(
        return await self._semantic_service.generate_embedding(
            text=text_to_embed,
            payload={
                "packet_id": str(envelope.packet_id),
                "packet_type": envelope.packet_type,
                "thread_id": str(envelope.thread_id) if envelope.thread_id else None,
                "timestamp": envelope.timestamp.isoformat(),
            },
            agent_id=agent_id,
        )

        return True

    async def _store_artifacts(self, envelope: PacketEnvelope) -> int:
        """
        Store any artifacts associated with the packet.

        Artifacts are extracted from payload.artifacts field.

        Returns count of stored artifacts.
        """
        artifacts = envelope.payload.get("artifacts", [])

        if not artifacts or not isinstance(artifacts, list):
            return 0

        # For now, artifacts are stored inline in packet payload
        # Future: separate artifact storage
        return len(artifacts)

    async def _update_lineage(self, envelope: PacketEnvelope) -> None:
        """
        Update lineage graph for the packet.

        If packet has parent_ids, verify they exist and update
        the lineage tracking.
        """
        if not envelope.lineage:
memory/substrate_repository.py
memory/substrate_repository.py
+32
-13

@@ -755,67 +755,86 @@ class SubstrateRepository:
                for r in rows
            ]

    # =========================================================================
    # Semantic Memory Operations (pgvector)
    # =========================================================================

    async def insert_semantic_embedding(
        self,
        vector: list[float],
        payload: dict[str, Any],
        agent_id: Optional[str] = None,
    ) -> UUID:
        """
        Insert a semantic embedding into semantic_memory.

        Args:
            vector: Embedding vector (1536 dimensions for text-embedding-3-large)
            payload: JSON payload associated with this embedding
            agent_id: Optional agent identifier

        Returns:
            embedding_id of the inserted record
        """
        embedding_id = uuid4()
        rls_conn = _current_rls_connection.get()
        if rls_conn:
            await self._insert_semantic_embedding_with_connection(
                rls_conn, embedding_id, vector, payload, agent_id
            )
            return embedding_id

        async with self.acquire() as conn:
            # pgvector expects vector as string format '[x,y,z,...]'
            vector_str = f"[{','.join(str(v) for v in vector)}]"
            await conn.execute(
                """
                INSERT INTO semantic_memory (embedding_id, agent_id, vector, payload, created_at)
                VALUES ($1, $2, $3::vector, $4, $5)
                """,
                embedding_id,
                agent_id,
                vector_str,
                json.dumps(payload),
                datetime.utcnow(),
            await self._insert_semantic_embedding_with_connection(
                conn, embedding_id, vector, payload, agent_id
            )
            logger.debug(f"Inserted semantic embedding {embedding_id}")
            return embedding_id

    async def _insert_semantic_embedding_with_connection(
        self,
        conn: asyncpg.Connection,
        embedding_id: UUID,
        vector: list[float],
        payload: dict[str, Any],
        agent_id: Optional[str],
    ) -> None:
        """Helper to insert semantic embedding using provided connection."""
        vector_str = f"[{','.join(str(v) for v in vector)}]"
        await conn.execute(
            """
            INSERT INTO semantic_memory (embedding_id, agent_id, vector, payload, created_at)
            VALUES ($1, $2, $3::vector, $4, $5)
            """,
            embedding_id,
            agent_id,
            vector_str,
            json.dumps(payload),
            datetime.utcnow(),
        )
        logger.debug(f"Inserted semantic embedding {embedding_id}")

    async def search_semantic_memory(
        self,
        query_embedding: list[float],
        top_k: int = 10,
        agent_id: Optional[str] = None,
    ) -> list[SemanticHit]:
        """
        Search semantic memory using cosine similarity.

        Args:
            query_embedding: Query vector
            top_k: Number of results to return
            agent_id: Optional filter by agent

        Returns:
            List of SemanticHit with embedding_id, score, payload
        """
        async with self.acquire() as conn:
            vector_str = f"[{','.join(str(v) for v in query_embedding)}]"

            if agent_id:
                rows = await conn.fetch(
                    """
                    SELECT
                        embedding_id,
memory/substrate_semantic.py
memory/substrate_semantic.py
+19
-0

@@ -233,50 +233,69 @@ class SemanticService:
        Returns:
            embedding_id as string
        """
        logger.debug(f"Generating embedding for text: {text[:100]}...")

        # Generate embedding
        vector = await self._provider.embed_text(text)

        # Enrich payload with original text
        enriched_payload = {
            **payload,
            "_text": text,
            "_model": getattr(self._provider, "_model", "unknown"),
        }

        # Store in database
        embedding_id = await self._repository.insert_semantic_embedding(
            vector=vector,
            payload=enriched_payload,
            agent_id=agent_id,
        )

        logger.debug(f"Stored embedding {embedding_id}")
        return str(embedding_id)

    async def generate_embedding(
        self,
        text: str,
        payload: dict[str, Any],
        agent_id: Optional[str] = None,
    ) -> tuple[list[float], dict[str, Any], Optional[str]]:
        """
        Generate an embedding and return vector + enriched payload.

        This is useful for transactional write paths where insertion is deferred.
        """
        vector = await self._provider.embed_text(text)
        enriched_payload = {
            **payload,
            "_text": text,
            "_model": getattr(self._provider, "_model", "unknown"),
        }
        return vector, enriched_payload, agent_id

    async def search(
        self,
        query: str,
        top_k: int = 10,
        agent_id: Optional[str] = None,
    ) -> list[dict[str, Any]]:
        """
        Search semantic memory for similar content.

        Args:
            query: Natural language query
            top_k: Number of results
            agent_id: Optional filter by agent

        Returns:
            List of hits with embedding_id, score, payload
        """
        logger.debug(f"Semantic search: {query[:100]}...")

        # Generate query embedding
        query_vector = await self._provider.embed_text(query)

        # Search database
        hits = await self._repository.search_semantic_memory(
            query_embedding=query_vector,
memory/tool_router.py
memory/tool_router.py
+55
-27

"""
L9 Memory - Semantic Tool Router
================================

pgvector-backed semantic search for dynamic tool discovery.

Instead of injecting all 50+ tools into every prompt, agents can search
for the most relevant tools by semantic similarity.

Workflow:
1. Tool descriptions are embedded and stored in pgvector
2. Agent query → semantic search for relevant tools
3. Only top-k matching tools injected into context

Benefits:
- Reduces prompt bloat (50 tools → 5 relevant tools)
- Enables dynamic tool discovery
- Tools can be added/updated without code changes

Version: 1.0.0
"""

from __future__ import annotations

import hashlib
import asyncio
import structlog
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional
from uuid import UUID, uuid4

logger = structlog.get_logger(__name__)


# =============================================================================
# Data Classes
# =============================================================================


@dataclass
class ToolEmbedding:
    """Embedded tool for semantic search."""

    tool_name: str
    description: str
    category: str
    embedding_id: UUID = field(default_factory=uuid4)

    # Metadata
    risk_level: str = "low"
@@ -141,137 +142,146 @@ class ToolRouter:

    # Agent ID used for tool embeddings
    TOOL_AGENT_ID = "tool_router"

    def __init__(
        self,
        embedding_provider: Optional[Any] = None,
        repository: Optional[Any] = None,
        cache_embeddings: bool = True,
    ):
        """
        Initialize tool router.

        Args:
            embedding_provider: EmbeddingProvider for generating embeddings
            repository: SubstrateRepository for pgvector storage
            cache_embeddings: Whether to cache embeddings in memory
        """
        self._provider = embedding_provider
        self._repository = repository
        self._cache_embeddings = cache_embeddings

        # In-memory cache for testing without DB
        self._tool_cache: dict[str, ToolEmbedding] = {}
        self._embedding_cache: dict[str, list[float]] = {}
        self._cache_lock = asyncio.Lock()
        self._cache_version = 0

        # Track if tools have been embedded
        self._tools_embedded = False

        logger.info("ToolRouter initialized", cache_enabled=cache_embeddings)

    async def embed_tool(self, tool: Any) -> Optional[ToolEmbedding]:
        """
        Embed a single tool definition.

        Args:
            tool: ToolDefinition from core.tools.tool_graph

        Returns:
            ToolEmbedding if successful
        """
        # Extract fields from ToolDefinition
        tool_name = getattr(tool, "name", str(tool))
        description = getattr(tool, "description", "")
        category = getattr(tool, "category", "general")
        risk_level = getattr(tool, "risk_level", "low")
        is_destructive = getattr(tool, "is_destructive", False)
        requires_confirmation = getattr(tool, "requires_confirmation", False)
        external_apis = getattr(tool, "external_apis", [])

        # Create embedding record
        embedding = ToolEmbedding(
            tool_name=tool_name,
            description=description,
            category=category,
            risk_level=risk_level,
            is_destructive=is_destructive,
            requires_confirmation=requires_confirmation,
            external_apis=external_apis,
        )

        embedding.content_hash = embedding.compute_hash()

        # Check if already embedded with same content
        if tool_name in self._tool_cache:
            cached = self._tool_cache[tool_name]
            if cached.content_hash == embedding.content_hash:
                logger.debug(f"Tool already embedded: {tool_name}")
                return cached
        async with self._cache_lock:
            cached = self._tool_cache.get(tool_name)
        if cached and cached.content_hash == embedding.content_hash:
            logger.debug(f"Tool already embedded: {tool_name}")
            return cached

        # Generate embedding
        searchable_text = embedding.to_searchable_text()

        vector = None
        if self._provider:
            try:
                vector = await self._provider.embed_text(searchable_text)

                # Store in pgvector if repository available
                if self._repository:
                    await self._store_embedding(embedding, vector)

                # Cache
                if self._cache_embeddings:
                    self._embedding_cache[tool_name] = vector

            except Exception as e:
                logger.error(f"Failed to embed tool {tool_name}: {e}")
                return None

        embedding.embedded_at = datetime.utcnow()
        self._tool_cache[tool_name] = embedding

        async with self._cache_lock:
            cached = self._tool_cache.get(tool_name)
            if cached and cached.content_hash == embedding.content_hash:
                return cached
            if vector is not None and self._cache_embeddings:
                self._embedding_cache[tool_name] = vector
            embedding.embedded_at = datetime.utcnow()
            self._tool_cache[tool_name] = embedding
            self._cache_version += 1

        logger.debug(f"Embedded tool: {tool_name}")
        return embedding

    async def embed_tools(self, tools: list[Any]) -> int:
        """
        Embed multiple tool definitions.

        Args:
            tools: List of ToolDefinition objects

        Returns:
            Number of tools successfully embedded
        """
        count = 0
        for tool in tools:
            result = await self.embed_tool(tool)
            if result:
                count += 1

        self._tools_embedded = True
        async with self._cache_lock:
            self._tools_embedded = True
            self._cache_version += 1
        logger.info(f"Embedded {count}/{len(tools)} tools")
        return count

    async def _store_embedding(
        self,
        tool: ToolEmbedding,
        vector: list[float],
    ) -> None:
        """Store tool embedding in pgvector."""
        if not self._repository:
            return

        try:
            # Use semantic_memory table with tool_router agent_id
            await self._repository.store_semantic_memory(
                embedding_id=tool.embedding_id,
                agent_id=self.TOOL_AGENT_ID,
                vector=vector,
                payload={
                    "tool_name": tool.tool_name,
                    "description": tool.description,
                    "category": tool.category,
                    "risk_level": tool.risk_level,
                    "is_destructive": tool.is_destructive,
                    "external_apis": tool.external_apis,
@@ -320,123 +330,138 @@ class ToolRouter:
                    if hit.get("score", 0) < min_similarity:
                        continue

                    payload = hit.get("payload", {})

                    # Apply category filter
                    if category_filter and payload.get("category") != category_filter:
                        continue

                    matches.append(ToolMatch(
                        tool_name=payload.get("tool_name", "unknown"),
                        description=payload.get("description", ""),
                        category=payload.get("category", "general"),
                        similarity=hit.get("score", 0.0),
                        risk_level=payload.get("risk_level", "low"),
                        is_destructive=payload.get("is_destructive", False),
                        external_apis=payload.get("external_apis", []),
                    ))

                    if len(matches) >= limit:
                        break

            except Exception as e:
                logger.warning(f"pgvector search failed, falling back to cache: {e}")

        tool_cache, _, _, _ = await self._snapshot_cache()

        # Fallback to in-memory cache search
        if not matches and self._tool_cache:
        if not matches and tool_cache:
            matches = await self._search_cache(query, limit, min_similarity, category_filter)

        search_time = (time.time() - start_time) * 1000

        return ToolSearchResult(
            query=query,
            matches=matches,
            search_time_ms=search_time,
            total_tools=len(self._tool_cache),
            total_tools=len(tool_cache),
        )

    async def _search_cache(
        self,
        query: str,
        limit: int,
        min_similarity: float,
        category_filter: Optional[str],
    ) -> list[ToolMatch]:
        """Search in-memory cache (fallback)."""
        tool_cache, embedding_cache, _, _ = await self._snapshot_cache()
        if not self._provider:
            # Without embeddings, do simple text matching
            return self._text_match_cache(query, limit, category_filter)
            return self._text_match_cache(tool_cache, query, limit, category_filter)

        try:
            query_vector = await self._provider.embed_text(query)
        except Exception:
            return self._text_match_cache(query, limit, category_filter)
            return self._text_match_cache(tool_cache, query, limit, category_filter)

        # Compute similarities
        scored: list[tuple[float, ToolEmbedding]] = []

        for tool_name, tool in self._tool_cache.items():
        for tool_name, tool in tool_cache.items():
            if category_filter and tool.category != category_filter:
                continue

            if tool_name in self._embedding_cache:
                tool_vector = self._embedding_cache[tool_name]
            if tool_name in embedding_cache:
                tool_vector = embedding_cache[tool_name]
                similarity = self._cosine_similarity(query_vector, tool_vector)

                if similarity >= min_similarity:
                    scored.append((similarity, tool))

        # Sort by similarity
        scored.sort(key=lambda x: x[0], reverse=True)

        return [
            ToolMatch(
                tool_name=tool.tool_name,
                description=tool.description,
                category=tool.category,
                similarity=score,
                risk_level=tool.risk_level,
                is_destructive=tool.is_destructive,
                external_apis=tool.external_apis,
            )
            for score, tool in scored[:limit]
        ]

    async def _snapshot_cache(
        self,
    ) -> tuple[dict[str, ToolEmbedding], dict[str, list[float]], bool, int]:
        async with self._cache_lock:
            return (
                dict(self._tool_cache),
                dict(self._embedding_cache),
                self._tools_embedded,
                self._cache_version,
            )

    def _text_match_cache(
        self,
        tool_cache: dict[str, ToolEmbedding],
        query: str,
        limit: int,
        category_filter: Optional[str],
    ) -> list[ToolMatch]:
        """Simple text matching fallback."""
        query_lower = query.lower()
        query_words = set(query_lower.split())

        scored: list[tuple[int, ToolEmbedding]] = []

        for tool in self._tool_cache.values():
        for tool in tool_cache.values():
            if category_filter and tool.category != category_filter:
                continue

            # Count word matches
            tool_text = f"{tool.tool_name} {tool.description}".lower()
            score = sum(1 for word in query_words if word in tool_text)

            if score > 0:
                scored.append((score, tool))

        scored.sort(key=lambda x: x[0], reverse=True)

        return [
            ToolMatch(
                tool_name=tool.tool_name,
                description=tool.description,
                category=tool.category,
                similarity=float(score) / len(query_words) if query_words else 0.0,
                risk_level=tool.risk_level,
                is_destructive=tool.is_destructive,
                external_apis=tool.external_apis,
            )
            for score, tool in scored[:limit]
        ]

@@ -484,65 +509,68 @@ class ToolRouter:
                apis = f" (uses: {', '.join(match.external_apis)})" if match.external_apis else ""
                lines.append(f"- **{match.tool_name}**{risk}: {match.description}{apis}")
            else:
                lines.append(f"- **{match.tool_name}**: {match.description}")

        return "\n".join(lines)

    async def get_tools_for_task(
        self,
        task_description: str,
        limit: int = 5,
    ) -> str:
        """
        Convenience method: search and format in one call.

        Args:
            task_description: What the agent is trying to do
            limit: Max tools to return

        Returns:
            Formatted tool context string
        """
        result = await self.find_relevant_tools(task_description, limit=limit)
        return self.get_tool_context(result)

    def list_embedded_tools(self) -> list[str]:
    async def list_embedded_tools(self) -> list[str]:
        """List all embedded tool names."""
        return list(self._tool_cache.keys())
        tool_cache, _, _, _ = await self._snapshot_cache()
        return list(tool_cache.keys())

    def get_stats(self) -> dict[str, Any]:
    async def get_stats(self) -> dict[str, Any]:
        """Get router statistics."""
        tool_cache, embedding_cache, tools_embedded, cache_version = await self._snapshot_cache()
        categories = {}
        for tool in self._tool_cache.values():
        for tool in tool_cache.values():
            categories[tool.category] = categories.get(tool.category, 0) + 1

        return {
            "total_tools": len(self._tool_cache),
            "tools_with_embeddings": len(self._embedding_cache),
            "total_tools": len(tool_cache),
            "tools_with_embeddings": len(embedding_cache),
            "categories": categories,
            "is_ready": self._tools_embedded,
            "is_ready": tools_embedded,
            "cache_version": cache_version,
        }


# =============================================================================
# Singleton Factory
# =============================================================================


_router: Optional[ToolRouter] = None


async def get_tool_router(
    embedding_provider: Optional[Any] = None,
    repository: Optional[Any] = None,
) -> ToolRouter:
    """Get or create singleton tool router."""
    global _router

    if _router is None:
        _router = ToolRouter(
            embedding_provider=embedding_provider,
            repository=repository,
        )

    return _router
