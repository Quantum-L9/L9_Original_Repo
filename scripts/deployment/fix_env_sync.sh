#!/bin/bash
# =============================================================================
# L9 One-Command Env Sync Fix
# Syncs .env.example → .env AND restarts Docker containers with new env vars
#
# Usage:
#   ./fix_env_sync.sh           # Normal mode
#   ./fix_env_sync.sh --quiet  # Quiet mode
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

QUIET=false
if [[ "${1:-}" == "--quiet" ]] || [[ "${1:-}" == "-q" ]]; then
    QUIET=true
fi

log() {
    if [ "$QUIET" = false ]; then
        echo -e "$1"
    fi
}

log_always() {
    echo -e "$1"
}

log_always "${BLUE}╔════════════════════════════════════════════════════════════════╗${NC}"
log_always "${BLUE}║  L9 Env Sync Fix - Sync + Restart Containers                  ║${NC}"
log_always "${BLUE}╚════════════════════════════════════════════════════════════════╝${NC}"
log ""

# Determine if running on VPS or local
if [ -f "/opt/l9/.env" ]; then
    ENV_FILE="/opt/l9/.env"
    EXAMPLE_FILE="/opt/l9/.env.example"
    WORK_DIR="/opt/l9"
    IS_VPS=true
elif [ -f "$REPO_ROOT/.env" ]; then
    ENV_FILE="$REPO_ROOT/.env"
    EXAMPLE_FILE="$REPO_ROOT/.env.example"
    WORK_DIR="$REPO_ROOT"
    IS_VPS=false
else
    log_always "${RED}❌ ERROR: No .env file found${NC}"
    exit 1
fi

if [ ! -f "$EXAMPLE_FILE" ]; then
    log_always "${RED}❌ ERROR: .env.example not found${NC}"
    exit 1
fi

log "📄 Target: ${BLUE}$ENV_FILE${NC}"
log "📋 Source: ${BLUE}$EXAMPLE_FILE${NC}"
log "📁 Working: ${BLUE}$WORK_DIR${NC}"
log ""

# Step 1: Sync env vars
log "${BLUE}[1/3]${NC} Syncing environment variables..."
cd "$WORK_DIR"
bash "$REPO_ROOT/scripts/deployment/sync_env_vars.sh" --quiet
SYNC_EXIT=$?

if [ $SYNC_EXIT -ne 0 ]; then
    log_always "${RED}❌ Env sync failed${NC}"
    exit 1
fi
log_always "${GREEN}✅ Env vars synced${NC}"
log ""

# Step 2: Verify docker-compose.yml exists
if [ ! -f "$WORK_DIR/docker-compose.yml" ]; then
    log_always "${YELLOW}⚠️  No docker-compose.yml found - skipping container restart${NC}"
    exit 0
fi

# Step 3: Restart containers to pick up new env vars
log "${BLUE}[2/3]${NC} Restarting Docker containers to load new env vars..."
cd "$WORK_DIR"

# Check if containers are running
if docker compose ps --format json 2>/dev/null | grep -q '"State":"running"'; then
    log "  Stopping containers..."
    docker compose stop 2>/dev/null || true

    log "  Starting containers with new env vars..."
    if docker compose up -d; then
        log_always "${GREEN}✅ Containers restarted${NC}"
    else
        log_always "${RED}❌ Container restart failed${NC}"
        exit 1
    fi
else
    log "  No running containers - starting fresh..."
    if docker compose up -d; then
        log_always "${GREEN}✅ Containers started${NC}"
    else
        log_always "${RED}❌ Container start failed${NC}"
        exit 1
    fi
fi
log ""

# Step 4: Wait and verify
log "${BLUE}[3/3]${NC} Verifying containers are healthy..."
sleep 5

CONTAINER_COUNT=$(docker compose ps --format json 2>/dev/null | grep -c '"State":"running"' || echo "0")
log "  Running containers: $CONTAINER_COUNT"

if [ "$CONTAINER_COUNT" -gt 0 ]; then
    log_always "${GREEN}✅ All containers running${NC}"
else
    log_always "${YELLOW}⚠️  No containers running - check logs${NC}"
fi

log ""
log_always "${GREEN}╔════════════════════════════════════════════════════════════════╗${NC}"
log_always "${GREEN}║  Env Sync Fix Complete                                         ║${NC}"
log_always "${GREEN}╚════════════════════════════════════════════════════════════════╝${NC}"
log ""
log "View logs:  cd $WORK_DIR && docker compose logs -f"
log ""
