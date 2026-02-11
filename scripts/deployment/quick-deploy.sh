#!/usr/bin/env bash
set -e

VPS_HOST="admin@157.180.73.53"
VPS_PATH="/opt/l9"
LOCAL_REPO="/Users/ib-mac/Projects/L9"

echo "╔═══════════════════════════════════════════════════════════════╗"
echo "║ L9 QUICK DEPLOY (Code-Only, No Config Changes)               ║"
echo "╚═══════════════════════════════════════════════════════════════╝"
echo ""

# 1. Local git check
cd "$LOCAL_REPO"
echo "[LOCAL] Current branch: $(git branch --show-current)"
echo "[LOCAL] Last commit: $(git log -1 --oneline)"
echo ""

# 2. Push to GitHub
echo "[LOCAL] Pushing to GitHub..."
if ! git push origin main; then
  echo "❌ Git push failed. Commit your changes first."
  exit 1
fi
echo "✅ Pushed to GitHub"
echo ""

# 3. Pull on VPS + rebuild
echo "[VPS] Pulling latest code and rebuilding..."
ssh "$VPS_HOST" bash << 'REMOTE_SCRIPT'
set -e
cd /opt/l9

echo "  → Git pull"
git fetch origin
git reset --hard origin/main

echo "  → Rebuild app containers (l9-api, l9-mcp-memory)"
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build --force-recreate l9-api l9-mcp-memory

echo "  → Wait 10s for startup"
sleep 10

echo "  → Health check"
curl -sf http://127.0.0.1:8000/health | jq -r '"API: \(.status) | startup_ready: \(.startup_ready)"' || echo "❌ API not ready"

echo ""
echo "✅ Deploy complete"
REMOTE_SCRIPT

echo ""
echo "╔═══════════════════════════════════════════════════════════════╗"
echo "║  ✅ DONE - API restarted with latest code                     ║"
echo "╚═══════════════════════════════════════════════════════════════╝"
