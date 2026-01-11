# L9 MCP Memory Server - VPS Deployment Guide

**Date:** 2026-01-09  
**Status:** Production-ready deployment instructions

---

## Prerequisites

- VPS running at `157.180.73.53`
- PostgreSQL with L9 memory substrate (migrations 0001-0013 applied)
- Caddy reverse proxy configured
- Python 3.11+ with virtual environment
- Environment variables configured

---

## Step 1: Deploy Code to VPS

```bash
# On local machine
cd /Users/ib-mac/Projects/L9
git push origin main  # Push latest code

# On VPS
ssh root@157.180.73.53
cd /opt/l9
git pull origin main
```

---

## Step 2: Apply Database Migration

**Migration 0013** adds `caller` and `project_id` to `tool_audit_log`:

```bash
# On VPS
cd /opt/l9
source venv/bin/activate
psql $MEMORY_DSN -f migrations/0013_mcp_audit_columns.sql
```

**Verify:**
```sql
\d tool_audit_log
-- Should show caller and project_id columns
```

---

## Step 3: Configure Environment Variables

**File:** `/opt/l9/.env`

```bash
# MCP Memory Server
MCP_API_KEY_L=...  # L-CTO API key (for L kernel)
MCP_API_KEY_C=...  # Cursor IDE API key (for Cursor)
L_CTO_USER_ID=l9-shared  # Shared user ID
OPENAI_API_KEY=...  # For embeddings
MEMORY_DSN=postgresql://postgres:...@localhost:5432/l9_memory

# Server Configuration
MCP_HOST=0.0.0.0
MCP_PORT=9001
MCP_ENV=production
LOG_LEVEL=INFO
```

---

## Step 4: Install Systemd Service

```bash
# On VPS
cd /opt/l9
sudo cp mcp_memory/deploy/systemd/l9-mcp.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable l9-mcp
sudo systemctl start l9-mcp
```

**Verify service is running:**
```bash
sudo systemctl status l9-mcp
sudo journalctl -u l9-mcp -f  # View logs
```

---

## Step 5: Configure Caddy Routing

**File:** `/etc/caddy/Caddyfile`

### Update IP-based routing (157.180.73.53:9001):

```caddyfile
# Cursor MCP endpoint (IP:9001)
# Routes /mcp/* to MCP Memory Server (9001)
157.180.73.53:9001 {
    encode gzip
    
    # MCP Memory Server routes → port 9001
    reverse_proxy /mcp/* 127.0.0.1:9001
    
    # Default to l9-api → port 8000
    reverse_proxy 127.0.0.1:8000
}
```

### Add to domain routing (l9.quantumaipartners.com):

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
        reverse_proxy 127.0.0.1:9001
    }
    
    # MCP Memory Server - direct memory API (backward compatibility)
    handle /api/v1/memory/* {
        reverse_proxy 127.0.0.1:9001
    }
    
    # Default to L9 API
    reverse_proxy 127.0.0.1:8000
}
```

**Reload Caddy:**
```bash
sudo systemctl reload caddy
```

---

## Step 6: Verify Deployment

### Health Check

```bash
# From anywhere (via Cloudflare)
curl https://l9.quantumaipartners.com/health

# From VPS directly
curl http://127.0.0.1:9001/health
```

### MCP Tools Discovery

```bash
curl -H "Authorization: Bearer $MCP_API_KEY_C" \
  https://l9.quantumaipartners.com/mcp/tools
```

### Test Memory Operations

```bash
# Save memory
curl -X POST https://l9.quantumaipartners.com/mcp/call \
  -H "Authorization: Bearer $MCP_API_KEY_C" \
  -H "Content-Type: application/json" \
  -d '{
    "tool_name": "save_memory",
    "arguments": {
      "content": "Test memory via MCP",
      "kind": "preference",
      "scope": "developer",
      "duration": "long",
      "user_id": "l9-shared"
    }
  }'

# Search memory
curl -X POST https://l9.quantumaipartners.com/mcp/call \
  -H "Authorization: Bearer $MCP_API_KEY_C" \
  -H "Content-Type: application/json" \
  -d '{
    "tool_name": "search_memory",
    "arguments": {
      "query": "test",
      "user_id": "l9-shared",
      "scopes": ["developer", "global"],
      "top_k": 5
    }
  }'
```

---

## Troubleshooting

### Service Not Starting

```bash
# Check logs
sudo journalctl -u l9-mcp -n 50

# Common issues:
# - Missing environment variables → Check .env file
# - Database connection failed → Verify MEMORY_DSN
# - Port already in use → Check: sudo lsof -i :9001
```

### Caddy Routing Not Working

```bash
# Test Caddy config
sudo caddy validate --config /etc/caddy/Caddyfile

# Check Caddy logs
sudo journalctl -u caddy -n 50

# Verify routing
curl -v https://l9.quantumaipartners.com/mcp/tools \
  -H "Authorization: Bearer $MCP_API_KEY_C"
```

### Database Migration Issues

```bash
# Check if migration already applied
psql $MEMORY_DSN -c "\d tool_audit_log"

# If columns exist, migration already applied (idempotent)
# If not, apply:
psql $MEMORY_DSN -f migrations/0013_mcp_audit_columns.sql
```

---

## Rollback

If deployment fails:

```bash
# Stop service
sudo systemctl stop l9-mcp
sudo systemctl disable l9-mcp

# Revert Caddy config
sudo systemctl reload caddy

# Memory client will fall back to REST API (if still available)
```

---

## Post-Deployment Checklist

- [ ] Systemd service `l9-mcp` is running
- [ ] Health endpoint responds: `curl https://l9.quantumaipartners.com/health`
- [ ] MCP tools discovery works: `curl -H "Authorization: Bearer $MCP_API_KEY_C" https://l9.quantumaipartners.com/mcp/tools`
- [ ] Save memory works via MCP
- [ ] Search memory works via MCP
- [ ] Audit log captures caller and project_id
- [ ] Caddy routes /mcp/* correctly
- [ ] Cursor mcp.json configured with correct API key

---

**Last Updated:** 2026-01-09

