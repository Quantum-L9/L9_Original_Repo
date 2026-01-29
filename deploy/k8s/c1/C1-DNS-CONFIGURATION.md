# C1 DNS Configuration

**Date:** 2026-01-28
**Status:** Active

---

## DNS Records (Cloudflare)

| Type | Name | Content | Proxy Status | Purpose |
|------|------|---------|--------------|---------|
| A | `l9` | `157.180.73.53` | Proxied (orange) | Legacy L9 server |
| A | `mcp` | `46.62.243.82` | DNS only (gray) | **C1 MCP Memory Server** |

---

## Resulting Endpoints

| Subdomain | Resolves To | Server |
|-----------|-------------|--------|
| `l9.quantumaipartners.com` | Cloudflare → `157.180.73.53` | Old L9 VPS |
| `mcp.quantumaipartners.com` | Direct → `46.62.243.82` | **C1 Hetzner** |

---

## C1 Services (via mcp.quantumaipartners.com)

| Service | Port | Full URL |
|---------|------|----------|
| L9 API | 30080 | `http://mcp.quantumaipartners.com:30080` |
| MCP Memory | 30902 | `http://mcp.quantumaipartners.com:30902` |
| PostgreSQL | 30432 | `mcp.quantumaipartners.com:30432` |
| Neo4j HTTP | 30474 | `http://mcp.quantumaipartners.com:30474` |
| Neo4j Bolt | 30687 | `bolt://mcp.quantumaipartners.com:30687` |
| Redis | 30379 | `mcp.quantumaipartners.com:30379` |

---

## Why "DNS only" for MCP?

| Setting | Behavior | Used For |
|---------|----------|----------|
| **Proxied** (orange cloud) | Traffic → Cloudflare → Server | Web apps needing DDoS protection |
| **DNS only** (gray cloud) | Traffic → Server directly | API/MCP traffic, lower latency, no WAF |

MCP uses "DNS only" because:
1. **No WAF interference** — Cloudflare WAF was blocking Cursor with error 1010
2. **Lower latency** — Direct connection, no proxy hop
3. **Non-HTTP ports** — Cloudflare proxy only works for HTTP/HTTPS on standard ports

---

## Client Configuration

### Environment Variables

```bash
# For Cursor Memory Client
export L9_API_URL=http://mcp.quantumaipartners.com:30080

# For MCP direct access
export C1_MCP_URL=http://mcp.quantumaipartners.com:30902

# Database connections
export C1_POSTGRES_DSN=postgresql://l9_user:PASSWORD@mcp.quantumaipartners.com:30432/l9_memory
export C1_NEO4J_URL=bolt://mcp.quantumaipartners.com:30687
export C1_REDIS_URL=redis://mcp.quantumaipartners.com:30379
```

### cursor_memory_client.py

Update default URL to use C1:
```python
L9_API_URL = os.getenv("L9_API_URL", "http://mcp.quantumaipartners.com:30080")
```

---

## Verification

```bash
# Test DNS resolution
nslookup mcp.quantumaipartners.com
# Should return: 46.62.243.82

# Test MCP health
curl http://mcp.quantumaipartners.com:30080/health

# Test MCP Memory
curl http://mcp.quantumaipartners.com:30902/health
```

---

## History

| Date | Change | Reason |
|------|--------|--------|
| 2026-01-28 | Created `mcp` A record → C1 | Cursor getting Cloudflare 1010 errors on `l9` subdomain |
| 2026-01-28 | Set to "DNS only" | Bypass Cloudflare WAF for API traffic |

---

## Related Files

- `agents/cursor/cursor_memory_client.py` — Cursor memory client
- `deploy/k8s/c1/docker-compose.yml` — C1 service definitions
- `.cursor/rules/03-mcp-memory.mdc` — MCP memory rules
