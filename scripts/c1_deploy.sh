#!/usr/bin/env bash
#
# c1_deploy.sh - Quick C1 Deploy (commit → push → pull → rebuild → MRI)
#
# Usage:
#   ./scripts/c1_deploy.sh                  # Full deploy (commit + rebuild)
#   ./scripts/c1_deploy.sh --no-cache       # Force full rebuild
#   ./scripts/c1_deploy.sh --pull-only      # Just pull, no rebuild
#   ./scripts/c1_deploy.sh --mri            # MRI diagnostics only (no deploy)
#   ./scripts/c1_deploy.sh -m "message"     # Custom commit message
#

set -euo pipefail

# ─────────────────────────────────────────────────────────────────────
# Configuration
# ─────────────────────────────────────────────────────────────────────
C1_IP="46.62.243.82"
SSH_KEY="$HOME/.ssh/Hetzner-C1-nopass"
C1_PATH="/opt/l9"
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# Options
NO_CACHE=""
PULL_ONLY=false
MRI_ONLY=false
COMMIT_MSG=""

# Parse args
while [[ $# -gt 0 ]]; do
    case $1 in
        --no-cache)     NO_CACHE="--no-cache"; shift ;;
        --pull-only)    PULL_ONLY=true; shift ;;
        --mri)          MRI_ONLY=true; shift ;;
        -m|--message)   COMMIT_MSG="$2"; shift 2 ;;
        -h|--help)
            echo "Usage: $0 [options]"
            echo ""
            echo "Options:"
            echo "  --no-cache      Force full container rebuild"
            echo "  --pull-only     Pull code only, skip rebuild"
            echo "  --mri           Run MRI diagnostics only"
            echo "  -m, --message   Custom commit message"
            exit 0
            ;;
        *) echo "Unknown option: $1"; exit 1 ;;
    esac
done

# SSH helper
c1() { ssh -o StrictHostKeyChecking=no -o ConnectTimeout=10 -i "$SSH_KEY" root@"$C1_IP" "$@"; }

cd "$REPO_ROOT"

echo "╔═══════════════════════════════════════════════════════════════╗"
echo "║  C1 Quick Deploy (46.62.243.82)                              ║"
echo "╚═══════════════════════════════════════════════════════════════╝"
echo ""

# ─────────────────────────────────────────────────────────────────────
# MRI ONLY MODE
# ─────────────────────────────────────────────────────────────────────
if $MRI_ONLY; then
    echo "┌─────────────────────────────────────────────────────────────────┐"
    echo "│ MRI DIAGNOSTICS                                                │"
    echo "└─────────────────────────────────────────────────────────────────┘"
    echo ""
    
    echo "[1/5] Container status..."
    c1 "cd $C1_PATH && docker compose -f docker-compose.yml -f docker-compose.prod.yml ps"
    echo ""
    
    echo "[2/5] Git status on C1..."
    c1 "cd $C1_PATH && git log -1 --oneline && git status -s | head -5"
    echo ""
    
    echo "[3/5] API health..."
    c1 "curl -sf http://127.0.0.1:8000/health 2>/dev/null | head -c 200 || echo 'API not responding'"
    echo ""
    
    echo "[4/5] Recent API logs..."
    c1 "cd $C1_PATH && docker compose -f docker-compose.yml -f docker-compose.prod.yml logs l9-api --tail=20" 2>/dev/null || true
    echo ""
    
    echo "[5/5] Bootstrap status..."
    c1 "cd $C1_PATH && docker compose -f docker-compose.yml -f docker-compose.prod.yml ps -a | grep -E 'bootstrap|NAME'"
    echo ""
    
    echo "✅ MRI complete"
    exit 0
fi

# ─────────────────────────────────────────────────────────────────────
# PHASE 1: LOCAL (Commit & Push)
# ─────────────────────────────────────────────────────────────────────
echo "┌─────────────────────────────────────────────────────────────────┐"
echo "│ PHASE 1: LOCAL (Commit & Push)                                 │"
echo "└─────────────────────────────────────────────────────────────────┘"
echo ""

echo "[1/4] Current state:"
echo "  Branch: $(git branch --show-current)"
echo "  Commit: $(git rev-parse --short HEAD)"
echo ""

# Show all pending changes (tracked + untracked)
echo "[2/4] Pending changes:"
MODIFIED=$(git status --porcelain | grep -E '^ ?M' | wc -l | tr -d ' ')
ADDED=$(git status --porcelain | grep -E '^\?\?' | wc -l | tr -d ' ')
DELETED=$(git status --porcelain | grep -E '^ ?D' | wc -l | tr -d ' ')
STAGED_ALREADY=$(git status --porcelain | grep -E '^[MADRC]' | wc -l | tr -d ' ')
echo "  Modified: $MODIFIED, New: $ADDED, Deleted: $DELETED, Already staged: $STAGED_ALREADY"
echo ""

# Stage ALL changes (tracked + untracked)
echo "[3/4] Staging all changes..."
git add -A

# Check what's now staged
STAGED=$(git diff --cached --name-only | wc -l | tr -d ' ')

if [ "$STAGED" -gt 0 ]; then
    echo "  Staged $STAGED file(s):"
    git diff --cached --name-only | head -15 | sed 's/^/    /'
    [ "$STAGED" -gt 15 ] && echo "    ... and $((STAGED - 15)) more"
    echo ""
    
    # Commit message
    if [ -z "$COMMIT_MSG" ]; then
        COMMIT_MSG="deploy: $(date '+%Y-%m-%d %H:%M') - $STAGED file(s)"
    fi
    
    echo "[4/4] Committing..."
    git commit -m "$COMMIT_MSG"
    echo "  ✅ Committed: $COMMIT_MSG"
else
    echo "  No new changes to commit (already up to date)"
fi
echo ""

# Push
echo "[3/3] Pushing to origin/main..."
git push origin main
echo "  ✅ Pushed"
echo ""

# ─────────────────────────────────────────────────────────────────────
# PHASE 2: C1 (Pull)
# ─────────────────────────────────────────────────────────────────────
echo "┌─────────────────────────────────────────────────────────────────┐"
echo "│ PHASE 2: C1 (Pull from GitHub)                                 │"
echo "└─────────────────────────────────────────────────────────────────┘"
echo ""

echo "[1/1] Pulling on C1..."
c1 "cd $C1_PATH && git fetch origin && git reset --hard origin/main"
C1_SHA=$(c1 "cd $C1_PATH && git rev-parse --short HEAD")
echo "  ✅ C1 now at: $C1_SHA"
echo ""

if $PULL_ONLY; then
    echo "✅ Pull complete (--pull-only, skipping rebuild)"
    exit 0
fi

# ─────────────────────────────────────────────────────────────────────
# PHASE 3: C1 (Rebuild & Restart)
# ─────────────────────────────────────────────────────────────────────
echo "┌─────────────────────────────────────────────────────────────────┐"
echo "│ PHASE 3: C1 (Rebuild & Restart)                                │"
echo "└─────────────────────────────────────────────────────────────────┘"
echo ""

COMPOSE="docker compose -f docker-compose.yml -f docker-compose.prod.yml"

echo "[1/3] Stopping containers..."
c1 "cd $C1_PATH && $COMPOSE down"
echo "  ✅ Stopped"
echo ""

echo "[2/3] Pruning build cache + all unused images..."
c1 "docker builder prune -f" 2>/dev/null || true
c1 "docker image prune -a -f" 2>/dev/null || true
echo "  ✅ Pruned"
echo ""

if [ -n "$NO_CACHE" ]; then
    echo "[3/4] Building images (--no-cache)..."
    c1 "cd $C1_PATH && $COMPOSE build --no-cache"
    echo "  ✅ Built"
    echo ""
    echo "[4/4] Starting containers..."
    c1 "cd $C1_PATH && $COMPOSE up -d"
else
    echo "[3/3] Building & starting (cached)..."
    c1 "cd $C1_PATH && $COMPOSE up -d --build"
fi
echo "  ✅ Started"
echo ""

# ─────────────────────────────────────────────────────────────────────
# PHASE 4: COMPREHENSIVE MRI (Medical Readiness Inspection)
# ─────────────────────────────────────────────────────────────────────
echo "┌─────────────────────────────────────────────────────────────────┐"
echo "│ PHASE 4: COMPREHENSIVE MRI                                     │"
echo "└─────────────────────────────────────────────────────────────────┘"
echo ""

echo "Waiting for services to initialize (15s)..."
sleep 15
echo ""

# Run comprehensive MRI on C1
c1 "cd $C1_PATH && bash -s" << 'MRI_SCRIPT'
COMPOSE="docker compose -f docker-compose.yml -f docker-compose.prod.yml"

# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 1: INFRASTRUCTURE BASELINE
# ═══════════════════════════════════════════════════════════════════════════════
echo "═══════════════════════════════════════════════════════════════"
echo "SECTION 1: INFRASTRUCTURE BASELINE"
echo "═══════════════════════════════════════════════════════════════"

echo -e "\n[1.1] SYSTEM RESOURCES"
free -h
echo ""
df -h / /var/lib/docker 2>/dev/null || df -h /
echo ""
uptime

echo -e "\n[1.2] GIT STATUS"
echo "Commit: $(git rev-parse --short HEAD 2>/dev/null || echo 'N/A')"
echo "Branch: $(git branch --show-current 2>/dev/null || echo 'N/A')"

# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 2: CONTAINER STATUS
# ═══════════════════════════════════════════════════════════════════════════════
echo -e "\n═══════════════════════════════════════════════════════════════"
echo "SECTION 2: CONTAINER STATUS"
echo "═══════════════════════════════════════════════════════════════"

echo -e "\n[2.1] ALL CONTAINERS"
$COMPOSE ps -a

echo -e "\n[2.2] CONTAINER DETAILS"
docker ps -a --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" | head -20

echo -e "\n[2.3] IMAGES IN USE"
docker images --format "table {{.Repository}}\t{{.Tag}}\t{{.Size}}\t{{.CreatedSince}}" | grep -E "l9|postgres|neo4j|redis|NAME"

# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 3: SERVICE HEALTH CHECKS
# ═══════════════════════════════════════════════════════════════════════════════
echo -e "\n═══════════════════════════════════════════════════════════════"
echo "SECTION 3: SERVICE HEALTH CHECKS"
echo "═══════════════════════════════════════════════════════════════"

echo -e "\n[3.1] L9 API HEALTH"
curl -sf http://127.0.0.1:8000/health 2>/dev/null && echo "" || echo "❌ API not responding"

echo -e "\n[3.2] POSTGRESQL HEALTH"
docker exec l9-postgres pg_isready -U postgres -d l9_memory 2>/dev/null && echo "✅ PostgreSQL ready" || echo "❌ PostgreSQL not ready"

echo -e "\n[3.3] NEO4J HEALTH"
curl -sf http://127.0.0.1:7474 2>/dev/null && echo "✅ Neo4j browser accessible" || echo "❌ Neo4j browser not responding"

echo -e "\n[3.4] REDIS HEALTH"
docker exec l9-redis redis-cli ping 2>/dev/null && echo "✅ Redis responding" || echo "❌ Redis not responding"

# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 4: NETWORK & PORTS
# ═══════════════════════════════════════════════════════════════════════════════
echo -e "\n═══════════════════════════════════════════════════════════════"
echo "SECTION 4: NETWORK & PORTS"
echo "═══════════════════════════════════════════════════════════════"

echo -e "\n[4.1] LISTENING PORTS"
ss -tlnp 2>/dev/null | grep -E "LISTEN|State" | head -20 || netstat -tlnp 2>/dev/null | head -20

# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 5: LOGS & ERRORS (last 5 min)
# ═══════════════════════════════════════════════════════════════════════════════
echo -e "\n═══════════════════════════════════════════════════════════════"
echo "SECTION 5: LOGS & ERRORS (last 5 min)"
echo "═══════════════════════════════════════════════════════════════"

echo -e "\n[5.1] L9 API ERRORS"
$COMPOSE logs l9-api --since 5m 2>/dev/null | grep -iE "error|exception|traceback|fatal|critical" | tail -15 || echo "(no recent errors)"

echo -e "\n[5.2] BOOTSTRAP STATUS"
$COMPOSE ps -a 2>/dev/null | grep -E "bootstrap|NAME"
$COMPOSE logs l9-bootstrap --tail=20 2>/dev/null | tail -10 || echo "(bootstrap logs N/A)"

# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 6: DATA PERSISTENCE
# ═══════════════════════════════════════════════════════════════════════════════
echo -e "\n═══════════════════════════════════════════════════════════════"
echo "SECTION 6: DATA PERSISTENCE (VOLUMES)"
echo "═══════════════════════════════════════════════════════════════"

echo -e "\n[6.1] DOCKER VOLUMES"
docker volume ls | grep -E "l9|NAME"

echo -e "\n[6.2] POSTGRESQL DATA"
docker exec l9-postgres psql -U postgres -d l9_memory -c "SELECT count(*) as packet_count FROM packets;" 2>/dev/null || echo "(query failed)"

# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 7: API ENDPOINT TESTS
# ═══════════════════════════════════════════════════════════════════════════════
echo -e "\n═══════════════════════════════════════════════════════════════"
echo "SECTION 7: API ENDPOINT TESTS"
echo "═══════════════════════════════════════════════════════════════"

echo -e "\n[7.1] CRITICAL ENDPOINTS"
for ep in "http://127.0.0.1:8000/health" "http://127.0.0.1:8000/docs" "http://127.0.0.1:8000/openapi.json"; do
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

echo -e "\n[8.1] REQUIRED ENV VARS"
for var in POSTGRES_PASSWORD NEO4J_PASSWORD OPENAI_API_KEY L9_API_KEY; do
    if grep -q "^${var}=" .env 2>/dev/null; then
        echo "✅ $var is set"
    else
        echo "❌ $var is MISSING"
    fi
done

# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 9: MRI SUMMARY
# ═══════════════════════════════════════════════════════════════════════════════
echo -e "\n═══════════════════════════════════════════════════════════════"
echo "SECTION 9: MRI SUMMARY"
echo "═══════════════════════════════════════════════════════════════"

echo -e "\nTimestamp: $(date '+%Y-%m-%d %H:%M:%S %Z')"
echo "Hostname: $(hostname)"
echo "Git commit: $(git rev-parse --short HEAD 2>/dev/null || echo 'N/A')"
echo ""

echo "SERVICE STATUS SUMMARY:"
echo "───────────────────────"
api_ok=$(curl -sf http://127.0.0.1:8000/health >/dev/null 2>&1 && echo "✅" || echo "❌")
pg_ok=$(docker exec l9-postgres pg_isready -U postgres >/dev/null 2>&1 && echo "✅" || echo "❌")
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
MRI_SCRIPT

# ─────────────────────────────────────────────────────────────────────
# FINAL STATUS
# ─────────────────────────────────────────────────────────────────────
echo ""
echo "┌─────────────────────────────────────────────────────────────────┐"
echo "│ FINAL STATUS                                                   │"
echo "└─────────────────────────────────────────────────────────────────┘"
echo ""

LOCAL_SHA=$(git rev-parse --short HEAD)
echo "  Local:  $LOCAL_SHA"
echo "  C1:     $C1_SHA"
echo ""

if [ "$LOCAL_SHA" = "$C1_SHA" ]; then
    echo "╔═══════════════════════════════════════════════════════════════╗"
    echo "║  ✅ DEPLOY SUCCESS - All systems in sync                     ║"
    echo "╚═══════════════════════════════════════════════════════════════╝"
else
    echo "╔═══════════════════════════════════════════════════════════════╗"
    echo "║  ⚠️  WARNING - Commits don't match                           ║"
    echo "╚═══════════════════════════════════════════════════════════════╝"
fi
