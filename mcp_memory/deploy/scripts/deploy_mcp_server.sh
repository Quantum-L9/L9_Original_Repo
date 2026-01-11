#!/bin/bash
# L9 MCP Memory Server - Deployment Script
# Deploys MCP server to VPS with systemd service

set -e

echo "=========================================="
echo "L9 MCP Memory Server Deployment"
echo "=========================================="

# Configuration
MCP_DIR="/opt/l9/mcp_memory"
VENV_DIR="/opt/l9/venv"
SERVICE_FILE="mcp_memory/deploy/systemd/l9-mcp.service"
SERVICE_NAME="l9-mcp"

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo "❌ Please run as root (sudo)"
    exit 1
fi

# Step 1: Verify code is deployed
echo ""
echo "[1/6] Verifying code deployment..."
if [ ! -d "$MCP_DIR" ]; then
    echo "❌ MCP directory not found: $MCP_DIR"
    echo "   Run: git pull origin main in /opt/l9"
    exit 1
fi
echo "✅ Code found at $MCP_DIR"

# Step 2: Verify virtual environment
echo ""
echo "[2/6] Verifying virtual environment..."
if [ ! -d "$VENV_DIR" ]; then
    echo "❌ Virtual environment not found: $VENV_DIR"
    echo "   Create with: python3.11 -m venv $VENV_DIR"
    exit 1
fi
echo "✅ Virtual environment found"

# Step 3: Install/update dependencies
echo ""
echo "[3/6] Installing dependencies..."
cd "$MCP_DIR"
source "$VENV_DIR/bin/activate"
pip install --upgrade pip -q
pip install -r requirements.txt -q
echo "✅ Dependencies installed"

# Step 4: Verify environment variables
echo ""
echo "[4/6] Verifying environment variables..."
cd /opt/l9
if [ ! -f ".env" ]; then
    echo "❌ .env file not found at /opt/l9/.env"
    exit 1
fi

# Check required vars
source .env
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
    exit 1
fi
echo "✅ Environment variables configured"

# Step 5: Apply database migration (if needed)
echo ""
echo "[5/6] Checking database migration..."
cd /opt/l9
if psql "$MEMORY_DSN" -tAc "SELECT 1 FROM information_schema.columns WHERE table_name='tool_audit_log' AND column_name='caller'" | grep -q 1; then
    echo "✅ Migration 0013 already applied (caller column exists)"
else
    echo "⚠️  Applying migration 0013..."
    psql "$MEMORY_DSN" -f migrations/0013_mcp_audit_columns.sql
    echo "✅ Migration applied"
fi

# Step 6: Install systemd service
echo ""
echo "[6/6] Installing systemd service..."
cd /opt/l9
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
sleep 2

if systemctl is-active --quiet "$SERVICE_NAME"; then
    echo "✅ Service installed and running"
else
    echo "❌ Service failed to start"
    echo "   Check logs: sudo journalctl -u $SERVICE_NAME -n 50"
    exit 1
fi

# Final verification
echo ""
echo "=========================================="
echo "✅ Deployment Complete!"
echo "=========================================="
echo ""
echo "Service Status:"
systemctl status "$SERVICE_NAME" --no-pager -l | head -n 10
echo ""
echo "Test endpoints:"
echo "  Health: curl http://127.0.0.1:9001/health"
echo "  Tools:  curl -H 'Authorization: Bearer \$MCP_API_KEY_C' http://127.0.0.1:9001/mcp/tools"
echo ""
echo "View logs: sudo journalctl -u $SERVICE_NAME -f"

