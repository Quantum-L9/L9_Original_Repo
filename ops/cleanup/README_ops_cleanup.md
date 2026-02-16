# ops/cleanup/ — L9 Disk & Memory Substrate Recovery Tools

> **Purpose:** Automated cleanup and health verification for C1/VPS when disk exhaustion
> causes Postgres crash-loops, DNS resolution failures, and cascading L9 API/MCP memory outages.
>
> **Risk Tier:** T2 (reversible ops actions, no protected surface changes)

---

## Problem This Solves

When `/dev/sda1` reaches 100%, the following cascade occurs:

```
Disk 100% → Postgres cannot write WAL → crash-loop (Restarting)
         → Docker DNS fails to resolve "l9-postgres"
         → API gets [Errno -3] Temporary failure in name resolution
         → memory_system.init FAILED
         → Agent Executor cannot initialize
         → Application startup failed
         → MCP memory reports unhealthy (HTTP 500 + API timeout)
```

These scripts break the cascade by freeing disk, restarting substrates in order, and verifying recovery.

---

## Scripts

| Script | Purpose | Destructive? |
|--------|---------|--------------|
| `l9_cleanup_disk_and_memory.sh` | Free disk + restart substrates + verify | Yes (deletes logs/temp, prunes Docker) |
| `l9_check_memory_health.sh` | Read-only health probe of all substrates | No |
| `l9_rotate_postgres_logs.sh` | Compress/rotate Postgres logs + WAL check | Yes (truncates/compresses logs) |

---

## Quick Start (Emergency: Disk 100%, API Down)

```bash
# SSH into C1
ssh c1

# 1. Preview what will be cleaned (no changes)
sudo bash /opt/l9/ops/cleanup/l9_cleanup_disk_and_memory.sh --dry-run

# 2. Execute cleanup with confirmation prompt
sudo bash /opt/l9/ops/cleanup/l9_cleanup_disk_and_memory.sh

# 3. Verify all substrates recovered
bash /opt/l9/ops/cleanup/l9_check_memory_health.sh
```

---

## Script Details

### l9_cleanup_disk_and_memory.sh

**Options:**

| Flag | Effect |
|------|--------|
| `--dry-run` | Show what would be cleaned, no deletions |
| `--yes` | Skip interactive confirmation (for automation/cron) |
| `--help` | Show usage |

**Environment Variables:**

| Variable | Default | Purpose |
|----------|---------|---------|
| `L9_ROOT` | `/opt/l9` | L9 installation directory |
| `L9_LOG_RETAIN` | `5` | Number of log files to keep per directory |
| `L9_LOG_MAX_AGE_DAYS` | `7` | Delete logs older than N days |
| `L9_ALLOW_CLEANUP` | `0` | Set to `1` to allow on non-C1 hosts |
| `L9_CLEANUP_CONFIRM` | unset | Set to `1` for non-interactive mode (same as `--yes`) |

**What it cleans (safe targets only):**

- `/opt/l9/logs/` — old `.log`, `.log.*`, `.log.gz` files
- `/opt/l9/tmp/`, `/opt/l9/cache/` — ephemeral scratch data
- `/tmp/l9-*` — temporary diagnostic files
- Docker: dangling images, stopped containers, build cache
- Docker container JSON logs > 100MB (truncated, not deleted)
- Old L9 images not currently running

**What it NEVER touches:**

- Postgres data volume (`postgres_data`)
- Neo4j data volume (`neo4j_data`)
- Redis data volume (`redis_data`)
- Grafana/Prometheus data volumes
- Running containers or their images
- `docker-compose.yml`, `kernel_loader.py`, `websocket_orchestrator.py`

**Restart sequence:**

1. Stop crash-looping Postgres → start fresh
2. Wait for `pg_isready` (max 60s)
3. Restart Neo4j if unhealthy
4. Restart L9 API → wait for HTTP 200 on `/health` (max 90s)
5. Restart MCP memory container

---

### l9_check_memory_health.sh

Read-only probe. Checks:

- Container running states for: `l9-postgres`, `l9-neo4j`, `l9-redis`, `l9-l9-api-1`, `l9-l9-mcp-memory-1`
- `pg_isready` + `SELECT 1` query
- Neo4j HTTP endpoint
- Redis `PING` → `PONG`
- API `/health` and `/health/services` endpoints
- MCP memory `/health` endpoint
- `MEMORY_DSN` connection from inside the API container (asyncpg)

**Exit codes:**

- `0` — all substrates healthy
- `1` — at least one substrate unhealthy

**Structured output (for automation):**

```
L9_HEALTH_FAILURES=0
```

---

### l9_rotate_postgres_logs.sh

```bash
# Preview
sudo bash /opt/l9/ops/cleanup/l9_rotate_postgres_logs.sh --dry-run

# Execute
sudo bash /opt/l9/ops/cleanup/l9_rotate_postgres_logs.sh
```

**What it does:**

1. Truncates Postgres Docker JSON log if > 50MB
2. Compresses Postgres internal logs older than 14 days
3. Keeps last 7 compressed logs, deletes the rest
4. Checks WAL size; runs `CHECKPOINT` if > 2GB

**Environment Variables:**

| Variable | Default | Purpose |
|----------|---------|---------|
| `L9_PG_LOG_RETAIN` | `7` | Compressed log files to keep |
| `L9_PG_LOG_MAX_AGE` | `14` | Days before compressing |

---

## Preventive: Cron Setup (Optional)

To prevent future disk exhaustion, add to C1 crontab:

```bash
# Weekly cleanup (Sundays 3 AM UTC), auto-confirmed
0 3 * * 0 L9_ROOT=/opt/l9 /opt/l9/ops/cleanup/l9_cleanup_disk_and_memory.sh --yes >> /opt/l9/logs/cleanup.log 2>&1

# Daily Postgres log rotation (2 AM UTC)
0 2 * * * /opt/l9/ops/cleanup/l9_rotate_postgres_logs.sh >> /opt/l9/logs/pg_rotate.log 2>&1

# Hourly health check (log only)
0 * * * * /opt/l9/ops/cleanup/l9_check_memory_health.sh >> /opt/l9/logs/health_check.log 2>&1
```

---

## Cursor Deployment Flow

### Branch
```
feature/l9-disk-memory-cleanup
```

### New files to add
```
ops/cleanup/l9_cleanup_disk_and_memory.sh    (chmod +x)
ops/cleanup/l9_check_memory_health.sh        (chmod +x)
ops/cleanup/l9_rotate_postgres_logs.sh       (chmod +x)
ops/cleanup/README.md
```

### Pre-commit validation
```bash
# Lint all shell scripts
shellcheck ops/cleanup/*.sh

# Verify no protected surfaces modified
git diff --name-only | grep -E "(docker-compose|kernel_loader|websocket_orchestrator)" && echo "ABORT: protected file touched" && exit 1
```

### Deploy to C1
```bash
# Copy to C1
scp -r ops/cleanup/ c1:/opt/l9/ops/cleanup/

# Set permissions
ssh c1 'chmod +x /opt/l9/ops/cleanup/*.sh'

# Verify
ssh c1 'bash /opt/l9/ops/cleanup/l9_check_memory_health.sh'
```

### PR metadata
- **Title:** `ops: add disk cleanup and memory substrate health scripts`
- **Labels:** `ops`, `T2-reversible`, `infra`
- **Reviewer:** L=CTO
- **Risk tier:** T2

---

## Invariants Respected

- ❌ No changes to `docker-compose.yml`
- ❌ No changes to `kernel_loader.py`
- ❌ No changes to `websocket_orchestrator.py`
- ❌ No changes to memory substrates (Postgres/Redis/Neo4j schemas)
- ❌ No changes to authority model (L/Cursor/Igor)
- ❌ No changes to PacketEnvelope or MemorySubstrateService
- ✅ Ops-only scripts in `ops/cleanup/` directory
- ✅ All scripts are additive (new files only)
