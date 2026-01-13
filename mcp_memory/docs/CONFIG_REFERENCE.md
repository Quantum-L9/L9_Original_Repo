# MCP Memory Configuration Reference

**Last Updated:** 2026-01-13  
**Status:** ✅ Canonical — matches VPS production

---

## Architecture Summary

```
┌─────────────────────────────────────────────────────────────────────────┐
│ MacBook (Local)                                                         │
│  └─ Cursor IDE → cursor_memory_client.py → HTTPS                       │
└──────────────────────────────┬──────────────────────────────────────────┘
                               │ Port 443 (via Cloudflare) or 9001 (direct IP)
┌──────────────────────────────↓──────────────────────────────────────────┐
│ VPS: 157.180.73.53                                                      │
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │ Caddy (reverse proxy)                                            │   │
│  │   :443  l9.quantumaipartners.com  ──┬──► 127.0.0.1:8000         │   │
│  │   :9001 157.180.73.53:9001 ─────────┘        (l9-api)           │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                    │                                    │
│  ┌─────────────────────────────────↓───────────────────────────────┐   │
│  │ l9-api Docker Container (port 8000)                              │   │
│  │                                                                  │   │
│  │  /health            → Health check                               │   │
│  │  /mcp/tools         → List MCP tools                             │   │
│  │  /mcp/call          → Execute MCP tool                           │   │
│  │  /memory/*          → Memory API (REST)                          │   │
│  │  /api/v1/memory/*   → Memory API v1                              │   │
│  └──────────────────────────────────────────────────────────────────┘   │
│                                    │                                    │
│  ┌─────────────────────────────────↓───────────────────────────────┐   │
│  │ l9-postgres Docker Container (port 5432)                         │   │
│  │   Database: l9_memory                                            │   │
│  │   Tables: packet_store, memory_embeddings, tool_audit_log        │   │
│  └──────────────────────────────────────────────────────────────────┘   │
│                                                                         │
│  Redis (6379) + Neo4j (7687) — also Docker containers                  │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Port Reference

| Port | Service | Notes |
|------|---------|-------|
| **8000** | l9-api container | Unified FastAPI app (MCP + Memory + API) |
| **9001** | Caddy HTTPS | Alternate front door (IP-based), routes to 8000 |
| **443** | Caddy HTTPS | Domain-based, routes to 8000 |
| **5432** | l9-postgres | PostgreSQL (localhost only) |
| **6379** | Redis | Task queue, caching (localhost only) |
| **7474** | Neo4j HTTP | Browser UI (localhost only) |
| **7687** | Neo4j Bolt | Graph queries (localhost only) |
| ~~9002~~ | ~~MCP standalone~~ | **DEPRECATED** — never deployed, do not use |

---

## Environment Variables

### VPS `.env` (Required)

```bash
# === PostgreSQL ===
POSTGRES_USER=l9_user
POSTGRES_PASSWORD=<your-password>
POSTGRES_DB=l9_memory
DATABASE_URL=postgresql://l9_user:<password>@l9-postgres:5432/l9_memory
MEMORY_DSN=postgresql://l9_user:<password>@l9-postgres:5432/l9_memory

# === API Keys ===
OPENAI_API_KEY=sk-...
L9_API_KEY=<your-l9-api-key>
L9_EXECUTOR_API_KEY=<your-executor-key>

# === MCP Memory Keys (Governance) ===
MCP_API_KEY_L=<l-cto-api-key>      # L-CTO: full read/write/delete
MCP_API_KEY_C=<cursor-api-key>     # Cursor: read all, write/delete own only

# === Optional ===
MCP_API_KEY=<legacy-fallback>      # Legacy (use _L/_C instead)
LOG_LEVEL=INFO
```

### Local `.env` (Cursor Client)

```bash
L9_API_URL=https://157.180.73.53:9001
L9_EXECUTOR_API_KEY=<same-as-MCP_API_KEY_C>
```

---

## Caddy Configuration

**File:** `/etc/caddy/Caddyfile` (VPS)

```caddyfile
# L9 Main API (domain-based)
l9.quantumaipartners.com {
    encode gzip
    reverse_proxy 127.0.0.1:8000
}

# Cursor MCP endpoint (IP:9001)
157.180.73.53:9001 {
    encode gzip
    reverse_proxy 127.0.0.1:8000
}
```

**Commands:**
```bash
sudo caddy validate --config /etc/caddy/Caddyfile
sudo systemctl reload caddy
```

---

## Docker Services

**File:** `/opt/l9/docker-compose.yml`

| Container | Image | Purpose |
|-----------|-------|---------|
| `l9-api` | Custom (runtime/Dockerfile) | Unified API + MCP |
| `l9-postgres` | postgres:16-alpine | L9 Memory substrate |
| `l9-redis` | redis:7-alpine | Task queue, caching |
| `l9-neo4j` | neo4j:5-community | Knowledge graph |

**Commands:**
```bash
# Start all
docker compose up -d

# Restart API only
docker compose restart l9-api

# View logs
docker compose logs -f l9-api

# Rebuild after code changes
docker compose build l9-api && docker compose up -d l9-api
```

---

## Database Schema

### Core Tables (L9 Memory Substrate)

| Table | Purpose |
|-------|---------|
| `packet_store` | Event log (all memory operations) |
| `memory_embeddings` | Vector store (pgvector HNSW indexed) |
| `tool_audit_log` | MCP tool call audit trail |

### Migrations

Applied via `migrations/` folder:
- `0001-0013` — Core L9 substrate (packet_store, memory_embeddings)
- `0013_mcp_audit_columns.sql` — Added `caller`, `project_id` to audit log

**Apply manually:**
```bash
psql $MEMORY_DSN -f migrations/0013_mcp_audit_columns.sql
```

---

## MCP Tools

### Core
| Tool | Description |
|------|-------------|
| `save_memory` | Store with automatic embedding |
| `search_memory` | Semantic similarity search |
| `get_memory_stats` | Usage statistics |
| `delete_expired_memories` | Cleanup expired |

### 10X Cognitive
| Tool | Description |
|------|-------------|
| `get_context_injection` | Auto-context before tasks |
| `extract_session_learnings` | Extract patterns from session |
| `get_proactive_suggestions` | Pattern-based suggestions |
| `query_temporal` | Time-based queries |
| `save_memory_with_confidence` | Confidence-scored saves |
| `compound_similar_memories` | Merge similar |
| `apply_importance_decay` | Decay unused |

---

## Governance Model

| Caller | API Key | Read | Write | Delete |
|--------|---------|------|-------|--------|
| **L-CTO** | `MCP_API_KEY_L` | All | All | All |
| **Cursor** | `MCP_API_KEY_C` | All | Own only | Own only |

**Enforcement:**
- Server-side in `src/mcp_server.py`
- `metadata.creator` set server-side (never trust client)
- SQL-level filtering on write/delete

---

## File Locations

### VPS
```
/opt/l9/                      # Git repo root
├── docker-compose.yml        # Service definitions
├── .env                      # Environment variables
├── migrations/               # SQL migrations
└── mcp_memory/
    ├── src/                  # MCP server code
    └── deploy/               # Deployment scripts
```

### Local (Mac)
```
$HOME/Projects/L9/
├── .env                      # Local env (L9_API_URL, L9_EXECUTOR_API_KEY)
├── agents/cursor/
│   └── cursor_memory_kernel.py  # Memory integration
└── mcp_memory/               # MCP server source
```

---

## Quick Health Checks

```bash
# From VPS
curl http://127.0.0.1:8000/health

# Via HTTPS (external)
curl https://l9.quantumaipartners.com/health
curl -sk https://157.180.73.53:9001/health

# MCP Tools (requires auth)
curl -H "Authorization: Bearer $MCP_API_KEY_C" \
  https://l9.quantumaipartners.com/mcp/tools
```

---

## Related Documentation

| Document | Purpose |
|----------|---------|
| `deploy/VPS_DEPLOYMENT_GUIDE.md` | Step-by-step VPS deployment |
| `deploy/CADDY_CONFIG.md` | Caddy reverse proxy config |
| `QUICK_REFERENCE.md` | Concise usage guide |
| `memory-setup-instructions.md` | Governance specification |

---

**Canonical Source:** This file reflects the actual VPS configuration as of 2026-01-13.
