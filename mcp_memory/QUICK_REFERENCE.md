# MCP Memory Server - Quick Reference

**Last Updated:** 2026-01-05  
**Status:** ✅ Active - Production-ready

> **For Cursor Agent:** This file is automatically loaded at startup via `setup-new-workspace.yaml` Phase 2.6 (memory_context) and Phase 4 (reference_learning). Read this to understand MCP Memory usage patterns, endpoints, and configuration.

---

## Architecture

### Unified Substrate
- **Tables:** `packet_store` (event log) + `memory_embeddings` (vectors)
- **Migrations:** L9 migrations (`migrations/0001-0013`)
- **Handlers:** `src/routes/memory_unified.py`

### Deployment
- **Method:** Docker (runs inside `l9-api` container)
- **Activation:** `deploy/scripts/init_mcp_memory.sh`
- **Routing:** Caddy routes `/mcp/*` → `l9-api:8000`

---

## Quick Activation (VPS)

```bash
cd /opt/l9
bash mcp_memory/deploy/scripts/init_mcp_memory.sh
```

**What it does:**
1. Checks MCP env vars in `.env`
2. Sets `MCPMEMORYENABLED=true`
3. Restarts `l9-api` Docker container
4. Verifies health

---

## Key Files

| File | Purpose |
|------|---------|
| `src/main.py` | FastAPI app entry point |
| `src/routes/memory_unified.py` | Unified memory handlers |
| `src/mcp_server.py` | MCP tool definitions |
| `src/config.py` | Settings (env vars) |
| `deploy/scripts/init_mcp_memory.sh` | Activation script |
| `deploy/VPS_DEPLOYMENT_GUIDE.md` | Full deployment guide |
| `memory-setup-instructions.md` | Governance specification |

---

## Environment Variables

### MCP Server (VPS .env)
```bash
MCP_API_KEY_L=...      # L-CTO API key
MCP_API_KEY_C=...      # Cursor IDE API key
OPENAI_API_KEY=...     # For embeddings
MEMORY_DSN=...         # PostgreSQL connection
```

### Cursor Client (cursor_memory_client.py) - Set in .env
```bash
L9_API_URL=https://157.180.73.53:9001  # MCP server URL (default)
# OR for local Docker:
# L9_API_URL=http://127.0.0.1:8000

L9_EXECUTOR_API_KEY=$MCP_API_KEY_C  # Use MCP_API_KEY_C value from VPS .env
```

**Note:** `cursor_memory_client.py` loads from `.env` file automatically. Set `L9_API_URL` and `L9_EXECUTOR_API_KEY` in your local `.env` file.

### Server Config
```bash
MCP_HOST=0.0.0.0       # Bind address
MCP_PORT=9001          # Server port (inside Docker)
MCP_ENV=production     # Environment
MCPMEMORYENABLED=true  # Enable flag
```

---

## MCP Tools

### Core Tools
- `save_memory` - Store with embedding
- `search_memory` - Semantic similarity search
- `get_memory_stats` - Usage statistics
- `delete_expired_memories` - Cleanup expired

### 10X Cognitive Tools
- `get_context_injection` - Auto-context before tasks
- `extract_session_learnings` - Extract patterns from session
- `get_proactive_suggestions` - Pattern-based suggestions
- `query_temporal` - Time-based queries
- `save_memory_with_confidence` - Confidence-scored saves
- `compound_similar_memories` - Merge similar memories
- `apply_importance_decay` - Decay unused importance

---

## Governance

### Scopes
- `developer` - Shared between L and Cursor
- `l-private` - L only (Cursor blocked)
- `global` - Cross-project shared

### API Keys
- `MCP_API_KEY_L` - L-CTO (full read/write/delete)
- `MCP_API_KEY_C` - Cursor IDE (read all, write/delete own only)

### Enforcement
- Server-side in `src/mcp_server.py`
- SQL-level filtering in queries
- Metadata: `creator`, `source`, `caller`, `project_id`

---

## Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/health` | GET | Health check |
| `/mcp/tools` | GET | List MCP tools |
| `/mcp/call` | POST | Execute MCP tool |
| `/memory/save` | POST | Save memory (legacy REST) |
| `/memory/search` | POST | Search memories (legacy REST) |

---

## Testing

```bash
# Health check
curl http://127.0.0.1:8000/health

# MCP tools (requires API key)
curl -H "Authorization: Bearer $MCP_API_KEY_C" \
  http://127.0.0.1:8000/mcp/tools

# Save memory (via MCP)
curl -X POST http://127.0.0.1:8000/mcp/call \
  -H "Authorization: Bearer $MCP_API_KEY_C" \
  -H "Content-Type: application/json" \
  -d '{
    "server_id": "l9-memory",
    "tool_name": "save_memory",
    "arguments": {
      "content": "Test memory",
      "kind": "milestone",
      "scope": "developer"
    }
  }'
```

---

## Troubleshooting

### Container Not Starting
```bash
docker logs l9-api
docker ps | grep l9-api
```

### Missing Env Vars
```bash
cd /opt/l9
grep -E "MCP|MEMORY" .env
```

### Health Check Fails
```bash
# Check container health
docker ps

# Check logs
docker logs l9-api --tail 50

# Restart
docker compose restart l9-api
```

---

## Related Documentation

- **Full Guide:** `deploy/L9-MCP-IMPL.md` (1506 lines)
- **Deployment:** `deploy/VPS_DEPLOYMENT_GUIDE.md`
- **Governance:** `memory-setup-instructions.md`
- **Architecture:** `mcp-memory-architecture/ARCHITECTURE.md`
- **Main README:** `README.md`

---

## Current Status

✅ **Active** - Production-ready  
✅ **Unified Substrate** - Uses `packet_store` + `memory_embeddings`  
✅ **Docker-based** - Runs inside `l9-api` container  
✅ **MCP Tools** - All 12 tools implemented  
✅ **Governance** - Scope enforcement active  

**Last Verified:** 2026-01-05
