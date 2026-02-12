#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════════════════
# L9 VPS Deep MRI - C1 Production Environment
# Generated: 2026-02-12T17:22:00Z
# Target: admin@157.180.73.53 (/opt/l9)
# ═══════════════════════════════════════════════════════════════════════════

set -euo pipefail

echo "═══════════════════════════════════════════════════════════════════════════"
echo "L9 Deep MRI - C1 Production VPS"
echo "Timestamp: $(date -u +"%Y-%m-%dT%H:%M:%SZ")"
echo "═══════════════════════════════════════════════════════════════════════════"
echo ""

# ═══════════════════════════════════════════════════════════════════════════
# 1. SYSTEM OVERVIEW
# ═══════════════════════════════════════════════════════════════════════════
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "1. SYSTEM OVERVIEW"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Hostname: $(hostname)"
echo "Uptime: $(uptime -p)"
echo "Kernel: $(uname -r)"
echo "Load Average: $(uptime | awk -F'load average:' '{print $2}')"
echo ""

# ═══════════════════════════════════════════════════════════════════════════
# 2. DOCKER INFRASTRUCTURE
# ═══════════════════════════════════════════════════════════════════════════
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "2. DOCKER INFRASTRUCTURE (9 Containers)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
cd /opt/l9
docker compose ps --format "table {{.Name}}\t{{.Status}}\t{{.Health}}" | column -t
echo ""
echo "Docker Daemon Status:"
systemctl status docker --no-pager | grep -E "(Active|Memory|Tasks)" || echo "N/A"
echo ""

# ═══════════════════════════════════════════════════════════════════════════
# 3. CONTAINER RESOURCE USAGE
# ═══════════════════════════════════════════════════════════════════════════
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "3. CONTAINER RESOURCE USAGE"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.NetIO}}" \
  $(docker ps --filter "label=com.docker.compose.project=l9" --format "{{.Names}}")
echo ""

# ═══════════════════════════════════════════════════════════════════════════
# 4. NETWORK CONNECTIVITY
# ═══════════════════════════════════════════════════════════════════════════
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "4. NETWORK CONNECTIVITY (127.0.0.1 Ports)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
for port in 8000 5432 6379 7474 7687 9090 3000 16686 9002; do
  if nc -z 127.0.0.1 "$port" 2>/dev/null; then
    echo "✓ Port $port OPEN"
  else
    echo "✗ Port $port CLOSED"
  fi
done
echo ""

# ═══════════════════════════════════════════════════════════════════════════
# 5. DATABASE SUBSTRATE HEALTH
# ═══════════════════════════════════════════════════════════════════════════
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "5. DATABASE SUBSTRATE HEALTH"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

echo "PostgreSQL:"
# Load credentials from .env
PG_USER=$(grep "^POSTGRES_USER=" /opt/l9/.env 2>/dev/null | cut -d= -f2 || echo "postgres")
PG_DB=$(grep "^POSTGRES_DB=" /opt/l9/.env 2>/dev/null | cut -d= -f2 || echo "l9_memory")
docker compose exec -T l9-postgres psql -U "$PG_USER" -d "$PG_DB" -c "SELECT version();" 2>/dev/null | head -3 || echo "✗ Query failed"
docker compose exec -T l9-postgres psql -U "$PG_USER" -d "$PG_DB" -c "SELECT count(*) as tables FROM information_schema.tables WHERE table_schema='public';" 2>/dev/null | tail -2 || echo "✗ Table count failed"
echo ""

echo "Redis:"
# Extract password after first = (handles passwords with = in them)
REDIS_PW=$(grep "^REDIS_PASSWORD=" /opt/l9/.env 2>/dev/null | sed 's/^REDIS_PASSWORD=//')
if [ -n "$REDIS_PW" ]; then
  docker compose exec -T redis redis-cli -a "$REDIS_PW" --no-auth-warning PING || echo "✗ PING failed"
  docker compose exec -T redis redis-cli -a "$REDIS_PW" --no-auth-warning INFO stats | grep -E "(total_commands_processed|instantaneous_ops_per_sec)" || echo "✗ Stats failed"
else
  docker compose exec -T redis redis-cli PING || echo "✗ PING failed"
  docker compose exec -T redis redis-cli INFO stats | grep -E "(total_commands_processed|instantaneous_ops_per_sec)" || echo "✗ Stats failed"
fi
echo ""

echo "Neo4j:"
NEO4J_PW=$(grep "^NEO4J_PASSWORD=" /opt/l9/.env 2>/dev/null | cut -d= -f2)
curl -s -u "neo4j:$NEO4J_PW" http://127.0.0.1:7474/ | grep -q "Neo4j" && echo "✓ HTTP endpoint responsive" || echo "✗ HTTP endpoint failed"
echo ""

echo "MCP Memory Server:"
curl -s http://127.0.0.1:9002/health | jq -r '.status' 2>/dev/null || echo "✗ Health check failed"
echo ""

# ═══════════════════════════════════════════════════════════════════════════
# 6. L9 API HEALTH (ALL ENDPOINTS)
# ═══════════════════════════════════════════════════════════════════════════
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "6. L9 API HEALTH (Core Endpoints)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Read executor key from .env
EXEC_KEY=$(grep "^L9_EXECUTOR_API_KEY=" /opt/l9/.env | cut -d= -f2)

echo "GET /"
curl -s http://127.0.0.1:8000/ | jq -r '.status' || echo "✗ Failed"

echo "GET /health"
curl -s http://127.0.0.1:8000/health | jq -r '.status' || echo "✗ Failed"

echo "GET /health/startup"
curl -s http://127.0.0.1:8000/health/startup | jq -r '.status' || echo "✗ Failed"

echo "GET /health/neo4j"
curl -s http://127.0.0.1:8000/health/neo4j | jq -r '.status' || echo "✗ Failed"

echo "GET /health/services"
curl -s http://127.0.0.1:8000/health/services | jq -r '.status' || echo "✗ Failed"

echo "POST /kernels/reload (requires auth)"
curl -s -X POST http://127.0.0.1:8000/kernels/reload \
  -H "Authorization: Bearer ${EXEC_KEY}" \
  -H "Content-Type: application/json" \
  -d '{"force":false}' | jq -r '.success' || echo "✗ Failed"

echo "POST /lchat (requires auth)"
curl -s -X POST http://127.0.0.1:8000/lchat \
  -H "Authorization: Bearer ${EXEC_KEY}" \
  -H "Content-Type: application/json" \
  -d '{"message":"health check"}' | jq -r '.status' || echo "✗ Failed"
echo ""

# ═══════════════════════════════════════════════════════════════════════════
# 7. GIT STATE
# ═══════════════════════════════════════════════════════════════════════════
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "7. GIT STATE (/opt/l9)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
cd /opt/l9
echo "Branch: $(git rev-parse --abbrev-ref HEAD)"
echo "Commit: $(git rev-parse --short HEAD)"
echo "Commit Date: $(git log -1 --format=%cd --date=iso)"
echo "Status:"
git status --short | head -10 || echo "Clean working tree"
echo ""

# ═══════════════════════════════════════════════════════════════════════════
# 8. DISK USAGE
# ═══════════════════════════════════════════════════════════════════════════
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "8. DISK USAGE"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
df -h / | tail -1
echo ""
echo "Docker Volumes:"
docker volume ls --format "table {{.Name}}\t{{.Driver}}\t{{.Size}}" | grep l9 || echo "No L9 volumes found"
echo ""
echo "Docker System Usage:"
docker system df
echo ""

# ═══════════════════════════════════════════════════════════════════════════
# 9. RECENT LOGS (Last 50 lines per service)
# ═══════════════════════════════════════════════════════════════════════════
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "9. RECENT LOGS (Last 10 lines per critical service)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

for service in l9-api postgres neo4j redis mcp-memory; do
  echo ""
  echo "=== $service ==="
  docker compose logs --tail=10 "$service" 2>/dev/null || echo "No logs available"
done
echo ""

# ═══════════════════════════════════════════════════════════════════════════
# 10. OBSERVABILITY STACK
# ═══════════════════════════════════════════════════════════════════════════
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "10. OBSERVABILITY STACK"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Prometheus:"
curl -s http://127.0.0.1:9090/-/healthy && echo "✓ Healthy" || echo "✗ Unhealthy"

echo "Grafana:"
curl -s http://127.0.0.1:3000/api/health | jq -r '.database' 2>/dev/null || echo "✗ Check failed"

echo "Jaeger:"
curl -s http://127.0.0.1:16686/ | grep -q "Jaeger" && echo "✓ UI responsive" || echo "✗ UI failed"
echo ""

# ═══════════════════════════════════════════════════════════════════════════
# MRI SUMMARY
# ═══════════════════════════════════════════════════════════════════════════
echo "═══════════════════════════════════════════════════════════════════════════"
echo "MRI COMPLETE"
echo "═══════════════════════════════════════════════════════════════════════════"
echo "Container Count: 9"
echo "Healthy Containers: $(docker compose ps --format '{{.Health}}' | grep -c healthy || echo 0)"
echo "Open Ports: $(for p in 8000 5432 6379 7474 7687 9090 3000 16686 9002; do nc -z 127.0.0.1 $p 2>/dev/null && echo -n "1"; done | wc -c)"
echo "Timestamp: $(date -u +"%Y-%m-%dT%H:%M:%SZ")"
echo "═══════════════════════════════════════════════════════════════════════════"
