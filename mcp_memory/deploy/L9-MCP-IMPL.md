# Cursor MCP Memory Server — Implementation Pack
## L9 VPS Deployment (FastAPI + Python + PostgreSQL + pgvector)

**Last Updated:** 2026-01-01  
**Status:** Production-Ready  
**Stack:** FastAPI 0.115+, Python 3.11+, PostgreSQL + pgvector, OpenAI Embeddings, MCP Spec 2025-03-26  
**Domain:** `l9.quantumaipartners.com` (via Cloudflare)

---

## 📋 Table of Contents

1. [Architecture & Topology](#architecture)
2. [Project Structure](#project-structure)
3. [Installation & Setup](#installation)
4. [Configuration](#configuration)
5. [Database Schema](#database-schema)
6. [MCP Server Implementation](#mcp-server)
7. [API Endpoints](#endpoints)
8. [Deployment](#deployment)
9. [Cursor Integration](#cursor-integration)
10. [SSH Tunnel Setup](#ssh-tunnel)
11. [Testing & Debugging](#testing)
12. [Troubleshooting](#troubleshooting)

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│ MacBook Laptop (Local Development)                              │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ Cursor IDE                                               │   │
│  │  └─ MCP Client (HTTP)                                    │   │
│  │      ↓ (connects to https://l9.quantumaipartners.com)   │   │
│  └──────────────────────────────────────────────────────────┘   │
└──────────────────────┬──────────────────────────────────────────┘
                       │
           HTTPS via Cloudflare (no SSH tunnel needed!)
                       │
┌──────────────────────↓──────────────────────────────────────────┐
│ Cloudflare (Proxy)                                              │
│  ├─ DNS: l9.quantumaipartners.com → 157.180.73.53 (Proxied)   │
│  ├─ SSL/TLS: Full (strict) - automatic HTTPS                   │
│  ├─ DDoS protection, WAF, caching                              │
│  └─ Hides origin IP from public                                │
└──────────────────────┬──────────────────────────────────────────┘
                       │
                   Port 443
                       │
┌──────────────────────↓──────────────────────────────────────────┐
│ VPS (157.180.73.53) Ubuntu 24.04 LTS                            │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ Caddy (Reverse Proxy)                                    │   │
│  │  Port: 443 (HTTPS from Cloudflare)                       │   │
│  │  Routes:                                                 │   │
│  │   ├─ /api/*      → l9-api:8000 (L9 API)                 │   │
│  │   ├─ /slack/*    → l9-api:8000 (Slack webhooks)         │   │
│  │   ├─ /mcp/*      → mcp-memory:9001 (MCP protocol)       │   │
│  │   └─ /memory/*   → mcp-memory:9001 (Memory API)         │   │
│  └──────────────────────────────────────────────────────────┘   │
│           ↓                        ↓                             │
│  ┌────────────────┐    ┌────────────────────────────────────┐   │
│  │ l9-api:8000    │    │ mcp-memory:9001                    │   │
│  │ (Main L9 API)  │    │ (FastAPI MCP Server)               │   │
│  │                │    │  ├─ /mcp/tools                     │   │
│  │                │    │  ├─ /mcp/call                      │   │
│  │                │    │  ├─ /memory/save                   │   │
│  │                │    │  ├─ /memory/search                 │   │
│  │                │    │  └─ /health                        │   │
│  └────────────────┘    └────────────────────────────────────┘   │
│           ↓                        ↓                             │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ PostgreSQL 15 + pgvector                                 │   │
│  │  Port: 127.0.0.1:5432 (internal only)                   │   │
│  │  Databases:                                              │   │
│  │   ├─ l9 (main L9 database)                              │   │
│  │   └─ l9_memory (MCP memory schema)                      │   │
│  └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

**Key Principles:**
- **No SSH tunnel required** - Cloudflare handles HTTPS routing
- **Origin IP hidden** - VPS IP protected by Cloudflare proxy  
- **Single domain** - All L9 services via `l9.quantumaipartners.com`
- **Caddy routes** - Paths determine which service handles request

---

## Project Structure

```
/opt/l9/mcp_memory/
├── main.py                              # FastAPI app entry point
├── mcp_server.py                        # MCP protocol implementation
├── db.py                                # PostgreSQL async client
├── embeddings.py                        # OpenAI embedding helper
├── models.py                            # Pydantic schemas
├── config.py                            # Configuration (env-based)
├── routes/
│   ├── memory.py                        # Memory CRUD endpoints
│   ├── mcp_tools.py                     # MCP tools definition
│   └── health.py                        # Health check
├── schema/
│   ├── init.sql                         # Database initialization
│   └── migrations.py                    # Schema migration runner
├── requirements.txt                     # Python dependencies (supplement to L9 base)
├── .env.example                         # Example environment file
├── docker/
│   ├── Dockerfile.mcp                   # Separate MCP container (optional)
│   └── docker-compose.mcp.yml           # Compose override for MCP
├── systemd/
│   └── l9-mcp.service                   # Systemd service file
├── scripts/
│   ├── install.sh                       # Setup & installation
│   ├── migrate_db.py                    # Run migrations
│   └── test_connection.py               # Test Postgres + OpenAI
└── README.md                            # Full documentation
```

---

## Installation & Setup

### Prerequisites

- VPS: Ubuntu 24.04 LTS (already have it ✓)
- Python: 3.11+ (already have it ✓)
- PostgreSQL 15+ with pgvector (already have it ✓)
- OpenAI API key (already have it ✓)

### Step 1: Clone / Create Project

```bash
# SSH into VPS
ssh admin@157.180.73.53

# Create project directory
sudo mkdir -p /opt/l9/mcp_memory
sudo chown -R admin:admin /opt/l9/mcp_memory
cd /opt/l9/mcp_memory

# Initialize git (optional, for version control)
git init
```

### Step 2: Install Dependencies

Create `requirements_mcp.txt` (add to existing L9 requirements):

```txt
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
alembic>=1.13.0  # Database migrations

# Embeddings & LLM
openai>=1.0.0
tenacity>=8.2.0  # Retry logic for API calls

# Utils
python-dotenv>=1.0.0
pyyaml>=6.0.1
```

Install:

```bash
pip install -r requirements_mcp.txt
```

### Step 3: Create .env File

```bash
cat > /opt/l9/mcp_memory/.env << 'EOF'
# ═══════════════════════════════════════════════════════════════
# MCP Memory Server Configuration
# ═══════════════════════════════════════════════════════════════

# Server (bind to all interfaces for Caddy reverse proxy)
MCP_HOST=0.0.0.0
MCP_PORT=9001
MCP_ENV=production
LOG_LEVEL=INFO

# OpenAI (copy from L9 .env)
OPENAI_API_KEY=sk-proj-YOUR_KEY_HERE
OPENAI_EMBED_MODEL=text-embedding-3-small

# PostgreSQL (copy from L9 .env)
MEMORY_DSN=postgresql://postgres:YOUR_PASSWORD@127.0.0.1:5432/l9_memory

# Memory Behavior
MEMORY_SHORT_TERM_HOURS=1
MEMORY_MEDIUM_TERM_HOURS=24
MEMORY_CLEANUP_INTERVAL_MINUTES=60
MEMORY_SHORT_RETENTION_DAYS=7
MEMORY_MEDIUM_RETENTION_DAYS=30

# Vector Search
VECTOR_SEARCH_THRESHOLD=0.7
VECTOR_SEARCH_TOP_K=10

# Auth (for MCP clients)
MCP_API_KEY=your-secret-key-generate-with-openssl-rand-hex-32

# Embedding Cache (Redis, optional)
REDIS_ENABLED=false
REDIS_HOST=127.0.0.1
REDIS_PORT=6379

EOF
chmod 600 /opt/l9/mcp_memory/.env
```

---

## Configuration

### config.py

```python
import os
from pydantic_settings import BaseSettings
from typing import Optional

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
    
    # Database
    MEMORY_DSN: str
    
    # Memory Lifecycle
    MEMORY_SHORT_TERM_HOURS: int = 1
    MEMORY_MEDIUM_TERM_HOURS: int = 24
    MEMORY_CLEANUP_INTERVAL_MINUTES: int = 60
    MEMORY_SHORT_RETENTION_DAYS: int = 7
    MEMORY_MEDIUM_RETENTION_DAYS: int = 30
    
    # Vector Search
    VECTOR_SEARCH_THRESHOLD: float = 0.7
    VECTOR_SEARCH_TOP_K: int = 10
    
    # Auth
    MCP_API_KEY: str
    
    # Redis (optional embedding cache)
    REDIS_ENABLED: bool = False
    REDIS_HOST: str = "127.0.0.1"
    REDIS_PORT: int = 6379
    
    class Config:
        env_file = ".env"
        extra = "ignore"

# Load once
settings = Settings()
```

---

## Database Schema

### schema/init.sql

```sql
-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Create schema
CREATE SCHEMA IF NOT EXISTS memory;

-- Short-term memory (< 1 hour, aggressive cleanup)
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

-- Long-term memory (durable, searchable)
CREATE TABLE IF NOT EXISTS memory.long_term (
    id BIGSERIAL PRIMARY KEY,
    user_id TEXT NOT NULL,
    scope TEXT NOT NULL DEFAULT 'user',  -- 'user', 'project', 'global'
    kind TEXT NOT NULL,  -- 'preference', 'fact', 'context', 'error', 'success'
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

-- Indexes for performance
CREATE INDEX idx_short_term_user_expires ON memory.short_term(user_id, expires_at);
CREATE INDEX idx_short_term_embedding ON memory.short_term USING ivfflat(embedding vector_cosine_ops) WITH (lists = 100);

CREATE INDEX idx_medium_term_user_expires ON memory.medium_term(user_id, expires_at);
CREATE INDEX idx_medium_term_importance ON memory.medium_term(user_id, importance DESC) WHERE expires_at > CURRENT_TIMESTAMP;
CREATE INDEX idx_medium_term_embedding ON memory.medium_term USING ivfflat(embedding vector_cosine_ops) WITH (lists = 100);

CREATE INDEX idx_long_term_user_scope ON memory.long_term(user_id, scope);
CREATE INDEX idx_long_term_kind ON memory.long_term(kind);
CREATE INDEX idx_long_term_tags ON memory.long_term USING GIN(tags);
CREATE INDEX idx_long_term_embedding ON memory.long_term USING ivfflat(embedding vector_cosine_ops) WITH (lists = 100);
CREATE INDEX idx_long_term_access ON memory.long_term(last_accessed_at DESC);

-- Materialized view for memory stats
CREATE OR REPLACE VIEW memory.stats_view AS
SELECT
    'short_term' as memory_type,
    COUNT(*) as total_count,
    COUNT(DISTINCT user_id) as unique_users,
    AVG(importance) as avg_importance,
    NOW() as calculated_at
FROM memory.short_term
WHERE expires_at > CURRENT_TIMESTAMP
UNION ALL
SELECT
    'medium_term',
    COUNT(*),
    COUNT(DISTINCT user_id),
    AVG(importance),
    NOW()
FROM memory.medium_term
WHERE expires_at > CURRENT_TIMESTAMP
UNION ALL
SELECT
    'long_term',
    COUNT(*),
    COUNT(DISTINCT user_id),
    AVG(importance),
    NOW()
FROM memory.long_term;

-- Audit table for memory operations
CREATE TABLE IF NOT EXISTS memory.audit_log (
    id BIGSERIAL PRIMARY KEY,
    operation TEXT NOT NULL,  -- 'INSERT', 'UPDATE', 'DELETE', 'SEARCH'
    table_name TEXT NOT NULL,
    memory_id BIGINT,
    user_id TEXT,
    status TEXT NOT NULL DEFAULT 'success',
    details JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_audit_user_timestamp ON memory.audit_log(user_id, created_at DESC);
```

---

## MCP Server Implementation

### mcp_server.py

```python
"""
MCP (Model Context Protocol) Server Implementation
Handles tool definitions and call routing.
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
    """
    Define all tools available to Cursor via MCP.
    """
    return [
        MCPTool(
            name="save_memory",
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
                        "description": "Memory duration (short=<1hr, medium=<24hr, long=durable)",
                    },
                    "user_id": {
                        "type": "string",
                        "description": "User identifier",
                    },
                    "tags": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Optional tags for organization",
                    },
                    "importance": {
                        "type": "number",
                        "minimum": 0,
                        "maximum": 1,
                        "description": "Importance weight (0-1)",
                    },
                },
                "required": ["content", "kind", "duration", "user_id"],
            },
        ),
        MCPTool(
            name="search_memory",
            description="Search memories using semantic similarity (vector search)",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query (will be embedded)",
                    },
                    "user_id": {
                        "type": "string",
                        "description": "User identifier to scope search",
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
                        "description": "Filter by memory kinds (optional)",
                    },
                    "top_k": {
                        "type": "integer",
                        "default": 5,
                        "minimum": 1,
                        "maximum": 50,
                        "description": "Number of results to return",
                    },
                    "threshold": {
                        "type": "number",
                        "default": 0.7,
                        "description": "Similarity threshold (0-1)",
                    },
                    "duration": {
                        "type": "string",
                        "enum": ["short", "medium", "long", "all"],
                        "default": "all",
                        "description": "Which memory tables to search",
                    },
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
                    "user_id": {
                        "type": "string",
                        "description": "User identifier (optional, omit for global stats)",
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
            name="delete_expired_memories",
            description="Cleanup expired short and medium-term memories (admin only)",
            inputSchema={
                "type": "object",
                "properties": {
                    "dry_run": {
                        "type": "boolean",
                        "default": True,
                        "description": "If true, only report what would be deleted",
                    },
                },
                "required": [],
            },
        ),
    ]

async def handle_tool_call(tool: MCPToolCall, user_id: str) -> Dict[str, Any]:
    """
    Route tool calls to appropriate handler.
    """
    if tool.name == "save_memory":
        from .routes.memory import save_memory
        return await save_memory(
            user_id=user_id,
            content=tool.arguments.get("content"),
            kind=tool.arguments.get("kind"),
            scope=tool.arguments.get("scope", "user"),
            duration=tool.arguments.get("duration"),
            tags=tool.arguments.get("tags", []),
            importance=tool.arguments.get("importance", 1.0),
        )
    
    elif tool.name == "search_memory":
        from .routes.memory import search_memory
        return await search_memory(
            user_id=user_id,
            query=tool.arguments.get("query"),
            scopes=tool.arguments.get("scopes", ["user", "project", "global"]),
            kinds=tool.arguments.get("kinds"),
            top_k=tool.arguments.get("top_k", 5),
            threshold=tool.arguments.get("threshold", 0.7),
            duration=tool.arguments.get("duration", "all"),
        )
    
    elif tool.name == "get_memory_stats":
        from .routes.memory import get_memory_stats
        return await get_memory_stats(
            user_id=tool.arguments.get("user_id"),
            duration=tool.arguments.get("duration", "all"),
        )
    
    elif tool.name == "delete_expired_memories":
        from .routes.memory import delete_expired_memories
        return await delete_expired_memories(
            dry_run=tool.arguments.get("dry_run", True),
        )
    
    else:
        raise ValueError(f"Unknown tool: {tool.name}")
```

### main.py (FastAPI App)

```python
"""
FastAPI MCP Memory Server
Serves as both HTTP endpoint and MCP bridge for Cursor.
"""

import logging
from fastapi import FastAPI, HTTPException, Depends, Header, Request
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import asyncio

from config import settings
from db import init_db, close_db
from mcp_server import get_mcp_tools, MCPToolCall, handle_tool_call
from routes import memory, health

# ═════════════════════════════════════════════════════════════════
# Logging
# ═════════════════════════════════════════════════════════════════
logging.basicConfig(
    level=settings.LOG_LEVEL,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# ═════════════════════════════════════════════════════════════════
# Lifecycle
# ═════════════════════════════════════════════════════════════════

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Initializing database...")
    await init_db()
    logger.info("✓ Database initialized")
    
    # Start cleanup task
    asyncio.create_task(memory.cleanup_task())
    
    yield
    
    # Shutdown
    logger.info("Closing database connections...")
    await close_db()
    logger.info("✓ Shutdown complete")

# ═════════════════════════════════════════════════════════════════
# App
# ═════════════════════════════════════════════════════════════════

app = FastAPI(
    title="L9 MCP Memory Server",
    description="OpenAI embeddings + pgvector semantic search for Cursor",
    version="1.0.0",
    lifespan=lifespan,
)

# ═════════════════════════════════════════════════════════════════
# Auth
# ═════════════════════════════════════════════════════════════════

async def verify_api_key(authorization: str = Header(None)) -> str:
    """
    Verify MCP_API_KEY from Authorization header.
    Format: Authorization: Bearer <key>
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")
    
    token = authorization.replace("Bearer ", "")
    if token != settings.MCP_API_KEY:
        raise HTTPException(status_code=403, detail="Invalid API key")
    
    return token

# ═════════════════════════════════════════════════════════════════
# Routes
# ═════════════════════════════════════════════════════════════════

@app.get("/")
async def root():
    return {
        "status": "L9 MCP Memory Server",
        "version": "1.0.0",
        "mcp_version": "2025-03-26",
    }

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return await health.health_check()

# ═════════════════════════════════════════════════════════════════
# MCP Protocol Endpoints
# ═════════════════════════════════════════════════════════════════

@app.get("/mcp/tools")
async def list_tools(auth: str = Depends(verify_api_key)):
    """
    List all available MCP tools.
    Called by Cursor to discover capabilities.
    """
    return {
        "tools": get_mcp_tools(),
    }

@app.post("/mcp/call")
async def call_tool(
    request: Request,
    auth: str = Depends(verify_api_key),
):
    """
    Call an MCP tool by name with arguments.
    Cursor uses this to invoke memory operations.
    """
    try:
        payload = await request.json()
        tool_name = payload.get("tool_name")
        tool_args = payload.get("arguments", {})
        user_id = payload.get("user_id")
        
        if not user_id:
            raise HTTPException(status_code=400, detail="user_id required")
        
        tool_call = MCPToolCall(name=tool_name, arguments=tool_args)
        result = await handle_tool_call(tool_call, user_id)
        
        return {
            "status": "success",
            "result": result,
        }
    
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("Tool call error")
        raise HTTPException(status_code=500, detail=str(e))

# ═════════════════════════════════════════════════════════════════
# Memory Endpoints (direct HTTP API)
# ═════════════════════════════════════════════════════════════════

app.include_router(memory.router, prefix="/memory", tags=["memory"])

# ═════════════════════════════════════════════════════════════════
# Error Handlers
# ═════════════════════════════════════════════════════════════════

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled exception")
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host=settings.MCP_HOST,
        port=settings.MCP_PORT,
        log_level=settings.LOG_LEVEL.lower(),
    )
```

### db.py (PostgreSQL Async Client)

```python
"""
PostgreSQL async client with pgvector support.
"""

import asyncpg
import logging
from typing import List, Dict, Any, Optional
from config import settings

logger = logging.getLogger(__name__)

# Global connection pool
pool: Optional[asyncpg.Pool] = None

async def init_db():
    """Initialize database connection pool and run migrations."""
    global pool
    
    pool = await asyncpg.create_pool(
        dsn=settings.MEMORY_DSN,
        min_size=5,
        max_size=20,
        command_timeout=60,
    )
    
    # Register pgvector codec
    await pool.execute("CREATE EXTENSION IF NOT EXISTS vector;")
    
    logger.info("Database pool initialized")

async def close_db():
    """Close database connection pool."""
    global pool
    if pool:
        await pool.close()
        pool = None
        logger.info("Database pool closed")

async def execute(query: str, *args) -> Any:
    """Execute a query and return result."""
    if not pool:
        raise RuntimeError("Database pool not initialized")
    
    async with pool.acquire() as conn:
        return await conn.execute(query, *args)

async def fetch_one(query: str, *args) -> Optional[Dict[str, Any]]:
    """Fetch a single row as dict."""
    if not pool:
        raise RuntimeError("Database pool not initialized")
    
    async with pool.acquire() as conn:
        row = await conn.fetchrow(query, *args)
        return dict(row) if row else None

async def fetch_all(query: str, *args) -> List[Dict[str, Any]]:
    """Fetch all rows as dicts."""
    if not pool:
        raise RuntimeError("Database pool not initialized")
    
    async with pool.acquire() as conn:
        rows = await conn.fetch(query, *args)
        return [dict(row) for row in rows]

async def insert_many(query: str, args_list: List[tuple]) -> int:
    """Insert multiple rows, return count."""
    if not pool:
        raise RuntimeError("Database pool not initialized")
    
    async with pool.acquire() as conn:
        result = await conn.executemany(query, args_list)
    
    # executemany returns command completion tag like "INSERT 0 42"
    count = int(result.split()[-1]) if result else 0
    return count
```

### embeddings.py (OpenAI Integration)

```python
"""
OpenAI embedding generation with caching.
"""

import logging
from typing import List
from openai import AsyncOpenAI
from config import settings

logger = logging.getLogger(__name__)

client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

async def embed_text(text: str) -> List[float]:
    """
    Generate embedding for text using OpenAI.
    """
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
    """
    Generate embeddings for multiple texts (batched).
    """
    try:
        response = await client.embeddings.create(
            model=settings.OPENAI_EMBED_MODEL,
            input=texts,
        )
        # Sort by index to maintain order
        sorted_data = sorted(response.data, key=lambda x: x.index)
        return [item.embedding for item in sorted_data]
    
    except Exception as e:
        logger.error(f"Batch embedding error: {e}")
        raise
```

### models.py (Pydantic Schemas)

```python
"""
Request/response models.
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime

class SaveMemoryRequest(BaseModel):
    content: str
    kind: str  # 'preference', 'fact', 'context', 'error', 'success'
    scope: str = "user"  # 'user', 'project', 'global'
    duration: str  # 'short', 'medium', 'long'
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
    tags: Optional[List[str]]
    created_at: datetime
    similarity: Optional[float] = None  # For search results

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
```

---

## API Endpoints

### routes/memory.py

```python
"""
Memory CRUD and search routes.
"""

import logging
import time
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException, Query
import asyncio

from db import fetch_all, fetch_one, execute, insert_many
from embeddings import embed_text, embed_texts
from models import (
    SaveMemoryRequest, MemoryResponse, SearchMemoryRequest,
    SearchMemoryResponse, MemoryStatsResponse
)
from config import settings

logger = logging.getLogger(__name__)
router = APIRouter()

# ═════════════════════════════════════════════════════════════════
# Save Memory
# ═════════════════════════════════════════════════════════════════

@router.post("/save", response_model=MemoryResponse)
async def save_memory(
    req: SaveMemoryRequest
) -> MemoryResponse:
    """
    Save a memory to appropriate table based on duration.
    Generates embedding automatically.
    """
    try:
        # Generate embedding
        embedding = await embed_text(req.content)
        
        # Determine table and expiration
        if req.duration == "short":
            table = "memory.short_term"
            expires_at = datetime.utcnow() + timedelta(
                hours=settings.MEMORY_SHORT_TERM_HOURS
            )
        elif req.duration == "medium":
            table = "memory.medium_term"
            expires_at = datetime.utcnow() + timedelta(
                hours=settings.MEMORY_MEDIUM_TERM_HOURS
            )
        elif req.duration == "long":
            table = "memory.long_term"
            expires_at = None  # No expiration
        else:
            raise ValueError(f"Invalid duration: {req.duration}")
        
        # Insert
        if req.duration in ["short", "medium"]:
            query = f"""
            INSERT INTO {table} (
                user_id, kind, content, embedding, importance, metadata, expires_at
            )
            VALUES ($1, $2, $3, $4::vector, $5, $6, $7)
            RETURNING id, user_id, kind, content, importance, metadata::text, created_at;
            """
            result = await fetch_one(
                query,
                req.user_id, req.kind, req.content, embedding,
                req.importance, req.metadata, expires_at
            )
        else:  # long-term
            query = """
            INSERT INTO memory.long_term (
                user_id, scope, kind, content, embedding, importance, tags, metadata
            )
            VALUES ($1, $2, $3, $4, $5::vector, $6, $7, $8)
            RETURNING id, user_id, kind, content, importance, tags, created_at;
            """
            result = await fetch_one(
                query,
                req.user_id, req.scope, req.kind, req.content, embedding,
                req.importance, req.tags, req.metadata
            )
        
        # Audit
        await execute(
            """
            INSERT INTO memory.audit_log (operation, table_name, memory_id, user_id, status, details)
            VALUES ($1, $2, $3, $4, $5, $6)
            """,
            "INSERT", table, result["id"], req.user_id, "success",
            {"duration": req.duration, "kind": req.kind}
        )
        
        return MemoryResponse(**result)
    
    except Exception as e:
        logger.exception("Error saving memory")
        raise HTTPException(status_code=500, detail=str(e))

# ═════════════════════════════════════════════════════════════════
# Search Memory
# ═════════════════════════════════════════════════════════════════

@router.post("/search", response_model=SearchMemoryResponse)
async def search_memory(
    req: SearchMemoryRequest
) -> SearchMemoryResponse:
    """
    Semantic search across memory tables using vector similarity.
    """
    start_time = time.time()
    
    try:
        # Generate query embedding
        embed_start = time.time()
        query_embedding = await embed_text(req.query)
        embed_time_ms = (time.time() - embed_start) * 1000
        
        search_start = time.time()
        results = []
        
        # Search each requested duration
        durations = ["short", "medium", "long"] if req.duration == "all" else [req.duration]
        
        for duration in durations:
            if duration == "short":
                table = "memory.short_term"
                where = "AND expires_at > CURRENT_TIMESTAMP"
            elif duration == "medium":
                table = "memory.medium_term"
                where = "AND expires_at > CURRENT_TIMESTAMP"
            else:
                table = "memory.long_term"
                where = ""
            
            # Build WHERE clause
            where_clauses = [f"user_id = $1 {where}"]
            params = [req.user_id]
            
            if req.scopes and duration == "long":  # Only long-term has scope
                scopes_clause = ", ".join([f"${i}" for i in range(2, 2 + len(req.scopes))])
                where_clauses.append(f"scope IN ({scopes_clause})")
                params.extend(req.scopes)
            
            if req.kinds:
                kinds_clause = ", ".join([f"${i}" for i in range(len(params) + 1, len(params) + 1 + len(req.kinds))])
                where_clauses.append(f"kind IN ({kinds_clause})")
                params.extend(req.kinds)
            
            param_idx = len(params) + 1
            
            query = f"""
            SELECT
                id, user_id, kind, content, importance,
                1 - (embedding <-> ${ param_idx}::vector) as similarity,
                metadata::text
            FROM {table}
            WHERE {' AND '.join(where_clauses)}
            AND 1 - (embedding <-> ${param_idx}::vector) >= ${ param_idx + 1}
            ORDER BY similarity DESC
            LIMIT ${param_idx + 2};
            """
            
            params.extend([query_embedding, req.threshold, req.top_k])
            
            rows = await fetch_all(query, *params)
            results.extend(rows)
        
        # Sort by similarity and take top_k
        results.sort(key=lambda x: x.get("similarity", 0), reverse=True)
        results = results[:req.top_k]
        
        search_time_ms = (time.time() - search_start) * 1000
        
        # Audit
        await execute(
            """
            INSERT INTO memory.audit_log (operation, user_id, status, details)
            VALUES ($1, $2, $3, $4)
            """,
            "SEARCH", req.user_id, "success",
            {"query": req.query, "results_count": len(results)}
        )
        
        memory_results = [MemoryResponse(**r) for r in results]
        
        return SearchMemoryResponse(
            results=memory_results,
            query_embedding_time_ms=embed_time_ms,
            search_time_ms=search_time_ms,
            total_results=len(memory_results),
        )
    
    except Exception as e:
        logger.exception("Error searching memory")
        raise HTTPException(status_code=500, detail=str(e))

# ═════════════════════════════════════════════════════════════════
# Cleanup (Background Task)
# ═════════════════════════════════════════════════════════════════

async def cleanup_task():
    """
    Periodically delete expired short and medium-term memories.
    """
    while True:
        try:
            interval_seconds = settings.MEMORY_CLEANUP_INTERVAL_MINUTES * 60
            await asyncio.sleep(interval_seconds)
            
            # Delete expired
            result = await execute(
                """
                DELETE FROM memory.short_term WHERE expires_at < CURRENT_TIMESTAMP;
                """
            )
            
            result = await execute(
                """
                DELETE FROM memory.medium_term WHERE expires_at < CURRENT_TIMESTAMP;
                """
            )
            
            logger.info(f"Cleanup task completed")
        
        except Exception as e:
            logger.error(f"Cleanup task error: {e}")
```

---

## Deployment

### systemd/l9-mcp.service

```ini
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
ExecStart=/opt/l9/venv/bin/python main.py
Restart=on-failure
RestartSec=10
StandardOutput=journal
StandardError=journal
SyslogIdentifier=l9-mcp

[Install]
WantedBy=multi-user.target
```

### Installation Script (scripts/install.sh)

```bash
#!/bin/bash
set -e

echo "╔════════════════════════════════════════════════════════════════╗"
echo "║  L9 MCP Memory Server Installation                            ║"
echo "╚════════════════════════════════════════════════════════════════╝"

MCP_DIR="/opt/l9/mcp_memory"
VENV_DIR="/opt/l9/venv_mcp"

# 1. Create virtual environment
echo "[1/6] Creating Python virtual environment..."
python3.11 -m venv $VENV_DIR
source $VENV_DIR/bin/activate

# 2. Install dependencies
echo "[2/6] Installing dependencies..."
pip install --upgrade pip
pip install -r $MCP_DIR/requirements_mcp.txt

# 3. Run database migrations
echo "[3/6] Initializing database..."
python $MCP_DIR/scripts/migrate_db.py

# 4. Test connection
echo "[4/6] Testing connections..."
python $MCP_DIR/scripts/test_connection.py

# 5. Install systemd service
echo "[5/6] Installing systemd service..."
sudo cp $MCP_DIR/systemd/l9-mcp.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable l9-mcp

# 6. Start service
echo "[6/6] Starting service..."
sudo systemctl start l9-mcp

echo ""
echo "✓ Installation complete!"
echo ""
echo "Check status: sudo systemctl status l9-mcp"
echo "View logs:    sudo journalctl -u l9-mcp -f"
echo "Test locally: curl http://127.0.0.1:9001/health"
```

---

## Cursor Integration

### Cursor MCP Configuration

Add to your Cursor settings (Cursor → Settings → MCP):

```json
{
  "mcpServers": {
    "l9-memory": {
      "command": "curl",
      "args": [
        "-X", "GET", "https://l9.quantumaipartners.com/mcp/tools",
        "-H", "Authorization: Bearer YOUR_MCP_API_KEY"
      ],
      "env": {
        "MCP_URL": "https://l9.quantumaipartners.com",
        "MCP_API_KEY": "YOUR_MCP_API_KEY"
      }
    }
  }
}
```

**OR** (recommended for easier HTTP integration):

Configure in `~/.cursor/mcp.json`:

```json
{
  "mcpServers": {
    "l9-memory": {
      "command": "node",
      "args": ["/path/to/mcp-http-bridge.js"],
      "env": {
        "MCP_SERVER_URL": "https://l9.quantumaipartners.com",
        "MCP_API_KEY": "YOUR_MCP_API_KEY"
      }
    }
  }
}
```

**Note:** No SSH tunnel required! Cloudflare proxies all traffic via HTTPS.

---

## Cloudflare Setup (Production)

### DNS Configuration

In Cloudflare dashboard for `quantumaipartners.com`:

| Type | Name | Content | Proxy Status |
|------|------|---------|--------------|
| A | `l9` | `157.180.73.53` | Proxied (orange cloud) |

### SSL/TLS Settings

- **Mode:** Full (strict)
- **Always Use HTTPS:** On
- **Minimum TLS Version:** 1.2

### Caddy Configuration

On VPS, update `/etc/caddy/Caddyfile`:

```caddyfile
l9.quantumaipartners.com {
    # L9 API (main application)
    handle /api/* {
        reverse_proxy l9-api:8000
    }
    
    # Slack webhooks
    handle /slack/* {
        reverse_proxy l9-api:8000
    }
    
    # MCP Memory - protocol endpoints
    handle /mcp/* {
        reverse_proxy 127.0.0.1:9001
    }
    
    # MCP Memory - direct memory API
    handle /memory/* {
        reverse_proxy 127.0.0.1:9001
    }
    
    # Health check
    handle /health {
        reverse_proxy 127.0.0.1:9001
    }
    
    # Default to L9 API
    handle {
        reverse_proxy l9-api:8000
    }
}
```

Reload Caddy:

```bash
sudo systemctl reload caddy
```

### Verify Setup

```bash
# From anywhere (no SSH needed!)
curl https://l9.quantumaipartners.com/health
curl -H "Authorization: Bearer YOUR_API_KEY" https://l9.quantumaipartners.com/mcp/tools
```

---

## SSH Tunnel (Legacy/Development Only)

**Note:** SSH tunnel is no longer required for production. Use only for local development if needed.

```bash
# Only if you need direct access bypassing Cloudflare
ssh -L 9001:127.0.0.1:9001 root@157.180.73.53
```

Then access via `http://127.0.0.1:9001` locally.

---

## Testing & Debugging

### Test Connection (Production - via Cloudflare)

```bash
# Test health endpoint (no auth needed)
curl https://l9.quantumaipartners.com/health

# Test MCP tools endpoint (requires auth)
curl -H "Authorization: Bearer YOUR_API_KEY" \
  https://l9.quantumaipartners.com/mcp/tools

# From VPS directly (bypassing Cloudflare)
ssh root@157.180.73.53
curl http://127.0.0.1:9001/health
```

### Example Memory Operations

```bash
# Save a memory
curl -X POST https://l9.quantumaipartners.com/memory/save \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -d '{
    "content": "User prefers dark mode in IDE",
    "kind": "preference",
    "scope": "user",
    "duration": "long",
    "user_id": "ib-mac",
    "tags": ["ui", "settings"],
    "importance": 0.9
  }'

# Search memories
curl -X POST https://l9.quantumaipartners.com/memory/search \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -d '{
    "query": "dark mode preferences",
    "user_id": "ib-mac",
    "top_k": 5,
    "duration": "all"
  }'

# Get stats
curl https://l9.quantumaipartners.com/memory/stats \
  -H "Authorization: Bearer YOUR_API_KEY"
```

---

## Troubleshooting

### "Connection refused" or timeout

1. **Check Cloudflare DNS:** Verify `l9.quantumaipartners.com` resolves correctly
   ```bash
   dig l9.quantumaipartners.com
   ```

2. **Check Caddy routing:** Ensure paths are configured correctly
   ```bash
   ssh root@157.180.73.53
   sudo systemctl status caddy
   sudo journalctl -u caddy -f
   ```

3. **Check MCP server:** Verify service is running
   ```bash
   sudo systemctl status l9-mcp
   sudo journalctl -u l9-mcp -f
   ```

4. **Test locally on VPS:**
   ```bash
   curl http://127.0.0.1:9001/health
   ```

### PostgreSQL connection errors

- Verify Postgres is running: `sudo systemctl status postgresql`
- Check MEMORY_DSN in `.env`
- Test from VPS: `psql -U postgres -d l9_memory -c "SELECT COUNT(*) FROM memory.long_term;"`

### Embedding failures

- Check OpenAI API key: `echo $OPENAI_API_KEY`
- Test OpenAI directly: `python -c "from openai import AsyncOpenAI; ..."`
- Monitor quota at https://platform.openai.com/account/usage/overview

### High latency on vector searches

- Ensure pgvector indexes are created: `\d+ memory.long_term` (check for `ivfflat` indexes)
- Monitor index health: `ANALYZE memory.long_term;`
- Tune `lists` parameter in IVF index for your data size

---

## Next Steps

1. **Install** the server using `scripts/install.sh`
2. **Configure** MCP_API_KEY in `.env`
3. **Test** connectivity from your MacBook with SSH tunnel
4. **Integrate** MCP server into Cursor settings
5. **Monitor** logs and memory growth

End of Implementation Pack.
