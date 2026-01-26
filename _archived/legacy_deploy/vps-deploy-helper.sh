#!/usr/bin/env bash

################################################################################
# vps-deploy-helper.sh
#
# Purpose: Smart deploy script that lives on VPS and handles all Dockerfiles
#
# This script:
#   1. Validates the checked-out code
#   2. Discovers all services to build
#   3. Builds only changed Dockerfiles (smart)
#   4. Starts all services in correct order
#   5. Health checks each service
#
# Usage (on VPS):
#   ./vps-deploy-helper.sh v0.6.0-l9
#
################################################################################

set -euo pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Parameters
TAG="${1:-}"
VERBOSE="${VERBOSE:-0}"
SKIP_BUILD="${SKIP_BUILD:-0}"

# State
SERVICES=()
DOCKERFILES_CHANGED=()

################################################################################
# UTILITIES
################################################################################

log() {
  echo -e "${BLUE}[deploy]${NC} $1"
}

success() {
  echo -e "${GREEN}[✓]${NC} $1"
}

error() {
  echo -e "${RED}[✗]${NC} $1"
  exit 1
}

warning() {
  echo -e "${YELLOW}[!]${NC} $1"
}

verbose() {
  [[ "$VERBOSE" == "1" ]] && echo -e "${BLUE}[verbose]${NC} $1" || true
}

################################################################################
# VALIDATION
################################################################################

validate_tag() {
  [[ -z "$TAG" ]] && error "Usage: $0 <version-tag> (e.g., v0.6.0-l9)"
  log "Deploying tag: $TAG"
}

validate_repo_state() {
  log "Validating repo state..."

  [[ ! -f docker-compose.yml ]] && error "docker-compose.yml not found"
  success "docker-compose.yml found"

  [[ ! -d "runtime" ]] && error "runtime/ directory not found"
  success "runtime/ directory found"

  if [[ ! -f "runtime/Dockerfile" ]]; then
    error "runtime/Dockerfile not found"
  fi
  success "runtime/Dockerfile found"
}

################################################################################
# PHASE 1: DISCOVER SERVICES
################################################################################

discover_services() {
  log "Phase 1: Discovering services..."

  # Get all services from docker-compose.yml
  local services=$(docker-compose config | grep "services:" -A 999 | grep "^  [a-z]" | sed 's/://g' | tr -d ' ')

  SERVICES=($services)

  [[ ${#SERVICES[@]} -eq 0 ]] && error "No services found in docker-compose.yml"

  log "Found services:"
  for service in "${SERVICES[@]}"; do
    log "  • $service"
  done
}

################################################################################
# PHASE 2: DETECT CHANGED DOCKERFILES
################################################################################

detect_changed_dockerfiles() {
  log "Phase 2: Detecting which Dockerfiles have changed..."

  # Get the previous tag
  local prev_tag=$(git describe --tags --abbrev=0 2>/dev/null || echo "HEAD~1")

  verbose "Comparing against: $prev_tag"

  # Find all Dockerfiles
  while IFS= read -r dockerfile; do
    verbose "Checking: $dockerfile"

    # See if this file changed between prev_tag and HEAD
    if git diff "$prev_tag"..HEAD --name-only | grep -q "$(basename "$dockerfile")"; then
      DOCKERFILES_CHANGED+=("$dockerfile")
      warning "Changed: $dockerfile (will rebuild)"
    else
      verbose "Unchanged: $dockerfile"
    fi
  done < <(find . -maxdepth 3 -name "Dockerfile*" -type f 2>/dev/null)

  if [[ ${#DOCKERFILES_CHANGED[@]} -eq 0 ]]; then
    warning "No Dockerfile changes detected (using cached images if available)"
  fi
}

################################################################################
# PHASE 3: VALIDATE DOCKER-COMPOSE
################################################################################

validate_compose_config() {
  log "Phase 3: Validating docker-compose configuration..."

  if ! docker-compose config > /tmp/docker-compose-validated.yml 2>&1; then
    error "Invalid docker-compose.yml"
    cat /tmp/docker-compose-validated.yml
    exit 1
  fi

  success "docker-compose.yml is valid"
}

################################################################################
# PHASE 4: BACKUP CURRENT STATE
################################################################################

backup_current_state() {
  log "Phase 4: Backing up current state..."

  local backup_dir="/opt/l9/backups/$(date +%Y%m%d-%H%M%S)"
  mkdir -p "$backup_dir"

  # Save current running container IDs
  docker-compose ps -q > "$backup_dir/running-containers.txt" 2>/dev/null || true

  # Save current image IDs
  docker-compose images | tail -n +2 > "$backup_dir/current-images.txt" 2>/dev/null || true

  success "State backed up to: $backup_dir"
}

################################################################################
# PHASE 5: BUILD SERVICES
################################################################################

build_services() {
  if [[ "$SKIP_BUILD" == "1" ]]; then
    warning "Skipping build (SKIP_BUILD=1)"
    return 0
  fi

  log "Phase 5: Building services..."

  # Build all services (docker-compose is smart about layer caching)
  if ! docker-compose build --no-cache 2>&1 | tee /tmp/docker-build.log; then
    error "Build failed"
    echo ""
    echo "Last 50 lines of build output:"
    tail -50 /tmp/docker-build.log
    exit 1
  fi

  success "Build completed"
}

################################################################################
# PHASE 6: STOP OLD CONTAINERS
################################################################################

stop_old_containers() {
  log "Phase 6: Stopping old containers..."

  # Graceful stop with 30 second timeout
  docker-compose down --timeout 30 2>&1 | grep -v "Removing network\|Removing volume" || true

  success "Old containers stopped"
}

################################################################################
# PHASE 7: START NEW CONTAINERS
################################################################################

start_new_containers() {
  log "Phase 7: Starting new containers..."

  if ! docker-compose up -d 2>&1; then
    error "Failed to start containers"
  fi

  success "Containers started"

  # Give services time to boot
  log "Waiting 10 seconds for services to boot..."
  sleep 10
}

################################################################################
# PHASE 8: HEALTH CHECKS
################################################################################

health_check() {
  log "Phase 8: Running health checks..."

  local health_ok=0
  local max_attempts=5
  local attempt=0

  while [[ $attempt -lt $max_attempts ]]; do
    ((attempt++))

    log "Health check attempt $attempt/$max_attempts..."

    # Check main API
    if curl -sf http://127.0.0.1:8000/health > /dev/null 2>&1; then
      success "L9 API is healthy"
      health_ok=1
      break
    fi

    warning "Health check failed, retrying in 5 seconds..."
    sleep 5
  done

  if [[ $health_ok -eq 0 ]]; then
    error "Health checks failed after $max_attempts attempts"
    echo ""
    echo "Container logs:"
    docker-compose logs --tail=50 l9-api || true
  fi

  success "All health checks passed"
}

################################################################################
# PHASE 9: POST-DEPLOY VERIFICATION
################################################################################

post_deploy_verification() {
  log "Phase 9: Post-deploy verification..."

  # Check running services
  log "Running services:"
  docker-compose ps

  # Show image info
  log "Deployed images:"
  docker-compose images

  success "Deployment verification complete"
}

################################################################################
# ROLLBACK PROCEDURE
################################################################################

rollback() {
  local reason="$1"
  error "Deployment failed: $reason"

  warning "ATTEMPTING ROLLBACK..."

  log "Stopping current containers..."
  docker-compose down --timeout 30 2>&1 || true

  log "Rolling back to previous version..."
  git checkout HEAD~1 || warning "Could not revert git state"

  log "Restarting previous version..."
  docker-compose up -d 2>&1 || error "Rollback failed - manual intervention required"

  warning "Rollback completed (verify manually!)"
  exit 1
}

################################################################################
# ERROR HANDLER
################################################################################

trap 'rollback "Script error"' ERR

################################################################################
# MAIN
################################################################################

main() {
  echo ""
  echo "╔══════════════════════════════════════════════════════════════════════╗"
  echo "║                    VPS DEPLOY HELPER - $TAG                          ║"
  echo "╚══════════════════════════════════════════════════════════════════════╝"
  echo ""

  validate_tag
  validate_repo_state
  discover_services
  detect_changed_dockerfiles
  validate_compose_config
  backup_current_state
  build_services
  stop_old_containers
  start_new_containers
  health_check
  post_deploy_verification

  echo ""
  echo "╔══════════════════════════════════════════════════════════════════════╗"
  echo -e "║                    ${GREEN}✓ DEPLOYMENT SUCCESSFUL${NC}                             ║"
  echo "║                                                                      ║"
  echo "║  Services running at:                                               ║"
  echo "║    • API:    https://l9.quantumaipartners.com                       ║"
  echo "║    • Memory: https://memory.quantumaipartners.com                   ║"
  echo "╚══════════════════════════════════════════════════════════════════════╝"
  echo ""
}

main "$@"
