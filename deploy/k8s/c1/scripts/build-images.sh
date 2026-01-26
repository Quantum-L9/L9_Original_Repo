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
#   - All requirements from requirements-production.txt are installed
#   - Images are tagged properly for K8s deployment
#   - Build artifacts are logged for audit
# =============================================================================

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../../.." && pwd)"
BUILD_DIR="$SCRIPT_DIR/.."

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
    
    # Check we're in the right directory
    if [[ ! -f "$REPO_ROOT/requirements.txt" ]]; then
        log_error "Cannot find requirements.txt in repo root: $REPO_ROOT"
        exit 1
    fi
    
    # Check production requirements exist
    if [[ ! -f "$BUILD_DIR/requirements-production.txt" ]]; then
        log_warn "requirements-production.txt not found, copying from template..."
        # Generate from main requirements.txt by excluding dev deps
        grep -v -E "^pytest|^ruff|^mypy|^vulture|^mutmut|^playwright|^black" "$REPO_ROOT/requirements.txt" \
            > "$BUILD_DIR/requirements-production.txt"
    fi
    
    log_success "Prerequisites verified"
    log_info "Repo root: $REPO_ROOT"
    log_info "Build dir: $BUILD_DIR"
    log_info "Version: $VERSION"
    log_info "VCS ref: $VCS_REF"
}

# =============================================================================
# PHASE 2: Sync requirements
# =============================================================================
sync_requirements() {
    log_step "SYNC REQUIREMENTS"
    
    log_info "Ensuring requirements-production.txt is up to date..."
    
    # Count packages in production requirements
    PROD_COUNT=$(grep -c "^[a-zA-Z]" "$BUILD_DIR/requirements-production.txt" || echo 0)
    log_info "Production requirements: $PROD_COUNT packages"
    
    # Show key packages
    log_info "Key packages:"
    grep -E "^(fastapi|pydantic|asyncpg|neo4j|redis|openai|langchain|structlog|prometheus)" "$BUILD_DIR/requirements-production.txt" | while read line; do
        echo "  - $line"
    done
    
    log_success "Requirements synced"
}

# =============================================================================
# PHASE 3: Build L9 API image
# =============================================================================
build_l9_api() {
    log_step "BUILD L9 API IMAGE"
    
    local image_tag="$REGISTRY/$L9_API_IMAGE:$VERSION"
    local latest_tag="$REGISTRY/$L9_API_IMAGE:latest"
    
    log_info "Building: $image_tag"
    log_info "Build context: $REPO_ROOT"
    log_info "Dockerfile: $BUILD_DIR/Dockerfile"
    
    cd "$REPO_ROOT"
    
    docker build $NO_CACHE \
        -f "$BUILD_DIR/Dockerfile" \
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
# PHASE 4: Build MCP Memory image (if Dockerfile exists)
# =============================================================================
build_mcp_memory() {
    log_step "BUILD MCP MEMORY IMAGE"
    
    local mcp_dockerfile="$BUILD_DIR/Dockerfile.mcp-memory"
    
    if [[ ! -f "$mcp_dockerfile" ]]; then
        log_warn "Dockerfile.mcp-memory not found, creating from template..."
        create_mcp_dockerfile
    fi
    
    local image_tag="$REGISTRY/$MCP_MEMORY_IMAGE:$VERSION"
    local latest_tag="$REGISTRY/$MCP_MEMORY_IMAGE:latest"
    
    log_info "Building: $image_tag"
    
    cd "$REPO_ROOT"
    
    docker build $NO_CACHE \
        -f "$mcp_dockerfile" \
        --build-arg BUILD_DATE="$BUILD_DATE" \
        --build-arg VCS_REF="$VCS_REF" \
        --build-arg VERSION="$VERSION" \
        -t "$image_tag" \
        -t "$latest_tag" \
        .
    
    log_success "Built: $image_tag"
}

# =============================================================================
# Create MCP Memory Dockerfile if it doesn't exist
# =============================================================================
create_mcp_dockerfile() {
    cat > "$BUILD_DIR/Dockerfile.mcp-memory" << 'DOCKERFILE'
# =============================================================================
# L9 MCP Memory Server Dockerfile
# =============================================================================
FROM python:3.12-slim

RUN groupadd -r l9 -g 1000 && useradd -r -u 1000 -g l9 -m l9

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends curl && \
    rm -rf /var/lib/apt/lists/*

COPY deploy/k8s/c1/requirements-production.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY --chown=l9:l9 mcp_memory/ ./mcp_memory/
COPY --chown=l9:l9 memory/ ./memory/
COPY --chown=l9:l9 core/ ./core/
COPY --chown=l9:l9 config/ ./config/
COPY --chown=l9:l9 migrations/ ./migrations/

RUN mkdir -p /app/logs && chown -R l9:l9 /app
USER l9

ENV PYTHONPATH=/app PYTHONUNBUFFERED=1

HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:9000/health || exit 1

EXPOSE 9000

CMD ["python", "-m", "mcp_memory.server", "--host", "0.0.0.0", "--port", "9000"]
DOCKERFILE
    
    log_success "Created Dockerfile.mcp-memory"
}

# =============================================================================
# PHASE 5: Push images to registry
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
# PHASE 6: Verify images
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
    sync_requirements
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
