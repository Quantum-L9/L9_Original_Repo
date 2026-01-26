#!/bin/bash
# Install Reverse Tunnel
# Sets up SSH tunnel LaunchAgent for Mac Agent connectivity

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LAUNCH_AGENTS_DIR="$HOME/Library/LaunchAgents"

echo "=== L9 Reverse Tunnel Installation ==="

# Check if running as regular user (not root)
if [ "$EUID" -eq 0 ]; then
    echo "ERROR: Do not run this script as root/sudo"
    echo "Run as your regular user account"
    exit 1
fi

# Create LaunchAgents directory if it doesn't exist
mkdir -p "$LAUNCH_AGENTS_DIR"

# Install tunnel LaunchAgent
echo "Installing tunnel LaunchAgent..."
cp "$SCRIPT_DIR/com.l9.tunnel.plist" "$LAUNCH_AGENTS_DIR/"

# Update plist path to use actual agent directory
AGENT_DIR="/opt/l9_agent"
sed -i '' "s|/opt/l9_agent|$AGENT_DIR|g" "$LAUNCH_AGENTS_DIR/com.l9.tunnel.plist"

# Load LaunchAgent
echo "Loading tunnel LaunchAgent..."
launchctl load "$LAUNCH_AGENTS_DIR/com.l9.tunnel.plist" 2>/dev/null || \
    (launchctl unload "$LAUNCH_AGENTS_DIR/com.l9.tunnel.plist" && \
     launchctl load "$LAUNCH_AGENTS_DIR/com.l9.tunnel.plist")

echo ""
echo "=== Installation Complete ==="
echo ""
echo "Tunnel LaunchAgent installed and loaded"
echo ""
echo "To check status:"
echo "  launchctl list | grep l9.tunnel"
echo ""
echo "To view logs:"
echo "  tail -f /opt/l9_agent/logs/tunnel.log"
echo ""
echo "To unload:"
echo "  launchctl unload $LAUNCH_AGENTS_DIR/com.l9.tunnel.plist"
echo ""
