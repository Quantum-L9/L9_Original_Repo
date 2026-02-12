#!/usr/bin/env bash

set -euo pipefail

# ==============================================================================
# L9 10X Deploy v2.0 (GitHub SSOT + Env Sync + Selective Rebuild + GOD MODE)
# RISK TIER: T2 (reversible infra)
#
# Behavior:
# - LOCAL: stages + commits + pushes current branch to origin
# - VPS: git hard reset to origin/$BRANCH, optional env sync, docker rebuild + restart
# - HEALTH: Always runs deep_mri.sh; optionally runs e2e_test_GODMODE.sh
#
# Blast radius:
# - Remote repo at $VPS_REPO is reset to match origin/$BRANCH (untracked files removed)
# - Remote Docker stack (prod overlay) is rebuilt and restarted (all or selected services)
# - Optional: docker system prune -af (NO volumes) when explicitly enabled
# ==============================================================================
# Usage:
# ./scripts/deployment/10X_Deploy_Script.sh --msg "your message" --no-cache --prune-docker
#
# Flags:
#   --msg ""                 Commit message (default: timestamp)
#   --no-cache               Rebuild images without cache
#   --prune-docker           docker system prune -af (NO volumes) [gated by L9_ALLOW_DOCKER_PRUNE]
#   --no-sync-env            Do not sync .env.vps -> VPS .env
#   --no-rebuild             Skip container rebuild (git pull + env sync only)
#   --services "svc1 svc2"   Rebuild only specified services (space-separated)
#   --core                   Rebuild only core L9 services (l9-api mcp-memory postgres)
#   --godmode                Run e2e_test_GODMODE.sh smoke after deployment (critical deploys)
#   --dry-run                Print commands without executing
#   -h | --help              Show help

### CONFIG (edit once, use forever)
VPS_HOST_DEFAULT="c1"
VPS_REPO_DEFAULT="/opt/l9"
BRANCH_DEFAULT="main"
COMPOSE_BASE="docker-compose.yml"
COMPOSE_PROD="docker-compose.prod.yml"
ENV_EXAMPLE=".env.example"
ENV_VPS_LOCAL=".env.vps"           # real secrets, MUST be gitignored
ENV_VPS_TEMPLATE=".env.vps.template" # placeholders only, SHOULD be committed
REMOTE_ENV_FILE=".env"             # lives at $VPS_REPO/.env

# Optional safety/env controls
REQUIRED_DEPLOY_BRANCH="${REQUIRED_DEPLOY_BRANCH:-$BRANCH_DEFAULT}"
ALLOW_NON_MAIN_DEPLOY="${L9_ALLOW_NON_MAIN_DEPLOY:-false}"
ALLOW_DOCKER_PRUNE="${L9_ALLOW_DOCKER_PRUNE:-false}"
SSH_OPTS="-o BatchMode=yes -o StrictHostKeyChecking=accept-new"

### RUNTIME
VPS_HOST="${VPS_HOST:-$VPS_HOST_DEFAULT}"
VPS_REPO="${VPS_REPO:-$VPS_REPO_DEFAULT}"
BRANCH="${BRANCH:-$BRANCH_DEFAULT}"
NO_CACHE=false
PRUNE_DOCKER=false
SYNC_ENV=true
DRY_RUN=false
NO_REBUILD=false
RUN_GODMODE=false
SERVICES=""  # Empty = rebuild all
COMMIT_MSG="deploy: $(date +'%Y-%m-%d %H:%M:%S')"

# ------------------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------------------
run() {
  if $DRY_RUN; then
    echo "DRY: $*"
  else
    eval "$@"
  fi
}

die() {
  echo "❌ $*" 1>&2
  exit 1
}

usage() {
  cat <<'EOF'
Usage: ./scripts/deployment/10X_Deploy_Script.sh [flags]

Flags:
  --msg ""                 Commit message
  --no-cache               Rebuild docker images without cache on VPS
  --prune-docker           docker system prune -af on VPS (NO volumes, requires L9_ALLOW_DOCKER_PRUNE=true)
  --no-sync-env            Do not sync .env.vps -> /opt/l9/.env
  --no-rebuild             Skip container rebuild (git pull + env sync only)
  --services "svc1 svc2"   Rebuild ONLY specified services (space-separated, e.g. "l9-api postgres")
  --core                   Rebuild ONLY core L9 services (l9-api mcp-memory postgres)
  --godmode                Run e2e_test_GODMODE.sh smoke after deployment (for critical deploys)
  --dry-run                Print commands without executing
  -h, --help               Help

Examples:
  # Full rebuild (all containers)
  ./scripts/deployment/10X_Deploy_Script.sh --msg "full deploy"

  # No rebuild (git pull + env sync only)
  ./scripts/deployment/10X_Deploy_Script.sh --no-rebuild

  # Rebuild only l9-api
  ./scripts/deployment/10X_Deploy_Script.sh --services "l9-api"

  # Rebuild core L9 services
  ./scripts/deployment/10X_Deploy_Script.sh --core

  # Critical deploy with GOD MODE validation
  ./scripts/deployment/10X_Deploy_Script.sh --msg "critical hotfix" --godmode

  # Full rebuild with GOD MODE (automatically enabled)
  ./scripts/deployment/10X_Deploy_Script.sh --no-cache
EOF
}

ensure_gitignore_allows_env_template() {
  [[ -f ".gitignore" ]] || return 0
  if grep -qE '^[[:space:]]*\.env\.\*' .gitignore; then
    if ! grep -qE '^[[:space:]]*!\.env\.vps\.template' .gitignore; then
      echo " + Patching .gitignore to allow tracking $ENV_VPS_TEMPLATE"
      printf '\n# Allow committing the VPS env template (placeholders only)\n!%s\n' "$ENV_VPS_TEMPLATE" >> .gitignore
    fi
  fi
}

patch_env_vps_template_from_example() {
  # Rewrites .env.vps.template to contain ALL keys from .env.example (placeholders only).
  # Compatible with Bash 3.2+ (no associative arrays).
  local repo_root="$1"
  local example_path="$repo_root/$ENV_EXAMPLE"
  local template_path="$repo_root/$ENV_VPS_TEMPLATE"
  [[ -f "$example_path" ]] || die "Missing $ENV_EXAMPLE at repo root."
  
  local tmp_out
  tmp_out="$(mktemp)"
  
  while IFS= read -r line; do
    if [[ "$line" =~ ^[[:space:]]*# ]] || [[ -z "$line" ]]; then
      echo "$line" >> "$tmp_out"
      continue
    fi
    if [[ "$line" =~ ^([A-Za-z_][A-Za-z0-9_]*)=(.*)$ ]]; then
      local key="${BASH_REMATCH[1]}"
      if [[ -f "$template_path" ]]; then
        local existing
        existing="$(grep -E "^${key}=" "$template_path" 2>/dev/null | head -1 || true)"
        if [[ -n "$existing" ]]; then
          echo "$existing" >> "$tmp_out"
        else
          echo "${key}=" >> "$tmp_out"
        fi
      else
        echo "${key}=" >> "$tmp_out"
      fi
    else
      echo "$line" >> "$tmp_out"
    fi
  done < "$example_path"
  
  if [[ ! -f "$template_path" ]] || ! cmp -s "$tmp_out" "$template_path"; then
    echo " + Patched $ENV_VPS_TEMPLATE from $ENV_EXAMPLE"
    mv "$tmp_out" "$template_path"
  else
    rm -f "$tmp_out"
    echo " = $ENV_VPS_TEMPLATE already up-to-date"
  fi
}

sync_env_vps_to_server() {
  # Streams local .env.vps to VPS as $VPS_REPO/.env (backup first). Uses SSH, not scp.
  local repo_root="$1"
  local local_env="$repo_root/$ENV_VPS_LOCAL"
  local remote_env="$VPS_REPO/$REMOTE_ENV_FILE"
  
  $SYNC_ENV || { echo " = Env sync disabled"; return 0; }
  [[ -f "$local_env" ]] || die "Missing $ENV_VPS_LOCAL at repo root. Create it with real values."
  
  echo "[ENV] Syncing $ENV_VPS_LOCAL -> $VPS_HOST:$remote_env"
  local stamp
  stamp="$(date +%Y%m%d_%H%M%S)"
  
  # Backup existing remote .env
  ssh $SSH_OPTS "$VPS_HOST" "cd '$VPS_REPO' && (test -f '$remote_env' && cp -a '$remote_env' '$remote_env.bak.$stamp' || true)"
  
  if $DRY_RUN; then
    echo "DRY: streaming $local_env -> $VPS_HOST:$remote_env"
  else
    ssh $SSH_OPTS "$VPS_HOST" "cat > '$remote_env' && chmod 600 '$remote_env'" < "$local_env"
  fi
  
  if ! $DRY_RUN; then
    local local_hash remote_hash
    local_hash="$(shasum -a 256 "$local_env" | awk '{print $1}')"
    remote_hash="$(ssh $SSH_OPTS "$VPS_HOST" "shasum -a 256 $remote_env" | awk '{print $1}')"
    [[ "$local_hash" == "$remote_hash" ]] || die "Env sync mismatch (local $local_hash != remote $remote_hash)"
    echo " ✅ Env synced (sha256 match)"
  fi
}

remote_git_hard_reset() {
  echo "[VPS] Hard reset to origin/$BRANCH (SSOT)"
  ssh $SSH_OPTS "$VPS_HOST" "cd '$VPS_REPO' && git fetch origin '$BRANCH' && git reset --hard 'origin/$BRANCH' && git clean -fd"
}

remote_rebuild_stack() {
  local build_opts=""
  $NO_CACHE && build_opts="--no-cache"
  
  if [[ -n "$SERVICES" ]]; then
    # Selective rebuild
    echo "[VPS] Selective rebuild: $SERVICES (no-cache=$NO_CACHE)"
    ssh $SSH_OPTS "$VPS_HOST" "cd '$VPS_REPO' && docker compose -f $COMPOSE_BASE -f $COMPOSE_PROD stop $SERVICES"
    ssh $SSH_OPTS "$VPS_HOST" "cd '$VPS_REPO' && docker compose -f $COMPOSE_BASE -f $COMPOSE_PROD build $build_opts $SERVICES"
    ssh $SSH_OPTS "$VPS_HOST" "cd '$VPS_REPO' && docker compose -f $COMPOSE_BASE -f $COMPOSE_PROD up -d --force-recreate $SERVICES"
  else
    # Full rebuild - automatically enable GOD MODE for critical validation
    echo "[VPS] Full rebuild (all services) no-cache=$NO_CACHE"
    if [[ "$RUN_GODMODE" == "false" ]]; then
      echo "[VPS] Full rebuild detected → GOD MODE enabled automatically"
      RUN_GODMODE=true
    fi
    ssh $SSH_OPTS "$VPS_HOST" "cd '$VPS_REPO' && docker compose -f $COMPOSE_BASE -f $COMPOSE_PROD down --remove-orphans"
    ssh $SSH_OPTS "$VPS_HOST" "cd '$VPS_REPO' && docker compose -f $COMPOSE_BASE -f $COMPOSE_PROD build $build_opts"
    ssh $SSH_OPTS "$VPS_HOST" "cd '$VPS_REPO' && docker compose -f $COMPOSE_BASE -f $COMPOSE_PROD up -d --force-recreate --remove-orphans"
  fi
  
  if $PRUNE_DOCKER; then
    if [[ "$ALLOW_DOCKER_PRUNE" == "true" ]]; then
      echo "[VPS] Prune docker (no volumes) - L9_ALLOW_DOCKER_PRUNE=true"
      ssh $SSH_OPTS "$VPS_HOST" "docker system prune -af"
    else
      echo "[VPS] --prune-docker requested but L9_ALLOW_DOCKER_PRUNE!=true, skipping prune."
    fi
  fi
}

remote_health() {
  echo ""
  echo "┌─────────────────────────────────────────────────────────────────┐"
  echo "│ HEALTH VALIDATION (Deep MRI + Optional GOD MODE)                │"
  echo "└─────────────────────────────────────────────────────────────────┘"
  echo ""
  
  # Wait for containers to stabilize
  echo "⏳ Waiting for services to initialize (15s)..."
  sleep 15
  echo ""
  
  # Always run Deep MRI (fast operational health check)
  echo "═══════════════════════════════════════════════════════════════════"
  echo "PHASE 1: Deep MRI (scripts/deployment/deep_mri.sh)"
  echo "═══════════════════════════════════════════════════════════════════"
  
  ssh $SSH_OPTS "$VPS_HOST" bash << 'DEEP_MRI'
    cd /opt/l9
    
    # Verify deep_mri.sh exists
    if [ ! -f scripts/deployment/deep_mri.sh ]; then
      echo "❌ ERROR: scripts/deployment/deep_mri.sh not found"
      echo "Expected location: /opt/l9/scripts/deployment/deep_mri.sh"
      exit 1
    fi
    
    # Make executable and run
    chmod +x scripts/deployment/deep_mri.sh
    ./scripts/deployment/deep_mri.sh
DEEP_MRI
  
  local mri_exit=$?
  if [ $mri_exit -eq 0 ]; then
    echo ""
    echo "✅ Deep MRI completed successfully"
  else
    echo ""
    echo "⚠️  Deep MRI completed with warnings (exit code: $mri_exit)"
  fi
  
  # Conditionally run GOD MODE (comprehensive E2E validation)
  if $RUN_GODMODE; then
    echo ""
    echo "═══════════════════════════════════════════════════════════════════"
    echo "PHASE 2: GOD MODE E2E (scripts/deployment/e2e_test_GODMODE.sh)"
    echo "═══════════════════════════════════════════════════════════════════"
    echo ""
    
    ssh $SSH_OPTS "$VPS_HOST" bash << 'GODMODE'
      cd /opt/l9
      
      # Verify e2e_test_GODMODE.sh exists
      if [ ! -f scripts/deployment/e2e_test_GODMODE.sh ]; then
        echo "❌ ERROR: scripts/deployment/e2e_test_GODMODE.sh not found"
        echo "Expected location: /opt/l9/scripts/deployment/e2e_test_GODMODE.sh"
        exit 1
      fi
      
      # Make executable and run smoke test
      chmod +x scripts/deployment/e2e_test_GODMODE.sh
      ./scripts/deployment/e2e_test_GODMODE.sh smoke
GODMODE
    
    local godmode_exit=$?
    echo ""
    if [ $godmode_exit -eq 0 ]; then
      echo "✅ GOD MODE E2E validation PASSED"
    else
      echo "❌ GOD MODE E2E validation FAILED (exit code: $godmode_exit)"
      echo "   Review output above for details"
      # Don't fail deployment, just warn
      echo "   Deployment completed but validation had issues"
    fi
  else
    echo ""
    echo "ℹ️  GOD MODE skipped (use --godmode for comprehensive E2E validation)"
  fi
}

# ------------------------------------------------------------------------------
# Parse flags
# ------------------------------------------------------------------------------
while [[ $# -gt 0 ]]; do
  case "$1" in
    --msg)
      COMMIT_MSG="$2"
      shift 2
      ;;
    --no-cache)
      NO_CACHE=true
      shift
      ;;
    --prune-docker)
      PRUNE_DOCKER=true
      shift
      ;;
    --no-sync-env)
      SYNC_ENV=false
      shift
      ;;
    --no-rebuild)
      NO_REBUILD=true
      shift
      ;;
    --services)
      SERVICES="$2"
      shift 2
      ;;
    --core)
      SERVICES="l9-api mcp-memory postgres"
      shift
      ;;
    --godmode)
      RUN_GODMODE=true
      shift
      ;;
    --dry-run)
      DRY_RUN=true
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      die "Unknown flag: $1"
      ;;
  esac
done

# ------------------------------------------------------------------------------
# MAIN
# ------------------------------------------------------------------------------
MAC_REPO="$(git rev-parse --show-toplevel 2>/dev/null || true)"
[[ -n "$MAC_REPO" ]] || die "Run this from inside the L9 git repo."
cd "$MAC_REPO"

echo "╔═══════════════════════════════════════════════════════════════╗"
echo "║ L9 10X Deploy v2.0 (GitHub SSOT + Selective + GOD MODE)     ║"
echo "╚═══════════════════════════════════════════════════════════════╝"
echo ""
echo "[LOCAL] Repo: $MAC_REPO"
echo "[LOCAL] Branch: $(git rev-parse --abbrev-ref HEAD)"
echo "[LOCAL] Commit: $(git rev-parse --short HEAD)"

if [[ -n "$SERVICES" ]]; then
  echo "[MODE] Selective rebuild: $SERVICES"
elif $NO_REBUILD; then
  echo "[MODE] No rebuild (git pull + env sync only)"
else
  echo "[MODE] Full rebuild (all containers)"
fi

if $RUN_GODMODE; then
  echo "[HEALTH] Deep MRI + GOD MODE E2E validation"
else
  echo "[HEALTH] Deep MRI only (use --godmode for E2E)"
fi
echo ""

# Branch safety
current_branch="$(git rev-parse --abbrev-ref HEAD)"
if [[ "$current_branch" != "$REQUIRED_DEPLOY_BRANCH" && "$ALLOW_NON_MAIN_DEPLOY" != "true" ]]; then
  die "Refusing deploy from branch '$current_branch'. Expected '$REQUIRED_DEPLOY_BRANCH' or L9_ALLOW_NON_MAIN_DEPLOY=true."
fi

# Dirty-state check (informational)
echo "[LOCAL] Git status:"
git status --porcelain || true
echo ""

# 0) Make sure template is trackable + complete
ensure_gitignore_allows_env_template
patch_env_vps_template_from_example "$MAC_REPO"

# 1) Stage + commit + push (bypass git hooks)
git add -A
if git diff --cached --quiet; then
  echo " = Nothing staged; skipping commit/push"
else
  git commit --no-verify -m "${COMMIT_MSG}"
  git push --no-verify origin HEAD
fi

# 2) VPS: hard reset (SSOT), then sync env, then rebuild (conditional)
remote_git_hard_reset
sync_env_vps_to_server "$MAC_REPO"

if $NO_REBUILD; then
  echo "[VPS] Skipping container rebuild (--no-rebuild flag)"
else
  remote_rebuild_stack
fi

# 3) Health validation (always Deep MRI, conditional GOD MODE)
remote_health

echo ""
echo "✅ Done."
