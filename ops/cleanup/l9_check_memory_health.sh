#!/usr/bin/env bash
# ops/cleanup/l9_check_memory_health.sh
# Purpose: Verify L9 memory substrate connectivity (Postgres, Neo4j, Redis, API).
# Non-destructive read-only probe. Exit 0 = all healthy, exit 1 = at least one unhealthy.
set -euo pipefail
IFS=$'\n\t'

readonly SCRIPT_NAME="$(basename "$0")"

# Container names (match actual C1 deployment)
readonly API_CONTAINER="l9-l9-api-1"
readonly MCP_CONTAINER="l9-l9-mcp-memory-1"
readonly PG_CONTAINER="l9-postgres"
readonly NEO4J_CONTAINER="l9-neo4j"
readonly REDIS_CONTAINER="l9-redis"

# ── Output helpers ───────────────────────────────────────────

RED='\033[0;31m'
GRN='\033[0;32m'
YLW='\033[0;33m'
RST='\033[0m'

status_ok()   { echo -e "  ${GRN}✅${RST} $1"; }
status_fail() { echo -e "  ${RED}❌${RST} $1"; }
status_warn() { echo -e "  ${YLW}⚠️${RST}  $1"; }

FAILURES=0

check_result() {
    local name="$1"
    local exit_code="$2"
    local detail="${3:-}"

    if (( exit_code == 0 )); then
        status_ok "${name}=HEALTHY ${detail}"
    else
        status_fail "${name}=UNHEALTHY ${detail}"
        FAILURES=$((FAILURES + 1))
    fi
}

print_header() {
    echo ""
    echo "── $1 ────────────────────────────────────────"
}

print_status() {
    local section="$1" name="$2" type="$3" detail="$4"
    if [[ "$type" == "pass" ]]; then
        status_ok "${name}=HEALTHY (${detail})"
    elif [[ "$type" == "fail" ]]; then
        status_fail "${name}=UNHEALTHY (${detail})"
        FAILURES=$((FAILURES + 1))
    else
        echo "  📊 ${name}: ${detail}"
    fi
}

# ── Checks ───────────────────────────────────────────────────

check_container_running() {
    local name="$1"
    local state
    state=$(docker inspect --format='{{.State.Status}}' "$name" 2>/dev/null || echo "not_found")

    if [[ "$state" == "running" ]]; then
        local health
        health=$(docker inspect --format='{{.State.Health.Status}}' "$name" 2>/dev/null || echo "none")
        check_result "CONTAINER_${name}" 0 "(state=${state}, health=${health})"
        return 0
    else
        check_result "CONTAINER_${name}" 1 "(state=${state})"
        return 1
    fi
}

check_postgres() {
    echo ""
    echo "── Postgres ──────────────────────────────────────"

    if ! check_container_running "${PG_CONTAINER}"; then
        return
    fi

    # pg_isready
    if docker exec "${PG_CONTAINER}" pg_isready -U postgres -q 2>/dev/null; then
        check_result "PG_ISREADY" 0
    else
        check_result "PG_ISREADY" 1
        return
    fi

    # Query test
    local query_result
    query_result=$(docker exec "${PG_CONTAINER}" psql -U postgres -d l9_memory -t -c "SELECT 1;" 2>&1 || echo "FAIL")
    if echo "$query_result" | grep -q "1"; then
        check_result "PG_QUERY" 0 "(SELECT 1 OK)"
    else
        check_result "PG_QUERY" 1 "(${query_result})"
    fi

    # Disk usage inside PG data dir
    local pg_du
    pg_du=$(docker exec "${PG_CONTAINER}" du -sh /var/lib/postgresql/data 2>/dev/null | awk '{print $1}' || echo "unknown")
    echo "  📊 PG data dir size: ${pg_du}"

    # WAL size
    local wal_size
    wal_size=$(docker exec "${PG_CONTAINER}" du -sh /var/lib/postgresql/data/pg_wal 2>/dev/null | awk '{print $1}' || echo "unknown")
    echo "  📊 PG WAL size: ${wal_size}"
}

check_neo4j() {
    echo ""
    echo "── Neo4j ─────────────────────────────────────────"

    if ! check_container_running "${NEO4J_CONTAINER}"; then
        return
    fi

    local http_code
    http_code=$(docker exec "${API_CONTAINER}" curl -s -o /dev/null -w "%{http_code}" --max-time 5 "http://neo4j:7474" 2>/dev/null || echo "000")
    if [[ "$http_code" == "200" ]]; then
        check_result "NEO4J_HTTP" 0 "(HTTP ${http_code})"
    else
        check_result "NEO4J_HTTP" 1 "(HTTP ${http_code})"
    fi
}

check_redis() {
    local section="REDIS"
    print_header "$section"

    # ── Pull auth from the API container's env (never hardcode creds) ──
    local redis_pass
    redis_pass=$(docker exec "${API_CONTAINER}" sh -c 'echo "$REDIS_PASSWORD"' 2>/dev/null || echo "")

    # ── Build the auth flag array once ──
    local auth_flags=()
    if [[ -n "$redis_pass" ]]; then
        auth_flags=(-a "$redis_pass" --no-auth-warning)
    fi

    # ── 1. PING ──
    local ping_result
    ping_result=$(docker exec "${REDIS_CONTAINER}" redis-cli "${auth_flags[@]}" ping 2>/dev/null || echo "FAIL")
    if [[ "$ping_result" == "PONG" ]]; then
        print_status "$section" "PING" "pass" "PONG"
    else
        print_status "$section" "PING" "fail" "$ping_result"
        return
    fi

    # ── 2. Memory usage ──
    local redis_mem
    redis_mem=$(docker exec "${REDIS_CONTAINER}" redis-cli "${auth_flags[@]}" info memory 2>/dev/null \
        | grep "used_memory_human" | cut -d: -f2 | tr -d '\r' || echo "unknown")
    print_status "$section" "MEMORY" "info" "$redis_mem"

    # ── 3. Connected clients ──
    local redis_clients
    redis_clients=$(docker exec "${REDIS_CONTAINER}" redis-cli "${auth_flags[@]}" info clients 2>/dev/null \
        | grep "connected_clients" | cut -d: -f2 | tr -d '\r' || echo "unknown")
    print_status "$section" "CLIENTS" "info" "$redis_clients"

    # ── 4. Key count (all DBs) ──
    local redis_keys
    redis_keys=$(docker exec "${REDIS_CONTAINER}" redis-cli "${auth_flags[@]}" info keyspace 2>/dev/null \
        | grep "^db" || echo "no keys")
    print_status "$section" "KEYSPACE" "info" "$redis_keys"

    # ── 5. Uptime ──
    local redis_uptime
    redis_uptime=$(docker exec "${REDIS_CONTAINER}" redis-cli "${auth_flags[@]}" info server 2>/dev/null \
        | grep "uptime_in_seconds" | cut -d: -f2 | tr -d '\r' || echo "unknown")
    print_status "$section" "UPTIME" "info" "${redis_uptime}s"
}

check_api() {
    echo ""
    echo "── L9 API ────────────────────────────────────────"

    if ! check_container_running "${API_CONTAINER}"; then
        return
    fi

    local http_code body
    http_code=$(curl -s -o /tmp/l9_health_body -w "%{http_code}" --max-time 10 "http://127.0.0.1:8000/health" 2>/dev/null || echo "000")
    body=$(cat /tmp/l9_health_body 2>/dev/null || echo "")

    if [[ "$http_code" == "200" ]]; then
        check_result "API_HEALTH" 0 "(HTTP ${http_code})"
    else
        check_result "API_HEALTH" 1 "(HTTP ${http_code})"
    fi

    # Services endpoint
    local svc_code svc_body
    svc_code=$(curl -s -o /tmp/l9_svc_body -w "%{http_code}" --max-time 10 "http://127.0.0.1:8000/health/services" 2>/dev/null || echo "000")
    svc_body=$(cat /tmp/l9_svc_body 2>/dev/null || echo "")

    if [[ "$svc_code" == "200" ]]; then
        check_result "API_SERVICES" 0 "(HTTP ${svc_code})"
    else
        check_result "API_SERVICES" 1 "(HTTP ${svc_code})"
    fi
}

check_mcp_memory() {
    echo ""
    echo "── MCP Memory ────────────────────────────────────"

    if ! check_container_running "${MCP_CONTAINER}"; then
        return
    fi

    local mcp_code
    mcp_code=$(curl -s -o /dev/null -w "%{http_code}" --max-time 10 "http://127.0.0.1:9002/health" 2>/dev/null || echo "000")
    if [[ "$mcp_code" == "200" ]]; then
        check_result "MCP_HEALTH" 0 "(HTTP ${mcp_code})"
    else
        check_result "MCP_HEALTH" 1 "(HTTP ${mcp_code})"
    fi
}

check_memory_dsn_from_api() {
    echo ""
    echo "── Memory DSN (from API container) ──────────────"

    local dsn_check
    dsn_check=$(docker exec "${API_CONTAINER}" sh -lc '
python3 - << "PY"
import asyncio, os, sys
try:
    import asyncpg
except ImportError:
    print("SKIP:asyncpg_not_available"); sys.exit(0)

dsn = os.environ.get("MEMORY_DSN") or os.environ.get("DATABASE_URL", "")
if not dsn:
    print("FAIL:no_dsn_configured"); sys.exit(1)

async def probe():
    conn = await asyncpg.connect(dsn, timeout=10)
    result = await conn.fetchval("SELECT 1")
    await conn.close()
    return result

try:
    r = asyncio.run(probe())
    print(f"OK:query_returned_{r}")
except Exception as e:
    print(f"FAIL:{type(e).__name__}:{e}")
    sys.exit(1)
PY
' 2>/dev/null || echo "FAIL:exec_error")

    if [[ "$dsn_check" == OK:* ]]; then
        check_result "MEMORY_DSN_CONN" 0 "(${dsn_check})"
    elif [[ "$dsn_check" == SKIP:* ]]; then
        status_warn "MEMORY_DSN_CONN=SKIPPED (${dsn_check})"
    else
        check_result "MEMORY_DSN_CONN" 1 "(${dsn_check})"
    fi
}

# ── Main ─────────────────────────────────────────────────────

main() {
    echo ""
    echo "╔══════════════════════════════════════════════════╗"
    echo "║       L9 MEMORY SUBSTRATE HEALTH CHECK          ║"
    echo "║       $(date '+%Y-%m-%d %H:%M:%S %Z')              ║"
    echo "╚══════════════════════════════════════════════════╝"

    # Host disk
    echo ""
    echo "── Host Disk ─────────────────────────────────────"
    df -h / | tail -1 | awk '{printf "  📊 Disk: %s used (%s), %s available\n", $3, $5, $4}'

    check_postgres
    check_neo4j
    check_redis
    check_api
    check_mcp_memory
    check_memory_dsn_from_api

    echo ""
    echo "══════════════════════════════════════════════════"
    if (( FAILURES == 0 )); then
        echo -e "  ${GRN}ALL SUBSTRATES HEALTHY${RST} (0 failures)"
    else
        echo -e "  ${RED}${FAILURES} SUBSTRATE(S) UNHEALTHY${RST}"
    fi
    echo "══════════════════════════════════════════════════"
    echo ""

    # Structured output for automation
    echo "L9_HEALTH_FAILURES=${FAILURES}"

    exit $(( FAILURES > 0 ? 1 : 0 ))
}

main "$@"
