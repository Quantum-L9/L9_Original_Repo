#!/usr/bin/env bash
# cleanup-l9.sh - Free memory, remove dangling containers/images/volumes
# Usage: ./cleanup-l9.sh [--aggressive]
# Purpose: Reclaim disk space and memory safely

set -euo pipefail

AGGRESSIVE="${1:-}"
COMPOSE_FILES="-f docker-compose.yml -f docker-compose.prod.yml"

cd /opt/l9

echo "=== L9 CLEANUP ==="
echo "Timestamp: $(date -Iseconds)"
echo ""

# Phase 1: Show current resource usage
echo "## Phase 1: Current Resource Usage"
echo "### Disk Usage"
df -h / | grep -E "Filesystem|/$"
echo ""
echo "### Docker Disk Usage"
docker system df
echo ""
echo "### Memory Usage"
free -h
echo ""

# Phase 2: Stop and remove orphaned containers
echo "## Phase 2: Remove Orphaned Containers"
ORPHANS=$(docker compose ${COMPOSE_FILES} ps -a --filter "status=exited" -q 2>/dev/null || echo "")
if [[ -n "${ORPHANS}" ]]; then
    echo "Found exited containers, removing..."
    docker compose ${COMPOSE_FILES} rm -f
    echo "✓ Orphaned containers removed"
else
    echo "✓ No orphaned containers found"
fi
echo ""

# Phase 3: Remove dangling images
echo "## Phase 3: Remove Dangling Images"
DANGLING=$(docker images -f "dangling=true" -q)
if [[ -n "${DANGLING}" ]]; then
    echo "Found $(echo ${DANGLING} | wc -w) dangling images, removing..."
    docker rmi ${DANGLING} 2>/dev/null || echo "Some images still in use, skipping"
    echo "✓ Dangling images cleaned"
else
    echo "✓ No dangling images found"
fi
echo ""

# Phase 4: Remove unused build cache
echo "## Phase 4: Remove Build Cache"
docker builder prune -f
echo "✓ Build cache cleared"
echo ""

# Phase 5: Prune stopped containers (safe)
echo "## Phase 5: Prune Stopped Containers"
docker container prune -f
echo "✓ Stopped containers removed"
echo ""

# Phase 6: Aggressive mode (optional)
if [[ "${AGGRESSIVE}" == "--aggressive" ]]; then
    echo "## Phase 6: AGGRESSIVE CLEANUP"
    echo "WARNING: This will remove ALL unused images and volumes"
    echo "Sleeping 5 seconds... (Ctrl+C to abort)"
    sleep 5
    
    echo "### Removing unused images"
    docker image prune -a -f
    echo "✓ Unused images removed"
    echo ""
    
    echo "### Removing unused volumes (excluding active volumes)"
    # Get list of volumes used by running services
    ACTIVE_VOLUMES=$(docker compose ${COMPOSE_FILES} config --volumes 2>/dev/null || echo "")
    ALL_VOLUMES=$(docker volume ls -q)
    
    for vol in ${ALL_VOLUMES}; do
        if ! echo "${ACTIVE_VOLUMES}" | grep -q "${vol}"; then
            echo "Removing unused volume: ${vol}"
            docker volume rm "${vol}" 2>/dev/null || echo "  ↳ Volume in use, skipping"
        fi
    done
    echo "✓ Unused volumes checked"
    echo ""
    
    echo "### Removing unused networks"
    docker network prune -f
    echo "✓ Unused networks removed"
    echo ""
fi

# Phase 7: Clean system logs older than 7 days
echo "## Phase 7: Clean Old Docker Logs"
find /var/lib/docker/containers/ -name "*.log" -mtime +7 -exec truncate -s 0 {} \; 2>/dev/null || echo "  ↳ No old logs or permission denied"
echo "✓ Old logs truncated"
echo ""

# Phase 8: Clear apt cache (VPS-specific)
echo "## Phase 8: Clear APT Cache"
sudo apt-get clean 2>/dev/null || echo "  ↳ Permission denied or not available"
echo "✓ APT cache cleared"
echo ""

# Phase 9: Show freed space
echo "## Phase 9: Post-Cleanup Resource Usage"
echo "### Disk Usage"
df -h / | grep -E "Filesystem|/$"
echo ""
echo "### Docker Disk Usage"
docker system df
echo ""
echo "### Memory Usage"
free -h
echo ""

# Phase 10: Check running services still healthy
echo "## Phase 10: Service Health Check"
docker compose ${COMPOSE_FILES} ps --filter "status=running"
echo ""

HEALTH_CHECK=$(curl -sf http://127.0.0.1:8000/health | jq -r '.status' 2>/dev/null || echo "unreachable")
if [[ "${HEALTH_CHECK}" == "healthy" ]]; then
    echo "✓ L9 API still healthy after cleanup"
else
    echo "⚠ L9 API health check failed: ${HEALTH_CHECK}"
    echo "  Run: docker compose ${COMPOSE_FILES} logs l9-api --tail=50"
fi
echo ""

echo "=== CLEANUP COMPLETE ==="
if [[ "${AGGRESSIVE}" == "--aggressive" ]]; then
    echo "Mode: AGGRESSIVE"
else
    echo "Mode: SAFE (run with --aggressive for deeper clean)"
fi
