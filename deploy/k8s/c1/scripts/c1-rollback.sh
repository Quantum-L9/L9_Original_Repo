#!/bin/bash
# =============================================================================
# C1 Kubernetes Rollback Script
# =============================================================================
# Target: C1 (46.62.243.82) - Hetzner CPX32
#
# SAFE ROLLBACK OPTIONS:
# 1. Delete specific deployments (data preserved)
# 2. Delete entire namespace (data preserved in PVCs)
# 3. Full k3s uninstall (complete reset)
#
# Usage:
#   ./c1-rollback.sh                    # Interactive mode
#   ./c1-rollback.sh --deployment NAME  # Rollback specific deployment
#   ./c1-rollback.sh --namespace        # Delete entire namespace
#   ./c1-rollback.sh --full             # Complete k3s uninstall
# =============================================================================

set -euo pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Configuration
C1_IP="46.62.243.82"
L9_IP="157.180.73.53"  # OFF LIMITS
NAMESPACE="l9-c1"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Logging
log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Safety check
check_target() {
    CURRENT_IP=$(hostname -I 2>/dev/null | awk '{print $1}' || echo "unknown")
    
    if [[ "$CURRENT_IP" == "$L9_IP" ]]; then
        log_error "SAFETY VIOLATION: Cannot run rollback on L9 server!"
        exit 1
    fi
}

# Show current status
show_status() {
    log_info "Current deployment status:"
    echo ""
    
    if kubectl get namespace $NAMESPACE &>/dev/null; then
        echo "=== NAMESPACE: $NAMESPACE ==="
        kubectl get pods -n $NAMESPACE 2>/dev/null || echo "No pods found"
        echo ""
        kubectl get pvc -n $NAMESPACE 2>/dev/null || echo "No PVCs found"
    else
        log_warn "Namespace $NAMESPACE does not exist"
    fi
    echo ""
}

# Rollback specific deployment
rollback_deployment() {
    local deployment=$1
    log_info "Rolling back deployment: $deployment"
    
    kubectl delete deployment "$deployment" -n $NAMESPACE --ignore-not-found
    log_success "Deployment $deployment deleted"
}

# Rollback specific statefulset
rollback_statefulset() {
    local statefulset=$1
    log_info "Rolling back statefulset: $statefulset"
    
    kubectl delete statefulset "$statefulset" -n $NAMESPACE --ignore-not-found
    log_success "StatefulSet $statefulset deleted (PVC data preserved)"
}

# Delete namespace (preserves PVC data on local-path)
delete_namespace() {
    log_warn "This will delete ALL resources in namespace $NAMESPACE"
    log_warn "PVC data will be preserved on disk at /var/lib/rancher/k3s/storage/"
    read -p "Are you sure? (type 'yes' to confirm) " -r
    
    if [[ "$REPLY" == "yes" ]]; then
        log_info "Deleting namespace $NAMESPACE..."
        kubectl delete namespace $NAMESPACE --ignore-not-found
        log_success "Namespace deleted. Data preserved in local-path storage."
    else
        log_info "Aborted"
    fi
}

# Full k3s uninstall
full_uninstall() {
    log_error "=== FULL K3S UNINSTALL ==="
    log_error "This will:"
    log_error "  - Stop and remove k3s"
    log_error "  - Delete ALL Kubernetes resources"
    log_error "  - Delete ALL persistent data"
    log_error ""
    log_error "The server will return to a clean state."
    read -p "Type 'UNINSTALL' to confirm: " -r
    
    if [[ "$REPLY" == "UNINSTALL" ]]; then
        log_info "Uninstalling k3s..."
        
        if [[ -f /usr/local/bin/k3s-uninstall.sh ]]; then
            /usr/local/bin/k3s-uninstall.sh
            log_success "k3s uninstalled completely"
        else
            log_error "k3s uninstall script not found"
        fi
    else
        log_info "Aborted"
    fi
}

# Interactive mode
interactive_mode() {
    show_status
    
    echo "=== ROLLBACK OPTIONS ==="
    echo "1. Rollback L9 API only"
    echo "2. Rollback MCP Memory only"
    echo "3. Rollback PostgreSQL (preserves data)"
    echo "4. Rollback Neo4j (preserves data)"
    echo "5. Rollback Redis (preserves data)"
    echo "6. Rollback monitoring (Prometheus + Grafana)"
    echo "7. Delete entire namespace (preserves PVC data)"
    echo "8. Full k3s uninstall (DESTRUCTIVE)"
    echo "9. Cancel"
    echo ""
    read -p "Select option (1-9): " -r
    
    case $REPLY in
        1)
            rollback_deployment "l9-api"
            ;;
        2)
            rollback_deployment "l9-mcp-memory"
            ;;
        3)
            rollback_statefulset "l9-postgres"
            ;;
        4)
            rollback_statefulset "l9-neo4j"
            ;;
        5)
            rollback_deployment "l9-redis"
            ;;
        6)
            rollback_deployment "prometheus"
            rollback_deployment "grafana"
            ;;
        7)
            delete_namespace
            ;;
        8)
            full_uninstall
            ;;
        9)
            log_info "Cancelled"
            ;;
        *)
            log_error "Invalid option"
            ;;
    esac
}

# Parse arguments
main() {
    check_target
    
    if [[ $# -eq 0 ]]; then
        interactive_mode
        exit 0
    fi
    
    case $1 in
        --deployment)
            if [[ -n "${2:-}" ]]; then
                rollback_deployment "$2"
            else
                log_error "Specify deployment name: --deployment NAME"
            fi
            ;;
        --statefulset)
            if [[ -n "${2:-}" ]]; then
                rollback_statefulset "$2"
            else
                log_error "Specify statefulset name: --statefulset NAME"
            fi
            ;;
        --namespace)
            delete_namespace
            ;;
        --full)
            full_uninstall
            ;;
        --status)
            show_status
            ;;
        *)
            echo "Usage: $0 [--deployment NAME|--statefulset NAME|--namespace|--full|--status]"
            ;;
    esac
}

main "$@"
