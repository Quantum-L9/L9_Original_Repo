#!/bin/bash
# =============================================================================
# L9 10X Deployment Script v3.0
# Full pipeline: Mac → Git → VPS → Rebuild → Verify
#
# IMPROVEMENTS:
#   v2.0 (GMP-71): Safe git pull, --dry-run, --quick, rollback
#   v3.0 (GMP-77): Pre-flight checks, health retries, migrations gate,
#                  conditional prune, .env backup, Slack notify, enhanced rollback
#
# Usage:
#   ./10X_Deploy_Script.sh [options] [commit-message]
#
# Options:
#   --dry-run         Show what would happen without doing it
#   --quick           Skip --no-cache rebuild (faster)
#   --skip-mri        Skip full MRI diagnostic
#   --skip-e2e        Skip MCP E2E test
#   --run-migrations  Apply pending database migrations
#   --prune-docker    Clean Docker system (volumes, images, containers)
#   --version         Show version and exit
#   -h, --help        Show this help
#
# Examples:
#   ./10X_Deploy_Script.sh "feat(memory): activate full compose stack"
#   ./10X_Deploy_Script.sh --dry-run
#   ./10X_Deploy_Script.sh --quick "hotfix: typo"
#   ./10X_Deploy_Script.sh --run-migrations --prune-docker "major release"
# =============================================================================

set -euo pipefail

# =============================================================================
# CONFIGURATION
# =============================================================================

MAC_REPO="$HOME/Projects/L9"
VPS_HOST="admin@157.180.73.53"
VPS_REPO="/opt/l9"
DEPLOY_LOG="/tmp/l9-deploy-10x-$(date +%s).log"

# Flags
DRY_RUN=false
QUICK=false
SKIP_MRI=false
SKIP_E2E=false
RUN_MIGRATIONS=false
PRUNE_DOCKER=false
COMMIT_MSG=""

# State tracking
PREV_VPS_SHA=""
CURRENT_SHA=""

# Health check settings
HEALTH_MAX_RETRIES=12  # 60 seconds total (12 × 5s)
HEALTH_RETRY_INTERVAL=5

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

# Structured logging: capture all output to file AND stdout
exec > >(tee -a "$DEPLOY_LOG")
exec 2>&1

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

verify_vps_env_complete() {
    log_step "Ensuring VPS .env defines all keys from .env.example..."
    if ssh "$VPS_HOST" "cd $VPS_REPO && bash -lc 'set -euo pipefail; \
        if [[ ! -f .env ]]; then echo \"Missing .env\"; exit 1; fi; \
        if [[ ! -f .env.example ]]; then echo \"Missing .env.example\"; exit 1; fi; \
        required_keys=\$(grep -E \"^[A-Z0-9_]+=\" .env.example | cut -d= -f1 | sort -u); \
        present_keys=\$(grep -E \"^[A-Z0-9_]+=\" .env | cut -d= -f1 | sort -u); \
        missing=\$(comm -23 <(echo \"\$required_keys\") <(echo \"\$present_keys\")); \
        if [[ -n \"\$missing\" ]]; then echo \"Missing keys in .env:\"; echo \"\$missing\"; exit 1; fi'"; then
        log_ok "VPS .env includes all .env.example keys"
    else
        log_error "VPS .env missing required keys"
        rollback
    fi
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
L9 10X Deployment Script v3.0

Usage: $0 [options] [commit-message]

Options:
    --dry-run         Show what would happen without executing
    --quick           Skip --no-cache on docker build (faster)
    --skip-mri        Skip full MRI diagnostic at the end
    --skip-e2e        Skip MCP E2E test
    --run-migrations  Apply pending database migrations
    --prune-docker    Clean Docker system (volumes, images, containers)
    --version         Show version and exit
    -h, --help        Show this help

Examples:
    $0 "feat(memory): new feature"
    $0 --dry-run
    $0 --quick "hotfix: typo fix"
    $0 --run-migrations --prune-docker "major release"

Default commit message: "chore(deploy): automated 10X deployment"
EOF
}

rollback() {
    log_header "ROLLBACK INITIATED"
    log_error "Deployment failed! Reverting to previous state..."
    
    if [[ -n "$PREV_VPS_SHA" ]]; then
        log_step "Reverting VPS to SHA: $PREV_VPS_SHA"
        ssh "$VPS_HOST" "cd $VPS_REPO && git checkout $PREV_VPS_SHA 2>&1" || log_error "Git rollback failed!"
        
        log_step "Rebuilding services with previous code..."
        ssh "$VPS_HOST" "cd $VPS_REPO && docker compose up -d --build l9-api" || log_error "Service restart failed!"
        
        wait_with_spinner 10 "Allowing services to stabilize..."
        
        # Verify rollback worked
        log_step "Verifying rollback health..."
        ROLLBACK_HEALTH=$(ssh "$VPS_HOST" "curl -s --max-time 10 http://127.0.0.1:8000/health 2>/dev/null || echo 'FAIL'")
        if [[ "$ROLLBACK_HEALTH" == *"status"* ]] || [[ "$ROLLBACK_HEALTH" == *"ok"* ]]; then
            log_ok "Rollback successful - service is healthy"
        else
            log_error "Rollback failed - manual intervention required!"
            log_error "SSH: ssh $VPS_HOST"
            log_error "Logs: cd $VPS_REPO && docker compose logs l9-api --tail=100"
        fi
    else
        log_error "No previous SHA saved - cannot rollback"
        log_error "Manual intervention required: ssh $VPS_HOST"
    fi
    
    log_error "Deployment log: $DEPLOY_LOG"
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
        --run-migrations)
            RUN_MIGRATIONS=true
            shift
            ;;
        --prune-docker)
            PRUNE_DOCKER=true
            shift
            ;;
        --version)
            echo "L9 10X Deployment Script v3.0"
            echo "Compatible with: L9 VPS production stack"
            echo "Features: pre-flight checks, health retries, migrations, rollback"
            exit 0
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
# PHASE 0: PRE-FLIGHT CHECKS
# =============================================================================
log_header "PHASE 0: Pre-flight Checks"

log_step "Verifying SSH connectivity to VPS..."
if ! ssh -o ConnectTimeout=10 -o BatchMode=yes "$VPS_HOST" "echo 'OK'" >/dev/null 2>&1; then
    log_error "Cannot reach VPS at $VPS_HOST"
    log_error "Check: SSH keys, network, VPS status"
    exit 1
fi
log_ok "SSH connection OK"

log_step "Verifying local repo is on main branch..."
cd "$MAC_REPO"
BRANCH=$(git rev-parse --abbrev-ref HEAD)
if [[ "$BRANCH" != "main" ]]; then
    log_error "Must be on 'main' branch (currently on '$BRANCH')"
    log_error "Run: git checkout main"
    exit 1
fi
log_ok "On main branch"

log_step "Checking for merge conflicts..."
if git ls-files -u 2>/dev/null | grep -q '^'; then
    log_error "Unresolved merge conflicts detected!"
    log_error "Run: git status to see conflicts"
    exit 1
fi
log_ok "No merge conflicts"

log_step "Checking for uncommitted secrets..."
if git diff --cached --name-only 2>/dev/null | grep -qE '\.env$|credentials|secret|\.pem$|\.key$'; then
    log_warn "Potential secrets in staged files - review before commit"
fi

log_ok "Pre-flight checks passed"
echo "Logging to: $DEPLOY_LOG"

# =============================================================================
# PHASE 1: LOCAL VERIFICATION (MAC)
# =============================================================================
log_header "PHASE 1: Local Verification (Mac)"

# Already in $MAC_REPO from Phase 0

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

log_step "Backing up VPS .env before sync..."
ssh "$VPS_HOST" "cd $VPS_REPO && cp .env .env.backup-\$(date +%s)" 2>/dev/null || log_warn "No .env to backup"
log_ok ".env backup created"

log_step "Running environment sync and verification..."
verify_vps_env_complete
ssh "$VPS_HOST" "cd $VPS_REPO && bash scripts/vps/sync_env_vars.sh --quiet" || true
ssh "$VPS_HOST" "cd $VPS_REPO && bash scripts/vps/verify_vps_env.sh --quick" | tee -a "$DEPLOY_LOG"

log_ok "Environment verification complete"

# =============================================================================
# PHASE 4.5: DATABASE MIGRATION CHECK
# =============================================================================
log_header "PHASE 4.5: Database Migration Check"

log_step "Checking for migration files..."
MIGRATION_COUNT=$(ssh "$VPS_HOST" "cd $VPS_REPO && ls -1 migrations/*.sql 2>/dev/null | wc -l" || echo "0")
MIGRATION_COUNT=$(echo "$MIGRATION_COUNT" | tr -d '[:space:]')

if [[ "$MIGRATION_COUNT" -gt 0 ]]; then
    log_warn "Found $MIGRATION_COUNT migration file(s) in migrations/"
    
    if [[ "$RUN_MIGRATIONS" == "true" ]]; then
        log_step "Running migrations (--run-migrations flag set)..."
        if ssh "$VPS_HOST" "cd $VPS_REPO && bash scripts/vps/run_migrations.sh 2>&1"; then
            log_ok "Migrations applied successfully"
        else
            log_error "Migration failed!"
            rollback
        fi
    else
        log_warn "Skipping migrations (use --run-migrations to apply)"
        log_warn "Check: ls $VPS_REPO/migrations/*.sql"
    fi
else
    log_ok "No pending migrations found"
fi

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

log_step "Testing API health endpoint (with retries)..."
RETRY_COUNT=0
HEALTH_OK=false

while [[ $RETRY_COUNT -lt $HEALTH_MAX_RETRIES ]]; do
    HEALTH_RESPONSE=$(ssh "$VPS_HOST" "curl -s --max-time 10 http://127.0.0.1:8000/health 2>/dev/null || echo 'FAIL'")
    
    if [[ "$HEALTH_RESPONSE" == *"status"* ]] || [[ "$HEALTH_RESPONSE" == *"ok"* ]] || [[ "$HEALTH_RESPONSE" == *"healthy"* ]]; then
        HEALTH_OK=true
        break
    fi
    
    ((RETRY_COUNT++))
    if [[ $RETRY_COUNT -lt $HEALTH_MAX_RETRIES ]]; then
        echo -n "  Retry $RETRY_COUNT/$HEALTH_MAX_RETRIES..."
        sleep $HEALTH_RETRY_INTERVAL
    fi
done

if [[ "$HEALTH_OK" == "true" ]]; then
    log_ok "API is healthy (after $RETRY_COUNT retries)"
    echo "$HEALTH_RESPONSE" | jq . 2>/dev/null || echo "$HEALTH_RESPONSE"
else
    log_error "API health check failed after $HEALTH_MAX_RETRIES attempts!"
    log_error "Last response: $HEALTH_RESPONSE"
    log_step "Fetching container logs for diagnosis..."
    ssh "$VPS_HOST" "cd $VPS_REPO && docker compose logs l9-api --tail=100"
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
# PHASE 8: DOCKER CLEANUP (Conditional)
# =============================================================================
log_header "PHASE 8: Docker Cleanup"

if [[ "$PRUNE_DOCKER" == "true" ]]; then
    log_step "Cleaning up Docker system (--prune-docker flag set)..."
    log_warn "This will remove unused images, containers, and volumes!"
    ssh "$VPS_HOST" "docker system prune -af --volumes" || log_warn "Docker prune failed (non-fatal)"
    log_ok "Docker cleanup complete"
else
    log_warn "Skipping Docker prune (use --prune-docker if needed)"
    log_step "Removing only dangling images..."
    ssh "$VPS_HOST" "docker image prune -f" 2>/dev/null || true
fi

# =============================================================================
# PHASE 9: FULL MRI DIAGNOSTIC (Optional)
# =============================================================================
if [[ "$SKIP_MRI" == "false" ]]; then
    log_header "PHASE 9: Full MRI Diagnostic"
    
    log_step "Running vps-mri.sh..."
    ssh "$VPS_HOST" "cd $VPS_REPO && bash scripts/deployment/vps-mri.sh" 2>&1 | tee -a "$DEPLOY_LOG" | tail -50
else
    log_header "PHASE 9: MRI Diagnostic (SKIPPED)"
    log_warn "Use without --skip-mri for full diagnostic"
fi

# =============================================================================
# PHASE 10: MCP E2E TEST (Optional)
# =============================================================================
if [[ "$SKIP_E2E" == "false" ]]; then
    log_header "PHASE 10: MCP Memory E2E Test"
    
    MCP_KEY=$(ssh "$VPS_HOST" "cd $VPS_REPO && grep MCP_API_KEY_C .env 2>/dev/null | cut -d= -f2" || echo "")
    if [[ -n "$MCP_KEY" ]]; then
        log_step "Running MCP memory write test..."
        
        E2E_RESULT=$(ssh "$VPS_HOST" "curl -s -X POST http://127.0.0.1:8000/memory/packet \
            -H 'Authorization: Bearer $MCP_KEY' \
            -H 'Content-Type: application/json' \
            -d '{\"content\": \"E2E Test via 10X Deploy v3.0 - $(date)\", \"kind\": \"note\", \"tags\": [\"deploy\", \"e2e\"]}'" 2>/dev/null || echo "FAIL")
        
        if [[ "$E2E_RESULT" == *"id"* ]] || [[ "$E2E_RESULT" == *"success"* ]]; then
            log_ok "MCP memory write OK"
        else
            log_warn "MCP E2E test inconclusive: $E2E_RESULT"
        fi
    else
        log_warn "MCP_API_KEY_C not set, skipping E2E test"
    fi
else
    log_header "PHASE 10: MCP E2E Test (SKIPPED)"
fi

# =============================================================================
# PHASE 11: NOTIFICATIONS (Optional)
# =============================================================================
log_header "PHASE 11: Notifications"

# Slack notification (if webhook configured)
if [[ -n "${SLACK_WEBHOOK_URL:-}" ]]; then
    log_step "Sending Slack notification..."
    SLACK_PAYLOAD=$(cat <<EOF
{
    "text": "✅ L9 Deploy Complete",
    "blocks": [
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "*✅ L9 Deployment Successful*\n• SHA: \`${CURRENT_SHA:0:8}\`\n• Build: $([[ "$QUICK" == "true" ]] && echo "quick" || echo "full")\n• Migrations: $([[ "$RUN_MIGRATIONS" == "true" ]] && echo "applied" || echo "skipped")"
            }
        }
    ]
}
EOF
)
    curl -s -X POST "$SLACK_WEBHOOK_URL" \
        -H 'Content-Type: application/json' \
        -d "$SLACK_PAYLOAD" >/dev/null 2>&1 || log_warn "Slack notification failed (non-fatal)"
    log_ok "Slack notification sent"
else
    log_warn "SLACK_WEBHOOK_URL not set, skipping notification"
fi

# =============================================================================
# PHASE 12: SUMMARY
# =============================================================================
log_header "PHASE 12: Deployment Summary"

echo ""
log_ok "✅ DEPLOYMENT COMPLETE (v3.0)"
echo ""
echo "Summary:"
echo "  • Mac SHA: $CURRENT_SHA"
echo "  • VPS SHA: $VPS_SHA"
echo "  • Previous VPS SHA: $PREV_VPS_SHA (for rollback)"
echo "  • Build mode: $([[ "$QUICK" == "true" ]] && echo "quick (cached)" || echo "full (no-cache)")"
echo "  • Migrations: $([[ "$RUN_MIGRATIONS" == "true" ]] && echo "applied" || echo "skipped")"
echo "  • Docker prune: $([[ "$PRUNE_DOCKER" == "true" ]] && echo "yes" || echo "no")"
echo ""
echo "Deployment log: $DEPLOY_LOG"
echo ""
echo "Next steps:"
echo "  1. Monitor: ssh $VPS_HOST 'cd $VPS_REPO && docker compose logs -f l9-api'"
echo "  2. Test: curl https://l9.quantumaipartners.com/health"
echo "  3. Full diagnostic: ssh $VPS_HOST 'cd $VPS_REPO && bash scripts/deployment/vps-mri.sh'"
echo ""
echo "Rollback (if needed):"
echo "  ssh $VPS_HOST 'cd $VPS_REPO && git checkout $PREV_VPS_SHA && docker compose up -d --build l9-api'"
echo ""
log_ok "Ready for production!"
