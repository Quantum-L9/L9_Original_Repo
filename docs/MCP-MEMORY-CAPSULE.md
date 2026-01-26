# MCP Memory Integration - Official Configuration

**Status:** ✅ **PRODUCTION** - Verified E2E 2026-01-12
**Purpose:** Single source of truth for MCP Memory wiring between Cursor IDE and L9 VPS

---

## Architecture Summary

```
┌─────────────────────────────────────────────────────────────┐
│  Cursor IDE (MacBook)                                       │
│  └─ MCP Client → HTTPS → Cloudflare → VPS                  │
└──────────────────────┬──────────────────────────────────────┘
                       │ HTTPS (no SSH tunnel!)
┌──────────────────────▼──────────────────────────────────────┐
│  Cloudflare (Proxy)                                         │
│  └─ l9.quantumaipartners.com → 157.180.73.53               │
└──────────────────────┬──────────────────────────────────────┘
                       │ Port 443
┌──────────────────────▼──────────────────────────────────────┐
│  VPS (157.180.73.53)                                        │
│  ├─ Caddy (reverse proxy)                                   │
│  │   └─ :443, :9001 → 127.0.0.1:8000                        │
│  ├─ l9-api (Docker, port 8000)                              │
│  │   ├─ /mcp/tools, /mcp/call (MCP endpoints)              │
│  │   ├─ /api/v1/memory/* (Memory API)                       │
│  │   └─ MemorySubstrateService (full DAG pipeline)          │
│  └─ PostgreSQL + pgvector (l9memory database)              │
│       ├─ packet_store (event log)                           │
│       └─ memory_embeddings (vector store)                   │
└─────────────────────────────────────────────────────────────┘
```

**Key Points:**
- **Unified architecture** — MCP endpoints live inside `l9-api` (no separate service)
- **Port 8000** — All traffic routes to `l9-api` Docker container
- **Port 9001** — Alternate HTTPS front door (IP-based), also routes to 8000
- **No port 9002** — Deprecated, never deployed

---

## Official Configuration (Locked)

### Cursor MCP Config

**File:** `~/.cursor/mcp.json` (on MacBook)

```json
{
  "mcpServers": {
    "l9-memory": {
      "command": "node",
      "args": ["/path/to/mcp-http-bridge.js"],
      "env": {
        "MCPSERVERURL": "https://157.180.73.53:9001",
        "MCPAPIKEYC": "YOUR_MCP_API_KEY_C_VALUE"
      }
    }
  }
}
```

**OR** if using HTTP client directly:

```json
{
  "mcpServers": {
    "l9-memory": {
      "type": "http",
      "url": "https://157.180.73.53:9001",
      "headers": {
        "Authorization": "Bearer YOUR_MCP_API_KEY_C_VALUE"
      }
    }
  }
}
```

### Environment Variables

**VPS (`/opt/l9/.env`):**
```bash
# MCP API Keys
MCP_API_KEY_C=your-cursor-api-key-here    # ✅ Cursor IDE key
MCP_API_KEY_L=your-l-cto-api-key-here     # L-CTO key (optional)

# Database
MEMORY_DSN=postgresql://postgres:password@127.0.0.1:5432/l9memory

# OpenAI (for embeddings)
OPENAI_API_KEY=sk-...

# Enable MCP Memory
MCPMEMORYENABLED=true
```

**MacBook (local `.env` for `cursor_memory_client.py`):**
```bash
# MCP Server URL (use IP:9001 or domain)
L9_API_URL=https://157.180.73.53:9001
# OR: L9_API_URL=https://l9.quantumaipartners.com

# API Key (same as MCP_API_KEY_C from VPS)
L9_EXECUTOR_API_KEY=your-cursor-api-key-here
```

---

## Verified Endpoints

| Endpoint | Method | Description | Auth |
|----------|--------|-------------|------|
| `https://157.180.73.53:9001/mcp/tools` | GET | List MCP tools | Bearer token |
| `https://157.180.73.53:9001/mcp/call` | POST | Execute MCP tool | Bearer token |
| `https://157.180.73.53:9001/health` | GET | Health check | None |
| `https://l9.quantumaipartners.com/mcp/tools` | GET | List MCP tools (domain) | Bearer token |

**Test Command:**
```bash
curl -ks -H "Authorization: Bearer $MCP_API_KEY_C" \
  https://157.180.73.53:9001/mcp/tools | jq .
```

---

## Caddy Configuration

**File:** `/etc/caddy/Caddyfile` (on VPS)

```caddyfile
# L9 Main API (domain-based)
l9.quantumaipartners.com {
    encode gzip
    reverse_proxy 127.0.0.1:8000
}

# Cursor MCP endpoint (IP:9001 - alternate HTTPS front door)
# Routes ALL traffic to unified l9-api (8000)
157.180.73.53:9001 {
    encode gzip
    reverse_proxy 127.0.0.1:8000
}
```

**Key Points:**
- ✅ **No `/mcp/*` special routing** — All traffic goes to 8000
- ✅ **No port 9002** — Deprecated, never used
- ✅ **Unified backend** — Single `l9-api` container handles everything

---

## Pipeline Verification

When MCP memory saves work correctly, you should see:

1. **Response includes `"pipeline": "main_dag"`**
   ```json
   {
     "packet_id": "...",
     "pipeline": "main_dag",
     "written_tables": [
       "packet_store",
       "memory_embeddings",
       "knowledge_facts",
       "reasoning_traces"
     ]
   }
   ```

2. **Database verification:**
   - `packet_store` table has entry
   - `memory_embeddings` table has vector
   - `knowledge_facts` table has extracted facts (if applicable)
   - `reasoning_traces` table has trace (if applicable)

3. **Search works:**
   ```bash
   # Save memory
   curl -X POST https://157.180.73.53:9001/mcp/call \
     -H "Authorization: Bearer $MCP_API_KEY_C" \
     -H "Content-Type: application/json" \
     -d '{"tool_name": "save_memory", "arguments": {"content": "Test", "kind": "preference"}}'

   # Search for it (wait 2-5 seconds for embedding)
   curl -X POST https://157.180.73.53:9001/mcp/call \
     -H "Authorization: Bearer $MCP_API_KEY_C" \
     -H "Content-Type: application/json" \
     -d '{"tool_name": "search_memory", "arguments": {"query": "Test", "top_k": 5}}'
   ```

---

## Troubleshooting

### HTTP 502 Bad Gateway

**Cause:** Caddy routing to wrong port (e.g., 9002)

**Fix:**
```bash
# Check Caddyfile
grep 9002 /etc/caddy/Caddyfile

# If found, remove 9002 references
sudo sed -i 's|127.0.0.1:9002|127.0.0.1:8000|g' /etc/caddy/Caddyfile
sudo systemctl reload caddy
```

### HTTP 401 Unauthorized

**Cause:** Invalid or missing API key

**Fix:**
1. Verify `MCP_API_KEY_C` in VPS `.env`
2. Verify `L9_EXECUTOR_API_KEY` in local `.env` matches
3. Check Bearer token format: `Authorization: Bearer <key>`

### HTTP 429 Rate Limit Exceeded

**Cause:** Too many requests (60/minute default)

**Fix:**
- Wait 60 seconds
- Check rate limit logs: `docker compose logs l9-api | grep rate`
- If blocked due to failed auth: Wait 5 minutes (block expires)

---

## Rate Limiting & Auth Blocking

### Rate Limits

**Per-IP Limits:**
- **60 requests per minute** (default window)
- Tracked in-memory per IP address
- Resets automatically after window expires

**Per-Key Limits:**
- Same 60/minute limit applies per API key
- `MCP_API_KEY_C` and `MCP_API_KEY_L` tracked separately

### Auth Failure Blocking

**Brute-Force Protection:**
- **5 failed auth attempts** → IP blocked for 5 minutes
- Block expires automatically
- Tracked per IP address

**What Triggers Blocking:**
- Invalid API key
- Missing `Authorization: Bearer` header
- Wrong key format

**Recovery:**
1. **Fix API key** — Verify `MCP_API_KEY_C` in VPS `.env` matches local `.env`
2. **Wait 5 minutes** — Block expires automatically
3. **Clear Redis keys** (if Redis enabled):
   ```bash
   docker exec -it l9-redis redis-cli DEL "cursor:session:*:failed_auth"
   ```

### Testing Rate Limits

**Tight Loop Test (from MacBook):**
```bash
# Test rate limiting (should see 429 after 60 requests)
for i in {1..70}; do
  curl -ks -H "Authorization: Bearer $MCP_API_KEY_C" \
    https://157.180.73.53:9001/mcp/tools
  echo "Request $i"
  sleep 0.5
done
```

**Expected Behavior:**
- Requests 1-60: HTTP 200 OK
- Request 61+: HTTP 429 Rate Limit Exceeded
- After 60 seconds: Requests resume (200 OK)

### Memory Not Found in Search

**Cause:** Embedding not yet indexed

**Fix:**
- Wait 2-5 seconds after save before searching
- Check `memory_embeddings` table: `SELECT * FROM memory_embeddings WHERE packet_id = '...'`

---

## Governance Model

| Caller | API Key | Read | Write | Delete | Creator |
|--------|---------|------|-------|--------|---------|
| **L** | `MCP_API_KEY_L` | All memories | All memories | All memories | `L-CTO` |
| **C** | `MCP_API_KEY_C` | All memories | Own only | Own only | `Cursor-IDE` |

**Scopes:**
- `developer` — Shared between L and Cursor
- `l-private` — L only (Cursor blocked from writing)
- `global` — Cross-project shared

---

## Related Documentation

- **Quick Reference:** `mcp_memory/QUICK_REFERENCE.md`
- **Full README:** `mcp_memory/README.md`
- **Caddy Config:** `mcp_memory/deploy/CADDY_CONFIG.md`
- **Governance:** `mcp_memory/memory-setup-instructions.md`
- **E2E Test:** `mcp_memory/tests/verify_main_pipeline_e2e.py`

---

## Neo4j Posture (Deliberate Decision)

**Current Status:** Postgres-only mode (Neo4j optional)

**Decision:** The system is designed to run in **Postgres-only mode** for MCP memory operations. Neo4j graph sync is available but not required for core functionality.

### When Neo4j is Used

Neo4j is used for:
- **Repo structure graph** — File/class/function relationships (via `load_indexes_to_neo4j.py`)
- **World model** — Entity/relationship graph (if enabled)
- **Graph-based search** — Relationship traversal queries

### When Neo4j is NOT Required

MCP memory operations work fully without Neo4j:
- ✅ Memory saves (via `packet_store` + `memory_embeddings`)
- ✅ Semantic search (via pgvector)
- ✅ Fact extraction (stored in `knowledge_facts` table)
- ✅ Reasoning traces (stored in `reasoning_traces` table)

### Enabling Neo4j (Optional)

If you want to enable Neo4j on VPS:

1. **Set password in `.env`:**
   ```bash
   NEO4J_PASSWORD=your-secure-password
   ```

2. **Start Neo4j container:**
   ```bash
   docker compose up -d neo4j
   ```

3. **Load repo indexes:**
   ```bash
   python3 tools/export_repo_indexes.py
   python3 scripts/load_indexes_to_neo4j.py
   ```

4. **Expose world-model HTTP routes** (if needed):
   - Add routes to `api/world_model/router.py`
   - Register in `api/server.py`

**Reference:** See `TODO-ON-VPS.md` for complete Neo4j setup instructions.

---

## Deployment & Git Sync

### Git Hygiene Protocol

**Problem:** `/opt/l9` on VPS can diverge from GitHub `main` (extra commits, backup files).

**Solution:** Always sync via GitHub:

```bash
# On MacBook (local)
cd /Users/ib-mac/Projects/L9
git add .
git commit -m "Milestone cleanup: MCP official config"
git push origin main

# On VPS
ssh root@157.180.73.53
cd /opt/l9
git fetch origin
git reset --hard origin/main  # ⚠️ WARNING: Discards local changes
```

**Before `git reset --hard`:**
- ✅ All changes committed and pushed from local
- ✅ VPS `.env` backed up (if modified)
- ✅ Any VPS-only configs documented

### Keeping Docs Updated

**Files to keep in sync:**
- `docs/MCP-MEMORY-CAPSULE.md` (this file)
- `mcp_memory/deploy/CADDY_CONFIG.md`
- `mcp_memory/README.md`
- `mcp_memory/QUICK_REFERENCE.md`

**VPS Briefing:**
- Update `L9-VPS-BRIEFING.md` (if exists) with unified MCP + memory setup
- Document any VPS-specific configuration changes

---

## Change Log

- **2026-01-12:** Locked official URL (`https://157.180.73.53:9001`) and key (`MCP_API_KEY_C`)
- **2026-01-12:** Verified main pipeline integration (full DAG pipeline active)
- **2026-01-12:** Removed port 9002 references (deprecated, never deployed)
- **2026-01-12:** Added rate limiting & auth blocking documentation
- **2026-01-12:** Documented Neo4j posture (Postgres-only mode decision)
- **2026-01-12:** Added deployment & git sync protocol
