# Cursor Memory Client

> **File:** `agents/cursor/cursor_memory_client.py`  
> **Server:** C1 Hetzner (`mcp.quantumaipartners.com`)  
> **Last Verified:** 2026-01-29  
> **RLS Verified:** 2026-01-29 (13 tables with RLS, `platform_admin` role)

---

## Architecture — C1 Memory Stack

```
┌──────────────────────────────────────────────────────────────────────────┐
│  C1 Hetzner (46.62.243.82)                                               │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐     │
│  │  PostgreSQL │  │  pgvector   │  │  Neo4j      │  │  Redis      │     │
│  │  :30432     │  │  (embedded) │  │  :30474     │  │  :30379     │     │
│  └──────┬──────┘  └──────┬──────┘  └─────────────┘  └─────────────┘     │
│         │                │                                               │
│         └────────┬───────┘                                               │
│                  ▼                                                       │
│         ┌───────────────┐      ┌───────────────┐                        │
│         │  L9 API       │      │  MCP Memory   │ ← PRIMARY              │
│         │  :30080       │      │  :30902       │                        │
│         └───────────────┘      └───────┬───────┘                        │
└────────────────────────────────────────│────────────────────────────────┘
                                         │ HTTP
                                         ▼
┌──────────────────────────────────────────────────────────────────────────┐
│  Mac (Local)                                                             │
│  cursor_memory_client.py → mcp_call_tool() → /mcp/call                   │
└──────────────────────────────────────────────────────────────────────────┘
```

---

## Quick Start

```bash
cd /Users/ib-mac/Projects/L9

# Health check (tests MCP + API)
python3 agents/cursor/cursor_memory_client.py health

# Search memory
python3 agents/cursor/cursor_memory_client.py search "governance rules"

# Write to memory
python3 agents/cursor/cursor_memory_client.py write "lesson content" --kind lesson

# Get stats
python3 agents/cursor/cursor_memory_client.py stats
```

---

## Environment

```bash
# Required in .env (L9 project root)
MCP_API_KEY_C=<cursor-key>        # PRIMARY - identifies caller as Cursor
L9_API_URL=http://mcp.quantumaipartners.com:30080    # L9 API
MCP_URL=http://mcp.quantumaipartners.com:30902       # MCP Memory Server
```

---

## Memory Operations Flow

### WRITE — How Content Gets Stored

```
cmd_write("content", kind="lesson")
         │
         ▼
┌─────────────────────────────────────────────────────────────────┐
│ 1. BUILD PACKET                                                  │
│    - Generate daily session UUID (same ID all day)               │
│    - Map kind → duration (lesson=long, note=medium)              │
│    - Set scope="developer" (Cursor can't write to l-private)     │
└─────────────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────────┐
│ 2. MCP CALL                                                      │
│    POST http://mcp.quantumaipartners.com:30902/mcp/call          │
│    {                                                             │
│      "tool_name": "save_memory",                                 │
│      "arguments": {                                              │
│        "content": "...",                                         │
│        "kind": "lesson",                                         │
│        "scope": "developer",                                     │
│        "duration": "long",                                       │
│        "user_id": "l9-shared",                                   │
│        "tags": [],                                               │
│        "importance": 1.0                                         │
│      }                                                           │
│    }                                                             │
└─────────────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────────┐
│ 3. SERVER PIPELINE (main_dag)                                    │
│    a) Write to `packets` table (PostgreSQL)                      │
│    b) Generate embedding (pgvector)                              │
│    c) Extract facts → `knowledge_facts` table                    │
│    d) Create relationships → `relationships` table               │
│    e) Return packet_id + enrichment status                       │
└─────────────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────────┐
│ 4. RESPONSE                                                      │
│    {                                                             │
│      "packet_id": "uuid-here",                                   │
│      "written_tables": ["packets", "knowledge_facts", ...],      │
│      "ingest_time_ms": 350,                                      │
│      "enrichment_status": "success",                             │
│      "tier_used": "full"                                         │
│    }                                                             │
└─────────────────────────────────────────────────────────────────┘
```

### SEARCH — How Content Gets Retrieved

```
cmd_search("governance rules", limit=10)
         │
         ▼
┌─────────────────────────────────────────────────────────────────┐
│ 1. MCP CALL                                                      │
│    POST http://mcp.quantumaipartners.com:30902/mcp/call          │
│    {                                                             │
│      "tool_name": "search_memory",                               │
│      "arguments": {                                              │
│        "query": "governance rules",                              │
│        "user_id": "l9-shared",                                   │
│        "scopes": ["developer", "global"],                        │
│        "top_k": 20,                                              │
│        "threshold": 0.0,                                         │
│        "duration": "all"                                         │
│      }                                                           │
│    }                                                             │
└─────────────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────────┐
│ 2. SERVER PROCESSING                                             │
│    a) Generate embedding for query (pgvector)                    │
│    b) Vector similarity search against stored embeddings         │
│    c) Filter by scope (developer, global)                        │
│    d) Rank by similarity score                                   │
│    e) Return top_k results                                       │
└─────────────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────────┐
│ 3. CLIENT POST-PROCESSING                                        │
│    a) Filter by min_confidence (if specified)                    │
│    b) Sort by: relevance | importance | recency                  │
│    c) Limit to requested count                                   │
│    d) Return results with similarity scores                      │
└─────────────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────────┐
│ 4. RESPONSE                                                      │
│    {                                                             │
│      "query": "governance rules",                                │
│      "hits": [                                                   │
│        {"embedding_id": "...", "similarity": 0.85, ...},         │
│        {"embedding_id": "...", "similarity": 0.72, ...}          │
│      ],                                                          │
│      "count": 8                                                  │
│    }                                                             │
└─────────────────────────────────────────────────────────────────┘
```

### INJECT — 5-Layer Context Loading

```
cmd_inject("memory substrate work")
         │
         ▼
┌─────────────────────────────────────────────────────────────────┐
│ LAYER 1: PREFERENCES                                             │
│    search_memory("Igor preferences coding style")                │
│    → Load user preferences for coding patterns                   │
└─────────────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────────┐
│ LAYER 2: LESSONS                                                 │
│    search_memory("lessons learned {task}")                       │
│    → Load past mistakes and learnings                            │
└─────────────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────────┐
│ LAYER 3: DOMAIN                                                  │
│    search_memory("{task} patterns architecture")                 │
│    → Load domain-specific context                                │
└─────────────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────────┐
│ LAYER 4: TEMPORAL                                                │
│    search_memory("session recent {date}")                        │
│    → Load recent session activity                                │
└─────────────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────────┐
│ LAYER 5: WARNINGS                                                │
│    search_memory("mistakes errors avoid {task}")                 │
│    → Surface anti-patterns to avoid                              │
└─────────────────────────────────────────────────────────────────┘
```

---

## Write Kinds & Durations

| Kind         | Duration | TTL      | Use For                    |
|--------------|----------|----------|----------------------------|
| `preference` | long     | Forever  | Igor's preferences         |
| `lesson`     | long     | Forever  | Lessons learned            |
| `insight`    | long     | Forever  | Strategic insights         |
| `fact`       | long     | Forever  | Knowledge facts            |
| `rule`       | long     | Forever  | Governance rules           |
| `error`      | medium   | 90 days  | Error patterns             |
| `note`       | medium   | 90 days  | General notes              |

---

## Search Options

```bash
--limit N           # Max results (default 10)
--min-confidence X  # 0.0-1.0 similarity threshold
--sort TYPE         # relevance | importance | recency
```

**Examples:**

```bash
# High-confidence results only
python3 agents/cursor/cursor_memory_client.py search "docker" --min-confidence 0.5

# Sort by most recent
python3 agents/cursor/cursor_memory_client.py search "GMP" --sort recency

# Limit to 3 results
python3 agents/cursor/cursor_memory_client.py search "error" --limit 3
```

---

## All 27 Commands

### Core Memory Commands (6)

| Command    | What It Does                         | Definition              |
|------------|--------------------------------------|-------------------------|
| `health`   | Check MCP endpoint + API health      | `cmd_health()` line 249 |
| `stats`    | Get packet counts, embeddings, facts | `cmd_stats()` line 237  |
| `search`   | Semantic search with filtering       | `cmd_search()` line 329 |
| `write`    | Write packet to memory               | `cmd_write()` line 387  |
| `session`  | Show current daily session UUID      | `cmd_session()` line 431|
| `mcp-test` | Round-trip test (write + search)     | `cmd_mcp_test()` line 447|

### Session Commands (4)

| Command          | What It Does                           |
|------------------|----------------------------------------|
| `session-close`  | Close session, create embedding anchor |
| `session-resume` | Resume with context from past sessions |
| `resume-for`     | Resume for specific task by similarity |
| `session-diff`   | Compare current session to previous    |

### Context Injection Commands (6)

| Command        | What It Does                                       |
|----------------|----------------------------------------------------|
| `inject`       | 5-layer context injection (prefs, lessons, domain) |
| `warn`         | Surface past mistakes relevant to task             |
| `suggest`      | Pattern-based next-step suggestions                |
| `temporal`     | Time-windowed search (24h, 7d, 30d)                |
| `fix-error`    | Find past fixes for an error                       |
| `dedupe-check` | Check if content already exists                    |

### Graph Commands - Neo4j (5)

| Command         | What It Does                 |
|-----------------|------------------------------|
| `graph-health`  | Check Neo4j health           |
| `graph-context` | Get context for a domain     |
| `graph-query`   | Run Cypher query             |
| `graph-entity`  | Get entity by type and ID    |
| `graph-rels`    | Get relationships for entity |

### Cache Commands - Redis (6)

| Command             | What It Does                |
|---------------------|------------------------------|
| `cache-health`      | Check Redis health          |
| `cache-get`         | Get value by key            |
| `cache-set`         | Set value with optional TTL |
| `cache-session`     | Get current session context |
| `cache-set-session` | Set session context         |
| `cache-sessions`    | List recent sessions        |

---

## Database Schema

### packets table (PostgreSQL)

```sql
CREATE TABLE packets (
    id UUID PRIMARY KEY,
    user_id VARCHAR(255),
    content TEXT,
    kind VARCHAR(50),
    scope VARCHAR(50),
    importance FLOAT,
    created_at TIMESTAMP,
    session_id UUID,
    schema_version VARCHAR(20)
);
```

### embeddings table (pgvector)

```sql
CREATE TABLE embeddings (
    id UUID PRIMARY KEY,
    packet_id UUID REFERENCES packets(id),
    embedding vector(1536),  -- OpenAI embedding dimension
    created_at TIMESTAMP
);
```

---

## Row-Level Security (RLS)

All memory tables use PostgreSQL Row-Level Security for multi-tenant isolation.

### RLS Credentials (Deterministic UUIDs)

The client uses deterministic UUIDs generated from string identifiers via `uuid5`:

| Identifier       | String Value  | UUID                                   |
|------------------|---------------|----------------------------------------|
| **Tenant**       | `l9`          | `73350468-3158-5d0f-9b8c-9b193d96fc4b` |
| **Organization** | `quantumai`   | `14910cef-fea1-51d7-9a28-05579e6c0c18` |
| **User**         | `l9-shared`   | `2f00c090-3816-51a0-806c-34d32522a070` |

**Source:** `config/rls_config.py`

### How RLS Works

```
cursor_memory_client.py
         │
         ▼
MCP Server (mcp_memory/src/main.py)
         │
         ├─► get_rls_config()  →  RLSConfig(tenant="l9", org="quantumai", user="l9-shared")
         │
         ▼
memory/substrate_repository.py
         │
         └─► SELECT l9_set_scope(tenant_uuid, org_uuid, user_uuid, role)
                    │
                    ▼
            PostgreSQL: SET LOCAL app.tenant_id = '...'
                        SET LOCAL app.org_id = '...'
                        SET LOCAL app.user_id = '...'
                        SET LOCAL app.role = 'platform_admin'
                    │
                    ▼
            RLS policies enforced per-transaction
```

### RLS Roles

| Role             | Access Level                                    |
|------------------|------------------------------------------------|
| `platform_admin` | Full access to all data (default for Cursor)   |
| `tenant_admin`   | Full access within tenant                      |
| `org_admin`      | Full access within organization                |
| `end_user`       | Access to own data + shared scope only         |

### Tables with RLS Enabled (13)

| Table                     | Policy Type                              |
|---------------------------|------------------------------------------|
| `packet_store`            | tenant + org + scope + admin override    |
| `semantic_memory`         | tenant + org + scope + admin override    |
| `knowledge_facts`         | tenant + org + scope + admin override    |
| `episodic_events`         | tenant + role-based (platform/tenant/end)|
| `episodic_semantic_links` | inherited from episodic_events           |
| `memory_embeddings`       | tenant + org + admin override            |
| `memory_access_log`       | tenant + org + admin override            |
| `entity_relationships`    | tenant + org + admin override            |
| `memory_summaries`        | tenant + org + admin override            |
| `reflection_store`        | tenant + org + admin override            |
| `task_reflections`        | tenant + org + admin override            |
| `semantic_facts`          | tenant + role-based                      |
| `feedback_events`         | tenant + org + admin override            |

### Direct PostgreSQL Access (Bypass Client)

```bash
# SSH to C1 and set RLS context manually
ssh c1 "docker exec l9-postgres psql -U postgres -d l9_memory -c \"
SELECT l9_set_scope(
    '73350468-3158-5d0f-9b8c-9b193d96fc4b'::uuid,  -- tenant (l9)
    '14910cef-fea1-51d7-9a28-05579e6c0c18'::uuid,  -- org (quantumai)
    '2f00c090-3816-51a0-806c-34d32522a070'::uuid,  -- user (l9-shared)
    'platform_admin'                                -- role
);

-- Now all queries respect RLS
SELECT COUNT(*) FROM packet_store;
SELECT packet_type, COUNT(*) FROM packet_store GROUP BY packet_type;
\""
```

### Neo4j Access (No RLS)

Neo4j uses password authentication, not RLS:

```bash
# Direct cypher-shell access
ssh c1 "docker exec l9-neo4j cypher-shell \
  -u neo4j \
  -p 'FVmgaD1diPcz41zRbYLLP0UzyGvAi4E' \
  'MATCH (n) RETURN labels(n) as type, count(*) ORDER BY count DESC'"

# Current node counts
# Tool: 118
# API: 15
# Kernel: 10
# Agent: 2
```

### Environment Overrides

Override RLS identifiers via environment variables:

```bash
# In .env
RLS_TENANT_ID=l9          # Default: "l9"
RLS_ORG_ID=quantumai      # Default: "quantumai"
RLS_USER_ID=l9-shared     # Default: "l9-shared"
```

---

## Troubleshooting

### Health Check Failed

```bash
# Check if C1 is reachable
curl -s http://mcp.quantumaipartners.com:30902/health

# Check API key is set
echo $MCP_API_KEY_C

# Test MCP endpoint directly
curl -X POST http://mcp.quantumaipartners.com:30902/mcp/call \
  -H "Authorization: Bearer $MCP_API_KEY_C" \
  -H "Content-Type: application/json" \
  -d '{"tool_name": "get_memory_stats", "arguments": {"user_id": "l9-shared", "duration": "all"}}'
```

### Write Returns Error

1. Check API key is correct (`MCP_API_KEY_C`)
2. Verify C1 is running (`docker ps` on C1)
3. Check content isn't too long (max ~10KB)

### Search Returns No Content

The search returns embeddings with similarity scores. To get full content:
1. Use the `packet_id` from search results
2. Query the packets table directly (if needed)

### RLS Error: "RLS scope required"

If you see `RLS scope required for MemorySubstratePacketSource (tenant_id, org_id, user_id)`:

1. The client isn't setting RLS context before queries
2. Fix: Ensure `l9_set_scope()` is called in the transaction

```python
# In your code, before any query:
await session.execute(
    "SELECT l9_set_scope($1::uuid, $2::uuid, $3::uuid, $4::text)",
    tenant_uuid, org_uuid, user_uuid, "platform_admin"
)
```

### Migration FK Constraint Error

If migration fails with "no unique constraint matching given keys":

- **Cause:** FK references a column without UNIQUE or PRIMARY KEY
- **Fix:** Remove FK constraint or add UNIQUE index to referenced column

```sql
-- ❌ WRONG: thread_id is NOT unique in packet_store
thread_id UUID REFERENCES packet_store(thread_id)

-- ✅ CORRECT: Remove FK, keep as plain UUID
thread_id UUID  -- no FK constraint
```

---

## C1 Endpoints Reference

| Service        | Endpoint                                    | Port  |
|----------------|---------------------------------------------|-------|
| **MCP Memory** | `http://mcp.quantumaipartners.com:30902`    | 30902 |
| **L9 API**     | `http://mcp.quantumaipartners.com:30080`    | 30080 |
| **PostgreSQL** | `46.62.243.82:30432`                        | 30432 |
| **Neo4j HTTP** | `http://46.62.243.82:30474`                 | 30474 |
| **Neo4j Bolt** | `bolt://46.62.243.82:30687`                 | 30687 |
| **Redis**      | `46.62.243.82:30379`                        | 30379 |

---

## Governance Rules in Memory

As of 2026-01-29, the following governance rules are stored:

| Rule                  | Packet ID                              |
|-----------------------|----------------------------------------|
| KERNEL_TIER           | `c85492dc-8da9-56cd-a078-3f75a4bdc0d5` |
| RUNTIME_TIER          | `6ece3805-3968-581a-b12c-e253cf2e59f0` |
| INFRA_TIER            | `38bf5c64-d6bf-5631-b51d-bc0c1d1ec91f` |
| UX_TIER               | `db1d2952-7b21-5b73-a018-2aad473307b8` |
| Required Patterns     | `85e67e52-657c-5cba-a47b-972b6917d91f` |
| Forbidden Patterns    | `ac596545-65d6-5ed1-9404-08e36203dfe6` |
| Protected Files List  | `12a97f6f-4893-536a-8741-626aab140a58` |
| GMP Phases            | `7e4486a2-b3d6-5689-becb-3a0d8b8e4d6c` |

Search with:
```bash
python3 agents/cursor/cursor_memory_client.py search "GOVERNANCE RULE"
python3 agents/cursor/cursor_memory_client.py search "KERNEL_TIER protected"
python3 agents/cursor/cursor_memory_client.py search "forbidden patterns"
```
