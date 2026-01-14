# L9 Canonical Deployment Method

> **Last Updated:** 2026-01-14

## ✅ Docker Compose (ONLY Supported Method)

L9 is deployed using **Docker Compose** exclusively. All services run as Docker containers.

### Deployment Command

```bash
cd /opt/l9
docker compose up -d
```

### Services

| Container | Port | Description |
|-----------|------|-------------|
| `l9-api` | 8000 | Main API server (includes MCP routes) |
| `l9-postgres` | 5432 | PostgreSQL + pgvector |
| `l9-redis` | 6379 | Redis cache |
| `l9-neo4j` | 7474, 7687 | Neo4j graph database |
| `l9-prometheus` | 9090 | Metrics |
| `l9-grafana` | 3000 | Dashboards |
| `l9-jaeger` | 16686 | Tracing |

### Health Check

```bash
curl http://127.0.0.1:8000/health
```

---

## ❌ Systemd Services (DEPRECATED)

The following systemd services are **NOT supported** and should be **removed** if found:

| Service | Status | Action |
|---------|--------|--------|
| `l9.service` | DEPRECATED | `sudo systemctl stop l9 && sudo systemctl disable l9` |
| `l9-mcp.service` | DEPRECATED | `sudo systemctl stop l9-mcp && sudo systemctl disable l9-mcp` |
| `l9-agent.service` | DEPRECATED | `sudo systemctl stop l9-agent && sudo systemctl disable l9-agent` |

### Cleanup Commands

If you find these services running on VPS:

```bash
# Stop and disable all deprecated systemd services
sudo systemctl stop l9.service l9-mcp.service l9-agent.service 2>/dev/null
sudo systemctl disable l9.service l9-mcp.service l9-agent.service 2>/dev/null

# Remove service files
sudo rm -f /etc/systemd/system/l9.service
sudo rm -f /etc/systemd/system/l9-mcp.service
sudo rm -f /etc/systemd/system/l9-agent.service
sudo systemctl daemon-reload

# Restart Docker services
cd /opt/l9 && docker compose up -d
```

---

## Why Docker Only?

1. **Consistency**: Same environment locally and on VPS
2. **Networking**: Docker Compose handles service discovery
3. **Isolation**: Each service in its own container
4. **Updates**: `docker compose up -d --build` for atomic updates
5. **Logs**: `docker logs l9-api -f` for unified logging

---

## Deployment Script

Use the 10X deploy script for full deployment:

```bash
./scripts/deployment/10X_Deploy_Script.sh "your commit message"
```

This handles:
- Git commit and push
- SSH to VPS
- Git pull
- Docker rebuild
- Health checks
