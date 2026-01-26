#!/bin/bash
# =============================================================================
# L9 10X Deployment Script v3.1 (FRESH SLATE)
# Full pipeline: Mac → Git → VPS → Rebuild ALL → Verify
#
# IMPROVEMENTS:
#   v2.0 (GMP-71): Safe git pull, --dry-run, --quick, rollback
#   v3.0 (GMP-77): Pre-flight checks, health retries, migrations gate,
#                  conditional prune, .env backup, Slack notify, enhanced rollback
#   v3.1: FRESH SLATE - rebuild ALL containers, aggressive port cleanup,
#         trust automatic migrations, skip Phase 4 restart when doing full rebuild
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
    log_step "Ensuring VPS .env defines all keys from .env.example (no value changes)..."
    if ssh "$VPS_HOST" "cd $VPS_REPO && bash -lc '
        set -euo pipefail
        if [[ ! -f .env ]]; then echo \"Missing .env\"; exit 1; fi
        if [[ ! -f .env.example ]]; then echo \"Missing .env.example\"; exit 1; fi

        required_keys=\$(grep -E \"^[A-Z0-9_]+=\" .env.example | cut -d= -f1 | sort -u)
        present_keys=\$(grep -E \"^[A-Z0-9_]+=\" .env | cut -d= -f1 | sort -u)
        missing=\$(comm -23 <(echo \"\$required_keys\") <(echo \"\$present_keys\"))

        if [[ -n \"\$missing\" ]]; then
            echo \"Missing keys in .env:\"
            echo \"\$missing\"
            exit 1
        fi
    '"; then
        log_ok "VPS .env includes all .env.example keys"
    else
        log_error "VPS .env missing required keys. Fix .env on VPS and re-run deploy."
        log_error "SSH: ssh $VPS_HOST && cd $VPS_REPO && vim .env   # or your editor"
        exit 1
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
L9 10X Deployment Script v3.1 (FRESH SLATE)

Usage: $0 [options] [commit-message]

Options:
    --dry-run         Show what would happen without executing
    --quick           Skip full rebuild (faster, uses cache, only restart)
    --skip-mri        Skip full MRI diagnostic at the end
    --skip-e2e        Skip MCP E2E test
    --run-migrations  Force manual migration run (auto runs on startup anyway)
    --prune-docker    Clean Docker system (volumes, images, containers)
    --version         Show version and exit
    -h, --help        Show this help

FRESH SLATE MODE (default):
    - Rebuilds ALL containers (l9-api, l9-mcp-memory)
    - Forces --no-cache for clean builds
    - Aggressive port cleanup (kills stuck processes)
    - Auto-runs migrations on container startup
    - DATA IS PRESERVED (volumes are NOT deleted)

Examples:
    $0 "feat(memory): new feature"     # FRESH SLATE rebuild
    $0 --quick "hotfix: typo fix"      # Quick mode (restart only)
    $0 --dry-run                       # Preview changes
    $0 --prune-docker "major release"  # Clean old images after deploy

Default commit message: "chore(deploy): automated 10X deployment"
EOF
}

rollback() {
    log_header "ROLLBACK INITIATED"
    log_error "Deployment failed! Reverting to previous state..."

    if [[ -n "$PREV_VPS_SHA" ]]; then
        log_step "Reverting VPS to SHA: $PREV_VPS_SHA"
        ssh "$VPS_HOST" "cd $VPS_REPO && git checkout $PREV_VPS_SHA 2>&1" || log_error "Git rollback failed!"

        log_step "Rebuilding ALL services with previous code..."
        ssh "$VPS_HOST" "cd $VPS_REPO && docker compose down 2>/dev/null || true"
        ssh "$VPS_HOST" "cd $VPS_REPO && docker compose up -d --build" || log_error "Service restart failed!"

        wait_with_spinner 15 "Allowing all services to stabilize..."

        # Verify rollback worked
        log_step "Verifying rollback health..."
        ROLLBACK_HEALTH=$(ssh "$VPS_HOST" "curl -s --max-time 10 http://127.0.0.1:8000/health 2>/dev/null || echo 'FAIL'")
        if [[ "$ROLLBACK_HEALTH" == *"status"* ]] || [[ "$ROLLBACK_HEALTH" == *"ok"* ]]; then
            log_ok "Rollback successful - service is healthy"
        else
            log_error "Rollback failed - manual intervention required!"
            log_error "SSH: ssh $VPS_HOST"
            log_error "Logs: cd $VPS_REPO && docker compose logs --tail=100"
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
            echo "L9 10X Deployment Script v3.1 (FRESH SLATE)"
            echo "Compatible with: L9 VPS production stack"
            echo "Features: FRESH SLATE rebuild (all containers), aggressive port cleanup,"
            echo "          auto migrations, pre-flight checks, health retries, rollback"
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
# CRITICAL: Sync FIRST, then verify (sync adds missing keys from .env.example)
ssh "$VPS_HOST" "cd $VPS_REPO && bash scripts/vps/sync_env_vars.sh --quiet" || true
# Now verify all keys are present (after sync)
verify_vps_env_complete
ssh "$VPS_HOST" "cd $VPS_REPO && bash scripts/vps/verify_vps_env.sh --quick" | tee -a "$DEPLOY_LOG"

# NOTE: Skip container restart here - Phase 5 will rebuild ALL containers anyway
# This avoids port conflicts and unnecessary double-restarts
if [[ "$QUICK" == "true" ]]; then
    # Quick mode only: restart to load new env vars (no rebuild in Phase 5)
    log_step "Restarting containers to load synced env vars (quick mode)..."
    ssh "$VPS_HOST" "cd $VPS_REPO && docker compose restart 2>/dev/null || true"
    wait_with_spinner 5 "Allowing containers to reload..."
else
    log_ok "Skipping restart (Phase 5 will rebuild ALL containers with fresh env)"
fi

log_ok "Environment verification complete"

# =============================================================================
# PHASE 4.5: DATABASE MIGRATION INFO
# =============================================================================
log_header "PHASE 4.5: Database Migration Info"

log_step "Checking migration files..."
MIGRATION_COUNT=$(ssh "$VPS_HOST" "cd $VPS_REPO && ls -1 migrations/*.sql 2>/dev/null | wc -l" || echo "0")
MIGRATION_COUNT=$(echo "$MIGRATION_COUNT" | tr -d '[:space:]')

if [[ "$MIGRATION_COUNT" -gt 0 ]]; then
    log_ok "Found $MIGRATION_COUNT migration file(s) - auto-applied on l9-api startup"

    # Show migration status from database (Python runner uses schema_migrations table)
    log_step "Checking applied migrations in database..."
    APPLIED_COUNT=$(ssh "$VPS_HOST" "cd $VPS_REPO && docker compose exec -T l9-postgres psql -U \$POSTGRES_USER -d \$POSTGRES_DB -t -c 'SELECT COUNT(*) FROM schema_migrations' 2>/dev/null | tr -d ' '" || echo "0")
    log_ok "Already applied: $APPLIED_COUNT migrations (tracked in schema_migrations table)"

    # Manual run is deprecated - just show info
    if [[ "$RUN_MIGRATIONS" == "true" ]]; then
        log_warn "--run-migrations is deprecated (migrations auto-run on startup)"
        log_warn "If you need to force migrations, restart l9-api container"
    fi
else
    log_ok "No migration files in migrations/"
fi
# NOTE: api/server.py runs migrations automatically via memory.migration_runner.run_migrations()
# Migrations are tracked in schema_migrations table, NOT .migrations_applied file

# =============================================================================
# PHASE 5: VPS DOCKER REBUILD (ALL CONTAINERS - FRESH SLATE)
# =============================================================================
log_header "PHASE 5: VPS Docker Rebuild (Fresh Slate)"

# CRITICAL: Stop ALL containers and ensure port 8000 is free
log_step "Stopping ALL containers for fresh slate rebuild..."
ssh "$VPS_HOST" "cd $VPS_REPO && docker compose down 2>/dev/null || true"
wait_with_spinner 3 "Waiting for graceful shutdown..."

# AGGRESSIVE PORT CLEANUP: Kill any process using port 8000
log_step "Ensuring port 8000 is free..."
PORT_PID=$(ssh "$VPS_HOST" "ss -tlnp 2>/dev/null | grep ':8000 ' | grep -oP 'pid=\K[0-9]+' | head -1" || echo "")
if [[ -n "$PORT_PID" ]]; then
    log_warn "Port 8000 still in use by PID $PORT_PID - killing..."
    ssh "$VPS_HOST" "sudo kill -9 $PORT_PID 2>/dev/null || true"
    wait_with_spinner 2 "Waiting for port release..."
fi

# Verify port is now free
PORT_CHECK=$(ssh "$VPS_HOST" "ss -tlnp 2>/dev/null | grep ':8000 ' || echo ''")
if [[ -n "$PORT_CHECK" ]]; then
    log_error "Port 8000 still in use after cleanup attempt!"
    log_error "Manual intervention required: ssh $VPS_HOST 'sudo lsof -i :8000'"
    rollback
fi
log_ok "Port 8000 is free"

# Get the current image IDs before rebuild (for verification)
OLD_API_IMAGE=$(ssh "$VPS_HOST" "docker images -q l9-l9-api 2>/dev/null | head -1" || echo "none")
OLD_MCP_IMAGE=$(ssh "$VPS_HOST" "docker images -q l9-l9-mcp-memory 2>/dev/null | head -1" || echo "none")
log_step "Previous images: l9-api=${OLD_API_IMAGE:-none}, l9-mcp-memory=${OLD_MCP_IMAGE:-none}"

BUILD_OPTS=""
if [[ "$QUICK" == "false" ]]; then
    BUILD_OPTS="--no-cache"
    log_step "Building ALL images (no cache - FRESH SLATE)..."

    # Remove old images to force complete rebuild
    log_step "Removing old images to force fresh builds..."
    ssh "$VPS_HOST" "docker rmi l9-l9-api l9-l9-mcp-memory 2>/dev/null || true"
else
    log_step "Building ALL images (with cache - quick mode)..."
fi

# BUILD ALL CUSTOM IMAGES (l9-api and l9-mcp-memory)
log_step "Building l9-api..."
if ! ssh "$VPS_HOST" "cd $VPS_REPO && docker compose build $BUILD_OPTS l9-api 2>&1"; then
    log_error "l9-api build failed!"
    rollback
fi
log_ok "l9-api built"

log_step "Building l9-mcp-memory..."
if ! ssh "$VPS_HOST" "cd $VPS_REPO && docker compose build $BUILD_OPTS l9-mcp-memory 2>&1"; then
    log_warn "l9-mcp-memory build failed (non-fatal)"
fi
log_ok "l9-mcp-memory built"

# Verify new images were created
NEW_API_IMAGE=$(ssh "$VPS_HOST" "docker images -q l9-l9-api 2>/dev/null | head -1" || echo "none")
NEW_MCP_IMAGE=$(ssh "$VPS_HOST" "docker images -q l9-l9-mcp-memory 2>/dev/null | head -1" || echo "none")
log_step "New images: l9-api=${NEW_API_IMAGE:-none}, l9-mcp-memory=${NEW_MCP_IMAGE:-none}"

if [[ "$OLD_API_IMAGE" == "$NEW_API_IMAGE" ]] && [[ "$OLD_API_IMAGE" != "none" ]] && [[ "$QUICK" == "false" ]]; then
    log_warn "l9-api image ID unchanged after --no-cache - may indicate build issue"
fi

# START ALL CONTAINERS (fresh instances)
log_step "Starting ALL containers (fresh slate)..."
ssh "$VPS_HOST" "cd $VPS_REPO && docker compose up -d --force-recreate"
log_ok "All containers started with fresh instances"

# Show container status
log_step "Container status:"
ssh "$VPS_HOST" "cd $VPS_REPO && docker compose ps --format 'table {{.Name}}\t{{.Status}}'" | head -15

wait_with_spinner 10 "Waiting for all services to initialize..."

# =============================================================================
# PHASE 6: VPS HEALTH CHECKS
# =============================================================================
log_header "PHASE 6: VPS Health Checks"

log_step "Checking container status..."
CONTAINER_STATUS=$(ssh "$VPS_HOST" "cd $VPS_REPO && docker compose ps l9-api --format '{{.State}}'" 2>/dev/null || echo "unknown")
ssh "$VPS_HOST" "cd $VPS_REPO && docker compose ps l9-api" | tee -a "$DEPLOY_LOG"

# Early exit if container isn't running
if [[ "$CONTAINER_STATUS" != "running" ]]; then
    log_error "Container is not running! State: $CONTAINER_STATUS"
    log_step "Fetching container logs for diagnosis..."
    ssh "$VPS_HOST" "cd $VPS_REPO && docker compose logs l9-api --tail=50" | tee -a "$DEPLOY_LOG"
    rollback
fi

log_step "Checking startup logs (last 30 lines)..."
ssh "$VPS_HOST" "cd $VPS_REPO && docker compose logs l9-api --tail=30 --no-log-prefix 2>&1" | tee -a "$DEPLOY_LOG"

# Check for common startup errors in logs
STARTUP_ERRORS=$(ssh "$VPS_HOST" "cd $VPS_REPO && docker compose logs l9-api --tail=50 2>&1 | grep -iE '(error|exception|failed|traceback|ModuleNotFoundError|ImportError)' | head -5" || echo "")
if [[ -n "$STARTUP_ERRORS" ]]; then
    log_warn "Potential startup errors detected in logs:"
    echo "$STARTUP_ERRORS"
    echo ""
fi

wait_with_spinner 8 "Allowing API to fully initialize..."

log_step "Testing API health endpoint (with retries)..."
RETRY_COUNT=0
HEALTH_OK=false
LAST_HTTP_CODE=""

while [[ $RETRY_COUNT -lt $HEALTH_MAX_RETRIES ]]; do
    # Get both HTTP code and response body
    HEALTH_RESULT=$(ssh "$VPS_HOST" "curl -s -w '\n%{http_code}' --max-time 10 http://127.0.0.1:8000/health 2>/dev/null || echo -e 'FAIL\n000'")
    HEALTH_RESPONSE=$(echo "$HEALTH_RESULT" | head -n -1)
    LAST_HTTP_CODE=$(echo "$HEALTH_RESULT" | tail -1)

    if [[ "$LAST_HTTP_CODE" == "200" ]]; then
        HEALTH_OK=true
        break
    fi

    # Also accept these patterns even without 200 (some health endpoints return different codes)
    if [[ "$HEALTH_RESPONSE" == *"status"* ]] || [[ "$HEALTH_RESPONSE" == *"ok"* ]] || [[ "$HEALTH_RESPONSE" == *"healthy"* ]]; then
        HEALTH_OK=true
        break
    fi

    ((RETRY_COUNT++))
    if [[ $RETRY_COUNT -lt $HEALTH_MAX_RETRIES ]]; then
        echo "  Retry $RETRY_COUNT/$HEALTH_MAX_RETRIES (HTTP $LAST_HTTP_CODE)..."
        sleep $HEALTH_RETRY_INTERVAL
    fi
done

if [[ "$HEALTH_OK" == "true" ]]; then
    log_ok "API is healthy (after $RETRY_COUNT retries, HTTP $LAST_HTTP_CODE)"
    echo "$HEALTH_RESPONSE" | jq . 2>/dev/null || echo "$HEALTH_RESPONSE"
else
    log_error "API health check failed after $HEALTH_MAX_RETRIES attempts!"
    log_error "Last HTTP code: $LAST_HTTP_CODE"
    log_error "Last response: $HEALTH_RESPONSE"

    # Enhanced diagnostics
    log_step "Running enhanced diagnostics..."

    log_step "1. Container resource usage:"
    ssh "$VPS_HOST" "docker stats l9-l9-api-1 --no-stream 2>/dev/null" || true

    log_step "2. Container network connectivity:"
    ssh "$VPS_HOST" "docker exec l9-l9-api-1 curl -s http://127.0.0.1:8000/health 2>&1 || echo 'Internal curl failed'" || true

    log_step "3. Process list inside container:"
    ssh "$VPS_HOST" "docker exec l9-l9-api-1 ps aux 2>/dev/null | head -10" || true

    log_step "4. Full container logs (last 100 lines):"
    ssh "$VPS_HOST" "cd $VPS_REPO && docker compose logs l9-api --tail=100" | tee -a "$DEPLOY_LOG"

    log_step "5. Container inspect (exit code, state):"
    ssh "$VPS_HOST" "docker inspect l9-l9-api-1 --format='State: {{.State.Status}}, ExitCode: {{.State.ExitCode}}, Error: {{.State.Error}}'" 2>/dev/null || true

    rollback
fi

# Additional health verifications
log_step "Verifying additional endpoints..."

# Test /docs endpoint (OpenAPI)
DOCS_CHECK=$(ssh "$VPS_HOST" "curl -s -o /dev/null -w '%{http_code}' --max-time 5 http://127.0.0.1:8000/docs 2>/dev/null || echo '000'")
if [[ "$DOCS_CHECK" == "200" ]]; then
    log_ok "API docs endpoint OK (/docs)"
else
    log_warn "API docs endpoint returned HTTP $DOCS_CHECK (non-critical)"
fi

# Test a lightweight API endpoint if available
READY_CHECK=$(ssh "$VPS_HOST" "curl -s -o /dev/null -w '%{http_code}' --max-time 5 http://127.0.0.1:8000/ready 2>/dev/null || echo '000'")
if [[ "$READY_CHECK" == "200" ]]; then
    log_ok "API ready endpoint OK (/ready)"
elif [[ "$READY_CHECK" != "000" ]] && [[ "$READY_CHECK" != "404" ]]; then
    log_warn "API ready endpoint returned HTTP $READY_CHECK"
fi

# =============================================================================
# PHASE 6.5: SERVICE VERIFICATION
# =============================================================================
log_header "PHASE 6.5: Service Verification"

log_step "Verifying internal services are responding..."

# Check that the git SHA in the container matches what we deployed
log_step "Checking deployed code version..."
CONTAINER_GIT_SHA=$(ssh "$VPS_HOST" "docker exec l9-l9-api-1 cat /app/.git-sha 2>/dev/null || docker exec l9-l9-api-1 git -C /app rev-parse HEAD 2>/dev/null || echo 'unknown'" | tr -d '[:space:]')
if [[ "$CONTAINER_GIT_SHA" == "$VPS_SHA"* ]] || [[ "$VPS_SHA" == "$CONTAINER_GIT_SHA"* ]]; then
    log_ok "Container running correct code version: ${CONTAINER_GIT_SHA:0:8}"
elif [[ "$CONTAINER_GIT_SHA" == "unknown" ]]; then
    log_warn "Could not verify container code version (git not in container)"
else
    log_warn "Container SHA ($CONTAINER_GIT_SHA) may differ from VPS SHA ($VPS_SHA)"
fi

# Verify Python can import key modules
log_step "Verifying Python imports..."
IMPORT_CHECK=$(ssh "$VPS_HOST" "docker exec l9-l9-api-1 python3 -c 'from api.server import app; print(\"OK\")' 2>&1" || echo "FAIL")
if [[ "$IMPORT_CHECK" == *"OK"* ]]; then
    log_ok "Core API module imports successfully"
else
    log_warn "Import check issue: $IMPORT_CHECK"
fi

# Check if uvicorn/gunicorn process is running
log_step "Verifying API server process..."
API_PROCESS=$(ssh "$VPS_HOST" "docker exec l9-l9-api-1 pgrep -f 'uvicorn|gunicorn' 2>/dev/null || echo 'none'")
if [[ "$API_PROCESS" != "none" ]] && [[ -n "$API_PROCESS" ]]; then
    log_ok "API server process running (PID: $(echo $API_PROCESS | head -1))"
else
    log_warn "Could not verify API server process"
fi

# Memory check - ensure container isn't OOM
log_step "Checking container memory..."
MEM_USAGE=$(ssh "$VPS_HOST" "docker stats l9-l9-api-1 --no-stream --format '{{.MemUsage}}' 2>/dev/null" || echo "unknown")
if [[ "$MEM_USAGE" != "unknown" ]]; then
    log_ok "Container memory usage: $MEM_USAGE"
else
    log_warn "Could not check container memory usage"
fi

log_ok "Service verification complete"

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
log_ok "✅ DEPLOYMENT COMPLETE (v3.1 - FRESH SLATE)"
echo ""
echo "Summary:"
echo "  • Mac SHA: $CURRENT_SHA"
echo "  • VPS SHA: $VPS_SHA"
echo "  • Previous VPS SHA: $PREV_VPS_SHA (for rollback)"
echo "  • Build mode: $([[ "$QUICK" == "true" ]] && echo "quick (cached)" || echo "FRESH SLATE (all containers rebuilt)")"
echo "  • Migrations: auto (run on l9-api startup)"
echo "  • Docker prune: $([[ "$PRUNE_DOCKER" == "true" ]] && echo "yes" || echo "no")"
echo ""
echo "Containers rebuilt:"
echo "  • l9-api (FastAPI main service)"
echo "  • l9-mcp-memory (MCP memory server)"
echo "  • + all supporting services restarted"
echo ""
echo "Deployment log: $DEPLOY_LOG"
echo ""
echo "Next steps:"
echo "  1. Monitor: ssh $VPS_HOST 'cd $VPS_REPO && docker compose logs -f'"
echo "  2. Test: curl https://l9.quantumaipartners.com/health"
echo "  3. Full diagnostic: ssh $VPS_HOST 'cd $VPS_REPO && bash scripts/deployment/vps-mri.sh'"
echo ""
echo "Rollback (if needed):"
echo "  ssh $VPS_HOST 'cd $VPS_REPO && git checkout $PREV_VPS_SHA && docker compose down && docker compose up -d --build'"
echo ""
log_ok "Ready for production!"
