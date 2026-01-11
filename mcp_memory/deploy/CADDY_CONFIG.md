# Caddy Configuration for MCP Memory Server

**Purpose:** Configure Caddy reverse proxy to route MCP endpoints to the MCP Memory Server

**File Location:** `/etc/caddy/Caddyfile` (on VPS)

---

## Current Configuration (from MRI)

The VPS Caddyfile currently has:

```caddyfile
# Memory API endpoint (IP:9001)
# Routes /memory/* to L9 Memory API (8000)
157.180.73.53:9001 {
    encode gzip
    
    # L9 Memory API routes → port 8000
    reverse_proxy /memory* 127.0.0.1:8000
    
    # Default to l9-api → port 8000
    reverse_proxy 127.0.0.1:8000
}

# MCP Memory Server endpoint (IP:9002)
# Routes /mcp/* to MCP Memory Server (9002)
157.180.73.53:9002 {
    encode gzip
    
    # MCP Memory Server routes → port 9002
    reverse_proxy /mcp/* 127.0.0.1:9002
    
    # Default to l9-api → port 8000
    reverse_proxy 127.0.0.1:8000
}
```

**Port Assignment:**
- **Port 9001** = L9 Memory API (via l9-api:8000)
- **Port 9002** = MCP Memory Server (standalone service)

---

## Required Updates

### 1. Update IP-Based Routing

**Port 9001 = Memory API, Port 9002 = MCP Server:**

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

### 2. Add Domain-Based Routing (l9.quantumaipartners.com)

**Add MCP routes to domain config:**

```caddyfile
l9.quantumaipartners.com {
    encode gzip

    # Core L9 API routes
    reverse_proxy /health 127.0.0.1:8000
    reverse_proxy /docs* 127.0.0.1:8000
    reverse_proxy /openapi.json 127.0.0.1:8000
    reverse_proxy /memory* 127.0.0.1:8000
    reverse_proxy /twilio* 127.0.0.1:8000
    reverse_proxy /waba* 127.0.0.1:8000
    reverse_proxy /slack/* 127.0.0.1:8000
    
    # MCP Memory Server - protocol endpoints
    handle /mcp/* {
        reverse_proxy 127.0.0.1:9002
    }
    
    # MCP Memory Server - direct memory API (backward compatibility)
    handle /api/v1/memory/* {
        reverse_proxy 127.0.0.1:9002
    }
    
    # Default to L9 API
    reverse_proxy 127.0.0.1:8000
}
```

---

## Deployment Steps

### On VPS:

```bash
# 1. Edit Caddyfile
sudo nano /etc/caddy/Caddyfile

# 2. Update comments (port 9002 → 9001)
# 3. Add domain routing for /mcp/* and /api/v1/memory/*

# 4. Validate config
sudo caddy validate --config /etc/caddy/Caddyfile

# 5. Reload Caddy
sudo systemctl reload caddy

# 6. Verify routing
curl -v https://l9.quantumaipartners.com/mcp/tools \
  -H "Authorization: Bearer $MCP_API_KEY_C"
```

---

## Routing Priority

Caddy processes routes in order:

1. **Specific paths first** (`/mcp/*`, `/api/v1/memory/*`)
2. **Then default** (everything else → l9-api:8000)

This ensures MCP endpoints are routed correctly before falling back to L9 API.

---

## Testing

### Test IP-based routing (157.180.73.53:9001):

```bash
curl http://157.180.73.53:9001/health
curl -H "Authorization: Bearer $MCP_API_KEY_C" \
  http://157.180.73.53:9001/mcp/tools
```

### Test domain-based routing (l9.quantumaipartners.com):

```bash
curl https://l9.quantumaipartners.com/health
curl -H "Authorization: Bearer $MCP_API_KEY_C" \
  https://l9.quantumaipartners.com/mcp/tools
```

---

## Troubleshooting

### Route Not Working

```bash
# Check Caddy logs
sudo journalctl -u caddy -n 50

# Verify MCP server is running
sudo systemctl status l9-mcp
curl http://127.0.0.1:9001/health
```

### SSL/TLS Issues

```bash
# Check Caddy cert status
sudo caddy list-certificates

# Force cert renewal (if needed)
sudo systemctl restart caddy
```

---

**Last Updated:** 2026-01-09

