#!/bin/bash
# Mac Agent Installation Script
# Installs Mac Agent, dependencies, and LaunchAgent plists

set -e

AGENT_DIR="/opt/l9_agent"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LAUNCH_AGENTS_DIR="$HOME/Library/LaunchAgents"

echo "=== L9 Mac Agent Installation ==="

# Check if running as regular user (not root)
if [ "$EUID" -eq 0 ]; then
    echo "ERROR: Do not run this script as root/sudo"
    echo "Run as your regular user account"
    exit 1
fi

# Create agent directory
echo "Creating agent directory: $AGENT_DIR"
sudo mkdir -p "$AGENT_DIR"/logs
sudo chown -R "$USER:staff" "$AGENT_DIR"

# Copy agent files
echo "Copying agent files..."
cp "$SCRIPT_DIR/agent.py" "$AGENT_DIR/"
cp "$SCRIPT_DIR/__init__.py" "$AGENT_DIR/" 2>/dev/null || true
cp "$SCRIPT_DIR/config.yaml" "$AGENT_DIR/"
cp "$SCRIPT_DIR/reverse_tunnel.sh" "$AGENT_DIR/"
chmod +x "$AGENT_DIR/agent.py"
chmod +x "$AGENT_DIR/reverse_tunnel.sh"

# Install Python dependencies
echo "Installing Python dependencies..."
pip3 install -r "$SCRIPT_DIR/requirements.txt"

# Install Playwright browsers
if command -v playwright &> /dev/null; then
    echo "Installing Playwright browsers..."
    playwright install chromium
else
    echo "Playwright not found, skipping browser installation"
fi

# Create LaunchAgents directory if it doesn't exist
mkdir -p "$LAUNCH_AGENTS_DIR"

# Install LaunchAgent plists
echo "Installing LaunchAgent plists..."
cp "$SCRIPT_DIR/com.l9.agent.plist" "$LAUNCH_AGENTS_DIR/"
cp "$SCRIPT_DIR/com.l9.tunnel.plist" "$LAUNCH_AGENTS_DIR/"

# Update plist paths to use actual agent directory
sed -i '' "s|/opt/l9_agent|$AGENT_DIR|g" "$LAUNCH_AGENTS_DIR/com.l9.agent.plist"
sed -i '' "s|/opt/l9_agent|$AGENT_DIR|g" "$LAUNCH_AGENTS_DIR/com.l9.tunnel.plist"

# Load LaunchAgents
echo "Loading LaunchAgents..."
launchctl load "$LAUNCH_AGENTS_DIR/com.l9.agent.plist" 2>/dev/null || launchctl unload "$LAUNCH_AGENTS_DIR/com.l9.agent.plist" && launchctl load "$LAUNCH_AGENTS_DIR/com.l9.agent.plist"
launchctl load "$LAUNCH_AGENTS_DIR/com.l9.tunnel.plist" 2>/dev/null || launchctl unload "$LAUNCH_AGENTS_DIR/com.l9.tunnel.plist" && launchctl load "$LAUNCH_AGENTS_DIR/com.l9.tunnel.plist"

echo ""
echo "=== Installation Complete ==="
echo ""
echo "Agent directory: $AGENT_DIR"
echo "Logs: $AGENT_DIR/logs/"
echo ""
echo "To check status:"
echo "  launchctl list | grep l9"
echo ""
echo "To view logs:"
echo "  tail -f $AGENT_DIR/logs/agent.log"
echo "  tail -f $AGENT_DIR/logs/tunnel.log"
echo ""
echo "To unload agents:"
echo "  launchctl unload $LAUNCH_AGENTS_DIR/com.l9.agent.plist"
echo "  launchctl unload $LAUNCH_AGENTS_DIR/com.l9.tunnel.plist"
echo ""
