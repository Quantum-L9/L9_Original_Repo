# Caddy Configuration for L9 API (Unified Architecture)

**Purpose:** Configure Caddy reverse proxy to route all traffic (including MCP endpoints) to the unified `l9-api`

**File Location:** `/etc/caddy/Caddyfile` (on VPS)

**Last Updated:** 2026-01-12

---

## Architecture Summary

```
┌──────────────────────────────────────────────────────────────┐
│                      L9 VPS (157.180.73.53)                  │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  Internet                                                    │
│     │                                                        │
│     ▼                                                        │
│  ┌─────────────────────────────────────────────────────┐    │
│  │                    CADDY                             │    │
│  │                                                      │    │
│  │  :443 (l9.quantumaipartners.com) ─┬─► 127.0.0.1:8000│    │
│  │  :9001 (157.180.73.53:9001) ──────┘     (l9-api)    │    │
│  │                                                      │    │
│  └─────────────────────────────────────────────────────┘    │
│                          │                                   │
│                          ▼                                   │
│  ┌─────────────────────────────────────────────────────┐    │
│  │               l9-api (port 8000)                     │    │
│  │                                                      │    │
│  │  • /health, /docs, /openapi.json                    │    │
│  │  • /memory/*, /api/v1/memory/*                      │    │
│  │  • /mcp/tools, /mcp/call, /mcp/health               │    │
│  │  • /slack/*, /twilio/*, /waba/*                     │    │
│  │                                                      │    │
│  └─────────────────────────────────────────────────────┘    │
│                          │                                   │
│                          ▼                                   │
│         PostgreSQL (l9_memory) + Neo4j + Redis              │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

**Key Points:**

- **No standalone MCP server** — MCP endpoints are integrated into `l9-api`
- **Port 9001** is an alternate HTTPS front door, routing to the same `l9-api` on 8000
- **Port 9002 is not used** — there is no separate MCP service

---

## Canonical Caddyfile Configuration

```caddyfile
# L9 Main API (domain-based, with SSL)
l9.quantumaipartners.com {
    encode gzip

    # All traffic → unified l9-api
    reverse_proxy 127.0.0.1:8000
}

# Cursor MCP endpoint (IP:9001 - alternate HTTPS front door)
# Routes ALL traffic to unified l9-api (8000)
# MCP endpoints (/mcp/*) are implemented inside l9-api
157.180.73.53:9001 {
    encode gzip

    # All traffic → unified l9-api
    reverse_proxy 127.0.0.1:8000
}
```

---

## Endpoints Available Through l9-api

| Endpoint                 | Description                   |
| ------------------------ | ----------------------------- |
| `/health`                | API health check              |
| `/mcp/tools`             | List available MCP tools      |
| `/mcp/call`              | Execute MCP tool calls        |
| `/mcp/health`            | MCP-specific health check     |
| `/api/v1/memory/*`       | Memory API routes             |
| `/memory/*`              | Memory API routes (alternate) |
| `/slack/*`               | Slack webhook routes          |
| `/docs`, `/openapi.json` | API documentation             |

---

## Deployment / Update Steps

### Apply Canonical Config

```bash
# SSH to VPS
ssh root@157.180.73.53

# Backup current config
sudo cp /etc/caddy/Caddyfile /etc/caddy/Caddyfile.bak

# Write canonical config
sudo tee /etc/caddy/Caddyfile << 'EOF'
# L9 Main API
l9.quantumaipartners.com {
    encode gzip
    reverse_proxy 127.0.0.1:8000
}

# Cursor MCP endpoint (IP:9001)
157.180.73.53:9001 {
    encode gzip
    reverse_proxy 127.0.0.1:8000
}
EOF

# Validate and reload
sudo caddy validate --config /etc/caddy/Caddyfile
sudo systemctl reload caddy
```

### If Only Fixing 502 Error (Minimal Change)

If Caddy still has old `/mcp/*` → `9002` routing:

```bash
# One-liner fix: remove /mcp/* special routing (all goes to 8000)
sudo sed -i 's|reverse_proxy /mcp/\* 127.0.0.1:9002|reverse_proxy 127.0.0.1:8000|' /etc/caddy/Caddyfile
sudo systemctl reload caddy
```

---

## Testing

### Test via domain (443):

```bash
# Health
curl -s https://l9.quantumaipartners.com/health | jq .

# MCP tools (requires auth)
curl -s -H "Authorization: Bearer $MCP_API_KEY_C" \
  https://l9.quantumaipartners.com/mcp/tools | jq .

# MCP call
curl -s -X POST https://l9.quantumaipartners.com/mcp/call \
  -H "Authorization: Bearer $MCP_API_KEY_C" \
  -H "Content-Type: application/json" \
  -d '{"tool_name": "get_memory_stats", "arguments": {"user_id": "l9-shared"}}' | jq .
```

### Test via IP:9001:

```bash
# Health (bypasses domain, uses IP directly)
curl -ks https://157.180.73.53:9001/health | jq .

# MCP tools
curl -ks -H "Authorization: Bearer $MCP_API_KEY_C" \
  https://157.180.73.53:9001/mcp/tools | jq .
```

---

## Troubleshooting

### HTTP 502 Bad Gateway

**Cause:** Caddy routing to a backend that doesn't exist (e.g., port 9002)

**Fix:**

```bash
# Check current Caddyfile for 9002 references
grep 9002 /etc/caddy/Caddyfile

# If found, fix routing to use 8000
sudo sed -i 's|127.0.0.1:9002|127.0.0.1:8000|g' /etc/caddy/Caddyfile
sudo systemctl reload caddy
```

### HTTP 404 Not Found on /mcp/\*

**Cause:** MCP endpoints not integrated into `l9-api`

**Fix:** Ensure `api/routes/mcp.py` exists and is registered in `api/server.py`:

```python
# In api/server.py
from api.routes.mcp import router as mcp_router
app.include_router(mcp_router)
```

Then rebuild and restart:

```bash
cd /opt/l9
docker compose build l9-api
docker compose up -d l9-api
```

### Check Caddy Logs

```bash
sudo journalctl -u caddy -n 50 --no-pager
```

### Check l9-api Logs

```bash
docker compose logs -f l9-api --tail 50
```

---

## Why Unified Architecture?

- **Single codebase** — MCP endpoints live in `api/routes/mcp.py`, same FastAPI app
- **Shared PostgreSQL substrate** — Uses `DATABASE_URL` / `MEMORY_DSN` pointing to `l9_memory`
- **Shared authentication** — Same API key infrastructure for L and Cursor
- **Simpler deployment** — One Docker container (`l9-api`), no separate MCP service
- **Same ingestion pipeline** — MCP memory writes go through `MemorySubstrateService`

---

## Legacy Notes

> **⚠️ Deprecated:** Previous documentation referenced a standalone MCP server on port 9002.
> This architecture was **never deployed** on the VPS. All MCP functionality is integrated into
> the unified `l9-api` service on port 8000.
>
> **Do not create port 9002 routing** — it will cause 502 errors. All traffic routes to 8000.

---

## Official Configuration (Locked 2026-01-12)

**Verified Working Configuration:**

- **URL:** `https://157.180.73.53:9001` (IP-based) or `https://l9.quantumaipartners.com` (domain)
- **Backend:** `127.0.0.1:8000` (l9-api Docker container)
- **API Key:** `MCP_API_KEY_C` (for Cursor IDE)

See `docs/MCP-MEMORY-CAPSULE.md` for complete wiring documentation.

---
