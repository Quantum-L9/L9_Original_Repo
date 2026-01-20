#!/usr/bin/env bash
# =============================================================================
# L9 One-Click VPS Deployment
# Version: 1.0.0
#
# Provisions a new Hetzner VPS and fully configures it with L9.
# Run from your Mac - handles everything automatically.
#
# Usage:
#   ./scripts/infra/deploy_new_vps.sh
#   ./scripts/infra/deploy_new_vps.sh --destroy  # Tear down
#
# GOVERNANCE: IGOR_ONLY
# =============================================================================

set -euo pipefail

# =============================================================================
# CONFIGURATION
# =============================================================================

# Hetzner
HCLOUD_TOKEN="${HCLOUD_TOKEN:-Wt3rc9BWLbs19H2sS2enFRRYBFzMQWX2ndSWV4hv6xIFSTYr3zA8IjD8vBMCnz8p}"
SSH_KEY_NAME="${SSH_KEY_NAME:-Hetzner-L9}"
SERVER_NAME="${SERVER_NAME:-l9-vps}"
SERVER_TYPE="${SERVER_TYPE:-cx21}"  # 2 vCPU, 4GB RAM, €4.85/mo
LOCATION="${LOCATION:-nbg1}"        # Nuremberg

# L9
L9_REPO="${L9_REPO:-https://github.com/cryptoxdog/L9}"
L9_BRANCH="${L9_BRANCH:-main}"
L9_DIR="/opt/l9"
ADMIN_USER="admin"

# AWS (for S3 backups)
AWS_ACCESS_KEY="${AWS_ACCESS_KEY:-AKIAQJL4O6D4JOYGSMPB}"
AWS_SECRET_KEY="${AWS_SECRET_KEY:-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}"
AWS_REGION="${AWS_REGION:-us-east-1}"
S3_BUCKET="${S3_BUCKET:-l9-backups}"

# Paths
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TERRAFORM_DIR="$SCRIPT_DIR/terraform"

# =============================================================================
# COLORS
# =============================================================================

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

log() { echo -e "${GREEN}[$(date '+%H:%M:%S')]${NC} $1"; }
warn() { echo -e "${YELLOW}[$(date '+%H:%M:%S')] WARNING:${NC} $1"; }
error() { echo -e "${RED}[$(date '+%H:%M:%S')] ERROR:${NC} $1"; exit 1; }
section() { echo -e "\n${BLUE}══════════════════════════════════════════════════════════════${NC}"; echo -e "${CYAN}  $1${NC}"; echo -e "${BLUE}══════════════════════════════════════════════════════════════${NC}\n"; }

# =============================================================================
# PREREQUISITES CHECK
# =============================================================================

check_prerequisites() {
    section "Checking Prerequisites"
    
    local missing=()
    
    # Check Terraform
    if ! command -v terraform &> /dev/null; then
        missing+=("terraform (brew install terraform)")
    else
        log "✓ Terraform: $(terraform version -json | jq -r '.terraform_version')"
    fi
    
    # Check SSH key
    if [[ ! -f ~/.ssh/id_ed25519 && ! -f ~/.ssh/id_rsa ]]; then
        missing+=("SSH key (~/.ssh/id_ed25519 or ~/.ssh/id_rsa)")
    else
        log "✓ SSH key found"
    fi
    
    # Check jq
    if ! command -v jq &> /dev/null; then
        missing+=("jq (brew install jq)")
    else
        log "✓ jq installed"
    fi
    
    # Check hcloud CLI (optional but useful)
    if command -v hcloud &> /dev/null; then
        log "✓ hcloud CLI installed"
    else
        warn "hcloud CLI not installed (optional: brew install hcloud)"
    fi
    
    if [[ ${#missing[@]} -gt 0 ]]; then
        error "Missing prerequisites:\n  - ${missing[*]}"
    fi
    
    log "✓ All prerequisites met"
}

# =============================================================================
# TERRAFORM PROVISIONING
# =============================================================================

provision_server() {
    section "Provisioning Hetzner VPS"
    
    cd "$TERRAFORM_DIR"
    
    # Export token for Terraform
    export HCLOUD_TOKEN
    
    # Create tfvars
    cat > terraform.tfvars << EOF
server_name  = "$SERVER_NAME"
server_type  = "$SERVER_TYPE"
region       = "$LOCATION"
ssh_key_name = "$SSH_KEY_NAME"
EOF
    
    log "Terraform config:"
    cat terraform.tfvars
    echo ""
    
    # Initialize Terraform
    log "Initializing Terraform..."
    terraform init -upgrade
    
    # Plan
    log "Planning infrastructure..."
    terraform plan -out=tfplan
    
    # Apply
    log "Applying infrastructure..."
    terraform apply tfplan
    
    # Get IP
    SERVER_IP=$(terraform output -raw server_ip)
    log "✓ Server provisioned: $SERVER_IP"
    
    # Save IP for later
    echo "$SERVER_IP" > "$SCRIPT_DIR/.last_server_ip"
    
    cd - > /dev/null
}

# =============================================================================
# WAIT FOR SERVER
# =============================================================================

wait_for_server() {
    section "Waiting for Server to be Ready"
    
    local ip="$1"
    local max_attempts=30
    local attempt=1
    
    log "Waiting for SSH on $ip..."
    
    while [[ $attempt -le $max_attempts ]]; do
        if ssh -o ConnectTimeout=5 -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null "root@$ip" "echo ready" 2>/dev/null; then
            log "✓ SSH is ready"
            return 0
        fi
        echo -n "."
        sleep 10
        ((attempt++))
    done
    
    error "Server not ready after ${max_attempts} attempts"
}

# =============================================================================
# BOOTSTRAP SERVER
# =============================================================================

bootstrap_server() {
    section "Bootstrapping Server"
    
    local ip="$1"
    
    log "Running bootstrap on $ip..."
    
    # Copy bootstrap script
    scp -o StrictHostKeyChecking=no "$SCRIPT_DIR/bootstrap_vps.sh" "root@$ip:/tmp/"
    
    # Run bootstrap with all variables
    ssh -o StrictHostKeyChecking=no "root@$ip" << EOF
export L9_REPO="$L9_REPO"
export L9_BRANCH="$L9_BRANCH"
export ADMIN_USER="$ADMIN_USER"
export AWS_ACCESS_KEY="$AWS_ACCESS_KEY"
export AWS_SECRET_KEY="$AWS_SECRET_KEY"
export AWS_REGION="$AWS_REGION"
export S3_BUCKET="$S3_BUCKET"

chmod +x /tmp/bootstrap_vps.sh
/tmp/bootstrap_vps.sh
EOF
    
    log "✓ Bootstrap complete"
}

# =============================================================================
# VERIFY DEPLOYMENT
# =============================================================================

verify_deployment() {
    section "Verifying Deployment"
    
    local ip="$1"
    
    log "Checking services on $ip..."
    
    # Check Docker containers
    echo ""
    log "Docker containers:"
    ssh -o StrictHostKeyChecking=no "admin@$ip" "docker ps --format 'table {{.Names}}\t{{.Status}}'" || true
    
    # Check systemd services
    echo ""
    log "Systemd services:"
    for svc in caddy l9 l9-agent l9-mcp; do
        if ssh -o StrictHostKeyChecking=no "admin@$ip" "systemctl is-active $svc" 2>/dev/null | grep -q "active"; then
            echo -e "  ${GREEN}✓${NC} $svc: running"
        else
            echo -e "  ${YELLOW}○${NC} $svc: not running (may be expected)"
        fi
    done
    
    # Check API health
    echo ""
    log "API health check:"
    if ssh -o StrictHostKeyChecking=no "admin@$ip" "curl -s http://localhost:8000/health" 2>/dev/null | grep -q "ok\|healthy"; then
        echo -e "  ${GREEN}✓${NC} API is healthy"
    else
        echo -e "  ${YELLOW}○${NC} API not responding (check docker logs)"
    fi
    
    # Check crontab
    echo ""
    log "Crontab:"
    ssh -o StrictHostKeyChecking=no "admin@$ip" "crontab -l" 2>/dev/null || echo "  No crontab"
}

# =============================================================================
# DESTROY
# =============================================================================

destroy_server() {
    section "Destroying Server"
    
    cd "$TERRAFORM_DIR"
    export HCLOUD_TOKEN
    
    read -p "Are you sure you want to destroy the server? (yes/no): " confirm
    if [[ "$confirm" != "yes" ]]; then
        log "Aborted"
        exit 0
    fi
    
    terraform destroy -auto-approve
    
    log "✓ Server destroyed"
    rm -f "$SCRIPT_DIR/.last_server_ip"
}

# =============================================================================
# MAIN
# =============================================================================

main() {
    echo ""
    echo "╔═══════════════════════════════════════════════════════════════╗"
    echo "║         L9 One-Click VPS Deployment v1.0.0                    ║"
    echo "╚═══════════════════════════════════════════════════════════════╝"
    echo ""
    
    # Handle --destroy flag
    if [[ "${1:-}" == "--destroy" ]]; then
        destroy_server
        exit 0
    fi
    
    # Check prerequisites
    check_prerequisites
    
    # Provision server
    provision_server
    
    # Get IP
    SERVER_IP=$(cat "$SCRIPT_DIR/.last_server_ip")
    
    # Wait for server
    wait_for_server "$SERVER_IP"
    
    # Bootstrap
    bootstrap_server "$SERVER_IP"
    
    # Verify
    verify_deployment "$SERVER_IP"
    
    # Summary
    section "Deployment Complete!"
    
    echo -e "${GREEN}Server IP:${NC} $SERVER_IP"
    echo -e "${GREEN}SSH:${NC} ssh admin@$SERVER_IP"
    echo -e "${GREEN}API:${NC} http://$SERVER_IP:8000"
    echo ""
    echo "Next steps:"
    echo "  1. Update DNS to point to $SERVER_IP"
    echo "  2. Verify Caddy HTTPS is working"
    echo "  3. Test: curl https://your-domain.com/health"
    echo ""
    echo "To destroy: ./scripts/infra/deploy_new_vps.sh --destroy"
    echo ""
}

main "$@"
