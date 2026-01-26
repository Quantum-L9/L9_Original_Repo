#!/bin/bash
# Deploy L9 to VPS using Docker Compose (CANONICAL METHOD)
# Run this script ON THE VPS (not locally)
#
# IMPORTANT: Systemd services are DEPRECATED. Use Docker only.

set -euo pipefail

echo "=== L9 VPS Deployment (Docker) ==="
echo ""
echo "⚠️  NOTE: Systemd services (l9.service, l9-mcp.service) are DEPRECATED."
echo "         Docker Compose is the ONLY supported deployment method."
echo ""

# Step 1: Git pull
echo "[1/4] Pulling latest code..."
cd /opt/l9 && git pull origin main
echo "✓ Code updated"

# Step 2: Ensure no systemd services are running (cleanup)
echo ""
echo "[2/4] Checking for deprecated systemd services..."
for svc in l9.service l9-mcp.service l9-agent.service; do
    if systemctl is-active --quiet "$svc" 2>/dev/null; then
        echo "⚠️  Stopping deprecated $svc..."
        sudo systemctl stop "$svc" 2>/dev/null || true
        sudo systemctl disable "$svc" 2>/dev/null || true
    fi
done
echo "✓ Systemd cleanup complete"

# Step 3: Docker Compose
echo ""
echo "[3/4] Starting Docker containers..."
cd /opt/l9 && docker compose up -d --build l9-api l9-mcp-memory
echo "✓ Docker containers started (l9-api + l9-mcp-memory)"

# Step 4: Health check
echo ""
echo "[4/4] Running health checks..."
sleep 10
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" | grep l9-
echo ""
echo "API Health:"
curl -s http://127.0.0.1:8000/health | jq . || echo "⚠️  API health check failed"
echo ""
echo "MCP Memory Health:"
curl -s http://127.0.0.1:9002/health | jq . || echo "⚠️  MCP memory health check failed"

echo ""
echo "=== Deployment Complete ==="
echo ""
echo "Test endpoints:"
echo "  API Health:    curl http://127.0.0.1:8000/health"
echo "  MCP Health:    curl http://127.0.0.1:9002/health"
echo "  MCP Tools:     curl -H 'Authorization: Bearer \$MCP_API_KEY_C' http://127.0.0.1:9002/mcp/tools"
echo ""
echo "View logs:"
echo "  API:    docker logs l9-api -f"
echo "  MCP:    docker logs l9-mcp-memory -f"
