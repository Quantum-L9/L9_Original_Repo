# L9 MCP Memory Server

OpenAI embeddings + pgvector semantic search for **L-CTO and Cursor IDE** collaboration.

**Production URL:** `https://l9.quantumaipartners.com/mcp/*`

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
│  │   └─ /mcp/* → MCP Server:9002                               │
│  ├─ FastAPI MCP Server (127.0.0.1:9002, systemd service)        │
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

```bash
# 1. Bootstrap (creates all files)
./bootstrap.sh

# 2. Configure
cp .env.example .env
# Edit .env with your credentials

# 3. Deploy to VPS
scp -r . admin@YOUR_VPS:/opt/l9/mcp_memory/
ssh admin@YOUR_VPS
cd /opt/l9/mcp_memory
./deploy/scripts/install.sh
```

## Access (Production)

No SSH tunnel needed! Access directly via HTTPS:

```bash
curl https://l9.quantumaipartners.com/health
curl -H "Authorization: Bearer YOUR_API_KEY" https://l9.quantumaipartners.com/mcp/tools
```

## SSH Tunnel (Development Only)

Only needed for local development bypassing Cloudflare:

```bash
ssh -L 9001:127.0.0.1:9001 root@157.180.73.53
# Then access http://127.0.0.1:9001
```

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
├── src/
│   ├── main.py           # FastAPI app, lifespan, auth
│   ├── config.py         # Pydantic settings
│   ├── db.py             # asyncpg pool
│   ├── embeddings.py     # OpenAI embedding client
│   ├── models.py         # Pydantic request/response models
│   ├── mcp_server.py     # MCP tool definitions
│   └── routes/
│       ├── memory.py     # CRUD, search, compounding, decay
│       └── health.py     # Health check
├── schema/
│   ├── init.sql          # Initial schema
│   └── migrations/       # Schema migrations
├── tests/
│   ├── test_memory.py
│   ├── test_search.py
│   └── test_embeddings.py
├── deploy/
│   ├── L9-MCP-IMPL.md    # Full implementation guide
│   ├── systemd/          # Service files
│   └── scripts/          # Deploy scripts
├── requirements.txt
├── bootstrap.sh          # One-command setup
└── README.md             # This file
```

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

## VPS Deployment

### Caddy Configuration

Add to `/etc/caddy/Caddyfile`:

```caddyfile
l9.quantumaipartners.com {
    # MCP Memory endpoints
    handle /mcp/* {
        reverse_proxy 127.0.0.1:9001
    }
    handle /memory/* {
        reverse_proxy 127.0.0.1:9001
    }
    
    # L9 API (default)
    handle {
        reverse_proxy 127.0.0.1:8000
    }
}
```

Reload: `sudo systemctl reload caddy`

### Systemd Service

```bash
# Copy service file
sudo cp deploy/systemd/l9-mcp.service /etc/systemd/system/

# Enable and start
sudo systemctl daemon-reload
sudo systemctl enable l9-mcp
sudo systemctl start l9-mcp

# Check status
sudo systemctl status l9-mcp
sudo journalctl -u l9-mcp -f
```

### Deploy Commands

```bash
# On VPS
cd /opt/l9/mcp_memory
git pull origin main

# Install dependencies
pip install -r requirements.txt

# Apply schema
psql $MEMORY_DSN -f schema/init.sql
psql $MEMORY_DSN -f schema/migrations/001_hnsw_upgrade.sql
psql $MEMORY_DSN -f schema/migrations/002_10x_memory_upgrade.sql

# Restart service
sudo systemctl restart l9-mcp
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
