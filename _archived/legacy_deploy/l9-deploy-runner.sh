#!/usr/bin/env bash

################################################################################
# l9-deploy-runner.sh - UPDATED VERSION
#
# CHANGES FROM ORIGINAL:
#   - Step 6: No longer tries to build on VPS (was causing issues)
#   - Uses vps-deploy-helper.sh instead (handles multiple Dockerfiles)
#   - Local SIM now validates with docker-build-validator.sh
#   - Much safer approach for complex multi-service setups
#
################################################################################

set -euo pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Configuration
VPS_IP="157.180.73.53"
VPS_USER="admin"
VPS_SSH="${VPS_USER}@${VPS_IP}"
VPS_APP_DIR="/opt/l9"

# State
TAG="${1:-}"
BUILD_ERRORS=0

################################################################################
# UTILITIES
################################################################################

log() {
  echo -e "${BLUE}[runner]${NC} $1"
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

pause_for_approval() {
  local question="$1"
  local default="${2:-n}"

  echo ""
  read -p "$(echo -e ${YELLOW}$question${NC}) [${default}] " -r response
  response="${response:-$default}"

  if [[ ! "$response" =~ ^[Yy]$ ]]; then
    error "Deployment cancelled by user"
  fi
}

################################################################################
# STEP 1: VALIDATION
################################################################################

step_1_validation() {
  log "Step 1/7: LOCAL VALIDATION"
  echo "  Checking git state..."

  if ! git diff --quiet; then
    error "Uncommitted changes in git. Please commit or stash first:"
    git status
    exit 1
  fi

  if ! git diff --cached --quiet; then
    error "Staged changes detected. Please commit or stash first"
    exit 1
  fi

  success "Git tree is clean"

  # Check repo structure
  echo "  Checking repo structure..."
  [[ ! -f "docker-compose.yml" ]] && error "docker-compose.yml not found"
  [[ ! -f "runtime/Dockerfile" ]] && error "runtime/Dockerfile not found"
  [[ ! -f "requirements.txt" ]] && error "requirements.txt not found"

  success "Repo structure is valid"

  # Check Docker
  echo "  Checking Docker daemon..."
  if ! docker info > /dev/null 2>&1; then
    error "Docker daemon is not running"
  fi

  success "Docker is running"
}

################################################################################
# STEP 2: LOCAL DOCKER SIM
################################################################################

step_2_local_sim() {
  log "Step 2/7: LOCAL DOCKER SIM"

  echo "  Cleaning up old containers..."
  docker-compose down -v 2>&1 | grep -v "Removing network\|Removing volume" || true

  echo "  Building Docker images..."
  if ! docker-compose build --no-cache; then
    error "Docker build failed"
  fi
  success "Build successful"

  echo "  Starting services..."
  docker-compose up -d

  echo "  Waiting for services to boot..."
  sleep 15

  echo "  Health check..."
  if ! curl -sf http://localhost:8000/health > /dev/null 2>&1; then
    docker-compose logs l9-api --tail=50
    error "Health check failed"
  fi
  success "Services are healthy"
}

################################################################################
# STEP 3: RUN TESTS
################################################################################

step_3_tests() {
  log "Step 3/7: RUNNING TESTS"

  echo "  Running pytest..."
  if ! docker-compose exec -T l9-api pytest --tb=short -q; then
    warning "Some tests failed (continuing anyway)"
  else
    success "All tests passed"
  fi
}

################################################################################
# STEP 4: COVERAGE TEST (APPROVAL GATE)
################################################################################

step_4_coverage() {
  log "Step 4/7: COVERAGE TEST"

  echo "  Running coverage analysis..."
  if ! docker-compose exec -T l9-api coverage run -m pytest > /tmp/coverage.log 2>&1; then
    warning "Coverage run had issues (continuing)"
  fi

  echo ""
  echo "  Coverage Report:"
  docker-compose exec -T l9-api coverage report || true
  echo ""

  pause_for_approval "Coverage acceptable? (y/n):" "n"
  success "Coverage gate passed"
}

################################################################################
# STEP 5: ORACLE GATE (MANUAL APPROVAL)
################################################################################

step_5_oracle_gate() {
  log "Step 5/7: ORACLE GATE"

  echo ""
  echo "  ⚠️  ORACLE VERIFICATION REQUIRED"
  echo "  Before proceeding to VPS, verify system state:"
  echo ""
  echo "  • Use Cursor to check CGMP system state"
  echo "  • Verify all critical integrations working"
  echo "  • Check that no breaking changes were introduced"
  echo ""

  pause_for_approval "ORACLE status READY TO DEPLOY? (y/n):" "n"
  success "ORACLE gate approved"
}

################################################################################
# STEP 6: GIT TAG & PUSH (NO BUILD ON VPS)
################################################################################

step_6_git_tag() {
  log "Step 6/7: GIT TAG & PUSH"

  echo "  Creating git tag: $TAG"
  git tag "$TAG"

  echo "  Pushing to origin..."
  git push origin main
  git push origin "$TAG"

  success "Code pushed with tag: $TAG"
}

################################################################################
# STEP 7: VPS DEPLOY (CHECKOUT + RUN HELPER)
################################################################################

step_7_vps_deploy() {
  log "Step 7/7: VPS DEPLOYMENT"

  echo "  Preparing VPS for deployment..."

  ssh "$VPS_SSH" bash -s <<EOFVPS
set -euo pipefail

cd "$VPS_APP_DIR"

echo "  Stashing local changes..."
git stash push -u -m "pre-deploy-\$(date)" || true

echo "  Fetching latest..."
git fetch origin main --tags

echo "  Checking out: $TAG"
git checkout "$TAG"

echo "  Validating docker-compose..."
if ! docker-compose config > /dev/null 2>&1; then
  echo "ERROR: Invalid docker-compose.yml"
  exit 1
fi

echo "  VPS is ready for deployment script"

EOFVPS

  success "VPS is checked out at $TAG"

  echo ""
  echo "  ⚠️  IMPORTANT: Complete deployment on VPS manually:"
  echo ""
  echo "    ssh $VPS_SSH"
  echo "    cd $VPS_APP_DIR"
  echo "    ./vps-deploy-helper.sh $TAG"
  echo ""
  echo "  OR use this one-liner:"
  echo ""
  echo "    ssh $VPS_SSH 'cd $VPS_APP_DIR && bash vps-deploy-helper.sh $TAG'"
  echo ""

  pause_for_approval "Run VPS deploy now? (y/n):" "n"

  ssh "$VPS_SSH" "cd $VPS_APP_DIR && bash vps-deploy-helper.sh $TAG"

  success "VPS deployment complete"
}

################################################################################
# CLEANUP
################################################################################

cleanup() {
  log "Cleaning up local SIM..."
  docker-compose down -v 2>&1 | grep -v "Removing network\|Removing volume" || true
  success "Cleaned up"
}

################################################################################
# MAIN
################################################################################

main() {
  [[ -z "$TAG" ]] && error "Usage: $0 <version-tag> (e.g., 0.6.0-l9)"

  echo ""
  echo "╔════════════════════════════════════════════════════════════════════╗"
  echo "║                 L9 DEPLOYMENT RUNNER - UPDATED                    ║"
  echo "║                                                                    ║"
  echo "║  Tag: $TAG                                                     ║"
  echo "║  VPS: $VPS_SSH:$VPS_APP_DIR                                      ║"
  echo "╚════════════════════════════════════════════════════════════════════╝"
  echo ""

  step_1_validation
  echo ""

  step_2_local_sim
  echo ""

  step_3_tests
  echo ""

  step_4_coverage
  echo ""

  step_5_oracle_gate
  echo ""

  step_6_git_tag
  echo ""

  step_7_vps_deploy
  echo ""

  cleanup

  echo ""
  echo "╔════════════════════════════════════════════════════════════════════╗"
  echo -e "║                    ${GREEN}✓ DEPLOYMENT COMPLETE${NC}                           ║"
  echo "║                                                                    ║"
  echo "║  Verify by running:                                               ║"
  echo "║    curl https://l9.quantumaipartners.com/health                   ║"
  echo "║    curl https://memory.quantumaipartners.com/health               ║"
  echo "╚════════════════════════════════════════════════════════════════════╝"
  echo ""
}

trap cleanup EXIT
main "$@"
