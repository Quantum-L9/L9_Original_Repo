# VPS Caddy MCP Configuration

**Purpose:** Document Caddy reverse proxy configuration for MCP Memory Server

**File Location:** `/etc/caddy/Caddyfile` (on VPS)

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│                    Cloudflare (HTTPS)                    │
│              l9.quantumaipartners.com:443                │
└──────────────────────┬──────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────┐
│                    Caddy (Reverse Proxy)                │
│  Port 9001: Memory API → l9-api:8000                    │
│  Port 9001: /mcp/* → MCP Server:9002                    │
└──────────────────────┬──────────────────────────────────┘
                       │
        ┌──────────────┴──────────────┐
        │                             │
        ▼                             ▼
┌───────────────┐           ┌──────────────────┐
│  l9-api:8000  │           │  MCP Server:9002  │
│  (Docker)     │           │  (Systemd)       │
└───────────────┘           └──────────────────┘
```

**Port Assignment:**
- **9001** = TLS front door for MCP (Caddy listens, routes to backend)
- **9002** = MCP Memory Server (internal, systemd service)
- **8000** = L9 API (Docker container)

---

## Routing Rules

### Upstream Split

1. **MCP paths** (`/mcp/*`) → MCP server (127.0.0.1:9002)
2. **Memory API paths** (`/memory/*`, `/api/v1/memory/*`) → MCP server (127.0.0.1:9002) OR l9-api (127.0.0.1:8000)
3. **Everything else** → l9-api (127.0.0.1:8000)

### Priority Order

Caddy processes routes in order:
1. Specific path handlers (`handle /mcp/*`)
2. Path-based reverse proxy (`reverse_proxy /memory*`)
3. Default reverse proxy (`reverse_proxy 127.0.0.1:8000`)

---

## Configuration Examples

### Domain-Based (Recommended)

```caddyfile
l9.quantumaipartners.com {
    encode gzip

    # Core L9 API routes
    reverse_proxy /health 127.0.0.1:8000
    reverse_proxy /docs* 127.0.0.1:8000
    reverse_proxy /openapi.json 127.0.0.1:8000
    reverse_proxy /slack/* 127.0.0.1:8000
    reverse_proxy /twilio* 127.0.0.1:8000
    reverse_proxy /waba* 127.0.0.1:8000
    
    # MCP Memory Server - protocol endpoints
    handle /mcp/* {
        reverse_proxy 127.0.0.1:9002
    }
    
    # MCP Memory Server - direct memory API (backward compatibility)
    handle /api/v1/memory/* {
        reverse_proxy 127.0.0.1:9002
    }
    
    # Memory API (legacy, routes to l9-api)
    reverse_proxy /memory* 127.0.0.1:8000
    
    # Default to L9 API
    reverse_proxy 127.0.0.1:8000
}
```

### IP-Based (Alternative)

```caddyfile
# Memory API endpoint (IP:9001)
# Routes /memory/* to L9 Memory API (8000)
157.180.73.53:9001 {
    encode gzip
    reverse_proxy /memory* 127.0.0.1:8000
    reverse_proxy 127.0.0.1:8000
}

# MCP Memory Server endpoint (IP:9002)
# Routes /mcp/* to MCP Memory Server (9002)
157.180.73.53:9002 {
    encode gzip
    reverse_proxy /mcp/* 127.0.0.1:9002
    reverse_proxy 127.0.0.1:8000
}
```

---

## Deployment Steps

### 1. Fix Caddy Routing (Using sed, No nano)

```bash
cd /opt/l9 && \
# 1) Backup Caddyfile
sudo cp /etc/caddy/Caddyfile /etc/caddy/Caddyfile.backup && \
# 2) Point /mcp/* at 127.0.0.1:9002 via sed (no nano)
sudo sed -i 's#reverse_proxy /mcp/\* 127\.0\.0\.1:[0-9]\+#reverse_proxy /mcp/* 127.0.0.1:9002#' /etc/caddy/Caddyfile && \
# 3) Sanity check the mcp block
grep -A3 '/mcp/' /etc/caddy/Caddyfile && \
# 4) Reload Caddy
sudo systemctl reload caddy && \
sudo systemctl status caddy --no-pager | head -20
```

### 2. Validate Configuration (Optional)

```bash
sudo caddy validate --config /etc/caddy/Caddyfile
```

### 3. Verify Routing

```bash
cd /opt/l9 && \
# Load MCP key into shell (from .env)
set -a && source .env && set +a && \
# Test MCP endpoint through Caddy 9001 → 9002
curl -vk "https://l9.quantumaipartners.com/mcp/tools" \
  -H "Authorization: Bearer ${MCP_API_KEYC:-$MCP_API_KEY_C}" || true

# Test health
curl https://l9.quantumaipartners.com/mcp/health
```

---

## Testing

### Test MCP Tools Endpoint

```bash
curl -H "Authorization: Bearer $MCP_API_KEY_C" \
  https://l9.quantumaipartners.com/mcp/tools
```

**Expected Response:**
```json
{
  "tools": [
    {
      "name": "save_memory",
      "description": "Save a memory to the database...",
      ...
    }
  ],
  "caller": "C"
}
```

### Test MCP Call Endpoint

```bash
curl -X POST \
  -H "Authorization: Bearer $MCP_API_KEY_C" \
  -H "Content-Type: application/json" \
  -d '{
    "tool_name": "search_memory",
    "arguments": {
      "query": "test",
      "user_id": "l9-shared",
      "top_k": 5
    }
  }' \
  https://l9.quantumaipartners.com/mcp/call
```

---

## Troubleshooting

### Route Not Working

```bash
# Check Caddy logs
sudo journalctl -u caddy -n 50

# Verify MCP server is running
sudo systemctl status l9-mcp
curl http://127.0.0.1:9002/health

# Test routing locally
curl -v http://127.0.0.1:9001/mcp/health
```

### SSL/TLS Issues

```bash
# Check Caddy cert status
sudo caddy list-certificates

# Force cert renewal (if needed)
sudo systemctl restart caddy
```

### 502 Bad Gateway

**Cause:** MCP server not running or not listening on port 9002

**Fix:**
```bash
# Check service status
sudo systemctl status l9-mcp

# Check port binding
sudo ss -tlnp | grep ':9002'

# Restart service
sudo systemctl restart l9-mcp
```

---

## Security Notes

1. **TLS Termination:** Caddy handles TLS, MCP server runs HTTP internally
2. **Port Binding:** MCP server binds to `127.0.0.1:9002` (localhost only)
3. **Authentication:** All MCP endpoints require `Authorization: Bearer <key>` header
4. **Rate Limiting:** MCP server enforces rate limits (60 req/min per IP)

---

## Related Documentation

- **MCP Server Deployment:** `mcp_memory/docs/L9-MCP-IMPL.md`
- **Caddy Config Guide:** `mcp_memory/deploy/CADDY_CONFIG.md`
- **VPS Deployment:** `mcp_memory/deploy/VPS_DEPLOYMENT_GUIDE.md`

---

**Last Updated:** 2026-01-09

