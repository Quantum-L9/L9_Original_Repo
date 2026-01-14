#!/usr/bin/env bash
# L9 VPS CONSOLIDATED MRI (UPDATED 2026-01-14)
# Host assumptions:
# - Code: /opt/l9
# - Docker Compose: /opt/l9/docker-compose.yml
# - Services: l9-api, l9-postgres, redis, neo4j, prometheus, grafana, jaeger
# - Optional: l9-mcp-memory (port 9002)
# - Caddy: systemd service, Caddyfile at /etc/caddy/Caddyfile
# - Slack Adapter: SLACK_APP_ENABLED, SLACK_BOT_TOKEN, SLACK_SIGNING_SECRET

set -euo pipefail

echo
echo "===== L9 VPS MRI – UPDATED FULL DIAGNOSTIC ====="
date
echo

###############################################################################
# PART A: SYSTEM-LEVEL DIAGNOSTICS
###############################################################################

echo
echo "A1) SYSTEM IDENTITY"
echo "-------------------"
hostname
whoami
ip addr show | grep 'inet ' | grep -v '127.0.0.1'
uname -a

echo
echo "A2) ALL LISTENING PORTS (TOP 50)"
echo "--------------------------------"
sudo ss -tlnp 2>/dev/null | head -50 || true

echo
echo "A3) FIREWALL STATUS (UFW + CLOUD-FIREWALL HINT)"
echo "----------------------------------------------"
sudo ufw status numbered 2>/dev/null || echo "UFW not active or not installed"
echo
echo "If ports look blocked externally, check cloud firewall rules (TCP 22, 80, 443, 9001, 7474, 7687, 5432, 6379, 9090, 3000, 16686 as needed)."

echo
echo "A4) DISK SPACE (KEY PATHS)"
echo "--------------------------"
df -h / /opt /var /tmp 2>/dev/null || true

echo
echo "A5) MEMORY (RAM)"
echo "----------------"
free -h

echo
echo "A6) SYSTEM LOAD"
echo "---------------"
uptime

###############################################################################
# PART B: GIT + REPO STATE
###############################################################################

echo
echo "B1) GIT STATE (/opt/l9)"
echo "-----------------------"
cd /opt/l9 2>/dev/null || { echo "/opt/l9 missing – L9 not deployed here"; exit 1; }

echo
echo "Git status:"
git status

echo
echo "Git diff (HEAD vs working tree, first 100 lines):"
git diff | head -100 || true

echo
echo "Untracked files (first 20):"
git ls-files --others --exclude-standard | head -20 || true

###############################################################################
# PART C: COMPOSE / CONTAINER RUNTIME
###############################################################################

echo
echo "C1) DOCKER / COMPOSE VERSIONS"
echo "-----------------------------"
docker --version || echo "Docker CLI not found"
docker compose version || echo "docker compose plugin not found"
systemctl is-active docker || echo "Docker service not active (may be socket-activated)"

echo
echo "C2) DOCKER COMPOSE PS"
echo "----------------------"
cd /opt/l9
docker compose ps

echo
echo "C3) CONTAINER LOGS (l9-api last 80 lines)"
echo "-----------------------------------------"
docker compose logs l9-api --tail=80 || echo "l9-api logs not available"

echo
echo "C4) DOCKER NETWORK + PORTS OF INTEREST"
echo "--------------------------------------"
echo "docker0 / bridge networks:"
ip addr show docker0 2>/dev/null | grep inet || echo "No docker0 interface (host networking or different bridge)"
echo
echo "Explicit port checks (8000, 9001, 5432, 7474, 7687, 6379, 9090, 3000, 16686):"
sudo ss -tlnp 2>/dev/null | grep -E '(:8000|:9001|:5432|:7474|:7687|:6379|:9090|:3000|:16686)' || echo "No matches for those ports"

echo
echo "C5) DOCKER IMAGES"
echo "-----------------"
docker images --format "table {{.Repository}}\t{{.Tag}}\t{{.Size}}" | head -15 || echo "Cannot list images"

echo
echo "C6) DOCKER NETWORKS"
echo "-------------------"
docker network ls || echo "Cannot list networks"

echo
echo "C7) DOCKER CONTAINER ERRORS (RECENT)"
echo "------------------------------------"
for container in l9-api l9-postgres redis neo4j; do
    if docker ps -a --format '{{.Names}}' 2>/dev/null | grep -q "$container"; then
        echo "--- $container ---"
        docker logs "$container" 2>&1 | grep -iE "error|exception|fail|critical" | tail -5 || echo "No recent errors"
    fi
done

###############################################################################
# PART D: CONFIG (.env, CADDYFILE, COMPOSE)
###############################################################################

echo
echo "D1) .env (SANITIZED KEYS ONLY)"
echo "------------------------------"
cd /opt/l9
if [ -f .env ]; then
  sed 's/=.*/=REDACTED/' .env | grep -E 'POSTGRES|DATABASE_URL|NEO4J_|REDIS|OPENAI|SLACK|L9_API_KEY|L9_EXECUTOR_API_KEY|PERPLEXITY|ANTHROPIC|QDRANT|MACAGENT|PROMETHEUS|GRAFANA|MCP_API_KEY' | sort
else
  echo ".env not found in /opt/l9"
fi

echo
echo "D1b) SLACK ADAPTER VARS CHECK"
echo "-----------------------------"
if [ -f .env ]; then
  echo "SLACK_APP_ENABLED:"
  grep -E '^SLACK_APP_ENABLED=' .env || echo "  NOT SET (default: true)"
  echo "SLACK_BOT_TOKEN:"
  grep -E '^SLACK_BOT_TOKEN=' .env | sed 's/=.*/=SET/' || echo "  NOT SET"
  echo "SLACK_SIGNING_SECRET:"
  grep -E '^SLACK_SIGNING_SECRET=' .env | sed 's/=.*/=SET/' || echo "  NOT SET"
  echo "L9_ENABLE_LEGACY_SLACK_ROUTER:"
  grep -E '^L9_ENABLE_LEGACY_SLACK_ROUTER=' .env || echo "  NOT SET (default: false = new routing)"
else
  echo ".env not found – skipping Slack var check"
fi

echo
echo "D2) NEO4J ENV VARS PRESENCE CHECK"
echo "---------------------------------"
if [ -f .env ]; then
  grep -E 'NEO4J_URI|NEO4J_USER|NEO4J_PASSWORD' .env || echo "No NEO4J_* vars found in .env"
else
  echo ".env not found – skipping NEO4J var check"
fi

echo
echo "D3) docker-compose.yml (SERVICES + NEO4J SECTION)"
echo "------------------------------------------------"
if [ -f docker-compose.yml ]; then
  echo "-- services (first 60 lines) --"
  sed -n '1,60p' docker-compose.yml
  echo
  echo "-- neo4j service block (if any) --"
  grep -n 'neo4j' docker-compose.yml || echo "No neo4j service references found in docker-compose.yml"
else
  echo "docker-compose.yml not found in /opt/l9"
fi

echo
echo "D4) CADDY CONFIG (TOP 80 LINES)"
echo "-------------------------------"
if [ -f /etc/caddy/Caddyfile ]; then
  sed -n '1,80p' /etc/caddy/Caddyfile
else
  echo "/etc/caddy/Caddyfile not found"
fi

###############################################################################
# PART E: SERVICE HEALTH (API, WORLD MODEL, MCP, NEO4J)
###############################################################################

echo
echo "E1) L9 API HEALTH (DIRECT ON 8000)"
echo "----------------------------------"
curl -sS http://127.0.0.1:8000/health || echo "API health on 8000 not responding"

echo
echo "E2) L9 MEMORY ENDPOINTS"
echo "-----------------------"
curl -sS http://127.0.0.1:8000/memory/stats || echo "memory/stats not responding"
curl -sS http://127.0.0.1:8000/memory/health || echo "memory/health not responding"

echo
echo "E3) MCP / CADDY FRONT DOOR HEALTH (9001)"
echo "----------------------------------------"
echo "HTTP → expect 'Client sent an HTTP request to an HTTPS server' if TLS-only:"
curl -sS http://127.0.0.1:9001/health || echo "HTTP on 9001 not responding (may be TLS-only, expected)"
echo
echo "HTTPS → /health:"
curl -kfsS https://127.0.0.1:9001/health || echo "HTTPS /health on 9001 not responding (check Caddy and certs)"

echo
echo "E4) DNS RESOLUTION + PUBLIC IP"
echo "------------------------------"
echo "Public IP:"
curl -s --max-time 5 ifconfig.me 2>/dev/null || echo "Cannot reach ifconfig.me"
echo
echo "DNS resolution for l9.quantumaipartners.com:"
getent hosts l9.quantumaipartners.com 2>/dev/null || echo "DNS not resolving"

echo
echo "E5) PUBLIC HEALTH VIA DOMAIN (IF DNS CONFIGURED)"
echo "-----------------------------------------------"
echo "Public API health (443):"
curl -kfsS https://l9.quantumaipartners.com/health || echo "Public /health failed (DNS, Caddy, or cert issue)"
echo "Public world model state-version (443):"
curl -kfsS https://l9.quantumaipartners.com/api/v1/worldmodel/state-version || echo "Public worldmodel state-version failed"

echo
echo "E6) API ROUTES AVAILABLE (via OpenAPI)"
echo "--------------------------------------"
curl -s --max-time 5 http://127.0.0.1:8000/openapi.json 2>/dev/null | python3 -c "import sys,json; d=json.load(sys.stdin); print('\n'.join(sorted(d.get('paths',{}).keys())[:25]))" 2>/dev/null || echo "Cannot fetch OpenAPI spec"

###############################################################################
# PART F: DATABASES (POSTGRES, NEO4J, REDIS)
###############################################################################

echo
echo "F1) POSTGRES STATUS + DB LIST"
echo "-----------------------------"
sudo systemctl status postgresql --no-pager | head -10 || echo "PostgreSQL systemd unit not found or inactive"
echo
echo "Port 5432 listeners:"
sudo ss -tlnp 2>/dev/null | grep 5432 || echo "No process listening on 5432"
echo
echo "Database list (first 15):"
sudo -u postgres psql -l 2>/dev/null | head -15 || echo "Unable to list databases as postgres user"

echo
echo "F2) NEO4J CONTAINER + PORTS"
echo "---------------------------"
docker ps --filter name=neo4j --format "table {{.ID}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}" || echo "No neo4j container in docker ps"
echo
echo "Neo4j ports:"
sudo ss -tlnp 2>/dev/null | grep -E ':7474|:7687' || echo "Neo4j ports 7474/7687 not listening"

echo
echo "F3) NEO4J BOLT CONNECTIVITY (IF PASSWORD SET)"
echo "--------------------------------------------"
if grep -q 'NEO4J_PASSWORD' .env 2>/dev/null; then
  echo "Attempting Neo4j driver smoke test via python..."
  python3 - <<'EOF' 2>/dev/null || echo "Neo4j Python driver test failed (driver not installed or auth error)"
import os
from neo4j import GraphDatabase
uri = os.environ.get("NEO4J_URI", "bolt://localhost:7687")
user = os.environ.get("NEO4J_USER", "neo4j")
password = os.environ.get("NEO4J_PASSWORD")
if not password:
    raise SystemExit("NEO4J_PASSWORD not set in environment")
driver = GraphDatabase.driver(uri, auth=(user, password))
with driver.session() as session:
    result = session.run("RETURN 1 AS ok")
    print("Neo4j connectivity OK, result:", result.single()["ok"])
driver.close()
EOF
else
  echo "NEO4J_PASSWORD not configured in .env – skipping direct Neo4j smoke test"
fi

echo
echo "F4) REDIS STATUS (IF USED)"
echo "--------------------------"
docker ps --filter name=redis --format "table {{.ID}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}" || echo "No redis container in docker ps"
echo
sudo ss -tlnp 2>/dev/null | grep 6379 || echo "No process listening on 6379"

###############################################################################
# PART G: L9 MEMORY SUBSTRATE + WORLD MODEL SNAPSHOT
###############################################################################

echo
echo "G1) MEMORY SUBSTRATE DETAILED"
echo "-----------------------------"
echo "Memory stats:"
curl -sS http://127.0.0.1:8000/memory/stats || echo "memory/stats not responding"
echo
echo "Memory GC stats:"
curl -sS http://127.0.0.1:8000/memory/gc/stats || echo "memory/gc/stats not responding"
echo
echo "Semantic search test (empty query):"
curl -sS -X POST http://127.0.0.1:8000/memory/semantic/search -H "Content-Type: application/json" -d '{"query":"test","limit":1}' 2>/dev/null | head -100 || echo "semantic search not responding"

echo
echo "G2) SLACK ADAPTER STATUS"
echo "------------------------"
echo "Slack commands endpoint:"
curl -sS http://127.0.0.1:8000/slack/commands -X POST -d "" 2>/dev/null | head -5 || echo "Slack commands endpoint not responding (expected without valid payload)"
echo "Slack events endpoint:"
curl -sS http://127.0.0.1:8000/slack/events -X POST -d "" 2>/dev/null | head -5 || echo "Slack events endpoint not responding (expected without valid payload)"

###############################################################################
# PART H: OBSERVABILITY (PROMETHEUS, GRAFANA, JAEGER)
###############################################################################

echo
echo "H1) PROMETHEUS STATUS"
echo "---------------------"
docker ps --filter name=prometheus --format "table {{.ID}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}" || echo "No prometheus container in docker ps"
curl -sS http://127.0.0.1:9090/-/healthy 2>/dev/null || echo "Prometheus health endpoint not responding"

echo
echo "H2) GRAFANA STATUS"
echo "------------------"
docker ps --filter name=grafana --format "table {{.ID}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}" || echo "No grafana container in docker ps"
curl -sS http://127.0.0.1:3000/api/health 2>/dev/null || echo "Grafana API health not responding"

echo
echo "H3) JAEGER STATUS"
echo "-----------------"
docker ps --filter name=jaeger --format "table {{.ID}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}" || echo "No jaeger container in docker ps"
curl -sS http://127.0.0.1:16686 2>/dev/null | head -5 || echo "Jaeger UI not reachable on 16686"

echo
echo "H4) MCP MEMORY SERVER STATUS (OPTIONAL)"
echo "---------------------------------------"
docker ps --filter name=mcp-memory --format "table {{.ID}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}" || echo "No l9-mcp-memory container (optional service)"
curl -sS http://127.0.0.1:9002/health 2>/dev/null || echo "MCP Memory server not responding on 9002 (may not be deployed)"

echo
echo "H5) PYTHON/UVICORN PROCESSES (OUTSIDE DOCKER)"
echo "---------------------------------------------"
ps aux | grep -E "python|uvicorn" | grep -v grep || echo "No Python/Uvicorn processes outside Docker"
echo
echo "Python version:"
python3 --version 2>&1

###############################################################################
# PART I: QUICK STATUS SUMMARY
###############################################################################

echo
echo "===== QUICK STATUS SUMMARY ====="
echo "--------------------------------"

# Docker
if systemctl is-active docker &>/dev/null; then
    echo "✓ Docker: Running"
else
    echo "✗ Docker: NOT Running"
fi

# Caddy
if systemctl is-active caddy &>/dev/null; then
    echo "✓ Reverse Proxy: Caddy"
elif systemctl is-active nginx &>/dev/null; then
    echo "✓ Reverse Proxy: Nginx"
else
    echo "✗ Reverse Proxy: NONE RUNNING"
fi

# L9 API
if curl -fs --max-time 3 http://127.0.0.1:8000/health &>/dev/null; then
    echo "✓ L9 API: Healthy"
else
    echo "✗ L9 API: NOT Responding"
fi

# PostgreSQL
if sudo ss -tlnp 2>/dev/null | grep -q ":5432 "; then
    echo "✓ PostgreSQL: Listening"
else
    echo "⚠ PostgreSQL: Not detected on 5432"
fi

# Redis
if sudo ss -tlnp 2>/dev/null | grep -q ":6379 "; then
    echo "✓ Redis: Listening"
else
    echo "⚠ Redis: Not detected on 6379"
fi

# Neo4j
if sudo ss -tlnp 2>/dev/null | grep -q ":7687 "; then
    echo "✓ Neo4j: Listening"
else
    echo "⚠ Neo4j: Not detected on 7687"
fi

# Public endpoint
if curl -kfs --max-time 5 https://l9.quantumaipartners.com/health &>/dev/null; then
    echo "✓ Public HTTPS: Accessible"
else
    echo "✗ Public HTTPS: NOT Accessible"
fi

###############################################################################
# PART J: SUMMARY HINTS
###############################################################################

echo
echo "===== MRI SUMMARY HINTS (READ OUTPUT ABOVE) ====="
echo "- If l9-api is unhealthy or degraded in docker compose ps, check /health payload and logs for failing optional backends (Neo4j, observability)."
echo "- If Postgres 5432 is not listening, memory system will be broken."
echo "- If Neo4j container is up but NEO4J_* vars missing in .env, graph features are effectively OFF."
echo "- If Caddy on 9001 responds with 'HTTP request to HTTPS server' over HTTP, that is expected (TLS only)."
echo "- If DNS for l9.quantumaipartners.com fails, public HTTPS access will fail; use IP or fix DNS."
echo "- SLACK ADAPTER: Requires SLACK_APP_ENABLED=true, SLACK_BOT_TOKEN, SLACK_SIGNING_SECRET in .env"
echo "- SLACK ROUTING: If using new routing, agent_executor must initialize successfully (check startup logs)"
echo "- If l9-api crashes with 'Agent Executor required for new Slack routing', set L9_ENABLE_LEGACY_SLACK_ROUTER=true as workaround"

echo
echo "===== END OF L9 VPS MRI ====="
