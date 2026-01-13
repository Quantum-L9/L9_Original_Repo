# L9 MCP Memory Server Implementation Guide

**Version:** 1.0.0  
**Date:** 2026-01-09  
**Status:** Active

---

## Overview

The L9 MCP Memory Server provides a dedicated Model Context Protocol (MCP) interface for Cursor IDE, enabling structured memory operations through OpenAI embeddings and pgvector semantic search.

**Architecture:**
- **Protocol:** MCP (Model Context Protocol)
- **Backend:** FastAPI (Python)
- **Database:** PostgreSQL + pgvector (unified L9 substrate)
- **Deployment:** Systemd service (not Docker)
- **Port:** 9002 (internal), 9001 (Caddy reverse proxy)

---

## How to Enable on VPS

### Prerequisites

- VPS running L9 stack (PostgreSQL, Redis, etc.)
- Python 3.11+ with virtual environment at `/opt/l9/venv`
- Caddy reverse proxy configured
- Environment variables set in `/opt/l9/.env`

### Step 1: Verify Environment Variables

**File:** `/opt/l9/.env`

Ensure these are set:
```bash
# MCP Server Configuration
MCP_HOST=127.0.0.1
MCP_PORT=9002
MCP_ENV=production

# API Keys (at least one required)
MCP_API_KEY_L=...  # L-CTO API key (required)
MCP_API_KEY_C=...  # Cursor IDE API key (required)

# Legacy fallbacks (optional)
MCP_API_KEY=...  # Shared fallback
MCPL9MEMORYKEY=...  # Legacy alias

# Database
MEMORY_DSN=postgresql://postgres:password@localhost:5432/l9_memory

# OpenAI
OPENAI_API_KEY=...
OPENAI_EMBED_MODEL=text-embedding-3-small
```

### Step 2: Install Systemd Service

```bash
cd /opt/l9 && \
# Install and start l9-mcp systemd unit
sudo cp /opt/l9/mcp_memory/deploy/systemd/l9-mcp.service /etc/systemd/system/l9-mcp.service && \
sudo systemctl daemon-reload && \
sudo systemctl enable l9-mcp && \
sudo systemctl start l9-mcp && \
# Verify service and port 9002
sudo systemctl status l9-mcp --no-pager | head -20 && \
sudo ss -tlnp | grep ':9002' || echo 'ERROR: 9002 not listening'
```

### Step 3: Verify Service Status

```bash
# Check service status
sudo systemctl status l9-mcp --no-pager | head -20

# Check if port 9002 is listening
sudo ss -tlnp | grep ':9002'

# View logs
sudo journalctl -u l9-mcp -f
```

### Step 4: Fix Caddy Routing

**File:** `/etc/caddy/Caddyfile`

Update Caddy to route `/mcp/*` to `127.0.0.1:9002`:

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

### Step 5: Test Health Endpoint

```bash
# Test local health check
curl http://127.0.0.1:9002/health

# Test via Caddy (port 9001)
curl http://127.0.0.1:9001/mcp/health

# Test via domain (HTTPS)
curl https://l9.quantumaipartners.com/mcp/health
```

### Step 6: Test MCP Tools Endpoint

```bash
cd /opt/l9 && \
# Load MCP key into shell (from .env)
set -a && source .env && set +a && \
# Hit MCP tools endpoint through Caddy 9001 → 9002
curl -vk "https://l9.quantumaipartners.com/mcp/tools" \
  -H "Authorization: Bearer ${MCP_API_KEYC:-$MCP_API_KEY_C}" || true
```

---

## Caddy Configuration

**File:** `/etc/caddy/Caddyfile`

### IP-Based Routing (157.180.73.53:9001)

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

### Domain-Based Routing (l9.quantumaipartners.com)

```caddyfile
l9.quantumaipartners.com {
    encode gzip

    # Core L9 API routes
    reverse_proxy /health 127.0.0.1:8000
    reverse_proxy /docs* 127.0.0.1:8000
    reverse_proxy /memory* 127.0.0.1:8000
    
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

**After updating Caddyfile:**
```bash
# Validate config
sudo caddy validate --config /etc/caddy/Caddyfile

# Reload Caddy
sudo systemctl reload caddy
```

---

## Troubleshooting

### Service Won't Start

```bash
# Check logs
sudo journalctl -u l9-mcp -n 50

# Common issues:
# - Missing environment variables → Check /opt/l9/.env
# - Database connection failed → Check MEMORY_DSN
# - Port already in use → Check if another process on 9002
```

### Port Not Listening

```bash
# Check if service is running
sudo systemctl status l9-mcp

# Check if port is bound
sudo ss -tlnp | grep ':9002'

# Check firewall
sudo ufw status | grep 9002
```

### Caddy Routing Not Working

```bash
# Check Caddy logs
sudo journalctl -u caddy -n 50

# Verify Caddyfile syntax
sudo caddy validate --config /etc/caddy/Caddyfile

# Test routing locally
curl -v http://127.0.0.1:9001/mcp/health
```

### API Key Authentication Fails

```bash
# Verify API keys are set
grep MCP_API_KEY /opt/l9/.env

# Test with correct key
curl -H "Authorization: Bearer $MCP_API_KEY_C" \
  https://l9.quantumaipartners.com/mcp/tools

# Check service logs for auth errors
sudo journalctl -u l9-mcp | grep -i "auth\|key"
```

---

## Service Management

### Start/Stop/Restart

```bash
# Start service
sudo systemctl start l9-mcp

# Stop service
sudo systemctl stop l9-mcp

# Restart service
sudo systemctl restart l9-mcp

# Reload config (if .env changed)
sudo systemctl daemon-reload
sudo systemctl restart l9-mcp
```

### View Logs

```bash
# Follow logs in real-time
sudo journalctl -u l9-mcp -f

# View last 100 lines
sudo journalctl -u l9-mcp -n 100

# View logs since boot
sudo journalctl -u l9-mcp --since boot
```

### Check Health

```bash
# Health endpoint
curl http://127.0.0.1:9002/health

# MCP tools endpoint
curl -H "Authorization: Bearer $MCP_API_KEY_C" \
  http://127.0.0.1:9002/mcp/tools
```

---

## Security Considerations

1. **API Keys:** Store in `/opt/l9/.env` (not in code)
2. **Port Binding:** MCP server binds to `127.0.0.1` (localhost only)
3. **Caddy Reverse Proxy:** Handles TLS termination and external access
4. **Rate Limiting:** In-memory rate limiting (60 req/min per IP)
5. **Brute Force Protection:** Blocks IPs after 5 failed auth attempts

---

## Performance Tuning

### Rate Limits

**File:** `mcp_memory/src/main.py`

```python
RATE_LIMIT_REQUESTS = 60  # Max requests per window
RATE_LIMIT_WINDOW = 60  # Window in seconds (1 minute)
```

### Database Connection Pool

**File:** `mcp_memory/src/db.py`

Adjust connection pool size based on load.

### Vector Search Parameters

**File:** `mcp_memory/src/config.py`

```python
VECTOR_SEARCH_THRESHOLD: float = 0.7
VECTOR_SEARCH_TOP_K: int = 10
HNSW_EF_SEARCH: int = 40
```

---

## Monitoring

### Health Checks

```bash
# Local health check
curl http://127.0.0.1:9002/health

# Via Caddy
curl https://l9.quantumaipartners.com/mcp/health
```

### Metrics

- Request count per IP (in-memory)
- Failed auth attempts (in-memory)
- Database connection pool status
- Vector search performance

---

## Related Documentation

- **Deployment Guide:** `mcp_memory/deploy/VPS_DEPLOYMENT_GUIDE.md`
- **Caddy Config:** `mcp_memory/deploy/CADDY_CONFIG.md`
- **Architecture:** `mcp_memory/README.md`
- **Governance Spec:** `mcp_memory/memory-setup-instructions.md`

---

**Last Updated:** 2026-01-09

