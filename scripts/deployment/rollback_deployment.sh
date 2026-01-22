#!/usr/bin/env bash
# ============================================================================
# Rollback Deployment Script
# ============================================================================
# 
# This script rolls back to the previous deployment if the new deployment fails.
#
# DORA META:
# - component_name: "Rollback-Deployment"
# - module_version: "1.0.0"
# - created_by: "Manus AI"
# - created_at: "2026-01-20T00:00:00Z"
# - layer: "operations"
# - domain: "deployment"
# - type: "script"
# - status: "active"
# ============================================================================

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}⚠ Initiating deployment rollback...${NC}"

# Check if backup exists
BACKUP_DIR="/var/backups/l9_deployments"
LATEST_BACKUP=$(ls -t "$BACKUP_DIR" 2>/dev/null | head -1 || echo "")

if [ -z "$LATEST_BACKUP" ]; then
    echo -e "${RED}✗ No backup found. Cannot rollback.${NC}"
    exit 1
fi

echo "Found backup: $LATEST_BACKUP"

# Stop current services
echo -n "Stopping current services... "
docker compose down
echo -e "${GREEN}✓${NC}"

# Restore from backup
echo -n "Restoring from backup... "
tar -xzf "$BACKUP_DIR/$LATEST_BACKUP" -C /
echo -e "${GREEN}✓${NC}"

# Start services with previous version
echo -n "Starting services with previous version... "
docker compose up -d
echo -e "${GREEN}✓${NC}"

# Wait for services to stabilize
echo "Waiting for services to stabilize (30s)..."
sleep 30

# Run post-deployment health check
echo "Running health checks..."
if ./scripts/deployment/post_deploy_check.sh; then
    echo -e "${GREEN}✓ Rollback successful${NC}"
    exit 0
else
    echo -e "${RED}✗ Rollback failed - services are not healthy${NC}"
    exit 1
fi
