# Cursor memory client memory type
_Exported on 1/14/2026 at 17:35:42 GMT-4 from Cursor (2.3.35)_

---

**User**

cursor_memory_client.py
uses mcp or http memory?

---

**Cursor**

**`cursor_memory_client.py` uses MCP as PRIMARY, HTTP as FALLBACK.**

| Operation | Method | Endpoint/Tool |
|-----------|--------|---------------|
| **Memory operations** (search, write, stats) | **MCP (PRIMARY)** | `/mcp/call` → `save_memory`, `search_memory`, `get_memory_stats` |
| **Graph operations** (Neo4j) | HTTP (FALLBACK) | `/api/v1/memory/graph/*` |
| **Cache operations** (Redis) | HTTP (FALLBACK) | `/api/v1/memory/cache/*` |

**Key architecture from the docstring:**

```3:9:agents/cursor/cursor_memory_client.py
## ARCHITECTURE

    PRIMARY METHOD:  MCP Tools via /mcp/call endpoint
    FALLBACK METHOD: Direct HTTP API (deprecated, for graph/cache only)
```

The `mcp_call_tool()` function (line 134) is the primary method — it POSTs to `/mcp/call` with a tool name and arguments. All memory operations (`cmd_search`, `cmd_write`, `cmd_stats`, etc.) use this.

Direct HTTP via `api_request()` (line 177) is only used for:
- Graph operations (Neo4j) — no MCP tools available
- Cache operations (Redis) — no MCP tools available

---

**User**

why:
Graph operations (Neo4j) — no MCP tools available
Cache operations (Redis) — no MCP tools available
can enable mcp tool calls to them?

---

**Cursor**

Good question. Let me check what MCP tools are currently defined and how they're implemented.

Now let me check where Neo4j/Redis operations are defined to understand what would need to be wired:

Now I understand the full picture.

## Why No MCP Tools for Graph/Cache

**Simple answer:** They weren't added yet. The MCP server was built for memory operations (PostgreSQL + pgvector), and Graph/Cache were added separately as REST APIs.

| System | Current Implementation |
|--------|----------------------|
| **Memory** (PostgreSQL + pgvector) | MCP tools in `mcp_memory/src/mcp_server.py` |
| **Graph** (Neo4j) | REST API in `api/memory/graph.py` |
| **Cache** (Redis) | REST API in `api/memory/cache.py` |

## Can We Enable MCP Tools for Them?

**Yes, absolutely.** This is a straightforward enhancement. Would add to `mcp_server.py`:

### Proposed Graph Tools (Neo4j)

| Tool | Purpose |
|------|---------|
| `graph_query` | Run Cypher query |
| `graph_get_entity` | Get entity by type/id |
| `graph_get_context` | Get domain context (already in REST API) |
| `graph_get_relationships` | Get entity relationships |

### Proposed Cache Tools (Redis)

| Tool | Purpose |
|------|---------|
| `cache_get` | Get value by key |
| `cache_set` | Set value with optional TTL |
| `cache_get_session` | Get session context |
| `cache_set_session` | Set session context |

## Implementation Path

1. **Add MCPTool definitions** to `mcp_memory/src/mcp_server.py`:
   - Define input schemas for each tool
   
2. **Add handlers** in `handle_tool_call()`:
   - Import graph/cache clients
   - Route tool calls to existing functions

3. **Update models.py** with Pydantic args classes

---

**Want me to implement this?** It would be a GMP — touching `KERNEL_TIER` (mcp_server is part of memory substrate).

---

**User**

do it /gmp style

---

**Cursor**

I'll execute this as a GMP. Let me start with the proper protocol.

## 🔒 GMP SCOPE LOCK (v1.1)

**GMP ID:** GMP-77: MCP-Tools-Graph-Cache
**Source:** User prompt
**Tier:** RUNTIME_TIER (mcp_memory is memory substrate, not KERNEL)

### 📋 VARIABLE BINDINGS
| Variable | Value |
|----------|-------|
| TASK_NAME | `mcp_tools_graph_cache` |
| EXECUTION_SCOPE | Add MCP tools for Neo4j graph and Redis cache operations |
| RISK_LEVEL | Medium |
| IMPACT_METRICS | API consistency, client simplicity, memory operations coverage |
| VALIDATION_NOTES | Test via cursor_memory_client.py health check |

### 📍 STATE_SYNC (from workflow_state.md)
- Phase: 6 (FINALIZE)
- Context: Memory debugging in local Docker, MCP `/mcp/call` working
- Priority: 🟡 Enhancement (not blocking)

### 🔒 CONSTRAINT CHECK
- [x] KERNEL-TIER files NOT in scope (mcp_memory is RUNTIME)
- [x] No duplicated responsibilities (adding new tools, not overlapping)
- [x] Unified interfaces will be used (MCPTool pattern)
- [x] No placeholders in output

### 📁 FILE BUDGET
**MAY modify:**
- `mcp_memory/src/mcp_server.py` — Add MCPTool definitions + handlers
- `mcp_memory/src/models.py` — Add Pydantic validation Args classes
- `agents/cursor/cursor_memory_client.py` — Update to use MCP tools

**MAY NOT modify:**
- `core/kernels/kernel_loader.py`
- `core/agents/executor.py`
- `memory/substrate_service.py`
- `runtime/websocket_orchestrator.py`
- `docker-compose.yml`

### ✅ VALIDATION GATES
- [x] py_compile
- [x] lint (ruff) — if available
- [ ] tests — existing tests should pass

---

## TODO PLAN (LOCKED)

### Phase 1: Pydantic Validation Models

- **[T1]** File: `/Users/ib-mac/Projects/L9/mcp_memory/src/models.py`
  - Lines: END (append)
  - Action: Insert
  - Target: `Graph/Cache MCP Args classes`
  - Change: Add 6 Pydantic validation models for graph/cache tool arguments
  - Gate: py_compile
  - Imports: NONE (already has required imports)

### Phase 2: MCP Tool Definitions

- **[T2]** File: `/Users/ib-mac/Projects/L9/mcp_memory/src/mcp_server.py`
  - Lines: 297 (after existing MCPTool list, before `]`)
  - Action: Insert
  - Target: `get_mcp_tools()` return list
  - Change: Add 6 MCPTool definitions for graph/cache operations
  - Gate: py_compile
  - Imports: NONE

### Phase 3: Tool Handlers

- **[T3]** File: `/Users/ib-mac/Projects/L9/mcp_memory/src/mcp_server.py`
  - Lines: 539-540 (after existing tool handlers, before `else: raise ValueError`)
  - Action: Insert
  - Target: `handle_tool_call()` function
  - Change: Add handlers for 6 new graph/cache tools
  - Gate: py_compile
  - Imports: Add `GraphQueryArgs, GraphGetEntityArgs, GraphGetContextArgs, CacheGetArgs, CacheSetArgs, CacheSessionContextArgs` to imports from models

### Phase 4: Update Client (Optional)

- **[T4]** File: `/Users/ib-mac/Projects/L9/agents/cursor/cursor_memory_client.py`
  - Lines: 1139-1200 (graph commands section)
  - Action: Replace
  - Target: `cmd_graph_*` functions
  - Change: Update to use MCP tools instead of direct HTTP API
  - Gate: py_compile
  - Imports: NONE

---

⏸️ **AWAITING:** "CONFIRM SCOPE" to proceed with execution

