# MCP Memory — Agent Integration Guide

**Status:** ✅ **PRODUCTION** — Verified E2E 2026-02-13
**Audience:** AI agents (Cursor IDE, Emma, future agents) — not humans
**Server:** C1 Hetzner (46.62.243.82)

---

## Architecture

```
┌──────────────────────────────────────────────────────────────┐
│  Agent (Cursor IDE / Emma / Future Agent)                    │
│  └─ HTTP POST → http://46.62.243.82:9002/mcp/call           │
│     Header: Authorization: Bearer <MCP_API_KEY_C>            │
└──────────────────────┬───────────────────────────────────────┘
                       │ Port 9002 (direct, no proxy)
┌──────────────────────▼───────────────────────────────────────┐
│  C1 VPS (46.62.243.82)                                       │
│  ├─ l9-mcp-memory (Docker, port 9002) ← HIT THIS DIRECTLY   │
│  │   ├─ /health              Health check (no auth)          │
│  │   ├─ /mcp/tools           List tools (auth required)      │
│  │   └─ /mcp/call            Execute tool (auth required)    │
│  │                                                           │
│  ├─ PostgreSQL (port 30432)                                  │
│  │   ├─ packet_store         Canonical event log             │
│  │   ├─ semantic_memory      Vector embeddings (pgvector)    │
│  │   ├─ knowledge_facts      Extracted facts                 │
│  │   ├─ reasoning_traces     Reasoning audit trail           │
│  │   ├─ agent_memory_events  Agent event log                 │
│  │   └─ graph_checkpoints    Graph state snapshots           │
│  │                                                           │
│  ├─ Neo4j (port 30474)       Knowledge graph (optional)      │
│  └─ Redis (port 30379)       Session cache                   │
└──────────────────────────────────────────────────────────────┘
```

**Direct connection to port 9002.** No nginx, no Caddy, no reverse proxy. The MCP memory server binds to `0.0.0.0:9002` inside Docker and is published on the host.

---

## Endpoints

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `http://46.62.243.82:9002/health` | GET | None | Health check |
| `http://46.62.243.82:9002/mcp/tools` | GET | Bearer | List available tools |
| `http://46.62.243.82:9002/mcp/call` | POST | Bearer | Execute any MCP tool |

All tool calls go through `/mcp/call` with this payload shape:

```json
{
  "tool_name": "<tool_name>",
  "arguments": { ... }
}
```

Response shape:

```json
{
  "status": "success",
  "result": { ... },
  "caller": "C"
}
```

---

## Authentication & Caller Identity

| Caller | API Key Env Var | caller_id | creator | source | Default scope |
|--------|-----------------|-----------|---------|--------|---------------|
| **L** (L-CTO kernel) | `MCP_API_KEY_L` | `"L"` | `"L-CTO"` | `"l9-kernel"` | `"developer"` |
| **C** (Cursor IDE) | `MCP_API_KEY_C` | `"C"` | `"Cursor-IDE"` | `"cursor"` | `"cursor"` |

The server determines caller identity from the API key. `creator` and `source` are enforced server-side — agents cannot override them.

**Auth header format:**
```
Authorization: Bearer <your_api_key>
```

---

## Scopes & RLS

Every memory has a `scope` that controls visibility via PostgreSQL Row-Level Security.

| Scope | Who can read | Who can write | Use case |
|-------|-------------|---------------|----------|
| `cursor` | Cursor IDE, platform_admin | Cursor IDE | Cursor session context, lessons, preferences |
| `developer` | All callers | All callers | Shared development knowledge |
| `global` | All callers | All callers | Cross-project shared knowledge |
| `agent` | All callers | All callers | Agent-generated memories (Emma, etc.) |
| `l-private` | L-CTO, platform_admin | L-CTO | L-CTO private reasoning |

### Scope rules per caller

| Caller | Allowed scopes | Default write scope |
|--------|---------------|-------------------|
| **L** | `developer`, `global`, `l-private`, `cursor` | `developer` |
| **C** | `cursor`, `developer`, `global` | `cursor` |
| **Future agents (Emma, etc.)** | `agent`, `developer`, `global` | `agent` |

### RLS enforcement

- `role="end_user"` — default for all callers; can read/write `developer`, `global`, `agent`
- `role="cursor"` — set by cursor_memory_kernel; additionally can read/write `cursor` scope
- `role="l9_system"` — additionally can read/write `l-private` scope
- `role="platform_admin"` — full access to all scopes

RLS is enforced at the PostgreSQL level. Even if application code has a bug, the database will reject unauthorized scope access.

---

## Core Tools

### save_memory

Write a memory to the full DAG pipeline (6 tables).

```json
{
  "tool_name": "save_memory",
  "arguments": {
    "content": "The actual memory content to store",
    "kind": "lesson",
    "scope": "cursor",
    "duration": "long",
    "user_id": "l9-shared",
    "tags": ["optional", "tags"],
    "importance": 1.0
  }
}
```

**Required:** `content`, `kind`, `duration`, `user_id`
**Optional:** `scope` (defaults to caller's default), `tags`, `importance` (0.0-1.0)

**Valid `kind` values:** `preference`, `lesson`, `pattern`, `decision`, `error`, `success`, `context`, `insight`, `observation`

**Valid `duration` values:** `short` (24h TTL), `medium` (7d TTL), `long` (no expiry)

**Response includes:**
```json
{
  "packet_id": "uuid",
  "scope": "cursor",
  "written_tables": ["packet_store", "agent_memory_events", "reasoning_traces", "semantic_memory", "knowledge_facts", "graph_checkpoints"],
  "pipeline": "main_dag",
  "ingest_time_ms": 645.3
}
```

### search_memory

Semantic similarity search across memories.

```json
{
  "tool_name": "search_memory",
  "arguments": {
    "query": "what I'm looking for",
    "user_id": "l9-shared",
    "scopes": ["cursor", "developer", "global"],
    "top_k": 5,
    "threshold": 0.0,
    "duration": "all"
  }
}
```

**Required:** `query`, `user_id`
**Optional:** `scopes` (defaults to caller's allowed scopes), `top_k` (default 5), `threshold` (0.0-1.0, default 0.7), `duration`, `kinds` (filter by kind)

**Response:**
```json
{
  "results": [
    {
      "packet_id": "uuid",
      "content": "...",
      "kind": "lesson",
      "scope": "cursor",
      "similarity": 0.57,
      "importance": 0.5,
      "tags": [],
      "created_at": "2026-02-13T22:16:41Z"
    }
  ],
  "query_embedding_time_ms": 204.7,
  "search_time_ms": 3.6,
  "total_results": 1
}
```

### get_context

Proactive context injection — retrieves relevant memories + recent activity for a task.

```json
{
  "tool_name": "get_context",
  "arguments": {
    "task_description": "Working on RLS scope alignment",
    "user_id": "l9-shared",
    "scopes": ["cursor", "developer", "global"],
    "top_k": 5
  }
}
```

### Other tools

| Tool | Purpose |
|------|---------|
| `get_memory_stats` | Memory counts by duration/kind |
| `delete_expired_memories` | Clean up TTL-expired memories |
| `compound_memories` | Merge highly similar memories |
| `apply_decay` | Apply importance decay to old memories |
| `extract_session_learnings` | Extract and store session lessons/decisions/errors |
| `get_proactive_suggestions` | Get suggestions based on current context |
| `query_temporal` | Query memories by time range |
| `save_memory_with_confidence` | Save with explicit confidence scoring |
| `graph_query` | Neo4j Cypher query |
| `graph_get_entity` | Get entity from knowledge graph |
| `graph_get_context` | Get graph context for entity |
| `graph_create_event` | Create temporal event in graph |
| `graph_get_event_timeline` | Get event timeline |
| `graph_get_event_sequence` | Get event sequence |
| `graph_get_temporal_events` | Get events in time range |
| `cache_get` | Get Redis cache value |
| `cache_set` | Set Redis cache value |
| `cache_get_session_context` | Get session context from cache |
| `cache_delete` | Delete Redis cache key |
| `cache_keys` | List Redis cache keys by pattern |

---

## Agent Configuration

### Cursor IDE (caller C)

**Environment variables (MacBook `~/.zshrc` or project `.env`):**
```bash
MCP_API_KEY_C=<your-cursor-api-key>       # From VPS /opt/l9/.env
L9_EXECUTOR_API_KEY=<same-key>            # Legacy alias, same value
MCP_URL=http://46.62.243.82/memory        # Only if using nginx path (not recommended)
```

**CLI client:**
```bash
# Write (defaults to scope=cursor)
python3 agents/cursor/cursor_memory_client.py write "content" --kind lesson --scope cursor

# Search (searches cursor + developer + global)
python3 agents/cursor/cursor_memory_client.py search "query" --limit 5

# Health check
python3 agents/cursor/cursor_memory_client.py health
```

Note: The CLI client (`cursor_memory_client.py`) currently routes through nginx on port 80 (`http://46.62.243.82/memory/mcp/call`). For direct access, set `MCP_URL=http://46.62.243.82:9002`.

### Future agents (Emma, Research, etc.)

New agents should:

1. **Get an API key** — Add a new key to VPS `/opt/l9/.env` (e.g., `MCP_API_KEY_EMMA`)
2. **Register in `verify_api_key`** — Add key check in `mcp_memory/src/main.py`
3. **Use `role="end_user"`** — Standard role, access to `developer`, `global`, `agent` scopes
4. **Default to `scope="agent"`** — Agent-generated memories go in `agent` scope
5. **Hit port 9002 directly** — `http://46.62.243.82:9002/mcp/call`

**Example call from any HTTP client:**
```bash
curl -X POST http://46.62.243.82:9002/mcp/call \
  -H "Authorization: Bearer $MCP_API_KEY_EMMA" \
  -H "Content-Type: application/json" \
  -d '{
    "tool_name": "save_memory",
    "arguments": {
      "content": "User prefers morning meeting summaries",
      "kind": "preference",
      "scope": "agent",
      "duration": "long",
      "user_id": "l9-shared"
    }
  }'
```

---

## Pipeline Verification

A successful `save_memory` writes to 6 tables in one atomic DAG pass:

| Table | What's stored |
|-------|--------------|
| `packet_store` | Canonical event (PacketEnvelope JSONB) |
| `semantic_memory` | Vector embedding (1536-dim, pgvector) |
| `knowledge_facts` | Extracted facts (if applicable) |
| `reasoning_traces` | Reasoning audit trail |
| `agent_memory_events` | Agent event log entry |
| `graph_checkpoints` | Graph state snapshot |

**Verify with:**
```bash
# Check packet exists
SELECT packet_id, scope, packet_type FROM packet_store WHERE scope = 'cursor' ORDER BY timestamp DESC LIMIT 3;

# Check embedding exists
SELECT embedding_id, scope FROM semantic_memory WHERE scope = 'cursor' ORDER BY created_at DESC LIMIT 3;
```

---

## Rate Limiting

| Limit | Value |
|-------|-------|
| Requests per minute per IP | 60 |
| Failed auth attempts before block | 5 |
| Block duration after failed auth | 5 minutes |

Rate limiting is in-memory per IP. If blocked, wait for the window to expire.

---

## Troubleshooting

### 403: Scope not authorized

**Cause:** Requesting a scope not in caller's `allowed_scopes`.

**Fix:** Use only your allowed scopes. Cursor uses `cursor`, `developer`, `global`. Agents use `agent`, `developer`, `global`.

### 403: project_id must be derived from governance context

**Cause:** `project_id` mismatch between governance context and search handler.

**Fix:** Don't pass `project_id` in arguments — it's derived from `L9_PROJECT_ID` env var on the server (defaults to `l9-default`).

### 500: Internal Server Error

**Check logs:**
```bash
ssh c1 'docker logs --tail 50 l9-l9-mcp-memory-1 2>&1 | grep -i error'
```

### Empty search results

**Possible causes:**
1. Embedding not yet generated (wait 1-2 seconds after write)
2. Threshold too high (try `threshold: 0.0`)
3. Scope mismatch (search scopes must include the scope the memory was written to)
4. RLS blocking (check `app.role` matches the scope's access policy)

### Connection refused on port 9002

**Fix:**
```bash
ssh c1 'docker ps --filter name=mcp-memory'
# If not running:
ssh c1 'cd /opt/l9 && docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d l9-mcp-memory'
```

---

## Change Log

- **2026-02-13:** Rewrote for direct port 9002 access (no nginx/Caddy proxy). Added cursor scope, RLS documentation, agent onboarding guide. Updated to C1 (46.62.243.82).
- **2026-02-13:** Added migration 0033 — cursor scope in packet_store CHECK + RLS policies for semantic_memory and knowledge_facts.
- **2026-01-12:** Original version — locked official URL, verified main pipeline, documented rate limiting.
