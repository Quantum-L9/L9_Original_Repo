#!/usr/bin/env bash
# L9 MCP Memory - Activation Helper
# Usage: cd /opt/l9 && bash mcp_memory_activate.sh

set -euo pipefail

L9_DIR="/opt/l9"

echo "╔══════════════════════════════════════╗"
echo "║  L9 MCP Memory - Activation Helper   ║"
echo "╚══════════════════════════════════════╝"
echo ""

cd "$L9_DIR"

if [ ! -f ".env" ]; then
  echo "❌ .env not found at $L9_DIR/.env"
  exit 1
fi

echo "[1/4] Checking MCP env keys in .env..."

# These are the keys used by the MCP memory server (from mcp_memory/src/config.py)
# Primary keys (required):
# - MCP_API_KEY_L: L-CTO kernel (full read/write/delete)
# - MCP_API_KEY_C: Cursor IDE (read all, write/delete own only)
# Legacy fallbacks (optional but checked):
# - MCP_API_KEY: Shared fallback
# - MCPL9MEMORYKEY: Legacy alias
# - MCP_API_KEYL: Legacy alias for MCP_API_KEY_L
# - MCP_API_KEYC: Legacy alias for MCP_API_KEY_C
# Server config (with defaults, but checked):
# - MCP_HOST (default: 127.0.0.1)
# - MCP_PORT (default: 9002)
# - MCP_ENV (default: production)
# Required:
# - OPENAI_API_KEY: For embeddings
# - MEMORY_DSN: PostgreSQL connection string
REQUIRED_VARS=( "MCP_API_KEY_L" "MCP_API_KEY_C" "OPENAI_API_KEY" "MEMORY_DSN" )
OPTIONAL_VARS=( "MCP_API_KEY" "MCPL9MEMORYKEY" "MCP_API_KEYL" "MCP_API_KEYC" "MCP_HOST" "MCP_PORT" "MCP_ENV" )

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
  echo "Then re-run: bash mcp_memory_activate.sh"
  exit 1
fi

echo "✅ MCP env variables present in .env"
echo ""

echo "[2/4] Checking MCP memory server dependencies..."

# Check if virtual environment exists
if [ ! -d "venv" ]; then
  echo "⚠️  Virtual environment not found - MCP server may need dependencies"
  echo "   Run: python3.11 -m venv venv && source venv/bin/activate && pip install -r mcp_memory/requirements.txt"
else
  echo "✅ Virtual environment found"
fi
echo ""

echo "[3/4] Checking MCP memory server status..."

# Check if systemd service exists
if systemctl list-unit-files | grep -q "l9-mcp.service"; then
  if systemctl is-active --quiet l9-mcp; then
    echo "✅ MCP memory server (l9-mcp) is running"
  else
    echo "⚠️  MCP memory server (l9-mcp) service exists but not running"
    echo "   Start with: sudo systemctl start l9-mcp"
    echo "   Check logs: sudo journalctl -u l9-mcp -n 50"
  fi
else
  echo "⚠️  MCP memory server systemd service not installed"
  echo "   Install with: sudo cp mcp_memory/deploy/systemd/l9-mcp.service /etc/systemd/system/"
  echo "   Then: sudo systemctl daemon-reload && sudo systemctl enable l9-mcp && sudo systemctl start l9-mcp"
fi

echo ""
echo "[4/4] Testing MCP memory endpoints..."

# Test local MCP server (if running)
if systemctl is-active --quiet l9-mcp 2>/dev/null; then
  source .env
  echo "Testing MCP tools endpoint..."
  curl -s -H "Authorization: Bearer ${MCP_API_KEY_C}" \
    "http://127.0.0.1:9002/mcp/tools" | jq . || echo "⚠️  MCP server not responding on port 9002"
else
  echo "⚠️  MCP server not running - skipping endpoint test"
fi

echo ""
echo "✅ MCP memory activation check complete"
echo ""
echo "Next steps:"
echo "  1. Ensure l9-mcp service is running: sudo systemctl status l9-mcp"
echo "  2. Configure Caddy to route /mcp/* to port 9002"
echo "  3. Test via HTTPS: curl -H 'Authorization: Bearer \$MCP_API_KEY_C' https://l9.quantumaipartners.com/mcp/tools"
echo "  4. Update Cursor mcp.json with MCP_API_KEY_C as Bearer token"
