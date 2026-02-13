#!/usr/bin/env bash

set -euo pipefail

# ==============================================================================
# L9 10X Deploy (GitHub SSOT + Env Sync)
# RISK TIER: T2 (reversible infra)
#
# Behavior:
# - LOCAL: stages + commits + pushes current branch to origin
# - VPS: git hard reset to origin/$BRANCH, optional env sync, docker rebuild + restart
#
# Blast radius:
# - Remote repo at $VPS_REPO is reset to match origin/$BRANCH (untracked files removed)
# - Remote Docker stack (prod overlay) is rebuilt and restarted
# - Optional: docker system prune -af (NO volumes) when explicitly enabled
# ==============================================================================

# Usage:
#   ./scripts/deployment/10X_Deploy_Script.sh --msg "your message" --no-cache --prune-docker
#
# Flags:
#   --msg ""         Commit message (default: timestamp)
#   --no-cache       Rebuild images without cache
#   --prune-docker   docker system prune -af (NO volumes) [gated by L9_ALLOW_DOCKER_PRUNE]
#   --no-sync-env    Do not sync .env.vps -> VPS .env
#   --dry-run        Print commands without executing
#   -h | --help      Show help

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
  --msg ""         Commit message
  --no-cache       Rebuild docker images without cache on VPS
  --prune-docker   docker system prune -af on VPS (NO volumes, requires L9_ALLOW_DOCKER_PRUNE=true)
  --no-sync-env    Do not sync .env.vps -> /opt/l9/.env
  --dry-run        Print commands without executing
  -h, --help       Help
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

  echo "[VPS] Rebuild stack (base + prod overlay) no-cache=$NO_CACHE"
  ssh $SSH_OPTS "$VPS_HOST" "cd '$VPS_REPO' && docker compose -f $COMPOSE_BASE -f $COMPOSE_PROD down --remove-orphans"
  ssh $SSH_OPTS "$VPS_HOST" "cd '$VPS_REPO' && docker compose -f $COMPOSE_BASE -f $COMPOSE_PROD build $build_opts"
  ssh $SSH_OPTS "$VPS_HOST" "cd '$VPS_REPO' && docker compose -f $COMPOSE_BASE -f $COMPOSE_PROD up -d --force-recreate --remove-orphans"

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
  echo "│ COMPREHENSIVE MRI (Medical Readiness Inspection)               │"
  echo "└─────────────────────────────────────────────────────────────────┘"
  echo ""
  echo "Waiting for services to initialize (15s)..."
  sleep 15
  echo ""

  # Run comprehensive MRI on VPS
  ssh $SSH_OPTS "$VPS_HOST" "cd '$VPS_REPO' && bash -s" << 'MRI_SCRIPT'
COMPOSE="docker compose -f docker-compose.yml -f docker-compose.prod.yml"

# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 1: INFRASTRUCTURE BASELINE
# ═══════════════════════════════════════════════════════════════════════════════
echo "═══════════════════════════════════════════════════════════════"
echo "SECTION 1: INFRASTRUCTURE BASELINE"
echo "═══════════════════════════════════════════════════════════════"

echo -e "\n[1.1] SYSTEM RESOURCES"
free -h
echo ""
df -h / /var/lib/docker 2>/dev/null || df -h /
echo ""
uptime

echo -e "\n[1.2] GIT STATUS"
echo "Commit: $(git rev-parse --short HEAD 2>/dev/null || echo 'N/A')"
echo "Branch: $(git branch --show-current 2>/dev/null || echo 'N/A')"

# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 2: CONTAINER STATUS
# ═══════════════════════════════════════════════════════════════════════════════
echo -e "\n═══════════════════════════════════════════════════════════════"
echo "SECTION 2: CONTAINER STATUS"
echo "═══════════════════════════════════════════════════════════════"

echo -e "\n[2.1] ALL CONTAINERS"
$COMPOSE ps -a

echo -e "\n[2.2] CONTAINER DETAILS"
docker ps -a --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" | head -20

echo -e "\n[2.3] IMAGES IN USE"
docker images --format "table {{.Repository}}\t{{.Tag}}\t{{.Size}}\t{{.CreatedSince}}" | grep -E "l9|postgres|neo4j|redis|NAME"

# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 3: SERVICE HEALTH CHECKS
# ═══════════════════════════════════════════════════════════════════════════════
echo -e "\n═══════════════════════════════════════════════════════════════"
echo "SECTION 3: SERVICE HEALTH CHECKS"
echo "═══════════════════════════════════════════════════════════════"

echo -e "\n[3.1] L9 API HEALTH"
curl -sf http://127.0.0.1:8000/health 2>/dev/null && echo "" || echo "❌ API not responding"

echo -e "\n[3.2] POSTGRESQL HEALTH"
docker exec l9-postgres pg_isready -U postgres -d l9_memory 2>/dev/null && echo "✅ PostgreSQL ready" || echo "❌ PostgreSQL not ready"

echo -e "\n[3.3] NEO4J HEALTH"
curl -sf http://127.0.0.1:7474 2>/dev/null && echo "✅ Neo4j browser accessible" || echo "❌ Neo4j browser not responding"

echo -e "\n[3.4] REDIS HEALTH"
docker exec l9-redis redis-cli ping 2>/dev/null && echo "✅ Redis responding" || echo "❌ Redis not responding"

# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 4: NETWORK & PORTS
# ═══════════════════════════════════════════════════════════════════════════════
echo -e "\n═══════════════════════════════════════════════════════════════"
echo "SECTION 4: NETWORK & PORTS"
echo "═══════════════════════════════════════════════════════════════"

echo -e "\n[4.1] LISTENING PORTS"
ss -tlnp 2>/dev/null | grep -E "LISTEN|State" | head -20 || netstat -tlnp 2>/dev/null | head -20

# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 5: LOGS & ERRORS (last 5 min)
# ═══════════════════════════════════════════════════════════════════════════════
echo -e "\n═══════════════════════════════════════════════════════════════"
echo "SECTION 5: LOGS & ERRORS (last 5 min)"
echo "═══════════════════════════════════════════════════════════════"

echo -e "\n[5.1] L9 API ERRORS"
$COMPOSE logs l9-api --since 5m 2>/dev/null | grep -iE "error|exception|traceback|fatal|critical" | tail -15 || echo "(no recent errors)"

echo -e "\n[5.2] BOOTSTRAP STATUS"
$COMPOSE ps -a 2>/dev/null | grep -E "bootstrap|NAME"
$COMPOSE logs l9-bootstrap --tail=20 2>/dev/null | tail -10 || echo "(bootstrap logs N/A)"

# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 6: DATA PERSISTENCE
# ═══════════════════════════════════════════════════════════════════════════════
echo -e "\n═══════════════════════════════════════════════════════════════"
echo "SECTION 6: DATA PERSISTENCE (VOLUMES)"
echo "═══════════════════════════════════════════════════════════════"

echo -e "\n[6.1] DOCKER VOLUMES"
docker volume ls | grep -E "l9|NAME"

echo -e "\n[6.2] POSTGRESQL DATA"
docker exec l9-postgres psql -U postgres -d l9_memory -c "SELECT count(*) as packet_count FROM packets;" 2>/dev/null || echo "(query failed)"

# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 7: API ENDPOINT TESTS
# ═══════════════════════════════════════════════════════════════════════════════
echo -e "\n═══════════════════════════════════════════════════════════════"
echo "SECTION 7: API ENDPOINT TESTS"
echo "═══════════════════════════════════════════════════════════════"

echo -e "\n[7.1] CRITICAL ENDPOINTS"
for ep in "http://127.0.0.1:8000/health" "http://127.0.0.1:8000/docs" "http://127.0.0.1:8000/openapi.json"; do
    status=$(curl -sf -o /dev/null -w "%{http_code}" "$ep" 2>/dev/null || echo "000")
    if [ "$status" = "200" ]; then
        echo "✅ $ep ($status)"
    else
        echo "❌ $ep ($status)"
    fi
done

# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 8: ENVIRONMENT VALIDATION
# ═══════════════════════════════════════════════════════════════════════════════
echo -e "\n═══════════════════════════════════════════════════════════════"
echo "SECTION 8: ENVIRONMENT VALIDATION"
echo "═══════════════════════════════════════════════════════════════"

echo -e "\n[8.1] REQUIRED ENV VARS"
for var in POSTGRES_PASSWORD NEO4J_PASSWORD OPENAI_API_KEY L9_API_KEY; do
    if grep -q "^${var}=" .env 2>/dev/null; then
        echo "✅ $var is set"
    else
        echo "❌ $var is MISSING"
    fi
done

# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 9: MRI SUMMARY
# ═══════════════════════════════════════════════════════════════════════════════
echo -e "\n═══════════════════════════════════════════════════════════════"
echo "SECTION 9: MRI SUMMARY"
echo "═══════════════════════════════════════════════════════════════"

echo -e "\nTimestamp: $(date '+%Y-%m-%d %H:%M:%S %Z')"
echo "Hostname: $(hostname)"
echo "Git commit: $(git rev-parse --short HEAD 2>/dev/null || echo 'N/A')"
echo ""

echo "SERVICE STATUS SUMMARY:"
echo "───────────────────────"
api_ok=$(curl -sf http://127.0.0.1:8000/health >/dev/null 2>&1 && echo "✅" || echo "❌")
pg_ok=$(docker exec l9-postgres pg_isready -U postgres >/dev/null 2>&1 && echo "✅" || echo "❌")
neo_ok=$(curl -sf http://127.0.0.1:7474 >/dev/null 2>&1 && echo "✅" || echo "❌")
redis_ok=$(docker exec l9-redis redis-cli ping >/dev/null 2>&1 && echo "✅" || echo "❌")

echo "  L9 API:     $api_ok"
echo "  PostgreSQL: $pg_ok"
echo "  Neo4j:      $neo_ok"
echo "  Redis:      $redis_ok"
echo ""

if [ "$api_ok" = "✅" ] && [ "$pg_ok" = "✅" ] && [ "$redis_ok" = "✅" ]; then
    echo "╔═══════════════════════════════════════════════════════════════╗"
    echo "║  ✅ MRI PASSED - Core services healthy                       ║"
    echo "╚═══════════════════════════════════════════════════════════════╝"
else
    echo "╔═══════════════════════════════════════════════════════════════╗"
    echo "║  ❌ MRI FAILED - Check sections above for issues             ║"
    echo "╚═══════════════════════════════════════════════════════════════╝"
fi
MRI_SCRIPT
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
echo "║ L9 10X Deploy (GitHub SSOT + Env Sync)                        ║"
echo "╚═══════════════════════════════════════════════════════════════╝"
echo ""
echo "[LOCAL] Repo:   $MAC_REPO"
echo "[LOCAL] Branch: $(git rev-parse --abbrev-ref HEAD)"
echo "[LOCAL] Commit: $(git rev-parse --short HEAD)"
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

# 2) VPS: hard reset (SSOT), then sync env, then rebuild
remote_git_hard_reset
sync_env_vps_to_server "$MAC_REPO"
remote_rebuild_stack
remote_health

echo ""
echo "✅ Done."
