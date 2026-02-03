#!/usr/bin/env bash
#
# push.sh - Local commit → push → VPS pull (no rebuild)
#
# Usage:
#   ./scripts/push.sh                     # Auto commit msg, push, pull on VPS
#   ./scripts/push.sh -m "msg"           # Custom commit message
#   ./scripts/push.sh --skip-verify      # Skip VPS pull + SHA check
#

set -euo pipefail

# ─────────────────────────────────────────────────────────────────────
# Configuration (aligned with c1_deploy.sh)
# ─────────────────────────────────────────────────────────────────────
C1_IP="46.62.243.82"
SSH_KEY="$HOME/.ssh/Hetzner-C1-nopass"
C1_PATH="/opt/l9"
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

VERIFY=true
COMMIT_MSG=""

# SSH helper
c1() {
  ssh -o StrictHostKeyChecking=no -o ConnectTimeout=10 -i "$SSH_KEY" root@"$C1_IP" "$@"
}

# ─────────────────────────────────────────────────────────────────────
# Parse args
# ─────────────────────────────────────────────────────────────────────
while [[ $# -gt 0 ]]; do
  case "$1" in
    -m|--message)
      COMMIT_MSG="$2"
      shift 2
      ;;
    --skip-verify)
      VERIFY=false
      shift
      ;;
    -h|--help)
      echo "Usage: $0 [options]"
      echo ""
      echo "Options:"
      echo "  -m, --message     Custom commit message"
      echo "  --skip-verify     Skip VPS pull + SHA verification"
      exit 0
      ;;
    *)
      echo "Unknown option: $1" >&2
      exit 1
      ;;
  esac
done

cd "$REPO_ROOT"

echo "╔═══════════════════════════════════════════════════════════════╗"
echo "║  PUSH: local → origin/main → C1                              ║"
echo "╚═══════════════════════════════════════════════════════════════╝"
echo ""

# ─────────────────────────────────────────────────────────────────────
# PHASE 1: LOCAL (Stage & Commit)
# ─────────────────────────────────────────────────────────────────────
echo "┌─────────────────────────────────────────────────────────────────┐"
echo "│ PHASE 1: LOCAL (Stage & Commit)                                │"
echo "└─────────────────────────────────────────────────────────────────┘"
echo ""

echo "[1/4] Current state:"
echo "  Branch: $(git branch --show-current)"
echo "  Commit: $(git rev-parse --short HEAD)"
echo ""

# Pending changes breakdown (tracked + untracked)
echo "[2/4] Pending changes:"
STATUS=$(git status --porcelain)

MODIFIED=$(printf "%s\n" "$STATUS" | grep -E '^ ?M'  | wc -l | tr -d ' ' || true)
ADDED=$(printf "%s\n" "$STATUS"   | grep -E '^\?\?'  | wc -l | tr -d ' ' || true)
DELETED=$(printf "%s\n" "$STATUS" | grep -E '^ ?D'  | wc -l | tr -d ' ' || true)
STAGED_ALREADY=$(printf "%s\n" "$STATUS" | grep -E '^[MADRC]' | wc -l | tr -d ' ' || true)

echo "  Modified:       $MODIFIED"
echo "  New (untracked): $ADDED"
echo "  Deleted:        $DELETED"
echo "  Already staged: $STAGED_ALREADY"
echo ""

# Stage ALL changes
echo "[3/4] Staging all changes (tracked + untracked)..."
git add -A

STAGED=$(git diff --cached --name-only | wc -l | tr -d ' ')

if [ "$STAGED" -gt 0 ]; then
  echo "  Staged $STAGED file(s):"
  git diff --cached --name-only | head -15 | sed 's/^/    /'
  if [ "$STAGED" -gt 15 ]; then
    echo "    ... and $((STAGED - 15)) more"
  fi
  echo ""

  # Commit message
  if [ -z "$COMMIT_MSG" ]; then
    COMMIT_MSG="push: $(date '+%Y-%m-%d %H:%M') - $STAGED file(s)"
  fi

  echo "[4/4] Committing..."
  git commit -m "$COMMIT_MSG"
  echo "  ✅ Committed: $COMMIT_MSG"
else
  echo "  No staged changes after git add -A (nothing to commit)"
fi

echo ""

# ─────────────────────────────────────────────────────────────────────
# PHASE 2: PUSH
# ─────────────────────────────────────────────────────────────────────
echo "┌─────────────────────────────────────────────────────────────────┐"
echo "│ PHASE 2: PUSH TO ORIGIN/MAIN                                   │"
echo "└─────────────────────────────────────────────────────────────────┘"
echo ""

echo "[1/1] Pushing to origin/main..."
git push origin main
echo "  ✅ Pushed"
echo ""

# ─────────────────────────────────────────────────────────────────────
# PHASE 3: VPS PULL + VERIFY (no rebuild)
# ─────────────────────────────────────────────────────────────────────
if ! $VERIFY; then
  echo "✅ Completed (local push only; --skip-verify set)"
  exit 0
fi

echo "┌─────────────────────────────────────────────────────────────────┐"
echo "│ PHASE 3: C1 (Pull & Verify)                                    │"
echo "└─────────────────────────────────────────────────────────────────┘"
echo ""

LOCAL_SHA=$(git rev-parse --short HEAD)
echo "[1/2] Pulling on C1..."
c1 "cd $C1_PATH && git fetch origin && git reset --hard origin/main" >/dev/null
C1_SHA=$(c1 "cd $C1_PATH && git rev-parse --short HEAD")

echo "  Local SHA: $LOCAL_SHA"
echo "  C1 SHA:    $C1_SHA"
echo ""

echo "[2/2] Verification result:"
if [ "$LOCAL_SHA" = "$C1_SHA" ]; then
  echo "  ✅ C1 is in sync with local main"
else
  echo "  ⚠️  WARNING: C1 is NOT in sync with local main"
fi
echo ""

echo "✅ push.sh complete (commit → push → C1 pull, no rebuild)"
