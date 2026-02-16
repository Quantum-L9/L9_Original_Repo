#!/usr/bin/env bash
# deploy-l9-safe.sh - Safe production deployment with rollback capability
# Usage: ./deploy-l9-safe.sh [version]
# Example: ./deploy-l9-safe.sh 0.6.2-l9

set -euo pipefail

VERSION="${1:-latest}"
COMPOSE_FILES="-f docker-compose.yml -f docker-compose.prod.yml"

cd /opt/l9

echo "=== L9 SAFE DEPLOY: v${VERSION} ==="
echo "Timestamp: $(date -Iseconds)"
echo ""

# Phase 1: Pre-flight checks
echo "## Phase 1: Pre-flight Checks"
if [[ -n $(git status --porcelain) ]]; then
    echo "ERROR: Uncommitted changes detected. Commit or stash first."
    git status --short
    exit 1
fi

git fetch origin main --quiet
if [[ $(git rev-list --count HEAD..origin/main) -gt 0 ]]; then
    echo "ERROR: Local is behind origin/main. Pull first."
    exit 1
fi

echo "✓ Git state clean"
echo ""

# Phase 2: Backup current state
echo "## Phase 2: Backup"
BACKUP_TAG="backup-$(date +%Y%m%d-%H%M%S)"
git tag "${BACKUP_TAG}"
echo "✓ Created rollback tag: ${BACKUP_TAG}"
echo ""

# Phase 3: Pull latest code
echo "## Phase 3: Pull Code"
git pull origin main
echo "✓ Code updated"
echo ""

# Phase 4: Build new images
echo "## Phase 4: Build Images (no cache)"
docker compose ${COMPOSE_FILES} build --no-cache l9-api l9-mcp-memory
echo "✓ Images built"
echo ""

# Phase 5: Deploy
echo "## Phase 5: Deploy"
docker compose ${COMPOSE_FILES} up -d
echo "✓ Containers started"
echo ""

# Phase 6: Health validation
echo "## Phase 6: Health Validation (60s grace period)"
sleep 60

HEALTH_CHECK=$(curl -sf http://127.0.0.1:8000/health | jq -r '.status' || echo "FAIL")
if [[ "${HEALTH_CHECK}" == "healthy" ]]; then
    echo "✓ Health check PASSED"
    echo ""
    echo "=== DEPLOY SUCCESS ==="
    echo "Version: ${VERSION}"
    echo "Rollback tag: ${BACKUP_TAG}"
    exit 0
else
    echo "✗ Health check FAILED"
    echo ""
    echo "## INITIATING ROLLBACK"
    git reset --hard "${BACKUP_TAG}"
    docker compose ${COMPOSE_FILES} up -d --force-recreate
    echo ""
    echo "=== DEPLOY FAILED (ROLLED BACK) ==="
    exit 1
fi
