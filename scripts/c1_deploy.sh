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

echo "[1/3] Current state:"
echo "  Branch: $(git branch --show-current)"
echo "  Commit: $(git rev-parse --short HEAD)"
CHANGES=$(git status --porcelain | wc -l | tr -d ' ')
echo "  Changes: $CHANGES file(s)"
echo ""

# Stage and commit
git add -A
STAGED=$(git diff --cached --name-only | wc -l | tr -d ' ')

if [ "$STAGED" -gt 0 ]; then
    echo "[2/3] Staging $STAGED file(s):"
    git diff --cached --name-only | head -10 | sed 's/^/    /'
    [ "$STAGED" -gt 10 ] && echo "    ... and $((STAGED - 10)) more"
    echo ""
    
    # Commit message
    if [ -z "$COMMIT_MSG" ]; then
        COMMIT_MSG="deploy: $(date '+%Y-%m-%d %H:%M') - $STAGED file(s)"
    fi
    
    git commit -m "$COMMIT_MSG"
    echo "  ✅ Committed: $COMMIT_MSG"
else
    echo "[2/3] No changes to commit"
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

echo "[2/3] Pruning build cache..."
c1 "docker builder prune -f" 2>/dev/null || true
echo "  ✅ Pruned"
echo ""

echo "[3/3] Building & starting (${NO_CACHE:-cached})..."
c1 "cd $C1_PATH && $COMPOSE up -d --build $NO_CACHE"
echo "  ✅ Started"
echo ""

# ─────────────────────────────────────────────────────────────────────
# PHASE 4: MRI (Diagnostics)
# ─────────────────────────────────────────────────────────────────────
echo "┌─────────────────────────────────────────────────────────────────┐"
echo "│ PHASE 4: MRI (Post-Deploy Diagnostics)                         │"
echo "└─────────────────────────────────────────────────────────────────┘"
echo ""

echo "[1/3] Waiting for services (10s)..."
sleep 10
echo ""

echo "[2/3] Container status:"
c1 "cd $C1_PATH && $COMPOSE ps"
echo ""

echo "[3/3] Bootstrap logs (last 30 lines):"
c1 "cd $C1_PATH && $COMPOSE logs l9-bootstrap --tail=30" 2>/dev/null || echo "  (bootstrap container not found or exited)"
echo ""

# ─────────────────────────────────────────────────────────────────────
# FINAL STATUS
# ─────────────────────────────────────────────────────────────────────
echo "┌─────────────────────────────────────────────────────────────────┐"
echo "│ FINAL STATUS                                                   │"
echo "└─────────────────────────────────────────────────────────────────┘"
echo ""

LOCAL_SHA=$(git rev-parse --short HEAD)
echo "  Local:  $LOCAL_SHA"
echo "  C1:     $C1_SHA"
echo ""

# Quick health check
API_HEALTH=$(c1 "curl -sf http://127.0.0.1:8000/health 2>/dev/null | head -c 50" || echo "DOWN")
echo "  API Health: $API_HEALTH"
echo ""

if [ "$LOCAL_SHA" = "$C1_SHA" ]; then
    echo "╔═══════════════════════════════════════════════════════════════╗"
    echo "║  ✅ DEPLOY SUCCESS                                           ║"
    echo "╚═══════════════════════════════════════════════════════════════╝"
else
    echo "╔═══════════════════════════════════════════════════════════════╗"
    echo "║  ⚠️  WARNING - Commits don't match                           ║"
    echo "╚═══════════════════════════════════════════════════════════════╝"
fi
