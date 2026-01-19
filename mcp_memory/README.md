# MCP Memory Server

**Updated:** 2026-01-16 | **URL:** `https://157.180.73.53:9001`

Unified memory substrate: PostgreSQL `packet_store` + pgvector `memory_embeddings`

## Governance

| Caller | API Key | Read | Write/Delete |
|--------|---------|------|--------------|
| L | `MCP_API_KEY_L` | All | All |
| Cursor | `MCP_API_KEY_C` | All | Own only |

`metadata.creator` enforced server-side. Cursor writes tagged `Cursor-IDE`.

## Architecture

```
MacBook → HTTPS → Cloudflare → VPS Caddy (:443, :9001) → l9-api:8000 → PostgreSQL
```

Runs inside `l9-api` Docker container. No separate service.

## CLI Usage

```bash
python3 agents/cursor/cursor_memory_client.py write "content" --kind fact
python3 agents/cursor/cursor_memory_client.py search "query"
python3 agents/cursor/cursor_memory_client.py health
python3 agents/cursor/cursor_memory_client.py stats
```

## MCP Tools

**Core:** `save_memory`, `search_memory`, `get_memory_stats`, `delete_expired_memories`  
**Graph:** `graph_query`, `graph_get_entity`, `graph_get_context`  
**Cognitive:** `get_context_injection`, `extract_session_learnings`, `query_temporal`

## Env Vars

**Required (VPS):**
- `OPENAI_API_KEY` - embeddings
- `MEMORY_DSN` - PostgreSQL connection
- `MCP_API_KEY_L`, `MCP_API_KEY_C` - auth

**Local .env:**
```bash
L9_API_URL=https://157.180.73.53:9001
L9_EXECUTOR_API_KEY=<MCP_API_KEY_C value>
```

## Key Files

- `src/mcp_server.py` - MCP tool definitions
- `src/routes/memory_unified.py` - handlers
- `api/routes/mcp.py` - `/mcp/call` endpoint (governance context here)
- `memory/governance_gate.py` - ContextVar enforcement

## Deploy (VPS)

```bash
cd /opt/l9
git pull && docker-compose build --no-cache l9-api && docker-compose up -d l9-api
```

Or: `bash scripts/deployment/10X_Deploy_Script.sh --quick --skip-mri --skip-e2e`

## Troubleshooting

| Issue | Fix |
|-------|-----|
| Governance context error | Rebuild container on VPS |
| 401 Unauthorized | Check `L9_EXECUTOR_API_KEY` in local `.env` |
| Connection timeout | Check `docker ps`, Caddy status |
| Logs | `docker logs l9-api --tail 50` |

## Recent Fix (GMP-68)

`api/routes/mcp.py` now wraps tool calls in `async with governance_context(gov_ctx)` - fixes "Governance context required" error.
