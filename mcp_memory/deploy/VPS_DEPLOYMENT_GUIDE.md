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

**Git Hygiene Protocol (CRITICAL):**

```bash
# On local machine (MacBook)
cd /Users/ib-mac/Projects/L9
git add .
git commit -m "Your commit message"
git push origin main  # Push latest code

# On VPS
ssh root@157.180.73.53
cd /opt/l9

# ⚠️ WARNING: This discards any local VPS changes
# Only run after all changes are committed and pushed from local
git fetch origin
git reset --hard origin/main
```

**Before `git reset --hard`:**
- ✅ All changes committed and pushed from local
- ✅ VPS `.env` backed up (if modified)
- ✅ Any VPS-only configs documented

**Reference:** See `docs/MCP-MEMORY-CAPSULE.md` for complete git sync protocol.

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

# Server Configuration (NOTE: MCP runs inside l9-api Docker container)
MCPMEMORYENABLED=true  # Enable MCP memory in l9-api
MCP_ENV=production
LOG_LEVEL=INFO
```

**Note:** MCP Memory runs **inside the `l9-api` Docker container** (port 8000), not as a separate systemd service. No separate MCP service installation needed.

---

## Step 4: Activate MCP Memory in l9-api

**MCP Memory is integrated into `l9-api` Docker container:**

```bash
# On VPS
cd /opt/l9

# Activate MCP Memory (sets MCPMEMORYENABLED=true and restarts container)
bash mcp_memory/deploy/scripts/init_mcp_memory.sh
```

**Verify:**
```bash
# Check container health
docker compose ps l9-api

# Check logs
docker compose logs -f l9-api | grep -i "Memory Substrate Service"

# Test health endpoint
curl http://127.0.0.1:8000/health
```

---

## Step 5: Configure Caddy Routing

**File:** `/etc/caddy/Caddyfile`

**UNIFIED ARCHITECTURE:** All traffic routes to `l9-api` on port 8000. No separate MCP service.

```caddyfile
# L9 Main API (domain-based)
l9.quantumaipartners.com {
    encode gzip
    reverse_proxy 127.0.0.1:8000
}

# Cursor MCP endpoint (IP:9001 - alternate HTTPS front door)
# Routes ALL traffic to unified l9-api (8000)
157.180.73.53:9001 {
    encode gzip
    reverse_proxy 127.0.0.1:8000
}
```

**Key Points:**
- ✅ **No `/mcp/*` special routing** — All traffic goes to 8000
- ✅ **No port 9002** — Deprecated, never deployed
- ✅ **Unified backend** — Single `l9-api` container handles everything

**Reload Caddy:**
```bash
sudo systemctl reload caddy
```

**Reference:** See `mcp_memory/deploy/CADDY_CONFIG.md` for complete Caddy configuration.

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

