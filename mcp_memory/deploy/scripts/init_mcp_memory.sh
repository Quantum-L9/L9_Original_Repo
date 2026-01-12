#!/bin/bash
# L9 MCP Memory Server - Initialization Script
# Run this on VPS to initialize MCP memory server
#
# Usage: sudo bash /opt/l9/mcp_memory/deploy/scripts/init_mcp_memory.sh

set -e

echo "╔════════════════════════════════════════════════════════════════╗"
echo "║  L9 MCP Memory Server - Initialization                        ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""

# Configuration
L9_DIR="/opt/l9"
MCP_DIR="$L9_DIR/mcp_memory"
VENV_DIR="$L9_DIR/venv"
SERVICE_NAME="l9-mcp"

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo "❌ Please run as root (sudo)"
    exit 1
fi

# Step 1: Verify code is pulled
echo "[1/7] Verifying code deployment..."
if [ ! -d "$MCP_DIR" ]; then
    echo "❌ MCP directory not found: $MCP_DIR"
    echo "   Run: cd $L9_DIR && git pull origin main"
    exit 1
fi
echo "✅ Code found"

# Step 2: Load environment variables
echo ""
echo "[2/7] Loading environment variables..."
cd "$L9_DIR"
if [ ! -f ".env" ]; then
    echo "❌ .env file not found at $L9_DIR/.env"
    exit 1
fi
source .env

# Check required variables
REQUIRED_VARS=("MCP_API_KEY_L" "MCP_API_KEY_C" "OPENAI_API_KEY" "MEMORY_DSN")
MISSING_VARS=()

for var in "${REQUIRED_VARS[@]}"; do
    if [ -z "${!var}" ]; then
        MISSING_VARS+=("$var")
    fi
done

if [ ${#MISSING_VARS[@]} -ne 0 ]; then
    echo "❌ Missing environment variables:"
    printf '   - %s\n' "${MISSING_VARS[@]}"
    echo ""
    echo "Add them to $L9_DIR/.env"
    exit 1
fi
echo "✅ Environment variables configured"

# Step 3: Verify virtual environment
echo ""
echo "[3/7] Verifying virtual environment..."
if [ ! -d "$VENV_DIR" ]; then
    echo "⚠️  Virtual environment not found, creating..."
    python3.11 -m venv "$VENV_DIR"
    echo "✅ Virtual environment created"
else
    echo "✅ Virtual environment found"
fi

# Step 4: Install/update dependencies
echo ""
echo "[4/7] Installing dependencies..."
cd "$MCP_DIR"
source "$VENV_DIR/bin/activate"
pip install --upgrade pip -q
if [ -f "requirements.txt" ]; then
    pip install -r requirements.txt -q
    echo "✅ Dependencies installed"
else
    echo "⚠️  requirements.txt not found, installing core packages..."
    pip install fastapi uvicorn asyncpg pgvector openai pydantic-settings structlog -q
    echo "✅ Core dependencies installed"
fi

# Step 5: Verify L9 migrations are applied
echo ""
echo "[5/7] Verifying L9 memory substrate migrations..."
cd "$L9_DIR"

# Check if packet_store exists (from migration 0001)
if psql "$MEMORY_DSN" -tAc "SELECT 1 FROM information_schema.tables WHERE table_schema='public' AND table_name='packet_store'" | grep -q 1; then
    echo "✅ packet_store table exists (migration 0001 applied)"
else
    echo "⚠️  packet_store not found - applying L9 migrations..."
    if [ -f "migrations/0001_init_memory_substrate.sql" ]; then
        psql "$MEMORY_DSN" -f migrations/0001_init_memory_substrate.sql
        echo "✅ Migration 0001 applied"
    else
        echo "❌ Migration 0001 not found - L9 substrate may not be initialized"
        exit 1
    fi
fi

# Check if memory_embeddings exists (from migration 0008)
if psql "$MEMORY_DSN" -tAc "SELECT 1 FROM information_schema.tables WHERE table_schema='public' AND table_name='memory_embeddings'" | grep -q 1; then
    echo "✅ memory_embeddings table exists (migration 0008 applied)"
else
    echo "⚠️  memory_embeddings not found - applying migration 0008..."
    if [ -f "migrations/0008_memory_substrate_10x.sql" ]; then
        psql "$MEMORY_DSN" -f migrations/0008_memory_substrate_10x.sql
        echo "✅ Migration 0008 applied"
    else
        echo "⚠️  Migration 0008 not found - continuing anyway"
    fi
fi

# Step 6: Apply MCP-specific migration (0013)
echo ""
echo "[6/7] Applying MCP audit migration (0013)..."
if psql "$MEMORY_DSN" -tAc "SELECT 1 FROM information_schema.columns WHERE table_name='tool_audit_log' AND column_name='caller'" | grep -q 1; then
    echo "✅ Migration 0013 already applied (caller column exists)"
else
    if [ -f "migrations/0013_mcp_audit_columns.sql" ]; then
        psql "$MEMORY_DSN" -f migrations/0013_mcp_audit_columns.sql
        echo "✅ Migration 0013 applied"
    else
        echo "⚠️  Migration 0013 not found - continuing anyway"
    fi
fi

# Step 7: Install and start systemd service
echo ""
echo "[7/7] Installing systemd service..."
cd "$L9_DIR"

SERVICE_FILE="$MCP_DIR/deploy/systemd/l9-mcp.service"
if [ ! -f "$SERVICE_FILE" ]; then
    echo "❌ Service file not found: $SERVICE_FILE"
    exit 1
fi

cp "$SERVICE_FILE" /etc/systemd/system/
systemctl daemon-reload
systemctl enable "$SERVICE_NAME"

# Check if service is already running
if systemctl is-active --quiet "$SERVICE_NAME"; then
    echo "⚠️  Service already running, restarting..."
    systemctl restart "$SERVICE_NAME"
else
    echo "Starting service..."
    systemctl start "$SERVICE_NAME"
fi

# Wait for service to start
sleep 3

if systemctl is-active --quiet "$SERVICE_NAME"; then
    echo "✅ Service installed and running"
else
    echo "❌ Service failed to start"
    echo "   Check logs: sudo journalctl -u $SERVICE_NAME -n 50"
    exit 1
fi

# Final verification
echo ""
echo "╔════════════════════════════════════════════════════════════════╗"
echo "║  ✅ Initialization Complete!                                 ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""
echo "Service Status:"
systemctl status "$SERVICE_NAME" --no-pager -l | head -n 12
echo ""
echo "Test Commands:"
echo "  Health: curl http://127.0.0.1:9001/health"
echo "  Tools:  curl -H 'Authorization: Bearer \$MCP_API_KEY_C' http://127.0.0.1:9001/mcp/tools"
echo ""
echo "View logs: sudo journalctl -u $SERVICE_NAME -f"
echo ""
echo "Next Steps:"
echo "  1. Configure Caddy routing (see mcp_memory/deploy/VPS_DEPLOYMENT_GUIDE.md)"
echo "  2. Test via HTTPS: curl https://l9.quantumaipartners.com/mcp/health"
echo "  3. Update Cursor mcp.json with MCP server config"
