#!/usr/bin/env bash
# =============================================================================
# L9 VPS Bootstrap Script
# Version: 1.0.0
#
# Takes a fresh Ubuntu 22.04 VPS to fully working L9 server.
# Run as root or with sudo on a fresh VPS.
#
# Usage:
#   curl -sL https://raw.githubusercontent.com/YOUR_REPO/l9/main/scripts/infra/bootstrap_vps.sh | sudo bash
#   # OR
#   sudo ./bootstrap_vps.sh
#
# Prerequisites:
#   - Fresh Ubuntu 22.04 LTS
#   - Root or sudo access
#   - Internet connectivity
#
# GOVERNANCE: IGOR_ONLY
# =============================================================================

set -euo pipefail

# =============================================================================
# CONFIGURATION - EDIT THESE
# =============================================================================

L9_DOMAIN="${L9_DOMAIN:-your-domain.com}"           # Your domain
L9_EMAIL="${L9_EMAIL:-your-email@example.com}"      # For Let's Encrypt
L9_REPO="${L9_REPO:-git@github.com:your/l9.git}"    # L9 git repo
L9_BRANCH="${L9_BRANCH:-main}"                       # Git branch
L9_DIR="${L9_DIR:-/opt/l9}"                          # Install directory
ADMIN_USER="${ADMIN_USER:-admin}"                    # Non-root user
S3_BUCKET="${S3_BUCKET:-l9-backups}"                 # S3 backup bucket

# AWS credentials (pass via env or edit here)
AWS_ACCESS_KEY="${AWS_ACCESS_KEY:-}"
AWS_SECRET_KEY="${AWS_SECRET_KEY:-}"
AWS_REGION="${AWS_REGION:-us-east-1}"

# =============================================================================
# COLORS
# =============================================================================

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log() { echo -e "${GREEN}[$(date '+%H:%M:%S')]${NC} $1"; }
warn() { echo -e "${YELLOW}[$(date '+%H:%M:%S')] WARNING:${NC} $1"; }
error() { echo -e "${RED}[$(date '+%H:%M:%S')] ERROR:${NC} $1"; exit 1; }
section() { echo -e "\n${BLUE}========== $1 ==========${NC}\n"; }

# =============================================================================
# PHASE 1: SYSTEM SETUP
# =============================================================================

phase1_system_setup() {
    section "PHASE 1: System Setup"
    
    # Update system
    log "Updating system packages..."
    apt-get update && apt-get upgrade -y
    
    # Install essentials
    log "Installing essential packages..."
    apt-get install -y \
        curl \
        wget \
        git \
        unzip \
        htop \
        vim \
        jq \
        software-properties-common \
        apt-transport-https \
        ca-certificates \
        gnupg \
        lsb-release
    
    # Create admin user if doesn't exist
    if ! id "$ADMIN_USER" &>/dev/null; then
        log "Creating admin user: $ADMIN_USER"
        useradd -m -s /bin/bash "$ADMIN_USER"
        usermod -aG sudo "$ADMIN_USER"
        echo "$ADMIN_USER ALL=(ALL) NOPASSWD:ALL" > /etc/sudoers.d/$ADMIN_USER
    fi
    
    log "✅ Phase 1 complete"
}

# =============================================================================
# PHASE 2: DOCKER INSTALLATION
# =============================================================================

phase2_docker() {
    section "PHASE 2: Docker Installation"
    
    if command -v docker &> /dev/null; then
        log "Docker already installed: $(docker --version)"
    else
        log "Installing Docker..."
        curl -fsSL https://get.docker.com | sh
        
        # Add admin user to docker group
        usermod -aG docker "$ADMIN_USER"
    fi
    
    # Install Docker Compose v2
    if ! docker compose version &> /dev/null; then
        log "Installing Docker Compose..."
        apt-get install -y docker-compose-plugin
    fi
    
    # Enable and start Docker
    systemctl enable docker
    systemctl start docker
    
    log "Docker version: $(docker --version)"
    log "Docker Compose version: $(docker compose version)"
    log "✅ Phase 2 complete"
}

# =============================================================================
# PHASE 3: CADDY (REVERSE PROXY)
# =============================================================================

phase3_caddy() {
    section "PHASE 3: Caddy Installation"
    
    if command -v caddy &> /dev/null; then
        log "Caddy already installed: $(caddy version)"
    else
        log "Installing Caddy..."
        apt-get install -y debian-keyring debian-archive-keyring apt-transport-https
        curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
        curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' | tee /etc/apt/sources.list.d/caddy-stable.list
        apt-get update
        apt-get install -y caddy
    fi
    
    # Caddy config will be restored from S3 backup
    log "✅ Phase 3 complete"
}

# =============================================================================
# PHASE 4: AWS CLI
# =============================================================================

phase4_aws() {
    section "PHASE 4: AWS CLI Installation"
    
    if command -v aws &> /dev/null; then
        log "AWS CLI already installed: $(aws --version)"
    else
        log "Installing AWS CLI v2..."
        curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "/tmp/awscliv2.zip"
        unzip -q /tmp/awscliv2.zip -d /tmp
        /tmp/aws/install
        rm -rf /tmp/aws /tmp/awscliv2.zip
    fi
    
    # Configure AWS for admin user
    if [[ -n "$AWS_ACCESS_KEY" && -n "$AWS_SECRET_KEY" ]]; then
        log "Configuring AWS credentials..."
        sudo -u "$ADMIN_USER" mkdir -p /home/$ADMIN_USER/.aws
        
        cat > /home/$ADMIN_USER/.aws/credentials << EOF
[default]
aws_access_key_id = $AWS_ACCESS_KEY
aws_secret_access_key = $AWS_SECRET_KEY
EOF
        
        cat > /home/$ADMIN_USER/.aws/config << EOF
[default]
region = $AWS_REGION
output = json
EOF
        
        chown -R $ADMIN_USER:$ADMIN_USER /home/$ADMIN_USER/.aws
        chmod 600 /home/$ADMIN_USER/.aws/credentials
    else
        warn "AWS credentials not provided. Set AWS_ACCESS_KEY and AWS_SECRET_KEY."
    fi
    
    log "✅ Phase 4 complete"
}

# =============================================================================
# PHASE 5: CLONE L9 REPOSITORY
# =============================================================================

phase5_clone_repo() {
    section "PHASE 5: Clone L9 Repository"
    
    if [[ -d "$L9_DIR/.git" ]]; then
        log "L9 repo already exists at $L9_DIR"
        cd "$L9_DIR"
        sudo -u "$ADMIN_USER" git pull origin "$L9_BRANCH"
    else
        log "Cloning L9 repository..."
        mkdir -p "$(dirname $L9_DIR)"
        git clone -b "$L9_BRANCH" "$L9_REPO" "$L9_DIR"
        chown -R $ADMIN_USER:$ADMIN_USER "$L9_DIR"
    fi
    
    log "✅ Phase 5 complete"
}

# =============================================================================
# PHASE 6: RESTORE FROM S3 BACKUP
# =============================================================================

phase6_restore_backup() {
    section "PHASE 6: Restore from S3 Backup"
    
    cd "$L9_DIR"
    
    # Check if we can access S3
    if ! sudo -u "$ADMIN_USER" aws s3 ls "s3://$S3_BUCKET/" &>/dev/null; then
        warn "Cannot access S3 bucket. Skipping backup restore."
        warn "You'll need to manually configure .env and restore data."
        return 0
    fi
    
    # Create backup directories
    mkdir -p "$L9_DIR/backups/server-config"
    chown -R $ADMIN_USER:$ADMIN_USER "$L9_DIR/backups"
    
    # Download server configs
    log "Downloading server configs from S3..."
    sudo -u "$ADMIN_USER" aws s3 cp "s3://$S3_BUCKET/server-config/system-configs-latest.tar.gz" "$L9_DIR/backups/server-config/" || warn "No server configs found"
    sudo -u "$ADMIN_USER" aws s3 cp "s3://$S3_BUCKET/server-config/crontab_admin.txt" "$L9_DIR/backups/server-config/" || warn "No crontab found"
    
    # Restore system configs
    if [[ -f "$L9_DIR/backups/server-config/system-configs-latest.tar.gz" ]]; then
        log "Restoring Caddy and systemd configs..."
        tar -xzvf "$L9_DIR/backups/server-config/system-configs-latest.tar.gz" -C /
        systemctl daemon-reload
    fi
    
    # Restore crontab
    if [[ -f "$L9_DIR/backups/server-config/crontab_admin.txt" ]]; then
        log "Restoring crontab..."
        sudo -u "$ADMIN_USER" crontab "$L9_DIR/backups/server-config/crontab_admin.txt"
    fi
    
    log "✅ Phase 6 complete"
}

# =============================================================================
# PHASE 7: START DOCKER CONTAINERS
# =============================================================================

phase7_start_containers() {
    section "PHASE 7: Start Docker Containers"
    
    cd "$L9_DIR"
    
    # Check for .env file
    if [[ ! -f "$L9_DIR/.env" ]]; then
        warn ".env file not found!"
        warn "Attempting to download latest config backup from S3..."
        
        # Try to get latest config backup
        LATEST_CONFIG=$(sudo -u "$ADMIN_USER" aws s3 ls "s3://$S3_BUCKET/config/" --recursive | sort | tail -1 | awk '{print $4}')
        if [[ -n "$LATEST_CONFIG" ]]; then
            sudo -u "$ADMIN_USER" aws s3 cp "s3://$S3_BUCKET/$LATEST_CONFIG" /tmp/config.tar.gz
            tar -xzvf /tmp/config.tar.gz -C "$L9_DIR"
            rm /tmp/config.tar.gz
        else
            error "No .env file found and no config backup in S3. Create .env manually."
        fi
    fi
    
    # Start containers
    log "Starting Docker containers..."
    cd "$L9_DIR"
    sudo -u "$ADMIN_USER" docker compose up -d
    
    # Wait for containers
    log "Waiting for containers to be healthy..."
    sleep 10
    sudo -u "$ADMIN_USER" docker compose ps
    
    log "✅ Phase 7 complete"
}

# =============================================================================
# PHASE 8: RESTORE MEMORY DATA
# =============================================================================

phase8_restore_data() {
    section "PHASE 8: Restore Memory Data"
    
    cd "$L9_DIR"
    
    # Check if restore script exists
    if [[ ! -f "$L9_DIR/scripts/backup/restore_l9_memory.sh" ]]; then
        warn "Restore script not found. Skipping data restore."
        return 0
    fi
    
    # Run restore
    log "Restoring PostgreSQL and Neo4j data from S3..."
    chmod +x "$L9_DIR/scripts/backup/restore_l9_memory.sh"
    sudo -u "$ADMIN_USER" "$L9_DIR/scripts/backup/restore_l9_memory.sh" latest --yes || warn "Restore failed or no backup found"
    
    log "✅ Phase 8 complete"
}

# =============================================================================
# PHASE 9: START SERVICES
# =============================================================================

phase9_start_services() {
    section "PHASE 9: Start Services"
    
    # Reload systemd
    systemctl daemon-reload
    
    # Start Caddy
    log "Starting Caddy..."
    systemctl enable caddy
    systemctl restart caddy || warn "Caddy start failed (check Caddyfile)"
    
    # Start L9 services if they exist
    for svc in l9 l9-agent l9-mcp; do
        if [[ -f "/etc/systemd/system/${svc}.service" ]]; then
            log "Starting $svc..."
            systemctl enable "$svc"
            systemctl restart "$svc" || warn "$svc start failed"
        fi
    done
    
    log "✅ Phase 9 complete"
}

# =============================================================================
# PHASE 10: VERIFICATION
# =============================================================================

phase10_verify() {
    section "PHASE 10: Verification"
    
    echo ""
    log "=== Docker Containers ==="
    docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
    
    echo ""
    log "=== Systemd Services ==="
    for svc in caddy l9 l9-agent l9-mcp; do
        if systemctl is-active --quiet "$svc" 2>/dev/null; then
            echo -e "  ${GREEN}✓${NC} $svc: running"
        else
            echo -e "  ${RED}✗${NC} $svc: not running"
        fi
    done
    
    echo ""
    log "=== Crontab ==="
    sudo -u "$ADMIN_USER" crontab -l 2>/dev/null || echo "  No crontab"
    
    echo ""
    log "=== Disk Usage ==="
    df -h "$L9_DIR"
    
    echo ""
    log "✅ Bootstrap complete!"
    echo ""
    echo "Next steps:"
    echo "  1. Verify .env file: cat $L9_DIR/.env"
    echo "  2. Check logs: docker compose logs -f"
    echo "  3. Test API: curl -s http://localhost:8000/health"
    echo ""
}

# =============================================================================
# MAIN
# =============================================================================

main() {
    echo ""
    echo "╔═══════════════════════════════════════════════════════════════╗"
    echo "║           L9 VPS Bootstrap Script v1.0.0                      ║"
    echo "╚═══════════════════════════════════════════════════════════════╝"
    echo ""
    
    # Check root
    if [[ $EUID -ne 0 ]]; then
        error "This script must be run as root (sudo)"
    fi
    
    phase1_system_setup
    phase2_docker
    phase3_caddy
    phase4_aws
    phase5_clone_repo
    phase6_restore_backup
    phase7_start_containers
    phase8_restore_data
    phase9_start_services
    phase10_verify
}

main "$@"
