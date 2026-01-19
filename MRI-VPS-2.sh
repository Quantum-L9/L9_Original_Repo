#!/usr/bin/env bash
set -euo pipefail

echo "===== L9 VPS MRI v4 – Docker-Only, Caddy 9001, Neo4j-Optional ====="
date -u +"%a %b %d %I:%M:%S %p UTC %Y"

###############################################################################
# PART A: SYSTEM IDENTITY
###############################################################################

echo
echo "A1) SYSTEM IDENTITY"
echo "-------------------"
hostname
whoami
ip addr show | grep 'inet ' | grep -v '127.0.0.1' | head -3
uname -r

echo
echo "A2) CRITICAL PORTS (Docker + Caddy)"
echo "-----------------------------------"
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
git status --short
git diff --stat | head -10 || true

###############################################################################
# PART C: DOCKER STACK
###############################################################################

echo
echo "C1) DOCKER COMPOSE PS (ALL CONTAINERS)"
echo "--------------------------------------"
docker compose ps

echo
echo "C2) L9-API LOGS (LAST 40 LINES)"
echo "--------------------------------"
docker compose logs l9-api --tail=40 || echo "No l9-api logs available"

###############################################################################
# PART D: CORE ENVS (FROM /opt/l9/.env)
###############################################################################

echo
echo "D1) CORE ENV VARS (sanitized)"
echo "-----------------------------"
if [[ -f .env ]]; then
  grep -E '^(OPENAI_API_KEY|DATABASE_URL|MEMORY_DSN|NEO4J_URI|NEO4J_URL|NEO4J_USER|NEO4J_PASSWORD|MCP_API_KEY_C|SLACK_BOT_TOKEN|SLACK_SIGNING_SECRET)=' .env \
    | sed 's/=.*/=SET/' || true
else
  echo ".env missing"
fi

###############################################################################
# PART E: SERVICE HEALTH
###############################################################################

echo
echo "E1) INTERNAL L9 API HEALTH (127.0.0.1:8000)"
echo "-------------------------------------------"
API_HEALTH_RAW=$(curl -s --max-time 5 http://127.0.0.1:8000/health || echo '')
if echo "$API_HEALTH_RAW" | grep -q '"status":"ok"'; then
  echo "✅ API healthy (internal): $API_HEALTH_RAW"
else
  echo "❌ API health unexpected or empty: ${API_HEALTH_RAW:-<no response>}"
fi

echo
echo "E2) BACKEND SERVICES"
echo "--------------------"

echo "Postgres (5432):"
if docker exec l9-postgres pg_isready -U postgres >/dev/null 2>&1; then
  echo "  ✅ Ready"
else
  echo "  ❌ Not ready (pg_isready failed)"
fi

echo "Redis (6379):"
if docker exec l9-redis redis-cli ping 2>/dev/null | grep -q PONG; then
  echo "  ✅ PONG"
else
  echo "  ❌ Not responding"
fi

echo "Neo4j (7687):"
if nc -z 127.0.0.1 7687 >/dev/null 2>&1; then
  echo "  ✅ TCP port open"
else
  echo "  ❌ Not connected (port 7687 closed)"
fi

echo
echo "E3) MCP MEMORY VIA CADDY (9001 /memory*)"
echo "----------------------------------------"
MCP_HEALTH=$(curl -sk --max-time 5 https://157.180.73.53:9001/memory/health || echo '')
if [[ -n "$MCP_HEALTH" ]]; then
  echo "ℹ️  MCP /memory/health response:"
  echo "$MCP_HEALTH"
else
  echo "⚠️  MCP /memory/health not responding (this may be expected if route not defined)"
fi

###############################################################################
# PART F: CADDY / PUBLIC API
###############################################################################

echo
echo "F1) CADDY STATUS"
echo "----------------"
if systemctl is-active --quiet caddy; then
  echo "active"
  echo "✅ Caddy running"
else
  echo "inactive"
  echo "❌ Caddy not running"
fi

echo
echo "F2) PUBLIC HEALTH VIA CADDY 9001"
echo "--------------------------------"
PUBLIC_HEALTH=$(curl -sk --max-time 5 https://157.180.73.53:9001/health || echo '')
if echo "$PUBLIC_HEALTH" | grep -q '"status":"ok"'; then
  echo "✅ Public API healthy via 9001"
  echo "$PUBLIC_HEALTH"
else
  echo "❌ Public API health unexpected or empty via 9001: ${PUBLIC_HEALTH:-<no response>}"
fi

###############################################################################
# SUMMARY
###############################################################################

echo
echo "===== DIAGNOSTIC SUMMARY ====="
docker compose ps | sed -n '2,999p' || true
echo
echo "Key checks:"
echo "  - Internal API health: status ok? -> see E1"
echo "  - Caddy 9001 /health: status ok? -> see F2"
echo "  - Postgres/Redis/Neo4j ports reachable: see E2"
echo
echo "===== END OF MRI v4 ====="
