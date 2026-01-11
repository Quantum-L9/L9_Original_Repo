#!/bin/bash
# Deploy MCP Memory Server to VPS
# Run this script ON THE VPS (not locally)

set -euo pipefail

echo "=== MCP Memory Server VPS Deployment ==="
echo ""

# Step 1: Fix Caddy Routing
echo "[1/3] Fixing Caddy routing for /mcp/* → 127.0.0.1:9002..."
cd /opt/l9 && \
sudo cp /etc/caddy/Caddyfile /etc/caddy/Caddyfile.backup && \
sudo sed -i 's#reverse_proxy /mcp/\* 127\.0\.0\.1:[0-9]\+#reverse_proxy /mcp/* 127.0.0.1:9002#' /etc/caddy/Caddyfile && \
echo "✓ Caddyfile backed up and updated" && \
grep -A3 '/mcp/' /etc/caddy/Caddyfile && \
echo "" && \
sudo systemctl reload caddy && \
echo "✓ Caddy reloaded" && \
sudo systemctl status caddy --no-pager | head -20

echo ""
echo "[2/3] Installing and starting l9-mcp systemd service..."
cd /opt/l9 && \
sudo cp /opt/l9/mcp_memory/deploy/systemd/l9-mcp.service /etc/systemd/system/l9-mcp.service && \
sudo systemctl daemon-reload && \
sudo systemctl enable l9-mcp && \
sudo systemctl start l9-mcp && \
echo "✓ Service installed and started" && \
sudo systemctl status l9-mcp --no-pager | head -20 && \
echo "" && \
sudo ss -tlnp | grep ':9002' || echo '⚠️  WARNING: Port 9002 not listening (service may be starting)'

echo ""
echo "[3/3] Testing MCP endpoints..."
cd /opt/l9 && \
set -a && source .env && set +a && \
echo "Testing MCP tools endpoint..." && \
curl -vk "https://l9.quantumaipartners.com/mcp/tools" \
  -H "Authorization: Bearer ${MCP_API_KEYC:-$MCP_API_KEY_C}" || echo "⚠️  MCP endpoint test failed (check service logs)"

echo ""
echo "=== Deployment Complete ==="
echo ""
echo "Next steps:"
echo "  1. Check service logs: sudo journalctl -u l9-mcp -f"
echo "  2. Test health: curl http://127.0.0.1:9002/health"
echo "  3. Test via Caddy: curl https://l9.quantumaipartners.com/mcp/health"

