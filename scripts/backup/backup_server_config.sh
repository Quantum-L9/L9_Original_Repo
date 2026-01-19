#!/usr/bin/env bash
# =============================================================================
# L9 Server Configuration Backup
# Version: 1.0.0
#
# Backs up VPS system configs needed to replicate the server setup.
# REQUIRES SUDO - run manually or via root cron.
#
# GOVERNANCE: IGOR_ONLY
# CURSOR_SAFE: false (requires sudo)
# =============================================================================

set -euo pipefail

# =============================================================================
# CONFIGURATION
# =============================================================================

BACKUP_DIR="${BACKUP_DIR:-/opt/l9/backups/server-config}"
S3_BUCKET="${S3_BUCKET:-l9-backups}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# =============================================================================
# WHAT GETS BACKED UP
# =============================================================================
#
# This script backs up all configs needed to rebuild the VPS from scratch:
#
# 1. CRONTAB (user: admin)
#    - Scheduled jobs (backup cron, etc.)
#    - Location: `crontab -l`
#
# 2. CADDY (reverse proxy)
#    - HTTPS termination, routing to L9 services
#    - Location: /etc/caddy/Caddyfile
#
# 3. SYSTEMD SERVICES
#    - l9.service - Main L9 API service
#    - l9-agent.service - Agent executor service
#    - l9-mcp.service - MCP memory service
#    - l9.env - Shared environment variables
#    - Locations: /etc/systemd/system/l9*
#
# 4. SYSTEMD OVERRIDES
#    - environment.conf - Additional env vars
#    - twilio.conf - Twilio credentials
#    - waba.conf - WhatsApp Business API credentials
#    - relax-protect.conf - Security relaxations for Docker
#    - override.conf - Service overrides
#    - Locations: /etc/systemd/system/l9.service.d/
#                 /etc/systemd/system/l9-agent.service.d/
#
# 5. AWS CREDENTIALS (user: admin)
#    - For S3 backup access
#    - Location: ~/.aws/credentials, ~/.aws/config
#
# 6. L9 ENV FILE
#    - Main application config
#    - Location: /opt/l9/.env
#    - NOTE: Already backed up by backup_l9_memory.sh
#
# =============================================================================

log() {
    echo -e "${GREEN}[$(date '+%H:%M:%S')]${NC} $1"
}

warn() {
    echo -e "${YELLOW}[$(date '+%H:%M:%S')] WARNING:${NC} $1"
}

error() {
    echo -e "${RED}[$(date '+%H:%M:%S')] ERROR:${NC} $1"
}

# =============================================================================
# MAIN
# =============================================================================

main() {
    log "Starting server config backup..."
    
    # Check sudo
    if [[ $EUID -ne 0 ]]; then
        error "This script must be run with sudo"
        echo "Usage: sudo $0"
        exit 1
    fi
    
    # Create backup directory
    mkdir -p "$BACKUP_DIR"
    cd "$BACKUP_DIR"
    
    # 1. Backup crontab (as admin user)
    log "Backing up crontab..."
    sudo -u admin crontab -l > crontab_admin.txt 2>/dev/null || echo "# No crontab for admin" > crontab_admin.txt
    crontab -l > crontab_root.txt 2>/dev/null || echo "# No crontab for root" > crontab_root.txt
    
    # 2. Backup AWS credentials (as admin user)
    log "Backing up AWS credentials..."
    if [[ -f /home/admin/.aws/credentials ]]; then
        cp /home/admin/.aws/credentials aws_credentials
        cp /home/admin/.aws/config aws_config
    else
        warn "No AWS credentials found"
    fi
    
    # 3. Create tarball of system configs
    log "Creating system configs tarball..."
    TARBALL="system-configs_${TIMESTAMP}.tar.gz"
    
    tar -czvf "$TARBALL" \
        /etc/caddy/Caddyfile \
        /etc/systemd/system/l9*.service \
        /etc/systemd/system/l9.env \
        /etc/systemd/system/l9.service.d \
        /etc/systemd/system/l9-agent.service.d \
        2>/dev/null || true
    
    # 4. Upload to S3
    log "Uploading to S3..."
    if command -v aws &> /dev/null; then
        # Upload timestamped version
        aws s3 cp "$TARBALL" "s3://${S3_BUCKET}/server-config/${TARBALL}"
        
        # Also upload as "latest" for easy restore
        aws s3 cp "$TARBALL" "s3://${S3_BUCKET}/server-config/system-configs-latest.tar.gz"
        
        # Upload individual files for easy inspection
        aws s3 cp crontab_admin.txt "s3://${S3_BUCKET}/server-config/crontab_admin.txt"
        [[ -f aws_credentials ]] && aws s3 cp aws_credentials "s3://${S3_BUCKET}/server-config/aws_credentials"
        [[ -f aws_config ]] && aws s3 cp aws_config "s3://${S3_BUCKET}/server-config/aws_config"
        
        log "✅ Uploaded to s3://${S3_BUCKET}/server-config/"
    else
        warn "AWS CLI not found, skipping S3 upload"
        log "Backup saved locally to: $BACKUP_DIR/$TARBALL"
    fi
    
    # 5. Cleanup old local backups (keep last 3)
    log "Cleaning up old local backups..."
    ls -t system-configs_*.tar.gz 2>/dev/null | tail -n +4 | xargs -r rm -f
    
    log "✅ Server config backup complete!"
    echo ""
    echo "Files backed up:"
    ls -la "$BACKUP_DIR"
}

# =============================================================================
# RESTORE INSTRUCTIONS
# =============================================================================
#
# To restore on a new server:
#
# 1. Download from S3:
#    aws s3 cp s3://l9-backups/server-config/system-configs-latest.tar.gz .
#
# 2. Extract:
#    sudo tar -xzvf system-configs-latest.tar.gz -C /
#
# 3. Reload systemd:
#    sudo systemctl daemon-reload
#
# 4. Restore crontab:
#    crontab crontab_admin.txt
#
# 5. Restore AWS credentials:
#    mkdir -p ~/.aws
#    cp aws_credentials ~/.aws/credentials
#    cp aws_config ~/.aws/config
#
# 6. Restart services:
#    sudo systemctl restart caddy l9 l9-agent l9-mcp
#
# =============================================================================

main "$@"
