# Memory Instantiation Plan (GMP-28)

**Goal:** Fully working memory for L and Cursor  
**Definition of Done:** Memory upload, read, write executed and confirmed with empirical proof (hash/ID)

---

## Current State

| Component | Status | Location |
|-----------|--------|----------|
| MCP Server code | ✅ EXISTS | `mcp_memory/src/` |
| Schema (memory.*) | ✅ EXISTS (deprecated) | `mcp_memory/schema/` |
| L9 substrate (packet_store) | ✅ EXISTS | `migrations/` |
| Governance metadata migration | ✅ EXISTS | `mcp_memory/schema/migrations/003_governance_metadata.sql` |
| Scope enforcement | ✅ CODE EXISTS | `mcp_memory/src/routes/memory.py` |
| VPS deployment | ⏳ PARTIAL | Port 9001 needs Caddy routing |

---

## Instantiation Steps

### Phase 1: Schema Update (VPS)

```bash
# 1. SSH to VPS
ssh root@157.180.73.53

# 2. Add project_id column to packet_store
docker exec -it l9-postgres psql -U postgres -d l9memory <<'SQL'
-- Add project_id column
ALTER TABLE public.packet_store ADD COLUMN IF NOT EXISTS project_id TEXT DEFAULT 'l9';

-- Update scope constraint to allow new values
-- (Check existing constraint first)
\d+ packet_store

-- Add composite index for fast queries
CREATE INDEX IF NOT EXISTS idx_packet_store_project_scope 
  ON public.packet_store(project_id, scope);

-- Verify
SELECT column_name, data_type FROM information_schema.columns 
WHERE table_name = 'packet_store' ORDER BY ordinal_position;
SQL
```

### Phase 2: Update MCP Handlers (Code)

Files to modify:
- `mcp_memory/src/routes/memory.py` → Write to `packet_store` not `memory.*`
- `mcp_memory/src/mcp_server.py` → Update tool handlers

Key change: Replace `memory.long_term` with `public.packet_store`:

```python
# BEFORE (deprecated)
INSERT INTO memory.long_term (user_id, content, ...) VALUES (...)

# AFTER (unified)
INSERT INTO public.packet_store (project_id, scope, envelope, metadata, ...) VALUES (...)
```

### Phase 3: VPS Deployment

```bash
# 1. Pull latest code
cd /opt/l9 && git pull

# 2. Update .env with dual API keys
# MCP_API_KEY_L=<L's key>
# MCP_API_KEY_C=<Cursor's key>

# 3. Restart MCP service
sudo systemctl restart l9-mcp

# 4. Verify port 9001 is up
curl http://127.0.0.1:9001/health
```

### Phase 4: Caddy Routing (if not using SSH tunnel)

Add to Caddy config:
```
mcp.l9.ai {
    reverse_proxy 127.0.0.1:9001
}
```

Or use Cloudflare tunnel instead.

### Phase 5: Test Write (Cursor)

```bash
# From Mac - test write
curl -X POST http://157.180.73.53:9001/mcp/call \
  -H "Authorization: Bearer $MCP_API_KEY_C" \
  -H "Content-Type: application/json" \
  -d '{
    "tool_name": "save_memory",
    "arguments": {
      "content": "Test memory from Cursor - instantiation proof",
      "kind": "test",
      "scope": "developer"
    },
    "user_id": "cursor"
  }'
```

**Expected:** Returns `{"status": "success", "result": {"memory_id": 123, ...}}`

### Phase 6: Test Read (L)

Have L query the same memory:

```sql
-- L queries packet_store
SELECT packet_id, envelope->>'content' as content, scope, created_at
FROM packet_store
WHERE scope = 'developer'
ORDER BY created_at DESC
LIMIT 5;
```

**Expected:** L sees "Test memory from Cursor - instantiation proof"

### Phase 7: Empirical Proof

1. **Memory ID** returned from write (e.g., `packet_id: 42`)
2. **Cross-reference:** Ask L "What's in packet_id 42?"
3. **Verification:** L confirms content matches

---

## Checklist

- [ ] Schema: project_id column added to packet_store
- [ ] Code: MCP handlers write to packet_store (not memory.*)
- [ ] VPS: .env has MCP_API_KEY_L and MCP_API_KEY_C
- [ ] VPS: l9-mcp service running on port 9001
- [ ] Network: Cursor can reach port 9001 (Caddy or tunnel)
- [ ] Test: Write from Cursor returns memory_id
- [ ] Test: Read from L confirms content
- [ ] Proof: L reports same content Cursor wrote

---

## Quick Commands

```bash
# Check if MCP service is running
ssh root@157.180.73.53 "systemctl status l9-mcp"

# Check port 9001
ssh root@157.180.73.53 "curl -s http://127.0.0.1:9001/health"

# Check packet_store schema
ssh root@157.180.73.53 "docker exec l9-postgres psql -U postgres -d l9memory -c '\d packet_store'"

# Count developer memories
ssh root@157.180.73.53 "docker exec l9-postgres psql -U postgres -d l9memory -c \"SELECT COUNT(*) FROM packet_store WHERE scope='developer'\""
```

---

## Definition of Done

✅ **COMPLETE when:**
1. Cursor writes memory → gets `packet_id` back
2. L queries `SELECT * FROM packet_store WHERE packet_id = X` → sees same content
3. Igor can verify both see the same data (empirical proof)





