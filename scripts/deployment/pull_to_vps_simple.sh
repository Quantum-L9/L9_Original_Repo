#!/usr/bin/env bash
#
# L9 VPS Deploy Script (10X Edition)
#
# PRINCIPLE: GitHub is SSOT. VPS must match GitHub exactly.
# NO stashing, NO local changes preserved, NO merge conflicts.
#
# This script:
# 1. Show current VPS state
# 2. Fetch latest from GitHub
# 3. Hard reset to origin/main (SSOT)
# 4. Sync env variables (.env.example → .env)
# 5. Rebuild Docker containers
# 6. Prune unused Docker resources
# 7. Health checks
#

set -euo pipefail

cd /opt/l9

echo "╔═══════════════════════════════════════════════════════════════╗"
echo "║  L9 VPS Deploy (10X Edition) - GitHub SSOT                    ║"
echo "╚═══════════════════════════════════════════════════════════════╝"
echo ""

# Step 1: Show current state
echo "[1/7] Current VPS state:"
echo "  Commit: $(git rev-parse --short HEAD)"
echo "  Branch: $(git branch --show-current)"
echo ""

# Step 2: Fetch latest from GitHub
echo "[2/7] Fetching from GitHub..."
git fetch origin main
BEHIND=$(git rev-list HEAD..origin/main --count)
echo "  VPS is $BEHIND commit(s) behind origin/main"
echo ""

# Step 3: Hard reset to match GitHub EXACTLY
echo "[3/7] Hard reset to origin/main (SSOT)..."
git reset --hard origin/main
echo "  ✅ VPS now matches GitHub exactly"
echo "  New commit: $(git rev-parse --short HEAD)"
echo ""

# Step 4: Sync environment variables (.env.example → .env)
echo "[4/7] Syncing environment variables..."
if [ -f .env.example ]; then
    # Add any NEW variables from .env.example to .env (preserves existing values)
    while IFS='=' read -r key value; do
        # Skip comments and empty lines
        [[ "$key" =~ ^#.*$ || -z "$key" ]] && continue
        # If key doesn't exist in .env, add it
        if ! grep -q "^${key}=" .env 2>/dev/null; then
            echo "${key}=${value}" >> .env
            echo "  + Added: $key"
        fi
    done < .env.example
    echo "  ✅ Environment variables synced"
else
    echo "  ⚠️  No .env.example found"
fi
echo ""

# Step 5: Rebuild and restart Docker containers
echo "[5/7] Rebuilding ALL Docker containers..."
docker compose build --no-cache
docker compose up -d --force-recreate
echo "  ✅ All containers rebuilt and restarted"
echo ""

# Step 6: Prune unused Docker resources (keeps disk lean)
echo "[6/7] Pruning unused Docker resources..."
docker system prune -a -f
DISK_FREE=$(df -h / | tail -1 | awk '{print $4}')
echo "  ✅ Docker pruned. Disk free: $DISK_FREE"
echo ""

# Step 7: Health checks
echo "[7/7] Health checks (waiting 15s for startup)..."
sleep 15

echo ""
echo "Container status:"
docker ps --format "table {{.Names}}\t{{.Status}}" | grep l9- || echo "  ⚠️  No L9 containers running"

echo ""
echo "API Health:"
curl -sf http://127.0.0.1:8000/health | jq -c . 2>/dev/null || echo "  ⚠️  API not responding"

echo ""
echo "MCP Memory Health:"
curl -sf http://127.0.0.1:9002/health | jq -c . 2>/dev/null || echo "  ⚠️  MCP not responding"

echo ""
echo "╔═══════════════════════════════════════════════════════════════╗"
echo "║  Deploy Complete                                              ║"
echo "╚═══════════════════════════════════════════════════════════════╝"
echo ""
echo "VPS commit: $(git rev-parse --short HEAD)"
echo "Disk free:  $DISK_FREE"
echo ""
echo "View logs:  docker compose logs -f l9-api"
