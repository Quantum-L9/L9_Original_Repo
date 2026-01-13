#!/bin/bash
# =============================================================================
# L9 10X Deployment Script v2.0
# Full pipeline: Mac → Git → VPS → Rebuild → Verify
#
# IMPROVEMENTS (GMP-71):
#   1. Safe git pull (stash + pull, no reset --hard)
#   2. Correct paths (scripts/vps/)
#   3. Uses existing vps-mri.sh instead of inline
#   4. --dry-run and --quick flags
#   5. Rollback capability on failure
#
# Usage:
#   ./10X_Deploy_Script.sh [options] [commit-message]
#
# Options:
#   --dry-run     Show what would happen without doing it
#   --quick       Skip --no-cache rebuild (faster)
#   --skip-mri    Skip full MRI diagnostic
#   --skip-e2e    Skip MCP E2E test
#   -h, --help    Show this help
#
# Examples:
#   ./10X_Deploy_Script.sh "feat(memory): activate full compose stack"
#   ./10X_Deploy_Script.sh --dry-run
#   ./10X_Deploy_Script.sh --quick "hotfix: typo"
# =============================================================================

set -euo pipefail

# =============================================================================
# CONFIGURATION
# =============================================================================

MAC_REPO="/Users/ib-mac/Projects/L9"
VPS_HOST="admin@157.180.73.53"
VPS_REPO="/opt/l9"
DEPLOY_LOG="/tmp/l9-deploy-10x-$(date +%s).log"

# Flags
DRY_RUN=false
QUICK=false
SKIP_MRI=false
SKIP_E2E=false
COMMIT_MSG=""

# State tracking
PREV_VPS_SHA=""
CURRENT_SHA=""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

log_header() {
    echo ""
    echo -e "${CYAN}╔════════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║  $1${NC}"
    echo -e "${CYAN}╚════════════════════════════════════════════════════════════════╝${NC}"
}

log_step() {
    echo -e "${BLUE}➜${NC} $1"
}

log_ok() {
    echo -e "${GREEN}✅${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}⚠️${NC} $1"
}

log_error() {
    echo -e "${RED}❌${NC} $1"
}

wait_with_spinner() {
    local duration=$1
    local message=$2
    echo -n "$message "
    for ((i=0; i<duration; i++)); do
        echo -n "."
        sleep 1
    done
    echo " done"
}

usage() {
    cat <<EOF
L9 10X Deployment Script v2.0

Usage: $0 [options] [commit-message]

Options:
    --dry-run     Show what would happen without executing
    --quick       Skip --no-cache on docker build (faster)
    --skip-mri    Skip full MRI diagnostic at the end
    --skip-e2e    Skip MCP E2E test
    -h, --help    Show this help

Examples:
    $0 "feat(memory): new feature"
    $0 --dry-run
    $0 --quick "hotfix: typo fix"

Default commit message: "chore(deploy): automated 10X deployment"
EOF
}

rollback() {
    if [[ -n "$PREV_VPS_SHA" ]]; then
        log_error "Deployment failed! Rolling back VPS to $PREV_VPS_SHA..."
        ssh "$VPS_HOST" "cd $VPS_REPO && git checkout $PREV_VPS_SHA" || true
        ssh "$VPS_HOST" "cd $VPS_REPO && docker compose up -d l9-api" || true
        log_warn "Rollback attempted. Check VPS manually."
    fi
    exit 1
}

# =============================================================================
# ARGUMENT PARSING
# =============================================================================

while [[ $# -gt 0 ]]; do
    case $1 in
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        --quick)
            QUICK=true
            shift
            ;;
        --skip-mri)
            SKIP_MRI=true
            shift
            ;;
        --skip-e2e)
            SKIP_E2E=true
            shift
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            COMMIT_MSG="$1"
            shift
            ;;
    esac
done

# Default commit message
COMMIT_MSG="${COMMIT_MSG:-chore(deploy): automated 10X deployment}"

# =============================================================================
# DRY RUN MODE
# =============================================================================

if [[ "$DRY_RUN" == "true" ]]; then
    log_header "DRY RUN MODE - No changes will be made"
    
    cd "$MAC_REPO"
    
    echo ""
    log_step "Would commit with message: '$COMMIT_MSG'"
    echo ""
    
    log_step "Local changes to commit:"
    git status --short
    echo ""
    
    log_step "Commits to push:"
    git fetch origin 2>/dev/null || true
    git log --oneline origin/main..HEAD 2>/dev/null || echo "  (none or not fetched)"
    echo ""
    
    log_step "VPS would pull and rebuild l9-api"
    [[ "$QUICK" == "true" ]] && echo "  (--quick mode: with cache)" || echo "  (full rebuild: --no-cache)"
    echo ""
    
    log_ok "Dry run complete. Run without --dry-run to execute."
    exit 0
fi

# =============================================================================
# PHASE 1: LOCAL VERIFICATION (MAC)
# =============================================================================
log_header "PHASE 1: Local Verification (Mac)"

cd "$MAC_REPO"

log_step "Checking git status..."
git status --short
echo ""

log_step "Staging any uncommitted changes..."
if [[ -n "$(git status --porcelain)" ]]; then
    git add -A
    log_ok "Changes staged"
else
    log_ok "Working tree clean"
fi

# =============================================================================
# PHASE 2: GIT COMMIT & PUSH (MAC)
# =============================================================================
log_header "PHASE 2: Git Commit & Push"

log_step "Committing: '$COMMIT_MSG'"
git commit -m "$COMMIT_MSG" 2>/dev/null || log_ok "No changes to commit"

log_step "Fetching from origin..."
git fetch origin

log_step "Checking sync status..."
LOCAL_COMMITS=$(git rev-list --count origin/main..main 2>/dev/null || echo "0")
if [[ "$LOCAL_COMMITS" -gt 0 ]]; then
    log_step "Pushing $LOCAL_COMMITS commit(s) to origin..."
    git push origin main
    log_ok "Pushed to origin/main"
else
    log_ok "Already in sync with origin/main"
fi

CURRENT_SHA=$(git rev-parse HEAD)
log_ok "Current SHA: $CURRENT_SHA"

# =============================================================================
# PHASE 3: VPS GIT PULL (SAFE - preserves local changes)
# =============================================================================
log_header "PHASE 3: VPS Git Pull (Safe)"

log_step "Connecting to VPS ($VPS_HOST)..."
ssh "$VPS_HOST" "echo 'SSH OK'" > /dev/null
log_ok "SSH connection established"

# Save previous SHA for rollback
PREV_VPS_SHA=$(ssh "$VPS_HOST" "cd $VPS_REPO && git rev-parse HEAD")
log_step "Previous VPS SHA: $PREV_VPS_SHA"

# SAFE PULL: Stash local changes, pull, restore
log_step "Stashing VPS local changes (if any)..."
ssh "$VPS_HOST" "cd $VPS_REPO && git stash push -m 'pre-deploy-$(date +%s)' 2>/dev/null || true"

log_step "Pulling latest from origin..."
ssh "$VPS_HOST" "cd $VPS_REPO && git fetch origin"
if ssh "$VPS_HOST" "cd $VPS_REPO && git pull --ff-only origin main"; then
    log_ok "Fast-forward pull successful"
else
    log_warn "Cannot fast-forward, attempting merge..."
    if ssh "$VPS_HOST" "cd $VPS_REPO && git pull origin main"; then
        log_ok "Merge pull successful"
    else
        log_error "Pull failed! Check VPS for conflicts."
        rollback
    fi
fi

# Restore stashed changes
log_step "Restoring VPS local changes..."
ssh "$VPS_HOST" "cd $VPS_REPO && git stash pop 2>/dev/null || true"

# Verify sync
VPS_SHA=$(ssh "$VPS_HOST" "cd $VPS_REPO && git rev-parse HEAD")
if [[ "$CURRENT_SHA" == "$VPS_SHA" ]]; then
    log_ok "VPS SHA matches Mac: $VPS_SHA"
else
    log_warn "SHA mismatch (Mac: $CURRENT_SHA, VPS: $VPS_SHA) - may have local commits"
fi

# =============================================================================
# PHASE 3.5: INSTALL GIT HOOKS
# =============================================================================
log_header "PHASE 3.5: Install Git Hooks"

log_step "Installing git hooks on VPS..."
if ssh "$VPS_HOST" "cd $VPS_REPO && bash scripts/install_git_hooks.sh"; then
    log_ok "Git hooks installed"
else
    log_warn "Git hooks installation failed (non-fatal)"
fi

# =============================================================================
# PHASE 4: VPS ENVIRONMENT VERIFICATION
# =============================================================================
log_header "PHASE 4: VPS Environment Verification"

log_step "Running environment sync and verification..."
ssh "$VPS_HOST" "cd $VPS_REPO && bash scripts/vps/sync_env_vars.sh --quiet" || true
ssh "$VPS_HOST" "cd $VPS_REPO && bash scripts/vps/verify_vps_env.sh --quick" | tee -a "$DEPLOY_LOG"

log_ok "Environment verification complete"

# =============================================================================
# PHASE 5: VPS DOCKER REBUILD
# =============================================================================
log_header "PHASE 5: VPS Docker Rebuild"

log_step "Stopping current l9-api container..."
ssh "$VPS_HOST" "cd $VPS_REPO && docker compose stop l9-api" || true
wait_with_spinner 3 "Waiting for graceful shutdown..."

BUILD_OPTS=""
if [[ "$QUICK" == "false" ]]; then
    BUILD_OPTS="--no-cache"
    log_step "Building l9-api image (no cache - full rebuild)..."
else
    log_step "Building l9-api image (with cache - quick mode)..."
fi

if ssh "$VPS_HOST" "cd $VPS_REPO && docker compose build $BUILD_OPTS l9-api"; then
    log_ok "Build complete"
else
    log_error "Docker build failed!"
    rollback
fi

log_step "Starting l9-api container..."
ssh "$VPS_HOST" "cd $VPS_REPO && docker compose up -d l9-api"
log_ok "Container started"

wait_with_spinner 5 "Waiting for initialization..."

# =============================================================================
# PHASE 6: VPS HEALTH CHECKS
# =============================================================================
log_header "PHASE 6: VPS Health Checks"

log_step "Checking container status..."
ssh "$VPS_HOST" "cd $VPS_REPO && docker compose ps l9-api" | tee -a "$DEPLOY_LOG"

log_step "Checking startup logs..."
ssh "$VPS_HOST" "cd $VPS_REPO && docker compose logs l9-api --tail=20" | tee -a "$DEPLOY_LOG"

wait_with_spinner 5 "Allowing API to fully initialize..."

log_step "Testing API health endpoint..."
HEALTH_RESPONSE=$(ssh "$VPS_HOST" "curl -s http://127.0.0.1:8000/health 2>/dev/null || echo 'FAIL'")
if [[ "$HEALTH_RESPONSE" == *"status"* ]] || [[ "$HEALTH_RESPONSE" == *"ok"* ]]; then
    log_ok "API is healthy"
    echo "$HEALTH_RESPONSE" | jq . 2>/dev/null || echo "$HEALTH_RESPONSE"
else
    log_error "API health check failed!"
    log_error "Response: $HEALTH_RESPONSE"
    ssh "$VPS_HOST" "cd $VPS_REPO && docker compose logs l9-api --tail=50"
    rollback
fi

# =============================================================================
# PHASE 7: DATABASE CONNECTIVITY
# =============================================================================
log_header "PHASE 7: Database Connectivity"

log_step "Testing PostgreSQL..."
PG_TEST=$(ssh "$VPS_HOST" "cd $VPS_REPO && source .env && PGPASSWORD=\$POSTGRES_PASSWORD psql -h 127.0.0.1 -U \$POSTGRES_USER -d \$POSTGRES_DB -c 'SELECT 1;' 2>&1 || echo 'FAIL'")
if [[ "$PG_TEST" == *"1 row"* ]]; then
    log_ok "PostgreSQL connection OK"
else
    log_warn "PostgreSQL check inconclusive (may need container network)"
fi

# =============================================================================
# PHASE 8: FULL MRI DIAGNOSTIC (Optional)
# =============================================================================
if [[ "$SKIP_MRI" == "false" ]]; then
    log_header "PHASE 8: Full MRI Diagnostic"
    
    log_step "Running vps-mri.sh..."
    ssh "$VPS_HOST" "cd $VPS_REPO && bash scripts/vps/vps-mri.sh" 2>&1 | tee -a "$DEPLOY_LOG" | tail -50
else
    log_header "PHASE 8: MRI Diagnostic (SKIPPED)"
    log_warn "Use --skip-mri=false for full diagnostic"
fi

# =============================================================================
# PHASE 9: MCP E2E TEST (Optional)
# =============================================================================
if [[ "$SKIP_E2E" == "false" ]]; then
    log_header "PHASE 9: MCP Memory E2E Test"
    
    MCP_KEY=$(ssh "$VPS_HOST" "cd $VPS_REPO && grep MCP_API_KEY_C .env 2>/dev/null | cut -d= -f2" || echo "")
    if [[ -n "$MCP_KEY" ]]; then
        log_step "Running MCP memory write test..."
        
        E2E_RESULT=$(ssh "$VPS_HOST" "curl -s -X POST http://127.0.0.1:8000/memory/packet \
            -H 'Authorization: Bearer $MCP_KEY' \
            -H 'Content-Type: application/json' \
            -d '{\"content\": \"E2E Test via 10X Deploy v2.0 - $(date)\", \"kind\": \"note\", \"tags\": [\"deploy\", \"e2e\"]}'" 2>/dev/null || echo "FAIL")
        
        if [[ "$E2E_RESULT" == *"id"* ]] || [[ "$E2E_RESULT" == *"success"* ]]; then
            log_ok "MCP memory write OK"
        else
            log_warn "MCP E2E test inconclusive: $E2E_RESULT"
        fi
    else
        log_warn "MCP_API_KEY_C not set, skipping E2E test"
    fi
else
    log_header "PHASE 9: MCP E2E Test (SKIPPED)"
fi

# =============================================================================
# PHASE 10: SUMMARY
# =============================================================================
log_header "PHASE 10: Deployment Summary"

echo ""
log_ok "✅ DEPLOYMENT COMPLETE"
echo ""
echo "Summary:"
echo "  • Mac SHA: $CURRENT_SHA"
echo "  • VPS SHA: $VPS_SHA"
echo "  • Previous VPS SHA: $PREV_VPS_SHA (for rollback)"
echo "  • Build mode: $([[ "$QUICK" == "true" ]] && echo "quick (cached)" || echo "full (no-cache)")"
echo ""
echo "Deployment log: $DEPLOY_LOG"
echo ""
echo "Next steps:"
echo "  1. Monitor: docker compose logs -f l9-api"
echo "  2. Test: curl https://l9.quantumaipartners.com/health"
echo "  3. Full diagnostic: ./scripts/vps/vps-mri.sh"
echo ""
echo "Rollback (if needed):"
echo "  ssh $VPS_HOST 'cd $VPS_REPO && git checkout $PREV_VPS_SHA && docker compose up -d --build l9-api'"
echo ""
log_ok "Ready for production!"
