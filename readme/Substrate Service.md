# L9 Memory Substrate Service

## Overview

The **MemorySubstrateService** is the central orchestration layer for L9's memory system. It coordinates all memory operations across PostgreSQL, Neo4j, Redis, and pgvector.

## Architecture

```
┌────────────────────────────────────────────────────────────────┐
│                    API Layer (FastAPI)                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐  │
│  │ /api/memory  │  │  /mcp/call   │  │  /api/v1/memory/...  │  │
│  └──────┬───────┘  └──────┬───────┘  └──────────┬───────────┘  │
└─────────┼─────────────────┼─────────────────────┼──────────────┘
          │                 │                     │
          v                 v                     v
┌────────────────────────────────────────────────────────────────┐
│               MemorySubstrateService (singleton)                │
│                   memory/substrate_service.py                   │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  - ingest_packet()     - semantic_search()               │  │
│  │  - get_packet()        - health_check()                  │  │
│  │  - fetch_and_enrich()  - get_consolidation()            │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────┬─────────────────┬─────────────────────┬──────────────┘
          │                 │                     │
          v                 v                     v
┌─────────────────┐ ┌───────────────┐ ┌───────────────────────────┐
│ SubstrateDAG    │ │ SemanticSvc   │ │ SubstrateRepository       │
│ (LangGraph)     │ │ (pgvector)    │ │ (PostgreSQL + RLS)        │
│                 │ │               │ │                           │
│ - reasoning     │ │ - embed()     │ │ - write_packet()          │
│ - semantic      │ │ - search()    │ │ - read_packet()           │
│ - insights      │ │               │ │ - get_facts_by_subject()  │
│ - world_model   │ │               │ │                           │
└─────────────────┘ └───────────────┘ └───────────────────────────┘
          │                 │                     │
          v                 v                     v
┌─────────────────────────────────────────────────────────────────┐
│                      Storage Layer                               │
│  ┌──────────┐  ┌───────────────┐  ┌───────────┐  ┌───────────┐  │
│  │PostgreSQL│  │   pgvector    │  │   Neo4j   │  │   Redis   │  │
│  │packet_   │  │semantic_memory│  │ (graph)   │  │ (cache)   │  │
│  │store     │  │               │  │           │  │           │  │
│  └──────────┘  └───────────────┘  └───────────┘  └───────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

## Key Components

### MemorySubstrateService (`memory/substrate_service.py`)

The singleton service that orchestrates all memory operations:

```python
from memory.substrate_service import get_service

# Get singleton instance
service = await get_service()

# Ingest a packet
result = await service.ingest_packet(packet_in)

# Semantic search
results = await service.semantic_search(search_request)
```

### SubstrateDAG (`memory/substrate_dag.py`)

LangGraph-based pipeline for packet processing:

- **reasoning_node** — Extracts reasoning metadata
- **semantic_embed_node** — Generates embeddings via pgvector
- **extract_insights_node** — Extracts knowledge facts
- **world_model_trigger_node** — Updates world model

### SubstrateRepository (`memory/substrate_repository.py`)

PostgreSQL access with Row-Level Security (RLS):

- Multi-tenant isolation via `app.tenant_id`, `app.org_id`, `app.user_id`
- Automatic RLS context setting before queries
- Connection pooling with asyncpg

### SemanticService (`memory/semantic_service.py`)

pgvector-powered vector operations:

- 1536-dimensional OpenAI embeddings
- HNSW index for fast similarity search
- Importance scoring and decay

## API Endpoints

### MCP Endpoints (Primary for Cursor)

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/mcp/call` | POST | Execute MCP tools (`save_memory`, `search_memory`, `get_memory_stats`) |
| `/mcp/tools` | GET | List available MCP tools |
| `/mcp/health` | GET | MCP-specific health check |

### Memory Router Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/v1/memory/packet` | POST | Ingest packet via DAG pipeline |
| `/api/v1/memory/semantic/search` | POST | Semantic similarity search |
| `/api/v1/memory/stats` | GET | Memory system statistics |
| `/api/v1/memory/batch` | POST | Batch packet ingestion |
| `/api/v1/memory/saga/fetch-and-enrich` | POST | Cross-DB fetch + graph enrichment |
| `/api/v1/memory/warm` | POST | Predictive memory warming |

## Multi-Tenant Isolation

### RLS Context

```sql
-- Set session context before queries
SET app.tenant_id = 'l9';
SET app.org_id = 'quantumai';
SET app.user_id = 'cursor';
SET app.role = 'developer';
```

### Scope Separation

| Scope | Access |
|-------|--------|
| `developer` | Cursor + L + admins |
| `global` | Everyone |
| `l-private` | L only (CTO kernel) |

## Governance Gate

All memory operations pass through governance context:

```python
from memory.governance_gate import build_governance_context, governance_context

ctx = build_governance_context(
    caller_id="C",
    role="developer",
    scope="developer",
    project_id="l9",
)

async with governance_context(ctx):
    result = await service.semantic_search(request)
```

## Initialization

The service is initialized during FastAPI lifespan:

```python
# api/server.py lifespan
async with lifespan_ctx as state:
    state.substrate_service = await get_service()
```

## Configuration

Environment variables:

| Variable | Purpose | Default |
|----------|---------|---------|
| `L9_DATABASE_URL` | PostgreSQL connection | `postgresql://...` |
| `L9_REDIS_URL` | Redis connection | `redis://localhost:6379` |
| `NEO4J_URI` | Neo4j connection | `bolt://localhost:7687` |
| `L9_OPENAI_API_KEY` | Embedding generation | (required) |
| `L9_PROJECT_ID` | Project identifier | `l9` |
| `L9_MEMORY_SCOPE` | Default scope | `shared` |

## Related Files

| File | Purpose |
|------|---------|
| `memory/substrate_service.py` | Main service singleton |
| `memory/substrate_repository.py` | PostgreSQL repository |
| `memory/substrate_dag.py` | LangGraph ingestion pipeline |
| `memory/semantic_service.py` | pgvector operations |
| `memory/governance_gate.py` | RLS context management |
| `memory/ingestion.py` | Canonical `ingest_packet()` |
| `memory/retrieval.py` | RetrievalPipeline |
| `memory/consolidation.py` | Deduplication + archival |
| `api/memory/router.py` | FastAPI router |
| `api/routes/mcp.py` | MCP tool router |
| `migrations/README.md` | Database schema docs |

---

*L9 Secure AI OS — Memory Substrate Service*
*Last updated: 2026-01-24*
