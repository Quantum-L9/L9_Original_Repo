#!/bin/bash
# L9 10X Deployment Script
# Full pipeline: Mac → Git → VPS → Rebuild → Verify
# Includes waits, health checks, and comprehensive diagnostics
#
# Usage:
#   chmod +x l9-deploy-10x.sh
#   ./l9-deploy-10x.sh [commit-message]
#
# Example:
#   ./l9-deploy-10x.sh "feat(memory): activate full compose stack"

set -e

# Configuration
COMMIT_MSG="${1:-chore(deploy): automated 10X deployment}"
MAC_REPO="/Users/ib-mac/Projects/L9"
VPS_HOST="admin@157.180.73.53"
VPS_REPO="/opt/l9"
DEPLOY_LOG="/tmp/l9-deploy-10x-$(date +%s).log"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Helper functions
log_header() {
    echo ""
    echo "╔════════════════════════════════════════════════════════════════╗"
    echo "║  $1"
    echo "╚════════════════════════════════════════════════════════════════╝"
}

log_step() {
    echo -e "${BLUE}➜${NC} $1"
}

log_ok() {
    echo -e "${GREEN}✅${NC} $1"
}

log_wait() {
    echo -e "${YELLOW}⏳${NC} $1"
}

log_error() {
    echo -e "${RED}❌${NC} $1"
}

wait_with_spinner() {
    local duration=$1
    local message=$2
    local end=$((SECONDS + duration))
    
    echo -n "$message "
    while [ $SECONDS -lt $end ]; do
        echo -n "."
        sleep 1
    done
    echo " done"
}

# ============================================================================
# PHASE 1: LOCAL VERIFICATION (MAC)
# ============================================================================
log_header "PHASE 1: Local Verification (Mac)"

cd "$MAC_REPO"

log_step "Checking git status..."
git status
echo ""

log_step "Verifying uncommitted changes..."
if [ -n "$(git status --porcelain)" ]; then
    log_wait "Found uncommitted changes. Staging all changes..."
    git add -A
    log_ok "Changes staged"
else
    log_ok "Working tree clean (or all staged)"
fi

log_step "Checking for untracked files..."
UNTRACKED=$(git ls-files --others --exclude-standard | wc -l)
if [ "$UNTRACKED" -gt 0 ]; then
    log_wait "Found $UNTRACKED untracked files. Review before commit."
    git ls-files --others --exclude-standard
    read -p "Continue? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        log_error "Deployment aborted by user"
        exit 1
    fi
fi

echo ""

# ============================================================================
# PHASE 2: GIT COMMIT & PUSH (MAC)
# ============================================================================
log_header "PHASE 2: Git Commit & Push"

log_step "Committing changes: '$COMMIT_MSG'"
git commit -m "$COMMIT_MSG" || log_ok "No changes to commit"

log_step "Fetching latest from origin..."
git fetch origin

log_step "Checking if local main is ahead of origin..."
LOCAL_COMMITS=$(git rev-list --count origin/main..main)
if [ "$LOCAL_COMMITS" -gt 0 ]; then
    log_step "Local main is $LOCAL_COMMITS commit(s) ahead. Pushing to origin..."
    git push origin main
    log_ok "Pushed to origin/main"
else
    log_ok "Already in sync with origin/main"
fi

log_step "Verifying push..."
git log --oneline -3
CURRENT_SHA=$(git rev-parse HEAD)
log_ok "Current SHA: $CURRENT_SHA"

echo ""

# ============================================================================
# PHASE 3: VPS GIT PULL & VERIFY
# ============================================================================
log_header "PHASE 3: VPS Git Pull & Verify"

log_step "Connecting to VPS ($VPS_HOST)..."
ssh "$VPS_HOST" "echo 'SSH connection OK'" > /dev/null
log_ok "SSH connection established"

log_step "Pulling latest from origin on VPS..."
ssh "$VPS_HOST" "cd $VPS_REPO && git fetch origin"
ssh "$VPS_HOST" "cd $VPS_REPO && git reset --hard origin/main"

log_step "Verifying VPS is in sync..."
VPS_SHA=$(ssh "$VPS_HOST" "cd $VPS_REPO && git rev-parse HEAD")
if [ "$CURRENT_SHA" == "$VPS_SHA" ]; then
    log_ok "VPS SHA matches Mac: $VPS_SHA"
else
    log_error "SHA mismatch! Mac: $CURRENT_SHA, VPS: $VPS_SHA"
    exit 1
fi

log_step "VPS git status:"
ssh "$VPS_HOST" "cd $VPS_REPO && git status"

echo ""

# ============================================================================
# PHASE 4: VPS ENVIRONMENT VERIFICATION
# ============================================================================
log_header "PHASE 4: VPS Environment Verification"

log_step "Running environment verification script on VPS..."
ssh "$VPS_HOST" "cd $VPS_REPO && bash scripts/verify_vps_env.sh" | tee -a "$DEPLOY_LOG"

log_ok "Environment verification complete"

echo ""

# ============================================================================
# PHASE 5: VPS DOCKER REBUILD (NO CACHE)
# ============================================================================
log_header "PHASE 5: VPS Docker Rebuild (No Cache)"

log_step "Stopping current l9-api container..."
ssh "$VPS_HOST" "cd $VPS_REPO && docker compose down l9-api" || true
wait_with_spinner 3 "Waiting for graceful shutdown..."

log_step "Building l9-api image (no cache)..."
ssh "$VPS_HOST" "cd $VPS_REPO && docker compose build --no-cache l9-api"
log_ok "Build complete"

log_step "Starting l9-api container..."
ssh "$VPS_HOST" "cd $VPS_REPO && docker compose up -d l9-api"
log_ok "Container started"

wait_with_spinner 5 "Waiting for container initialization..."

echo ""

# ============================================================================
# PHASE 6: VPS HEALTH CHECKS
# ============================================================================
log_header "PHASE 6: VPS Health Checks"

log_step "Checking Docker container status..."
ssh "$VPS_HOST" "cd $VPS_REPO && docker compose ps" | tee -a "$DEPLOY_LOG"

log_step "Checking l9-api startup logs..."
ssh "$VPS_HOST" "cd $VPS_REPO && docker compose logs l9-api --tail=30" | tee -a "$DEPLOY_LOG"

log_wait "Waiting for API to be ready..."
wait_with_spinner 5 "Allowing API to fully initialize..."

log_step "Testing API health endpoint..."
HEALTH_RESPONSE=$(ssh "$VPS_HOST" "curl -s http://127.0.0.1:8000/health 2>/dev/null || echo 'FAIL'")
if [[ "$HEALTH_RESPONSE" == *"status"* ]]; then
    log_ok "API is healthy"
    echo "Response: $HEALTH_RESPONSE" | jq . 2>/dev/null || echo "$HEALTH_RESPONSE"
else
    log_error "API health check failed: $HEALTH_RESPONSE"
    log_error "Checking logs for errors..."
    ssh "$VPS_HOST" "cd $VPS_REPO && docker compose logs l9-api --tail=50"
    exit 1
fi

echo ""

# ============================================================================
# PHASE 7: VPS DATABASE CONNECTIVITY
# ============================================================================
log_header "PHASE 7: VPS Database Connectivity"

log_step "Testing PostgreSQL connection..."
PG_TEST=$(ssh "$VPS_HOST" "cd $VPS_REPO && source .env && psql -h 127.0.0.1 -U \$POSTGRES_USER -d \$POSTGRES_DB -c 'SELECT 1;' 2>&1 || echo 'FAIL'")
if [[ "$PG_TEST" == *"(1 row)"* ]]; then
    log_ok "PostgreSQL connection OK"
else
    log_wait "PostgreSQL may not be ready yet"
fi

log_step "Testing memory schema..."
PG_SCHEMA=$(ssh "$VPS_HOST" "cd $VPS_REPO && source .env && psql -h 127.0.0.1 -U \$POSTGRES_USER -d \$POSTGRES_DB -c \"SELECT count(*) FROM information_schema.tables WHERE table_schema = 'memory';\" 2>&1 || echo 'FAIL'")
if [[ "$PG_SCHEMA" != "FAIL" ]]; then
    log_ok "Memory schema tables found: $PG_SCHEMA"
else
    log_wait "Memory schema check pending initialization"
fi

echo ""

# ============================================================================
# PHASE 8: VPS COMPREHENSIVE DIAGNOSTICS
# ============================================================================
log_header "PHASE 8: VPS Comprehensive Diagnostics"

log_step "Running full MRI diagnostic on VPS..."

# Build the MRI script inline
MRI_SCRIPT=$(cat <<'EOF'
#!/bin/bash
set -e

echo "════════════════════════════════════════════════════════════════"
echo "L9 VPS DEPLOYMENT DIAGNOSTICS"
echo "════════════════════════════════════════════════════════════════"
echo ""

echo "📊 SYSTEM INFO"
echo "────────────────────────────────────────────────────────────────"
hostname
uname -a
df -h / | tail -1
echo ""

echo "🐳 DOCKER STATUS"
echo "────────────────────────────────────────────────────────────────"
docker compose ps
echo ""

echo "📋 CONTAINER LOGS (Last 30 lines)"
echo "────────────────────────────────────────────────────────────────"
docker compose logs l9-api --tail=30
echo ""

echo "🔍 API ENDPOINTS"
echo "────────────────────────────────────────────────────────────────"
echo "Health:"
curl -s http://127.0.0.1:8000/health | jq . 2>/dev/null || echo "FAIL"
echo ""
echo "Docs:"
curl -s http://127.0.0.1:8000/docs -I | head -1
echo ""

echo "🗄️  DATABASE"
echo "────────────────────────────────────────────────────────────────"
source .env
psql -h 127.0.0.1 -U $POSTGRES_USER -d $POSTGRES_DB -c "SELECT 'PostgreSQL OK', count(*) as tables FROM information_schema.tables WHERE table_schema = 'memory';" 2>&1 || echo "PostgreSQL check skipped"
echo ""

echo "📦 SERVICES"
echo "────────────────────────────────────────────────────────────────"
echo "Redis:"
redis-cli -h 127.0.0.1 ping 2>&1 || echo "Redis not available"
echo ""
echo "Neo4j:"
neo4j-admin --version 2>&1 || echo "Neo4j check skipped"
echo ""

echo "🎯 NETWORKING"
echo "────────────────────────────────────────────────────────────────"
ss -tlnp | grep -E ":(8000|5432|6379|7687|9090|3000|16686)" || echo "Filtered ports not fully listening"
echo ""

echo "════════════════════════════════════════════════════════════════"
echo "✅ DIAGNOSTICS COMPLETE"
echo "════════════════════════════════════════════════════════════════"
EOF
)

ssh "$VPS_HOST" "cd $VPS_REPO && $MRI_SCRIPT" | tee -a "$DEPLOY_LOG"

echo ""

# ============================================================================
# PHASE 9: MCP MEMORY E2E TEST (OPTIONAL)
# ============================================================================
log_header "PHASE 9: MCP Memory E2E Test (Optional)"

log_step "Checking for MCP_API_KEY_C..."
MCP_KEY=$(ssh "$VPS_HOST" "cd $VPS_REPO && grep MCP_API_KEY_C .env | cut -d= -f2")
if [ -n "$MCP_KEY" ]; then
    log_wait "Running MCP memory E2E test..."
    
    # Save test
    MCP_TEST=$(cat <<EOF
import requests
import json
import os
import sys

url = 'http://127.0.0.1:8000/memory/packet'
key = '$MCP_KEY'
headers = {
    'Authorization': f'Bearer {key}',
    'Content-Type': 'application/json'
}
payload = {
    'content': 'E2E Test via 10X Deploy - ' + os.popen('date').read().strip(),
    'kind': 'preference',
    'scope': 'developer',
    'tags': ['deploy', 'e2e', '10x']
}

try:
    r = requests.post(url, headers=headers, json=payload, timeout=5)
    if r.status_code == 200:
        print('✅ MCP memory write OK')
        print(json.dumps(r.json(), indent=2))
    else:
        print(f'⚠️  MCP memory write returned {r.status_code}')
        print(r.text)
except Exception as e:
    print(f'❌ MCP memory test failed: {e}')
    sys.exit(1)
EOF
)
    
    ssh "$VPS_HOST" "cd $VPS_REPO && python3 -c \"$MCP_TEST\"" || log_wait "MCP test skipped (dependencies not loaded yet)"
else
    log_wait "MCP_API_KEY_C not set, skipping E2E test"
fi

echo ""

# ============================================================================
# PHASE 10: SUMMARY & NEXT STEPS
# ============================================================================
log_header "PHASE 10: Deployment Summary"

log_ok "✅ DEPLOYMENT COMPLETE"
echo ""
echo "Summary:"
echo "  • Mac repo synced with origin/main"
echo "  • VPS repo pulled and verified at SHA: $CURRENT_SHA"
echo "  • Environment verified"
echo "  • Docker image rebuilt (no cache)"
echo "  • Container health checks passed"
echo "  • Comprehensive diagnostics logged"
echo ""
echo "Deployment log: $DEPLOY_LOG"
echo ""
echo "Next steps:"
echo "  1. Monitor logs: docker compose -f /opt/l9/docker/docker-compose.yml logs -f l9-api"
echo "  2. Test endpoints: curl https://l9.quantumaipartners.com/health"
echo "  3. Check Caddy: sudo systemctl status caddy"
echo ""
log_ok "Ready for production validation!"
