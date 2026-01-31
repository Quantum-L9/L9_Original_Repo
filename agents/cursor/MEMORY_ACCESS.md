# Cursor Memory Access Instructions

## Quick Start

To access L9 memory from Cursor, use these environment variables:

```bash
export MCP_API_KEY_C="4836ea7e0f46c81fd6860c05f1be94577fbb99970fb378c49901cc6cffb9dd07"
export MCP_URL="http://46.62.243.82/memory"
```

**CRITICAL:** Use direct IP `46.62.243.82`, NOT `l9.quantumaipartners.com` - Cloudflare blocks Python user-agent.

---

## Memory Client Commands

```bash
# Health check
python3 agents/cursor/cursor_memory_client.py health

# Write a memory
python3 agents/cursor/cursor_memory_client.py write "Your content here" --kind lesson

# Search memories
python3 agents/cursor/cursor_memory_client.py search "query terms"

# Session stats
python3 agents/cursor/cursor_memory_client.py stats
```

### Kind options for write:
- `note` - General notes
- `preference` - User preferences
- `lesson` - Learned lessons
- `insight` - Insights discovered
- `error` - Error patterns

---

## MCP Tool API (curl)

For direct API access:

```bash
# Health
curl -s "http://46.62.243.82/memory/health"

# Write
curl -s -X POST "http://46.62.243.82/memory/mcp/call" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer 4836ea7e0f46c81fd6860c05f1be94577fbb99970fb378c49901cc6cffb9dd07" \
  -d '{"name": "save_memory", "arguments": {"content": "...", "kind": "lesson", "duration": "long", "user_id": "l9-shared"}}'

# Search
curl -s -X POST "http://46.62.243.82/memory/mcp/call" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer 4836ea7e0f46c81fd6860c05f1be94577fbb99970fb378c49901cc6cffb9dd07" \
  -d '{"name": "search_memory", "arguments": {"query": "...", "user_id": "l9-shared"}}'
```

---

## C1 Server Architecture

| Service | Internal Port | External Access |
|---------|---------------|-----------------|
| l9-mcp-memory | 9002 | via nginx `/memory/` |
| l9-api | 8000 | via nginx `/` |
| l9-postgres | 5432 | localhost only |
| l9-neo4j | 7687 | localhost only |
| l9-redis | 6379 | localhost only |
| l9-nginx | 80 | `46.62.243.82:80` |

**nginx routing:**
- `/memory/*` → strips prefix → `l9-mcp-memory:9002/*`
- `/*` → `l9-api:8000/*`

---

## API Keys (C1)

| Key | Purpose |
|-----|---------|
| `MCP_API_KEY_C` | Cursor IDE access (read all, write own) |
| `MCP_API_KEY_L` | L-CTO kernel (full access) |
| `MCP_API_KEY` | Legacy shared fallback |

Current `MCP_API_KEY_C`: `4836ea7e0f46c81fd6860c05f1be94577fbb99970fb378c49901cc6cffb9dd07`

---

## Troubleshooting

### "error code: 1010"
Cloudflare blocking Python user-agent. Use direct IP instead of domain.

### "Governance context required"
The REST `/search` endpoint doesn't set governance context. Use `/mcp/call` instead.

### "content: null" in search results
Old data has double-encoded JSONB payload (fixed 2026-01-31). New writes are correct.

### Container rebuild needed
```bash
ssh -i ~/.ssh/Hetzner-C1-nopass root@46.62.243.82 \
  "cd /opt/l9 && git pull origin main && docker compose build l9-mcp-memory && docker compose up -d l9-mcp-memory"
```

---

## Session Startup Checklist

1. Set env vars (MCP_API_KEY_C, MCP_URL with direct IP)
2. Run health check: `python3 agents/cursor/cursor_memory_client.py health`
3. If unhealthy, check C1: `ssh root@46.62.243.82 "docker ps | grep mcp"`
4. Search for relevant context: `python3 agents/cursor/cursor_memory_client.py search "[task keywords]"`

---

## History

- **2026-01-31:** Fixed JSONB double-encoding in `substrate_repository.py`
- **2026-01-31:** Added nginx `/memory/` route for external MCP access
- **2026-01-31:** Fixed `timezone` import in `audit.py` (rebuilt container)
