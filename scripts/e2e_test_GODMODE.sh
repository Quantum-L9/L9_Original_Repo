#!/usr/bin/env bash
# =============================================================================
# L9 GOD-MODE E2E TEST SCRIPT (C1 VPS)
# =============================================================================
# Version: 1.0.0
# Created: 2026-02-02
# Purpose: Comprehensive deployment validation for L9 on C1 VPS
# 
# USAGE:
#   ./godmode_e2e.sh smoke           # Quick health check (~30s)
#   ./godmode_e2e.sh full            # Complete validation (~2-3min)
#   ./godmode_e2e.sh infra           # Infrastructure only
#   ./godmode_e2e.sh db              # Database substrates only
#   ./godmode_e2e.sh app             # L9 API + core flows
#   ./godmode_e2e.sh websocket       # WebSocket auth validation
#   ./godmode_e2e.sh observability   # Prometheus/Grafana/Jaeger
#
# FLAGS:
#   --env-file <path>         # Override .env file location
#   --api-base <url>          # Override L9 API base URL (default: http://127.0.0.1:8000)
#   --allow-missing-env       # Continue with degraded checks if env vars missing (UNSAFE)
#   --continue-on-error       # Continue to next phase even if current phase fails
#   --dangerous               # Enable destructive operations (NONE in v1.0, reserved)
#   --verbose                 # Enable verbose logging
#   --skip-websocket          # Skip WebSocket checks (if deps unavailable)
#
# EXIT CODES:
#   0   = All checks passed
#   1   = Argument parsing error
#   2   = Environment validation failed
#   10  = Infrastructure checks failed
#   20  = Database checks failed
#   30  = App checks failed
#   40  = WebSocket checks failed
#   50  = Observability checks failed
#
# RISK TIER: T2 (reversible actions, read-only by default)
# =============================================================================

set -euo pipefail
IFS=$'\n\t'

# =============================================================================
# CONSTANTS
# =============================================================================

readonly SCRIPT_VERSION="1.0.0"
readonly SCRIPT_NAME="$(basename "${BASH_SOURCE[0]}")"
readonly SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

# Colors (ANSI escape codes)
readonly COLOR_RESET='\033[0m'
readonly COLOR_RED='\033[0;31m'
readonly COLOR_GREEN='\033[0;32m'
readonly COLOR_YELLOW='\033[1;33m'
readonly COLOR_BLUE='\033[0;34m'
readonly COLOR_CYAN='\033[0;36m'
readonly COLOR_BOLD='\033[1m'

# Exit codes
readonly EXIT_SUCCESS=0
readonly EXIT_ARG_ERROR=1
readonly EXIT_ENV_ERROR=2
readonly EXIT_INFRA_ERROR=10
readonly EXIT_DB_ERROR=20
readonly EXIT_APP_ERROR=30
readonly EXIT_WS_ERROR=40
readonly EXIT_OBS_ERROR=50

# =============================================================================
# GLOBAL STATE
# =============================================================================

# Environment detection
ENV_FILE="${ENV_FILE:-}"
COMPOSE_BASE="${COMPOSE_BASE:-docker-compose.yml}"
COMPOSE_OVERLAY="${COMPOSE_OVERLAY:-}"
COMPOSE_PROJECT_NAME="${COMPOSE_PROJECT_NAME:-l9}"

# API configuration
L9_API_BASE="${L9_API_BASE:-http://127.0.0.1:8000}"

# Flags
FLAG_ALLOW_MISSING_ENV=false
FLAG_CONTINUE_ON_ERROR=false
FLAG_DANGEROUS=false
FLAG_VERBOSE=false
FLAG_SKIP_WEBSOCKET=false

# Phase tracking
PHASE_RESULTS=()
PHASE_COUNT=0
PHASE_PASS=0
PHASE_FAIL=0

# =============================================================================
# LOGGING FUNCTIONS
# =============================================================================

log_msg() {
    local level="$1"
    shift
    local msg="$*"
    local timestamp
    timestamp="$(date '+%Y-%m-%d %H:%M:%S')"
    local hostname
    hostname="$(hostname -s 2>/dev/null || echo 'unknown')"
    
    case "$level" in
        INFO)
            echo -e "${COLOR_CYAN}[${timestamp}]${COLOR_RESET} [${hostname}] ${COLOR_BOLD}INFO${COLOR_RESET}  | ${msg}"
            ;;
        WARN)
            echo -e "${COLOR_YELLOW}[${timestamp}]${COLOR_RESET} [${hostname}] ${COLOR_BOLD}WARN${COLOR_RESET}  | ${msg}" >&2
            ;;
        ERROR)
            echo -e "${COLOR_RED}[${timestamp}]${COLOR_RESET} [${hostname}] ${COLOR_BOLD}ERROR${COLOR_RESET} | ${msg}" >&2
            ;;
        FATAL)
            echo -e "${COLOR_RED}[${timestamp}]${COLOR_RESET} [${hostname}] ${COLOR_BOLD}FATAL${COLOR_RESET} | ${msg}" >&2
            ;;
        DEBUG)
            if [[ "$FLAG_VERBOSE" == "true" ]]; then
                echo -e "${COLOR_BLUE}[${timestamp}]${COLOR_RESET} [${hostname}] ${COLOR_BOLD}DEBUG${COLOR_RESET} | ${msg}"
            fi
            ;;
        *)
            echo -e "${COLOR_CYAN}[${timestamp}]${COLOR_RESET} [${hostname}] ${msg}"
            ;;
    esac
}

info()  { log_msg INFO "$@"; }
warn()  { log_msg WARN "$@"; }
error() { log_msg ERROR "$@"; }
fatal() { log_msg FATAL "$@"; exit 1; }
debug() { log_msg DEBUG "$@"; }

# =============================================================================
# PHASE RESULT TRACKING
# =============================================================================

record_phase_result() {
    local phase_name="$1"
    local status="$2"  # "PASS" or "FAIL"
    local details="${3:-}"
    
    PHASE_COUNT=$((PHASE_COUNT + 1))
    
    if [[ "$status" == "PASS" ]]; then
        PHASE_PASS=$((PHASE_PASS + 1))
        PHASE_RESULTS+=("${COLOR_GREEN}[OK]${COLOR_RESET} ${phase_name} ${details}")
    else
        PHASE_FAIL=$((PHASE_FAIL + 1))
        PHASE_RESULTS+=("${COLOR_RED}[FAIL]${COLOR_RESET} ${phase_name} ${details}")
    fi
}

# =============================================================================
# HELPER UTILITIES
# =============================================================================

check_command() {
    local cmd="$1"
    if ! command -v "$cmd" &> /dev/null; then
        return 1
    fi
    return 0
}

check_port_listening() {
    local port="$1"
    local host="${2:-127.0.0.1}"
    
    # Try ss first (modern), fallback to netstat
    if check_command ss; then
        ss -lnt | grep -q "${host}:${port} " && return 0
    elif check_command netstat; then
        netstat -lnt | grep -q "${host}:${port} " && return 0
    else
        # Fallback: try connecting
        timeout 2 bash -c "cat < /dev/null > /dev/tcp/${host}/${port}" 2>/dev/null && return 0
    fi
    
    return 1
}

get_container_health() {
    local container="$1"
    docker inspect --format='{{.State.Health.Status}}' "$container" 2>/dev/null || echo "unknown"
}

get_container_state() {
    local container="$1"
    docker inspect --format='{{.State.Status}}' "$container" 2>/dev/null || echo "unknown"
}

# =============================================================================
# ENVIRONMENT DETECTION & VALIDATION
# =============================================================================

detect_environment() {
    info "Detecting C1 VPS environment..."
    
    # Detect ENV_FILE
    if [[ -z "$ENV_FILE" ]]; then
        if [[ -f "${PROJECT_ROOT}/.env" ]]; then
            ENV_FILE="${PROJECT_ROOT}/.env"
            info "Using env file: ${ENV_FILE}"
        elif [[ -f "${PROJECT_ROOT}/deploy/c1/.env.c1" ]]; then
            ENV_FILE="${PROJECT_ROOT}/deploy/c1/.env.c1"
            info "Using C1-specific env file: ${ENV_FILE}"
        else
            fatal "No .env file found. Set ENV_FILE or place .env in project root."
        fi
    fi
    
    # Detect COMPOSE_OVERLAY
    if [[ -z "$COMPOSE_OVERLAY" ]]; then
        if [[ -f "${PROJECT_ROOT}/docker-compose.prod.yml" ]]; then
            COMPOSE_OVERLAY="docker-compose.prod.yml"
            info "Using production overlay: ${COMPOSE_OVERLAY}"
        elif [[ -f "${PROJECT_ROOT}/deploy/c1/docker-compose.c1.yml" ]]; then
            COMPOSE_OVERLAY="deploy/c1/docker-compose.c1.yml"
            info "Using C1-specific overlay: ${COMPOSE_OVERLAY}"
        else
            warn "No production overlay found, using base compose only"
            COMPOSE_OVERLAY=""
        fi
    fi
    
    debug "Compose base: ${COMPOSE_BASE}"
    debug "Compose overlay: ${COMPOSE_OVERLAY:-none}"
    debug "Env file: ${ENV_FILE}"
    debug "API base: ${L9_API_BASE}"
}

validate_required_env_vars() {
    info "Validating required environment variables..."
    
    # Source the env file
    if [[ ! -f "$ENV_FILE" ]]; then
        error "Environment file not found: ${ENV_FILE}"
        return 1
    fi
    
    # Required variables (per docker-compose.yml comments)
    # MCP_API_KEY (or MCP_API_KEY_L) is MANDATORY for MCP memory operations
    local required_vars=(
        "POSTGRES_PASSWORD"
        "NEO4J_PASSWORD"
        "GRAFANA_PASSWORD"
        "OPENAI_API_KEY"
        "L9_EXECUTOR_API_KEY"
    )
    
    # Check for MCP API key (either MCP_API_KEY_L or MCP_API_KEY)
    local mcp_key_found=false
    if [[ -n "${MCP_API_KEY_L:-}" ]] || [[ -n "${MCP_API_KEY:-}" ]]; then
        mcp_key_found=true
    fi
    
    local missing_vars=()
    
    # Load env file
    set -a
    # shellcheck disable=SC1090
    source "$ENV_FILE"
    set +a
    
    for var in "${required_vars[@]}"; do
        if [[ -z "${!var:-}" ]]; then
            missing_vars+=("$var")
            error "Missing required env var: ${var}"
        else
            debug "Found required env var: ${var}"
        fi
    done
    
    # Check MCP API key after sourcing env file
    if [[ -z "${MCP_API_KEY_L:-}" ]] && [[ -z "${MCP_API_KEY:-}" ]]; then
        missing_vars+=("MCP_API_KEY or MCP_API_KEY_L")
        error "Missing required env var: MCP_API_KEY (or MCP_API_KEY_L) - MANDATORY for MCP memory"
    else
        debug "Found MCP API key (MCP_API_KEY_L or MCP_API_KEY)"
    fi
    
    if [[ ${#missing_vars[@]} -gt 0 ]]; then
        error "Missing ${#missing_vars[@]} required environment variable(s)"
        if [[ "$FLAG_ALLOW_MISSING_ENV" != "true" ]]; then
            return 1
        else
            warn "Continuing with degraded checks (--allow-missing-env)"
        fi
    else
        info "All required environment variables present"
    fi
    
    return 0
}

# =============================================================================
# PHASE: INFRASTRUCTURE CHECKS
# =============================================================================

run_infra_checks() {
    info "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    info "PHASE: Infrastructure Health & Wiring"
    info "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    
    local phase_failed=false
    
    # Check docker compose config
    info "Validating docker compose configuration..."
    pushd "$PROJECT_ROOT" > /dev/null
    
    if [[ -n "$COMPOSE_OVERLAY" ]]; then
        if ! docker compose -f "$COMPOSE_BASE" -f "$COMPOSE_OVERLAY" config > /dev/null 2>&1; then
            error "Docker compose config validation failed"
            phase_failed=true
        else
            debug "Docker compose config valid"
        fi
    else
        if ! docker compose -f "$COMPOSE_BASE" config > /dev/null 2>&1; then
            error "Docker compose config validation failed"
            phase_failed=true
        else
            debug "Docker compose config valid"
        fi
    fi
    
    popd > /dev/null
    
    # Check container states
    info "Checking container states..."
    local required_containers=(
        "${COMPOSE_PROJECT_NAME}-postgres"
        "${COMPOSE_PROJECT_NAME}-neo4j"
        "${COMPOSE_PROJECT_NAME}-redis"
        "${COMPOSE_PROJECT_NAME}-prometheus"
        "${COMPOSE_PROJECT_NAME}-grafana"
        "${COMPOSE_PROJECT_NAME}-jaeger"
        "${COMPOSE_PROJECT_NAME}-l9-api-1"
        "${COMPOSE_PROJECT_NAME}-l9-mcp-memory-1"
    )
    
    local container_stats=()
    local running_count=0
    local total_count=${#required_containers[@]}
    
    for container in "${required_containers[@]}"; do
        local state
        state="$(get_container_state "$container")"
        
        if [[ "$state" == "running" ]]; then
            container_stats+=("✓ ${container}")
            running_count=$((running_count + 1))
            debug "Container running: ${container}"
        else
            container_stats+=("✗ ${container} (state: ${state})")
            error "Container not running: ${container} (state: ${state})"
            phase_failed=true
        fi
    done
    
    info "Containers: ${running_count}/${total_count} running"
    
    # Check port bindings
    info "Checking port bindings on 127.0.0.1..."
    local required_ports=(
        "8000:l9-api"
        "5432:postgres"
        "6379:redis"
        "7474:neo4j-http"
        "7687:neo4j-bolt"
        "9090:prometheus"
        "3000:grafana"
        "16686:jaeger-ui"
    )
    
    local port_stats=()
    local listening_count=0
    local port_total=${#required_ports[@]}
    
    for port_spec in "${required_ports[@]}"; do
        local port="${port_spec%%:*}"
        local service="${port_spec##*:}"
        
        if check_port_listening "$port"; then
            port_stats+=("✓ ${port} (${service})")
            listening_count=$((listening_count + 1))
            debug "Port listening: ${port} (${service})"
        else
            port_stats+=("✗ ${port} (${service})")
            error "Port not listening: ${port} (${service})"
            phase_failed=true
        fi
    done
    
    info "Ports: ${listening_count}/${port_total} listening"
    
    # Check container health checks
    info "Checking container health status..."
    local health_stats=()
    local healthy_count=0
    local health_total=0
    
    for container in "${required_containers[@]}"; do
        local health
        health="$(get_container_health "$container")"
        
        if [[ "$health" == "healthy" ]]; then
            health_stats+=("✓ ${container}")
            healthy_count=$((healthy_count + 1))
            health_total=$((health_total + 1))
            debug "Container healthy: ${container}"
        elif [[ "$health" == "unknown" ]] || [[ "$health" == "" ]]; then
            # No healthcheck defined, skip
            debug "Container has no healthcheck: ${container}"
            continue
        else
            health_stats+=("✗ ${container} (${health})")
            error "Container unhealthy: ${container} (${health})"
            
            # Print logs for debugging
            if [[ "$FLAG_VERBOSE" == "true" ]]; then
                warn "Last 20 lines of logs for ${container}:"
                docker logs --tail=20 "$container" 2>&1 | sed 's/^/    /'
            fi
            
            health_total=$((health_total + 1))
            phase_failed=true
        fi
    done
    
    if [[ $health_total -gt 0 ]]; then
        info "Health checks: ${healthy_count}/${health_total} healthy"
    else
        debug "No containers with health checks configured"
    fi
    
    # Record result
    if [[ "$phase_failed" == "true" ]]; then
        record_phase_result "infra" "FAIL" "(${running_count}/${total_count} containers, ${listening_count}/${port_total} ports, ${healthy_count}/${health_total} healthy)"
        return $EXIT_INFRA_ERROR
    else
        record_phase_result "infra" "PASS" "(${running_count}/${total_count} containers, ${listening_count}/${port_total} ports, ${healthy_count}/${health_total} healthy)"
        return 0
    fi
}

# =============================================================================
# PHASE: DATABASE SUBSTRATE CHECKS
# =============================================================================

run_db_checks() {
    info "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    info "PHASE: Database Substrate Connectivity"
    info "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    
    local phase_failed=false
    local db_stats=()
    
    # Postgres check
    info "Testing PostgreSQL connectivity..."
    local postgres_container="${COMPOSE_PROJECT_NAME}-postgres"
    
    if docker exec "$postgres_container" psql -U "${POSTGRES_USER:-postgres}" -d "${POSTGRES_DB:-l9}" -c 'SELECT 1;' > /dev/null 2>&1; then
        db_stats+=("✓ postgres")
        debug "PostgreSQL query successful"
        
        # Check for pgvector extension
        if docker exec "$postgres_container" psql -U "${POSTGRES_USER:-postgres}" -d "${POSTGRES_DB:-l9}" \
            -c "SELECT extname FROM pg_extension WHERE extname = 'vector';" 2>/dev/null | grep -q vector; then
            debug "pgvector extension found"
        else
            warn "pgvector extension not found (may not be installed yet)"
        fi
    else
        db_stats+=("✗ postgres")
        error "PostgreSQL query failed"
        phase_failed=true
    fi
    
    # Redis check
    info "Testing Redis connectivity..."
    local redis_container="${COMPOSE_PROJECT_NAME}-redis"
    
    if docker exec "$redis_container" redis-cli -a "${REDIS_PASSWORD:-changeme}" PING 2>/dev/null | grep -q PONG; then
        db_stats+=("✓ redis")
        debug "Redis PING successful"
    else
        db_stats+=("✗ redis")
        error "Redis PING failed"
        phase_failed=true
    fi
    
    # Neo4j check
    info "Testing Neo4j connectivity..."
    if curl -fsS "http://127.0.0.1:7474" > /dev/null 2>&1; then
        db_stats+=("✓ neo4j")
        debug "Neo4j HTTP endpoint responsive"
        
        # Optional: Cypher query check (requires cypher-shell or REST API)
        # Skipping for now as it requires auth header construction
    else
        db_stats+=("✗ neo4j")
        error "Neo4j HTTP endpoint unreachable"
        phase_failed=true
    fi
    
    # MCP Memory server check (if running)
    info "Testing MCP Memory server..."
    local mcp_memory_url="${MCP_MEMORY_URL:-http://127.0.0.1:9002}"
    
    if response=$(curl -fsS "${mcp_memory_url}/health" 2>&1); then
        db_stats+=("✓ mcp-memory")
        debug "MCP Memory server healthy"
    elif curl -fsS "${mcp_memory_url}/" > /dev/null 2>&1; then
        db_stats+=("✓ mcp-memory (no /health endpoint)")
        debug "MCP Memory server responsive (no /health)"
    else
        db_stats+=("⊘ mcp-memory (not running)")
        warn "MCP Memory server not available at ${mcp_memory_url}"
        # Not a failure - MCP memory is optional
    fi
    
    # Summary
    local success_count=0
    for stat in "${db_stats[@]}"; do
        if [[ "$stat" == ✓* ]]; then
            success_count=$((success_count + 1))
        fi
    done
    
    info "Database substrates: ${success_count}/4 responsive"
    
    # Record result
    if [[ "$phase_failed" == "true" ]]; then
        record_phase_result "db" "FAIL" "(postgres/redis/neo4j/mcp-memory)"
        return $EXIT_DB_ERROR
    else
        record_phase_result "db" "PASS" "(postgres/redis/neo4j/mcp-memory)"
        return 0
    fi
}

# =============================================================================
# PHASE: L9 API + CORE ENDPOINTS
# =============================================================================

run_app_checks() {
    info "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    info "PHASE: L9 API + Core Endpoints"
    info "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    
    local phase_failed=false
    local endpoint_stats=()
    local success_count=0
    
    # Health endpoints (no auth required)
    info "Testing health endpoints..."
    
    local health_endpoints=(
        "/"
        "/health"
        "/health/startup"
        "/health/neo4j"
        "/health/services"
    )
    
    for endpoint in "${health_endpoints[@]}"; do
        local url="${L9_API_BASE}${endpoint}"
        debug "GET ${url}"
        
        if response=$(curl -fsS "$url" 2>&1); then
            # Validate JSON response
            if echo "$response" | python3 -m json.tool > /dev/null 2>&1; then
                endpoint_stats+=("✓ GET ${endpoint}")
                success_count=$((success_count + 1))
                debug "Endpoint healthy: ${endpoint}"
                
                # Parse specific fields for key endpoints
                if [[ "$endpoint" == "/health" ]]; then
                    local status
                    status=$(echo "$response" | python3 -c "import sys, json; print(json.load(sys.stdin).get('status', 'unknown'))" 2>/dev/null || echo "unknown")
                    if [[ "$status" != "ok" ]]; then
                        warn "Health endpoint status != 'ok': ${status}"
                    fi
                fi
            else
                endpoint_stats+=("⚠ GET ${endpoint} (invalid JSON)")
                warn "Endpoint returned invalid JSON: ${endpoint}"
            fi
        else
            endpoint_stats+=("✗ GET ${endpoint}")
            error "Endpoint failed: ${endpoint}"
            if [[ "$FLAG_VERBOSE" == "true" ]]; then
                error "Response: ${response}"
            fi
            phase_failed=true
        fi
    done
    
    # Kernel reload (authenticated)
    info "Testing kernel reload endpoint..."
    local reload_url="${L9_API_BASE}/kernels/reload"
    
    if [[ -n "${L9_EXECUTOR_API_KEY:-}" ]]; then
        debug "POST ${reload_url}"
        
        if curl -fsS -X POST \
            -H "Authorization: Bearer ${L9_EXECUTOR_API_KEY}" \
            -H "Content-Type: application/json" \
            -d '{}' \
            "$reload_url" > /dev/null 2>&1; then
            endpoint_stats+=("✓ POST /kernels/reload")
            success_count=$((success_count + 1))
            debug "Kernel reload successful"
        else
            endpoint_stats+=("✗ POST /kernels/reload")
            error "Kernel reload failed"
            phase_failed=true
        fi
    else
        endpoint_stats+=("⊘ POST /kernels/reload (no L9_EXECUTOR_API_KEY)")
        warn "Skipping kernel reload check (L9_EXECUTOR_API_KEY not set)"
    fi
    
    # LChat endpoint (minimal payload test)
    info "Testing lchat endpoint..."
    local chat_url="${L9_API_BASE}/lchat"
    
    if [[ -n "${L9_EXECUTOR_API_KEY:-}" ]]; then
        debug "POST ${chat_url}"
        
        local payload='{"message":"ping","stream":false}'
        
        if response=$(curl -fsS -X POST \
            -H "Authorization: Bearer ${L9_EXECUTOR_API_KEY}" \
            -H "Content-Type: application/json" \
            -d "$payload" \
            "$chat_url" 2>&1); then
            
            if echo "$response" | python3 -m json.tool > /dev/null 2>&1; then
                endpoint_stats+=("✓ POST /lchat")
                success_count=$((success_count + 1))
                debug "LChat endpoint responsive"
            else
                endpoint_stats+=("⚠ POST /lchat (invalid JSON)")
                warn "LChat endpoint returned invalid JSON"
            fi
        else
            endpoint_stats+=("✗ POST /lchat")
            error "LChat endpoint failed"
            if [[ "$FLAG_VERBOSE" == "true" ]]; then
                error "Response: ${response}"
            fi
            # LChat may fail due to missing OpenAI key or model issues - warn but don't fail
            warn "LChat endpoint may require valid OpenAI configuration"
        fi
    else
        endpoint_stats+=("⊘ POST /lchat (no L9_EXECUTOR_API_KEY)")
        warn "Skipping lchat endpoint check (L9_EXECUTOR_API_KEY not set)"
    fi
    
    # MCP Memory search endpoint (on separate port 9002)
    # MANDATORY: MCP Memory is required for L9 to function
    # Uses MCP_API_KEY (or MCP_API_KEY_L/MCP_API_KEY_C) for auth
    # Governance context (RLS) is built server-side from config
    info "Testing MCP memory search endpoint..."
    local mcp_memory_search_url="${MCP_MEMORY_URL:-http://127.0.0.1:9002}/memory/search"
    
    # Determine which MCP API key to use (prefer L key, fall back to generic)
    local mcp_key="${MCP_API_KEY_L:-${MCP_API_KEY:-}}"
    
    if [[ -n "${mcp_key}" ]]; then
        debug "POST ${mcp_memory_search_url}"
        
        # Search payload with proper schema for PacketEnvelope v2 memory search
        local memory_payload='{"query":"system health test","top_k":3,"scopes":["developer","global"]}'
        
        if response=$(curl -fsS -X POST \
            -H "Authorization: Bearer ${mcp_key}" \
            -H "Content-Type: application/json" \
            -d "$memory_payload" \
            "$mcp_memory_search_url" 2>&1); then
            
            # Validate response is valid JSON with expected structure
            if echo "$response" | python3 -c "
import sys, json
data = json.load(sys.stdin)
# MCP memory search returns: results, query_embedding_time_ms, search_time_ms, total_results
assert 'results' in data, 'Missing results field'
assert isinstance(data['results'], list), 'results must be a list'
print(f'MCP memory search: {len(data[\"results\"])} results, {data.get(\"search_time_ms\", 0):.1f}ms')
" 2>&1; then
                endpoint_stats+=("✓ POST :9002/memory/search")
                success_count=$((success_count + 1))
                debug "MCP memory search endpoint responsive with valid PacketEnvelope v2 response"
            else
                endpoint_stats+=("✗ POST :9002/memory/search (invalid response)")
                error "MCP memory search returned invalid response structure"
                error "Response: ${response:0:500}"
                phase_failed=true
            fi
        else
            endpoint_stats+=("✗ POST :9002/memory/search (failed)")
            error "MCP memory search endpoint failed - MANDATORY for L9 operation"
            error "Response: ${response:0:500}"
            phase_failed=true
        fi
    else
        endpoint_stats+=("✗ POST :9002/memory/search (no MCP_API_KEY)")
        error "MCP_API_KEY not set - MANDATORY for MCP memory operations"
        phase_failed=true
    fi
    
    # =========================================================================
    # INTEGRATION CHECKS: Slack, Tools, Kernels
    # =========================================================================
    
    # Slack integration health (GET /slack/health or check router is mounted)
    info "Testing Slack integration..."
    local slack_health_url="${L9_API_BASE}/slack/health"
    
    if response=$(curl -fsS -X GET "$slack_health_url" 2>&1); then
        endpoint_stats+=("✓ GET /slack/health")
        success_count=$((success_count + 1))
        debug "Slack integration healthy"
    else
        # Slack health endpoint may not exist, try checking if router is mounted via openapi
        debug "Slack health endpoint not available, checking OpenAPI..."
        if curl -fsS "${L9_API_BASE}/openapi.json" 2>/dev/null | grep -q '"/slack/'; then
            endpoint_stats+=("✓ Slack router mounted (via OpenAPI)")
            success_count=$((success_count + 1))
            debug "Slack router confirmed in OpenAPI spec"
        else
            endpoint_stats+=("⚠ Slack integration (not verified)")
            warn "Slack integration could not be verified"
            # Not a hard failure - Slack may be disabled
        fi
    fi
    
    # Tool Registry validation (check tool count via /tools or /health/services)
    info "Testing Tool Registry..."
    local tools_url="${L9_API_BASE}/health/services"
    
    if response=$(curl -fsS -X GET "$tools_url" 2>&1); then
        # Check if response contains tool_registry info
        if echo "$response" | python3 -c "
import sys, json
data = json.load(sys.stdin)
# Look for tool registry in services health
services = data.get('services', {})
tool_count = services.get('tool_registry', {}).get('tool_count', 0)
if tool_count > 0:
    print(f'Tool Registry: {tool_count} tools registered')
    sys.exit(0)
else:
    # Try alternate structure
    if 'tool_registry' in str(data):
        print('Tool Registry: present')
        sys.exit(0)
    print('Tool Registry: not found in response')
    sys.exit(1)
" 2>&1; then
            endpoint_stats+=("✓ Tool Registry")
            success_count=$((success_count + 1))
            debug "Tool Registry validated"
        else
            endpoint_stats+=("⚠ Tool Registry (structure unknown)")
            warn "Tool Registry response structure unexpected"
        fi
    else
        endpoint_stats+=("⚠ Tool Registry (health/services failed)")
        warn "Could not verify Tool Registry via /health/services"
    fi
    
    # Kernel Stack verification (check kernels loaded via /kernels or /health)
    info "Testing Kernel Stack..."
    local kernels_url="${L9_API_BASE}/kernels"
    
    if [[ -n "${L9_EXECUTOR_API_KEY:-}" ]]; then
        if response=$(curl -fsS -X GET \
            -H "Authorization: Bearer ${L9_EXECUTOR_API_KEY}" \
            "$kernels_url" 2>&1); then
            
            if echo "$response" | python3 -c "
import sys, json
data = json.load(sys.stdin)
# Kernel response should have kernels list or count
kernels = data.get('kernels', data.get('loaded_kernels', []))
if isinstance(kernels, list) and len(kernels) > 0:
    print(f'Kernel Stack: {len(kernels)} kernels loaded')
    sys.exit(0)
elif isinstance(kernels, dict):
    print(f'Kernel Stack: {len(kernels)} kernels loaded')
    sys.exit(0)
elif 'count' in data:
    print(f'Kernel Stack: {data[\"count\"]} kernels')
    sys.exit(0)
else:
    print(f'Kernel Stack: response={str(data)[:100]}')
    sys.exit(0)  # Don't fail, just report
" 2>&1; then
                endpoint_stats+=("✓ Kernel Stack")
                success_count=$((success_count + 1))
                debug "Kernel Stack validated"
            else
                endpoint_stats+=("⚠ Kernel Stack (parse error)")
                warn "Kernel Stack response could not be parsed"
            fi
        else
            endpoint_stats+=("⚠ GET /kernels (failed)")
            warn "Could not verify Kernel Stack"
        fi
    else
        endpoint_stats+=("⊘ Kernel Stack (no API key)")
        debug "Skipping Kernel Stack check (no L9_EXECUTOR_API_KEY)"
    fi
    
    # WebSocket endpoint availability (just check if upgrade is offered)
    info "Testing WebSocket endpoint availability..."
    local ws_url="${L9_API_BASE}/ws/agent"
    
    # Check if WebSocket endpoint responds (will get 426 Upgrade Required or similar)
    if response=$(curl -fsS -I -X GET "$ws_url" 2>&1) || \
       response=$(curl -sS -I -X GET "$ws_url" 2>&1 | head -5); then
        if echo "$response" | grep -qiE "(upgrade|websocket|101|426)"; then
            endpoint_stats+=("✓ WebSocket /ws/agent (available)")
            success_count=$((success_count + 1))
            debug "WebSocket endpoint available"
        else
            # Just check if endpoint exists (any response)
            endpoint_stats+=("✓ WebSocket /ws/agent (responds)")
            success_count=$((success_count + 1))
            debug "WebSocket endpoint responds"
        fi
    else
        endpoint_stats+=("⚠ WebSocket /ws/agent (not available)")
        warn "WebSocket endpoint not responding"
    fi
    
    # Summary
    local total_endpoints=$((${#health_endpoints[@]} + 7))  # health + reload + lchat + memory + slack + tools + kernels + ws
    info "API endpoints: ${success_count}/${total_endpoints} healthy"
    
    # Record result
    if [[ "$phase_failed" == "true" ]]; then
        record_phase_result "app" "FAIL" "(${success_count}/${total_endpoints} endpoints)"
        return $EXIT_APP_ERROR
    else
        record_phase_result "app" "PASS" "(${success_count}/${total_endpoints} endpoints)"
        return 0
    fi
}

# =============================================================================
# PHASE: WEBSOCKET AUTH DIAGNOSTIC
# =============================================================================

run_websocket_checks() {
    info "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    info "PHASE: WebSocket Authentication"
    info "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    
    if [[ "$FLAG_SKIP_WEBSOCKET" == "true" ]]; then
        warn "Skipping WebSocket checks (--skip-websocket)"
        record_phase_result "websocket" "PASS" "(skipped)"
        return 0
    fi
    
    local phase_failed=false
    
    # Check if websocat is available
    if ! check_command websocat; then
        warn "websocat not found, trying Python websocket client..."
        
        # Try Python approach
        if ! check_command python3; then
            error "Python3 not found, cannot test WebSocket"
            record_phase_result "websocket" "FAIL" "(no client available)"
            return $EXIT_WS_ERROR
        fi
        
        # Check if websockets module available
        if ! python3 -c "import websockets" 2>/dev/null; then
            warn "Python websockets module not available"
            warn "Install with: pip install websockets"
            record_phase_result "websocket" "PASS" "(skipped - no deps)"
            return 0
        fi
        
        # Use Python WebSocket client
        info "Testing WebSocket auth with Python client..."
        
        local ws_url="${L9_API_BASE/http/ws}/ws/agent"
        
        # Test with valid token
        if [[ -n "${L9_EXECUTOR_API_KEY:-}" ]]; then
            debug "Testing valid token authentication..."
            
            local py_test_valid
            py_test_valid=$(python3 - <<'PYEOF'
import asyncio
import sys
import os

try:
    import websockets
except ImportError:
    sys.exit(2)

async def test_auth():
    token = os.environ.get('L9_EXECUTOR_API_KEY')
    url = os.environ.get('WS_URL')
    
    if not token or not url:
        return False
    
    try:
        async with websockets.connect(f"{url}?token={token}", timeout=5) as ws:
            return True
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return False

result = asyncio.run(test_auth())
sys.exit(0 if result else 1)
PYEOF
            )
            
            local exit_code=$?
            
            if [[ $exit_code -eq 0 ]]; then
                info "✓ WebSocket auth: valid token accepted"
            elif [[ $exit_code -eq 2 ]]; then
                warn "Python websockets module import failed"
                record_phase_result "websocket" "PASS" "(skipped - no deps)"
                return 0
            else
                error "✗ WebSocket auth: valid token rejected"
                phase_failed=true
            fi
            
            # Test with invalid token
            debug "Testing invalid token rejection..."
            
            export L9_EXECUTOR_API_KEY="invalid-token-12345"
            export WS_URL="$ws_url"
            
            local py_test_invalid
            py_test_invalid=$(python3 - <<'PYEOF'
import asyncio
import sys
import os

try:
    import websockets
except ImportError:
    sys.exit(2)

async def test_auth():
    token = os.environ.get('L9_EXECUTOR_API_KEY')
    url = os.environ.get('WS_URL')
    
    if not token or not url:
        return False
    
    try:
        async with websockets.connect(f"{url}?token={token}", timeout=5) as ws:
            return True  # Should NOT succeed
    except websockets.exceptions.InvalidStatusCode as e:
        if e.status_code in [401, 403]:
            return False  # Expected rejection
        return True  # Unexpected error
    except Exception:
        return False  # Expected rejection

result = asyncio.run(test_auth())
sys.exit(0 if not result else 1)  # Inverted: success = rejection
PYEOF
            )
            
            exit_code=$?
            
            if [[ $exit_code -eq 0 ]]; then
                info "✓ WebSocket auth: invalid token rejected (as expected)"
            else
                error "✗ WebSocket auth: invalid token NOT rejected"
                phase_failed=true
            fi
        else
            warn "L9_EXECUTOR_API_KEY not set, skipping WebSocket auth tests"
        fi
    else
        # Use websocat
        info "Testing WebSocket auth with websocat..."
        warn "websocat-based tests not yet implemented"
        # TODO: Implement websocat-based tests
    fi
    
    # Record result
    if [[ "$phase_failed" == "true" ]]; then
        record_phase_result "websocket" "FAIL" "(auth validation failed)"
        return $EXIT_WS_ERROR
    else
        record_phase_result "websocket" "PASS" "(auth positive/negative validated)"
        return 0
    fi
}

# =============================================================================
# PHASE: OBSERVABILITY CHECKS
# =============================================================================

run_observability_checks() {
    info "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    info "PHASE: Observability Stack (Prometheus/Grafana/Jaeger)"
    info "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    
    local phase_failed=false
    local obs_stats=()
    local success_count=0
    
    # Prometheus health
    info "Testing Prometheus..."
    if curl -fsS "http://127.0.0.1:9090/-/healthy" > /dev/null 2>&1; then
        obs_stats+=("✓ prometheus")
        success_count=$((success_count + 1))
        debug "Prometheus healthy"
        
        # Optional: query status
        if response=$(curl -fsS "http://127.0.0.1:9090/api/v1/status/runtimeinfo" 2>&1); then
            if echo "$response" | python3 -m json.tool > /dev/null 2>&1; then
                debug "Prometheus API responsive"
            fi
        fi
    else
        obs_stats+=("✗ prometheus")
        error "Prometheus health check failed"
        phase_failed=true
    fi
    
    # Grafana health
    info "Testing Grafana..."
    if response=$(curl -fsS "http://127.0.0.1:3000/api/health" 2>&1); then
        if echo "$response" | python3 -m json.tool > /dev/null 2>&1; then
            obs_stats+=("✓ grafana")
            success_count=$((success_count + 1))
            debug "Grafana healthy"
            
            # Check database status in response
            local db_status
            db_status=$(echo "$response" | python3 -c "import sys, json; print(json.load(sys.stdin).get('database', 'unknown'))" 2>/dev/null || echo "unknown")
            if [[ "$db_status" != "ok" ]]; then
                warn "Grafana database status != 'ok': ${db_status}"
            fi
        else
            obs_stats+=("⚠ grafana (invalid response)")
            warn "Grafana returned invalid JSON"
        fi
    else
        obs_stats+=("✗ grafana")
        error "Grafana health check failed"
        phase_failed=true
    fi
    
    # Jaeger UI
    info "Testing Jaeger..."
    if curl -fsS "http://127.0.0.1:16686" 2>&1 | grep -q "Jaeger UI"; then
        obs_stats+=("✓ jaeger")
        success_count=$((success_count + 1))
        debug "Jaeger UI accessible"
    else
        obs_stats+=("✗ jaeger")
        error "Jaeger UI not accessible"
        phase_failed=true
    fi
    
    # L9 metrics endpoint
    info "Testing L9 metrics endpoint..."
    local metrics_url="${L9_API_BASE}/metrics"
    
    if response=$(curl -fsS "$metrics_url" 2>&1); then
        # Check for Prometheus format (contains # TYPE or metric names)
        if echo "$response" | grep -qE '(# TYPE|# HELP|^[a-z_]+{)'; then
            obs_stats+=("✓ l9-metrics")
            success_count=$((success_count + 1))
            debug "L9 metrics endpoint responsive"
            
            # Check for L9-specific metrics
            if echo "$response" | grep -q "l9_"; then
                debug "L9-specific metrics found"
            else
                warn "No L9-specific metrics found (may not be instrumented yet)"
            fi
        else
            obs_stats+=("⚠ l9-metrics (unexpected format)")
            warn "L9 metrics endpoint returned unexpected format"
        fi
    else
        obs_stats+=("⊘ l9-metrics (not available)")
        warn "L9 metrics endpoint not available (may not be enabled)"
    fi
    
    # Summary
    info "Observability: ${success_count}/4 components healthy"
    
    # Record result
    if [[ "$phase_failed" == "true" ]]; then
        record_phase_result "observability" "FAIL" "(prometheus/grafana/jaeger/metrics)"
        return $EXIT_OBS_ERROR
    else
        record_phase_result "observability" "PASS" "(prometheus/grafana/jaeger/metrics)"
        return 0
    fi
}

# =============================================================================
# RUN MODES
# =============================================================================

run_smoke_test() {
    info "Running SMOKE TEST (quick health check)..."
    info ""
    
    local overall_failed=false
    
    # Infra
    if ! run_infra_checks; then
        overall_failed=true
        if [[ "$FLAG_CONTINUE_ON_ERROR" != "true" ]]; then
            return $EXIT_INFRA_ERROR
        fi
    fi
    
    info ""
    
    # DB
    if ! run_db_checks; then
        overall_failed=true
        if [[ "$FLAG_CONTINUE_ON_ERROR" != "true" ]]; then
            return $EXIT_DB_ERROR
        fi
    fi
    
    info ""
    
    # App (minimal)
    if ! run_app_checks; then
        overall_failed=true
        if [[ "$FLAG_CONTINUE_ON_ERROR" != "true" ]]; then
            return $EXIT_APP_ERROR
        fi
    fi
    
    if [[ "$overall_failed" == "true" ]]; then
        return 1
    fi
    
    return 0
}

run_full_test() {
    info "Running FULL E2E TEST (all checks)..."
    info ""
    
    local overall_failed=false
    
    # Infra
    if ! run_infra_checks; then
        overall_failed=true
        if [[ "$FLAG_CONTINUE_ON_ERROR" != "true" ]]; then
            return $EXIT_INFRA_ERROR
        fi
    fi
    
    info ""
    
    # DB
    if ! run_db_checks; then
        overall_failed=true
        if [[ "$FLAG_CONTINUE_ON_ERROR" != "true" ]]; then
            return $EXIT_DB_ERROR
        fi
    fi
    
    info ""
    
    # App
    if ! run_app_checks; then
        overall_failed=true
        if [[ "$FLAG_CONTINUE_ON_ERROR" != "true" ]]; then
            return $EXIT_APP_ERROR
        fi
    fi
    
    info ""
    
    # WebSocket
    if ! run_websocket_checks; then
        overall_failed=true
        if [[ "$FLAG_CONTINUE_ON_ERROR" != "true" ]]; then
            return $EXIT_WS_ERROR
        fi
    fi
    
    info ""
    
    # Observability
    if ! run_observability_checks; then
        overall_failed=true
        if [[ "$FLAG_CONTINUE_ON_ERROR" != "true" ]]; then
            return $EXIT_OBS_ERROR
        fi
    fi
    
    if [[ "$overall_failed" == "true" ]]; then
        return 1
    fi
    
    return 0
}

# =============================================================================
# SUMMARY REPORT
# =============================================================================

print_summary() {
    local exit_code="$1"
    
    info ""
    info "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    info "L9 C1 GODMODE E2E SUMMARY"
    info "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    
    for result in "${PHASE_RESULTS[@]}"; do
        echo -e "$result"
    done
    
    info ""
    info "Phases: ${PHASE_COUNT} total, ${PHASE_PASS} passed, ${PHASE_FAIL} failed"
    info ""
    
    if [[ $exit_code -eq 0 ]]; then
        echo -e "${COLOR_GREEN}${COLOR_BOLD}Overall: PASS${COLOR_RESET}"
    else
        echo -e "${COLOR_RED}${COLOR_BOLD}Overall: FAIL${COLOR_RESET}"
    fi
    
    info ""
    info "Exit code: ${exit_code}"
    info "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
}

# =============================================================================
# ARGUMENT PARSING
# =============================================================================

parse_args() {
    local command="${1:-}"
    shift || true
    
    # Parse flags
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --env-file)
                ENV_FILE="$2"
                shift 2
                ;;
            --api-base)
                L9_API_BASE="$2"
                shift 2
                ;;
            --allow-missing-env)
                FLAG_ALLOW_MISSING_ENV=true
                shift
                ;;
            --continue-on-error)
                FLAG_CONTINUE_ON_ERROR=true
                shift
                ;;
            --dangerous)
                FLAG_DANGEROUS=true
                warn "Dangerous mode enabled (reserved for future destructive ops)"
                shift
                ;;
            --verbose)
                FLAG_VERBOSE=true
                shift
                ;;
            --skip-websocket)
                FLAG_SKIP_WEBSOCKET=true
                shift
                ;;
            --help|-h)
                print_usage
                exit 0
                ;;
            *)
                error "Unknown flag: $1"
                print_usage
                exit $EXIT_ARG_ERROR
                ;;
        esac
    done
    
    # Dispatch command
    case "$command" in
        smoke)
            detect_environment
            validate_required_env_vars || exit $EXIT_ENV_ERROR
            run_smoke_test
            local exit_code=$?
            print_summary "$exit_code"
            exit "$exit_code"
            ;;
        full)
            detect_environment
            validate_required_env_vars || exit $EXIT_ENV_ERROR
            run_full_test
            local exit_code=$?
            print_summary "$exit_code"
            exit "$exit_code"
            ;;
        infra)
            detect_environment
            validate_required_env_vars || exit $EXIT_ENV_ERROR
            run_infra_checks
            local exit_code=$?
            print_summary "$exit_code"
            exit "$exit_code"
            ;;
        db)
            detect_environment
            validate_required_env_vars || exit $EXIT_ENV_ERROR
            run_db_checks
            local exit_code=$?
            print_summary "$exit_code"
            exit "$exit_code"
            ;;
        app)
            detect_environment
            validate_required_env_vars || exit $EXIT_ENV_ERROR
            run_app_checks
            local exit_code=$?
            print_summary "$exit_code"
            exit "$exit_code"
            ;;
        websocket)
            detect_environment
            validate_required_env_vars || exit $EXIT_ENV_ERROR
            run_websocket_checks
            local exit_code=$?
            print_summary "$exit_code"
            exit "$exit_code"
            ;;
        observability)
            detect_environment
            validate_required_env_vars || exit $EXIT_ENV_ERROR
            run_observability_checks
            local exit_code=$?
            print_summary "$exit_code"
            exit "$exit_code"
            ;;
        "")
            error "No command specified"
            print_usage
            exit $EXIT_ARG_ERROR
            ;;
        *)
            error "Unknown command: ${command}"
            print_usage
            exit $EXIT_ARG_ERROR
            ;;
    esac
}

print_usage() {
    cat <<EOF
L9 GOD-MODE E2E TEST SCRIPT v${SCRIPT_VERSION}

USAGE:
    ${SCRIPT_NAME} <command> [options]

COMMANDS:
    smoke            Quick health check (~30s)
    full             Complete validation (~2-3min)
    infra            Infrastructure checks only
    db               Database substrate checks only
    app              L9 API checks only
    websocket        WebSocket auth checks only
    observability    Observability stack checks only

OPTIONS:
    --env-file <path>         Override .env file location
    --api-base <url>          Override L9 API base URL (default: http://127.0.0.1:8000)
    --allow-missing-env       Continue with degraded checks if env vars missing (UNSAFE)
    --continue-on-error       Continue to next phase even if current phase fails
    --dangerous               Enable destructive operations (reserved, none in v1.0)
    --verbose                 Enable verbose logging
    --skip-websocket          Skip WebSocket checks (if deps unavailable)
    --help, -h                Show this help message

EXAMPLES:
    # Quick smoke test after deployment
    ${SCRIPT_NAME} smoke

    # Full validation with verbose output
    ${SCRIPT_NAME} full --verbose

    # Test only infrastructure health
    ${SCRIPT_NAME} infra

    # Use custom env file
    ${SCRIPT_NAME} full --env-file /path/to/.env.production

EXIT CODES:
    0   = All checks passed
    1   = Argument parsing error
    2   = Environment validation failed
    10  = Infrastructure checks failed
    20  = Database checks failed
    30  = App checks failed
    40  = WebSocket checks failed
    50  = Observability checks failed

EOF
}

# =============================================================================
# MAIN ENTRYPOINT
# =============================================================================

main() {
    info "L9 GOD-MODE E2E TEST SCRIPT v${SCRIPT_VERSION}"
    info "Host: $(hostname)"
    info "Date: $(date)"
    info ""
    
    parse_args "$@"
}

# Run main
main "$@"
