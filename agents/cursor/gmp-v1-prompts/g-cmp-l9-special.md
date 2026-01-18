# 🧠 G-CMP v2.0 — L9 DEVOPS SPECIALIZATION

**For:** VPS deployment, Docker fixes, FastAPI/PostgreSQL issues on L9 system
**Context:** Ubuntu VPS (157.180.73.53), L9 backend, Docker Compose, Caddy, PostgreSQL

---

## L9-SPECIFIC OVERRIDES

### Standard File Paths (Don't Guess)

```
/opt/l9/                          # Root project
├── docker/                        # Docker configs (Dockerfile, docker-compose.yml)
├── api/                           # FastAPI server (/opt/l9/api/server.py)
├── .env                           # Environment vars (SLACK_SIGNING_SECRET, etc.)
├── requirements.txt               # Python dependencies
└── logs/                          # Service logs
```

### Standard Services

```
l9-api       → FastAPI on 0.0.0.0:8000 (uvicorn)
l9-postgres  → PostgreSQL on 0.0.0.0:5432 (pgvector enabled)
l9-redis     → Redis on 0.0.0.0:6379
l9-neo4j     → Neo4j on 0.0.0.0:7474 (web) + 7687 (bolt)
```

### Docker Compose Commands (L9-specific)

```bash
# From /opt/l9:
cd /opt/l9

# View status
sudo docker compose ps

# View logs
sudo docker compose logs l9-api --tail 50
sudo docker compose logs l9-postgres --tail 50

# Restart service
sudo docker compose restart l9-api

# Full rebuild (clean)
sudo docker compose down && \
sudo docker image rm l9-api l9-postgres --force 2>/dev/null || true && \
sudo docker compose build --no-cache && \
sudo docker compose up -d

# Health check
curl -sS http://127.0.0.1:8000/health && echo ""
```

### Common L9 Errors & Patterns

| Error | Cause | Fix |
|-------|-------|-----|
| `NameError: name 'settings' undefined` | Code uses undefined variable | Replace with `_has_*` feature flags |
| `ERROR: unable to select packages: pgvector` | pgvector not in Alpine repos | Use `pgvector/pgvector:pg16` image instead |
| `psycopg error: connection refused` | PostgreSQL not ready | Add health check + sleep before app start |
| `curl: (7) Failed to connect to 127.0.0.1 port 8000` | App failed to start | Check logs: `docker logs l9-api` |
| `docker-compose.yml: version attribute is obsolete` | Old syntax | Remove `version: "3.8"` line from docker-compose.yml |

---

## L9 CONTEXT PROFILES

### PROFILE 1A: L9 SINGLE-FILE FIX (FastAPI Python)

**When:** Bug in `/opt/l9/api/server.py` or similar

```
MISSION OBJECTIVE:
Fix: [Error description with line number from server.py]
File: /opt/l9/api/server.py
Lines: [XXX-YYY]
Error Evidence: [Paste docker logs output showing error]

### L9 Context:
- Framework: FastAPI + Uvicorn
- Entry point: `uvicorn api.server:app --host 0.0.0.0 --port 8000`
- Feature flags pattern: _has_slack, _has_research, etc. (defined ~line 30-150)
- Forbidden: Core app structure, router includes, startup/shutdown hooks

### Analysis:
1. [ ] Searched for all instances of [undefined_reference]
   - Count: [X] occurrences
   - Lines: [List all]

2. [ ] Identified replacement strategy
   - Old pattern: [settings.slack_app_enabled]
   - New pattern: [_has_slack] (feature flag, defined line YYY)

3. [ ] Verified replacement exists
   - Location: Line [YYY]
   - Code: [Exact line from file]

### TODO Items:
1. [ ] Replace all `settings.slack_app_enabled` → `_has_slack`
   - Count: [X] replacements
   - Verification: `grep settings /opt/l9/api/server.py` returns 0

2. [ ] Add missing flag if needed
   - Code: `_has_mac_agent = os.getenv("MAC_AGENT_ENABLED", "false").lower() == "true"`
   - Location: Line ~165 (after LOCAL_DEV definition)

### Forbidden Changes:
- ❌ Refactor app initialization
- ❌ Change router includes
- ❌ Modify startup/shutdown hooks
- ❌ Add new dependencies
```

### PROFILE 1B: L9 DOCKER FIX (Dockerfile or docker-compose.yml)

**When:** Docker build fails or container won't start

```
MISSION OBJECTIVE:
Fix: [Docker error: e.g., "Dockerfile build fails on pgvector"]
System: Docker / Docker Compose
Symptom: [Full error message from build output]
Root Cause: [What's actually broken]

### L9 Context:
- Docker path: /opt/l9/docker/
- Compose file: /opt/l9/docker-compose.yml
- Dockerfiles: Dockerfile (api), Dockerfile.postgres, etc.
- Build command: `cd /opt/l9 && sudo docker compose build --no-cache`
- Compose networks: l9-network (host network sometimes used)

### Problem Analysis:
1. [ ] Read current Dockerfile.postgres (or target file)
   - Current approach: [Describe what it's trying to do]
   - Why it fails: [Root cause]

2. [ ] Identify correct fix
   - Option A: [Replace with pre-built image: pgvector/pgvector:pg16]
   - Option B: [Use different base image: postgres:16-bullseye]
   - Rationale: [Why this fixes it]

3. [ ] Verify docker-compose.yml references
   - Service name: l9-postgres
   - Build path: ./docker/Dockerfile.postgres (relative to docker-compose.yml)
   - No other references to change

### TODO Items:
1. [ ] Backup current file
   - Command: `cp /opt/l9/docker/Dockerfile.postgres /opt/l9/docker/Dockerfile.postgres.backup`

2. [ ] Replace Dockerfile.postgres with working version
   - New content: [Exact replacement code]
   - Verification: `cat /opt/l9/docker/Dockerfile.postgres`

3. [ ] Clean rebuild
   - Command: See L9 rebuild process above
   - Verify: `sudo docker compose ps` shows all services running

### Forbidden Changes:
- ❌ Change other Dockerfiles
- ❌ Modify service names in docker-compose.yml
- ❌ Change port mappings
- ❌ Add new services
```

### PROFILE 3A: L9 POSTGRESQL FIX

**When:** Database initialization, pgvector, migration issues

```
MISSION OBJECTIVE:
Fix: [PostgreSQL issue: e.g., "pgvector extension not loading"]
Database: PostgreSQL 16 + pgvector
Symptom: [Error from logs or health check]

### L9 Context:
- Docker container: l9-postgres
- Port: 5432 (only accessible from l9-api container)
- Credentials: POSTGRES_PASSWORD=${POSTGRES_PASSWORD} (from .env)
- pgvector: Must be enabled with `CREATE EXTENSION vector`
- Migrations: Run by Python ORM at startup

### Analysis:
1. [ ] Check PostgreSQL container status
   - Command: `sudo docker compose logs l9-postgres --tail 50`
   - Looking for: [Extension loading errors, init errors, etc.]

2. [ ] Verify Dockerfile.postgres
   - Must have: [pgvector pre-installed or compilable]
   - Pattern: [Base image must support vector extension]

3. [ ] Check initialization
   - SQL scripts: If custom init SQL needed, where stored?
   - ORM migrations: Python code should run `CREATE EXTENSION vector`

### TODO Items:
1. [ ] Fix Dockerfile.postgres (if applicable)
   - New base: pgvector/pgvector:pg16
   - ENVs: POSTGRES_PASSWORD, POSTGRES_USER, POSTGRES_DB

2. [ ] Verify extension is loaded
   - Test: `psql -U postgres -d l9_memory -c "SELECT * FROM pg_extension WHERE extname='vector'"`
   - Expect: vector extension listed

### Forbidden Changes:
- ❌ Change database credentials (use .env)
- ❌ Delete migration scripts
- ❌ Change port mappings
```

---

## L9 PHASE 0: BASELINE CONFIRMATION (CUSTOMIZED)

```markdown
## L9 BASELINE CHECKLIST

[ ] Docker daemon is running
    - Command: `sudo docker ps`
    - Status: ✓ (can list containers)

[ ] Project directory exists
    - Path: /opt/l9
    - Status: ✓ (files present)

[ ] Target file exists at exact path
    - Path: [/opt/l9/api/server.py or /opt/l9/docker/Dockerfile.postgres]
    - Size: [Confirm byte count matches expected]
    - Status: ✓

[ ] .env file has required variables
    - Command: `grep "SLACK_SIGNING_SECRET\|MAC_AGENT_ENABLED" /opt/l9/.env`
    - Count: [X] variables present
    - Status: ✓

[ ] Current error reproduces
    - Command: [How to trigger the error]
    - Output: [Shows error message]
    - Status: ✓

[ ] Feature flags are defined (if Python fix)
    - Grep: `grep "_has_slack\|_has_research" /opt/l9/api/server.py`
    - Count: [X] flags found
    - Location: [Line YYY]
    - Status: ✓

[ ] No existing "settings" object (if Python fix)
    - Command: `grep "^settings = \|^class Settings" /opt/l9/api/server.py`
    - Result: No matches (0)
    - Status: ✓
```

---

## L9 PHASE 1: IMPLEMENTATION (CUSTOMIZED)

### For Python Fixes

```bash
# Make change
sed -i 's/settings\.slack_app_enabled/_has_slack/g' /opt/l9/api/server.py

# Verify
grep -n "settings\." /opt/l9/api/server.py  # Should be 0 results
grep -n "_has_slack" /opt/l9/api/server.py  # Should show X results
```

### For Docker Fixes

```bash
# Backup
cp /opt/l9/docker/Dockerfile.postgres /opt/l9/docker/Dockerfile.postgres.backup

# Replace (use cat or echo)
cat > /opt/l9/docker/Dockerfile.postgres << 'EOF'
[Exact new content]
EOF

# Verify
cat /opt/l9/docker/Dockerfile.postgres
```

### For Multi-Container Changes

```bash
# Stop all containers
cd /opt/l9 && sudo docker compose down

# Clean old images
sudo docker image rm l9-api l9-postgres --force 2>/dev/null || true

# Rebuild and restart
sudo docker compose build --no-cache && \
sudo docker compose up -d && \
sleep 30

# Verify
curl -sS http://127.0.0.1:8000/health && echo ""
sudo docker compose ps
```

---

## L9 PHASE 4: VALIDATION (CUSTOMIZED)

### Health Check

```bash
# App health
curl -sS http://127.0.0.1:8000/health && echo ""

# PostgreSQL connectivity
sudo docker compose exec l9-api psql -h l9-postgres -U postgres -d l9_memory -c "SELECT 1"

# Redis connectivity
sudo docker compose exec l9-api redis-cli -h l9-redis ping

# Neo4j connectivity
curl -sS http://localhost:7474/browser/
```

### Container Logs Inspection

```bash
# Look for errors
sudo docker compose logs l9-api | grep -i "error\|warning\|critical"

# Look for startup messages
sudo docker compose logs l9-api | grep -i "started\|ready\|listening"

# Full context around error
sudo docker compose logs l9-api --tail 100 | grep -A 5 -B 5 "NameError"
```

### Regression Tests

```bash
# Original problem should be gone
curl -sS http://127.0.0.1:8000/health
# Expected: {"status": "ok"} (or similar)

# Services should be running
sudo docker compose ps
# Expected: All services showing "Up" status

# No docker errors
sudo docker compose logs | grep "ERROR" | wc -l
# Expected: 0 (or expected count if some warnings are normal)
```

---

## L9 PHASE 5: FINAL AUDIT (CUSTOMIZED)

### Checklist for L9

- [ ] All L9 feature flags are used consistently (_has_*, not settings.*)
- [ ] Docker image builds without warnings (or only expected warnings)
- [ ] All containers start and show healthy status
- [ ] Health check endpoint responds
- [ ] No breaking changes to router/startup order
- [ ] .env variables are optional (graceful defaults)
- [ ] Logs are clean (no orphaned errors)
- [ ] Ready for production VPS deployment

---

## L9 FINAL REPORT (CUSTOMIZED EXAMPLE)

```markdown
# EXECUTION REPORT — L9 API FIX

**Task:** Fix NameError on line 797 (undefined settings object)
**Status:** ✓ COMPLETE
**System:** L9 FastAPI on Ubuntu VPS

---

## Changes Summary

**File Modified:** `/opt/l9/api/server.py`

**Changes:**
1. Replaced all `settings.slack_app_enabled` with `_has_slack` (2 occurrences)
   - Lines: 797, 820
   
2. Replaced all `settings.mac_agent_enabled` with `_has_mac_agent` (1 occurrence)
   - Line: 825
   
3. Added `_has_mac_agent` feature flag definition
   - Line: 165
   - Pattern: Matches existing feature flags

**Total lines changed:** 3

---

## Verification

✓ Phase 0: All assumptions confirmed
- settings object: Not defined (0 results)
- _has_slack flag: Defined at line 28
- _has_mac_agent: Added at line 165
- File structure: Preserved

✓ Phase 4: Validation passed
- Health check: curl returns 200 ✓
- Logs: No NameError ✓
- Feature flags: All 6 _has_* flags present ✓

✓ Phase 5: No gaps found
- Architecture: Preserved ✓
- No scope creep: Confirmed ✓
- Ready for deployment: YES ✓

---

## Deployment Steps

1. Push file to VPS:
   ```bash
   scp /path/to/server.py admin@157.180.73.53:/opt/l9/api/server.py
   ```

2. Restart container:
   ```bash
   ssh admin@157.180.73.53
   cd /opt/l9 && sudo docker compose restart l9-api && sleep 10
   curl -sS http://127.0.0.1:8000/health && echo ""
   ```

3. Verify: Health endpoint returns OK

---

**Status:** READY FOR PRODUCTION ✓
```

---

## L9-SPECIFIC QUICK COMMANDS

```bash
# Status check (from VPS)
cd /opt/l9 && sudo docker compose ps && echo "---" && curl -sS http://127.0.0.1:8000/health

# View errors quickly
sudo docker compose logs l9-api 2>&1 | grep -i "error" | head -20

# Kill and rebuild (nuclear option)
cd /opt/l9 && sudo docker compose down && sudo docker system prune -f && sudo docker compose build --no-cache && sudo docker compose up -d

# Copy local file to VPS
scp ~/local/file.py admin@157.180.73.53:/opt/l9/path/file.py

# SSH and restart one service
ssh admin@157.180.73.53 "cd /opt/l9 && sudo docker compose restart l9-api"

# Monitor logs in real-time
ssh admin@157.180.73.53 "cd /opt/l9 && sudo docker compose logs -f l9-api"
```

---

## REMEMBER FOR L9

✓ Always work from `/opt/l9` directory on VPS
✓ Use `sudo docker compose` (lowercase "compose")
✓ Health check: `curl http://127.0.0.1:8000/health`
✓ Logs: `docker compose logs [service]`
✓ Feature flags pattern: `_has_*` (not `settings.*)
✓ Docker files in: `/opt/l9/docker/`
✓ Config in: `/opt/l9/.env`
✓ Code in: `/opt/l9/api/`, `/opt/l9/memory/`, etc.
✓ All services in one compose file (no multiple files)
✓ Network name: `l9-network` or `l9_l9-network` (depends on docker compose version)

---

**Version:** L9 Specialization v1.0
**Last Updated:** 2025-12-21
**Compatible with:** G-CMP v2.0
**Status:** Production Ready for L9 VPS