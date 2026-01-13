# E2E Integration Checklist - MCP Memory Server

**Date:** 2026-01-09
**Status:** Integration points identified, pending implementation

## ✅ Completed (Core Implementation)

- [x] Unified handlers (save, search, stats, cleanup, compound, decay, 10x tools)
- [x] Scope enforcement (Python + SQL-level)
- [x] Governance metadata (creator, source, caller)
- [x] project_id in metadata (default: 'l9')
- [x] Audit logging (wrapped in try/except)
- [x] Perplexity recommendations integrated

## ⚠️ Integration Points Requiring Updates

### 1. Cursor mcp.json Configuration

**File:** `/Users/ib-mac/.cursor/mcp.json`

**Current:** No `l9-memory` server configured

**Needs:**
```json
{
  "mcpServers": {
    "l9-memory": {
      "type": "sse",
      "url": "https://l9.quantumaipartners.com/mcp",
      "headers": {
        "Authorization": "Bearer ${MCP_API_KEY_C}"
      }
    }
  }
}
```

**OR** if Cursor requires HTTP bridge:
```json
{
  "mcpServers": {
    "l9-memory": {
      "command": "node",
      "args": ["path/to/mcp-http-bridge.js"],
      "env": {
        "MCPSERVERURL": "https://l9.quantumaipartners.com",
        "MCPAPIKEY": "${MCP_API_KEY_C}"
      }
    }
  }
}
```

**Action:** Add l9-memory server config to mcp.json

---

### 2. cursor_memory_client.py - MCP Tool Support

**File:** `.cursor-commands/cursor-memory/cursor_memory_client.py`

**Current:** Uses REST API at `/api/v1/memory/*` (bypasses MCP)

**Options:**
- **Option A:** Keep REST API for backward compatibility, add MCP option
- **Option B:** Migrate to MCP tools (requires MCP client library)

**Recommendation:** Option A - Add MCP support while keeping REST fallback

**Action:** 
- Add `--mcp` flag to use MCP tools
- Default to REST for now (backward compatible)
- Update `/mem` command to use MCP when available

---

### 3. Caddy Routing Fix

**File:** `/etc/caddy/Caddyfile` (on VPS)

**Current:** Comment says "port 9002" but should be "9001"

**Needs:**
```caddyfile
# Cursor MCP endpoint (IP:9001)
# Routes /mcp/* to MCP Memory Server (9001)  # FIX: was 9002
157.180.73.53:9001 {
    encode gzip
    
    # MCP Memory Server routes → port 9001  # FIX: was 9002
    reverse_proxy /mcp/* 127.0.0.1:9001
    
    # Default to l9-api → port 8000
    reverse_proxy 127.0.0.1:8000
}
```

**Also add to domain config:**
```caddyfile
l9.quantumaipartners.com {
    # ... existing routes ...
    
    # MCP Memory Server
    handle /mcp/* {
        reverse_proxy 127.0.0.1:9001
    }
    handle /memory/* {
        reverse_proxy 127.0.0.1:9001
    }
}
```

**Action:** Update Caddyfile on VPS, reload Caddy

---

### 4. Audit Log Schema Enhancement

**File:** `mcp_memory/schema/migrations/004_audit_governance.sql` (NEW)

**Current:** `memory.audit_log` exists but missing `caller` and `project_id` columns

**Needs:**
```sql
-- Add caller column (L or C)
ALTER TABLE memory.audit_log 
ADD COLUMN IF NOT EXISTS caller TEXT;

-- Add project_id column
ALTER TABLE memory.audit_log 
ADD COLUMN IF NOT EXISTS project_id TEXT;

-- Add indexes
CREATE INDEX IF NOT EXISTS idx_audit_caller 
ON memory.audit_log(caller, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_audit_project 
ON memory.audit_log(project_id, created_at DESC);
```

**Action:** Create migration file, apply on VPS

---

### 5. Runtime MCP Client Update

**File:** `runtime/mcp_client.py`

**Current:** Says "L9 Memory MCP is deprecated" (line 339-345)

**Needs:** Update comment to reflect that MCP server is now active

**Action:**
```python
# ========================================================================
# L9 Memory MCP (Active as of 2026-01-09)
# ========================================================================
# MCP server is live at https://l9.quantumaipartners.com/mcp
# Uses unified substrate (packet_store + memory_embeddings)
# See: mcp_memory/README.md for details
# ========================================================================
```

---

### 6. Docker Compose Service (Optional)

**File:** `docker-compose.yml`

**Current:** No `mcp-memory` service defined

**Decision:** MCP server runs as systemd service (not Docker) per current architecture

**Action:** Document that MCP server is systemd-managed, not Docker

---

### 7. Systemd Service Deployment

**File:** `mcp_memory/deploy/systemd/l9-mcp.service`

**Status:** File exists, needs to be deployed to VPS

**Action:**
```bash
# On VPS
sudo cp /opt/l9/mcp_memory/deploy/systemd/l9-mcp.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable l9-mcp
sudo systemctl start l9-mcp
```

---

### 8. Deployment Script Integration

**File:** `deploy.sh`

**Current:** Doesn't mention MCP server deployment

**Needs:** Add MCP server deployment step (if not already handled)

**Action:** Add MCP server deployment to deploy.sh (or document as separate step)

---

### 9. /mem Command Update

**File:** `.cursor-commands/commands/mem.md`

**Current:** Uses `cursor_memory_client.py` (REST API)

**Needs:** Option to use MCP tools when available

**Action:** Update `/mem` command to:
- Try MCP tools first (if mcp.json configured)
- Fall back to REST API if MCP unavailable
- Document both paths

---

### 10. Environment Variables

**File:** `.env` (on VPS and local)

**Needs:**
```bash
# MCP Memory Server
MCP_API_KEY_L=...  # L-CTO API key
MCP_API_KEY_C=...  # Cursor IDE API key
L_CTO_USER_ID=l9-shared  # Shared user ID
OPENAI_API_KEY=...  # For embeddings
MEMORY_DSN=postgresql://...  # Database connection
```

**Action:** Verify all env vars are set on VPS

---

## Integration Priority

### Critical (Blocks E2E)
1. ✅ **Cursor mcp.json** - Must be configured for Cursor to use MCP
2. ✅ **Caddy routing** - Must route `/mcp/*` correctly
3. ✅ **Systemd service** - Must be running on VPS
4. ✅ **Environment variables** - Must be set

### Important (Enhances Functionality)
5. ⚠️ **Audit log schema** - Adds caller/project_id tracking
6. ⚠️ **cursor_memory_client.py** - Add MCP support (backward compatible)
7. ⚠️ **Runtime MCP client** - Update deprecated comment

### Nice to Have (Documentation)
8. 📝 **Deploy script** - Document MCP server deployment
9. 📝 **Docker compose** - Document why systemd instead
10. 📝 **/mem command** - Add MCP option

---

## Testing Checklist

After integration:

- [ ] `curl https://l9.quantumaipartners.com/health` returns OK
- [ ] `curl -H "Authorization: Bearer $MCP_API_KEY_C" https://l9.quantumaipartners.com/mcp/tools` lists tools
- [ ] Cursor can discover MCP tools via mcp.json
- [ ] Cursor can call `save_memory` via MCP
- [ ] Cursor can call `search_memory` via MCP
- [ ] Scope enforcement works (Cursor blocked from l-private)
- [ ] Audit logging captures caller, project_id, scope
- [ ] `/mem` command works (REST or MCP)

---

## Files to Create/Update

### New Files
- [ ] `mcp_memory/schema/migrations/004_audit_governance.sql` - Add caller/project_id columns

### Files to Update
- [ ] `/Users/ib-mac/.cursor/mcp.json` - Add l9-memory server
- [ ] `.cursor-commands/cursor-memory/cursor_memory_client.py` - Add MCP support
- [ ] `runtime/mcp_client.py` - Update deprecated comment
- [ ] `.cursor-commands/commands/mem.md` - Document MCP option
- [ ] `deploy.sh` - Document MCP deployment (or add step)
- [ ] `/etc/caddy/Caddyfile` (VPS) - Fix port comment, ensure routing

### Files to Verify
- [ ] `mcp_memory/deploy/systemd/l9-mcp.service` - Service file correct
- [ ] `.env` (VPS) - All MCP env vars set
- [ ] VPS systemd - Service enabled and running

---

## Next Steps

1. **Immediate:** Update Cursor mcp.json with l9-memory server config
2. **Immediate:** Fix Caddy routing comment and verify routing works
3. **Immediate:** Deploy systemd service to VPS
4. **Next:** Create audit log migration (004_audit_governance.sql)
5. **Next:** Add MCP support to cursor_memory_client.py (backward compatible)
6. **Next:** Update runtime/mcp_client.py comment
7. **Documentation:** Update deploy.sh and /mem command docs

---

**Status:** Core implementation complete. Integration points identified. Ready for E2E wiring.

