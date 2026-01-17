#!/usr/bin/env bash
# L9 VPS CONSOLIDATED MRI v3 (2026-01-17)
# Focused on Agent Executor diagnostics + core L9 stack + Fresh Slate checks
#
# Usage: Run on VPS via SSH or copy-paste
#   bash scripts/deployment/vps-mri.sh
#   OR source this file directly

set -euo pipefail

# Load .env for credentials (don't hardcode!)
cd /opt/l9 2>/dev/null || cd ~/Projects/L9 2>/dev/null || true
if [ -f .env ]; then
    set -a
    source .env
    set +a
fi

echo "===== L9 VPS MRI v3 – FRESH SLATE DIAGNOSTICS ====="
date
echo

###############################################################################
# PART A: SYSTEM IDENTITY
###############################################################################

echo "A1) SYSTEM IDENTITY"
echo "-------------------"
hostname
whoami
ip addr show | grep 'inet ' | grep -v '127.0.0.1' | head -3
uname -r  # Just kernel version, not full uname

echo
echo "A2) CRITICAL PORTS"
echo "------------------"
sudo ss -tlnp 2>/dev/null | grep -E '(:8000|:8080|:9001|:5432|:7474|:7687|:6379)' || echo "No critical ports listening"

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
echo "C1) DOCKER COMPOSE PS (ALL CONTAINERS)"
echo "---------------------------------------"
docker compose ps --format "table {{.Name}}\t{{.Status}}\t{{.Ports}}" 2>/dev/null || docker compose ps

echo
echo "C2) L9-API LOGS (AGENT EXECUTOR FOCUS)"
echo "--------------------------------------"
echo "=== Last 20 lines ==="
docker compose logs l9-api --tail=20 --no-log-prefix 2>&1 | tail -20

echo
echo "=== Errors/Exceptions ==="
docker compose logs l9-api 2>&1 | grep -iE "error|exception|failed|traceback" | tail -10 || echo "No errors in logs"

echo
echo "=== Lifespan startup sequence ==="
docker compose logs l9-api 2>&1 | grep -E "lifespan|initialized|startup|Migration" | tail -15 || echo "No lifespan logs"

echo
echo "C3) L9-MCP-MEMORY STATUS"
echo "------------------------"
docker compose ps l9-mcp-memory --format "{{.Status}}" 2>/dev/null || echo "l9-mcp-memory not found"
docker compose logs l9-mcp-memory --tail=10 --no-log-prefix 2>&1 | tail -5 || true

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
API_HEALTH=$(curl -sS --max-time 5 http://127.0.0.1:8000/health 2>&1)
if echo "$API_HEALTH" | grep -q "healthy"; then
    echo "✅ API healthy: $API_HEALTH"
else
    echo "❌ API not responding: $API_HEALTH"
fi

echo
echo "E2) BACKEND SERVICES"
echo "--------------------"
echo "Postgres (5432):"
if docker compose exec -T l9-postgres pg_isready -U "$POSTGRES_USER" 2>/dev/null; then
    echo "  ✅ Ready"
else
    echo "  ❌ Not ready"
fi

echo "Redis (6379):"
REDIS_PING=$(docker compose exec -T redis redis-cli ping 2>/dev/null || echo "FAIL")
if [ "$REDIS_PING" = "PONG" ]; then
    echo "  ✅ PONG"
else
    echo "  ❌ Not responding"
fi

echo "Neo4j (7687):"
# Use env var from .env (loaded at top), NEVER hardcode password!
if [ -n "${NEO4J_PASSWORD:-}" ]; then
    NEO4J_CHECK=$(docker compose exec -T neo4j cypher-shell -u neo4j -p "$NEO4J_PASSWORD" "RETURN 1 AS ok" 2>/dev/null || echo "FAIL")
    if echo "$NEO4J_CHECK" | grep -q "ok"; then
        echo "  ✅ Connected"
    else
        echo "  ❌ Not connected (check NEO4J_PASSWORD)"
    fi
else
    echo "  ⚠️  NEO4J_PASSWORD not set in .env"
fi

echo
echo "E3) MCP MEMORY API (8080)"
echo "-------------------------"
MCP_HEALTH=$(curl -sS --max-time 5 http://127.0.0.1:8080/health 2>&1 || echo "FAIL")
if echo "$MCP_HEALTH" | grep -qiE "healthy|ok"; then
    echo "✅ MCP Memory healthy"
else
    echo "❌ MCP Memory not responding: $MCP_HEALTH"
fi

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
# PART H: DATABASE MIGRATIONS
###############################################################################

echo
echo "H1) MIGRATION STATUS"
echo "--------------------"
# Check schema_migrations table (Python runner tracks here)
MIGRATION_COUNT=$(docker compose exec -T l9-postgres psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -t -c "SELECT COUNT(*) FROM schema_migrations" 2>/dev/null | tr -d ' ' || echo "0")
echo "Applied migrations (schema_migrations table): $MIGRATION_COUNT"

# Check migration files
SQL_FILES=$(ls -1 migrations/*.sql 2>/dev/null | wc -l || echo "0")
echo "Migration files in migrations/: $SQL_FILES"

# Show recent migrations
echo "Recent migrations:"
docker compose exec -T l9-postgres psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "SELECT migration_name, applied_at FROM schema_migrations ORDER BY applied_at DESC LIMIT 5" 2>/dev/null || echo "  (cannot query schema_migrations)"

###############################################################################
# SUMMARY
###############################################################################

echo
echo "===== DIAGNOSTIC SUMMARY ====="

# Count healthy containers
HEALTHY_COUNT=$(docker compose ps --format json 2>/dev/null | grep -c '"healthy"' || echo "0")
TOTAL_CONTAINERS=$(docker compose ps --format json 2>/dev/null | grep -c '"Name"' || echo "0")

echo "📦 Containers: $HEALTHY_COUNT/$TOTAL_CONTAINERS healthy"
echo "🔌 l9-api: $(docker compose ps l9-api --format '{{.Status}}' 2>/dev/null || echo 'unknown')"
echo "🔌 l9-mcp-memory: $(docker compose ps l9-mcp-memory --format '{{.Status}}' 2>/dev/null || echo 'unknown')"
echo "📊 Migrations: $MIGRATION_COUNT applied"
echo
echo "🔍 TROUBLESHOOTING:"
echo "   1. Check PART D1 for missing env vars"
echo "   2. Check PART C2/C3 for container errors"
echo "   3. Check PART G1 Step 3 for port conflicts"
echo "   4. Check PART H1 for migration status"
echo
echo "===== END OF MRI v3 ====="