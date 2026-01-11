# L9 Unified Memory Architecture

**Version:** 2.0 (Multi-Project)  
**Updated:** 2026-01-02  
**Status:** LOCKED

---

## Overview

L (L-CTO) and Cursor share a **unified memory substrate** with scope-based access:

- **`scope = 'developer'`** → Cursor + L (code collaboration)
- **`scope = 'l-private'`** → L only (internal operations)

**Cursor has global access** = can read/write `scope='developer'` across ALL projects.

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         UNIFIED MEMORY SUBSTRATE                             │
│                        (L9 packet_store + memory_embeddings)                 │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│   PROJECT: l9              PROJECT: future-x         PROJECT: future-y      │
│   ┌─────────────────┐      ┌─────────────────┐       ┌─────────────────┐    │
│   │  developer ✅   │      │  developer ✅   │       │  developer ✅   │    │
│   │  ───────────    │      │  ───────────    │       │  ───────────    │    │
│   │  • Code prefs   │      │  • Code prefs   │       │  • Code prefs   │    │
│   │  • GMP learnings│      │  • Patterns     │       │  • Solutions    │    │
│   │  • Error fixes  │      │  • Decisions    │       │  • Context      │    │
│   │  • Arch decisions│     │                 │       │                 │    │
│   ├─────────────────┤      ├─────────────────┤       ├─────────────────┤    │
│   │  l-private ❌   │      │  l-private ❌   │       │  l-private ❌   │    │
│   │  ───────────    │      │  ───────────    │       │  ───────────    │    │
│   │  • Reasoning    │      │  • World model  │       │  • Approvals    │    │
│   │  • Slack msgs   │      │  • Agent ops    │       │  • Internal     │    │
│   └─────────────────┘      └─────────────────┘       └─────────────────┘    │
│                                                                              │
│                    ┌────────────────────────────────┐                        │
│                    │   CURSOR GLOBAL ACCESS         │                        │
│                    │   WHERE scope = 'developer'    │                        │
│                    │   (across ALL projects)        │                        │
│                    └────────────────────────────────┘                        │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Access Matrix

| Actor | `developer` | `l-private` |
|-------|-------------|-------------|
| **Cursor (C)** | ✅ READ/WRITE (global) | ❌ BLOCKED |
| **L-CTO** | ✅ READ/WRITE | ✅ READ/WRITE |

**Key invariant:** `WHERE scope = 'developer'` on ALL Cursor queries.

---

## Memory Flow

```
┌──────────────────┐                    ┌──────────────────┐
│     CURSOR       │                    │      L-CTO       │
│   (Cursor IDE)   │                    │    (L9 Agent)    │
└────────┬─────────┘                    └────────┬─────────┘
         │                                       │
         │ MCP API                               │ Direct PostgreSQL
         │ (HTTPS via Cloudflare)                │ (MemorySubstrateService)
         │                                       │
         ▼                                       ▼
┌─────────────────────────────────────────────────────────────────┐
│                    MCP MEMORY SERVER (port 9001)                 │
│                                                                  │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │  SCOPE ENFORCEMENT                                          │ │
│  │  ──────────────────                                         │ │
│  │  • Cursor API key → scope='developer' ONLY                 │ │
│  │  • L API key → all scopes                                   │ │
│  │  • Enforced server-side (never trust client)               │ │
│  └────────────────────────────────────────────────────────────┘ │
│                              │                                   │
└──────────────────────────────┼───────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                    POSTGRESQL (l9memory)                         │
│                                                                  │
│  ┌───────────────────────────┐  ┌──────────────────────────────┐│
│  │      packet_store          │  │     memory_embeddings        ││
│  │  ─────────────────────     │  │  ────────────────────────    ││
│  │  • project_id (l9, ...)    │  │  • vector (1536)             ││
│  │  • scope (developer/...)   │  │  • embedding_type            ││
│  │  • envelope (JSONB)        │  │  • packet_id (FK)            ││
│  │  • metadata                │  │  • chunk_text                ││
│  │  • timestamp               │  │                              ││
│  └───────────────────────────┘  └──────────────────────────────┘│
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Write Flow (Cursor → Memory)

```
1. Cursor calls MCP tool: save_memory(content="...", kind="preference")

2. MCP Server receives request:
   - Validates API key (MCP_API_KEY_C)
   - Determines caller = "C" (Cursor)
   - Enforces scope = "developer" (server-side, not client)
   - Sets metadata.creator = "Cursor-IDE"
   - Sets metadata.source = "cursor-ide"

3. Insert into packet_store:
   INSERT INTO packet_store (
     project_id,      -- 'l9' (or current project)
     scope,           -- 'developer' (enforced)
     envelope,        -- {content, kind, ...}
     metadata,        -- {creator: "Cursor-IDE", source: "cursor-ide"}
     ...
   )

4. Generate embedding:
   INSERT INTO memory_embeddings (
     packet_id,       -- FK to packet_store
     vector,          -- OpenAI embedding
     embedding_type   -- 'content'
   )

5. Audit log:
   INSERT INTO audit_log (
     operation,       -- 'INSERT'
     caller,          -- 'C'
     project_id,      -- 'l9'
     scope,           -- 'developer'
     ...
   )

6. Return success + memory_id
```

---

## Read Flow (Cursor → Search)

```
1. Cursor calls MCP tool: search_memory(query="error handling")

2. MCP Server receives request:
   - Validates API key (MCP_API_KEY_C)
   - Determines caller = "C" (Cursor)
   - Enforces WHERE scope = 'developer' (CRITICAL)

3. Search query (simplified):
   SELECT p.*, e.vector <=> $query_embedding AS similarity
   FROM packet_store p
   JOIN memory_embeddings e ON p.packet_id = e.packet_id
   WHERE p.scope = 'developer'  -- ENFORCED
     AND e.vector <=> $query_embedding < 0.3
   ORDER BY similarity
   LIMIT 5;

4. Return matching memories (only developer scope, across all projects)
```

---

## L's Private Write Flow

```
1. L writes reasoning trace (internal operation)

2. L-CTO sets scope = "l-private":
   await substrate.ingest_packet(PacketEnvelope(
     project_id='l9',
     scope='l-private',  -- NOT visible to Cursor
     envelope={...},
     metadata={creator: 'L-CTO', source: 'l9-kernel'}
   ))

3. Cursor queries cannot see this:
   WHERE scope = 'developer'  -- l-private excluded
```

---

## Collaboration Example

```
┌─────────────────────────────────────────────────────────────────┐
│ L writes with scope='developer' (intended for Cursor to see):   │
│                                                                  │
│   await substrate.ingest_packet(PacketEnvelope(                 │
│     project_id='l9',                                            │
│     scope='developer',  ← Cursor CAN read this                  │
│     envelope={'kind': 'preference', 'content': 'Igor prefers...'}│
│   ))                                                             │
│                                                                  │
├─────────────────────────────────────────────────────────────────┤
│ Cursor searches and FINDS this:                                  │
│                                                                  │
│   search_memory(query="Igor preferences")                       │
│   → Returns: "Igor prefers surgical edits..."                   │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Key Invariants

1. **Scope determines visibility**, not author
2. **Cursor = `developer` scope ONLY** (enforced server-side)
3. **L sees everything** (full substrate access)
4. **No separate memory.* tables** (unified substrate)
5. **project_id enables multi-project** (l9, future projects)
6. **Audit trail on every operation** (caller, scope, project)

---

## Implementation Status

| Component | Status | Notes |
|-----------|--------|-------|
| Schema changes (project_id, scope) | ⏳ PENDING | Need migration |
| MCP handlers → packet_store | ⏳ PENDING | Rewrite handlers |
| Scope enforcement in handlers | ⏳ PENDING | Add WHERE clause |
| Delete memory.* tables | ⏳ PENDING | After migration |
| VPS deployment | ⏳ PENDING | Caddy + restart |
| End-to-end test | ⏳ PENDING | Write + read + verify |

---

## Files

- **Spec:** `mcp_memory/memory-setup-instructions.md`
- **Architecture:** `mcp_memory/mcp-memory-architecture/ARCHITECTURE.md` (this file)
- **Old docs:** `mcp_memory/mcp-memory-architecture/_archived/` (deprecated)





