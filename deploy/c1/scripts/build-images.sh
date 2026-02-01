#!/bin/bash
# =============================================================================
# L9 Docker Image Build Script for C1
# =============================================================================
# Builds production Docker images with ALL requirements installed.
#
# Usage:
#   ./build-images.sh                    # Build and tag as :latest
#   ./build-images.sh --push             # Build and push to registry
#   ./build-images.sh --version 2.0.1    # Build with specific version
#   ./build-images.sh --no-cache         # Force fresh build
#
# This script ensures:
#   - Root Dockerfile and Dockerfile.mcp-memory (canonical) are used
#   - Images are tagged properly for K8s deployment
#   - Build artifacts are logged for audit
# =============================================================================

set -euo pipefail

# Configuration: use repo root Dockerfiles (canonical per ADR-0089)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../../.." && pwd)"

# Image names
REGISTRY="${REGISTRY:-ghcr.io/igor-beylin}"
L9_API_IMAGE="l9-api"
MCP_MEMORY_IMAGE="l9-mcp-memory"
VERSION="${VERSION:-latest}"

# Build options
PUSH=false
NO_CACHE=""
BUILD_DATE=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
VCS_REF=$(git -C "$REPO_ROOT" rev-parse --short HEAD 2>/dev/null || echo "unknown")

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

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --push)
            PUSH=true
            shift
            ;;
        --version)
            VERSION="$2"
            shift 2
            ;;
        --no-cache)
            NO_CACHE="--no-cache"
            shift
            ;;
        --registry)
            REGISTRY="$2"
            shift 2
            ;;
        *)
            log_error "Unknown argument: $1"
            exit 1
            ;;
    esac
done

# =============================================================================
# PHASE 1: Verify prerequisites
# =============================================================================
verify_prerequisites() {
    log_step "VERIFY PREREQUISITES"

    # Check Docker
    if ! command -v docker &> /dev/null; then
        log_error "Docker not found. Please install Docker."
        exit 1
    fi

    if [[ ! -f "$REPO_ROOT/Dockerfile" ]]; then
        log_error "Cannot find Dockerfile in repo root: $REPO_ROOT"
        exit 1
    fi
    if [[ ! -f "$REPO_ROOT/Dockerfile.mcp-memory" ]]; then
        log_error "Cannot find Dockerfile.mcp-memory in repo root: $REPO_ROOT"
        exit 1
    fi

    log_success "Prerequisites verified"
    log_info "Repo root: $REPO_ROOT"
    log_info "Version: $VERSION"
    log_info "VCS ref: $VCS_REF"
}

# =============================================================================
# PHASE 2: Build L9 API image
# =============================================================================
build_l9_api() {
    log_step "BUILD L9 API IMAGE"

    local image_tag="$REGISTRY/$L9_API_IMAGE:$VERSION"
    local latest_tag="$REGISTRY/$L9_API_IMAGE:latest"

    log_info "Building: $image_tag"
    log_info "Build context: $REPO_ROOT"
    log_info "Dockerfile: $REPO_ROOT/Dockerfile"

    cd "$REPO_ROOT"

    docker build $NO_CACHE \
        -f Dockerfile \
        --target production \
        --build-arg BUILD_DATE="$BUILD_DATE" \
        --build-arg VCS_REF="$VCS_REF" \
        --build-arg VERSION="$VERSION" \
        -t "$image_tag" \
        -t "$latest_tag" \
        .

    log_success "Built: $image_tag"

    # Show image size
    local size=$(docker images --format "{{.Size}}" "$image_tag")
    log_info "Image size: $size"
}

# =============================================================================
# PHASE 3: Build MCP Memory image (root Dockerfile.mcp-memory)
# =============================================================================
build_mcp_memory() {
    log_step "BUILD MCP MEMORY IMAGE"

    local image_tag="$REGISTRY/$MCP_MEMORY_IMAGE:$VERSION"
    local latest_tag="$REGISTRY/$MCP_MEMORY_IMAGE:latest"

    log_info "Building: $image_tag"
    log_info "Dockerfile: $REPO_ROOT/Dockerfile.mcp-memory"

    cd "$REPO_ROOT"

    docker build $NO_CACHE \
        -f Dockerfile.mcp-memory \
        --target production \
        --build-arg BUILD_DATE="$BUILD_DATE" \
        --build-arg VCS_REF="$VCS_REF" \
        --build-arg VERSION="$VERSION" \
        -t "$image_tag" \
        -t "$latest_tag" \
        .

    log_success "Built: $image_tag"
}

# =============================================================================
# PHASE 4: Push images to registry
# =============================================================================
push_images() {
    if ! $PUSH; then
        log_info "Skipping push (use --push to push to registry)"
        return
    fi

    log_step "PUSH IMAGES TO REGISTRY"

    log_info "Pushing L9 API..."
    docker push "$REGISTRY/$L9_API_IMAGE:$VERSION"
    docker push "$REGISTRY/$L9_API_IMAGE:latest"

    log_info "Pushing MCP Memory..."
    docker push "$REGISTRY/$MCP_MEMORY_IMAGE:$VERSION"
    docker push "$REGISTRY/$MCP_MEMORY_IMAGE:latest"

    log_success "All images pushed to $REGISTRY"
}

# =============================================================================
# PHASE 5: Verify images
# =============================================================================
verify_images() {
    log_step "VERIFY IMAGES"

    log_info "Local images:"
    docker images | grep -E "(l9-api|l9-mcp-memory)" | head -10

    log_info "Verifying L9 API image can import key modules..."
    docker run --rm "$REGISTRY/$L9_API_IMAGE:$VERSION" python -c "
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
    print('✅ All key modules importable')
except ImportError as e:
    print(f'❌ Import error: {e}')
    sys.exit(1)
"

    log_success "Image verification passed"
}

# =============================================================================
# MAIN
# =============================================================================
main() {
    echo ""
    echo "============================================="
    echo "   L9 Docker Image Builder"
    echo "   Version: $VERSION"
    echo "   Registry: $REGISTRY"
    echo "   Date: $BUILD_DATE"
    echo "============================================="
    echo ""

    verify_prerequisites
    build_l9_api
    build_mcp_memory
    push_images
    verify_images

    echo ""
    echo "============================================="
    echo -e "${GREEN}   BUILD COMPLETE${NC}"
    echo "============================================="
    echo ""
    echo "Images built:"
    echo "  - $REGISTRY/$L9_API_IMAGE:$VERSION"
    echo "  - $REGISTRY/$MCP_MEMORY_IMAGE:$VERSION"
    echo ""
    if $PUSH; then
        echo "Images pushed to registry."
    else
        echo "To push: ./build-images.sh --push"
    fi
    echo ""
}

main "$@"
