#!/bin/bash
# =============================================================================
# C1 Kubernetes Deployment Script
# =============================================================================
# Target: C1 (46.62.243.82) - Hetzner CPX32
# 
# CONSTRAINTS:
# - L9 server (157.180.73.53) is OFF LIMITS
# - All actions must be repeatable and rollback-able
#
# Usage:
#   ./c1-deploy.sh              # Deploy all components
#   ./c1-deploy.sh --dry-run    # Show what would be deployed
#   ./c1-deploy.sh --skip-k3s   # Skip k3s installation (if already installed)
# =============================================================================

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
C1_IP="46.62.243.82"
L9_IP="157.180.73.53"  # OFF LIMITS
NAMESPACE="l9-c1"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Parse arguments
DRY_RUN=false
SKIP_K3S=false
for arg in "$@"; do
    case $arg in
        --dry-run)
            DRY_RUN=true
            ;;
        --skip-k3s)
            SKIP_K3S=true
            ;;
    esac
done

# Logging functions
log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Safety check - ensure we're not targeting L9
check_target() {
    log_info "Checking deployment target..."
    
    CURRENT_IP=$(hostname -I 2>/dev/null | awk '{print $1}' || echo "unknown")
    
    if [[ "$CURRENT_IP" == "$L9_IP" ]]; then
        log_error "SAFETY VIOLATION: This script is running on L9 server!"
        log_error "L9 (157.180.73.53) is OFF LIMITS. Aborting."
        exit 1
    fi
    
    if [[ "$CURRENT_IP" == "$C1_IP" ]]; then
        log_success "Target verified: C1 ($C1_IP)"
    else
        log_warn "Running on: $CURRENT_IP (expected C1: $C1_IP)"
        read -p "Continue anyway? (y/N) " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    fi
}

# Phase 1: System preparation
prepare_system() {
    log_info "Phase 1: Preparing system..."
    
    if $DRY_RUN; then
        echo "Would run: apt update && apt upgrade -y"
        echo "Would install: curl wget git htop"
        return
    fi
    
    apt update
    apt install -y curl wget git htop
    
    # Set hostname
    hostnamectl set-hostname c1-k8s
    
    log_success "System prepared"
}

# Phase 2: Install k3s
install_k3s() {
    if $SKIP_K3S; then
        log_info "Skipping k3s installation (--skip-k3s flag)"
        return
    fi
    
    log_info "Phase 2: Installing k3s..."
    
    if $DRY_RUN; then
        echo "Would install k3s with: curl -sfL https://get.k3s.io | sh -"
        return
    fi
    
    # Check if k3s already installed
    if command -v kubectl &> /dev/null; then
        log_warn "kubectl already available, checking k3s..."
        if systemctl is-active --quiet k3s; then
            log_success "k3s already running"
            return
        fi
    fi
    
    # Install k3s (keeps traefik for ingress)
    curl -sfL https://get.k3s.io | sh -
    
    # Wait for k3s to be ready
    log_info "Waiting for k3s to be ready..."
    sleep 10
    
    # Verify installation
    kubectl get nodes
    
    # Make kubectl accessible
    mkdir -p ~/.kube
    cp /etc/rancher/k3s/k3s.yaml ~/.kube/config
    chmod 600 ~/.kube/config
    
    log_success "k3s installed and running"
}

# Phase 3: Deploy L9 stack
deploy_stack() {
    log_info "Phase 3: Deploying L9 stack..."
    
    cd "$SCRIPT_DIR"
    
    # Deploy order matters - dependencies first
    MANIFESTS=(
        "c1-namespace.yaml"
        "c1-secrets.yaml"
        "c1-rbac.yaml"
        "c1-postgres.yaml"
        "c1-neo4j.yaml"
        "c1-redis.yaml"
        "c1-l9-api.yaml"
        "c1-mcp-memory.yaml"
        "c1-monitoring.yaml"
        "c1-ingress.yaml"
        "c1-network-policy.yaml"
    )
    
    for manifest in "${MANIFESTS[@]}"; do
        log_info "Applying $manifest..."
        if $DRY_RUN; then
            echo "Would run: kubectl apply -f $manifest"
        else
            kubectl apply -f "$manifest"
        fi
    done
    
    log_success "All manifests applied"
}

# Phase 4: Wait for pods
wait_for_pods() {
    log_info "Phase 4: Waiting for pods to be ready..."
    
    if $DRY_RUN; then
        echo "Would wait for pods in namespace $NAMESPACE"
        return
    fi
    
    # Wait for Neo4j (slowest to start)
    log_info "Waiting for Neo4j..."
    kubectl wait --for=condition=ready pod -l app=l9-neo4j -n $NAMESPACE --timeout=180s || true
    
    # Wait for Redis
    log_info "Waiting for Redis..."
    kubectl wait --for=condition=ready pod -l app=l9-redis -n $NAMESPACE --timeout=60s || true
    
    # Wait for PostgreSQL
    log_info "Waiting for PostgreSQL..."
    kubectl wait --for=condition=ready pod -l app=l9-postgres -n $NAMESPACE --timeout=120s || true
    
    # Wait for L9 API
    log_info "Waiting for L9 API..."
    kubectl wait --for=condition=ready pod -l app=l9-api -n $NAMESPACE --timeout=120s || true
    
    # Wait for MCP Memory
    log_info "Waiting for MCP Memory..."
    kubectl wait --for=condition=ready pod -l app=l9-mcp-memory -n $NAMESPACE --timeout=60s || true
    
    # Wait for monitoring
    log_info "Waiting for monitoring..."
    kubectl wait --for=condition=ready pod -l app=prometheus -n $NAMESPACE --timeout=60s || true
    kubectl wait --for=condition=ready pod -l app=grafana -n $NAMESPACE --timeout=60s || true
    
    log_success "All pods ready"
}

# Phase 5: Verify deployment
verify_deployment() {
    log_info "Phase 5: Verifying deployment..."
    
    if $DRY_RUN; then
        echo "Would verify: kubectl get pods -n $NAMESPACE"
        return
    fi
    
    echo ""
    echo "=== PODS ==="
    kubectl get pods -n $NAMESPACE -o wide
    
    echo ""
    echo "=== SERVICES ==="
    kubectl get svc -n $NAMESPACE
    
    echo ""
    echo "=== PERSISTENT VOLUMES ==="
    kubectl get pvc -n $NAMESPACE
    
    echo ""
    echo "=== ACCESS ENDPOINTS ==="
    echo "L9 Orchestrator: http://$C1_IP:30800"
    echo "Neo4j Browser:   http://$C1_IP:30474"
    echo "Neo4j Bolt:      bolt://$C1_IP:30687"
    echo "Grafana:         http://$C1_IP:30300"
    echo "Prometheus:      http://$C1_IP:30909"
    
    log_success "Deployment verified"
}

# Main execution
main() {
    echo "============================================="
    echo "   C1 Kubernetes Deployment"
    echo "   Target: $C1_IP"
    echo "============================================="
    echo ""
    
    if $DRY_RUN; then
        log_warn "DRY RUN MODE - No changes will be made"
        echo ""
    fi
    
    check_target
    prepare_system
    install_k3s
    deploy_stack
    wait_for_pods
    verify_deployment
    
    echo ""
    log_success "=========================================="
    log_success "   C1 DEPLOYMENT COMPLETE"
    log_success "=========================================="
    echo ""
    echo "Next steps:"
    echo "1. Update firewall to allow NodePorts (30300, 30474, 30687, 30800, 30909)"
    echo "2. Change default passwords in c1-secrets.yaml"
    echo "3. Test endpoints from external network"
    echo ""
    echo "To rollback: ./c1-rollback.sh"
}

main "$@"
