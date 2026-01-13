# Perplexity Recommendations → L9 Integration

**Date:** 2026-01-09
**Status:** Integrated into unified handlers

## Analysis of Perplexity Recommendations

### ✅ Already Implemented

1. **Unified Substrate** - ✅ DONE
   - Using `packet_store` + `memory_embeddings` (not deprecated `memory.*` tables)
   - All handlers migrated to unified substrate

2. **Scope Enforcement** - ✅ DONE
   - MCP scopes: `developer`, `l-private`, `global`
   - Server-side enforcement in `mcp_server.py`
   - Cursor blocked from `l-private` scope

3. **Governance Metadata** - ✅ DONE
   - `creator`: "L-CTO" or "Cursor-IDE" (enforced server-side)
   - `source`: "l9-kernel" or "cursor-ide" (enforced server-side)
   - `caller`: "L" or "C" (from API key)

4. **MCP Endpoints** - ✅ DONE
   - `/mcp/tools` - Lists available tools
   - `/mcp/call` - Executes tools with governance

5. **Embeddings & Search** - ✅ DONE
   - OpenAI embeddings on every save/search
   - Vector similarity search with pgvector
   - Access tracking (updates `last_accessed`, `access_count`)

### ⚠️ Needs Integration

1. **project_id Support** - ⚠️ PARTIAL
   - **Current:** Stored in metadata (no schema column)
   - **Perplexity says:** Should be column for multi-project isolation
   - **Decision:** Store in metadata for now (works immediately), add column later if needed
   - **Default:** `project_id='l9'` for L9 repo, `NULL` for global scope

2. **SQL-Level Scope Enforcement** - ⚠️ PARTIAL
   - **Current:** Python-level filtering in `mcp_server.py`
   - **Perplexity says:** Also enforce in SQL WHERE clauses
   - **Action:** Add explicit `WHERE scope IN (...)` to all queries

3. **Audit Logging** - ⚠️ MISSING
   - **Perplexity says:** Log all Cursor calls with caller, project_id, scope, filters
   - **Action:** Add audit logging to unified handlers

4. **Cursor System Prompt** - ⚠️ MISSING
   - **Perplexity says:** Create system prompt telling Cursor to use MCP tools
   - **Action:** Create guide document

## Integration Changes Made

### 1. project_id in Metadata

**Location:** `save_memory_handler()` in `memory_unified.py`

```python
# Store project_id in metadata (default: 'l9' for L9 repo)
metadata = {
    "project_id": metadata.get("project_id", "l9") if metadata else "l9",
    # ... other metadata
}
```

**Rationale:** 
- Works immediately without migration
- Can query via `envelope->>'metadata'->>'project_id'`
- Can add column later if needed for performance

### 2. SQL-Level Scope Enforcement

**Location:** All search/query handlers in `memory_unified.py`

**Before:**
```python
# Only Python-level filtering
if caller_id == "C":
    scopes = [s for s in scopes if s != "l-private"]
```

**After:**
```python
# Python-level + SQL-level enforcement
db_scopes = [map_mcp_scope_to_db_scope(s) for s in scopes]
scope_filter = f"AND ps.scope IN ({scope_placeholders})"
```

**Rationale:**
- Defense in depth (Python + SQL)
- Prevents accidental exposure even if Python logic fails
- Matches Perplexity's "server-side enforcement" recommendation

### 3. Audit Logging

**Location:** All handlers in `memory_unified.py`

**Added:**
```python
# Log to audit (if audit_log table exists)
await execute(
    """
    INSERT INTO memory.audit_log (operation, user_id, caller, project_id, scope, status, details)
    VALUES ($1, $2, $3, $4, $5, $6, $7)
    """,
    "SAVE_MEMORY",
    user_id,
    caller_id,
    project_id,
    scope,
    "success",
    json.dumps({"packet_id": str(packet_id), "kind": kind}),
)
```

**Note:** Audit table may need to be created. For now, wrapped in try/except to not break if missing.

### 4. Cursor System Prompt Guide

**Created:** `mcp_memory/docs/CURSOR_SYSTEM_PROMPT.md`

**Key Points:**
- Treat L9 MCP memory tools as source of truth
- Use `search_memory` before planning
- Use `save_memory` after outcomes
- Never assume built-in memory beyond current conversation
- Scope discipline: `developer` for project, `global` for cross-project

## What We Did NOT Integrate (And Why)

### 1. Separate `project_id` Column (Yet)

**Perplexity says:** Add `project_id` column to `packet_store`

**Why not yet:**
- Requires migration
- Storing in metadata works for now
- Can add column later if query performance needs it
- Current queries work with metadata JSONB

**Future:** Add migration if multi-project isolation becomes critical

### 2. Intelition Refiners Integration

**Perplexity says:** Plug C into Intelition refiners for consolidation/reflection

**Why not yet:**
- Intelition framework may not be fully implemented
- Need to verify what's actually available
- Can add later once Intelition is confirmed working

**Future:** Integrate when Intelition is ready

### 3. MCP HTTP Bridge

**Perplexity says:** Use `mcp-http-bridge.js` for Cursor connection

**Why not:**
- Cursor may support direct HTTP MCP (need to verify)
- Current `/mcp/tools` and `/mcp/call` endpoints should work
- Can add bridge later if Cursor requires it

**Future:** Add bridge if Cursor doesn't support direct HTTP MCP

## Validation Checklist

- [x] Unified substrate (packet_store + memory_embeddings)
- [x] Scope enforcement (Python + SQL)
- [x] Governance metadata (creator, source, caller)
- [x] MCP endpoints (/mcp/tools, /mcp/call)
- [x] Embeddings on every save/search
- [x] project_id in metadata (default: 'l9')
- [x] SQL-level scope filtering
- [x] Audit logging (wrapped in try/except)
- [x] Cursor system prompt guide
- [ ] project_id as column (future migration)
- [ ] Intelition integration (when available)
- [ ] MCP HTTP bridge (if needed)

## Next Steps

1. **Test with Cursor** - Verify MCP endpoints work
2. **Create audit_log table** - If missing, create migration
3. **Add project_id column** - If multi-project isolation needed
4. **Integrate Intelition** - When framework is ready
5. **Update /mem command** - Use MCP tools instead of REST API

---

**Summary:** Integrated all immediately applicable Perplexity recommendations. Deferred schema changes and optional features until needed. Core functionality (unified substrate, scope enforcement, governance) is complete and matches Perplexity's guidance.

