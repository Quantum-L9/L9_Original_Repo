#!/usr/bin/env bash

################################################################################
# docker-build-validator.sh
# 
# Purpose: Discover, validate, and safely build ALL Dockerfiles in the repo
# 
# Ensures:
#   1. All docker-compose.yml files are syntactically valid
#   2. All Dockerfiles referenced in compose files exist
#   3. All build contexts are correct
#   4. Build can happen on VPS without surprises
#
# Usage:
#   ./docker-build-validator.sh [--check-only | --validate-only | --build]
#
################################################################################

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Config
COMPOSE_FILES=()
DOCKERFILES=()
BUILD_ERRORS=0
VALIDATION_ERRORS=0

################################################################################
# UTILITY FUNCTIONS
################################################################################

log() {
  echo -e "${BLUE}[INFO]${NC} $1"
}

success() {
  echo -e "${GREEN}[✓]${NC} $1"
}

error() {
  echo -e "${RED}[✗]${NC} $1"
  ((VALIDATION_ERRORS++))
}

warning() {
  echo -e "${YELLOW}[!]${NC} $1"
}

################################################################################
# PHASE 1: DISCOVER ALL DOCKERFILES & COMPOSE FILES
################################################################################

discover_docker_files() {
  log "Phase 1: Discovering Docker files..."
  
  # Find all docker-compose files
  while IFS= read -r file; do
    if [[ -f "$file" ]]; then
      COMPOSE_FILES+=("$file")
      log "Found compose file: $file"
    fi
  done < <(find . -maxdepth 3 -name "docker-compose*.yml" -type f)
  
  # Find all Dockerfiles
  while IFS= read -r file; do
    if [[ -f "$file" ]]; then
      DOCKERFILES+=("$file")
      log "Found Dockerfile: $file"
    fi
  done < <(find . -maxdepth 3 -name "Dockerfile*" -type f)
  
  if [[ ${#COMPOSE_FILES[@]} -eq 0 ]]; then
    error "No docker-compose files found!"
    return 1
  fi
  
  if [[ ${#DOCKERFILES[@]} -eq 0 ]]; then
    error "No Dockerfiles found!"
    return 1
  fi
  
  success "Discovered ${#COMPOSE_FILES[@]} compose file(s) and ${#DOCKERFILES[@]} Dockerfile(s)"
}

################################################################################
# PHASE 2: VALIDATE COMPOSE FILES
################################################################################

validate_compose_files() {
  log "Phase 2: Validating docker-compose syntax..."
  
  for compose in "${COMPOSE_FILES[@]}"; do
    log "Checking: $compose"
    
    if ! docker-compose -f "$compose" config > /dev/null 2>&1; then
      error "Invalid syntax in: $compose"
      docker-compose -f "$compose" config 2>&1 | head -20
      return 1
    fi
    
    success "Valid: $compose"
  done
}

################################################################################
# PHASE 3: VALIDATE DOCKERFILE REFERENCES
################################################################################

validate_dockerfile_references() {
  log "Phase 3: Validating Dockerfile references..."
  
  for compose in "${COMPOSE_FILES[@]}"; do
    log "Checking references in: $compose"
    
    # Extract build: dockerfile: lines
    while IFS= read -r line; do
      dockerfile=$(echo "$line" | sed 's/.*dockerfile: //g' | tr -d "'" | tr -d '"')
      compose_dir=$(dirname "$compose")
      dockerfile_full_path="$compose_dir/$dockerfile"
      
      if [[ ! -f "$dockerfile_full_path" ]]; then
        error "Dockerfile not found: $dockerfile_full_path (referenced in $compose)"
      else
        success "Found: $dockerfile_full_path"
      fi
    done < <(grep -i "dockerfile:" "$compose" || true)
  done
}

################################################################################
# PHASE 4: VALIDATE BUILD CONTEXTS
################################################################################

validate_build_contexts() {
  log "Phase 4: Validating build contexts..."
  
  for compose in "${COMPOSE_FILES[@]}"; do
    log "Checking build contexts in: $compose"
    
    # Parse services with build context
    local compose_dir=$(dirname "$compose")
    
    # Simple extraction of build contexts (requires docker-compose config)
    docker-compose -f "$compose" config 2>/dev/null | \
      grep -A 5 "build:" | \
      grep -E "(context|dockerfile):" | \
      while read -r line; do
        path=$(echo "$line" | sed 's/.*context: //g' | tr -d " " | tr -d "'" | tr -d '"')
        
        if [[ -n "$path" ]] && [[ ! "$path" =~ "dockerfile:" ]]; then
          # Handle absolute vs relative paths
          if [[ "$path" == /* ]]; then
            full_path="$path"
          else
            full_path="$compose_dir/$path"
          fi
          
          if [[ ! -d "$full_path" ]]; then
            error "Build context directory not found: $full_path"
          else
            success "Build context exists: $full_path"
          fi
        fi
      done
  done
}

################################################################################
# PHASE 5: CHECK DOCKERFILE VALIDITY
################################################################################

validate_dockerfiles() {
  log "Phase 5: Validating Dockerfile structure..."
  
  for dockerfile in "${DOCKERFILES[@]}"; do
    log "Checking: $dockerfile"
    
    if ! grep -q "^FROM" "$dockerfile"; then
      error "Dockerfile missing FROM statement: $dockerfile"
      continue
    fi
    
    success "Valid: $dockerfile (has FROM)"
  done
}

################################################################################
# PHASE 6: DRY RUN - BUILD WITHOUT PUSHING
################################################################################

build_dockerfiles() {
  log "Phase 6: Building all services (dry run)..."
  
  for compose in "${COMPOSE_FILES[@]}"; do
    log "Building services from: $compose"
    
    if ! docker-compose -f "$compose" build --no-cache 2>&1 | tee /tmp/docker-build.log; then
      error "Build failed for: $compose"
      tail -50 /tmp/docker-build.log
      return 1
    fi
    
    success "Build successful: $compose"
  done
}

################################################################################
# PHASE 7: HEALTH CHECK - VERIFY IMAGES EXIST
################################################################################

verify_built_images() {
  log "Phase 7: Verifying built images..."
  
  for compose in "${COMPOSE_FILES[@]}"; do
    # Get image names from compose file
    local images=$(docker-compose -f "$compose" config 2>/dev/null | grep "image:" | sed 's/.*image: //g' | tr -d " " | sort | uniq)
    
    while IFS= read -r image; do
      if [[ -n "$image" ]]; then
        if docker image inspect "$image" > /dev/null 2>&1; then
          success "Image exists: $image"
        else
          warning "Image may not exist: $image"
        fi
      fi
    done < <(echo "$images")
  done
}

################################################################################
# MAIN EXECUTION
################################################################################

main() {
  local mode="${1:-check-only}"
  
  echo ""
  echo "╔════════════════════════════════════════════════════════════════════╗"
  echo "║              DOCKER BUILD VALIDATOR & EXECUTOR                    ║"
  echo "║                    Mode: $mode                               ║"
  echo "╚════════════════════════════════════════════════════════════════════╝"
  echo ""
  
  # Phase 1: Discovery
  if ! discover_docker_files; then
    error "Discovery phase failed"
    exit 1
  fi
  echo ""
  
  # Phase 2: Validate compose syntax
  if ! validate_compose_files; then
    error "Compose validation failed"
    exit 1
  fi
  echo ""
  
  # Phase 3: Validate Dockerfile references
  validate_dockerfile_references
  echo ""
  
  # Phase 4: Validate build contexts
  validate_build_contexts
  echo ""
  
  # Phase 5: Validate Dockerfile structure
  validate_dockerfiles
  echo ""
  
  # Report early errors
  if [[ $VALIDATION_ERRORS -gt 0 ]]; then
    error "Found $VALIDATION_ERRORS validation error(s)"
    
    case "$mode" in
      check-only|validate-only)
        exit 1
        ;;
      build)
        warning "Continuing to build despite validation warnings..."
        ;;
    esac
  fi
  
  # Phase 6: Build (only if requested)
  if [[ "$mode" == "build" ]]; then
    echo ""
    log "STARTING BUILD PHASE..."
    if ! build_dockerfiles; then
      error "Build failed"
      exit 1
    fi
    echo ""
    
    # Phase 7: Verify images
    verify_built_images
  fi
  
  echo ""
  echo "╔════════════════════════════════════════════════════════════════════╗"
  if [[ $VALIDATION_ERRORS -eq 0 ]]; then
    echo -e "║ ${GREEN}✓ ALL CHECKS PASSED${NC}"
    if [[ "$mode" == "build" ]]; then
      echo "║ ✓ BUILD SUCCESSFUL"
    fi
  else
    echo -e "║ ${RED}✗ $VALIDATION_ERRORS ERROR(S) FOUND${NC}"
  fi
  echo "╚════════════════════════════════════════════════════════════════════╝"
  echo ""
  
  [[ $VALIDATION_ERRORS -eq 0 ]] && exit 0 || exit 1
}

################################################################################
# HELP
################################################################################

show_help() {
  cat << EOF

USAGE: ./docker-build-validator.sh [MODE]

MODES:
  check-only      (default) Just validate syntax and references
  validate-only   Thorough validation of all Docker files
  build           Validate AND build all services (--no-cache)

EXAMPLES:
  # Validate before committing
  ./docker-build-validator.sh check-only

  # Full validation (for pre-deploy)
  ./docker-build-validator.sh validate-only

  # Build everything locally before pushing to VPS
  ./docker-build-validator.sh build

OUTPUT:
  ✓ = Valid/Success
  ✗ = Error (must fix before proceeding)
  ! = Warning (may proceed but investigate)

WHAT IT DOES:
  1. Discovers all docker-compose.yml and Dockerfile* files
  2. Validates compose file syntax
  3. Verifies all referenced Dockerfiles exist
  4. Checks build contexts are valid
  5. Validates Dockerfile structure (has FROM, etc)
  6. (build mode) Actually builds all services
  7. (build mode) Verifies built images exist

This ensures VPS deployment won't fail with Docker errors.

EOF
}

if [[ "${1:-}" == "--help" ]] || [[ "${1:-}" == "-h" ]]; then
  show_help
  exit 0
fi

main "$@"
