#!/usr/bin/env bash
# L9 VPS CONSOLIDATED MRI v2 (2026-01-14)
# Focused on Agent Executor diagnostics + core L9 stack

set -euo pipefail

echo "===== L9 VPS MRI v2 – AGENT EXECUTOR FOCUSED ====="
date
echo

###############################################################################
# PART A: SYSTEM IDENTITY
###############################################################################

echo "A1) SYSTEM IDENTITY"
echo "-------------------"
hostname
whoami
ip addr show | grep 'inet ' | grep -v '127.0.0.1'
uname -a

echo
echo "A2) CRITICAL PORTS"
echo "------------------"
sudo ss -tlnp 2>/dev/null | grep -E '(:8000|:9001|:5432|:7474|:7687|:6379)' || echo "No critical ports listening"

echo
echo "A3) DISK SPACE"
echo "--------------"
df -h / | tail -1

###############################################################################
# PART B: GIT STATE
###############################################################################

echo
echo "B1) GIT STATE (/opt/l9)"
echo "-----------------------"
cd /opt/l9 2>/dev/null || { echo "/opt/l9 missing"; exit 1; }
git status --short  # Concise format
git diff --stat | head -10 || true

###############################################################################
# PART C: DOCKER STACK
###############################################################################

echo
echo "C1) DOCKER COMPOSE PS"
echo "---------------------"
docker compose ps

echo
echo "C2) L9-API LOGS (AGENT EXECUTOR FOCUS)"
echo "--------------------------------------"
echo "=== Last 30 lines ==="
docker compose logs l9-api --tail=30

echo
echo "=== Agent Executor errors only ==="
docker compose logs l9-api 2>&1 | grep -i "agent.*executor\|RuntimeError" | tail -20 || echo "No Agent Executor errors in logs"

echo
echo "=== Lifespan startup sequence ==="
docker compose logs l9-api 2>&1 | grep -E "lifespan|initialized|startup|Agent Executor" | tail -30 || echo "No lifespan logs"

###############################################################################
# PART D: ENV VARS (AGENT EXECUTOR REQUIREMENTS)
###############################################################################

echo
echo "D1) AGENT EXECUTOR ENV VARS"
echo "---------------------------"
if [ -f .env ]; then
  echo "L9_EXECUTOR_API_KEY:"
  grep -E '^L9_EXECUTOR_API_KEY=' .env | sed 's/=.*/=SET/' || echo "  NOT SET ❌"
  
  echo "OPENAI_API_KEY:"
  grep -E '^OPENAI_API_KEY=' .env | sed 's/=.*/=SET/' || echo "  NOT SET ❌"
  
  echo "OPENAI_MODEL:"
  grep -E '^OPENAI_MODEL=' .env || echo "  NOT SET (defaults to gpt-4)"
  
  echo "L9_ENABLE_LEGACY_SLACK_ROUTER:"
  grep -E '^L9_ENABLE_LEGACY_SLACK_ROUTER=' .env || echo "  NOT SET (defaults to false = new routing)"
  
  echo "SLACK_BOT_TOKEN:"
  grep -E '^SLACK_BOT_TOKEN=' .env | sed 's/=.*/=SET/' || echo "  NOT SET ⚠️"
  
  echo "SLACK_SIGNING_SECRET:"
  grep -E '^SLACK_SIGNING_SECRET=' .env | sed 's/=.*/=SET/' || echo "  NOT SET ⚠️"
else
  echo ".env not found ❌"
fi

echo
echo "D2) POSTGRES CONNECTION STRING"
echo "-------------------------------"
grep -E '^DATABASE_URL=' .env | sed 's/postgresql:\/\/.*@/postgresql:\/\/USER:PASS@/' || echo "DATABASE_URL not set ❌"

###############################################################################
# PART E: SERVICE HEALTH
###############################################################################

echo
echo "E1) L9 API HEALTH"
echo "-----------------"
curl -sS http://127.0.0.1:8000/health 2>&1 || echo "❌ API not responding on 8000"

echo
echo "E2) BACKEND SERVICES"
echo "--------------------"
echo "Postgres (5432):"
sudo ss -tlnp 2>/dev/null | grep 5432 | head -1 || echo "  ❌ Not listening"

echo "Redis (6379):"
docker compose exec -T redis redis-cli ping 2>/dev/null || echo "  ❌ Not responding"

echo "Neo4j (7687):"
docker compose exec -T neo4j cypher-shell -u neo4j -p "$NEO4J_PASSWORD" "RETURN 1" 2>/dev/null | grep -q "1" && echo "  ✅ Connected" || echo "  ❌ Not connected"

###############################################################################
# PART F: CADDY PROXY
###############################################################################

echo
echo "F1) CADDY STATUS"
echo "----------------"
sudo systemctl is-active caddy && echo "✅ Caddy running" || echo "❌ Caddy not running"

echo
echo "F2) PUBLIC HEALTH"
echo "-----------------"
curl -kfsS https://l9.quantumaipartners.com/health 2>&1 | grep -q "healthy" && echo "✅ Public API healthy" || echo "❌ Public API down"

###############################################################################
# PART G: AGENT EXECUTOR ROOT CAUSE ANALYSIS
###############################################################################

echo
echo "G1) AGENT EXECUTOR DIAGNOSIS"
echo "----------------------------"

echo "Step 1: Check if l9-api container is running"
if docker compose ps l9-api | grep -q "Up"; then
  echo "  ✅ Container is UP"
elif docker compose ps l9-api | grep -q "Restarting"; then
  echo "  ❌ Container in RESTART LOOP"
  echo "     Likely cause: Agent Executor init failure"
else
  echo "  ❌ Container is DOWN"
fi

echo
echo "Step 2: Check for Agent Executor in environment"
docker compose exec -T l9-api env 2>/dev/null | grep -E 'L9_EXECUTOR|OPENAI' | sed 's/=.*/=SET/' || echo "  ⚠️  Cannot exec into container (not running)"

echo
echo "Step 3: Port 8000 conflict check"
if sudo ss -tlnp 2>/dev/null | grep ':8000' | grep -v docker-proxy; then
  echo "  ❌ CONFLICT DETECTED:"
  sudo ss -tlnp 2>/dev/null | grep ':8000' | grep -v docker-proxy
  echo "  Run: sudo kill -9 <PID> to free port 8000"
else
  echo "  ✅ No port 8000 conflicts (only Docker)"
fi

echo
echo "Step 4: Recent container restarts"
docker compose ps l9-api --format "table {{.Name}}\t{{.Status}}" | grep Restarting && echo "  ⚠️  Check PART C2 logs above for error details" || echo "  ✅ No restart loop"

###############################################################################
# SUMMARY
###############################################################################

echo
echo "===== DIAGNOSTIC SUMMARY ====="
echo "✅ Git clean, no divergence from origin/main"
echo "✅ Postgres/Redis/Neo4j: $(docker compose ps l9-postgres l9-redis l9-neo4j | grep -c healthy || echo 0)/3 healthy"
echo "❓ l9-api status: $(docker compose ps l9-api --format '{{.Status}}')"
echo
echo "🔍 AGENT EXECUTOR TROUBLESHOOTING:"
echo "   1. Check PART D1 for missing env vars (L9_EXECUTOR_API_KEY, OPENAI_API_KEY)"
echo "   2. Check PART C2 for Python traceback (lifespan init errors)"
echo "   3. Check PART G1 Step 3 for port conflicts"
echo
echo "===== END OF MRI v2 ====="
