# C1 Comprehensive MRI (Medical Readiness Inspection)
# Run after container rebuild to verify full system health

cd /opt/l9
COMPOSE="docker compose -f docker-compose.yml -f docker-compose.prod.yml"

# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 1: INFRASTRUCTURE BASELINE
# ═══════════════════════════════════════════════════════════════════════════════

echo "═══════════════════════════════════════════════════════════════"
echo "SECTION 1: INFRASTRUCTURE BASELINE"
echo "═══════════════════════════════════════════════════════════════"

# 1.1 System resources
echo -e "\n[1.1] SYSTEM RESOURCES"
echo "─────────────────────"
free -h
echo ""
df -h / /var/lib/docker 2>/dev/null || df -h /
echo ""
uptime

# 1.2 Docker info
echo -e "\n[1.2] DOCKER ENGINE"
echo "───────────────────"
docker info 2>/dev/null | grep -E "Server Version|Storage Driver|Docker Root Dir|Total Memory|CPUs"

# 1.3 Configuration files
echo -e "\n[1.3] CONFIGURATION FILES"
echo "─────────────────────────"
ls -la docker-compose*.yml .env* 2>/dev/null
echo ""
echo "Git commit: $(git rev-parse --short HEAD 2>/dev/null || echo 'N/A')"
echo "Git branch: $(git branch --show-current 2>/dev/null || echo 'N/A')"

# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 2: CONTAINER STATUS
# ═══════════════════════════════════════════════════════════════════════════════

echo -e "\n═══════════════════════════════════════════════════════════════"
echo "SECTION 2: CONTAINER STATUS"
echo "═══════════════════════════════════════════════════════════════"

# 2.1 All containers (including exited)
echo -e "\n[2.1] ALL CONTAINERS"
echo "────────────────────"
$COMPOSE ps -a

# 2.2 Container health/restart counts
echo -e "\n[2.2] CONTAINER DETAILS (restarts, created, status)"
echo "────────────────────────────────────────────────────"
docker ps -a --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" | head -20

# 2.3 Docker images in use
echo -e "\n[2.3] IMAGES IN USE"
echo "───────────────────"
docker images --format "table {{.Repository}}\t{{.Tag}}\t{{.Size}}\t{{.CreatedSince}}" | grep -E "l9|postgres|neo4j|redis|NAME"

# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 3: SERVICE HEALTH CHECKS
# ═══════════════════════════════════════════════════════════════════════════════

echo -e "\n═══════════════════════════════════════════════════════════════"
echo "SECTION 3: SERVICE HEALTH CHECKS"
echo "═══════════════════════════════════════════════════════════════"

# 3.1 L9 API
echo -e "\n[3.1] L9 API HEALTH"
echo "───────────────────"
curl -sf http://127.0.0.1:8000/health 2>/dev/null && echo "" || echo "❌ API not responding"
curl -sf http://127.0.0.1:8000/api/v1/status 2>/dev/null | head -c 500 || echo "(status endpoint N/A)"

# 3.2 PostgreSQL
echo -e "\n[3.2] POSTGRESQL HEALTH"
echo "───────────────────────"
docker exec l9-postgres pg_isready -U l9_user -d l9_memory 2>/dev/null && echo "✅ PostgreSQL ready" || echo "❌ PostgreSQL not ready"
docker exec l9-postgres psql -U l9_user -d l9_memory -c "SELECT count(*) as packet_count FROM packets;" 2>/dev/null || echo "(query failed)"

# 3.3 Neo4j
echo -e "\n[3.3] NEO4J HEALTH"
echo "──────────────────"
curl -sf http://127.0.0.1:7474 2>/dev/null && echo "✅ Neo4j browser accessible" || echo "❌ Neo4j browser not responding"
curl -sf -u neo4j:${NEO4J_PASSWORD:-password} http://127.0.0.1:7474/db/neo4j/tx/commit \
  -H "Content-Type: application/json" \
  -d '{"statements":[{"statement":"RETURN 1 as test"}]}' 2>/dev/null | head -c 200 || echo "(Cypher query failed)"

# 3.4 Redis
echo -e "\n[3.4] REDIS HEALTH"
echo "──────────────────"
docker exec l9-redis redis-cli ping 2>/dev/null && echo "✅ Redis responding" || echo "❌ Redis not responding"
docker exec l9-redis redis-cli info memory 2>/dev/null | grep -E "used_memory_human|maxmemory_human" || echo "(memory info N/A)"

# 3.5 MCP Memory (if running)
echo -e "\n[3.5] MCP MEMORY HEALTH"
echo "───────────────────────"
curl -sf http://127.0.0.1:30902/health 2>/dev/null && echo "" || echo "⚠️ MCP Memory not responding (may be expected)"

# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 4: NETWORK & PORTS
# ═══════════════════════════════════════════════════════════════════════════════

echo -e "\n═══════════════════════════════════════════════════════════════"
echo "SECTION 4: NETWORK & PORTS"
echo "═══════════════════════════════════════════════════════════════"

# 4.1 Listening ports
echo -e "\n[4.1] LISTENING PORTS"
echo "─────────────────────"
ss -tlnp 2>/dev/null | grep -E "LISTEN|State" | head -20 || netstat -tlnp 2>/dev/null | head -20

# 4.2 Docker networks
echo -e "\n[4.2] DOCKER NETWORKS"
echo "─────────────────────"
docker network ls | grep -E "l9|NAME"
echo ""
docker network inspect l9_default 2>/dev/null | jq -r '.[0].Containers | to_entries[] | "\(.value.Name): \(.value.IPv4Address)"' 2>/dev/null || echo "(network inspect failed)"

# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 5: LOGS & ERRORS
# ═══════════════════════════════════════════════════════════════════════════════

echo -e "\n═══════════════════════════════════════════════════════════════"
echo "SECTION 5: LOGS & ERRORS (last 5 min)"
echo "═══════════════════════════════════════════════════════════════"

# 5.1 L9 API errors
echo -e "\n[5.1] L9 API ERRORS"
echo "───────────────────"
$COMPOSE logs l9-api --since 5m 2>/dev/null | grep -iE "error|exception|traceback|fatal|critical" | tail -20 || echo "(no recent errors)"

# 5.2 PostgreSQL errors
echo -e "\n[5.2] POSTGRESQL ERRORS"
echo "───────────────────────"
$COMPOSE logs l9-postgres --since 5m 2>/dev/null | grep -iE "error|fatal|panic" | tail -10 || echo "(no recent errors)"

# 5.3 Neo4j errors
echo -e "\n[5.3] NEO4J ERRORS"
echo "──────────────────"
$COMPOSE logs l9-neo4j --since 5m 2>/dev/null | grep -iE "error|exception|fatal" | tail -10 || echo "(no recent errors)"

# 5.4 Redis errors
echo -e "\n[5.4] REDIS ERRORS"
echo "──────────────────"
$COMPOSE logs l9-redis --since 5m 2>/dev/null | grep -iE "error|fatal" | tail -10 || echo "(no recent errors)"

# 5.5 Bootstrap status
echo -e "\n[5.5] BOOTSTRAP STATUS"
echo "──────────────────────"
$COMPOSE ps -a 2>/dev/null | grep -E "bootstrap|NAME"
$COMPOSE logs l9-bootstrap --tail=30 2>/dev/null | tail -15 || echo "(bootstrap logs N/A)"

# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 6: DATA PERSISTENCE
# ═══════════════════════════════════════════════════════════════════════════════

echo -e "\n═══════════════════════════════════════════════════════════════"
echo "SECTION 6: DATA PERSISTENCE (VOLUMES)"
echo "═══════════════════════════════════════════════════════════════"

# 6.1 Docker volumes
echo -e "\n[6.1] DOCKER VOLUMES"
echo "────────────────────"
docker volume ls | grep -E "l9|NAME"

# 6.2 Volume sizes
echo -e "\n[6.2] VOLUME SIZES"
echo "──────────────────"
for vol in $(docker volume ls -q | grep l9); do
  size=$(docker run --rm -v ${vol}:/data alpine du -sh /data 2>/dev/null | cut -f1)
  echo "$vol: $size"
done

# 6.3 PostgreSQL table counts
echo -e "\n[6.3] POSTGRESQL DATA SUMMARY"
echo "──────────────────────────────"
docker exec l9-postgres psql -U l9_user -d l9_memory -c "
SELECT 
  (SELECT count(*) FROM packets) as packets,
  (SELECT count(*) FROM memory_packets) as memory_packets,
  (SELECT pg_size_pretty(pg_database_size('l9_memory'))) as db_size;
" 2>/dev/null || echo "(query failed)"

# 6.4 Neo4j node counts
echo -e "\n[6.4] NEO4J DATA SUMMARY"
echo "────────────────────────"
curl -sf -u neo4j:${NEO4J_PASSWORD:-password} http://127.0.0.1:7474/db/neo4j/tx/commit \
  -H "Content-Type: application/json" \
  -d '{"statements":[{"statement":"MATCH (n) RETURN labels(n)[0] as label, count(*) as count ORDER BY count DESC LIMIT 10"}]}' 2>/dev/null | jq -r '.results[0].data[].row | "\(.[0]): \(.[1])"' 2>/dev/null || echo "(query failed)"

# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 7: API ENDPOINT TESTS
# ═══════════════════════════════════════════════════════════════════════════════

echo -e "\n═══════════════════════════════════════════════════════════════"
echo "SECTION 7: API ENDPOINT TESTS"
echo "═══════════════════════════════════════════════════════════════"

# 7.1 Critical endpoints
echo -e "\n[7.1] CRITICAL ENDPOINTS"
echo "────────────────────────"
endpoints=(
  "http://127.0.0.1:8000/health"
  "http://127.0.0.1:8000/api/v1/status"
  "http://127.0.0.1:8000/docs"
  "http://127.0.0.1:8000/openapi.json"
)

for ep in "${endpoints[@]}"; do
  status=$(curl -sf -o /dev/null -w "%{http_code}" "$ep" 2>/dev/null || echo "000")
  if [ "$status" = "200" ]; then
    echo "✅ $ep ($status)"
  else
    echo "❌ $ep ($status)"
  fi
done

# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 8: ENVIRONMENT VALIDATION
# ═══════════════════════════════════════════════════════════════════════════════

echo -e "\n═══════════════════════════════════════════════════════════════"
echo "SECTION 8: ENVIRONMENT VALIDATION"
echo "═══════════════════════════════════════════════════════════════"

# 8.1 Required env vars (existence check, secrets redacted)
echo -e "\n[8.1] REQUIRED ENV VARS"
echo "───────────────────────"
required_vars="DATABASE_URL REDIS_URL NEO4J_URL OPENAI_API_KEY"
for var in $required_vars; do
  if grep -q "^${var}=" .env 2>/dev/null; then
    echo "✅ $var is set"
  else
    echo "❌ $var is MISSING"
  fi
done

# 8.2 Env file preview (secrets redacted)
echo -e "\n[8.2] ENV FILE (redacted)"
echo "─────────────────────────"
cat .env 2>/dev/null | sed 's/\(PASSWORD\|KEY\|SECRET\|TOKEN\)=.*/\1=***REDACTED***/g' | head -30

# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 9: SUMMARY
# ═══════════════════════════════════════════════════════════════════════════════

echo -e "\n═══════════════════════════════════════════════════════════════"
echo "SECTION 9: MRI SUMMARY"
echo "═══════════════════════════════════════════════════════════════"

echo -e "\nTimestamp: $(date '+%Y-%m-%d %H:%M:%S %Z')"
echo "Hostname: $(hostname)"
echo "Git commit: $(git rev-parse --short HEAD 2>/dev/null || echo 'N/A')"
echo ""

# Quick status summary
echo "SERVICE STATUS SUMMARY:"
echo "───────────────────────"
api_ok=$(curl -sf http://127.0.0.1:8000/health >/dev/null 2>&1 && echo "✅" || echo "❌")
pg_ok=$(docker exec l9-postgres pg_isready -U l9_user >/dev/null 2>&1 && echo "✅" || echo "❌")
neo_ok=$(curl -sf http://127.0.0.1:7474 >/dev/null 2>&1 && echo "✅" || echo "❌")
redis_ok=$(docker exec l9-redis redis-cli ping >/dev/null 2>&1 && echo "✅" || echo "❌")

echo "  L9 API:     $api_ok"
echo "  PostgreSQL: $pg_ok"
echo "  Neo4j:      $neo_ok"
echo "  Redis:      $redis_ok"
echo ""

if [ "$api_ok" = "✅" ] && [ "$pg_ok" = "✅" ] && [ "$redis_ok" = "✅" ]; then
  echo "╔═══════════════════════════════════════════════════════════════╗"
  echo "║  ✅ MRI PASSED - Core services healthy                       ║"
  echo "╚═══════════════════════════════════════════════════════════════╝"
else
  echo "╔═══════════════════════════════════════════════════════════════╗"
  echo "║  ❌ MRI FAILED - Check sections above for issues             ║"
  echo "╚═══════════════════════════════════════════════════════════════╝"
fi
