#!/usr/bin/env bash
# rollback-l9.sh - Emergency rollback to last known good state
# Usage: ./rollback-l9.sh [backup-tag]
# Example: ./rollback-l9.sh backup-20260213-091500

set -euo pipefail

BACKUP_TAG="${1:-}"
COMPOSE_FILES="-f docker-compose.yml -f docker-compose.prod.yml"

cd /opt/l9

echo "=== L9 EMERGENCY ROLLBACK ==="
echo "Timestamp: $(date -Iseconds)"
echo ""

# If no tag provided, show available backup tags
if [[ -z "${BACKUP_TAG}" ]]; then
    echo "Available backup tags:"
    git tag | grep "^backup-" | tail -10
    echo ""
    echo "Usage: ./rollback-l9.sh <backup-tag>"
    exit 1
fi

# Verify tag exists
if ! git rev-parse "${BACKUP_TAG}" >/dev/null 2>&1; then
    echo "ERROR: Tag '${BACKUP_TAG}' does not exist"
    exit 1
fi

echo "## Rolling back to: ${BACKUP_TAG}"
git reset --hard "${BACKUP_TAG}"
echo "✓ Code reverted"
echo ""

echo "## Rebuilding images from rollback state"
docker compose ${COMPOSE_FILES} build --no-cache l9-api l9-mcp-memory
echo "✓ Images rebuilt"
echo ""

echo "## Recreating containers"
docker compose ${COMPOSE_FILES} up -d --force-recreate
echo "✓ Containers recreated"
echo ""

echo "## Waiting 60s for stabilization"
sleep 60
echo ""

echo "## Health Check"
HEALTH_STATUS=$(curl -sf http://127.0.0.1:8000/health | jq -r '.status' || echo "FAIL")
echo "Health: ${HEALTH_STATUS}"
echo ""

if [[ "${HEALTH_STATUS}" == "healthy" ]]; then
    echo "=== ROLLBACK SUCCESS ==="
else
    echo "=== ROLLBACK UNCERTAIN - Manual review required ==="
    echo "Check logs: docker compose ${COMPOSE_FILES} logs l9-api --tail=100"
fi
