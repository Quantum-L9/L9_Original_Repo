#!/bin/bash
# SSH Tunnel Setup
# Creates forward tunnel from Mac to VPS
# Mac localhost:8080 -> VPS localhost:8080
# Mac Agent connects to localhost:8080 to reach VPS API

set -e

VPS_HOST="157.180.73.53"
VPS_USER="admin"
VPS_PORT="8000"
LOCAL_PORT="8000"
SSH_KEY="${HOME}/.ssh/id_rsa"

# Check if SSH key exists
if [ ! -f "$SSH_KEY" ]; then
    echo "ERROR: SSH key not found at $SSH_KEY"
    echo "Generate one with: ssh-keygen -t rsa -b 4096"
    exit 1
fi

echo "=== L9 SSH Tunnel Setup ==="
echo "VPS: $VPS_USER@$VPS_HOST"
echo "Forwarding: Mac localhost:$LOCAL_PORT -> VPS localhost:$VPS_PORT"
echo "Mac Agent connects to http://localhost:$LOCAL_PORT to reach VPS API (port 8000)"
echo ""

# Create forward tunnel
# -L local_port:remote_host:remote_port
# This forwards Mac localhost:8000 to VPS localhost:8000
ssh -N -L ${LOCAL_PORT}:localhost:${VPS_PORT} \
    -i "$SSH_KEY" \
    -o ServerAliveInterval=60 \
    -o ServerAliveCountMax=3 \
    -o ExitOnForwardFailure=yes \
    ${VPS_USER}@${VPS_HOST}
