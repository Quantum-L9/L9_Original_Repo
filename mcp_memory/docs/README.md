# MCP Memory Documentation

**Status:** ✅ Active — Production-ready

## Quick Links

| Document | Purpose |
|----------|---------|
| [CONFIG_REFERENCE.md](CONFIG_REFERENCE.md) | **Canonical** — Ports, env vars, architecture |
| [../QUICK_REFERENCE.md](../QUICK_REFERENCE.md) | Concise usage guide |
| [../deploy/VPS_DEPLOYMENT_GUIDE.md](../deploy/VPS_DEPLOYMENT_GUIDE.md) | Step-by-step VPS deployment |
| [../deploy/CADDY_CONFIG.md](../deploy/CADDY_CONFIG.md) | Caddy reverse proxy config |
| [../memory-setup-instructions.md](../memory-setup-instructions.md) | Governance specification |
| [../README.md](../README.md) | Main MCP Memory overview |

## Architecture at a Glance

```
Cursor IDE → HTTPS → Caddy (:443/:9001) → l9-api (:8000) → PostgreSQL
```

- **No standalone MCP server** — integrated into `l9-api` Docker container
- **Port 9002 deprecated** — never deployed, do not use
- **Unified substrate** — `packet_store` + `memory_embeddings` tables

## Key Facts

| Item | Value |
|------|-------|
| VPS IP | `157.180.73.53` |
| Domain | `l9.quantumaipartners.com` |
| API Port | `8000` (internal) |
| HTTPS Ports | `443` (domain), `9001` (IP) |
| Database | `l9_memory` on `l9-postgres` container |
| API Keys | `MCP_API_KEY_L` (L-CTO), `MCP_API_KEY_C` (Cursor) |

---

**Last Updated:** 2026-01-13
