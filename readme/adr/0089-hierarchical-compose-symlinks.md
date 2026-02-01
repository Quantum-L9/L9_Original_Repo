# ADR-0089: Hierarchical Compose and C1 Symlinks

**Status:** Accepted  
**Date:** 2026-01-31  
**Source:** Perplexity PHASE 0 plan + GMP deploy-docker unification  

## Context

Multiple docker-compose and Dockerfile copies (root, deploy/docker-production, deploy/k8s/c1) caused drift, env var chaos, and build fragmentation. A single flat file did not distinguish dev vs prod behavior cleanly.

## Decision

**Adopt hierarchical compose (base + dev/prod overlays) and C1 symlinks.**

### 1. Root layout (single source of truth)

- **`docker-compose.yml`** — Base infrastructure only (PostgreSQL, Neo4j, Redis, Prometheus, Grafana, Jaeger). No application services.
- **`docker-compose.dev.yml`** — Development overlay: l9-api, l9-mcp-memory with hot-reload, volume mounts, debug ports.
- **`docker-compose.prod.yml`** — Production overlay: l9-bootstrap, l9-api, l9-mcp-memory, nginx; resource limits, no volume mounts.
- **`.env.template`** — Single source for all variables; copy to `.env` (dev) or `deploy/c1/.env.c1` (prod).
- **`Dockerfile`**, **`Dockerfile.mcp-memory`** — Canonical multi-stage builds (development + production targets) at repo root.

### 2. Usage

```bash
# Development (local)
docker compose -f docker-compose.yml -f docker-compose.dev.yml up

# Production (C1 or prod host)
docker compose -f docker-compose.yml -f docker-compose.prod.yml --env-file deploy/c1/.env.c1 up -d
```

### 3. C1 deployment (symlinks)

On C1 (`/opt/l9` or equivalent):

- **Symlink** `docker-compose.yml` and `docker-compose.prod.yml` to the repo versions (so `git pull` updates compose without copy/sync).
- **Secrets:** `.env.c1` (gitignored) on the server; never commit.
- **Wrapper:** `deploy/c1/deploy.sh` — runs `git pull`, then `docker compose -f docker-compose.yml -f docker-compose.prod.yml --env-file .env.c1 pull/up -d`.

### 4. Deploy folder

- **`deploy/`** may contain scripts, tools, manifests, docs. Canonical compose and Dockerfiles live at **repo root only**.
- **Removed:** `deploy/docker-production/` and compose/Dockerfile under `deploy/k8s/c1/` have been deleted; root `Dockerfile`, `Dockerfile.mcp-memory`, and hierarchical compose are canonical.

## Consequences

- **DRY:** One base compose; dev/prod differ only in overlay.
- **No drift:** C1 uses symlinks to repo; no copy/sync script.
- **CI:** Build from root `Dockerfile` and `Dockerfile.mcp-memory` (e.g. `deploy/ci/docker-build.yml`).

## References

- PHASE 0 plan: `current_work/01-31-2026/docker-compose-repair/PHASE 0_ PLAN - CRITICAL ISSUES & RECOMMENDATIONS.md`
- Learned lessons: ROOT docker-compose only (92-learned-lessons.mdc)
