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
    
    # Check if IP is blocked
    check_auth_block(ip)
    
    # Check rate limit
    check_rate_limit(ip)
    
    # Record this request
    request_log[ip].append((time.time(), True))
    
    if not authorization or not authorization.startswith("Bearer "):
        record_failed_auth(ip)
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


@app.get("/")
async def root():
    return {
        "status": "L9 MCP Memory Server",
        "version": "1.0.0",
        "mcp_version": "2025-03-26",
    }


@app.get("/health")
async def health_check():
    return await health.health_check()


@app.get("/mcp/tools")
async def list_tools(request: Request, caller: CallerIdentity = Depends(verify_api_key)):
    return {"tools": get_mcp_tools(), "caller": caller.caller_id}


@app.post("/mcp/call")
async def call_tool(request: Request, caller: CallerIdentity = Depends(verify_api_key)):
    """Execute MCP tool with caller-enforced governance.
    
    Caller identity (L or C) determines:
    - user_id: Shared L_CTO_USER_ID (L and C collaborate in same space)
    - metadata.creator: "L-CTO" or "Cursor-IDE" (enforced server-side)
    - metadata.source: "l9-kernel" or "cursor-ide" (enforced server-side)
    - write/delete scope: C can only modify own memories (creator="Cursor-IDE")
    """
    try:
        payload = await request.json()
        # MCP protocol uses "name" for tool name, but support "tool_name" for backwards compat
        tool_name = payload.get("name") or payload.get("tool_name")
        tool_args = payload.get("arguments", {})
        # Use shared user_id from caller identity (not payload)
        # This enforces L + C operate in same semantic space
        user_id = caller.user_id
        tool_call = MCPToolCall(name=tool_name, arguments=tool_args)
        # Get substrate service from app state (if initialized)
        substrate_service = getattr(request.app.state, "substrate_service", None)
        result = await handle_tool_call(tool_call, user_id, caller, substrate_service)
        return {"status": "success", "result": result, "caller": caller.caller_id}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("Tool call error")
        raise HTTPException(status_code=500, detail=str(e))


# Memory routes (direct API)
app.include_router(memory.router, prefix="/memory", tags=["memory"])

# Backward compatibility: /api/v1/memory/* routes for cursor_memory_client.py
# The client calls /api/v1/memory/* but MCP server exposes /memory/*
# Add /api/v1 prefix for backward compatibility
app.include_router(memory.router, prefix="/api/v1/memory", tags=["memory"])


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle HTTP exceptions with proper status codes."""
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})


@app.exception_handler(ValidationError)
async def validation_exception_handler(request: Request, exc: ValidationError):
    """Handle Pydantic validation errors."""
    logger.warning("Validation error", errors=exc.errors())
    return JSONResponse(
        status_code=422,
        content={"detail": "Validation error", "errors": exc.errors()}
    )


@app.exception_handler(asyncpg.PostgresError)
async def postgres_exception_handler(request: Request, exc: asyncpg.PostgresError):
    """Handle PostgreSQL database errors."""
    logger.error("Database error", error=str(exc), error_code=getattr(exc, 'code', None))
    return JSONResponse(
        status_code=500,
        content={"detail": "Database error", "error_code": getattr(exc, 'code', None)}
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Catch-all for unexpected exceptions."""
    logger.exception("Unhandled exception", exc_info=exc)
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        app,
        host=settings.MCP_HOST,
        port=settings.MCP_PORT,
        log_level=settings.LOG_LEVEL.lower(),
    )
