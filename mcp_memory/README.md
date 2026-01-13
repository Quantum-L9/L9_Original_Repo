# L9 MCP Memory Server

OpenAI embeddings + pgvector semantic search for **L-CTO and Cursor IDE** collaboration.

**Status:** ✅ **ACTIVE** - Production-ready, Docker-based deployment  
**Production URL:** `https://l9.quantumaipartners.com:9001/mcp/*`  
**Architecture:** Unified L9 substrate (`packet_store` + `memory_embeddings`)

> **Quick Reference:** See `QUICK_REFERENCE.md` for concise usage guide.

## Governance Model (v2.0)

L (L-CTO kernel) and C (Cursor IDE) share a single memory substrate with asymmetric permissions:

| Caller | API Key | Read | Write | Delete | Creator |
|--------|---------|------|-------|--------|---------|
| **L** | `MCP_API_KEY_L` | All memories | All memories | All memories | `L-CTO` |
| **C** | `MCP_API_KEY_C` | All memories | Own only | Own only | `Cursor-IDE` |

**Key invariants:**
- L and C share the same `user_id` (`L_CTO_USER_ID`) for collaboration
- `metadata.creator` is enforced server-side (never trust client)
- C can only UPDATE/DELETE rows where `metadata.creator = 'Cursor-IDE'`
- All operations are captured in `tool_audit_log` with caller identity and project_id

**Note:** Legacy HTTP-only mode is supported but **not recommended** when MCP is available. MCP is the **preferred** path for external dev tools.

See: `memory-setup-instructions.md` for full governance spec.

```
┌─────────────────────────────────────────────────────────────────┐
│ MacBook (Local)                                                 │
│  └─ Cursor IDE → MCP Client → https://l9.quantumaipartners.com │
└──────────────────────┬──────────────────────────────────────────┘
                       │ HTTPS via Cloudflare (no SSH tunnel!)
┌──────────────────────↓──────────────────────────────────────────┐
│ Cloudflare (Proxy)                                              │
│  └─ DNS: l9.quantumaipartners.com → VPS (proxied)              │
└──────────────────────┬──────────────────────────────────────────┘
                       │ Port 443
┌──────────────────────↓──────────────────────────────────────────┐
│ VPS (L9)                                                        │
│  ├─ Caddy (reverse proxy)                                       │
│  │   └─ :443, :9001 → 127.0.0.1:8000 (unified l9-api)          │
│  ├─ l9-api (Docker, port 8000)                                  │
│  │   ├─ /mcp/tools     (tool discovery)                        │
│  │   ├─ /mcp/call      (tool execution)                        │
│  │   ├─ /memory/save   (store embeddings)                      │
│  │   └─ /memory/search (vector similarity)                     │
│  └─ PostgreSQL + pgvector (127.0.0.1:5432)                     │
│       ├─ packet_store (unified event log)                      │
│       └─ memory_embeddings (vector store, HNSW indexed)        │
└─────────────────────────────────────────────────────────────────┘
```

## Quick Start

### VPS Activation (Docker-based)

```bash
# On VPS
cd /opt/l9
bash mcp_memory/deploy/scripts/init_mcp_memory.sh
```

This script:
1. Checks MCP environment variables in `.env`
2. Enables MCP memory (`MCPMEMORYENABLED=true`)
3. Restarts `l9-api` Docker container
4. Verifies health endpoints

**Note:** MCP Memory runs **inside the `l9-api` Docker container**, not as a separate systemd service.

## Access (Production)

**Primary Method:** Via L9 API (Docker container)

```bash
# Health check
curl http://127.0.0.1:8000/health

# Via HTTPS (Caddy proxy)
curl -sk https://157.180.73.53:9001/health

# MCP tools (requires API key)
curl -H "Authorization: Bearer $MCP_API_KEY_C" \
  https://l9.quantumaipartners.com:9001/mcp/tools
```

**Note:** MCP Memory is integrated into `l9-api` container. No separate service needed.

## API Reference

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check |
| `/mcp/tools` | GET | List MCP tools |
| `/mcp/call` | POST | Execute MCP tool |
| `/memory/save` | POST | Save memory |
| `/memory/search` | POST | Search memories |
| `/memory/stats` | GET | Memory statistics |

## MCP Tools

### Core Tools
| Tool | Description |
|------|-------------|
| `save_memory` | Store with automatic embedding |
| `search_memory` | Semantic similarity search |
| `get_memory_stats` | Usage statistics |
| `delete_expired_memories` | Cleanup expired |

### 10X Cognitive Tools
| Tool | Description |
|------|-------------|
| `get_context_injection` | Auto-context before starting a task |
| `extract_session_learnings` | Extract patterns from completed session |
| `get_proactive_suggestions` | Pattern-based suggestions for current context |
| `query_temporal` | Time-based memory queries (what changed since X) |
| `save_memory_with_confidence` | Store with confidence scoring |
| `compound_memories` | Merge similar memories |
| `apply_decay` | Decay unused memory importance |

## Multi-User Support

All memory operations are scoped by `user_id`:

```json
{
  "tool_name": "save_memory",
  "arguments": {
    "content": "Remember this...",
    "kind": "fact",
    "duration": "long"
  },
  "user_id": "cursor"
}
```

| User ID | Purpose |
|---------|---------|
| `cursor` | Default for Cursor IDE |
| `igor` | Igor's personal memories (if needed) |
| `{agent_id}` | Other agents (not recommended - use L9 Memory) |

**Note:** The `user_id` defaults to `"cursor"` via `DEFAULT_USER_ID` env var.

## Environment Variables

### Required

| Variable | Description |
|----------|-------------|
| `OPENAI_API_KEY` | OpenAI API key for embeddings |
| `MEMORY_DSN` | PostgreSQL connection string |
| `MCP_API_KEY` | API key for authentication |

### Optional

| Variable | Default | Description |
|----------|---------|-------------|
| `MCP_HOST` | `0.0.0.0` | Bind address (0.0.0.0 for Caddy proxy) |
| `MCP_PORT` | `9001` | Server port |
| `MCP_ENV` | `production` | Environment |
| `LOG_LEVEL` | `INFO` | Logging level |
| `DEFAULT_USER_ID` | `cursor` | Default user_id for requests |
| `VECTOR_INDEX_TYPE` | `hnsw` | Index type (hnsw/ivfflat) |
| `HNSW_M` | `16` | HNSW connections per node |
| `HNSW_EF_CONSTRUCTION` | `64` | HNSW build quality |
| `HNSW_EF_SEARCH` | `40` | HNSW search quality |
| `COMPOUNDING_ENABLED` | `true` | Auto-merge similar memories |
| `DECAY_ENABLED` | `true` | Decay unused importance |

### Example `.env`

```bash
OPENAI_API_KEY=sk-...
MEMORY_DSN=postgresql://postgres:YOUR_PASSWORD@127.0.0.1:5432/l9_memory
MCP_API_KEY=your-secret-api-key
MCP_HOST=0.0.0.0
MCP_PORT=9001
LOG_LEVEL=INFO
DEFAULT_USER_ID=cursor
```

## File Structure

```
mcp_memory/
├── src/                          # Python implementation
│   ├── main.py                   # FastAPI app, lifespan, auth
│   ├── config.py                 # Pydantic settings
│   ├── db.py                     # asyncpg pool
│   ├── embeddings.py             # OpenAI embedding client
│   ├── models.py                 # Pydantic request/response models
│   ├── mcp_server.py             # MCP tool definitions
│   └── routes/
│       ├── memory_unified.py     # Unified handlers (packet_store + memory_embeddings)
│       ├── memory.py             # Legacy handlers (deprecated)
│       └── health.py             # Health check
├── deploy/                       # Deployment guides
│   ├── L9-MCP-IMPL.md            # Full implementation guide (1506 lines)
│   ├── VPS_DEPLOYMENT_GUIDE.md   # VPS deployment steps
│   ├── CADDY_CONFIG.md           # Caddy routing configuration
│   ├── scripts/
│   │   └── init_mcp_memory.sh    # Docker-based activation script
│   └── systemd/                   # Legacy systemd files (not used)
├── tests/                        # Test files
├── docs/                         # Canonical configuration docs
│   ├── README.md                 # Doc index
│   └── CONFIG_REFERENCE.md       # Ports, env vars, architecture
├── mcp-memory-architecture/      # Architecture documentation
│   └── ARCHITECTURE.md           # Current architecture
├── _archived/                    # Archived outdated docs
│   ├── status/                   # Completed status docs
│   ├── migration/                 # Migration docs
│   ├── comparison/                # Comparison/answer docs
│   ├── conceptual/                # Conceptual docs
│   └── schema/                    # Deprecated schema (memory.* tables)
├── memory-setup-instructions.md  # Governance specification
├── QUICK_REFERENCE.md            # Concise usage guide
├── requirements.txt
└── README.md                     # This file
```

**Note:** The `schema/` directory has been archived. MCP Memory uses the unified L9 substrate (`packet_store` + `memory_embeddings`) from L9 migrations.

## Dependencies

```
# Core
fastapi>=0.115.0
uvicorn[standard]>=0.30.0
pydantic-settings>=2.0.0

# Database
asyncpg>=0.29.0
pgvector>=0.2.5

# Embeddings
openai>=1.0.0

# Logging
structlog>=24.1.0

# Testing
pytest>=8.0.0
pytest-asyncio>=0.23.0
```

## VPS Deployment (Docker-Based)

> **IMPORTANT:** MCP Memory runs inside the `l9-api` Docker container, NOT as a standalone systemd service.
> See `deploy/VPS_DEPLOYMENT_GUIDE.md` for full instructions.

### Quick Activation

```bash
# On VPS
cd /opt/l9
bash mcp_memory/deploy/scripts/init_mcp_memory.sh
```

### Caddy Configuration

All traffic routes to unified `l9-api` (port 8000). See `deploy/CADDY_CONFIG.md` for full details.

```caddyfile
# L9 Main API (domain-based)
l9.quantumaipartners.com {
    encode gzip
    reverse_proxy 127.0.0.1:8000
}

# Cursor MCP endpoint (IP:9001 - alternate front door)
157.180.73.53:9001 {
    encode gzip
    reverse_proxy 127.0.0.1:8000
}
```

**Key Points:**
- ✅ No standalone MCP service — integrated into `l9-api`
- ✅ Port 9002 is **deprecated** (never deployed)
- ✅ Both `:443` and `:9001` route to `127.0.0.1:8000`

### Deploy Commands

```bash
# On VPS - sync code and restart
cd /opt/l9
git fetch origin && git reset --hard origin/main
docker compose build l9-api
docker compose up -d l9-api

# Verify
curl http://127.0.0.1:8000/health
```

## Troubleshooting

**Connection timeout:**
- Check Cloudflare DNS: `dig l9.quantumaipartners.com`
- Check Caddy: `sudo systemctl status caddy`
- Check service: `sudo systemctl status l9-mcp`

**401 Unauthorized:**
- Verify API key in request header: `Authorization: Bearer YOUR_API_KEY`
- Check `MCP_API_KEY` matches in `.env`

**Embedding failures:**
- Verify API key: `echo $OPENAI_API_KEY`
- Check quota: https://platform.openai.com/account/usage

**Slow searches:**
- Verify HNSW indexes: `\d+ memory.long_term`
- Run: `ANALYZE memory.long_term;`

**Service won't start:**
- Check logs: `sudo journalctl -u l9-mcp -n 50`
- Verify `.env` file exists with all required variables
- Verify PostgreSQL is running: `sudo systemctl status l9-postgres`
