#!/usr/bin/env bash
# =============================================================================
# L9 Docker Pre-Commit Smoke Test
# Version: 1.0.0
#
# Validates Docker compose, builds images, boots stack, runs smoke tests,
# and tears down cleanly. Designed for pre-commit hooks and CI/CD.
#
# Usage:
#   ./scripts/precommit_docker_smoke.sh
#
# Exit codes:
#   0 - All tests passed
#   1 - Compose validation failed
#   2 - Build failed
#   3 - Boot/health check failed
#   4 - Smoke tests failed
#   5 - Teardown failed
# =============================================================================

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
PROJECT_NAME="l9_precommit_$(date +%s)"
COMPOSE_FILE="$PROJECT_ROOT/docker-compose.yml"
HEALTH_TIMEOUT=120  # seconds
HEALTH_INTERVAL=2   # seconds

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() { echo -e "${BLUE}[INFO]${NC} $*"; }
log_success() { echo -e "${GREEN}[✓]${NC} $*"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $*"; }
log_error() { echo -e "${RED}[✗]${NC} $*"; }

# Cleanup function - always runs on exit
cleanup() {
    local exit_code=$?
    log_info "Cleaning up Docker resources..."
    
    # Capture logs on failure before teardown
    if [ $exit_code -ne 0 ]; then
        log_warn "Capturing service logs before teardown..."
        docker compose -p "$PROJECT_NAME" -f "$COMPOSE_FILE" logs --tail=50 2>/dev/null || true
    fi
    
    # Tear down with no residue
    docker compose -p "$PROJECT_NAME" -f "$COMPOSE_FILE" down -v --remove-orphans 2>/dev/null || true
    
    # Remove any dangling resources from this project
    docker network rm "${PROJECT_NAME}_l9-network" 2>/dev/null || true
    
    if [ $exit_code -eq 0 ]; then
        log_success "Cleanup complete - no residue"
    else
        log_warn "Cleanup complete (test failed with exit code $exit_code)"
    fi
}

# Register cleanup trap
trap cleanup EXIT INT TERM

# Wait for a container to be healthy
wait_for_healthy() {
    local service=$1
    local timeout=${2:-$HEALTH_TIMEOUT}
    local elapsed=0
    
    log_info "Waiting for $service to be healthy (timeout: ${timeout}s)..."
    
    while [ $elapsed -lt $timeout ]; do
        local health
        health=$(docker compose -p "$PROJECT_NAME" -f "$COMPOSE_FILE" ps --format json "$service" 2>/dev/null | \
            python3 -c "import sys, json; data=json.load(sys.stdin) if sys.stdin.read(1) else {}; print(data.get('Health', 'unknown'))" 2>/dev/null || echo "unknown")
        
        if [ "$health" = "healthy" ]; then
            log_success "$service is healthy"
            return 0
        fi
        
        sleep $HEALTH_INTERVAL
        elapsed=$((elapsed + HEALTH_INTERVAL))
        
        # Check if container is running at all
        local state
        state=$(docker compose -p "$PROJECT_NAME" -f "$COMPOSE_FILE" ps --format json "$service" 2>/dev/null | \
            python3 -c "import sys, json; data=json.load(sys.stdin) if sys.stdin.read(1) else {}; print(data.get('State', 'unknown'))" 2>/dev/null || echo "unknown")
        
        if [ "$state" = "exited" ]; then
            log_error "$service exited unexpectedly"
            docker compose -p "$PROJECT_NAME" -f "$COMPOSE_FILE" logs "$service" --tail=30
            return 1
        fi
    done
    
    log_error "$service failed to become healthy within ${timeout}s"
    docker compose -p "$PROJECT_NAME" -f "$COMPOSE_FILE" logs "$service" --tail=50
    return 1
}

# Run HTTP health check from inside the network
run_container_healthcheck() {
    local url=$1
    local expected_status=${2:-200}
    
    docker run --rm --network="${PROJECT_NAME}_l9-network" \
        curlimages/curl:latest \
        -sf -o /dev/null -w "%{http_code}" "$url" 2>/dev/null || echo "000"
}

# Main execution
main() {
    log_info "=== L9 Docker Pre-Commit Smoke Test ==="
    log_info "Project: $PROJECT_NAME"
    log_info "Compose: $COMPOSE_FILE"
    
    cd "$PROJECT_ROOT"
    
    # ==========================================================================
    # Gate 1: Compose Validation
    # ==========================================================================
    log_info "Gate 1: Validating docker-compose.yml..."
    
    if ! docker compose -f "$COMPOSE_FILE" config -q; then
        log_error "docker-compose.yml validation failed"
        exit 1
    fi
    log_success "Compose file is valid"
    
    # ==========================================================================
    # Gate 2: Build Images
    # ==========================================================================
    log_info "Gate 2: Building Docker images..."
    
    if ! docker compose -p "$PROJECT_NAME" -f "$COMPOSE_FILE" build --quiet; then
        log_error "Docker build failed"
        exit 2
    fi
    log_success "All images built successfully"
    
    # ==========================================================================
    # Gate 3: Boot Stack
    # ==========================================================================
    log_info "Gate 3: Starting stack..."
    
    if ! docker compose -p "$PROJECT_NAME" -f "$COMPOSE_FILE" up -d; then
        log_error "Failed to start stack"
        exit 3
    fi
    
    # Wait for services to be healthy
    log_info "Waiting for services to become healthy..."
    
    # Postgres first (other services depend on it)
    if ! wait_for_healthy "postgres" 60; then
        log_error "Postgres failed to start"
        exit 3
    fi
    
    # Memory API (depends on postgres)
    if ! wait_for_healthy "l9-memory-api" 90; then
        log_error "Memory API failed to start"
        exit 3
    fi
    
    # Main API (depends on postgres and memory-api)
    if ! wait_for_healthy "l9-api" 90; then
        log_error "Main API failed to start"
        exit 3
    fi
    
    log_success "All services are healthy"
    
    # ==========================================================================
    # Gate 4: Run Smoke Tests
    # ==========================================================================
    log_info "Gate 4: Running smoke tests..."
    
    # Run Python smoke tests inside the API container (has network access)
    # First, check if test file exists
    if [ -f "$PROJECT_ROOT/tests/docker/test_stack_smoke.py" ]; then
        # Run tests using pytest in the l9-api container
        if ! docker compose -p "$PROJECT_NAME" -f "$COMPOSE_FILE" exec -T l9-api \
            python -m pytest /app/tests/docker/test_stack_smoke.py -v --tb=short; then
            log_error "Smoke tests failed"
            exit 4
        fi
    else
        # Fallback: Run basic HTTP checks using curl container
        log_warn "Python smoke tests not found, running basic HTTP checks..."
        
        # Check main API /health
        local api_status
        api_status=$(run_container_healthcheck "http://l9-api:8000/health")
        if [ "$api_status" != "200" ]; then
            log_error "Main API /health returned $api_status (expected 200)"
            exit 4
        fi
        log_success "Main API /health: OK"
        
        # Check main API /docs
        api_status=$(run_container_healthcheck "http://l9-api:8000/docs")
        if [ "$api_status" != "200" ]; then
            log_error "Main API /docs returned $api_status (expected 200)"
            exit 4
        fi
        log_success "Main API /docs: OK"
        
        # Check OS health
        api_status=$(run_container_healthcheck "http://l9-api:8000/os/health")
        if [ "$api_status" != "200" ]; then
            log_error "OS /health returned $api_status (expected 200)"
            exit 4
        fi
        log_success "OS /health: OK"
        
        # Check Memory API /health
        api_status=$(run_container_healthcheck "http://l9-memory-api:8080/health")
        if [ "$api_status" != "200" ]; then
            log_error "Memory API /health returned $api_status (expected 200)"
            exit 4
        fi
        log_success "Memory API /health: OK"
    fi
    
    log_success "All smoke tests passed"
    
    # ==========================================================================
    # Gate 5: Validate DB Connectivity (prevent 127.0.0.1 bug)
    # ==========================================================================
    log_info "Gate 5: Validating DB connectivity..."
    
    # Check that API can reach postgres via service DNS
    if ! docker compose -p "$PROJECT_NAME" -f "$COMPOSE_FILE" exec -T l9-api \
        python -c "
import os
import asyncio
import asyncpg

async def check_db():
    url = os.environ.get('DATABASE_URL')
    if not url:
        print('ERROR: DATABASE_URL not set')
        return False
    
    # Verify it's using service DNS, not localhost
    if '127.0.0.1' in url or 'localhost' in url:
        print(f'ERROR: DATABASE_URL contains localhost: {url}')
        print('Fix: Use service DNS (e.g., postgres:5432) instead of localhost')
        return False
    
    try:
        conn = await asyncpg.connect(url)
        result = await conn.fetchval('SELECT 1')
        await conn.close()
        print(f'DB connectivity OK (SELECT 1 = {result})')
        return True
    except Exception as e:
        print(f'ERROR: DB connection failed: {e}')
        return False

exit(0 if asyncio.run(check_db()) else 1)
"; then
        log_error "DB connectivity validation failed"
        exit 4
    fi
    log_success "DB connectivity validated (no localhost DSN)"
    
    # ==========================================================================
    # Success
    # ==========================================================================
    log_success "=== All smoke tests passed ==="
    exit 0
}

# Run main
main "$@"

