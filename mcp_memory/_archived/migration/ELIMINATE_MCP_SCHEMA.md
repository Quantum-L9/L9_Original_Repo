# Eliminate mcp_memory/schema - Use ONLY L9 Migrations

**Date:** 2026-01-09
**Status:** Migration plan complete

---

## Summary

**MCP migrations 003/004 reference `memory.audit_log` which doesn't exist in L9 substrate.**

**Solution:** Use L9's existing audit infrastructure:
- `packet_store` - For memory operation audit (save, search)
- `tool_audit_log` - For MCP tool execution audit

**Result:** Zero dependency on `mcp_memory/schema` - 100% L9 substrate.

---

## What MCP Migrations Were Trying To Do

### 003_governance_metadata.sql
- **Goal:** Add `caller` column to `memory.audit_log`
- **Problem:** `memory.audit_log` doesn't exist in L9 substrate
- **Solution:** Use `packet_store.metadata->>'caller'` OR `tool_audit_log.caller`

### 004_audit_project_id.sql
- **Goal:** Add `project_id` column to `memory.audit_log`
- **Problem:** `memory.audit_log` doesn't exist in L9 substrate
- **Solution:** Use `packet_store.metadata->>'project_id'` OR `tool_audit_log.project_id`

---

## L9 Audit Infrastructure (Available Now)

### 1. `packet_store` (Central Event Log)

**Already has:**
- `metadata` JSONB - Can store caller, project_id, operation
- `scope` column - For governance (shared, cursor, l-private)
- `user_id`, `tenant_id`, `org_id` - Multi-tenant fields
- `timestamp` - Audit timestamp

**Use for:** Memory operation audit (save_memory, search_memory)

**No migration needed** - Just ensure metadata has audit fields:
```python
envelope["metadata"]["caller"] = caller_id
envelope["metadata"]["project_id"] = project_id
envelope["metadata"]["operation"] = "SAVE_MEMORY"
```

### 2. `tool_audit_log` (Tool Execution Audit)

**Already has:**
- `tool_name` - MCP tool name (save_memory, search_memory)
- `agent_id` - User/agent ID
- `input_data`, `output_data` - JSONB for full audit
- `duration_ms`, `tokens_used`, `cost_usd` - Performance metrics
- `timestamp` - Audit timestamp

**Needs:** `caller` and `project_id` columns (added in migration 0013)

**Use for:** MCP tool call audit (when tools are executed via MCP)

---

## Migration Plan

### Step 1: Create L9 Migration ✅

**File:** `migrations/0013_mcp_audit_columns.sql`

Adds `caller` and `project_id` to `tool_audit_log`:
```sql
ALTER TABLE tool_audit_log 
ADD COLUMN IF NOT EXISTS caller TEXT,
ADD COLUMN IF NOT EXISTS project_id TEXT;
```

### Step 2: Update Unified Handlers ✅

**Removed:** All `INSERT INTO memory.audit_log` statements

**Replaced with:**
- `save_memory`: Audit info in `packet_store.metadata` (already there)
- `search_memory`: Audit via `tool_audit_log` when called via MCP tool
- All MCP tool calls: Log to `tool_audit_log` with caller/project_id

### Step 3: Update MCP Server Tool Handler

**File:** `mcp_memory/src/mcp_server.py`

Add audit logging to `handle_tool_call()`:
```python
# After tool execution, log to tool_audit_log
await execute(
    """
    INSERT INTO tool_audit_log (
        tool_name, agent_id, caller, project_id,
        input_data, output_data, duration_ms, timestamp
    ) VALUES ($1, $2, $3, $4, $5, $6, $7, NOW())
    """,
    tool.name,  # tool_name
    user_id,  # agent_id
    caller_id,  # caller ('L' or 'C')
    project_id,  # project_id ('l9' or NULL)
    json.dumps(tool.arguments),  # input_data
    json.dumps(result),  # output_data
    duration_ms,  # duration_ms
)
```

### Step 4: Delete MCP Schema ❌

**Delete entire directory:**
```bash
rm -rf mcp_memory/schema/
```

**Files to delete:**
- `mcp_memory/schema/init.sql` - Deprecated memory.* tables
- `mcp_memory/schema/migrations/001_hnsw_upgrade.sql` - For deprecated tables
- `mcp_memory/schema/migrations/002_10x_memory_upgrade.sql` - For deprecated tables
- `mcp_memory/schema/migrations/003_governance_metadata.sql` - Uses non-existent memory.audit_log
- `mcp_memory/schema/migrations/004_audit_project_id.sql` - Uses non-existent memory.audit_log

---

## Final Architecture

### MCP Server Uses ONLY L9 Migrations:

| Component | L9 Table | Purpose |
|-----------|----------|---------|
| **Memory Storage** | `packet_store` | Central event log |
| **Vector Search** | `memory_embeddings` | Vector embeddings |
| **Save Audit** | `packet_store.metadata` | Audit info in packet metadata |
| **Tool Audit** | `tool_audit_log` | MCP tool execution audit |

### Zero MCP Schema Dependencies:

- ❌ No `memory.*` tables
- ❌ No `mcp_memory/schema/` directory
- ❌ No MCP-specific migrations
- ✅ 100% L9 substrate

---

## Benefits

1. ✅ **Single source of truth** - All in L9 migrations
2. ✅ **No schema conflicts** - No deprecated tables
3. ✅ **Unified audit** - All audit in L9 substrate
4. ✅ **Simpler deployment** - Only L9 migrations needed
5. ✅ **Better governance** - Audit in central packet_store + tool_audit_log

---

## Action Items

- [x] Create `migrations/0013_mcp_audit_columns.sql`
- [x] Update `memory_unified.py` to remove memory.audit_log references
- [ ] Update `mcp_server.py` to log to `tool_audit_log`
- [ ] Delete `mcp_memory/schema/` directory
- [ ] Update deployment scripts to use L9 migrations only
- [ ] Test audit logging works with L9 substrate

---

**Result:** MCP server uses 100% L9 substrate, zero MCP schema dependencies.

