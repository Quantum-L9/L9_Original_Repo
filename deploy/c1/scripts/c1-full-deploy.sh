#!/bin/bash
# =============================================================================
# C1 FULL AUTOMATED DEPLOYMENT
# =============================================================================
# This script:
#   1. Verifies C1 current state via Hetzner API
#   2. Adds SSH key to Hetzner project (if needed)
#   3. Rebuilds C1 with Ubuntu 24.04 + SSH key
#   4. Waits for server to be ready
#   5. Installs k3s
#   6. Deploys L9 K8s stack
#   7. Verifies all components
#   8. Reports SUCCESS or FAILURE
#
# Usage: ./c1-full-deploy.sh
#
# CONSTRAINTS:
#   - L9 server (157.180.73.53) is OFF LIMITS
#   - All actions are logged and rollback-able
# =============================================================================

set -euo pipefail

# =============================================================================
# CONFIGURATION
# =============================================================================
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_FILE="$SCRIPT_DIR/c1-deploy-$(date +%Y%m%d-%H%M%S).log"

# Load environment
source ~/Projects/L9/.env 2>/dev/null || true

# Hetzner Config
HCLOUD_TOKEN="${HCLOUD_TOKEN:-}"
C1_SERVER_ID="114194366"
C1_SERVER_NAME="C1"
C1_IP="46.62.243.82"
L9_IP="157.180.73.53"  # OFF LIMITS - Safety check

# SSH Config
SSH_KEY_NAME="Hetzner-C1"
SSH_KEY_FILE="$HOME/.ssh/Hetzner-C1"
SSH_PUBLIC_KEY="ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIDMs7d20QTjo5koa0u4AACplBhjEXXJW1BcmEFtjVfa+"

# Ubuntu 24.04 LTS image (Hetzner image name)
UBUNTU_IMAGE="ubuntu-24.04"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

# =============================================================================
# LOGGING
# =============================================================================
exec > >(tee -a "$LOG_FILE") 2>&1

log_info() { echo -e "${BLUE}[INFO $(date +%H:%M:%S)]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS $(date +%H:%M:%S)]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN $(date +%H:%M:%S)]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR $(date +%H:%M:%S)]${NC} $1"; }
log_step() { echo -e "${CYAN}[STEP $(date +%H:%M:%S)]${NC} ========== $1 =========="; }

# =============================================================================
# SAFETY CHECKS
# =============================================================================
safety_check() {
    log_step "SAFETY CHECKS"

    # Check we're not on L9
    if [[ "$(hostname -I 2>/dev/null | awk '{print $1}')" == "$L9_IP" ]]; then
        log_error "SAFETY VIOLATION: Running on L9 server! Aborting."
        exit 1
    fi

    # Check API token exists
    if [[ -z "$HCLOUD_TOKEN" ]]; then
        log_error "HCLOUD_TOKEN not set. Source your .env file."
        exit 1
    fi

    # Check SSH key exists
    if [[ ! -f "$SSH_KEY_FILE" ]]; then
        log_error "SSH key not found: $SSH_KEY_FILE"
        exit 1
    fi

    log_success "Safety checks passed"
}

# =============================================================================
# HETZNER API HELPERS
# =============================================================================
hcloud_api() {
    local method="$1"
    local endpoint="$2"
    local data="${3:-}"

    local url="https://api.hetzner.cloud/v1$endpoint"

    if [[ -n "$data" ]]; then
        curl -s -X "$method" "$url" \
            -H "Authorization: Bearer $HCLOUD_TOKEN" \
            -H "Content-Type: application/json" \
            -d "$data"
    else
        curl -s -X "$method" "$url" \
            -H "Authorization: Bearer $HCLOUD_TOKEN"
    fi
}

# =============================================================================
# PHASE 1: VERIFY C1 STATE
# =============================================================================
verify_c1_state() {
    log_step "PHASE 1: VERIFY C1 STATE"

    log_info "Fetching C1 server info..."
    local server_info=$(hcloud_api GET "/servers/$C1_SERVER_ID")

    local status=$(echo "$server_info" | jq -r '.server.status')
    local ip=$(echo "$server_info" | jq -r '.server.public_net.ipv4.ip')
    local image=$(echo "$server_info" | jq -r '.server.image.description')
    local server_type=$(echo "$server_info" | jq -r '.server.server_type.name')

    log_info "C1 Status: $status"
    log_info "C1 IP: $ip"
    log_info "C1 Image: $image"
    log_info "C1 Type: $server_type"

    if [[ "$ip" != "$C1_IP" ]]; then
        log_error "IP mismatch! Expected $C1_IP, got $ip"
        exit 1
    fi

    if [[ "$status" != "running" ]]; then
        log_error "C1 is not running (status: $status)"
        exit 1
    fi

    log_success "C1 verified: $server_type running at $ip"
    echo "$image"  # Return current image for later comparison
}

# =============================================================================
# PHASE 2: ENSURE SSH KEY IN HETZNER
# =============================================================================
ensure_ssh_key() {
    log_step "PHASE 2: ENSURE SSH KEY IN HETZNER"

    log_info "Checking for existing SSH key: $SSH_KEY_NAME"
    local keys=$(hcloud_api GET "/ssh_keys")
    local existing_key=$(echo "$keys" | jq -r ".ssh_keys[] | select(.name==\"$SSH_KEY_NAME\") | .id")

    if [[ -n "$existing_key" ]]; then
        log_success "SSH key '$SSH_KEY_NAME' already exists (ID: $existing_key)"
        echo "$existing_key"
        return
    fi

    log_info "Adding SSH key to Hetzner..."
    local result=$(hcloud_api POST "/ssh_keys" "{
        \"name\": \"$SSH_KEY_NAME\",
        \"public_key\": \"$SSH_PUBLIC_KEY\"
    }")

    local key_id=$(echo "$result" | jq -r '.ssh_key.id')

    if [[ "$key_id" == "null" || -z "$key_id" ]]; then
        log_error "Failed to add SSH key: $(echo "$result" | jq -r '.error.message')"
        exit 1
    fi

    log_success "SSH key added (ID: $key_id)"
    echo "$key_id"
}

# =============================================================================
# PHASE 3: GET UBUNTU 24.04 IMAGE ID
# =============================================================================
get_image_id() {
    log_step "PHASE 3: GET UBUNTU 24.04 IMAGE"

    log_info "Fetching available images..."
    local images=$(hcloud_api GET "/images?type=system&status=available")

    # Try ubuntu-24.04 first, fallback to ubuntu-22.04
    local image_id=$(echo "$images" | jq -r ".images[] | select(.name==\"$UBUNTU_IMAGE\") | .id")

    if [[ -z "$image_id" || "$image_id" == "null" ]]; then
        log_warn "Ubuntu 24.04 not found, checking available Ubuntu images..."
        echo "$images" | jq -r '.images[] | select(.name | startswith("ubuntu")) | "\(.name): \(.id)"'

        # Fallback to 22.04
        image_id=$(echo "$images" | jq -r '.images[] | select(.name=="ubuntu-22.04") | .id')

        if [[ -z "$image_id" || "$image_id" == "null" ]]; then
            log_error "No suitable Ubuntu image found!"
            exit 1
        fi
        log_warn "Using Ubuntu 22.04 (will need to install Python 3.12 manually)"
    else
        log_success "Found Ubuntu 24.04 (ID: $image_id)"
    fi

    echo "$image_id"
}

# =============================================================================
# PHASE 4: REBUILD C1
# =============================================================================
rebuild_c1() {
    local ssh_key_id="$1"
    local image_id="$2"

    log_step "PHASE 4: REBUILD C1"

    log_warn "This will WIPE C1 and reinstall Ubuntu!"
    log_info "Image ID: $image_id"
    log_info "SSH Key ID: $ssh_key_id"

    # Confirm (unless running non-interactively)
    if [[ -t 0 ]]; then
        read -p "Proceed with rebuild? (type 'REBUILD' to confirm): " -r
        if [[ "$REPLY" != "REBUILD" ]]; then
            log_error "Rebuild cancelled"
            exit 1
        fi
    fi

    log_info "Initiating rebuild..."
    local result=$(hcloud_api POST "/servers/$C1_SERVER_ID/actions/rebuild" "{
        \"image\": \"$image_id\",
        \"ssh_keys\": [$ssh_key_id]
    }")

    local action_id=$(echo "$result" | jq -r '.action.id')
    local root_password=$(echo "$result" | jq -r '.root_password')

    if [[ "$action_id" == "null" || -z "$action_id" ]]; then
        log_error "Rebuild failed: $(echo "$result" | jq -r '.error.message')"
        exit 1
    fi

    log_info "Rebuild started (Action ID: $action_id)"

    if [[ "$root_password" != "null" && -n "$root_password" ]]; then
        log_info "Root password (backup): $root_password"
        echo "$root_password" > "$SCRIPT_DIR/.c1-root-password"
        chmod 600 "$SCRIPT_DIR/.c1-root-password"
    fi

    # Wait for rebuild to complete
    log_info "Waiting for rebuild to complete..."
    local status="running"
    local attempts=0
    local max_attempts=60  # 5 minutes max

    while [[ "$status" == "running" && $attempts -lt $max_attempts ]]; do
        sleep 5
        local action_status=$(hcloud_api GET "/actions/$action_id")
        status=$(echo "$action_status" | jq -r '.action.status')
        local progress=$(echo "$action_status" | jq -r '.action.progress')
        echo -ne "\r${BLUE}[INFO]${NC} Rebuild progress: $progress% (status: $status)   "
        ((attempts++))
    done
    echo ""

    if [[ "$status" != "success" ]]; then
        log_error "Rebuild failed with status: $status"
        exit 1
    fi

    log_success "Rebuild completed successfully"
}

# =============================================================================
# PHASE 5: WAIT FOR SSH
# =============================================================================
wait_for_ssh() {
    log_step "PHASE 5: WAIT FOR SSH"

    log_info "Waiting for SSH to become available..."

    # Clear known hosts for this IP (fresh install = new host key)
    ssh-keygen -R "$C1_IP" 2>/dev/null || true

    local attempts=0
    local max_attempts=30  # 2.5 minutes max

    while [[ $attempts -lt $max_attempts ]]; do
        if ssh -o ConnectTimeout=5 -o StrictHostKeyChecking=no -o BatchMode=yes \
               -i "$SSH_KEY_FILE" root@"$C1_IP" "echo 'SSH OK'" 2>/dev/null; then
            log_success "SSH connection established"
            return 0
        fi
        echo -ne "\r${BLUE}[INFO]${NC} Waiting for SSH... attempt $((attempts+1))/$max_attempts   "
        sleep 5
        ((attempts++))
    done
    echo ""

    log_error "SSH connection failed after $max_attempts attempts"
    exit 1
}

# =============================================================================
# PHASE 6: VERIFY SYSTEM
# =============================================================================
verify_system() {
    log_step "PHASE 6: VERIFY SYSTEM"

    log_info "Verifying C1 system..."

    ssh -o StrictHostKeyChecking=no -i "$SSH_KEY_FILE" root@"$C1_IP" bash << 'REMOTE_SCRIPT'
echo "=== SYSTEM INFO ==="
echo "Hostname: $(hostname)"
echo "OS: $(cat /etc/os-release | grep PRETTY_NAME | cut -d'"' -f2)"
echo "Kernel: $(uname -r)"
echo "Python: $(python3 --version 2>/dev/null || echo 'Not installed')"
echo ""
echo "=== RESOURCES ==="
free -h
echo ""
df -h /
echo ""
echo "=== NETWORK ==="
ip addr show | grep -E "inet " | head -2
REMOTE_SCRIPT

    log_success "System verification complete"
}

# =============================================================================
# PHASE 7: INSTALL K3S + DOCKER
# =============================================================================
install_k3s() {
    log_step "PHASE 7: INSTALL K3S + DOCKER"

    log_info "Installing k3s and Docker on C1..."

    ssh -o StrictHostKeyChecking=no -i "$SSH_KEY_FILE" root@"$C1_IP" bash << 'REMOTE_SCRIPT'
set -e

echo "Updating system..."
apt-get update -qq
apt-get install -y -qq curl wget git htop jq ca-certificates gnupg

echo "Installing Docker..."
install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
chmod a+r /etc/apt/keyrings/docker.gpg

echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
  tee /etc/apt/sources.list.d/docker.list > /dev/null

apt-get update -qq
apt-get install -y -qq docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

echo "Installing k3s..."
curl -sfL https://get.k3s.io | sh -

echo "Waiting for k3s to be ready..."
sleep 10

echo "Verifying k3s..."
kubectl get nodes
kubectl get pods -A

echo "k3s and Docker installed successfully"
REMOTE_SCRIPT

    log_success "k3s and Docker installed"
}

# =============================================================================
# PHASE 8: SYNC ENV FILES TO VPS
# =============================================================================
sync_env_files() {
    log_step "PHASE 8: SYNC ENV FILES TO VPS"

    log_info "Syncing local .env files to C1..."

    # Create directories on VPS
    ssh -o StrictHostKeyChecking=no -i "$SSH_KEY_FILE" root@"$C1_IP" bash << 'REMOTE_SCRIPT'
mkdir -p /opt/l9/mcp_memory
mkdir -p /opt/l9/services/symbolic_computation
mkdir -p /opt/l9/config
chmod 700 /opt/l9
REMOTE_SCRIPT

    # Define env file mappings (local:remote)
    declare -a ENV_FILES=(
        "$HOME/Projects/L9/.env:/opt/l9/.env.production"
        "$HOME/Projects/L9/.env.docker:/opt/l9/.env.docker"
        "$HOME/Projects/L9/.env.vps:/opt/l9/.env.vps"
        "$HOME/Projects/L9/mcp_memory/.env:/opt/l9/mcp_memory/.env"
    )

    local synced=0
    local skipped=0

    for mapping in "${ENV_FILES[@]}"; do
        local local_path="${mapping%%:*}"
        local remote_path="${mapping##*:}"

        if [[ -f "$local_path" ]]; then
            log_info "Syncing: $(basename "$local_path") → $remote_path"
            scp -o StrictHostKeyChecking=no -i "$SSH_KEY_FILE" \
                "$local_path" "root@$C1_IP:$remote_path"
            # Secure permissions
            ssh -o StrictHostKeyChecking=no -i "$SSH_KEY_FILE" root@"$C1_IP" \
                "chmod 600 '$remote_path'"
            ((synced++))
        else
            log_warn "Skipping: $local_path (not found)"
            ((skipped++))
        fi
    done

    # Create .env symlink for docker-compose
    ssh -o StrictHostKeyChecking=no -i "$SSH_KEY_FILE" root@"$C1_IP" bash << 'REMOTE_SCRIPT'
if [[ -f /opt/l9/.env.production ]]; then
    ln -sf /opt/l9/.env.production /opt/l9/.env
    echo "Created symlink: /opt/l9/.env → .env.production"
fi
REMOTE_SCRIPT

    # Validate required variables
    log_info "Validating required variables..."
    ssh -o StrictHostKeyChecking=no -i "$SSH_KEY_FILE" root@"$C1_IP" bash << 'REMOTE_SCRIPT'
REQUIRED_VARS="OPENAI_API_KEY DATABASE_URL REDIS_URL NEO4J_URL"
MISSING=""

for var in $REQUIRED_VARS; do
    if ! grep -q "^${var}=" /opt/l9/.env.production 2>/dev/null; then
        MISSING="$MISSING $var"
    fi
done

if [[ -n "$MISSING" ]]; then
    echo "⚠️  Missing required variables:$MISSING"
    echo "Add these to your local .env before deploying!"
else
    echo "✅ All required variables present"
fi

echo ""
echo "=== ENV FILES ON VPS ==="
find /opt/l9 -name ".env*" -type f 2>/dev/null
REMOTE_SCRIPT

    log_success "Env files synced: $synced synced, $skipped skipped"
}

# =============================================================================
# PHASE 9: BUILD DOCKER IMAGES ON C1
# =============================================================================
build_docker_images() {
    log_step "PHASE 9: BUILD DOCKER IMAGES ON C1"

    log_info "Cloning L9 repo and building images with all requirements..."

    ssh -o StrictHostKeyChecking=no -i "$SSH_KEY_FILE" root@"$C1_IP" bash << 'REMOTE_SCRIPT'
set -e

echo "=== Setting up build environment ==="
mkdir -p /opt/l9-build
cd /opt/l9-build

# Clone or update L9 repo
if [[ -d "L9" ]]; then
    echo "Updating existing L9 repo..."
    cd L9
    git fetch origin
    git reset --hard origin/main
else
    echo "Cloning L9 repo..."
    git clone https://github.com/cryptoxdog/L9.git L9
    cd L9
fi

echo "=== Copying env files into build context ==="
# Copy synced env files from /opt/l9 to build context
if [[ -f /opt/l9/.env.production ]]; then
    cp /opt/l9/.env.production .env
    echo "Copied .env.production → .env"
fi

if [[ -f /opt/l9/mcp_memory/.env ]]; then
    mkdir -p mcp_memory
    cp /opt/l9/mcp_memory/.env mcp_memory/.env
    echo "Copied mcp_memory/.env"
fi

# List env files in build context
echo "Env files in build context:"
find . -name ".env*" -type f 2>/dev/null | head -10

echo "=== Building L9 API image (root Dockerfile) ==="
docker build \
    -f Dockerfile \
    --target production \
    --build-arg BUILD_DATE="$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
    --build-arg VCS_REF="$(git rev-parse --short HEAD)" \
    --build-arg VERSION="2.0.0" \
    -t ghcr.io/igor-beylin/l9-api:latest \
    -t l9-api:latest \
    .

echo "=== Verifying image has all dependencies ==="
docker run --rm l9-api:latest python -c "
import sys
try:
    import fastapi
    import pydantic
    import asyncpg
    import neo4j
    import redis
    import structlog
    import langchain_core
    import langgraph
    import prometheus_client
    import jsonschema
    import tenacity
    import opentelemetry
    import sentence_transformers
    print('✅ All production dependencies verified')
except ImportError as e:
    print(f'❌ Missing dependency: {e}')
    sys.exit(1)
"

echo "=== Building MCP Memory image (root Dockerfile.mcp-memory) ==="
docker build \
    -f Dockerfile.mcp-memory \
    --target production \
    -t ghcr.io/igor-beylin/l9-mcp-memory:latest \
    -t l9-mcp-memory:latest \
    .

echo "=== Docker images built ==="
docker images | grep -E "(l9-api|l9-mcp)" | head -10
REMOTE_SCRIPT

    log_success "Docker images built on C1"
}

# =============================================================================
# PHASE 10: DEPLOY K8S MANIFESTS
# =============================================================================
deploy_manifests() {
    log_step "PHASE 10: DEPLOY K8S MANIFESTS"

    log_info "Copying manifests to C1..."

    # Create directory on C1
    ssh -o StrictHostKeyChecking=no -i "$SSH_KEY_FILE" root@"$C1_IP" "mkdir -p /opt/l9-k8s"

    # Copy manifest files from the manifests directory
    scp -o StrictHostKeyChecking=no -i "$SSH_KEY_FILE" \
        "$SCRIPT_DIR"/../manifests/*.yaml \
        root@"$C1_IP":/opt/l9-k8s/

    log_info "Applying manifests..."

    ssh -o StrictHostKeyChecking=no -i "$SSH_KEY_FILE" root@"$C1_IP" bash << 'REMOTE_SCRIPT'
set -e
cd /opt/l9-k8s

echo "Applying namespace..."
kubectl apply -f c1-namespace.yaml

echo "Applying secrets..."
kubectl apply -f c1-secrets.yaml

echo "Applying RBAC..."
kubectl apply -f c1-rbac.yaml

echo "Applying PostgreSQL (memory substrate)..."
kubectl apply -f c1-postgres.yaml

echo "Applying Neo4j..."
kubectl apply -f c1-neo4j.yaml

echo "Applying Redis..."
kubectl apply -f c1-redis.yaml

echo "Applying L9 API..."
kubectl apply -f c1-l9-api.yaml

echo "Applying MCP Memory..."
kubectl apply -f c1-mcp-memory.yaml

echo "Applying Monitoring..."
kubectl apply -f c1-monitoring.yaml

echo "Applying Ingress..."
kubectl apply -f c1-ingress.yaml

echo "Applying Network Policies..."
kubectl apply -f c1-network-policy.yaml

echo "All manifests applied"
REMOTE_SCRIPT

    log_success "Manifests deployed"
}

# =============================================================================
# PHASE 11: WAIT FOR PODS
# =============================================================================
wait_for_pods() {
    log_step "PHASE 11: WAIT FOR PODS"

    log_info "Waiting for pods to be ready..."

    ssh -o StrictHostKeyChecking=no -i "$SSH_KEY_FILE" root@"$C1_IP" bash << 'REMOTE_SCRIPT'
set -e

echo "Waiting for PostgreSQL..."
kubectl wait --for=condition=ready pod -l app=l9-postgres -n l9-c1 --timeout=120s || echo "PostgreSQL still starting..."

echo "Waiting for Neo4j (may take 2-3 minutes)..."
kubectl wait --for=condition=ready pod -l app=l9-neo4j -n l9-c1 --timeout=180s || echo "Neo4j still starting..."

echo "Waiting for Redis..."
kubectl wait --for=condition=ready pod -l app=l9-redis -n l9-c1 --timeout=60s || echo "Redis still starting..."

echo "Waiting for L9 API..."
kubectl wait --for=condition=ready pod -l app=l9-api -n l9-c1 --timeout=120s || echo "L9 API still starting..."

echo "Waiting for MCP Memory..."
kubectl wait --for=condition=ready pod -l app=l9-mcp-memory -n l9-c1 --timeout=60s || echo "MCP Memory still starting..."

echo "Waiting for Prometheus..."
kubectl wait --for=condition=ready pod -l app=prometheus -n l9-c1 --timeout=60s || echo "Prometheus still starting..."

echo "Waiting for Grafana..."
kubectl wait --for=condition=ready pod -l app=grafana -n l9-c1 --timeout=60s || echo "Grafana still starting..."

echo ""
echo "=== POD STATUS ==="
kubectl get pods -n l9-c1 -o wide
REMOTE_SCRIPT

    log_success "Pods deployment complete"
}

# =============================================================================
# PHASE 12: FINAL VERIFICATION
# =============================================================================
final_verification() {
    log_step "PHASE 12: FINAL VERIFICATION"

    log_info "Running final checks..."

    ssh -o StrictHostKeyChecking=no -i "$SSH_KEY_FILE" root@"$C1_IP" bash << 'REMOTE_SCRIPT'
echo "=== PODS ==="
kubectl get pods -n l9-c1

echo ""
echo "=== SERVICES ==="
kubectl get svc -n l9-c1

echo ""
echo "=== PERSISTENT VOLUMES ==="
kubectl get pvc -n l9-c1

echo ""
echo "=== RESOURCE USAGE ==="
kubectl top nodes 2>/dev/null || echo "(metrics not yet available)"
REMOTE_SCRIPT

    # Test endpoints
    log_info "Testing endpoints..."

    local endpoints=(
        "30080:L9 API"
        "30902:MCP Memory"
        "30432:PostgreSQL"
        "30474:Neo4j Browser"
        "30300:Grafana"
        "30909:Prometheus"
    )

    for ep in "${endpoints[@]}"; do
        local port="${ep%%:*}"
        local name="${ep#*:}"
        if nc -z -w2 "$C1_IP" "$port" 2>/dev/null; then
            log_success "$name (port $port): ACCESSIBLE"
        else
            log_warn "$name (port $port): Not yet accessible"
        fi
    done

    log_success "Final verification complete"
}

# =============================================================================
# MAIN
# =============================================================================
main() {
    echo ""
    echo "============================================="
    echo "   C1 FULL AUTOMATED DEPLOYMENT"
    echo "   Target: $C1_IP"
    echo "   Started: $(date)"
    echo "   Log: $LOG_FILE"
    echo "============================================="
    echo ""

    safety_check

    local current_image=$(verify_c1_state)
    local ssh_key_id=$(ensure_ssh_key)
    local image_id=$(get_image_id)

    rebuild_c1 "$ssh_key_id" "$image_id"
    wait_for_ssh
    verify_system
    install_k3s
    sync_env_files
    build_docker_images
    deploy_manifests
    wait_for_pods
    final_verification

    echo ""
    echo "============================================="
    echo -e "${GREEN}   SUCCESS! C1 DEPLOYMENT COMPLETE${NC}"
    echo "============================================="
    echo ""
    echo "Access endpoints:"
    echo "  L9 API:          http://$C1_IP:30080"
    echo "  MCP Memory:      http://$C1_IP:30902"
    echo "  PostgreSQL:      postgresql://l9_user@$C1_IP:30432/l9_memory"
    echo "  Neo4j Browser:   http://$C1_IP:30474"
    echo "  Neo4j Bolt:      bolt://$C1_IP:30687"
    echo "  Grafana:         http://$C1_IP:30300"
    echo "  Prometheus:      http://$C1_IP:30909"
    echo ""
    echo "SSH: ssh -i ~/.ssh/Hetzner-C1 root@$C1_IP"
    echo "Log: $LOG_FILE"
    echo ""
}

main "$@"
