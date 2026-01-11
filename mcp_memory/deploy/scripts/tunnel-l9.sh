#!/bin/bash
VPS_IP="157.180.73.53"
VPS_USER="admin"
LOCAL_PORT="9001"
REMOTE_PORT="9001"

echo "🔗 Establishing SSH tunnel to L9 MCP server..."
ssh -L ${LOCAL_PORT}:127.0.0.1:${REMOTE_PORT} ${VPS_USER}@${VPS_IP}
