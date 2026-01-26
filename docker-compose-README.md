# Docker Compose Alignment Strategy

> **Version:** 1.0.0
> **Last Updated:** 2026-01-13
> **GMP:** GMP-68

## Overview

This document explains how L9 maintains **one `docker-compose.yml`** that works identically on:

- Local Mac development
- VPS production
- CI/CD pipelines

**Key principle:** Auto-detect execution context instead of maintaining divergent compose files.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    L9 Docker Stack                               │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│   ┌─────────────┐  ┌─────────────┐  ┌─────────────┐            │
│   │  l9-api     │  │ l9-postgres │  │  l9-redis   │            │
│   │  :8000      │  │  :5432      │  │  :6379      │            │
│   └─────────────┘  └─────────────┘  └─────────────┘            │
│                                                                  │
│   ┌─────────────┐  ┌─────────────┐  ┌─────────────┐            │
│   │  l9-neo4j   │  │ l9-grafana  │  │ l9-jaeger   │            │
│   │  :7474/7687 │  │  :3000      │  │  :16686     │            │
│   └─────────────┘  └─────────────┘  └─────────────┘            │
│                                                                  │
│   Internal Network: l9-network (Docker DNS enabled)             │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
        │
        │ Published Ports
        ▼
┌─────────────────────────────────────────────────────────────────┐
│  Host Machine (Mac / VPS)                                        │
│  127.0.0.1:8000, 127.0.0.1:5432, 127.0.0.1:6379, etc.           │
└─────────────────────────────────────────────────────────────────┘
```

---

## The Problem

Docker uses internal DNS for container-to-container communication:

- Inside Docker: `http://l9-api:8000` works
- From host: `http://l9-api:8000` **fails** (DNS cannot resolve)

This causes tests to fail when run from the host machine.

---

## The Solution: Auto-Detection

Instead of maintaining separate compose files, tests **auto-detect** their execution context:

```python
# tests/docker/conftest.py
def get_execution_context() -> Literal["docker", "host"]:
    """Detect if running inside Docker or on host machine."""
    if os.path.exists("/.dockerenv"):
        return "docker"
    try:
        socket.gethostbyname("l9-api")
        return "docker"
    except socket.gaierror:
        return "host"

def resolve_service_url(service_name: str, port: int) -> str:
    """Auto-resolve URL based on context."""
    context = get_execution_context()
    if context == "docker":
        return f"http://{service_name}:{port}"
    else:
        return f"http://127.0.0.1:{port}"
```

---

## Usage

### Running Tests from Host (Mac)

```bash
# No environment variables needed - auto-detects localhost
pytest tests/docker/test_stack_smoke.py -v

# Or with manual override
API_BASE_URL=http://127.0.0.1:8000 pytest tests/docker/test_stack_smoke.py -v
```

### Running Tests Inside Container

```bash
# From inside l9-api container - auto-detects Docker DNS
docker exec -it l9-api pytest tests/docker/test_stack_smoke.py -v
```

### VPS Production

```bash
# Same command works - context auto-detected
docker exec -it l9-api pytest tests/docker/test_stack_smoke.py -v
```

---

## Quick Reference

### Start Docker Stack

```bash
# Local development
docker-compose up -d

# Check health
docker ps --format "table {{.Names}}\t{{.Status}}"
```

### Test API Connectivity

```bash
# From host
curl http://127.0.0.1:8000/health

# From inside container
docker exec l9-api curl http://l9-api:8000/health
```

### View Logs

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f l9-api
```

### Stop Stack

```bash
docker-compose down

# With volume cleanup
docker-compose down -v
```

---

## Service Ports

| Service       | Container Port | Host Port           | Docker DNS         |
| ------------- | -------------- | ------------------- | ------------------ |
| l9-api        | 8000           | 127.0.0.1:8000      | l9-api:8000        |
| l9-postgres   | 5432           | 127.0.0.1:5432      | l9-postgres:5432   |
| l9-redis      | 6379           | 127.0.0.1:6379      | l9-redis:6379      |
| l9-neo4j      | 7474, 7687     | 127.0.0.1:7474/7687 | l9-neo4j:7474/7687 |
| l9-grafana    | 3000           | 127.0.0.1:3000      | l9-grafana:3000    |
| l9-prometheus | 9090           | 127.0.0.1:9090      | l9-prometheus:9090 |
| l9-jaeger     | 16686          | 127.0.0.1:16686     | l9-jaeger:16686    |

---

## Environment Variables (Optional Overrides)

| Variable              | Purpose                 | Default       |
| --------------------- | ----------------------- | ------------- |
| `API_BASE_URL`        | Override API URL        | Auto-detected |
| `MEMORY_API_BASE_URL` | Override Memory API URL | Auto-detected |
| `L9_API_URL`          | Alternative override    | Auto-detected |

---

## Troubleshooting

### "nodename nor servname provided"

**Cause:** Running tests from host without auto-detection.

**Fix:** Ensure you're using the updated test files with `conftest.py`:

```bash
# Should work automatically now
pytest tests/docker/test_stack_smoke.py -v
```

### Container Not Healthy

**Check:** `docker ps` shows health status

**Fix:**

```bash
# Restart unhealthy container
docker-compose restart l9-api

# Check logs
docker-compose logs l9-api
```

### Port Already in Use

**Fix:**

```bash
# Find process using port
lsof -i :8000

# Kill it or use different port
docker-compose down
# Edit docker-compose.yml to use different host port
docker-compose up -d
```

---

## File Structure

```
/l9/
├── docker-compose.yml          # Shared config (DO NOT DUPLICATE)
├── docker-compose-README.md    # This file
├── .env                        # Environment variables (gitignored)
├── .env.example                # Template for .env
└── tests/
    └── docker/
        ├── conftest.py         # Auto-detection helpers
        ├── test_stack_smoke.py # Smoke tests
        └── __init__.py
```

---

## Key Invariants

1. **ONE docker-compose.yml** — Never create docker-compose.local.yml or docker-compose.prod.yml
2. **Auto-detection first** — Tests should work without environment variables
3. **Manual override available** — Environment variables can override auto-detection
4. **Same file everywhere** — Mac, VPS, CI all use the same compose file

---

## Related Documentation

- `README.md` — Project overview
- `Makefile` — Common commands (`make docker-up`, `make smoke`)
- `tests/docker/conftest.py` — Auto-detection implementation
