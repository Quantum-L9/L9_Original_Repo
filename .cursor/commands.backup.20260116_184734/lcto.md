---
# === SUITE 6 CANONICAL HEADER ===
suite: "Cursor Governance Suite 6 (L9 + Suite 6)"
version: "8.2.0"
component_id: "CMD-LCTO-001"
component_name: "LCTO - Local CTO Startup"
layer: "commands"
domain: "infrastructure"
type: "slash_command"
status: "active"
created: "2025-12-01T00:00:00Z"
updated: "2026-01-06T00:00:00Z"
author: "Igor Beylin"
maintainer: "Igor Beylin"

# === GOVERNANCE METADATA ===
governance_level: "operational"
compliance_required: true
audit_trail: true
security_classification: "internal"

# === COMMAND METADATA ===
name: lcto
description: "L9 local development startup — full Docker stack + local dashboard UI + Mac Agent"
auto_chain: null
---

# === L9 LCTO: Local CTO Startup ===
# Cursor Slash Command: /lcto
# Version: 8.2.0 (Full Docker + Dashboard + Mac Agent)
# Updated: 2026-01-06

---

## WHAT IT DOES

**Starts complete L9 local environment from cold start:**

1. **Start Docker Desktop** (if not running)
2. **Wait** for Docker daemon to be ready
3. **Start containers** via docker compose (postgres, redis, neo4j, l9-api)
4. **Start local dashboard** (port 5050)
5. **Start Mac Agent** (local task executor)
6. **Open browser** to dashboard

---

## EXECUTION PROTOCOL

When `/lcto` is invoked, execute these steps IN ORDER:

### Step 1: Start Docker Desktop (if not running)

```bash
# Check if Docker daemon is running
docker info >/dev/null 2>&1

# If not running, start Docker Desktop
open -a Docker

# Wait for Docker daemon (up to 60 seconds)
for i in {1..60}; do
    docker info >/dev/null 2>&1 && break
    sleep 1
done
```

### Step 2: Start Docker Compose

```bash
cd /Users/ib-mac/Projects/L9
docker compose up -d
```

### Step 3: Wait for Health Checks

```bash
# Wait for l9-api to be healthy (up to 90 seconds)
for i in {1..90}; do
    curl -s http://localhost:8000/health >/dev/null && break
    sleep 1
done
```

### Step 4: Start Local Dashboard

```bash
cd /Users/ib-mac/Projects/L9
source venv/bin/activate
L9_API_URL="http://localhost:8000" python local_dashboard/app.py &
```

### Step 5: Open Browser

```bash
sleep 2
open http://127.0.0.1:5050
```

### Step 6: Start Mac Agent (Local Task Executor)

```bash
cd /Users/ib-mac/Projects/L9
source venv/bin/activate
MAC_AGENT_ENABLED=true python -m mac_agent.runner &
```

> **What Mac Agent does:** Polls for tasks L wants to execute on your local machine (shell commands, browser automation, file ops). L delegates to Mac Agent via the `mac_agent_exec_task` tool.

> **Alternative (permanent install):** Run `./mac_agent/install_mac_agent.sh` to install as LaunchAgent (auto-starts on login).

---

## QUICK START

```
/lcto

Runs all 6 steps automatically.
```

---

## EXECUTION MODES

### Default: Full Stack with Dashboard (Talk to L)
```
/lcto

Starts:
1. Docker Desktop (if needed)
2. postgres, redis, neo4j, l9-api containers
3. Local dashboard on :5050 ← THIS IS HOW YOU TALK TO L
4. Mac Agent (local task executor) ← L CAN NOW RUN TASKS ON YOUR MAC
5. Opens browser automatically
```

### Status Check
```
/lcto --status

Shows status of all components.
```

### Stop Everything
```
/lcto --stop

Stops:
1. Mac Agent runner
2. Local dashboard
3. Docker containers
```

---

## OUTPUT FORMAT

```
## 🚀 L9 LOCAL STARTUP

### Step 1: Docker Desktop
- [ ] Checking Docker daemon...
- [ ] Starting Docker Desktop...
- [ ] Waiting for daemon... (15s)
- [x] Docker ready

### Step 2: Containers
- [ ] Starting postgres...
- [ ] Starting redis...
- [ ] Starting neo4j...
- [ ] Starting l9-api...
- [x] All containers started

### Step 3: Health Check
- [ ] Waiting for l9-api health...
- [x] L9 API healthy

### Step 4: Dashboard
- [ ] Starting local dashboard...
- [x] Dashboard running on :5050

### Step 5: Browser
- [x] Opening http://127.0.0.1:5050

### Step 6: Mac Agent
- [ ] Starting Mac Agent runner...
- [x] Mac Agent polling for tasks

╔══════════════════════════════════════════════════════════════╗
║                    L9 READY                                  ║
╠══════════════════════════════════════════════════════════════╣
║  Dashboard:   http://127.0.0.1:5050                          ║
║  L9 API:      http://localhost:8000                          ║
║  API Docs:    http://localhost:8000/docs                     ║
║  Mac Agent:   Running (polls ~/.l9/mac_tasks/)               ║
╚══════════════════════════════════════════════════════════════╝
```

---

## PORTS

| Service | Port | URL |
|---------|------|-----|
| L9 API | 8000 | http://localhost:8000 |
| Dashboard | 5050 | http://127.0.0.1:5050 |
| PostgreSQL | 5432 | localhost:5432 |
| Redis | 6379 | localhost:6379 |
| Neo4j | 7474 | http://localhost:7474 |

---

## TROUBLESHOOTING

| Issue | Solution |
|-------|----------|
| Docker Desktop won't start | Check Docker Desktop app manually |
| Port 8000 in use | `lsof -i :8000 && kill -9 <pid>` |
| Container startup failed | `docker compose logs` |
| Dashboard won't start | `pkill -f local_dashboard/app.py` then retry |
| Health check timeout | Increase wait time, check container logs |
| Mac Agent not starting | Check `MAC_AGENT_ENABLED=true` is set |

---

## SHUTDOWN

```
/lcto --stop

# Or manually:
pkill -f "mac_agent.runner"
pkill -f "local_dashboard/app.py"
cd /Users/ib-mac/Projects/L9 && docker compose down
```

---

## FILES

| File | Purpose |
|------|---------|
| `docker-compose.yml` | Docker services configuration |
| `local_dashboard/app.py` | Dashboard UI |
| `mac_agent/runner.py` | Mac Agent task executor |
| `.env` | Environment variables |

---

## ANTI-PATTERNS

❌ **DON'T:** Run uvicorn directly (use Docker for l9-api)
❌ **DON'T:** Start services individually
❌ **DON'T:** Skip health checks
❌ **DON'T:** Forget to activate venv for dashboard/mac_agent

✅ **DO:** Let /lcto handle everything
✅ **DO:** Wait for all health checks
✅ **DO:** Use the dashboard to talk to L
✅ **DO:** Activate venv before running Python scripts

---

## MAC AGENT MANUAL COMMANDS

```bash
# Start Mac Agent manually (testing)
cd /Users/ib-mac/Projects/L9
source venv/bin/activate
MAC_AGENT_ENABLED=true python -m mac_agent.runner

# Install as LaunchAgent (permanent)
cd /Users/ib-mac/Projects/L9/mac_agent
./install_mac_agent.sh

# Check if running
launchctl list | grep l9

# View logs
tail -f /opt/l9_agent/logs/agent.log

# Stop LaunchAgent
launchctl unload ~/Library/LaunchAgents/com.l9.agent.plist

# Restart LaunchAgent
launchctl unload ~/Library/LaunchAgents/com.l9.agent.plist
launchctl load ~/Library/LaunchAgents/com.l9.agent.plist
```

---

## VPS DEPLOYMENT NOTE

For VPS deployment, Mac Agent needs to be adapted to a systemd service.
See `mac_agent/install_mac_agent.sh` for the LaunchAgent version that can be adapted.
