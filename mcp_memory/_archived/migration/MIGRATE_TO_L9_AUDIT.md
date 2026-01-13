# Migrate MCP Audit to L9 Substrate - Eliminate mcp_memory/schema

**Date:** 2026-01-09
**Goal:** Use ONLY L9 migrations, eliminate `mcp_memory/schema` entirely

---

## Current Problem

**MCP migrations 003/004 try to modify `memory.audit_log`:**
- `003_governance_metadata.sql` - Adds `caller` column to `memory.audit_log`
- `004_audit_project_id.sql` - Adds `project_id` column to `memory.audit_log`

**But `memory.audit_log` doesn't exist in L9 substrate!**

The MCP schema creates it in `mcp_memory/schema/init.sql`, but we're NOT using that schema.

---

## L9 Audit Infrastructure (Available)

### Option 1: `packet_store` (Recommended)

**Already exists in L9 migrations:**
- `packet_store` is the central event log
- Has `scope`, `metadata` (JSONB), `timestamp`, `user_id`, `tenant_id`, `org_id`
- Can store audit info in `metadata` JSONB or add columns

**Advantages:**
- ✅ Already exists
- ✅ Central event log (perfect for audit)
- ✅ Has multi-tenant fields
- ✅ Has `scope` column (for governance)
- ✅ Has `metadata` JSONB (can store caller, project_id, operation)

**Migration:**
```sql
-- Add audit-specific columns to packet_store (if needed)
ALTER TABLE packet_store 
ADD COLUMN IF NOT EXISTS caller TEXT,
ADD COLUMN IF NOT EXISTS project_id TEXT;

-- Or use metadata JSONB (no migration needed)
-- metadata->>'caller' = 'L' or 'C'
-- metadata->>'project_id' = 'l9' or NULL
```

### Option 2: `tool_audit_log` (For Tool Operations)

**Exists in L9 migrations (0011):**
- `tool_audit_log` - Tracks tool executions
- Has: `tool_name`, `agent_id`, `input_data`, `output_data`, `duration_ms`, `tokens_used`, `cost_usd`, `error`, `timestamp`, `request_id`

**Use for:** MCP tool call audit (save_memory, search_memory, etc.)

**Migration:**
```sql
-- Add caller and project_id to tool_audit_log
ALTER TABLE tool_audit_log 
ADD COLUMN IF NOT EXISTS caller TEXT,
ADD COLUMN IF NOT EXISTS project_id TEXT;
```

### Option 3: Create New `mcp_audit_log` in Public Schema

**Create dedicated audit table in L9 substrate:**
```sql
-- New migration: migrations/0013_mcp_audit_log.sql
CREATE TABLE IF NOT EXISTS mcp_audit_log (
    id BIGSERIAL PRIMARY KEY,
    operation TEXT NOT NULL,
    caller TEXT NOT NULL,  -- 'L' or 'C'
    project_id TEXT,  -- 'l9' or NULL
    scope TEXT,  -- 'developer', 'l-private', 'global'
    user_id TEXT,
    packet_id UUID REFERENCES packet_store(packet_id),
    status TEXT NOT NULL DEFAULT 'success',
    details JSONB,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_mcp_audit_caller ON mcp_audit_log(caller, created_at DESC);
CREATE INDEX idx_mcp_audit_project ON mcp_audit_log(project_id, created_at DESC);
CREATE INDEX idx_mcp_audit_scope ON mcp_audit_log(scope, created_at DESC);
```

---

## Recommended Solution: Use `packet_store` + `tool_audit_log`

### For Memory Operations (save, search)

**Use `packet_store` as audit log:**
- Every `save_memory` creates a packet in `packet_store`
- Every `search_memory` can create an audit packet
- Store audit metadata in `packet_store.metadata` JSONB:
  ```json
  {
    "caller": "C",
    "project_id": "l9",
    "operation": "SAVE_MEMORY",
    "scope": "developer",
    "kind": "preference"
  }
  ```

**No migration needed** - `packet_store` already has:
- `metadata` JSONB (store caller, project_id, operation)
- `scope` column (for governance)
- `user_id`, `tenant_id`, `org_id` (multi-tenant)
- `timestamp` (audit timestamp)

### For Tool Operations (MCP tool calls)

**Use `tool_audit_log` for MCP tool execution audit:**
- Track tool_name = 'save_memory', 'search_memory', etc.
- Add `caller` and `project_id` columns

**Migration needed:**
```sql
-- migrations/0013_add_mcp_audit_to_tool_audit.sql
ALTER TABLE tool_audit_log 
ADD COLUMN IF NOT EXISTS caller TEXT,
ADD COLUMN IF NOT EXISTS project_id TEXT;

CREATE INDEX idx_tool_audit_caller ON tool_audit_log(caller, timestamp DESC);
CREATE INDEX idx_tool_audit_project ON tool_audit_log(project_id, timestamp DESC);
```

---

## Updated Unified Handlers

### Current (Wrong - tries to use memory.audit_log):
```python
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
    json.dumps({...}),
)
```

### Fixed (Use packet_store):
```python
# For save_memory - packet is already created in packet_store
# Just ensure metadata has audit fields:
envelope["metadata"]["caller"] = caller_id
envelope["metadata"]["project_id"] = project_id
envelope["metadata"]["operation"] = "SAVE_MEMORY"
envelope["metadata"]["scope"] = scope

# For search_memory - create audit packet:
audit_packet = {
    "packet_type": "mcp_audit_search",
    "payload": {
        "operation": "SEARCH_MEMORY",
        "query": query,
        "scopes": scopes,
        "top_k": top_k,
    },
    "metadata": {
        "caller": caller_id,
        "project_id": project_id,
        "scope": ",".join(scopes or []),
        "operation": "SEARCH_MEMORY",
    },
    "scope": "shared",  # Audit packets are shared
}
# Insert into packet_store
```

### OR Use tool_audit_log:
```python
# For MCP tool operations
await execute(
    """
    INSERT INTO tool_audit_log (tool_name, agent_id, caller, project_id, input_data, output_data, duration_ms, timestamp)
    VALUES ($1, $2, $3, $4, $5, $6, $7, NOW())
    """,
    "save_memory",  # tool_name
    user_id,  # agent_id
    caller_id,  # caller
    project_id,  # project_id
    json.dumps({"content": content, "kind": kind, "scope": scope}),  # input_data
    json.dumps({"packet_id": str(packet_id), "status": "success"}),  # output_data
    embed_time_ms,  # duration_ms
)
```

---

## Migration Plan

### Step 1: Create L9 Migration for MCP Audit

**File:** `migrations/0013_mcp_audit_columns.sql`

```sql
-- Add caller and project_id to tool_audit_log for MCP tool audit
ALTER TABLE tool_audit_log 
ADD COLUMN IF NOT EXISTS caller TEXT,
ADD COLUMN IF NOT EXISTS project_id TEXT;

CREATE INDEX IF NOT EXISTS idx_tool_audit_caller 
ON tool_audit_log(caller, timestamp DESC);

CREATE INDEX IF NOT EXISTS idx_tool_audit_project 
ON tool_audit_log(project_id, timestamp DESC)
WHERE project_id IS NOT NULL;

COMMENT ON COLUMN tool_audit_log.caller IS 
    'Caller identity: "L" (L-CTO kernel) or "C" (Cursor IDE). Determined from API key.';

COMMENT ON COLUMN tool_audit_log.project_id IS 
    'Project identifier: "l9" for L9 repo, NULL for global scope. Enables multi-project isolation.';
```

### Step 2: Update Unified Handlers

**Remove:** All `INSERT INTO memory.audit_log` statements

**Replace with:**
- For `save_memory`: Ensure `packet_store.metadata` has caller/project_id
- For `search_memory`: Create audit packet in `packet_store` OR log to `tool_audit_log`
- For all MCP tool calls: Log to `tool_audit_log` with caller/project_id

### Step 3: Delete MCP Schema

**Delete:**
- `mcp_memory/schema/init.sql` (deprecated tables)
- `mcp_memory/schema/migrations/001_hnsw_upgrade.sql` (for deprecated tables)
- `mcp_memory/schema/migrations/002_10x_memory_upgrade.sql` (for deprecated tables)
- `mcp_memory/schema/migrations/003_governance_metadata.sql` (uses memory.audit_log)
- `mcp_memory/schema/migrations/004_audit_project_id.sql` (uses memory.audit_log)

**Keep:** Nothing - all functionality in L9 migrations

---

## Final Architecture

### MCP Server Uses ONLY L9 Migrations:

1. **Memory Storage:**
   - `packet_store` - Central event log
   - `memory_embeddings` - Vector embeddings

2. **Audit Logging:**
   - `packet_store` - For memory operations (save, search)
   - `tool_audit_log` - For MCP tool execution audit

3. **No MCP Schema:**
   - ❌ No `memory.*` tables
   - ❌ No `mcp_memory/schema/init.sql`
   - ❌ No MCP-specific migrations

---

## Benefits

1. ✅ **Single source of truth** - All in L9 migrations
2. ✅ **No schema conflicts** - No deprecated tables
3. ✅ **Unified audit** - All audit in L9 substrate
4. ✅ **Simpler deployment** - Only L9 migrations needed
5. ✅ **Better governance** - Audit in central packet_store

---

## Action Items

1. ✅ Create `migrations/0013_mcp_audit_columns.sql` (add caller/project_id to tool_audit_log)
2. ⚠️ Update `memory_unified.py` to use `packet_store` + `tool_audit_log` instead of `memory.audit_log`
3. ⚠️ Delete `mcp_memory/schema/` directory (all deprecated)
4. ⚠️ Update deployment scripts to use L9 migrations only
5. ⚠️ Test audit logging works with L9 substrate

---

**Result:** MCP server uses 100% L9 substrate, zero MCP schema dependencies.

