#!/usr/bin/env bash
# =============================================================================
# L9 VPS Rollback Script
# Version: 1.0.0
#
# Rolls back to the previous deployment version.
# =============================================================================

set -euo pipefail

# Configuration
VPS_HOST="157.180.73.53"
VPS_USER="root"
VPS_PATH="/root/L9"
BACKUP_PATH="/root/L9_backups"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info() { echo -e "[INFO] $*"; }
log_success() { echo -e "${GREEN}[✓]${NC} $*"; }
log_error() { echo -e "${RED}[✗]${NC} $*"; }

echo ""
echo -e "${YELLOW}═══════════════════════════════════════════════════════════════${NC}"
echo -e "${YELLOW}  L9 VPS Rollback${NC}"
echo -e "${YELLOW}═══════════════════════════════════════════════════════════════${NC}"
echo ""

# List available backups
log_info "Available backups:"
ssh "$VPS_USER@$VPS_HOST" "ls -lt $BACKUP_PATH/ | head -10" 2>/dev/null || {
    log_error "No backups found at $BACKUP_PATH"
    exit 1
}

echo ""

# Get latest backup
LATEST_BACKUP=$(ssh "$VPS_USER@$VPS_HOST" "ls -t $BACKUP_PATH/ | head -1" 2>/dev/null)

if [[ -z "$LATEST_BACKUP" ]]; then
    log_error "No backups available for rollback"
    exit 1
fi

echo -e "${YELLOW}Will rollback to: $LATEST_BACKUP${NC}"
echo ""
read -p "Continue with rollback? (y/N): " -n 1 -r
echo ""

if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Rollback cancelled."
    exit 0
fi

# Perform rollback
log_info "Rolling back to $LATEST_BACKUP..."

ssh "$VPS_USER@$VPS_HOST" bash <<EOF
    set -e
    cd $VPS_PATH
    
    echo "Stopping current stack..."
    docker compose down --remove-orphans 2>/dev/null || true
    
    echo "Restoring backup..."
    rm -rf $VPS_PATH/*
    cp -r $BACKUP_PATH/$LATEST_BACKUP/* $VPS_PATH/
    
    echo "Rebuilding and starting..."
    docker compose build --quiet
    docker compose up -d
    
    echo "Waiting for services..."
    sleep 10
    
    docker compose ps
EOF

# Verify rollback
sleep 5
HEALTH_STATUS=$(ssh "$VPS_USER@$VPS_HOST" "curl -sf http://localhost:8000/health" 2>/dev/null || echo "FAILED")

if [[ "$HEALTH_STATUS" == *"ok"* ]]; then
    log_success "Rollback complete - health check passed"
else
    log_error "Rollback complete but health check failed!"
    log_error "Manual intervention may be required"
    exit 1
fi

echo ""
log_success "Successfully rolled back to: $LATEST_BACKUP"

