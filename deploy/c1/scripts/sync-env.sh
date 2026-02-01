#!/bin/bash
# =============================================================================
# L9 Environment File Sync Script
# =============================================================================
# Syncs local .env files to C1 VPS before container builds.
#
# Usage:
#   ./sync-env.sh                    # Sync all env files
#   ./sync-env.sh --dry-run          # Show what would be synced
#   ./sync-env.sh --verify           # Verify env files on VPS
#
# This script:
#   1. Syncs root .env → /opt/l9/.env.production on VPS
#   2. Syncs module-specific .env files (mcp_memory, etc.)
#   3. Creates .env.production from template if needed
#   4. Validates required variables are set
#
# SECURITY:
#   - Uses SSH key authentication
#   - Files are chmod 600 on VPS
#   - Secrets never logged
# =============================================================================

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../../.." && pwd)"

# VPS Config
C1_IP="46.62.243.82"
SSH_KEY_FILE="$HOME/.ssh/Hetzner-C1"
VPS_L9_DIR="/opt/l9"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }
log_step() { echo -e "${CYAN}[STEP]${NC} ========== $1 =========="; }

# Options
DRY_RUN=false
VERIFY_ONLY=false

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        --verify)
            VERIFY_ONLY=true
            shift
            ;;
        --help)
            echo "Usage: $0 [--dry-run] [--verify]"
            echo ""
            echo "Options:"
            echo "  --dry-run    Show what would be synced without making changes"
            echo "  --verify     Verify env files exist on VPS"
            exit 0
            ;;
        *)
            log_error "Unknown option: $1"
            exit 1
            ;;
    esac
done

# =============================================================================
# ENV FILE MAPPINGS
# =============================================================================
# Format: "LOCAL_PATH:VPS_PATH"
# Local paths are relative to REPO_ROOT
# VPS paths are absolute
declare -a ENV_MAPPINGS=(
    ".env:$VPS_L9_DIR/.env.production"
    ".env.docker:$VPS_L9_DIR/.env.docker"
    ".env.vps:$VPS_L9_DIR/.env.vps"
    "mcp_memory/.env:$VPS_L9_DIR/mcp_memory/.env"
    "services/symbolic_computation/.env:$VPS_L9_DIR/services/symbolic_computation/.env"
)

# Required variables that MUST be set in .env.production
declare -a REQUIRED_VARS=(
    "OPENAI_API_KEY"
    "DATABASE_URL"
    "REDIS_URL"
    "NEO4J_URL"
    "NEO4J_PASSWORD"
)

# Optional but recommended variables
declare -a RECOMMENDED_VARS=(
    "SLACK_BOT_TOKEN"
    "SLACK_SIGNING_SECRET"
    "TWILIO_ACCOUNT_SID"
    "SENTRY_DSN"
)

# =============================================================================
# SSH Helper
# =============================================================================
ssh_cmd() {
    ssh -o StrictHostKeyChecking=no -o ConnectTimeout=10 -i "$SSH_KEY_FILE" root@"$C1_IP" "$@"
}

scp_cmd() {
    scp -o StrictHostKeyChecking=no -i "$SSH_KEY_FILE" "$@"
}

# =============================================================================
# PHASE 1: Verify Prerequisites
# =============================================================================
verify_prerequisites() {
    log_step "VERIFY PREREQUISITES"

    # Check SSH key exists
    if [[ ! -f "$SSH_KEY_FILE" ]]; then
        log_error "SSH key not found: $SSH_KEY_FILE"
        exit 1
    fi

    # Check we can connect to VPS
    log_info "Testing SSH connection to $C1_IP..."
    if ! ssh_cmd "echo 'SSH OK'" &>/dev/null; then
        log_error "Cannot connect to VPS at $C1_IP"
        exit 1
    fi

    log_success "Prerequisites verified"
}

# =============================================================================
# PHASE 2: Discover Local Env Files
# =============================================================================
discover_env_files() {
    log_step "DISCOVER LOCAL ENV FILES"

    log_info "Scanning for .env files in $REPO_ROOT..."

    local found_files=()

    # Check each mapping
    for mapping in "${ENV_MAPPINGS[@]}"; do
        local local_path="${mapping%%:*}"
        local vps_path="${mapping##*:}"
        local full_local="$REPO_ROOT/$local_path"

        if [[ -f "$full_local" ]]; then
            found_files+=("$local_path")
            log_info "  ✓ Found: $local_path"
        else
            log_warn "  ✗ Missing: $local_path"
        fi
    done

    # Discover any additional .env files not in mappings
    log_info "Scanning for additional .env files..."
    while IFS= read -r -d '' file; do
        local rel_path="${file#$REPO_ROOT/}"
        local already_mapped=false

        for mapping in "${ENV_MAPPINGS[@]}"; do
            local mapped_path="${mapping%%:*}"
            if [[ "$rel_path" == "$mapped_path" ]]; then
                already_mapped=true
                break
            fi
        done

        if ! $already_mapped; then
            log_warn "  ! Unmapped: $rel_path (add to ENV_MAPPINGS if needed)"
        fi
    done < <(find "$REPO_ROOT" -name ".env" -o -name ".env.*" -type f -print0 2>/dev/null | grep -zv "node_modules" | grep -zv ".git")

    log_success "Discovery complete: ${#found_files[@]} files found"
}

# =============================================================================
# PHASE 3: Create VPS Directories
# =============================================================================
create_vps_directories() {
    log_step "CREATE VPS DIRECTORIES"

    if $DRY_RUN; then
        log_info "[DRY RUN] Would create directories on VPS"
        return
    fi

    log_info "Creating directory structure on VPS..."

    ssh_cmd bash << 'REMOTE_SCRIPT'
set -e
mkdir -p /opt/l9
mkdir -p /opt/l9/mcp_memory
mkdir -p /opt/l9/services/symbolic_computation
mkdir -p /opt/l9/config
chmod 700 /opt/l9
echo "Directories created"
REMOTE_SCRIPT

    log_success "VPS directories ready"
}

# =============================================================================
# PHASE 4: Sync Env Files
# =============================================================================
sync_env_files() {
    log_step "SYNC ENV FILES TO VPS"

    local synced=0
    local skipped=0
    local failed=0

    for mapping in "${ENV_MAPPINGS[@]}"; do
        local local_path="${mapping%%:*}"
        local vps_path="${mapping##*:}"
        local full_local="$REPO_ROOT/$local_path"

        if [[ ! -f "$full_local" ]]; then
            log_warn "Skipping $local_path (file not found)"
            ((skipped++))
            continue
        fi

        log_info "Syncing: $local_path → $vps_path"

        if $DRY_RUN; then
            log_info "  [DRY RUN] Would copy $local_path"
            ((synced++))
            continue
        fi

        # Create parent directory on VPS
        local vps_dir=$(dirname "$vps_path")
        ssh_cmd "mkdir -p '$vps_dir'"

        # Copy file
        if scp_cmd "$full_local" "root@$C1_IP:$vps_path"; then
            # Set secure permissions
            ssh_cmd "chmod 600 '$vps_path'"
            log_success "  ✓ Synced: $local_path"
            ((synced++))
        else
            log_error "  ✗ Failed: $local_path"
            ((failed++))
        fi
    done

    echo ""
    log_info "Sync summary: $synced synced, $skipped skipped, $failed failed"

    if [[ $failed -gt 0 ]]; then
        log_error "Some files failed to sync!"
        return 1
    fi

    log_success "Env files synced"
}

# =============================================================================
# PHASE 5: Validate Required Variables
# =============================================================================
validate_env_vars() {
    log_step "VALIDATE REQUIRED VARIABLES"

    if $DRY_RUN; then
        log_info "[DRY RUN] Would validate variables on VPS"
        return
    fi

    log_info "Checking required variables in .env.production..."

    local missing_required=()
    local missing_recommended=()

    # Check required vars
    for var in "${REQUIRED_VARS[@]}"; do
        if ssh_cmd "grep -q '^${var}=' '$VPS_L9_DIR/.env.production' 2>/dev/null"; then
            log_info "  ✓ $var"
        else
            missing_required+=("$var")
            log_error "  ✗ $var (REQUIRED)"
        fi
    done

    # Check recommended vars
    for var in "${RECOMMENDED_VARS[@]}"; do
        if ssh_cmd "grep -q '^${var}=' '$VPS_L9_DIR/.env.production' 2>/dev/null"; then
            log_info "  ✓ $var"
        else
            missing_recommended+=("$var")
            log_warn "  ? $var (recommended)"
        fi
    done

    echo ""

    if [[ ${#missing_required[@]} -gt 0 ]]; then
        log_error "Missing REQUIRED variables: ${missing_required[*]}"
        log_error "Add these to your local .env before deploying!"
        return 1
    fi

    if [[ ${#missing_recommended[@]} -gt 0 ]]; then
        log_warn "Missing recommended variables: ${missing_recommended[*]}"
        log_warn "Some features may be disabled."
    fi

    log_success "Validation passed"
}

# =============================================================================
# PHASE 6: Create Docker Env Symlinks
# =============================================================================
create_docker_symlinks() {
    log_step "CREATE DOCKER ENV SYMLINKS"

    if $DRY_RUN; then
        log_info "[DRY RUN] Would create symlinks on VPS"
        return
    fi

    log_info "Creating symlinks for Docker containers..."

    ssh_cmd bash << 'REMOTE_SCRIPT'
set -e

# Main .env for docker-compose
if [[ -f /opt/l9/.env.production ]]; then
    ln -sf /opt/l9/.env.production /opt/l9/.env
    echo "Created: /opt/l9/.env → .env.production"
fi

# MCP Memory .env
if [[ -f /opt/l9/mcp_memory/.env ]]; then
    echo "MCP Memory .env ready"
fi

# List all env files
echo ""
echo "=== ENV FILES ON VPS ==="
find /opt/l9 -name ".env*" -type f 2>/dev/null | while read f; do
    echo "  $f ($(stat -c %a $f 2>/dev/null || stat -f %p $f 2>/dev/null) permissions)"
done
REMOTE_SCRIPT

    log_success "Symlinks created"
}

# =============================================================================
# PHASE 7: Verify on VPS
# =============================================================================
verify_on_vps() {
    log_step "VERIFY ENV FILES ON VPS"

    log_info "Listing env files on VPS..."

    ssh_cmd bash << 'REMOTE_SCRIPT'
echo "=== /opt/l9 ENV FILES ==="
find /opt/l9 -name ".env*" -type f 2>/dev/null | while read f; do
    lines=$(wc -l < "$f")
    perms=$(stat -c %a "$f" 2>/dev/null || stat -f %OLp "$f" 2>/dev/null)
    echo "  $f ($lines lines, mode $perms)"
done

echo ""
echo "=== VARIABLE COUNT PER FILE ==="
for f in /opt/l9/.env.production /opt/l9/mcp_memory/.env; do
    if [[ -f "$f" ]]; then
        vars=$(grep -c "^[A-Z]" "$f" 2>/dev/null || echo 0)
        echo "  $f: $vars variables"
    fi
done
REMOTE_SCRIPT

    log_success "Verification complete"
}

# =============================================================================
# MAIN
# =============================================================================
main() {
    echo ""
    echo "============================================="
    echo "   L9 Environment Sync"
    echo "   Target: $C1_IP"
    echo "============================================="
    echo ""

    if $DRY_RUN; then
        log_warn "DRY RUN MODE - No changes will be made"
        echo ""
    fi

    if $VERIFY_ONLY; then
        verify_prerequisites
        verify_on_vps
        exit 0
    fi

    verify_prerequisites
    discover_env_files
    create_vps_directories
    sync_env_files
    validate_env_vars
    create_docker_symlinks
    verify_on_vps

    echo ""
    echo "============================================="
    echo -e "${GREEN}   ENV SYNC COMPLETE${NC}"
    echo "============================================="
    echo ""
    echo "Env files synced to: $C1_IP:$VPS_L9_DIR/"
    echo ""
    echo "Next: Run container build with:"
    echo "  ./build-images.sh"
    echo ""
}

main "$@"
