cd /opt/l9
source <(grep REDIS_PASSWORD .env | sed 's/^/export /')
echo "╔════════════════════════════════════════════════════════════════╗"
echo "║ L9 PRODUCTION MRI - DEEP CHECK ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""
echo "🔍 Git: $(git rev-parse --short HEAD) | $(git branch --show-current) | $(date '+%Y-%m-%d %H:%M:%S %Z')"
echo ""

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "1. CONTAINER HEALTH"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
docker compose -f docker-compose.yml -f docker-compose.prod.yml ps --format "table {{.Name}}\t{{.Status}}" | grep -E "NAME|l9-api|l9-mcp|postgres|redis|neo4j"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "2. API ENDPOINTS"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
api_ok=$(curl -sf http://127.0.0.1:8000/health 2>/dev/null | jq -r '.status' 2>/dev/null)
api_ready=$(curl -sf http://127.0.0.1:8000/health 2>/dev/null | jq -r '.startup_ready' 2>/dev/null)
api_docs=$(curl -sf -o /dev/null -w "%{http_code}" http://127.0.0.1:8000/docs 2>/dev/null)
mcp_ok=$(curl -sf http://127.0.0.1:9002/health 2>/dev/null | jq -r '.status' 2>/dev/null)
echo "API /health: $([ "$api_ok" = "ok" ] && echo "✅" || echo "❌") (startup_ready: $api_ready)"
echo "API /docs:       $([ "$api_docs" = "200" ] && echo "✅" || echo "❌") ($api_docs)"
echo "MCP /health:     $([ "$mcp_ok" = "healthy" ] && echo "✅" || echo "❌")"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "3. DATABASE CONNECTIVITY"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
pg_ok=$(docker exec l9-postgres pg_isready -U postgres -d l9_memory >/dev/null 2>&1 && echo "ok" || echo "fail")
redis_ok=$(docker exec l9-redis redis-cli -a "$REDIS_PASSWORD" ping 2>/dev/null | grep -q PONG && echo "ok" || echo "fail")
neo4j_ok=$(curl -sf http://127.0.0.1:7474 >/dev/null 2>&1 && echo "ok" || echo "fail")
echo "PostgreSQL: $([ "$pg_ok" = "ok" ] && echo "✅" || echo "❌")"
echo "Redis: $([ "$redis_ok" = "ok" ] && echo "✅" || echo "❌")"
echo "Neo4j: $([ "$neo4j_ok" = "ok" ] && echo "✅" || echo "❌")"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "4. DATA LAYER"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
packet_count=$(docker exec l9-postgres psql -U postgres -d l9_memory -t -c "SELECT count(*) FROM packet_store;" 2>/dev/null | xargs || echo "0")
memory_count=$(docker exec l9-postgres psql -U postgres -d l9_memory -t -c "SELECT count(\*) FROM memory_packets;" 2>/dev/null | xargs || echo "0")
redis_keys=$(docker exec l9-redis redis-cli -a "$REDIS_PASSWORD" DBSIZE 2>/dev/null | grep -oE '[0-9]+' || echo "0")
db_size=$(docker exec l9-postgres psql -U postgres -d l9_memory -t -c "SELECT pg_size_pretty(pg_database_size('l9_memory'));" 2>/dev/null | xargs || echo "N/A")
echo "Packets: $packet_count"
echo "Memory Packets: $memory_count"
echo "Redis Keys: $redis_keys"
echo "DB Size: $db_size"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "5. RECENT ERRORS (last 5 min)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
api*errors=$(docker compose logs l9-api --since 5m 2>/dev/null | grep -i '"level".*"error"' | wc -l | xargs)
mcp_errors=$(docker compose logs l9-mcp-memory --since 5m 2>/dev/null | grep -i '"level".*"error"' | wc -l | xargs)
echo "API errors: $api_errors"
echo "MCP errors:      $mcp_errors"
if [ "$api*errors" -gt "0" ]; then
echo ""
echo "Last 3 API errors:"
docker compose logs l9-api --since 5m 2>/dev/null | grep -i '"level".*"error"' | tail -3 | sed 's/^/ /'
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "6. RESOURCE USAGE"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
free -h | grep -E "Mem:|Swap:"
df -h / | grep -E "Filesystem|/dev"
uptime | awk '{print "Load: " $(NF-2) " " $(NF-1) " " $NF}'

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "7. VERDICT"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
if [ "$api_ok" = "ok" ] && [ "$pg_ok" = "ok" ] && [ "$redis_ok" = "ok" ]; then
echo "╔═══════════════════════════════════════════════════════════════╗"
echo "║ ✅ ALL SYSTEMS OPERATIONAL - Production Ready ║"
echo "╚═══════════════════════════════════════════════════════════════╝"
else
echo "╔═══════════════════════════════════════════════════════════════╗"
echo "║ ❌ DEGRADED - Review sections above ║"
echo "╚═══════════════════════════════════════════════════════════════╝"
fi
