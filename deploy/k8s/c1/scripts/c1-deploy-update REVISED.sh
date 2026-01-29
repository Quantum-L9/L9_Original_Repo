#!/bin/bash

# =============================================================================
# C1 PULL & DEPLOY SCRIPT (L9 on C1 - UPDATE PATH)
# =============================================================================
#
# Complete deployment workflow for updating C1 with latest L9 code.
#
# Usage:
#   ./c1-deploy-update.sh                 # Full deploy
#   ./c1-deploy-update.sh --skip-migrations   # Skip DB + Neo4j migrations
#   ./c1-deploy-update.sh --skip-build        # Skip container rebuild
#   ./c1-deploy-update.sh --skip-neo4j        # Skip Neo4j migrations/checks
#   ./c1-deploy-update.sh --dry-run           # Preview actions (no changes)
#   ./c1-deploy-update.sh --force             # Non-interactive (no prompts)
#
# WORKFLOW:
#   Phase 1: Connect & Verify
#   Phase 2: Pull Latest Code (git hard-reset to origin/main)
#   Phase 3: Verify Env Files (VPS-managed, never synced from local)
#   Phase 4: Run Database Migrations (PostgreSQL)
#   Phase 5: Run Neo4j Migrations (Cypher)
#   Phase 6: Rebuild Containers
#   Phase 7: Restart Services
#   Phase 8: Health Checks (NodePort endpoints)
#   Phase 9: Verify Memory Substrate (Postgres / Redis / Neo4j)
#   Phase 10: Final Status
#
# PREREQUISITES:
#   - SSH key at ~/.ssh/Hetzner-C1-nopass (passwordless)
#   - VPS has .env.c1.hetzner configured (NOT synced from local)
#   - C1 already has base infrastructure (k3s, docker, c1-*.yaml applied)
# =============================================================================

set -euo pipefail

# =============================================================================
# CONFIGURATION
# =============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../../.." && pwd)"
LOG_FILE="$SCRIPT_DIR/deploy-update-$(date +%Y%m%d-%H%M%S).log"

# VPS / C1 Config
C1_IP="46.62.243.82"
SSH_KEY_FILE="$HOME/.ssh/Hetzner-C1-nopass"
VPS_L9_DIR="/opt/l9-k8s"   # Directory containing c1-*.yaml and scripts

# Git deploy target
GIT_REMOTE="origin"
GIT_BRANCH="main"

# Kubernetes namespace for C1
C1_NAMESPACE="l9-c1"

# Ports for external health checks (from C1-QUICK-REFERENCE.md)
SERVICE_NAMES=("L9 API" "MCP Memory" "PostgreSQL" "Neo4j Browser" "Neo4j Bolt" "Grafana" "Prometheus" "Redis")
SERVICE_PORTS=(30080 30902 30432 30474 30687 30300 30909 30379)

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

# Options
DRY_RUN=false
SKIP_MIGRATIONS=false
SKIP_BUILD=false
SKIP_NEO4J=false
FORCE=false
CHECK_CONFIG_ONLY=false

# Logging
exec > >(tee -a "$LOG_FILE") 2>&1

log_info()    { echo -e "${BLUE}[INFO $(date +%H:%M:%S)]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS $(date +%H:%M:%S)]${NC} $1"; }
log_warn()    { echo -e "${YELLOW}[WARN $(date +%H:%M:%S)]${NC} $1"; }
log_error()   { echo -e "${RED}[ERROR $(date +%H:%M:%S)]${NC} $1"; }
log_step()    { echo -e "${CYAN}[STEP $(date +%H:%M:%S)]${NC} ========== $1 =========="; }

PHASE_START_TS=0
phase_start() { PHASE_START_TS=$(date +%s); }
phase_end() {
  local label="$1"
  local end_ts
  end_ts=$(date +%s)
  local duration=$(( end_ts - PHASE_START_TS ))
  log_success "$label completed in ${duration}s"
}

confirm_or_exit() {
  local prompt="$1"
  if $FORCE; then
    log_warn "FORCE=true – skipping confirmation: $prompt"
    return 0
  fi
  read -r -p "$prompt [y/N]: " answer
  case "$answer" in
    [Yy]* ) return 0 ;;
    * ) log_error "Aborted by user."; exit 1 ;;
  esac
}

# =============================================================================
# PARSE ARGUMENTS
# =============================================================================

while [[ $# -gt 0 ]]; do
  case $1 in
    --dry-run)
      DRY_RUN=true
      shift
      ;;
    --skip-migrations)
      SKIP_MIGRATIONS=true
      shift
      ;;
    --skip-build)
      SKIP_BUILD=true
      shift
      ;;
    --skip-neo4j)
      SKIP_NEO4J=true
      shift
      ;;
    --force)
      FORCE=true
      shift
      ;;
    --check-config)
      CHECK_CONFIG_ONLY=true
      shift
      ;;
    --help)
      echo "Usage: $0 [options]"
      echo
      echo "Options:"
      echo "  --dry-run          Preview actions without making changes"
      echo "  --skip-migrations  Skip database (Postgres) and Neo4j migrations"
      echo "  --skip-build       Skip container rebuild / rollout"
      echo "  --skip-neo4j       Skip Neo4j migrations and checks"
      echo "  --force            Skip confirmations (non-interactive)"
      echo "  --check-config     Only validate connectivity, namespace, secrets, and ports; no deploy"
      echo
      echo "Defaults:"
      echo "  Target IP:         $C1_IP"
      echo "  SSH key:           $SSH_KEY_FILE"
      echo "  Remote repo dir:   $VPS_L9_DIR"
      echo "  Git target:        $GIT_REMOTE/$GIT_BRANCH"
      exit 0
      ;;
    *)
      log_error "Unknown option: $1"
      exit 1
      ;;
  esac
done

# =============================================================================
# SSH HELPERS
# =============================================================================

ssh_cmd() {
  ssh -o StrictHostKeyChecking=no -o ConnectTimeout=10 -i "$SSH_KEY_FILE" root@"$C1_IP" "$@"
}

# Note: env files are VPS-managed (e.g., .env.c1.hetzner), not synced from local.

# =============================================================================
# PHASE 1: CONNECT & VERIFY
# =============================================================================

connect_and_verify() {
  log_step "PHASE 1: CONNECT & VERIFY"
  phase_start

  if [[ ! -f "$SSH_KEY_FILE" ]]; then
    log_error "SSH key not found: $SSH_KEY_FILE"
    exit 1
  fi

  log_info "Testing SSH connection to $C1_IP..."
  if ! ssh_cmd "echo 'SSH OK'" &>/dev/null; then
    log_error "Cannot connect to C1 at $C1_IP"
    exit 1
  fi

  log_info "Verifying k3s is running..."
  if ! ssh_cmd "kubectl get nodes >/dev/null 2>&1"; then
    log_error "k3s is not running on C1"
    exit 1
  fi

  log_info "Verifying Docker is running..."
  if ! ssh_cmd "docker ps >/dev/null 2>&1"; then
    log_error "Docker is not running on C1"
    exit 1
  fi

  log_info "Current pod status in namespace $C1_NAMESPACE:"
  ssh_cmd "kubectl get pods -n $C1_NAMESPACE 2>/dev/null || echo 'No $C1_NAMESPACE namespace yet'"

  phase_end "PHASE 1: CONNECT & VERIFY"
}

# =============================================================================
# PHASE 2: PULL LATEST CODE
# =============================================================================

pull_latest_code() {
  log_step "PHASE 2: PULL LATEST CODE"
  phase_start

  if $DRY_RUN; then
    log_info "[DRY RUN] Would pull latest code in $VPS_L9_DIR and hard-reset to $GIT_REMOTE/$GIT_BRANCH"
    phase_end "PHASE 2: PULL LATEST CODE (dry run)"
    return
  fi

  confirm_or_exit "About to hard-reset C1 repo in $VPS_L9_DIR to $GIT_REMOTE/$GIT_BRANCH. Continue?"

  log_info "Pulling latest code from git on C1..."
  ssh_cmd bash << "REMOTE_SCRIPT"
set -e

REPO_DIR="/opt/l9-k8s"
GIT_REMOTE_ENV="${GIT_REMOTE:-origin}"
GIT_BRANCH_ENV="${GIT_BRANCH:-main}"

if [[ -d "$REPO_DIR/.git" ]]; then
  cd "$REPO_DIR"
  echo "Current commit: $(git rev-parse --short HEAD)"
  echo "Current branch: $(git branch --show-current || echo 'detached')"
  git stash --include-untracked 2>/dev/null || true
  git fetch "$GIT_REMOTE_ENV"
  git reset --hard "$GIT_REMOTE_ENV/$GIT_BRANCH_ENV"
  echo "Updated to: $(git rev-parse --short HEAD) on $GIT_REMOTE_ENV/$GIT_BRANCH_ENV"
else
  echo "ERROR: Expected git repo at $REPO_DIR (c1-k8s manifests). Aborting."
  exit 1
fi
REMOTE_SCRIPT

  phase_end "PHASE 2: PULL LATEST CODE"
}

# =============================================================================
# PHASE 3: VERIFY ENV FILES
# =============================================================================

verify_env_files() {
  log_step "PHASE 3: VERIFY ENV FILES (VPS-managed)"
  phase_start

  log_info "Verifying .env.c1.hetzner and Kubernetes secrets exist on C1..."

  ssh_cmd bash << "REMOTE_SCRIPT"
set -e

if [[ ! -f "/root/.env.c1.hetzner" && ! -f "/opt/l9-k8s/.env.c1.hetzner" ]]; then
  echo "WARNING: .env.c1.hetzner not found in /root or /opt/l9-k8s."
  echo "Ensure credentials are present before running full deploy."
fi

if ! kubectl get secrets -n l9-c1 c1-secrets >/dev/null 2>&1; then
  echo "WARNING: c1-secrets Kubernetes Secret not found in namespace l9-c1."
fi
REMOTE_SCRIPT

  phase_end "PHASE 3: VERIFY ENV FILES"
}

# =============================================================================
# PHASE 4: RUN DATABASE MIGRATIONS (PostgreSQL)
# =============================================================================

run_db_migrations() {
  log_step "PHASE 4: RUN DATABASE MIGRATIONS (PostgreSQL)"
  phase_start

  if $SKIP_MIGRATIONS; then
    log_warn "Skipping database migrations due to --skip-migrations"
    phase_end "PHASE 4: RUN DATABASE MIGRATIONS (skipped)"
    return
  fi

  if $DRY_RUN; then
    log_info "[DRY RUN] Would run PostgreSQL migrations against C1 Postgres (port 30432)"
    phase_end "PHASE 4: RUN DATABASE MIGRATIONS (dry run)"
    return
  fi

  confirm_or_exit "About to run PostgreSQL migrations on C1. Continue?"

  # Expect a migration runner script or psql invocation on C1 that uses /opt/l9-k8s/migrations
  ssh_cmd bash << "REMOTE_SCRIPT"
set -e

cd /opt/l9-k8s

if [[ ! -d "migrations" ]]; then
  echo "ERROR: migrations directory not found in /opt/l9-k8s"
  exit 1
fi

echo "Running PostgreSQL migrations via psql on port 30432..."
for file in migrations/000*.sql migrations/00*.sql migrations/20*.sql; do
  if [[ -f "$file" ]]; then
    echo "Applying migration: $file"
    PGPASSWORD="$POSTGRES_PASSWORD" psql \
      -h 46.62.243.82 \
      -p 30432 \
      -U "$POSTGRES_USER" \
      -d "$POSTGRES_DB" \
      -v ON_ERROR_STOP=1 \
      -f "$file"
  fi
done

echo "PostgreSQL migrations completed."
REMOTE_SCRIPT

  phase_end "PHASE 4: RUN DATABASE MIGRATIONS (PostgreSQL)"
}

# =============================================================================
# PHASE 5: RUN NEO4J MIGRATIONS (Cypher)
# =============================================================================

run_neo4j_migrations() {
  log_step "PHASE 5: RUN NEO4J MIGRATIONS (Cypher)"
  phase_start

  if $SKIP_MIGRATIONS || $SKIP_NEO4J; then
    log_warn "Skipping Neo4j migrations due to --skip-migrations or --skip-neo4j"
    phase_end "PHASE 5: RUN NEO4J MIGRATIONS (skipped)"
    return
  fi

  if $DRY_RUN; then
    log_info "[DRY RUN] Would run Neo4j Cypher migrations against bolt://$C1_IP:30687"
    phase_end "PHASE 5: RUN NEO4J MIGRATIONS (dry run)"
    return
  fi

  confirm_or_exit "About to run Neo4j migrations on C1. Continue?"

  ssh_cmd bash << "REMOTE_SCRIPT"
set -e

cd /opt/l9-k8s

if [[ ! -d "migrations" ]]; then
  echo "ERROR: migrations directory not found in /opt/l9-k8s"
  exit 1
fi

if ! command -v cypher-shell >/dev/null 2>&1; then
  echo "ERROR: cypher-shell not available on C1."
  exit 1
fi

for file in migrations/*.cypher; do
  if [[ -f "$file" ]]; then
    echo "Applying Neo4j migration: $file"
    cypher-shell -a "bolt://46.62.243.82:30687" -u "$NEO4J_USER" -p "$NEO4J_PASSWORD" < "$file"
  fi
done

echo "Neo4j migrations completed."
REMOTE_SCRIPT

  phase_end "PHASE 5: RUN NEO4J MIGRATIONS (Cypher)"
}

# =============================================================================
# PHASE 6: REBUILD CONTAINERS
# =============================================================================

rebuild_containers() {
  log_step "PHASE 6: REBUILD CONTAINERS (k8s manifests applied by c1-full-deploy.sh)"
  phase_start

  if $SKIP_BUILD; then
    log_warn "Skipping container rebuild due to --skip-build"
    phase_end "PHASE 6: REBUILD CONTAINERS (skipped)"
    return
  fi

  if $DRY_RUN; then
    log_info "[DRY RUN] Would run c1-full-deploy.sh (apply/update k8s manifests) on C1"
    phase_end "PHASE 6: REBUILD CONTAINERS (dry run)"
    return
  fi

  confirm_or_exit "About to run c1-full-deploy.sh (rebuild/redeploy L9 stack). Continue?"

  ssh_cmd bash << "REMOTE_SCRIPT"
set -e

cd /opt/l9-k8s

if [[ ! -x "./c1-full-deploy.sh" ]]; then
  echo "ERROR: ./c1-full-deploy.sh not found or not executable in /opt/l9-k8s"
  exit 1
fi

./c1-full-deploy.sh
REMOTE_SCRIPT

  phase_end "PHASE 6: REBUILD CONTAINERS"
}

# =============================================================================
# PHASE 7: RESTART SERVICES
# =============================================================================

restart_services() {
  log_step "PHASE 7: RESTART SERVICES (k8s rollouts)"
  phase_start

  if $DRY_RUN; then
    log_info "[DRY RUN] Would restart L9 deployments in namespace $C1_NAMESPACE"
    phase_end "PHASE 7: RESTART SERVICES (dry run)"
    return
  fi

  # In k8s, c1-full-deploy.sh should already ensure latest images apply;
  # here we can explicitly restart key deployments if needed.
  ssh_cmd bash << "REMOTE_SCRIPT"
set -e

NS="l9-c1"

echo "Restarting core deployments in namespace $NS..."
for deploy in l9-api l9-mcp-memory l9-postgres l9-redis l9-neo4j l9-prometheus l9-grafana; do
  if kubectl get deployment "$deploy" -n "$NS" >/dev/null 2>&1; then
    echo "Rolling restart: $deploy"
    kubectl rollout restart deployment "$deploy" -n "$NS"
  fi
done

echo "Waiting for rollouts to complete..."
for deploy in l9-api l9-mcp-memory l9-postgres l9-redis l9-neo4j l9-prometheus l9-grafana; do
  if kubectl get deployment "$deploy" -n "$NS" >/dev/null 2>&1; then
    kubectl rollout status deployment "$deploy" -n "$NS" --timeout=300s
  fi
done
REMOTE_SCRIPT

  phase_end "PHASE 7: RESTART SERVICES"
}

# =============================================================================
# PHASE 8: HEALTH CHECKS (NodePort endpoints)
# =============================================================================

health_checks() {
  log_step "PHASE 8: HEALTH CHECKS (NodePort endpoints on $C1_IP)"
  phase_start

  if [[ ${#SERVICE_NAMES[@]} -ne ${#SERVICE_PORTS[@]} ]]; then
    log_error "SERVICE_NAMES and SERVICE_PORTS length mismatch."
    exit 1
  fi

  if $DRY_RUN; then
    log_info "[DRY RUN] Running external health checks (nc/curl) against C1 endpoints (no state changes)."
  fi

  local failed_critical=0

  for i in "${!SERVICE_NAMES[@]}"; do
    local name="${SERVICE_NAMES[$i]}"
    local port="${SERVICE_PORTS[$i]}"
    log_info "Checking $name on $C1_IP:$port..."

    local critical=0
    case "$name" in
      "L9 API"|"MCP Memory"|"PostgreSQL"|"Neo4j Browser"|"Neo4j Bolt"|"Redis")
        critical=1
        ;;
    esac

    if nc -z -w5 "$C1_IP" "$port" >/dev/null 2>&1; then
      log_success "$name is reachable on port $port"
    else
      if [[ $critical -eq 1 ]]; then
        log_error "$name FAILED (critical) on port $port"
        failed_critical=1
      else
        log_warn "$name FAILED (non-critical) on port $port"
      fi
    fi
  done

  if [[ $failed_critical -ne 0 ]]; then
    log_error "One or more critical services failed health checks."
    exit 1
  fi

  phase_end "PHASE 8: HEALTH CHECKS"
}

# =============================================================================
# PHASE 9: VERIFY MEMORY SUBSTRATE (Postgres / Redis / Neo4j)
# =============================================================================

verify_memory_substrate() {
  log_step "PHASE 9: VERIFY MEMORY SUBSTRATE (Postgres / Redis / Neo4j)"
  phase_start

  if $DRY_RUN; then
    log_info "[DRY RUN] Would run read-only substrate checks on Postgres/Redis/Neo4j"
    phase_end "PHASE 9: VERIFY MEMORY SUBSTRATE (dry run)"
    return
  fi

  ssh_cmd bash << "REMOTE_SCRIPT"
set -e

NS="l9-c1"

echo "Verifying PostgreSQL substrate (SELECT 1)..."
kubectl exec -n "$NS" deploy/l9-postgres -- \
  bash -c 'PGPASSWORD="$POSTGRES_PASSWORD" psql -h 127.0.0.1 -p 5432 -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "SELECT 1;" >/dev/null'

echo "Verifying Redis substrate (PING)..."
kubectl exec -n "$NS" deploy/l9-redis -- \
  bash -c 'redis-cli -h 127.0.0.1 -p 6379 PING | grep -q PONG'

if kubectl get deploy l9-neo4j -n "$NS" >/dev/null 2>&1; then
  echo "Verifying Neo4j substrate (RETURN 1)..."
  kubectl exec -n "$NS" deploy/l9-neo4j -- \
    bash -c 'cypher-shell -a bolt://127.0.0.1:7687 -u "$NEO4J_USER" -p "$NEO4J_PASSWORD" "RETURN 1;" >/dev/null'
else
  echo "Neo4j deployment not found in namespace $NS – skipping Neo4j substrate check."
fi

REMOTE_SCRIPT

  log_success "Memory substrates verified successfully."
  phase_end "PHASE 9: VERIFY MEMORY SUBSTRATE"
}

# =============================================================================
# PHASE 10: FINAL STATUS
# =============================================================================

final_status() {
  log_step "PHASE 10: FINAL STATUS"
  phase_start

  log_success "C1 deployment update completed successfully."
  log_info "Log file: $LOG_FILE"
  log_info "Target: $C1_IP, namespace: $C1_NAMESPACE, repo dir: $VPS_L9_DIR"
  log_info "Git target: $GIT_REMOTE/$GIT_BRANCH"

  phase_end "PHASE 10: FINAL STATUS"
}

# =============================================================================
# CHECK CONFIG (--check-config mode)
# =============================================================================

check_config() {
  log_step "CONFIG CHECK: Validate C1 connectivity, namespace, secrets, and basic services"
  phase_start

  # SSH + k3s + Docker (reuse logic from connect_and_verify without exit)
  local ok=true

  if ! ssh_cmd "echo 'SSH OK'" >/dev/null 2>&1; then
    log_error "SSH check FAILED for $C1_IP"
    ok=false
  else
    log_success "SSH check OK for $C1_IP"
  fi

  if ! ssh_cmd "kubectl get nodes >/dev/null 2>&1"; then
    log_error "k3s node check FAILED"
    ok=false
  else
    log_success "k3s node check OK"
  fi

  if ! ssh_cmd "docker ps >/dev/null 2>&1"; then
    log_error "Docker check FAILED"
    ok=false
  else
    log_success "Docker check OK"
  fi

  # Namespace + core secrets
  ssh_cmd bash << "REMOTE_SCRIPT" || ok=false
set -e
NS="l9-c1"

if kubectl get ns "$NS" >/dev/null 2>&1; then
  echo "[SUCCESS] Namespace $NS exists"
else
  echo "[ERROR] Namespace $NS missing"
  exit 2
fi

if kubectl get secrets -n "$NS" c1-secrets >/dev/null 2>&1; then
  echo "[SUCCESS] Secret c1-secrets present in $NS"
else
  echo "[WARN] Secret c1-secrets missing in $NS"
fi
REMOTE_SCRIPT

  # External ports reachable (fast NC probe)
  if [[ ${#SERVICE_NAMES[@]} -ne ${#SERVICE_PORTS[@]} ]]; then
    log_error "SERVICE_NAMES / SERVICE_PORTS length mismatch."
    ok=false
  else
    for i in "${!SERVICE_NAMES[@]}"; do
      local name="${SERVICE_NAMES[$i]}"
      local port="${SERVICE_PORTS[$i]}"
      if nc -z -w3 "$C1_IP" "$port" >/dev/null 2>&1; then
        log_success "Port check OK for $name ($C1_IP:$port)"
      else
        log_warn "Port check FAILED for $name ($C1_IP:$port)"
      fi
    done
  fi

  if ! $ok; then
    log_error "CONFIG CHECK FAILED – see logs above."
    phase_end "CONFIG CHECK (failed)"
    exit 1
  fi

  log_success "CONFIG CHECK PASSED"
  phase_end "CONFIG CHECK"
}

# =============================================================================
# MAIN
# =============================================================================

main() {
  log_info "Starting C1 deploy update (DRY_RUN=$DRY_RUN, SKIP_MIGRATIONS=$SKIP_MIGRATIONS, SKIP_BUILD=$SKIP_BUILD, SKIP_NEO4J=$SKIP_NEO4J, FORCE=$FORCE, CHECK_CONFIG_ONLY=$CHECK_CONFIG_ONLY)"

  connect_and_verify
  verify_env_files

  if $CHECK_CONFIG_ONLY; then
    check_config
    log_info "CHECK-CONFIG mode enabled – skipping deploy phases."
    return
  fi

  pull_latest_code
  run_db_migrations
  run_neo4j_migrations
  rebuild_containers
  restart_services
  health_checks
  verify_memory_substrate
  final_status
}

main "$@"
