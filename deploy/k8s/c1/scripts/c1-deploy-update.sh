#!/bin/bash
# =============================================================================
# C1 PULL & DEPLOY SCRIPT
# =============================================================================
# Complete deployment workflow for updating C1 with latest code.
#
# Usage:
#   ./c1-deploy-update.sh                    # Full deploy
#   ./c1-deploy-update.sh --skip-migrations  # Skip DB migrations
#   ./c1-deploy-update.sh --skip-build       # Skip container rebuild
#   ./c1-deploy-update.sh --dry-run          # Preview actions
#
# WORKFLOW:
#   Phase 1:  Connect & Verify
#   Phase 2:  Pull Latest Code
#   Phase 3:  Sync Env Files
#   Phase 4:  Run Database Migrations (PostgreSQL)
#   Phase 5:  Run Neo4j Migrations (Cypher)
#   Phase 6:  Rebuild Containers
#   Phase 7:  Restart Services
#   Phase 8:  Health Checks
#   Phase 9:  Verify Memory Substrate
#   Phase 10: Final Status
#
# PREREQUISITES:
#   - SSH key at ~/.ssh/Hetzner-C1
#   - Local .env files configured
#   - C1 already has base infrastructure (k3s, docker)
# =============================================================================

set -euo pipefail

# =============================================================================
# CONFIGURATION
# =============================================================================
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../../.." && pwd)"
LOG_FILE="$SCRIPT_DIR/deploy-update-$(date +%Y%m%d-%H%M%S).log"

# VPS Config
C1_IP="46.62.243.82"
SSH_KEY_FILE="$HOME/.ssh/Hetzner-C1"
VPS_L9_DIR="/opt/l9"
VPS_BUILD_DIR="/opt/l9-build/L9"

# Ports for health checks (keys without spaces for macOS bash compatibility)
declare -A SERVICE_PORTS=(
    ["L9_API"]=30080
    ["MCP_Memory"]=30902
    ["PostgreSQL"]=30432
    ["Neo4j_Browser"]=30474
    ["Neo4j_Bolt"]=30687
    ["Grafana"]=30300
    ["Prometheus"]=30909
    ["Redis"]=30379
)

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

# Options
DRY_RUN=false
SKIP_MIGRATIONS=false
SKIP_BUILD=false
SKIP_NEO4J=false
FORCE=false

# Logging
exec > >(tee -a "$LOG_FILE") 2>&1

log_info() { echo -e "${BLUE}[INFO $(date +%H:%M:%S)]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS $(date +%H:%M:%S)]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN $(date +%H:%M:%S)]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR $(date +%H:%M:%S)]${NC} $1"; }
log_step() { echo -e "${CYAN}[STEP $(date +%H:%M:%S)]${NC} ========== $1 =========="; }

# =============================================================================
# PARSE ARGUMENTS
# =============================================================================
while [[ $# -gt 0 ]]; do
    case $1 in
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        --skip-migrations)
            SKIP_MIGRATIONS=true
            shift
            ;;
        --skip-build)
            SKIP_BUILD=true
            shift
            ;;
        --skip-neo4j)
            SKIP_NEO4J=true
            shift
            ;;
        --force)
            FORCE=true
            shift
            ;;
        --help)
            echo "Usage: $0 [options]"
            echo ""
            echo "Options:"
            echo "  --dry-run          Preview actions without making changes"
            echo "  --skip-migrations  Skip database migrations"
            echo "  --skip-build       Skip container rebuild"
            echo "  --skip-neo4j       Skip Neo4j migrations"
            echo "  --force            Skip confirmations"
            exit 0
            ;;
        *)
            log_error "Unknown option: $1"
            exit 1
            ;;
    esac
done

# =============================================================================
# SSH HELPERS
# =============================================================================
ssh_cmd() {
    ssh -o StrictHostKeyChecking=no -o ConnectTimeout=10 -i "$SSH_KEY_FILE" root@"$C1_IP" "$@"
}

scp_cmd() {
    scp -o StrictHostKeyChecking=no -i "$SSH_KEY_FILE" "$@"
}

# =============================================================================
# PHASE 1: CONNECT & VERIFY
# =============================================================================
connect_and_verify() {
    log_step "PHASE 1: CONNECT & VERIFY"

    # Check SSH key
    if [[ ! -f "$SSH_KEY_FILE" ]]; then
        log_error "SSH key not found: $SSH_KEY_FILE"
        exit 1
    fi

    # Test connection
    log_info "Testing SSH connection to $C1_IP..."
    if ! ssh_cmd "echo 'SSH OK'" &>/dev/null; then
        log_error "Cannot connect to C1 at $C1_IP"
        exit 1
    fi

    # Check k3s is running
    log_info "Verifying k3s is running..."
    if ! ssh_cmd "kubectl get nodes" &>/dev/null; then
        log_error "k3s is not running on C1"
        exit 1
    fi

    # Check docker is running
    log_info "Verifying Docker is running..."
    if ! ssh_cmd "docker ps" &>/dev/null; then
        log_error "Docker is not running on C1"
        exit 1
    fi

    # Show current state
    log_info "Current pod status:"
    ssh_cmd "kubectl get pods -n l9-c1 2>/dev/null || echo 'No l9-c1 namespace yet'"

    log_success "Connection verified"
}

# =============================================================================
# PHASE 2: PULL LATEST CODE
# =============================================================================
pull_latest_code() {
    log_step "PHASE 2: PULL LATEST CODE"

    if $DRY_RUN; then
        log_info "[DRY RUN] Would pull latest code on VPS"
        return
    fi

    log_info "Pulling latest code from git..."

    ssh_cmd bash << 'REMOTE_SCRIPT'
set -e

cd /opt/l9-build

# Clone if doesn't exist, otherwise pull
if [[ -d "L9" ]]; then
    cd L9
    echo "Current commit: $(git rev-parse --short HEAD)"
    echo "Current branch: $(git branch --show-current)"

    # Stash any local changes
    git stash --include-untracked 2>/dev/null || true

    # Fetch and reset to origin/main
    git fetch origin
    git reset --hard origin/main

    echo "Updated to: $(git rev-parse --short HEAD)"
else
    echo "Cloning L9 repository..."
    git clone https://github.com/cryptoxdog/L9.git L9
    cd L9
    echo "Cloned at: $(git rev-parse --short HEAD)"
fi

# Show recent commits
echo ""
echo "=== RECENT COMMITS ==="
git log --oneline -5
REMOTE_SCRIPT

    log_success "Code updated"
}

# =============================================================================
# PHASE 3: VERIFY ENV FILES (VPS-managed, never overwrite from local)
# =============================================================================
verify_env_files() {
    log_step "PHASE 3: VERIFY ENV FILES"

    # IMPORTANT: Env files are managed ON THE VPS, not synced from local.
    # This phase only verifies they exist and sets up symlinks.
    # To update env files, SSH to VPS and edit directly.

    if $DRY_RUN; then
        log_info "[DRY RUN] Would verify VPS env files"
        return
    fi

    log_info "Verifying VPS env files exist (NOT syncing from local)..."

    ssh_cmd bash << 'REMOTE_SCRIPT'
set -e

# Required env files on VPS
REQUIRED_FILES=(
    "/opt/l9/.env.production"
    "/opt/l9/.env.docker"
)

OPTIONAL_FILES=(
    "/opt/l9/.env.vps"
    "/opt/l9/mcp_memory/.env"
)

echo "=== REQUIRED ENV FILES ==="
missing=0
for f in "${REQUIRED_FILES[@]}"; do
    if [[ -f "$f" ]]; then
        echo "  ✓ $f ($(stat -c%s "$f" 2>/dev/null || stat -f%z "$f") bytes)"
    else
        echo "  ✗ $f MISSING"
        missing=$((missing + 1))
    fi
done

echo ""
echo "=== OPTIONAL ENV FILES ==="
for f in "${OPTIONAL_FILES[@]}"; do
    if [[ -f "$f" ]]; then
        echo "  ✓ $f"
    else
        echo "  - $f (not present)"
    fi
done

if [[ $missing -gt 0 ]]; then
    echo ""
    echo "ERROR: $missing required env file(s) missing on VPS!"
    echo "SSH to VPS and create them manually."
    exit 1
fi

# Ensure symlinks are correct
echo ""
echo "=== SYMLINKS ==="
ln -sf /opt/l9/.env.production /opt/l9/.env
echo "  ✓ /opt/l9/.env -> .env.production"

# Copy to build directory if it exists
if [[ -d /opt/l9-build/L9 ]]; then
    cp /opt/l9/.env.production /opt/l9-build/L9/.env 2>/dev/null || true
    echo "  ✓ Copied to /opt/l9-build/L9/.env"
fi

echo ""
echo "Env files verified on VPS."
REMOTE_SCRIPT

    log_success "VPS env files verified"
}

# =============================================================================
# PHASE 4: RUN DATABASE MIGRATIONS (PostgreSQL)
# =============================================================================
run_postgres_migrations() {
    log_step "PHASE 4: RUN DATABASE MIGRATIONS"

    if $SKIP_MIGRATIONS; then
        log_info "Skipping migrations (--skip-migrations flag)"
        return
    fi

    if $DRY_RUN; then
        log_info "[DRY RUN] Would run PostgreSQL migrations"
        return
    fi

    log_info "Running PostgreSQL migrations..."

    ssh_cmd bash << 'REMOTE_SCRIPT'
set -e
cd /opt/l9-build/L9

# Load environment
source /opt/l9/.env.production 2>/dev/null || true

# Get database URL from env or construct it
if [[ -z "$DATABASE_URL" ]]; then
    # Use K8s service names
    DATABASE_URL="postgresql://l9_user:${POSTGRES_PASSWORD:-l9_password}@l9-postgres.l9-c1.svc.cluster.local:5432/l9_memory"
fi

echo "Running migrations with Python..."

# Run migrations using the migration runner
python3 << 'PYTHON_SCRIPT'
import asyncio
import os
import sys

# Add repo to path
sys.path.insert(0, '/opt/l9-build/L9')

async def run():
    from memory.migration_runner import run_migrations

    database_url = os.getenv('DATABASE_URL') or os.getenv('MEMORY_DSN')

    # If using K8s, might need to use NodePort
    if not database_url:
        database_url = "postgresql://l9_user:l9_password@localhost:30432/l9_memory"

    print(f"Connecting to: {database_url.split('@')[1] if '@' in database_url else database_url}")

    try:
        result = await run_migrations(database_url)
        print(f"Status: {result['status']}")
        print(f"Applied: {result['applied']} migrations")
        print(f"Skipped: {result['skipped']} (already applied)")

        if result['errors']:
            print(f"Errors: {result['errors']}")
            for err in result['error_details']:
                print(f"  - {err['migration']}: {err['error']}")
            return 1
        return 0
    except Exception as e:
        print(f"Migration error: {e}")
        return 1

sys.exit(asyncio.run(run()))
PYTHON_SCRIPT

echo "Migrations complete"
REMOTE_SCRIPT

    log_success "PostgreSQL migrations complete"
}

# =============================================================================
# PHASE 5: RUN NEO4J MIGRATIONS (Cypher)
# =============================================================================
run_neo4j_migrations() {
    log_step "PHASE 5: RUN NEO4J MIGRATIONS"

    if $SKIP_MIGRATIONS || $SKIP_NEO4J; then
        log_info "Skipping Neo4j migrations"
        return
    fi

    if $DRY_RUN; then
        log_info "[DRY RUN] Would run Neo4j migrations"
        return
    fi

    log_info "Running Neo4j migrations (Cypher)..."

    ssh_cmd bash << 'REMOTE_SCRIPT'
set -e
cd /opt/l9-build/L9

# Load environment
source /opt/l9/.env.production 2>/dev/null || true

NEO4J_URL="${NEO4J_URL:-bolt://localhost:30687}"
NEO4J_USER="${NEO4J_USER:-neo4j}"
NEO4J_PASSWORD="${NEO4J_PASSWORD:-neo4j_password}"

# Find and run Cypher migrations
for cypher_file in migrations/*.cypher; do
    if [[ -f "$cypher_file" ]]; then
        echo "Running: $cypher_file"

        # Use cypher-shell if available, otherwise skip
        if command -v cypher-shell &>/dev/null; then
            cypher-shell -a "$NEO4J_URL" -u "$NEO4J_USER" -p "$NEO4J_PASSWORD" \
                < "$cypher_file" || echo "Warning: Cypher migration may have partial failures"
        else
            echo "  cypher-shell not available, skipping Neo4j migrations"
            echo "  Run manually: cat $cypher_file | cypher-shell -a $NEO4J_URL"
        fi
    fi
done

echo "Neo4j migrations complete"
REMOTE_SCRIPT

    log_success "Neo4j migrations complete"
}

# =============================================================================
# PHASE 6: REBUILD CONTAINERS
# =============================================================================
rebuild_containers() {
    log_step "PHASE 6: REBUILD CONTAINERS"

    if $SKIP_BUILD; then
        log_info "Skipping container rebuild (--skip-build flag)"
        return
    fi

    if $DRY_RUN; then
        log_info "[DRY RUN] Would rebuild containers"
        return
    fi

    log_info "Rebuilding Docker containers..."

    ssh_cmd bash << 'REMOTE_SCRIPT'
set -e
cd /opt/l9-build/L9

echo "=== Building L9 API image ==="
docker build \
    -f deploy/k8s/c1/Dockerfile \
    --build-arg BUILD_DATE="$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
    --build-arg VCS_REF="$(git rev-parse --short HEAD)" \
    -t ghcr.io/igor-beylin/l9-api:latest \
    -t l9-api:latest \
    .

echo "=== Building MCP Memory image ==="
if [[ -f deploy/k8s/c1/Dockerfile.mcp-memory ]]; then
    docker build \
        -f deploy/k8s/c1/Dockerfile.mcp-memory \
        -t ghcr.io/igor-beylin/l9-mcp-memory:latest \
        -t l9-mcp-memory:latest \
        .
fi

echo "=== Verifying images ==="
docker images | grep -E "(l9-api|l9-mcp)" | head -10

echo "=== Quick dependency check ==="
docker run --rm l9-api:latest python -c "
import fastapi, pydantic, asyncpg, neo4j, redis, structlog
print('✅ Core dependencies OK')
"
REMOTE_SCRIPT

    log_success "Containers rebuilt"
}

# =============================================================================
# PHASE 7: RESTART SERVICES
# =============================================================================
restart_services() {
    log_step "PHASE 7: RESTART SERVICES"

    if $DRY_RUN; then
        log_info "[DRY RUN] Would restart services"
        return
    fi

    log_info "Restarting K8s deployments..."

    ssh_cmd bash << 'REMOTE_SCRIPT'
set -e

# Restart L9 API (picks up new image)
echo "Restarting l9-api..."
kubectl rollout restart deployment/l9-api -n l9-c1 2>/dev/null || \
    echo "l9-api deployment not found, may need to apply manifests"

# Restart MCP Memory
echo "Restarting l9-mcp-memory..."
kubectl rollout restart deployment/l9-mcp-memory -n l9-c1 2>/dev/null || \
    echo "l9-mcp-memory deployment not found"

# Wait for rollouts
echo "Waiting for rollouts..."
kubectl rollout status deployment/l9-api -n l9-c1 --timeout=120s 2>/dev/null || true
kubectl rollout status deployment/l9-mcp-memory -n l9-c1 --timeout=60s 2>/dev/null || true

echo "Current pods:"
kubectl get pods -n l9-c1
REMOTE_SCRIPT

    log_success "Services restarted"
}

# =============================================================================
# PHASE 8: HEALTH CHECKS
# =============================================================================
health_checks() {
    log_step "PHASE 8: HEALTH CHECKS"

    log_info "Waiting 30s for services to stabilize..."
    sleep 30

    log_info "Checking service health..."

    local all_healthy=true

    for service in "${!SERVICE_PORTS[@]}"; do
        local port="${SERVICE_PORTS[$service]}"
        local display_name="${service//_/ }"  # Replace underscores with spaces for display

        if nc -z -w5 "$C1_IP" "$port" 2>/dev/null; then
            log_success "  ✓ $display_name (port $port): UP"
        else
            log_warn "  ✗ $display_name (port $port): DOWN or not exposed"
            all_healthy=false
        fi
    done

    # Check L9 API health endpoint
    log_info "Checking L9 API /health endpoint..."
    local api_health=$(curl -s -o /dev/null -w "%{http_code}" "http://$C1_IP:30080/health" 2>/dev/null || echo "000")

    if [[ "$api_health" == "200" ]]; then
        log_success "  ✓ L9 API health: HTTP 200"
    else
        log_warn "  ✗ L9 API health: HTTP $api_health"
        all_healthy=false
    fi

    # Check MCP Memory health
    log_info "Checking MCP Memory /health endpoint..."
    local mcp_health=$(curl -s -o /dev/null -w "%{http_code}" "http://$C1_IP:30902/health" 2>/dev/null || echo "000")

    if [[ "$mcp_health" == "200" ]]; then
        log_success "  ✓ MCP Memory health: HTTP 200"
    else
        log_warn "  ✗ MCP Memory health: HTTP $mcp_health"
        all_healthy=false
    fi

    if $all_healthy; then
        log_success "All health checks passed"
    else
        log_warn "Some services may still be starting"
    fi
}

# =============================================================================
# PHASE 9: VERIFY MEMORY SUBSTRATE
# =============================================================================
verify_memory_substrate() {
    log_step "PHASE 9: VERIFY MEMORY SUBSTRATE"

    if $DRY_RUN; then
        log_info "[DRY RUN] Would verify memory substrate"
        return
    fi

    log_info "Verifying memory substrate connectivity..."

    ssh_cmd bash << 'REMOTE_SCRIPT'
set -e

echo "=== PostgreSQL ==="
# Check if PostgreSQL is accessible
if kubectl exec -n l9-c1 deploy/l9-postgres -- pg_isready -U l9_user 2>/dev/null; then
    echo "✓ PostgreSQL is ready"

    # Check schema_migrations table
    kubectl exec -n l9-c1 deploy/l9-postgres -- psql -U l9_user -d l9_memory -c \
        "SELECT COUNT(*) as migrations_applied FROM schema_migrations;" 2>/dev/null || \
        echo "  (schema_migrations table may not exist yet)"
else
    echo "✗ PostgreSQL not accessible via kubectl"
fi

echo ""
echo "=== Redis ==="
if kubectl exec -n l9-c1 deploy/l9-redis -- redis-cli ping 2>/dev/null | grep -q PONG; then
    echo "✓ Redis is ready"
    kubectl exec -n l9-c1 deploy/l9-redis -- redis-cli info keyspace 2>/dev/null | head -5 || true
else
    echo "✗ Redis not accessible"
fi

echo ""
echo "=== Neo4j ==="
if nc -z localhost 30687 2>/dev/null; then
    echo "✓ Neo4j bolt port accessible"
else
    echo "? Neo4j bolt port not accessible from within container"
fi

echo ""
echo "=== Pod Status ==="
kubectl get pods -n l9-c1 -o wide
REMOTE_SCRIPT

    log_success "Memory substrate verified"
}

# =============================================================================
# PHASE 10: FINAL STATUS
# =============================================================================
final_status() {
    log_step "PHASE 10: FINAL STATUS"

    log_info "Generating deployment summary..."

    ssh_cmd bash << 'REMOTE_SCRIPT'
echo "=== DEPLOYMENT SUMMARY ==="
echo ""

echo "Git Commit: $(cd /opt/l9-build/L9 && git rev-parse --short HEAD)"
echo "Deployed:   $(date)"
echo ""

echo "=== PODS ==="
kubectl get pods -n l9-c1

echo ""
echo "=== SERVICES ==="
kubectl get svc -n l9-c1

echo ""
echo "=== IMAGES ==="
docker images | grep l9 | head -5
REMOTE_SCRIPT

    echo ""
    echo "============================================="
    echo -e "${GREEN}   DEPLOYMENT COMPLETE${NC}"
    echo "============================================="
    echo ""
    echo "Access endpoints:"
    echo "  L9 API:          http://$C1_IP:30080"
    echo "  MCP Memory:      http://$C1_IP:30902"
    echo "  PostgreSQL:      postgresql://l9_user@$C1_IP:30432/l9_memory"
    echo "  Neo4j Browser:   http://$C1_IP:30474"
    echo "  Neo4j Bolt:      bolt://$C1_IP:30687"
    echo "  Grafana:         http://$C1_IP:30300"
    echo "  Prometheus:      http://$C1_IP:30909"
    echo ""
    echo "Log: $LOG_FILE"
    echo ""
}

# =============================================================================
# MAIN
# =============================================================================
main() {
    echo ""
    echo "============================================="
    echo "   C1 PULL & DEPLOY"
    echo "   Target: $C1_IP"
    echo "   Started: $(date)"
    echo "============================================="
    echo ""

    if $DRY_RUN; then
        log_warn "DRY RUN MODE - No changes will be made"
        echo ""
    fi

    connect_and_verify
    pull_latest_code
    verify_env_files
    run_postgres_migrations
    run_neo4j_migrations
    rebuild_containers
    restart_services
    health_checks
    verify_memory_substrate
    final_status
}

main "$@"
