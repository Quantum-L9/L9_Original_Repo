# L9 Memory Substrate — Architecture Documentation

> **Version:** 1.1.0
> **Status:** NOT Production Ready
> **Last Updated:** 2025-12-27
> **Component ID:** MEM-SUB-001
> **Governance Level:** Core Infrastructure

unified MCP‑memory system that now runs through l9-api, not separate systems.
​

How the pieces fit
MCP routes in l9-api
/mcp/call in api/server.py is the HTTP entrypoint for MCP memory tools, mounted on the main FastAPI app and sharing its infra (auth, logging, etc.).
​

MCP DB pool
mcp_init_db() from mcpmemory.src.db is wired into the l9-api lifespan so the asyncpg pool for the MCP memory database is initialized once at startup and reused by MCP tool calls.
​

MCP → substrate_service
The MCP handler on /mcp/call builds an MCPToolCall, then passes the main substrate_service into handle_tool_call(), which lets Tier‑1 (full Substrate DAG pipeline with Neo4j, embeddings, enrichment) handle writes instead of dropping straight to direct DB fallback.
​

## Overview

The L9 Memory Substrate is a hybrid memory system combining:

- **Structured Storage** — PostgreSQL for packets, events, reasoning traces
- **Vector Storage** — pgvector for semantic embeddings
- **Knowledge Graph** — Extracted facts and insights
- **LangGraph DAG** — Processing pipeline with insight extraction

## Architecture

```
                    ┌─────────────────────────────────────────────────────────┐
                    │                   Memory Substrate DAG                   │
                    │                                                         │
   PacketEnvelope   │  ┌────────┐   ┌───────────┐   ┌──────────────┐         │
        │           │  │ intake │──▶│ reasoning │──▶│ memory_write │         │
        ▼           │  └────────┘   └─────┬─────┘   └──────┬───────┘         │
   ┌─────────┐      │                     │                │                 │
   │ Ingestion│─────│─────────────────────┼────────────────┼─────────────────│
   │ Pipeline │      │                     │                │                 │
   └─────────┘      │                     ▼                ▼                 │
                    │              ┌─────────────┐  ┌───────────────┐        │
                    │              │semantic_embed│  │extract_insights│        │
                    │              └──────┬──────┘  └───────┬───────┘        │
                    │                     │                 │                 │
                    │                     ▼                 ▼                 │
                    │              ┌─────────────────────────────┐           │
                    │              │      store_insights         │           │
                    │              └──────────────┬──────────────┘           │
                    │                             │                          │
                    │                             ▼                          │
                    │              ┌─────────────────────────────┐           │
                    │              │   world_model_trigger       │           │
                    │              └──────────────┬──────────────┘           │
                    │                             │                          │
                    │                             ▼                          │
                    │              ┌─────────────────────────────┐           │
                    │              │       checkpoint            │           │
                    │              └─────────────────────────────┘           │
                    └─────────────────────────────────────────────────────────┘
                                              │
                    ┌─────────────────────────┼─────────────────────────┐
                    │                         ▼                         │
                    │    ┌─────────────────────────────────────────┐    │
                    │    │          PostgreSQL + pgvector          │    │
                    │    │                                         │    │
                    │    │  ┌──────────────┐  ┌─────────────────┐  │    │
                    │    │  │ packet_store │  │ semantic_memory │  │    │
                    │    │  └──────────────┘  └─────────────────┘  │    │
                    │    │                                         │    │
                    │    │  ┌───────────────────┐  ┌────────────┐  │    │
                    │    │  │ agent_memory_events│  │ knowledge_ │  │    │
                    │    │  └───────────────────┘  │ facts      │  │    │
                    │    │                         └────────────┘  │    │
                    │    │  ┌──────────────────┐  ┌─────────────┐  │    │
                    │    │  │ reasoning_traces │  │ checkpoints │  │    │
                    │    │  └──────────────────┘  └─────────────┘  │    │
                    │    └─────────────────────────────────────────┘    │
                    └───────────────────────────────────────────────────┘
```

## Packet Lifecycle

### 1. Ingestion

**Canonical Entrypoint:** `memory.ingestion.ingest_packet()` (see `memory/WIRING.md`)

```python
from memory.ingestion import ingest_packet
from memory.substrate_models import PacketEnvelopeIn

# Primary entrypoint (recommended)
result = await ingest_packet(PacketEnvelopeIn(
    packet_type="event",
    payload={"action": "user_login", "user_id": "123"},
    tags=["auth", "login"],
    ttl=datetime.utcnow() + timedelta(days=30),
))

# Alternative: Direct pipeline access (advanced)
from memory.ingestion import get_ingestion_pipeline
pipeline = get_ingestion_pipeline()
result = await pipeline.ingest(PacketEnvelopeIn(...))
```

**Ingestion Steps:**

1. Validate packet structure
2. Auto-generate tags from content
3. Store to `packet_store`
4. Store to `agent_memory_events`
5. Generate embedding (if text content)
6. Update lineage graph
7. Store artifacts

### 2. Processing (DAG)

The LangGraph DAG processes packets through these nodes:

| Node                       | Function                          |
| -------------------------- | --------------------------------- |
| `intake_node`              | Validate, normalize, set defaults |
| `reasoning_node`           | Generate StructuredReasoningBlock |
| `memory_write_node`        | Persist packet and reasoning      |
| `semantic_embed_node`      | Generate and store embedding      |
| `extract_insights_node`    | Extract facts and insights        |
| `store_insights_node`      | Persist to knowledge_facts        |
| `world_model_trigger_node` | Trigger world model updates       |
| `gc_trigger_node`          | Probabilistic TTL eviction        |
| `checkpoint_node`          | Save graph state                  |

### 3. Retrieval

```python
from memory.retrieval import get_retrieval_pipeline

pipeline = get_retrieval_pipeline()

# Semantic search
results = await pipeline.semantic_search("user authentication", top_k=10)

# Hybrid search (semantic + filters)
results = await pipeline.hybrid_search(
    query="login events",
    filters={"packet_type": "event", "tags": ["auth"]},
    min_score=0.7,
)

# Thread reconstruction
thread = await pipeline.fetch_thread(thread_id)

# Lineage traversal
lineage = await pipeline.fetch_lineage(packet_id, direction="ancestors")
```

## Insight Pipeline

### Extraction

The `InsightExtractionPipeline` uses heuristic rules (no ML):

```python
from memory.insight_extraction import get_insight_pipeline

pipeline = get_insight_pipeline()
result = await pipeline.extract_from_packet(envelope)

# Returns:
# {
#   "packet_id": "...",
#   "insights": [...],  # ExtractedInsight objects
#   "facts": [...]      # KnowledgeFact objects
# }
```

### Insight Types

| Type             | Description                            |
| ---------------- | -------------------------------------- |
| `conclusion`     | Derived from reasoning decision tokens |
| `pattern`        | Text content detection                 |
| `anomaly`        | Unusual patterns or values             |
| `recommendation` | Suggested actions                      |

### Knowledge Facts

Facts are stored as subject-predicate-object triples:

```sql
-- knowledge_facts table
fact_id UUID PRIMARY KEY
subject TEXT NOT NULL        -- "user_123"
predicate TEXT NOT NULL      -- "logged_in_at"
object JSONB NOT NULL        -- "2025-12-08T10:30:00Z"
confidence FLOAT             -- 0.85
source_packet UUID           -- FK to packet_store
```

## Housekeeping

### Garbage Collection

```python
from memory.housekeeping import get_housekeeping_engine

engine = get_housekeeping_engine()
result = await engine.run_full_gc()

# Returns:
# {
#   "status": "ok",
#   "cleaned": {
#     "ttl_evicted": 15,
#     "orphans_cleaned": 3,
#     "tags_gc": 8
#   }
# }
```

### GC Operations

| Operation                    | Description                     |
| ---------------------------- | ------------------------------- |
| `evict_expired_ttl`          | Remove packets with expired TTL |
| `cleanup_orphan_packets`     | Fix invalid parent references   |
| `cleanup_parentless_packets` | Remove abandoned packets        |
| `cleanup_orphan_artifacts`   | Remove orphan embeddings/events |
| `gc_unused_tags`             | Remove low-usage tags           |

## API Reference

### Endpoints

**Base Path:** `/memory` (mounted in `api/server.py`)

| Method | Path               | Status               | Description                                         |
| ------ | ------------------ | -------------------- | --------------------------------------------------- |
| POST   | `/packet`          | ✅ **Implemented**   | Submit packet                                       |
| POST   | `/semantic/search` | ✅ **Implemented**   | Semantic search                                     |
| GET    | `/stats`           | ✅ **Implemented**   | Get memory statistics                               |
| GET    | `/packet/{id}`     | ⚠️ **Backend Ready** | Get packet by ID (repository method exists)         |
| POST   | `/hybrid/search`   | ⚠️ **Backend Ready** | Hybrid search (retrieval pipeline exists)           |
| GET    | `/thread/{id}`     | ⚠️ **Backend Ready** | Get thread packets (repository method exists)       |
| GET    | `/lineage/{id}`    | ⚠️ **Backend Ready** | Get packet lineage (retrieval pipeline exists)      |
| GET    | `/facts`           | ⚠️ **Backend Ready** | Query knowledge facts (repository method exists)    |
| GET    | `/insights`        | ⚠️ **Backend Ready** | Query insights (extraction pipeline exists)         |
| POST   | `/gc/run`          | ⚠️ **Backend Ready** | Run garbage collection (housekeeping engine exists) |
| GET    | `/gc/stats`        | ⚠️ **Backend Ready** | Get GC statistics (housekeeping engine exists)      |
| GET    | `/health`          | ⚠️ **Backend Ready** | Health check (service.health_check() exists)        |

**Note:** Endpoints marked "Backend Ready" have full repository/service support but need API route handlers added to `api/memory/router.py`.

### Client SDK

**✅ Memory Client SDK exists:** `clients/memory_client.py`

The `MemoryClient` is a complete async HTTP client that wraps all memory substrate API endpoints. It's used throughout the codebase (195+ references) and provides a clean interface for memory operations.

```python
from clients.memory_client import MemoryClient, get_memory_client

# Singleton pattern (recommended)
client = get_memory_client()

# Or direct instantiation
async with MemoryClient(base_url="http://l9-api:8000") as client:
    # Write packet
    result = await client.write_packet(
        packet_type="insight",
        payload={"summary": "User behavior analysis"},
    )

    # Semantic search
    results = await client.semantic_search("user behavior", top_k=10)

    # Hybrid search (requires API endpoint)
    results = await client.hybrid_search(
        query="login events",
        filters={"packet_type": "event"},
    )

    # Fetch lineage (requires API endpoint)
    lineage = await client.fetch_lineage(packet_id, direction="ancestors")

    # Fetch facts (requires API endpoint)
    facts = await client.fetch_facts(subject="user_123")

    # Run GC (requires API endpoint)
    gc_result = await client.run_gc()
```

**Important:** The client expects endpoints at `/api/v1/memory/*`, but the router is mounted at `/memory/*`. Either:

1. Update client base URL to include `/api/v1` prefix, or
2. Add `/api/v1` prefix to router mount path in `api/server.py`

**Current Implementation:**

- ✅ Client SDK: Complete (`clients/memory_client.py`)
- ✅ Backend methods: All repository/service methods exist
- ⚠️ API routes: Only 3/11 endpoints implemented in `api/memory/router.py`

## Database Schema

### Core Tables

```sql
-- packet_store (central packet storage)
packet_id UUID PRIMARY KEY
packet_type TEXT NOT NULL
envelope JSONB NOT NULL
timestamp TIMESTAMPTZ
thread_id UUID
parent_ids UUID[]
tags TEXT[]
ttl TIMESTAMP

-- semantic_memory (vector embeddings)
embedding_id UUID PRIMARY KEY
agent_id TEXT
vector VECTOR(1536)
payload JSONB
created_at TIMESTAMPTZ

-- knowledge_facts (extracted facts)
fact_id UUID PRIMARY KEY
subject TEXT NOT NULL
predicate TEXT NOT NULL
object JSONB NOT NULL
confidence FLOAT
source_packet UUID REFERENCES packet_store
created_at TIMESTAMP
```

### Migrations

Apply in order:

1. `0001_init_memory_substrate.sql` — Core tables
2. `0002_enhance_packet_store.sql` — Thread/lineage/tags/TTL
3. `0004_init_knowledge_facts.sql` — Knowledge facts table

## Configuration

| Variable             | Default                | Description                  |
| -------------------- | ---------------------- | ---------------------------- |
| `DATABASE_URL`       | -                      | PostgreSQL connection string |
| `OPENAI_API_KEY`     | -                      | For OpenAI embeddings        |
| `EMBEDDING_MODEL`    | text-embedding-3-large | Embedding model              |
| `EMBEDDING_PROVIDER` | openai                 | `openai` or `stub`           |
| `DB_POOL_SIZE`       | 5                      | Connection pool size         |
| `DB_MAX_OVERFLOW`    | 10                     | Pool overflow limit          |

## Examples

### Full Packet Lifecycle

```python
from memory.substrate_models import PacketEnvelopeIn, PacketLineage
from memory.substrate_service import create_substrate_service

# Initialize service
service = await create_substrate_service(
    database_url="postgresql://...",
    embedding_provider_type="openai",
)

# Create packet with lineage
packet = PacketEnvelopeIn(
    packet_type="analysis",
    payload={
        "subject": "user_behavior",
        "content": "Analysis of user login patterns shows...",
        "metrics": {"login_count": 150, "avg_duration": 45.2},
    },
    lineage=PacketLineage(
        parent_ids=[parent_packet_id],
        derivation_type="inference",
    ),
    tags=["analytics", "user_behavior"],
    ttl=datetime.utcnow() + timedelta(days=90),
)

# Process through DAG
result = await service.write_packet(packet)
print(f"Written to: {result.written_tables}")
```

### Insight Extraction

```python
from memory.insight_extraction import get_insight_pipeline

pipeline = get_insight_pipeline()

# Extract insights from existing packet
insights = await pipeline.extract_from_packet(envelope)

# Detect anomalies
anomalies = await pipeline.detect_anomalies(
    packet,
    historical_window=100,
)
```

---

_L9 Memory Substrate Documentation — v1.1.0_
