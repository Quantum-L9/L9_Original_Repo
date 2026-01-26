#!/usr/bin/env bash
#
# 10x_deploy.sh - L9 Master Deploy Script (10X Edition)
#
# THE master deploy script. Run from LOCAL machine. This script:
# 1. Commits all changes in L9
# 2. Pushes to GitHub
# 3. Verifies push succeeded
# 4. SSHs to VPS and runs pull_to_vps.sh
#
# PRINCIPLE: GitHub is SSOT. Local → GitHub → VPS
#

set -euo pipefail

# Configuration
VPS_HOST="${VPS_HOST:-157.180.73.53}"
VPS_USER="${VPS_USER:-admin}"
VPS_PATH="${VPS_PATH:-/opt/l9}"
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

cd "$REPO_ROOT"

echo "╔═══════════════════════════════════════════════════════════════╗"
echo "║  L9 Deploy (10X Edition) - Local → GitHub → VPS              ║"
echo "╚═══════════════════════════════════════════════════════════════╝"
echo ""

# ─────────────────────────────────────────────────────────────────────
# PHASE 1: LOCAL - Commit & Push
# ─────────────────────────────────────────────────────────────────────

echo "┌─────────────────────────────────────────────────────────────────┐"
echo "│ PHASE 1: LOCAL (Commit & Push to GitHub)                       │"
echo "└─────────────────────────────────────────────────────────────────┘"
echo ""

# Step 1: Show current state
echo "[1/4] Current local state:"
echo "  Branch: $(git branch --show-current)"
echo "  Commit: $(git rev-parse --short HEAD)"
CHANGES=$(git status --porcelain | wc -l | tr -d ' ')
echo "  Changes: $CHANGES file(s)"
echo ""

# Step 2: Stage and commit all changes
echo "[2/4] Staging all changes..."
git add -A
STAGED=$(git diff --cached --name-only | wc -l | tr -d ' ')

if [ "$STAGED" -eq 0 ]; then
    echo "  ℹ️  No changes to commit"
else
    echo "  Staged $STAGED file(s):"
    git diff --cached --name-only | head -10 | sed 's/^/    /'
    [ "$STAGED" -gt 10 ] && echo "    ... and $((STAGED - 10)) more"
    echo ""

    # Generate commit message with timestamp
    COMMIT_MSG="deploy: $(date '+%Y-%m-%d %H:%M') - $STAGED file(s)"

    echo "  Committing: $COMMIT_MSG"
    git commit -m "$COMMIT_MSG"
    echo "  ✅ Committed"
fi
echo ""

# Step 3: Push to GitHub
echo "[3/4] Pushing to GitHub..."
if git push origin main; then
    echo "  ✅ Pushed to origin/main"
else
    echo "  ❌ Push failed!"
    exit 1
fi
echo ""

# Step 4: Verify push
echo "[4/4] Verifying push..."
LOCAL_SHA=$(git rev-parse HEAD)
git fetch origin main --quiet
REMOTE_SHA=$(git rev-parse origin/main)

if [ "$LOCAL_SHA" = "$REMOTE_SHA" ]; then
    echo "  ✅ GitHub matches local: $LOCAL_SHA"
else
    echo "  ❌ Mismatch! Local: $LOCAL_SHA, Remote: $REMOTE_SHA"
    exit 1
fi
echo ""

# ─────────────────────────────────────────────────────────────────────
# PHASE 2: VPS - Pull & Deploy
# ─────────────────────────────────────────────────────────────────────

echo "┌─────────────────────────────────────────────────────────────────┐"
echo "│ PHASE 2: VPS (Pull from GitHub & Deploy)                       │"
echo "└─────────────────────────────────────────────────────────────────┘"
echo ""

echo "Connecting to $VPS_USER@$VPS_HOST..."
echo ""

# Run the VPS-side deploy script
ssh -t "$VPS_USER@$VPS_HOST" "cd $VPS_PATH && bash scripts/deployment/pull_to_vps.sh"

# ─────────────────────────────────────────────────────────────────────
# PHASE 3: Verification
# ─────────────────────────────────────────────────────────────────────

echo ""
echo "┌─────────────────────────────────────────────────────────────────┐"
echo "│ PHASE 3: Final Verification                                    │"
echo "└─────────────────────────────────────────────────────────────────┘"
echo ""

# Get VPS commit
VPS_SHA=$(ssh "$VPS_USER@$VPS_HOST" "cd $VPS_PATH && git rev-parse --short HEAD" 2>/dev/null || echo "unknown")

echo "  Local commit:  $(git rev-parse --short HEAD)"
echo "  GitHub commit: $(git rev-parse --short origin/main)"
echo "  VPS commit:    $VPS_SHA"
echo ""

if [ "$(git rev-parse --short HEAD)" = "$VPS_SHA" ]; then
    echo "╔═══════════════════════════════════════════════════════════════╗"
    echo "║  ✅ DEPLOY SUCCESS - All systems in sync                     ║"
    echo "╚═══════════════════════════════════════════════════════════════╝"
else
    echo "╔═══════════════════════════════════════════════════════════════╗"
    echo "║  ⚠️  WARNING - Commits don't match (check VPS logs)          ║"
    echo "╚═══════════════════════════════════════════════════════════════╝"
fi
