#!/usr/bin/env bash
# L9 MCP Memory - Quick Activation (Docker-based)
# Usage: cd /opt/l9 && bash mcp_memory/deploy/scripts/init_mcp_memory.sh

set -euo pipefail

L9_DIR="/opt/l9"

echo "╔══════════════════════════════════════╗"
echo "║  L9 MCP Memory - Quick Activation   ║"
echo "╚══════════════════════════════════════╝"
echo ""

cd "$L9_DIR"

if [ ! -f ".env" ]; then
  echo "❌ .env not found at $L9_DIR/.env"
  exit 1
fi

echo "[1/3] Checking MCP env keys in .env..."

# Variables used by l9-api Docker container for MCP memory
REQUIRED_VARS=( "MCPAPIKEY" "MCPAPIKEYL" "MCPAPIKEYC" "MCPL9MEMORYKEY" "MCPHOST" "MCPPORT" "MCPENV" "MCPMEMORYENABLED" "MCPMEMORYURL" "MEMORYDSN" )

MISSING=()
for v in "${REQUIRED_VARS[@]}"; do
  if ! grep -q "^$v=" .env; then
    MISSING+=("$v")
  fi
done

if [ "${#MISSING[@]}" -ne 0 ]; then
  echo "❌ Missing MCP-related variables in .env:"
  for v in "${MISSING[@]}"; do
    echo "   - $v"
  done
  echo ""
  echo "Edit $L9_DIR/.env and add the missing variables."
  echo "Then re-run: bash mcp_memory/deploy/scripts/init_mcp_memory.sh"
  exit 1
fi

echo "✅ MCP env variables present in .env"
echo ""

echo "[2/3] Ensuring MCP memory is enabled and restarting l9-api..."

# Force MCPMEMORYENABLED=true via sed (idempotent)
sudo sed -i 's/^MCPMEMORYENABLED=.*/MCPMEMORYENABLED=true/' .env || true
if ! grep -q "^MCPMEMORYENABLED=" .env; then
  echo "MCPMEMORYENABLED=true" | sudo tee -a .env >/dev/null
fi

# Restart l9-api to pick up env changes
docker compose restart l9-api

echo "✅ MCPMEMORYENABLED set to true, l9-api restarted"
echo ""

echo "[3/3] Verifying MCP memory health..."

# Wait a moment for container to start
sleep 2

# Local API health
echo "Local API health:"
curl -s "http://127.0.0.1:8000/health" | jq . || echo "⚠️  Local API not responding"

echo ""
echo "HTTPS health (via Caddy on 9001 → l9-api):"
curl -sk "https://157.180.73.53:9001/health" | jq . || echo "⚠️  HTTPS endpoint not responding"

echo ""
echo "✅ MCP memory activation complete"
echo ""
echo "If both health checks show status:\"ok\" and service:\"l9-api\", MCP memory is active."
echo "Cursor should point MCPSERVERURL to your MCP memory route and use MCPAPIKEYC from .env as the Bearer token."
